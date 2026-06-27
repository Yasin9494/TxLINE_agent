"use client";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import { Flag } from "@/components/Flag";
import { Empty, SectionTitle } from "@/components/RichText";
import { useStore } from "@/lib/store";

export default function TeamsPage() {
  return <Shell><TeamsInner /></Shell>;
}

function TeamsInner() {
  const { matches } = useStore();
  const names = Array.from(new Set(matches.flatMap((m) => [m.home_team, m.away_team]))).sort();
  if (!names.length) return <Empty icon="🌍" title="Teams load with the schedule…" />;
  return (
    <div className="rise">
      <SectionTitle>All teams</SectionTitle>
      <div className="grid gap-2.5 grid-cols-[repeat(auto-fill,minmax(150px,1fr))]">
        {names.map((n) => (
          <Link key={n} href={`/team?name=${encodeURIComponent(n)}`}
            className="flex items-center gap-2.5 rounded-2xl border border-line bg-card p-3.5">
            <Flag name={n} /><span className="text-[14px] font-semibold truncate">{n}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
