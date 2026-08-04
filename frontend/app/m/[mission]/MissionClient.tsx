'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ChatBox, { type ChatMsg } from '@/components/ChatBox';
import ToolCallPanel, { type ToolEvent } from '@/components/ToolCallPanel';
import SuccessOverlay from '@/components/SuccessOverlay';

type Mission = {
  id: string;
  title: string;
  summary: string;
  target_agent: string;
  available_tools: string[];
  solve_count: number;
  hint_1: string;
  hint_2: string;
  hint_1_after_turns: number;
  hint_2_after_turns: number;
  difficulty?: string;
  threat_class?: string;
  briefing_md?: string;
  internal_email_domain?: string;
};

type TraceStep = {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content?: string | null;
  tool_calls?: Array<{
    id: string;
    type: string;
    function: { name: string; arguments: string };
  }>;
  tool_call_id?: string;
  name?: string;
};

type SolveStatus = {
  solved: boolean;
  writeup_md: string | null;
  defense_note_md: string | null;
  flag: string | null;
  solve_count: number;
  trace: TraceStep[] | null;
  trace_labels: Record<string, unknown> | null;
};

type TraceLabels = {
  tool_roles?: Record<string, string>;
  trifecta?: Array<{ label: string; tool: string; description: string }>;
  injection_tools?: string[];
  injection_field?: string;
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy:   'text-emerald-400 border-emerald-800/60',
  medium: 'text-amber-400 border-amber-800/60',
  hard:   'text-rose-400 border-rose-800/60',
};

function getOrCreateSessionId(): string {
  if (typeof window === 'undefined') return '';
  const KEY = 'agentdojo:session_id';
  let v = window.localStorage.getItem(KEY);
  if (!v) {
    v = crypto.randomUUID().replace(/-/g, '');
    window.localStorage.setItem(KEY, v);
  }
  return v;
}

