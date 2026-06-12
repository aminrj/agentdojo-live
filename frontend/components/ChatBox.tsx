'use client';

import { useEffect, useRef } from 'react';

export type ChatMsg = { role: 'user' | 'assistant'; content: string };

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-3 py-2">
      <span className="label text-zinc-600 mr-1">agent</span>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="thinking-dot inline-block w-1.5 h-1.5 rounded-full bg-accent"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}

export default function ChatBox({
  messages,
  onSend,
  disabled,
  agentName = 'agent',
  thinking = false,
}: {
  messages: ChatMsg[];
  onSend: (text: string) => void;
  disabled: boolean;
  agentName?: string;
  thinking?: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  const displayName = agentName.replace(/_/g, ' ');

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-line px-4 py-2.5 flex items-center justify-between">
        <span className="label text-zinc-500">conversation</span>
        <span className="label text-accent">{displayName}</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && !thinking && (
          <div className="text-sm text-zinc-600 leading-relaxed pt-2">
            Send a message to{' '}
            <span className="text-zinc-400">{displayName}</span>.
            Watch the tool calls appear on the right as the agent acts.
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
          >
            <div
              className={[
                'max-w-[85%] rounded px-3 py-2 text-sm whitespace-pre-wrap leading-relaxed',
                m.role === 'user'
                  ? 'bg-zinc-700/60 text-zinc-200'
                  : 'bg-canvas border border-line text-zinc-300',
              ].join(' ')}
            >
              <div className="label text-zinc-600 mb-1.5">
                {m.role === 'user' ? 'you' : displayName}
              </div>
              {m.content}
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex justify-start">
            <div className="bg-canvas border border-line rounded px-1 py-1">
              <ThinkingIndicator />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
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
          placeholder={disabled ? 'Agent is thinking…' : 'Send a message…'}
          className="flex-1 bg-ink border border-line rounded px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 outline-none focus:border-accent disabled:opacity-50 transition-colors"
        />
        <button
          type="submit"
          disabled={disabled}
          className="rounded bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          Send
        </button>
      </form>
    </div>
  );
}
