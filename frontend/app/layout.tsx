import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'agentdojo.live — practice attacking AI agents in your browser',
  description:
    'Free, hosted, multi-agent attack playground. Land in your browser, pick a mission, attack a real LLM-backed agent.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