export default function MissionClient({ mission }: { mission: Mission }) {
  const [sessionId, setSessionId]         = useState('');
  const [started, setStarted]             = useState(false);
  const [messages, setMessages]           = useState<ChatMsg[]>([]);
  const [tools, setTools]                 = useState<ToolEvent[]>([]);
  const [busy, setBusy]                   = useState(false);
  const [turns, setTurns]                 = useState(0);
  const [solve, setSolve]                 = useState<SolveStatus | null>(null);
  const [overlayOpen, setOverlayOpen]     = useState(false);
  const [error, setError]                 = useState<string | null>(null);
  const [capacityCountdown, setCapacityCountdown] = useState<number | null>(null);
  const pendingMsgRef  = useRef<string | null>(null);
  const pollRef        = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
    if (typeof window !== 'undefined') {
      const k = `agentdojo:started:${mission.id}`;
      if (window.localStorage.getItem(k) === '1') setStarted(true);
    }
  }, [mission.id]);

  // Capacity countdown auto-retry
  useEffect(() => {
    if (capacityCountdown === null) return;
    if (capacityCountdown <= 0) {
      setCapacityCountdown(null);
      const msg = pendingMsgRef.current;
      pendingMsgRef.current = null;
      if (msg) void sendMessage(msg);
      return;
    }
    const t = setTimeout(() => setCapacityCountdown((c) => (c ?? 1) - 1), 1000);
    return () => clearTimeout(t);
  }, [capacityCountdown]); // eslint-disable-line react-hooks/exhaustive-deps

  const beginMission = useCallback(() => {
    setStarted(true);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(`agentdojo:started:${mission.id}`, '1');
    }
  }, [mission.id]);

  const checkSolve = useCallback(async () => {
    if (!sessionId) return;
    try {
      const r = await fetch(`/api/solve/${mission.id}/${sessionId}`, { cache: 'no-store' });
      if (!r.ok) return;
      const data: SolveStatus = await r.json();
      setSolve(data);
      if (data.solved) {
        setOverlayOpen(true);
        if (pollRef.current) clearInterval(pollRef.current);
      }
    } catch { /* ignore */ }
  }, [mission.id, sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    void checkSolve();
    pollRef.current = setInterval(checkSolve, 4000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [sessionId, checkSolve]);

  const sendMessage = useCallback(async (text: string) => {
    if (!sessionId || busy) return;
    setError(null);
    setBusy(true);
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    try {
      const r = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, mission_id: mission.id, message: text }),
      });
      if (!r.ok) {
        // The backend distinguishes transient pressure (retry) from a hard
        // stop (do not retry) via the `detail` field. Retrying a parked LLM
        // or an exhausted daily budget just spins forever.
        const detail = await r.json().then((b) => b?.detail).catch(() => null);

        if (r.status === 503 && detail === 'at_capacity') {
          const retryAfter = parseInt(r.headers.get('Retry-After') ?? '15', 10);
          pendingMsgRef.current = text;
          setMessages((prev) => prev.slice(0, -1));
          setCapacityCountdown(retryAfter);
        } else if (r.status === 503) {
          setError('The agent is parked for maintenance. The missions and write-ups still work — try again later.');
        } else if (r.status === 429 && detail === 'daily_budget_exhausted') {
          setError("Today's global budget for this demo is spent. It resets at 00:00 UTC — or run it locally, it's one command.");
        } else if (r.status === 429) {
          const ra = r.headers.get('Retry-After');
          setError(
            ra
              ? `Rate limit reached. Try again in ${Math.ceil(parseInt(ra, 10) / 60)} min.`
              : 'Rate limit reached. Try again later.',
          );
        } else {
          setError(`Backend error ${r.status}`);
        }
        setBusy(false);
        return;
      }
      const reader = r.body?.getReader();
      if (!reader) { setError('No stream from server.'); setBusy(false); return; }
      const decoder = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        // sse-starlette frames events with CRLF (\r\n\r\n between events); the
        // split below looks for \n\n, so normalize first or no frame ever
        // matches and nothing renders. Re-run on the whole buffer each read so
        // a CRLF split across chunk boundaries still normalizes.
        buf = buf.replace(/\r\n/g, '\n');
        let idx;
        while ((idx = buf.indexOf('\n\n')) !== -1) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          const dataLines = frame.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim());
          if (dataLines.length === 0) continue;
          try { handleEvent(JSON.parse(dataLines.join('\n'))); } catch { /* ignore */ }
        }
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
      void checkSolve();
    }
  }, [busy, mission.id, sessionId, checkSolve]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleEvent = (evt: Record<string, unknown>) => {
    switch (evt.type) {
      case 'assistant_text':
        setMessages((prev) => [...prev, { role: 'assistant', content: evt.content as string }]);
        break;
      case 'tool_call':
        setTools((prev) => [...prev, {
          kind: 'call', id: evt.id as string, name: evt.name as string,
          arguments: evt.arguments as Record<string, unknown>,
        }]);
        break;
      case 'tool_result':
        setTools((prev) => [...prev, {
          kind: 'result', id: evt.id as string, name: evt.name as string, content: evt.content as string,
        }]);
        break;
      case 'done':  setTurns((evt.turns as number) ?? 0); break;
      case 'solve': void checkSolve(); break;
      case 'error': setError((evt.message as string) || 'agent error'); break;
    }
  };

  const hint = useMemo(() => {
    if (solve?.solved) return null;
    if (turns >= mission.hint_2_after_turns) return mission.hint_2;
    if (turns >= mission.hint_1_after_turns) return mission.hint_1;
    return null;
  }, [turns, mission.hint_1, mission.hint_2, mission.hint_1_after_turns, mission.hint_2_after_turns, solve?.solved]);

  const agentDisplayName = (mission.target_agent ?? 'agent').replace(/_/g, ' ');

  // ---- Briefing screen ----
  if (!started) {
    return (
      <main className="min-h-screen flex flex-col">
        <header className="border-b border-line px-6 py-3 flex items-center justify-between">
          <a href="/" className="label text-zinc-600 hover:text-accent transition-colors">
            ← agentdojo.live
          </a>
          <div className="label text-zinc-700">
            session <span className="text-zinc-500">{sessionId.slice(0, 8) || '…'}</span>
          </div>
        </header>

        <section className="mx-auto w-full max-w-2xl px-6 py-10">
          <div className="label text-zinc-600 mb-2">{mission.id}</div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-100 leading-tight">
            {mission.title}
          </h1>

          <div className="mt-4 flex flex-wrap gap-2">
            {mission.difficulty && (
              <span className={`rounded border px-2 py-0.5 label ${DIFFICULTY_COLORS[mission.difficulty] ?? DIFFICULTY_COLORS.easy}`}>
                {mission.difficulty}
              </span>
            )}
            {mission.threat_class && (
              <span className="rounded border border-zinc-700/60 px-2 py-0.5 label text-zinc-500">
                {mission.threat_class}
              </span>
            )}
            <span className="rounded border border-zinc-700/60 px-2 py-0.5 label text-zinc-600">
              {mission.solve_count} solves
            </span>
          </div>

          <div className="prose prose-invert mt-6 max-w-none text-sm">
            <ReactMarkdown>
              {mission.briefing_md?.length ? mission.briefing_md : mission.summary}
            </ReactMarkdown>
          </div>

          {mission.available_tools.length > 0 && (
            <div className="mt-6 card p-4">
              <div className="label text-zinc-500 mb-2">agent tools</div>
              <div className="code text-zinc-300 text-xs">
                {mission.available_tools.join('  ·  ')}
              </div>
            </div>
          )}

          <div className="mt-8 flex items-center gap-4">
            <button
              onClick={beginMission}
              className="rounded bg-accent px-6 py-2.5 font-semibold text-white hover:opacity-90 transition-opacity"
            >
              Begin mission →
            </button>
            <span className="label text-zinc-700">per-IP rate limit applies</span>
          </div>
        </section>
      </main>
    );
  }

  // ---- Chat screen ----
  return (
    <main className="h-screen flex flex-col">
      {/* Top nav bar */}
      <header className="border-b border-line px-5 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <a href="/" className="label text-zinc-600 hover:text-accent transition-colors">
            ← agentdojo.live
          </a>
          <span className="text-zinc-700">·</span>
          <span className="font-display font-semibold text-zinc-200">{mission.title}</span>
          {mission.threat_class && (
            <span className="rounded border border-zinc-700/60 px-2 py-0.5 label text-zinc-500 hidden sm:inline">
              {mission.threat_class}
            </span>
          )}
        </div>
        <div className="label text-zinc-700 text-right">
          <span className="hidden sm:inline">session </span>
          <span className="code text-zinc-500">{sessionId.slice(0, 8)}</span>
          <span className="ml-3 hidden sm:inline">turn {turns}</span>
        </div>
      </header>

      {/* Status / hint / error bar */}
      {(hint || error || capacityCountdown !== null) && (
        <div className="border-b border-line px-5 py-2 text-xs shrink-0">
          {hint && (
            <span className="text-warn">Hint: {hint}</span>
          )}
          {capacityCountdown !== null && (
            <span className="text-zinc-400">
              At capacity — retrying in{' '}
              <span className="font-bold text-accent">{capacityCountdown}s</span>
            </span>
          )}
          {error && <span className="text-rose-400">⚠ {error}</span>}
        </div>
      )}

      {/* Two-pane layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 overflow-hidden min-h-0">
        <div className="border-r border-line overflow-hidden">
          <ChatBox
            messages={messages}
            onSend={sendMessage}
            disabled={busy || !sessionId || capacityCountdown !== null}
            agentName={agentDisplayName}
            thinking={busy && messages.length > 0 && messages[messages.length - 1]?.role === 'user'}
          />
        </div>
        <div className="overflow-hidden">
          <ToolCallPanel events={tools} availableTools={mission.available_tools} />
        </div>
      </div>

      {/* Post-solve overlay */}
      {overlayOpen && solve?.solved && solve.writeup_md && solve.flag && (
        <SuccessOverlay
          missionTitle={mission.title}
          missionId={mission.id}
          flag={solve.flag}
          writeup={solve.writeup_md}
          defenseNote={solve.defense_note_md}
          solveCount={solve.solve_count}
          trace={solve.trace}
          traceLabels={solve.trace_labels as TraceLabels | null}
          sessionId={sessionId}
          onClose={() => setOverlayOpen(false)}
        />
      )}
    </main>
  );
}
