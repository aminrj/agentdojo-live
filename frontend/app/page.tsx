import Link from 'next/link';

type Mission = {
  id: string;
  title: string;
  summary: string;
  available_tools: string[];
  solve_count: number;
  difficulty?: string;
  threat_class?: string;
};

async function getMissions(): Promise<Mission[]> {
  try {
    const backend = process.env.BACKEND_URL || 'http://backend:8000';
    const r = await fetch(`${backend}/api/missions`, { cache: 'no-store' });
    if (!r.ok) return [];
    const all: Mission[] = await r.json();
    // v1: missions 01 and 04 only. 02 and 03 ship in v1.x.
    return all;
  } catch {
    return [];
  }
}

const DIFFICULTY_COLORS: Record<string, string> = {
  easy:   'text-emerald-400 border-emerald-800/60',
  medium: 'text-amber-400 border-amber-800/60',
  hard:   'text-rose-400 border-rose-800/60',
};

const MISSION_NUMBERS: Record<string, string> = {
  'mission-01': '01',
  'mission-02': '02',
  'mission-03': '03',
  'mission-04': '04',
};

export default async function HomePage() {
  const missions = await getMissions();

  return (
    <main className="mx-auto max-w-4xl px-6 py-16 md:py-20">

      {/* ---- Masthead ---- */}
      <header className="pb-8 border-b border-line">
        <div className="label text-zinc-500 mb-3">
          molntek · security research
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight text-zinc-100 leading-tight">
          agentdojo<span className="text-accent">.</span>live
        </h1>
        <p className="mt-3 text-base text-zinc-400 max-w-xl leading-relaxed">
          A free, open-source playground for practicing attacks on agentic LLM systems.
          Real tool calls. Real exfiltration. And after you win — the exact trace that explains why.
        </p>
      </header>

      {/* ---- Differentiator block — Molntek left-accent style ---- */}
      <section className="mt-8 accent-bar py-1">
        <p className="text-sm text-zinc-400 leading-relaxed">
          <span className="font-semibold text-zinc-200">Gandalf scores you.</span>{' '}
          agentdojo.live shows you the trace, explains why the attack worked, and lets you fork
          the mission. Three things Gandalf can&apos;t offer:
        </p>
        <ul className="mt-3 space-y-2 text-sm text-zinc-400">
          {[
            ['Open & self-hostable', 'Run it on your own GPU, inspect every line. MIT licensed.'],
            ['Teaches the why', 'Post-solve trace panel: exact injection token, step sequence, and the control that would have blocked it.'],
            ['MCP-native', 'Tool-description poisoning — the 2025-class attack. Authored by an OWASP MCP Top 10 contributor.'],
          ].map(([title, desc]) => (
            <li key={title} className="flex gap-3">
              <span className="text-accent mt-0.5 shrink-0">▸</span>
              <span>
                <span className="font-semibold text-zinc-200">{title}</span>
                {' — '}{desc}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* ---- Mission grid ---- */}
      <section className="mt-12">
        <div className="label text-zinc-500 mb-5">missions</div>

        {missions.length === 0 && (
          <div className="card p-6 text-zinc-500 text-sm">
            Backend unreachable — check that the API is up.
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {missions.map((m) => {
            const diffColor = DIFFICULTY_COLORS[m.difficulty ?? 'easy'] ?? DIFFICULTY_COLORS.easy;
            const num = MISSION_NUMBERS[m.id] ?? '??';
            return (
              <article key={m.id} className="card flex flex-col p-6 hover:border-zinc-600 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="label text-zinc-600 mb-1">Mission {num}</div>
                    <h2 className="font-display text-xl font-semibold text-zinc-100 leading-snug">
                      {m.title}
                    </h2>
                  </div>
                  <div className="text-right shrink-0 pt-1">
                    <div className="font-display text-2xl font-bold text-accent leading-none">
                      {m.solve_count}
                    </div>
                    <div className="label text-zinc-600 mt-0.5">solves</div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`rounded border px-2 py-0.5 label ${diffColor}`}>
                    {m.difficulty ?? 'easy'}
                  </span>
                  {m.threat_class && (
                    <span className="rounded border border-zinc-700/60 px-2 py-0.5 label text-zinc-400">
                      {m.threat_class}
                    </span>
                  )}
                </div>

                <p className="mt-3 text-sm text-zinc-400 leading-relaxed">{m.summary}</p>

                {m.available_tools.length > 0 && (
                  <div className="mt-3 code text-zinc-600 text-xs">
                    {m.available_tools.join('  ·  ')}
                  </div>
                )}

                <div className="mt-auto pt-5">
                  <Link
                    href={`/m/${m.id}`}
                    className="inline-flex items-center gap-2 rounded bg-accent px-5 py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
                  >
                    Begin mission <span aria-hidden>→</span>
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* ---- Feature bar ---- */}
      <section className="mt-12 grid grid-cols-1 gap-3 text-sm text-zinc-400 md:grid-cols-3">
        {[
          ['No signup', 'Anonymous session in your browser. Nothing to install or create.'],
          ['Real local LLM', 'Backed by Ollama on the host. One pinned model — payloads stay reproducible.'],
          ['Open-source', 'MIT licensed. Add your own missions in a single Python file.'],
        ].map(([title, desc]) => (
          <div key={title} className="card p-4">
            <div className="font-semibold text-zinc-200 mb-1">{title}</div>
            <div className="leading-relaxed">{desc}</div>
          </div>
        ))}
      </section>

      {/* ---- Footer ---- */}
      <footer className="mt-16 pt-6 border-t border-line flex items-center justify-between text-xs text-zinc-600">
        <div className="label">
          Built by{' '}
          <a href="https://molntek.com" className="text-zinc-400 hover:text-accent transition-colors">
            Molntek
          </a>
          {' · '}
          <a href="https://aminrj.com" className="text-zinc-400 hover:text-accent transition-colors">
            I teach this
          </a>
        </div>
        <div className="label text-zinc-700">MIT</div>
      </footer>
    </main>
  );
}
