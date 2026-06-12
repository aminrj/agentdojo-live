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
      {/* Header: available tool list */}
      <div className="border-b border-line px-4 py-2.5">
        <div className="label text-zinc-500 mb-2">available tools</div>
        <div className="flex flex-wrap gap-1.5">
          {availableTools.map((t) => (
            <span
              key={t}
              className="code rounded border border-line bg-ink px-2 py-0.5 text-zinc-400 text-[11px]"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Event feed */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        {events.length === 0 && (
          <div className="text-sm text-zinc-600 pt-2">
            Tool calls appear here as the agent acts.
          </div>
        )}

        {events.map((e, i) =>
          e.kind === 'call' ? (
            <div key={i} className="rounded border border-line bg-canvas p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="label text-accent">call</span>
                <code className="code text-zinc-200 text-[11px]">{e.name}()</code>
              </div>
              <pre className="code text-zinc-500 text-[11px] whitespace-pre-wrap break-all leading-relaxed">
                {JSON.stringify(e.arguments, null, 2)}
              </pre>
            </div>
          ) : (
            <div key={i} className="rounded border border-zinc-800/60 bg-ink p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="label text-zinc-500">result</span>
                <code className="code text-zinc-400 text-[11px]">{e.name}</code>
              </div>
              <pre className="code text-zinc-500 text-[11px] whitespace-pre-wrap break-all leading-relaxed">
                {e.content}
              </pre>
            </div>
          )
        )}
      </div>
    </div>
  );
}
