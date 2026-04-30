'use client';

import ReactMarkdown from 'react-markdown';

export default function SuccessOverlay({
  flag,
  writeup,
  solveCount,
  onClose,
}: {
  flag: string;
  writeup: string;
  solveCount: number;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="card max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="text-xs uppercase tracking-widest text-accent">Mission solved</div>
        <h2 className="mt-1 text-2xl font-semibold">Silent Redirect — complete</h2>
        <div className="mt-3 text-sm text-zinc-400">
          You are solver #{solveCount}.
        </div>
        <div className="mt-4 card p-3">
          <div className="text-[10px] uppercase tracking-widest text-zinc-500">Flag</div>
          <div className="code mt-1 text-accent">{flag}</div>
        </div>
        <div className="prose prose-invert mt-6 max-w-none text-sm">
          <ReactMarkdown>{writeup}</ReactMarkdown>
        </div>
        <button
          onClick={onClose}
          className="mt-6 rounded bg-accent px-4 py-2 text-sm font-semibold text-ink"
        >
          Close
        </button>
      </div>
    </div>
  );
}
