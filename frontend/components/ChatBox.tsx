'use client';

export type ChatMsg = { role: 'user' | 'assistant'; content: string };

export default function ChatBox({
  messages,
  onSend,
  disabled,
}: {
  messages: ChatMsg[];
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-zinc-500 text-sm">
            Send a message to DocuAssist. The agent has tools shown on the right.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === 'user'
                ? 'self-end max-w-[85%] ml-auto rounded-lg bg-zinc-700 px-3 py-2 text-sm whitespace-pre-wrap'
                : 'max-w-[85%] rounded-lg bg-canvas border border-line px-3 py-2 text-sm whitespace-pre-wrap'
            }
          >
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1">
              {m.role === 'user' ? 'you' : 'docuassist'}
            </div>
            {m.content}
          </div>
        ))}
      </div>
      <form
        className="border-t border-line p-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          const text = String(fd.get('msg') || '').trim();
          if (!text) return;
          onSend(text);
          (e.currentTarget as HTMLFormElement).reset();
        }}
      >
        <input
          name="msg"
          autoComplete="off"
          disabled={disabled}
          placeholder={disabled ? 'Agent is thinking…' : 'Type your message…'}
          className="flex-1 bg-ink border border-line rounded px-3 py-2 text-sm outline-none focus:border-accent disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled}
          className="rounded bg-accent px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </div>
  );
}
