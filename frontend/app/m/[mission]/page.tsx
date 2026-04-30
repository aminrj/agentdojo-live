import { notFound } from 'next/navigation';
import MissionClient from './MissionClient';

async function getMission(id: string) {
  const backend = process.env.BACKEND_URL || 'http://backend:8000';
  const r = await fetch(`${backend}/api/missions/${id}`, { cache: 'no-store' });
  if (!r.ok) return null;
  return r.json();
}

export default async function MissionPage({
  params,
}: {
  params: { mission: string };
}) {
  const mission = await getMission(params.mission);
  if (!mission) notFound();
  return <MissionClient mission={mission} />;
}
