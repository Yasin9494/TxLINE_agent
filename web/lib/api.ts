// Thin client for the FastAPI backend (served from the same origin at /api/v1).

export type Odds = { HOME?: number | null; DRAW?: number | null; AWAY?: number | null };
export type Match = {
  fixture_id: string; home_team: string; away_team: string;
  minute: number; home_goals: number; away_goals: number;
  status: "upcoming" | "live" | "finished"; start: number;
  competition: string | null; prices: Odds; favourite: string | null;
};
export type Pundit = {
  fixture_id: string; match: string; minute: number;
  kind: "goal" | "red_card" | "sharp_shift"; text: string; speech: string;
};
export type Account = {
  id: string; display: string; username: string | null;
  solana: string | null; solana_linked: boolean; telegram_linked: boolean;
  is_demo: boolean; favourites: number[];
};
export type LoginOut = { token: string; account: Account };

const BASE = "/api/v1";
export const tokenStore = {
  get: () => (typeof window === "undefined" ? null : localStorage.getItem("aip_token")),
  set: (t: string) => localStorage.setItem("aip_token", t),
  clear: () => { localStorage.removeItem("aip_token"); localStorage.removeItem("aip_account"); },
};

async function req<T>(path: string, opts: { method?: string; body?: unknown; auth?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const t = tokenStore.get();
  if (opts.auth !== false && t) headers["Authorization"] = `Bearer ${t}`;
  const r = await fetch(BASE + path, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw { status: r.status, data };
  return data as T;
}

export const api = {
  register: (username: string, password: string) =>
    req<LoginOut>("/auth/register", { method: "POST", body: { username, password }, auth: false }),
  login: (username: string, password: string) =>
    req<LoginOut>("/auth/login", { method: "POST", body: { username, password }, auth: false }),
  demo: () => req<LoginOut>("/auth/demo", { method: "POST", auth: false }),
  me: () => req<Account>("/auth/me"),
  nonce: (pubkey: string) => req<{ message: string }>(`/auth/nonce?pubkey=${pubkey}`, { auth: false }),
  solana: (pubkey: string, signature: string) =>
    req<LoginOut>("/auth/solana", { method: "POST", body: { pubkey, signature }, auth: false }),
  solanaLink: (pubkey: string, signature: string) =>
    req<Account>("/auth/solana/link", { method: "POST", body: { pubkey, signature } }),
  linkCode: () => req<{ code: string; deep_link: string }>("/auth/telegram/link-code", { method: "POST" }),
  matches: () => req<Match[]>("/matches", { auth: false }),
  match: (id: string) => req<Match>(`/matches/${id}`, { auth: false }),
  live: () => req<{ source: string; matches: Match[]; feed: Pundit[] }>("/live", { auth: false }),
  pundit: (fixtureId?: string) =>
    req<Pundit[]>(`/pundit${fixtureId ? `?fixture_id=${fixtureId}&limit=40` : ""}`, { auth: false }),
  addFav: (id: number) => req<Account>(`/me/favourites/${id}`, { method: "POST" }),
  delFav: (id: number) => req<Account>(`/me/favourites/${id}`, { method: "DELETE" }),
};

// ---- pure helpers ----
export function fairProbs(o: Odds): { HOME: number; DRAW: number; AWAY: number } | null {
  if (!o || !o.HOME) return null;
  const inv = { HOME: o.HOME ? 1 / o.HOME : 0, DRAW: o.DRAW ? 1 / o.DRAW : 0, AWAY: o.AWAY ? 1 / o.AWAY : 0 };
  const t = inv.HOME + inv.DRAW + inv.AWAY;
  if (!t) return null;
  return { HOME: inv.HOME / t, DRAW: inv.DRAW / t, AWAY: inv.AWAY / t };
}
export const teamName = (m: Match, s: "HOME" | "DRAW" | "AWAY") =>
  s === "HOME" ? m.home_team : s === "AWAY" ? m.away_team : "Draw";
export function kickoff(ms: number) {
  if (!ms) return "";
  const d = new Date(ms);
  return d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
export const statusRank: Record<string, number> = { live: 0, upcoming: 1, finished: 2 };
