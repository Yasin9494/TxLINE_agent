"use client";
// Tiny shared client store: polls the API, caches to localStorage for instant paint,
// and exposes account + voice state. Shared across pages via useSyncExternalStore.
import { useSyncExternalStore } from "react";
import { api, tokenStore, type Account, type Match, type Pundit } from "./api";

type State = {
  matches: Match[];
  feed: Pundit[];
  account: Account | null;
  source: string;
  ready: boolean;
  voiceOn: boolean;
};

let state: State = { matches: [], feed: [], account: null, source: "", ready: false, voiceOn: false };
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());
const set = (p: Partial<State>) => { state = { ...state, ...p }; emit(); };

function hydrate() {
  if (typeof window === "undefined") return;
  try {
    const m = JSON.parse(localStorage.getItem("aip_m") || "null");
    const a = JSON.parse(localStorage.getItem("aip_account") || "null");
    state = { ...state, matches: m?.d ?? [], account: a ?? null };
  } catch {}
}

const spoken = new Set<string>();
let primed = false;
let polling = false;

export async function refresh() {
  try {
    const matches = await api.matches();
    localStorage.setItem("aip_m", JSON.stringify({ t: Date.now(), d: matches }));
    set({ matches, ready: true });
  } catch {}
  try {
    const live = await api.live();
    const fresh: Pundit[] = [];
    for (const x of live.feed) {
      const k = `${x.fixture_id}|${x.minute}|${x.kind}|${x.text}`;
      if (!spoken.has(k)) { spoken.add(k); fresh.push(x); }
    }
    if (primed && state.voiceOn) fresh.reverse().forEach((x) => speak(x.speech));
    primed = true;
    set({ feed: live.feed, source: live.source });
  } catch {}
}

export function startPolling() {
  if (polling) return;
  polling = true;
  hydrate();
  refresh();
  setInterval(() => { if (!document.hidden && tokenStore.get()) refresh(); }, 6000);
}

export function setAccount(a: Account | null) {
  if (a) localStorage.setItem("aip_account", JSON.stringify(a));
  set({ account: a });
}
export async function toggleFav(id: string) {
  const fav = (state.account?.favourites || []).map(String).includes(String(id));
  try {
    const acc = fav ? await api.delFav(Number(id)) : await api.addFav(Number(id));
    setAccount(acc);
  } catch {}
}
export const isFav = (id: string) =>
  !!state.account && (state.account.favourites || []).map(String).includes(String(id));

// ---- voice ----
let voices: SpeechSynthesisVoice[] = [];
function loadVoices() { try { voices = speechSynthesis.getVoices() || []; } catch {} }
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  loadVoices();
  speechSynthesis.onvoiceschanged = loadVoices;
}
export function speak(t: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  try {
    if (!voices.length) loadVoices();
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(t);
    const v = voices.find((v) => /en[-_]?(us|gb)/i.test(v.lang)) || voices.find((v) => /^en/i.test(v.lang));
    if (v) u.voice = v;
    u.lang = v?.lang || "en-US"; u.rate = 1.03;
    speechSynthesis.speak(u);
  } catch {}
}
export function toggleVoice() {
  const on = !state.voiceOn;
  set({ voiceOn: on });
  if (on) speak("AI Pundit voice is on. I will read out goals, cards and sharp money.");
}

export function useStore(): State {
  return useSyncExternalStore(
    (l) => { listeners.add(l); return () => listeners.delete(l); },
    () => state,
    () => state,
  );
}
