"use client";
import { useRouter } from "next/navigation";
import { ChevronLeft, Star } from "lucide-react";
import { Shell } from "@/components/Shell";
import { Flag } from "@/components/Flag";
import { PunditMsg } from "@/components/PunditMsg";
import { Empty, SectionTitle } from "@/components/RichText";
import { useStore, isFav, toggleFav } from "@/lib/store";
import { useQuery } from "@/lib/useQuery";
import { fairProbs, kickoff, teamName } from "@/lib/api";

export default function MatchPage() {
  return <Shell><MatchInner /></Shell>;
}

function MatchInner() {
  const router = useRouter();
  const { matches, feed } = useStore();
  const id = useQuery("id") || "";
  const m = matches.find((x) => String(x.fixture_id) === String(id));
  if (!m) return <Empty icon="⚽" title="Loading match…" />;

  const fp = fairProbs(m.prices);
  const cols = { HOME: "var(--color-accent)", DRAW: "var(--color-muted)", AWAY: "var(--color-brandblue)" } as const;
  const msgs = feed.filter((x) => String(x.fixture_id) === String(id));
  const fav = isFav(id);

  return (
    <div className="rise">
      <button onClick={() => router.push("/matches")} className="mb-2 inline-flex items-center gap-1 rounded-xl border border-line bg-card px-3 py-2 text-[14px]">
        <ChevronLeft size={16} /> Matches
      </button>
      <div className="text-center text-[11px] text-muted">{m.competition || "World Cup"}</div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-5">
        <div className="flex flex-col items-center gap-2"><Flag name={m.home_team} size="lg" /><span className="text-[15px] text-center">{m.home_team}</span></div>
        <div className="text-center">
          <div className="text-[40px] font-black tabular-nums">{m.status === "upcoming" ? "vs" : `${m.home_goals} – ${m.away_goals}`}</div>
          <div className="mt-2">
            {m.status === "live" ? <Badge tone="live"><span className="inline-block w-1.5 h-1.5 rounded-full bg-danger mr-1 pulse-dot" />LIVE {m.minute}&apos;</Badge>
              : m.status === "finished" ? <Badge tone="ft">Full time</Badge> : <Badge tone="up">{kickoff(m.start) || "Upcoming"}</Badge>}
          </div>
        </div>
        <div className="flex flex-col items-center gap-2"><Flag name={m.away_team} size="lg" /><span className="text-[15px] text-center">{m.away_team}</span></div>
      </div>

      <SectionTitle>What the market thinks</SectionTitle>
      {fp ? (
        <div className="flex flex-col gap-2.5">
          {(["HOME", "DRAW", "AWAY"] as const).map((s) => (
            <div key={s} className="flex items-center gap-2.5 text-[13px]">
              <span className="w-24 font-semibold truncate">{teamName(m, s)}</span>
              <div className="flex-1 h-2.5 rounded-md bg-bg2 overflow-hidden">
                <div className="h-full rounded-md" style={{ width: `${Math.round(fp[s] * 100)}%`, background: cols[s] }} />
              </div>
              <span className="w-[70px] text-right text-muted tabular-nums">{Math.round(fp[s] * 100)}% · {m.prices[s] ? m.prices[s]!.toFixed(2) : "-"}</span>
            </div>
          ))}
        </div>
      ) : <Empty icon="📈" title="Win-chances open closer to kick-off." />}

      <button onClick={() => toggleFav(id)}
        className={`mt-4 w-full rounded-xl py-3 font-semibold flex items-center justify-center gap-2 ${fav ? "border border-line bg-card" : "bg-gradient-to-b from-accent to-accent2 text-[#04160c]"}`}>
        <Star size={16} fill={fav ? "currentColor" : "none"} />{fav ? "Following" : "Follow this match"}
      </button>

      <SectionTitle>AI Pundit</SectionTitle>
      {msgs.length ? msgs.map((x, i) => <PunditMsg key={i} x={x} />)
        : <Empty icon="🎙️" title="No commentary yet" sub="I’ll narrate goals, cards & sharp money live." />}
    </div>
  );
}

function Badge({ tone, children }: { tone: "live" | "ft" | "up"; children: React.ReactNode }) {
  const cls = tone === "live" ? "bg-danger/15 text-danger" : tone === "ft" ? "bg-muted/15 text-muted" : "bg-brandblue/15 text-brandblue";
  return <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-extrabold uppercase tracking-wide ${cls}`}>{children}</span>;
}
