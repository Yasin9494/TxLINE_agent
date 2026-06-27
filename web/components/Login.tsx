"use client";
import { useState } from "react";
import { Zap, Wallet } from "lucide-react";
import { api, tokenStore } from "@/lib/api";
import { setAccount } from "@/lib/store";

export function Login({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");

  function done(res: { token: string; account: import("@/lib/api").Account }) {
    tokenStore.set(res.token); setAccount(res.account); onDone();
  }
  async function submit() {
    setErr("");
    try {
      done(await (mode === "login" ? api.login(u, p) : api.register(u, p)));
    } catch (e) {
      const d = (e as { data?: { detail?: string } })?.data?.detail;
      setErr(typeof d === "string" ? d : "Failed — check your details");
    }
  }
  async function demo() { try { done(await api.demo()); } catch {} }
  async function wallet() {
    const prov = (window as unknown as { solana?: { isPhantom?: boolean; connect: () => Promise<{ publicKey: { toString: () => string } }>; signMessage: (m: Uint8Array, e: string) => Promise<{ signature: Uint8Array }> } }).solana;
    if (!prov?.isPhantom) { alert("Install a Solana wallet (e.g. Phantom)."); return; }
    try {
      const res = await prov.connect();
      const pubkey = res.publicKey.toString();
      const { message } = await api.nonce(pubkey);
      const signed = await prov.signMessage(new TextEncoder().encode(message), "utf8");
      const sig = btoa(String.fromCharCode(...signed.signature));
      done(await api.solana(pubkey, sig));
    } catch (e) { console.error(e); }
  }

  const inp = "w-full rounded-xl border border-line bg-bg2 px-3.5 py-3 text-[15px] outline-none focus:border-accent";
  const btn = "w-full rounded-xl border border-line bg-bg2 px-3.5 py-3 text-[15px] font-medium active:scale-[.985] transition";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="text-6xl drop-shadow-[0_6px_18px_rgba(52,211,153,.33)]">⚽</div>
      <h1 className="text-3xl font-bold mt-3.5 tracking-tight">AI Pundit</h1>
      <p className="text-muted text-center text-sm mt-1 mb-5 leading-relaxed">
        The whole World Cup in one place — live scores, the odds as win-chances,<br />
        and an AI pundit that reads the market for you.
      </p>
      <div className="w-full max-w-[360px] rounded-3xl border border-line bg-gradient-to-b from-card to-bg2 p-4.5 shadow-2xl flex flex-col gap-2.5">
        <input className={inp} placeholder="Username" value={u} onChange={(e) => setU(e.target.value)} />
        <input className={inp} type="password" placeholder="Password" value={p} onChange={(e) => setP(e.target.value)} />
        <div className="text-danger text-[13px] text-center min-h-4">{err}</div>
        <button onClick={submit} className="w-full rounded-xl bg-gradient-to-b from-accent to-accent2 text-[#04160c] font-bold px-3.5 py-3 active:scale-[.985] transition">
          {mode === "login" ? "Log in" : "Create account"}
        </button>
        <div className="text-muted text-[13px] text-center">
          {mode === "login" ? "New here? " : "Have an account? "}
          <span className="text-accent font-semibold cursor-pointer" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Create account" : "Log in"}
          </span>
        </div>
        <div className="flex items-center gap-2.5 text-muted text-xs my-0.5 before:content-[''] before:flex-1 before:h-px before:bg-line after:content-[''] after:flex-1 after:h-px after:bg-line">or</div>
        <button onClick={demo} className={btn}><span className="inline-flex items-center gap-2 justify-center w-full"><Zap size={16} /> Explore as guest</span></button>
        <button onClick={wallet} className="w-full text-muted text-[13px] py-2"><span className="inline-flex items-center gap-2 justify-center"><Wallet size={14} /> Continue with Solana wallet</span></button>
      </div>
    </div>
  );
}
