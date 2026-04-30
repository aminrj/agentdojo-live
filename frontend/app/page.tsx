import Link from 'next/link';

type Mission = {
  id: string;
  title: string;
  summary: string;
  available_tools: string[];
  solve_count: number;
  difficulty?: 'easy' | 'medium' | 'hard' | string;
  threat_class?: string;
};

async function getMissions(): Promise<Mission[]> {
  try {
    const backend = process.env.BACKEND_URL || 'http://backend:8000';
    const r = await fetch(`${backend}/api/missions`, { cache: 'no-store' });
    if (!r.ok) return [];
    return r.json();
  } catch {
    return [];
  }
}

const DIFFICULTY_STYLES: Record<string, string> = {
  easy: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/40',
  medium: 'bg-amber-900/40 text-amber-300 border-amber-700/40',
  hard: 'bg-rose-900/40 text-rose-300 border-rose-700/40',
};

export default async function HomePage() {
  const missions = await getMissions();

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight">
        agentdojo<span className="text-accent">.live</span>
      </h1>
      <p className="mt-4 text-lg text-zinc-300">
        A free, hosted playground for practicing attacks on agentic LLM systems. Real local
        models. Real tool calls. Real exfiltration.
      </p>
      <p className="mt-2 text-sm text-zinc-500">
        Each mission is a small agent wired with realistic tools and a deliberate weakness
        from the OWASP LLM Top 10 (2025) or the broader agentic threat landscape.
      </p>

      <section className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2">
        {missions.length === 0 && (
          <div className="card p-6 text-zinc-400">
            Backend unreachable. Check that the API is up.
          </div>
        )}
        {missions.map((m, idx) => {
          const diffStyle =
            DIFFICULTY_STYLES[m.difficulty || 'easy'] || DIFFICULTY_STYLES.easy;
          const num = String(idx + 1).padStart(2, '0');
          return (
            <article key={m.id} className="card flex flex-col p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-widest text-zinc-500">
                    Mission {num}
                  </div>
                  <h2 className="mt-1 text-xl font-semibold">{m.title}</h2>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-2xl font-bold text-accent">{m.solve_count}</div>
                  <div className="text-[10px] uppercase tracking-widest text-zinc-500">
                    solves
                  </div>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <span
                  className={`rounded border px-2 py-0.5 text-xs font-medium ${diffStyle}`}
                >
                  {m.difficulty || 'easy'}
                </span>
                {m.threat_class && (
                  <span className="rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-300">
                    {m.threat_class}
                  </span>
                )}
              </div>

              <p className="mt-3 text-sm text-zinc-400">{m.summary}</p>

              {m.available_tools.length > 0 && (
                <div className="mt-3 text-xs text-zinc-500">
                  <span className="text-zinc-400">Tools:</span>{' '}
                  <code className="text-zinc-300">{m.available_tools.join(', ')}</code>
                </div>
              )}

              <div className="mt-auto pt-5">
                <Link
                  href={`/m/${m.id}`}
                  className="inline-block rounded bg-accent px-4 py-2 font-semibold text-ink hover:opacity-90"
                >
                  Start →
                </Link>
              </div>
            </article>
          );
        })}
      </section>

      <section className="mt-12 grid grid-cols-1 gap-4 text-sm text-zinc-400 md:grid-cols-3">
        <div className="card p-4">
          <div className="text-zinc-200 font-semibold">No signup</div>
          <div className="mt-1">Anonymous session in your browser. Nothing to install.</div>
        </div>
        <div className="card p-4">
          <div className="text-zinc-200 font-semibold">Real local LLM</div>
          <div className="mt-1">Backed by Ollama on the host. No third-party APIs.</div>
        </div>
        <div className="card p-4">
          <div className="text-zinc-200 font-semibold">Open-source</div>
          <div className="mt-1">MIT-licensed. Add your own missions in a single file.</div>
        </div>
      </section>

      <footer className="mt-16 text-xs text-zinc-600">
        Built by <a href="https://aminrj.com" className="underline">aminrj</a>. Source on
        GitHub. Licensed MIT.
      </footer>
    </main>
  );
}
