"use client";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { MatchCard } from "@/components/MatchCard";
import { Empty } from "@/components/RichText";
import { useStore, isFav } from "@/lib/store";
import { statusRank, type Match } from "@/lib/api";

const TABS = [
  { k: "all", label: "All" },
  { k: "live", label: "🔴 Live" },
  { k: "upcoming", label: "Upcoming" },
  { k: "finished", label: "Finished" },
  { k: "fav", label: "★" },
] as const;

export default function MatchesPage() {
  return <Shell><MatchesInner /></Shell>;
}

function MatchesInner() {
  const { matches } = useStore();
  const [tab, setTab] = useState<string>("all");

  const counts: Record<string, number> = { all: matches.length, live: 0, upcoming: 0, finished: 0, fav: 0 };
  matches.forEach((m) => { counts[m.status] = (counts[m.status] || 0) + 1; if (isFav(m.fixture_id)) counts.fav++; });

  let list: Match[];
  if (tab === "all") list = [...matches].sort((a, b) => (statusRank[a.status] - statusRank[b.status]) || ((a.start || 0) - (b.start || 0)));
  else if (tab === "fav") list = matches.filter((m) => isFav(m.fixture_id));
  else list = matches.filter((m) => m.status === tab).sort((a, b) => (a.start || 0) - (b.start || 0));

  const emptyCopy: Record<string, [string, string, string]> = {
    live: ["🕒", "No matches in play right now.", "Check Upcoming for what’s next."],
    finished: ["📅", "No finished matches yet.", "They show here after full time."],
    fav: ["★", "You’re not following any matches.", "Tap ★ on a match to follow it."],
    all: ["⚽", "Loading…", ""],
  };

  return (
    <div className="rise">
      <div className="flex gap-2 overflow-x-auto mb-1">
        {TABS.map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)}
            className={`px-3.5 py-2 rounded-full border text-[13px] font-semibold whitespace-nowrap ${tab === t.k ? "bg-fg text-bg border-fg" : "bg-card text-muted border-line"}`}>
            {t.label}{counts[t.k] ? <span className="opacity-70 ml-1">{counts[t.k]}</span> : ""}
          </button>
        ))}
      </div>
      {list.length ? (
        <div className="grid gap-3 sm:grid-cols-2">{list.map((m) => <MatchCard key={m.fixture_id} m={m} />)}</div>
      ) : (
        <Empty icon={(emptyCopy[tab] || emptyCopy.all)[0]} title={(emptyCopy[tab] || emptyCopy.all)[1]} sub={(emptyCopy[tab] || emptyCopy.all)[2]} />
      )}
    </div>
  );
}
