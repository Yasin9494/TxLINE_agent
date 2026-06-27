"use client";
import { Volume2 } from "lucide-react";
import { speak } from "@/lib/store";
import type { Pundit } from "@/lib/api";

const border = {
  goal: "border-l-accent", red_card: "border-l-danger", sharp_shift: "border-l-brandblue",
} as const;

function bold(text: string) {
  const parts = text.split(/\*(.+?)\*/g);
  return parts.map((p, i) => (i % 2 ? <b key={i}>{p}</b> : <span key={i}>{p}</span>));
}

export function PunditMsg({ x, showMatch = false }: { x: Pundit; showMatch?: boolean }) {
  return (
    <div className={`bg-card border border-line border-l-[3px] ${border[x.kind]} rounded-xl px-3.5 py-3 mb-2.5`}>
      <div className="flex items-center gap-2 text-[11px] text-muted mb-1">
        <span>{showMatch ? `${x.match} · ` : ""}{x.minute > 0 ? `${x.minute}'` : "pre-match"}</span>
        <button
          onClick={() => speak(x.speech)}
          className="flex items-center gap-1 rounded-full border border-line bg-bg2 text-brandblue px-2 py-0.5 text-[11px]"
        >
          <Volume2 size={12} /> listen
        </button>
      </div>
      <div className="text-[14px] leading-snug">{bold(x.text)}</div>
    </div>
  );
}
