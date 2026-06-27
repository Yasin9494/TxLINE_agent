"use client";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Shell } from "@/components/Shell";
import { MatchCard } from "@/components/MatchCard";
import { RichText, SectionTitle } from "@/components/RichText";
import { useStore } from "@/lib/store";
import { fairProbs, statusRank, teamName } from "@/lib/api";

export default function HomePage() {
  return <Shell><HomeInner /></Shell>;
}

function HomeInner() {
  const { matches, feed, account } = useStore();
  const next = [...matches]
    .filter((m) => m.status !== "finished")
    .sort((a, b) => (statusRank[a.status] - statusRank[b.status]) || ((a.start || 0) - (b.start || 0)))
    .slice(0, 4);

  let insight: React.ReactNode;
  if (feed.length) {
    insight = <><Kicker>AI Insight · live</Kicker><div><RichText text={feed[0].text} /></div></>;
  } else {
    const best = matches
      .map((m) => ({ m, fp: fairProbs(m.prices) }))
      .filter((o) => o.fp)
      .sort((a, b) => Math.max(b.fp!.HOME, b.fp!.AWAY) - Math.max(a.fp!.HOME, a.fp!.AWAY))[0];
    if (best) {
      const s = best.fp!.HOME > best.fp!.AWAY ? "HOME" : "AWAY";
      insight = <><Kicker>AI Insight</Kicker><div>The market&apos;s strongest pick right now: <b>{teamName(best.m, s)}</b> at ~{Math.round(Math.max(best.fp!.HOME, best.fp!.AWAY) * 100)}% to beat {teamName(best.m, s === "HOME" ? "AWAY" : "HOME")}.</div></>;
    } else {
      insight = <><Kicker>AI Insight</Kicker><div>Win-chances arrive as the odds open. I&apos;ll flag every sharp move live.</div></>;
    }
  }

  return (
    <div className="rise">
      <div className="rounded-3xl border border-line bg-gradient-to-br from-[#12351f] to-bg2 p-5 shadow-xl">
        <h1 className="text-[22px] font-bold tracking-tight mb-1.5">
          👋 {account && !account.is_demo ? `Welcome, ${account.display}` : "Welcome to AI Pundit"}
        </h1>
        <p className="text-[#b8c6d8] text-[13.5px] leading-relaxed">
          Your World Cup companion. See the market&apos;s <b>win-chances</b>, get AI alerts on goals,
          red cards and <b>sharp money</b> — across all 104 games.
        </p>
      </div>

      <div className="mt-3 rounded-2xl border border-line border-l-[3px] border-l-brandblue bg-card px-4 py-3.5">
        {insight}
      </div>

      <SectionTitle>Next up</SectionTitle>
      <div className="grid gap-3 sm:grid-cols-2">
        {next.length ? next.map((m) => <MatchCard key={m.fixture_id} m={m} />)
          : <div className="text-muted text-center py-8">Schedule loading…</div>}
      </div>

      <div className="text-center mt-4">
        <Link href="/matches" className="inline-block rounded-xl border border-line bg-card px-4 py-3 text-[15px]">See all matches →</Link>
      </div>
    </div>
  );
}

function Kicker({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-brandblue font-extrabold mb-1.5"><Sparkles size={13} />{children}</div>;
}
