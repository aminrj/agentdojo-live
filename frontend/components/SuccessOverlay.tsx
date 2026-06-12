'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

// ---- Types ----------------------------------------------------------------

type ToolCall = {
  id: string;
  type: string;
  function: { name: string; arguments: string };
};

type TraceStep = {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content?: string | null;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  name?: string;
};

type TrifectaItem = {
  label: string;
  tool: string;
  description: string;
};

export type TraceLabels = {
  tool_roles?: Record<string, string>;
  trifecta?: TrifectaItem[];
  injection_tools?: string[];
  injection_field?: string;
};

// ---- Trifecta label colors ------------------------------------------------

const TRIFECTA_STYLES: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  'private-data-access':  { border: 'border-blue-800/60',   bg: 'bg-blue-950/30',   text: 'text-blue-300',   dot: 'bg-blue-400' },
  'untrusted-content':    { border: 'border-orange-800/60', bg: 'bg-orange-950/30', text: 'text-orange-300', dot: 'bg-orange-400' },
  'outbound-action':      { border: 'border-rose-800/60',   bg: 'bg-rose-950/30',   text: 'text-rose-300',   dot: 'bg-rose-400' },
  'tool-poisoning':       { border: 'border-orange-800/60', bg: 'bg-orange-950/30', text: 'text-orange-300', dot: 'bg-orange-400' },
  'context-injection':    { border: 'border-amber-800/60',  bg: 'bg-amber-950/30',  text: 'text-amber-300',  dot: 'bg-amber-400' },
  'outbound-exfiltration':{ border: 'border-rose-800/60',   bg: 'bg-rose-950/30',   text: 'text-rose-300',   dot: 'bg-rose-400' },
  'tool-discovery':       { border: 'border-zinc-700/60',   bg: 'bg-zinc-900/40',   text: 'text-zinc-400',   dot: 'bg-zinc-500' },
  'data-access':          { border: 'border-blue-800/60',   bg: 'bg-blue-950/30',   text: 'text-blue-300',   dot: 'bg-blue-400' },
  'file-read':            { border: 'border-zinc-700/60',   bg: 'bg-zinc-900/40',   text: 'text-zinc-400',   dot: 'bg-zinc-500' },
  'injection-planted':    { border: 'border-orange-800/60', bg: 'bg-orange-950/30', text: 'text-orange-300', dot: 'bg-orange-400' },
  'file-search':          { border: 'border-zinc-700/60',   bg: 'bg-zinc-900/40',   text: 'text-zinc-400',   dot: 'bg-zinc-500' },
};

function roleStyle(role: string) {
  return TRIFECTA_STYLES[role] ?? { border: 'border-zinc-700/60', bg: 'bg-zinc-900/40', text: 'text-zinc-400', dot: 'bg-zinc-500' };
}

// ---- Helpers --------------------------------------------------------------

function parseArgs(raw: string): Record<string, unknown> {
  try { return JSON.parse(raw); } catch { return { raw }; }
}

function extractPayload(trace: TraceStep[], labels?: TraceLabels): string {
  if (!labels) return '';
  const { injection_tools = [], injection_field = 'content' } = labels;
  for (const step of trace) {
    if (step.role !== 'assistant' || !step.tool_calls) continue;
    for (const tc of step.tool_calls) {
      if (injection_tools.includes(tc.function.name)) {
        const args = parseArgs(tc.function.arguments);
        const val = args[injection_field];
        if (typeof val === 'string') return val;
      }
    }
  }
  return trace.find((s) => s.role === 'user')?.content ?? '';
}

// ---- Trace step renderer -------------------------------------------------

