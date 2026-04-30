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

type SolveStatus = {
  solved: boolean;
  writeup_md: string | null;
  flag: string | null;
  solve_count: number;
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
  const [sessionId, setSessionId] = useState('');
  const [started, setStarted] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState(0);
  const [solve, setSolve] = useState<SolveStatus | null>(null);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
    // Per-mission "already started" flag: returning visitors with chat
    // history shouldn't have to re-read the briefing every time.
    if (typeof window !== 'undefined') {
      const k = `agentdojo:started:${mission.id}`;
      if (window.localStorage.getItem(k) === '1') setStarted(true);
    }
  }, [mission.id]);

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
    } catch {
      /* ignore */
    }
  }, [mission.id, sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    void checkSolve();
    pollRef.current = setInterval(checkSolve, 4000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sessionId, checkSolve]);

  const send = useCallback(
    async (text: string) => {
      if (!sessionId || busy) return;
      setError(null);
      setBusy(true);
      setMessages((prev) => [...prev, { role: 'user', content: text }]);
      try {
        const r = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            mission_id: mission.id,
            message: text,
          }),
        });
        if (!r.ok) {
          if (r.status === 429) {
            const ra = r.headers.get('Retry-After') ?? '?';
            setError(`Rate limit reached. Try again in ${ra}s.`);
          } else {
            setError(`Backend error ${r.status}`);
          }
          setBusy(false);
          return;
        }
        const reader = r.body?.getReader();
        if (!reader) {
          setError('No stream from server.');
          setBusy(false);
          return;
        }
        const decoder = new TextDecoder();
        let buf = '';
        // SSE parser: split on double newline, lines start with "event:" / "data:".
        // We rely on the data: payload (JSON of the event object) which itself carries `type`.
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n\n')) !== -1) {
            const frame = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            const dataLines = frame
              .split('\n')
              .filter((l) => l.startsWith('data:'))
              .map((l) => l.slice(5).trim());
            if (dataLines.length === 0) continue;
            try {
              const evt = JSON.parse(dataLines.join('\n'));
              handleEvent(evt);
            } catch {
              /* ignore */
            }
          }
        }
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
        // Solve may have just happened.
        void checkSolve();
      }
    },
    [busy, mission.id, sessionId, checkSolve]
  );

  const handleEvent = (evt: any) => {
    switch (evt.type) {
      case 'assistant_text':
        setMessages((prev) => [...prev, { role: 'assistant', content: evt.content }]);
        break;
      case 'tool_call':
        setTools((prev) => [
          ...prev,
          { kind: 'call', id: evt.id, name: evt.name, arguments: evt.arguments },
        ]);
        break;
      case 'tool_result':
        setTools((prev) => [
          ...prev,
          { kind: 'result', id: evt.id, name: evt.name, content: evt.content },
        ]);
        break;
      case 'done':
        setTurns(evt.turns ?? 0);
        break;
      case 'solve':
        // Loop emitted a solve. Fetch the writeup + flag immediately so the
        // overlay opens without waiting for the 4s poll cycle.
        void checkSolve();
        break;
      case 'error':
        setError(evt.message || 'agent error');
        break;
    }
  };

  const hint = useMemo(() => {
    if (solve?.solved) return null;
    if (turns >= mission.hint_2_after_turns) return mission.hint_2;
    if (turns >= mission.hint_1_after_turns) return mission.hint_1;
    return null;
  }, [turns, mission.hint_1, mission.hint_2, mission.hint_1_after_turns, mission.hint_2_after_turns, solve?.solved]);

  if (!started) {
    return (
      <main className="min-h-screen flex flex-col">
        <header className="border-b border-line px-6 py-3 flex items-center justify-between">
          <a href="/" className="text-sm text-zinc-500 hover:text-zinc-300">
            ← agentdojo.live
          </a>
          <div className="text-xs text-zinc-500">
            session: <span className="code">{sessionId.slice(0, 8) || '…'}</span>
          </div>
        </header>

        <section className="mx-auto w-full max-w-3xl px-6 py-10">
          <div className="text-xs uppercase tracking-widest text-zinc-500">
            {mission.id}
          </div>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">{mission.title}</h1>
          <div className="mt-3 flex flex-wrap gap-2">
            {mission.difficulty && (
              <span className="rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-300">
                {mission.difficulty}
              </span>
            )}
            {mission.threat_class && (
              <span className="rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-300">
                {mission.threat_class}
              </span>
            )}
            <span className="rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-300">
              {mission.solve_count} solves
            </span>
          </div>

          <div className="prose prose-invert mt-6 max-w-none text-sm">
            <ReactMarkdown>
              {mission.briefing_md && mission.briefing_md.length > 0
                ? mission.briefing_md
                : mission.summary}
            </ReactMarkdown>
          </div>

          {mission.available_tools.length > 0 && (
            <div className="mt-6 card p-4 text-xs text-zinc-400">
              <div className="text-zinc-200 font-semibold">Tools the agent can call</div>
              <div className="mt-2 font-mono text-zinc-300">
                {mission.available_tools.join(', ')}
              </div>
            </div>
          )}

          <div className="mt-8 flex items-center gap-4">
            <button
              onClick={beginMission}
              className="rounded bg-accent px-5 py-2 font-semibold text-ink hover:opacity-90"
            >
              Begin mission →
            </button>
            <span className="text-xs text-zinc-500">
              Per-IP rate limit applies. Be civil.
            </span>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="h-screen flex flex-col">
      <header className="border-b border-line px-6 py-3 flex items-center justify-between">
        <div>
          <a href="/" className="text-sm text-zinc-500 hover:text-zinc-300">
            ← agentdojo.live
          </a>
          <h1 className="text-lg font-semibold">
            <span className="text-zinc-500">{mission.id}</span> ·{' '}
            <span className="text-accent">{mission.title}</span>
            {mission.threat_class && (
              <span className="ml-3 align-middle rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs font-normal text-zinc-300">
                {mission.threat_class}
              </span>
            )}
          </h1>
        </div>
        <div className="text-right text-xs text-zinc-500">
          <div>session: <span className="code">{sessionId.slice(0, 8) || '…'}</span></div>
          <div>turns: {turns}</div>
        </div>
      </header>

      <section className="border-b border-line px-6 py-3 text-sm text-zinc-400">
        {mission.summary}
        {hint && (
          <div className="mt-2 text-warn">
            Hint: {hint}
          </div>
        )}
        {error && <div className="mt-2 text-red-400">⚠ {error}</div>}
      </section>

      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 overflow-hidden">
        <div className="border-r border-line h-full overflow-hidden">
          <ChatBox messages={messages} onSend={send} disabled={busy || !sessionId} />
        </div>
        <div className="h-full overflow-hidden">
          <ToolCallPanel events={tools} availableTools={mission.available_tools} />
        </div>
      </div>

      {overlayOpen && solve?.solved && solve.writeup_md && solve.flag && (
        <SuccessOverlay
          missionTitle={mission.title}
          flag={solve.flag}
          writeup={solve.writeup_md}
          solveCount={solve.solve_count}
          onClose={() => setOverlayOpen(false)}
        />
      )}
    </main>
  );
}
