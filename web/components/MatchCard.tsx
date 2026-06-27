"use client";
import { useRouter } from "next/navigation";
import { Star } from "lucide-react";
import { fairProbs, kickoff, type Match } from "@/lib/api";
import { isFav, toggleFav, useStore } from "@/lib/store";
import { Flag } from "./Flag";

const first = (n: string) => (n || "").split(" ")[0];

export function MatchCard({ m }: { m: Match }) {
  const router = useRouter();
  useStore(); // re-render on favourite changes
  const fp = fairProbs(m.prices);
  const fav = isFav(m.fixture_id);
  const cols = { HOME: "var(--color-accent)", DRAW: "var(--color-muted)", AWAY: "var(--color-brandblue)" };

  return (
    <button
      onClick={() => router.push(`/match?id=${m.fixture_id}`)}
      className="text-left w-full rounded-2xl border border-line bg-gradient-to-b from-card to-card2 p-4 shadow-lg active:scale-[.99] transition rise"
    >
      <div className="flex items-center justify-between mb-2.5 text-[11px] text-muted">
        <span>{m.competition || "World Cup"}</span>
        <span className="flex items-center gap-2">
          {m.status === "live" ? (
            <span className="rounded-full bg-danger/15 text-danger px-2 py-0.5 text-[10.5px] font-extrabold uppercase tracking-wide">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-danger mr-1 pulse-dot" />LIVE {m.minute}&apos;
            </span>
          ) : m.status === "finished" ? (
            <span className="rounded-full bg-muted/15 text-muted px-2 py-0.5 text-[10.5px] font-extrabold uppercase">Full time</span>
          ) : (
            <span className="rounded-full bg-brandblue/15 text-brandblue px-2 py-0.5 text-[10.5px] font-extrabold uppercase">Upcoming</span>
          )}
          <span
            onClick={(e) => { e.stopPropagation(); toggleFav(m.fixture_id); }}
            className={fav ? "text-gold" : "text-[#3a445c]"}
          >
            <Star size={17} fill={fav ? "currentColor" : "none"} />
          </span>
        </span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <Flag name={m.home_team} />
          <span className="font-semibold text-[15px] truncate">{m.home_team}</span>
        </div>
        <div className="text-center min-w-[56px]">
          {m.status === "upcoming" ? (
            <>
              <div className="text-xs text-muted font-bold">VS</div>
              <div className="text-[11px] text-muted mt-0.5">{kickoff(m.start) || "TBD"}</div>
            </>
          ) : (
            <div className="text-[22px] font-extrabold tabular-nums">{m.home_goals}–{m.away_goals}</div>
          )}
        </div>
        <div className="flex items-center gap-2.5 min-w-0 justify-end">
          <span className="font-semibold text-[15px] truncate">{m.away_team}</span>
          <Flag name={m.away_team} />
        </div>
      </div>

      {fp ? (
        <>
          <div className="flex h-2 rounded-md overflow-hidden mt-3.5 bg-bg2">
            {(["HOME", "DRAW", "AWAY"] as const).map((s) => (
              <span key={s} style={{ width: `${(fp[s] * 100).toFixed(1)}%`, background: cols[s] }} />
            ))}
          </div>
          <div className="flex justify-between mt-1.5 text-[11px] text-muted">
            <span><b className="text-fg">{Math.round(fp.HOME * 100)}%</b> {first(m.home_team)}</span>
            <span><b className="text-fg">{Math.round(fp.DRAW * 100)}%</b> Draw</span>
            <span>{first(m.away_team)} <b className="text-fg">{Math.round(fp.AWAY * 100)}%</b></span>
          </div>
        </>
      ) : (
        <div className="mt-3 text-[11px] text-muted">Win-chances open closer to kick-off</div>
      )}
    </button>
  );
}
