"use client";
import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Shell } from "@/components/Shell";
import { MatchCard } from "@/components/MatchCard";
import { Flag } from "@/components/Flag";
import { Empty, SectionTitle } from "@/components/RichText";
import { useStore } from "@/lib/store";
import { useQuery } from "@/lib/useQuery";
import { statusRank } from "@/lib/api";

export default function TeamPage() {
  return <Shell><TeamInner /></Shell>;
}

function TeamInner() {
  const router = useRouter();
  const { matches } = useStore();
  const name = useQuery("name") || "";
  if (!name) return <Empty icon="🌍" title="Loading team…" />;
  const ms = matches
    .filter((m) => m.home_team === name || m.away_team === name)
    .sort((a, b) => (statusRank[a.status] - statusRank[b.status]) || ((a.start || 0) - (b.start || 0)));

  return (
    <div className="rise">
      <button onClick={() => router.push("/teams")} className="mb-3 inline-flex items-center gap-1 rounded-xl border border-line bg-card px-3 py-2 text-[14px]">
        <ChevronLeft size={16} /> Teams
      </button>
      <div className="flex flex-col items-center gap-3 py-4">
        <Flag name={name} size="lg" />
        <div className="text-xl font-bold">{name}</div>
      </div>
      <SectionTitle>Fixtures</SectionTitle>
      {ms.length ? <div className="grid gap-3 sm:grid-cols-2">{ms.map((m) => <MatchCard key={m.fixture_id} m={m} />)}</div>
        : <Empty icon="📅" title="No fixtures found." />}
    </div>
  );
}