function TraceStep({
  step,
  labels,
}: {
  step: TraceStep;
  labels?: TraceLabels;
}) {
  const [expanded, setExpanded] = useState(false);
  const injectionTools  = labels?.injection_tools ?? [];
  const injectionField  = labels?.injection_field ?? '';
  const toolRoles       = labels?.tool_roles ?? {};

  if (step.role === 'system') {
    return (
      <div className="rounded border border-zinc-800/40">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-full px-3 py-1.5 text-left label text-zinc-700 hover:text-zinc-500 transition-colors"
        >
          {expanded ? '▾' : '▸'} system prompt
        </button>
        {expanded && (
          <pre className="border-t border-zinc-800/40 px-3 pb-3 pt-2 code text-[11px] whitespace-pre-wrap text-zinc-600">
            {step.content}
          </pre>
        )}
      </div>
    );
  }

  if (step.role === 'user') {
    return (
      <div className="rounded border border-blue-900/40 bg-blue-950/10 px-3 py-2.5">
        <div className="label text-blue-500 mb-1.5">attacker</div>
        <div className="text-sm text-zinc-300 leading-relaxed">{step.content}</div>
      </div>
    );
  }

  if (step.role === 'assistant') {
    const hasText = !!(step.content?.trim());
    return (
      <div className="space-y-1.5">
        {hasText && (
          <div className="rounded border border-emerald-900/40 bg-emerald-950/10 px-3 py-2.5">
            <div className="label text-emerald-500 mb-1.5">agent</div>
            <div className="text-sm text-zinc-300 leading-relaxed">{step.content}</div>
          </div>
        )}
        {step.tool_calls?.map((tc) => {
          const isInjection = injectionTools.includes(tc.function.name);
          const role   = toolRoles[tc.function.name];
          const style  = role ? roleStyle(role) : null;
          const args   = parseArgs(tc.function.arguments);
          return (
            <div
              key={tc.id}
              className={`rounded border px-3 py-2.5 ${
                isInjection
                  ? 'border-orange-700/60 bg-orange-950/15'
                  : 'border-zinc-700/50 bg-canvas'
              }`}
            >
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="label text-amber-500">tool call</span>
                <code className="code text-zinc-200 text-[11px]">{tc.function.name}()</code>
                {role && style && (
                  <span className={`rounded px-1.5 py-0.5 label ${style.text} ${style.bg} border ${style.border}`}>
                    {role}
                  </span>
                )}
                {isInjection && (
                  <span className="rounded border border-orange-700/60 bg-orange-900/30 px-1.5 py-0.5 label text-orange-300">
                    injection vector
                  </span>
                )}
              </div>
              <div className="space-y-1 code text-[11px]">
                {Object.entries(args).map(([k, v]) => {
                  const isPayload = isInjection && k === injectionField;
                  return (
                    <div key={k} className="break-all">
                      <span className="text-zinc-600">{k}: </span>
                      <span className={isPayload ? 'rounded bg-orange-900/30 px-1 text-orange-200' : 'text-zinc-400'}>
                        {typeof v === 'string' ? `"${v}"` : JSON.stringify(v)}
                      </span>
                      {isPayload && (
                        <span className="ml-2 label text-orange-500">← injection payload</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  if (step.role === 'tool') {
    const role  = toolRoles[step.name ?? ''];
    const style = role ? roleStyle(role) : null;
    const isDanger = role === 'outbound-exfiltration';
    return (
      <div className={`rounded border px-3 py-2.5 ${isDanger ? 'border-rose-800/60 bg-rose-950/10' : 'border-zinc-800/50 bg-ink'}`}>
        <div className="flex flex-wrap items-center gap-2 mb-1.5">
          <span className="label text-zinc-600">tool result</span>
          <code className="code text-zinc-400 text-[11px]">{step.name}</code>
          {role && style && (
            <span className={`rounded px-1.5 py-0.5 label ${style.text} ${style.bg} border ${style.border}`}>
              {role}
            </span>
          )}
        </div>
        <pre className="code text-[11px] text-zinc-500 whitespace-pre-wrap break-all leading-relaxed">
          {step.content}
        </pre>
      </div>
    );
  }

  return null;
}

// ---- Trifecta banner -----------------------------------------------------

function TrifectaBanner({ trifecta }: { trifecta: TrifectaItem[] }) {
  return (
    <div className="rounded border border-zinc-700/40 bg-zinc-900/60 p-4 mb-5">
      <div className="label text-zinc-600 mb-3">attack chain</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {trifecta.map((item, i) => {
          const style = TRIFECTA_STYLES[item.label] ?? TRIFECTA_STYLES['file-read'];
          return (
            <div key={i} className={`rounded border px-3 py-2.5 ${style.border} ${style.bg}`}>
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}`} />
                <span className={`label ${style.text}`}>{item.label}</span>
              </div>
              <code className={`code text-[10px] opacity-60 block mb-1 ${style.text}`}>{item.tool}()</code>
              <p className={`text-xs leading-snug opacity-80 ${style.text}`}>{item.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---- Wall of solves publish ----------------------------------------------

function WallPublish({ missionId, sessionId, defaultPayload }: {
  missionId: string; sessionId: string; defaultPayload: string;
}) {
  const [username, setUsername] = useState(() =>
    typeof window !== 'undefined' ? window.localStorage.getItem('agentdojo:username') ?? '' : ''
  );
  const [payload, setPayload]  = useState(defaultPayload);
  const [status, setStatus]    = useState<'idle' | 'busy' | 'done' | 'error'>('idle');

  const publish = async () => {
    const name = username.trim();
    if (!name) return;
    if (typeof window !== 'undefined') window.localStorage.setItem('agentdojo:username', name);
    setStatus('busy');
    try {
      const r = await fetch(`/api/wall/${missionId}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, username: name, payload }),
      });
      setStatus(r.ok ? 'done' : 'error');
    } catch { setStatus('error'); }
  };

  if (status === 'done') {
    return (
      <div className="rounded border border-emerald-800/50 bg-emerald-950/20 px-4 py-3 text-sm text-emerald-300">
        Published to the wall of solves.
      </div>
    );
  }

  return (
    <div className="rounded border border-zinc-700/40 bg-zinc-900/50 p-4">
      <div className="label text-zinc-500 mb-3">publish to wall of solves</div>
      <div className="space-y-3">
        <div>
          <div className="label text-zinc-600 mb-1">handle — no email, no account</div>
          <input
            type="text"
            maxLength={32}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="hacker42"
            className="w-full rounded border border-line bg-ink px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-700 focus:border-accent outline-none transition-colors"
          />
        </div>
        <div>
          <div className="label text-zinc-600 mb-1">winning payload</div>
          <textarea
            maxLength={1000}
            rows={3}
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            className="w-full rounded border border-line bg-ink px-3 py-1.5 code text-[11px] text-zinc-300 placeholder-zinc-700 focus:border-accent outline-none resize-none transition-colors"
          />
        </div>
        <button
          onClick={publish}
          disabled={!username.trim() || status === 'busy'}
          className="rounded bg-accent px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          {status === 'busy' ? 'Publishing…' : 'Publish →'}
        </button>
        {status === 'error' && <p className="text-xs text-rose-400">Failed to publish.</p>}
      </div>
    </div>
  );
}

// ---- Main overlay ---------------------------------------------------------

type Tab = 'trace' | 'defense' | 'writeup';

export default function SuccessOverlay({
  missionTitle, missionId, flag, writeup, defenseNote,
  solveCount, trace, traceLabels, sessionId, onClose,
}: {
  missionTitle: string;
  missionId: string;
  flag: string;
  writeup: string;
  defenseNote?: string | null;
  solveCount: number;
  trace?: TraceStep[] | null;
  traceLabels?: TraceLabels | null;
  sessionId: string;
  onClose: () => void;
}) {
  const defaultTab: Tab = trace?.length ? 'trace' : 'writeup';
  const [tab, setTab] = useState<Tab>(defaultTab);

  const trifecta    = traceLabels?.trifecta ?? [];
  const defaultPayload = trace ? extractPayload(trace, traceLabels ?? undefined) : '';

  const TAB_BASE   = 'px-4 py-2.5 label transition-colors border-b-2';
  const TAB_ACTIVE = 'border-accent text-accent';
  const TAB_IDLE   = 'border-transparent text-zinc-500 hover:text-zinc-300';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4">
      <div className="flex flex-col w-full max-w-3xl max-h-[92vh] rounded border border-zinc-700/60 bg-canvas shadow-2xl">

        {/* ---- Header ---- */}
        <div className="px-6 pt-6 pb-4 shrink-0">
          {/* Molntek accent bar pattern */}
          <div className="accent-bar">
            <div className="label text-accent mb-1">mission solved</div>
            <h2 className="font-display text-2xl font-bold text-zinc-100 leading-tight">
              {missionTitle}
            </h2>
            <p className="text-sm text-zinc-500 mt-0.5">solver #{solveCount}</p>
          </div>

          {/* Flag */}
          <div className="mt-4 rounded border border-zinc-700/40 bg-ink px-4 py-3">
            <div className="label text-zinc-600 mb-1.5">flag</div>
            <div className="code text-accent text-sm select-all">{flag}</div>
          </div>
        </div>

        {/* ---- Tabs ---- */}
        <div className="flex border-b border-line px-6 shrink-0">
          <button onClick={() => setTab('trace')}
            className={`${TAB_BASE} ${tab === 'trace' ? TAB_ACTIVE : TAB_IDLE}`}>
            How it worked
          </button>
          {defenseNote && (
            <button onClick={() => setTab('defense')}
              className={`${TAB_BASE} ${tab === 'defense' ? TAB_ACTIVE : TAB_IDLE}`}>
              The defense
            </button>
          )}
          <button onClick={() => setTab('writeup')}
            className={`${TAB_BASE} ${tab === 'writeup' ? TAB_ACTIVE : TAB_IDLE}`}>
            Full writeup
          </button>
        </div>

        {/* ---- Tab content ---- */}
        <div className="flex-1 overflow-y-auto px-6 py-5">

          {tab === 'trace' && (
            <div>
              {trifecta.length > 0 && <TrifectaBanner trifecta={trifecta} />}

              {!trace?.length ? (
                <p className="text-sm text-zinc-600">Trace unavailable (session may have expired).</p>
              ) : (
                <div className="space-y-2">
                  {trace.map((step, i) => (
                    <TraceStep key={i} step={step} labels={traceLabels ?? undefined} />
                  ))}
                </div>
              )}

              <div className="mt-6">
                <WallPublish missionId={missionId} sessionId={sessionId} defaultPayload={defaultPayload} />
              </div>
            </div>
          )}

          {tab === 'defense' && defenseNote && (
            <div className="prose prose-invert max-w-none text-sm">
              <ReactMarkdown>{defenseNote}</ReactMarkdown>
            </div>
          )}

          {tab === 'writeup' && (
            <div className="prose prose-invert max-w-none text-sm">
              <ReactMarkdown>{writeup}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* ---- Footer ---- */}
        <div className="border-t border-line px-6 py-3 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="rounded border border-zinc-700 bg-zinc-800/60 px-5 py-1.5 text-sm font-medium text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
