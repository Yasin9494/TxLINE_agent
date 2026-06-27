"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Home, Trophy, Globe2, Sparkles, User, Volume2, VolumeX, MessageCircle, Wallet, LogOut, X } from "lucide-react";
import { api, tokenStore } from "@/lib/api";
import { setAccount, startPolling, toggleVoice, useStore } from "@/lib/store";
import { Login } from "./Login";

const NAV = [
  { href: "/", label: "Home", Icon: Home },
  { href: "/matches", label: "Matches", Icon: Trophy },
  { href: "/teams", label: "Teams", Icon: Globe2 },
  { href: "/insights", label: "Insights", Icon: Sparkles },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [sheet, setSheet] = useState(false);
  const { account, voiceOn } = useStore();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const has = !!tokenStore.get();
    setAuthed(has);
    if (has) startPolling();
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);

  if (authed === null) return null;
  if (!authed) return <Login onDone={() => { setAuthed(true); startPolling(); }} />;

  const active = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <div>
      <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-md" style={{ paddingTop: "env(safe-area-inset-top)" }}>
        <div className="mx-auto max-w-[1080px] flex items-center gap-3 px-4 py-2.5 flex-wrap">
          <Link href="/" className="font-extrabold text-[17px] tracking-tight flex items-center gap-2 whitespace-nowrap">
            <span className="w-[7px] h-[7px] rounded-full bg-accent shadow-[0_0_0_3px_rgba(52,211,153,.2)]" />AI Pundit
          </Link>
          <nav className="flex gap-1 flex-1 overflow-x-auto order-3 w-full mt-0.5 sm:order-none sm:w-auto sm:mt-0">
            {NAV.map(({ href, label, Icon }) => (
              <Link key={href} href={href}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[14px] font-semibold whitespace-nowrap ${active(href) ? "bg-card text-fg" : "text-muted"}`}>
                <Icon size={16} /><span>{label}</span>
              </Link>
            ))}
          </nav>
          <div className="flex gap-2 ml-auto">
            <button onClick={toggleVoice} title="Voice"
              className={`w-[38px] h-[38px] rounded-full border grid place-items-center ${voiceOn ? "border-gold text-gold" : "border-line text-fg"} bg-card`}>
              {voiceOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            <button onClick={() => setSheet(true)} title="Account"
              className="w-[38px] h-[38px] rounded-full border border-line bg-card grid place-items-center">
              <User size={16} />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1080px] px-4 pt-4 pb-16">{children}</main>

      {sheet && account && (
        <div className="fixed inset-0 z-40 bg-black/55 flex items-end" onClick={() => setSheet(false)}>
          <div className="w-full max-w-[520px] mx-auto rounded-t-3xl bg-card p-5 flex flex-col gap-3" onClick={(e) => e.stopPropagation()}
            style={{ paddingBottom: "calc(1.25rem + env(safe-area-inset-bottom))" }}>
            <div className="flex items-center justify-between">
              <div className="text-lg font-extrabold">{account.display}</div>
              <button onClick={() => setSheet(false)}><X size={20} className="text-muted" /></button>
            </div>
            <div className="text-muted text-[13px] -mt-2">{account.is_demo ? "Guest session" : account.username ? `@${account.username}` : ""}</div>
            <SheetButtons />
            <button onClick={() => { tokenStore.clear(); setAccount(null); setAuthed(false); router.push("/"); }}
              className="rounded-xl border border-line py-3 text-danger flex items-center justify-center gap-2"><LogOut size={16} /> Log out</button>
          </div>
        </div>
      )}
    </div>
  );
}

function SheetButtons() {
  const { account } = useStore();
  const [tg, setTg] = useState<{ code: string; deep_link: string } | null>(null);
  async function linkTelegram() { try { setTg(await api.linkCode()); } catch { alert("Please log in first"); } }
  async function linkWallet() {
    const prov = (window as unknown as { solana?: { isPhantom?: boolean; connect: () => Promise<{ publicKey: { toString: () => string } }>; signMessage: (m: Uint8Array, e: string) => Promise<{ signature: Uint8Array }> } }).solana;
    if (!prov?.isPhantom) { alert("Install a Solana wallet (e.g. Phantom)."); return; }
    try {
      const res = await prov.connect(); const pubkey = res.publicKey.toString();
      const { message } = await api.nonce(pubkey);
      const signed = await prov.signMessage(new TextEncoder().encode(message), "utf8");
      const sig = btoa(String.fromCharCode(...signed.signature));
      setAccount(await api.solanaLink(pubkey, sig)); alert("Wallet linked ✓");
    } catch (e) { console.error(e); }
  }
  const btn = "rounded-xl border border-line bg-bg2 py-3 flex items-center justify-center gap-2 text-[15px]";
  if (tg) return (
    <div className="flex flex-col gap-2">
      <div className="text-muted text-[13px]">Open the bot — it links automatically. Or send this code: <b className="text-fg">{tg.code}</b></div>
      <a href={tg.deep_link} target="_blank" className="rounded-xl bg-gradient-to-b from-accent to-accent2 text-[#04160c] font-bold py-3 text-center">Open Telegram bot</a>
    </div>
  );
  return (
    <>
      <button className={btn} onClick={linkTelegram}><MessageCircle size={16} />{account?.telegram_linked ? "Telegram linked ✓" : "Link Telegram for alerts"}</button>
      <button className={btn} onClick={linkWallet}><Wallet size={16} />{account?.solana_linked ? "Wallet linked ✓" : "Link Solana wallet (optional)"}</button>
    </>
  );
}
