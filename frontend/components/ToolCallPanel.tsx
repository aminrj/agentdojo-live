'use client';

export type ToolEvent =
  | { kind: 'call'; id: string; name: string; arguments: Record<string, unknown> }
  | { kind: 'result'; id: string; name: string; content: string };

export default function ToolCallPanel({
  events,
  availableTools,
}: {
  events: ToolEvent[];
  availableTools: string[];
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-line p-3">
        <div className="text-xs uppercase tracking-widest text-zinc-500">
          Agent tools
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {availableTools.map((t) => (
            <span key={t} className="rounded bg-ink border border-line px-2 py-1 code text-zinc-300">
              {t}
            </span>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {events.length === 0 && (
          <div className="text-zinc-500 text-sm">
            Tool calls and results will appear here as the agent acts.
          </div>
        )}
        {events.map((e, i) =>
          e.kind === 'call' ? (
            <div key={i} className="card p-2">
              <div className="text-[10px] uppercase tracking-widest text-accent">tool call</div>
              <div className="code mt-1">
                {e.name}({JSON.stringify(e.arguments)})
              </div>
            </div>
          ) : (
            <div key={i} className="card p-2 border-zinc-700">
              <div className="text-[10px] uppercase tracking-widest text-zinc-400">
                tool result · {e.name}
              </div>
              <pre className="code mt-1 whitespace-pre-wrap text-zinc-300">{e.content}</pre>
            </div>
          )
        )}
      </div>
    </div>
  );
}
