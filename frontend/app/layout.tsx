import './globals.css';
import type { Metadata } from 'next';
import localFont from 'next/font/local';

// Molntek brand fonts — Fraunces (display serif) + JetBrains Mono
const fraunces = localFont({
  src: [
    { path: '../public/Fraunces-Regular.woff2',  weight: '400', style: 'normal' },
    { path: '../public/Fraunces-SemiBold.woff2', weight: '600', style: 'normal' },
    { path: '../public/Fraunces-Bold.woff2',     weight: '700', style: 'normal' },
  ],
  variable: '--font-display',
  display: 'swap',
});

const jetbrainsMono = localFont({
  src: [
    { path: '../public/JetBrainsMono-Regular.woff2', weight: '400', style: 'normal' },
  ],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'agentdojo.live — practice attacking AI agents',
  description:
    'Free, open-source agentic attack playground. Pick a mission, attack a real LLM-backed agent, see the exact trace and the defense. Built by an OWASP MCP Top 10 author.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
