"use client";
import { Sparkles } from "lucide-react";
import { Shell } from "@/components/Shell";
import { PunditMsg } from "@/components/PunditMsg";
import { Empty, SectionTitle } from "@/components/RichText";
import { useStore } from "@/lib/store";

export default function InsightsPage() {
  return <Shell><InsightsInner /></Shell>;
}

function InsightsInner() {
  const { feed } = useStore();
  return (
    <div className="rise">
      <div className="rounded-3xl border border-line bg-gradient-to-br from-[#12351f] to-bg2 p-5 shadow-xl">
        <h1 className="text-[22px] font-bold tracking-tight mb-1.5 flex items-center gap-2"><Sparkles size={20} /> AI Insights</h1>
        <p className="text-[#b8c6d8] text-[13.5px] leading-relaxed">
          Real-time reads on the market — goals, cards and <b>sharp money</b> (big moves in the odds
          before anything happens on the pitch).
        </p>
      </div>
      {feed.length ? (
        <>
          <SectionTitle>Live feed</SectionTitle>
          {feed.map((x, i) => <PunditMsg key={i} x={x} showMatch />)}
        </>
      ) : (
        <Empty icon="🔮" title="No AI calls yet." sub="I flag goals, red cards and sharp-money moves as they happen — live." />
      )}
    </div>
  );
}
