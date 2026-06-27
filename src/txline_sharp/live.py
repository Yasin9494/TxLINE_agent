"""Live TxLINE adapter: real World Cup feed -> pundit engine + dashboard store.

Replaces the simulator with the real thing once a TXLINE_API_TOKEN is present.
Three confirmed pieces of the TxLINE API are used:

  GET /api/fixtures/snapshot          -> map FixtureId -> team names (CompetitionId 72 = World Cup)
  GET /api/odds/stream    (SSE)       -> live 1X2 demargined prices  (Bookmaker "TXLineStablePriceDemargined")
  GET /api/scores/stream  (SSE)       -> live goals / cards          (during in-running matches)

Headers for data calls: Authorization: Bearer <jwt>  +  X-Api-Token: <apiToken>.

Odds events (shape confirmed live):
  { FixtureId, Ts, Bookmaker, SuperOddsType:"1X2_PARTICIPANT_RESULT",
    PriceNames:["part1","draw","part2"], Prices:[1985,3284,5219] }   # decimal odds x1000
"""
from __future__ import annotations

import threading

import httpx

from .auth import Session, start_guest_session
from .config import CONFIG
from .events import LiveFrame, PunditEngine
from .stream import stream

WC_COMPETITION_ID = 72
DEMARGINED = "TXLineStablePriceDemargined"
ONEX2 = "1X2_PARTICIPANT_RESULT"


def build_session() -> Session:
    s = start_guest_session(CONFIG.base_url)
    s.api_token = CONFIG.api_token
    return s


def load_fixtures(session: Session) -> dict[int, dict]:
    """FixtureId -> {home, away, competition, start, p1home}."""
    r = httpx.get(f"{CONFIG.base_url}/api/fixtures/snapshot", headers=session.headers(), timeout=25)
    r.raise_for_status()
    out: dict[int, dict] = {}
    for f in r.json():
        fid = f.get("FixtureId")
        p1, p2 = f.get("Participant1"), f.get("Participant2")
        p1home = bool(f.get("Participant1IsHome", True))
        home, away = (p1, p2) if p1home else (p2, p1)
        out[fid] = {"home": home, "away": away, "competition": f.get("Competition"),
                    "start": f.get("StartTime") or 0, "p1home": p1home}
    return out


def _prices_from_odds(ev: dict, info: dict) -> dict[str, float] | None:
    names, prices = ev.get("PriceNames") or [], ev.get("Prices") or []
    if "draw" not in names or len(prices) != len(names):
        return None
    idx = {n: i for i, n in enumerate(names)}
    try:
        part1 = prices[idx["part1"]] / 1000.0
        draw = prices[idx["draw"]] / 1000.0
        part2 = prices[idx["part2"]] / 1000.0
    except (KeyError, IndexError, TypeError):
        return None
    home, away = (part1, part2) if info["p1home"] else (part2, part1)
    if min(home, draw, away) <= 1.0:
        return None
    return {"HOME": round(home, 3), "DRAW": round(draw, 3), "AWAY": round(away, 3)}


class LiveEngine:
    """Owns the live threads and writes into the shared dashboard store."""

    def __init__(self, store, notifier) -> None:
        self.store = store
        self.notifier = notifier
        self.session = build_session()
        self.fixtures = load_fixtures(self.session)
        self.pundit = PunditEngine()
        # per-fixture live score, updated by the scores thread, read by odds thread
        self.scores: dict[int, tuple[int, int]] = {}
        self._seed_store()

    def _seed_store(self) -> None:
        """Populate the hub with every World Cup fixture (upcoming, no odds yet)."""
        for fid, info in self.fixtures.items():
            key = str(fid)
            self.store.fixtures[key] = {
                "fixture_id": key, "home_team": info["home"], "away_team": info["away"],
                "competition": info["competition"], "start": info["start"],
            }
            self.store.matches.setdefault(key, {
                "fixture_id": key, "home_team": info["home"], "away_team": info["away"],
                "minute": 0, "home_goals": 0, "away_goals": 0,
                "prices": {}, "favourite": None, "status": "upcoming",
                "start": info["start"], "competition": info["competition"],
            })

    def start(self) -> None:
        self.store.source = "LIVE"
        threading.Thread(target=self._loop, args=(self._run_odds,), daemon=True).start()
        threading.Thread(target=self._loop, args=(self._run_scores,), daemon=True).start()

    def _loop(self, fn) -> None:
        import time
        while True:
            try:
                fn()
            except Exception as exc:
                print(f"[live] {fn.__name__} error: {exc}; reconnecting in 5s")
                time.sleep(5)

    def _emit(self, fixture_id: str, match: str, msgs) -> None:
        for m in msgs:
            item = {"fixture_id": fixture_id, "match": match, "minute": m.minute,
                    "kind": m.kind, "text": m.text, "speech": m.speech}
            self.store.feed.insert(0, item)
            del self.store.feed[60:]
            try:
                self.notifier.send(m.text)
            except Exception as exc:
                print(f"[telegram error] {exc}")

    def _run_odds(self) -> None:
        for frame in stream(CONFIG.base_url, self.session, "/api/odds/stream"):
            ev = frame.json()
            if not isinstance(ev, dict) or ev.get("SuperOddsType") != ONEX2:
                continue
            if ev.get("Bookmaker") != DEMARGINED:
                continue
            fid = ev.get("FixtureId")
            info = self.fixtures.get(fid)
            if not info:
                continue
            prices = _prices_from_odds(ev, info)
            if not prices:
                continue
            ts = (ev.get("Ts") or 0) / 1000.0
            start = info["start"] / 1000.0
            minute = max(0, int((ts - start) // 60)) if ts > start else 0
            hg, ag = self.scores.get(fid, (0, 0))
            fav = min(prices, key=prices.get)
            self.store.matches[str(fid)] = {
                "fixture_id": str(fid), "home_team": info["home"], "away_team": info["away"],
                "minute": minute, "home_goals": hg, "away_goals": ag,
                "prices": prices, "favourite": fav,
                "status": "live" if minute > 0 else "upcoming",
                "start": info["start"], "competition": info["competition"],
            }
            lf = LiveFrame(fixture_id=str(fid), home_team=info["home"], away_team=info["away"],
                           ts=ts, minute=minute, home_goals=hg, away_goals=ag, prices=prices)
            self._emit(str(fid), f"{info['home']} v {info['away']}", self.pundit.observe(lf))

    def _run_scores(self) -> None:
        for frame in stream(CONFIG.base_url, self.session, "/api/scores/stream"):
            ev = frame.json()
            if not isinstance(ev, dict):
                continue
            fid = ev.get("fixtureId") or ev.get("FixtureId")
            info = self.fixtures.get(fid)
            if not info:
                continue
            score = _extract_score(ev, info)
            if score is None:
                continue
            hg, ag, minute, event = score
            prev = self.scores.get(fid)
            self.scores[fid] = (hg, ag)
            if str(fid) in self.store.matches:
                self.store.matches[str(fid)].update(home_goals=hg, away_goals=ag, minute=minute)
            # only narrate when the score/cards actually changed
            if event is not None and prev != (hg, ag):
                lf = LiveFrame(fixture_id=str(fid), home_team=info["home"], away_team=info["away"],
                               ts=(ev.get("ts") or 0) / 1000.0, minute=minute,
                               home_goals=hg, away_goals=ag,
                               prices=self.store.matches.get(str(fid), {}).get("prices", {}),
                               event=event)
                if lf.prices:
                    self._emit(str(fid), f"{info['home']} v {info['away']}", self.pundit.observe(lf))


def start_engine(store, notifier) -> str:
    """Start the data engine: LIVE if we have an apiToken, else a simulator.

    Returns the resulting source label. Non-blocking (spawns daemon threads).
    """
    if CONFIG.api_token:
        try:
            LiveEngine(store, notifier).start()
            print("[engine] LIVE — streaming the real TxLINE feed")
            return "LIVE"
        except Exception as exc:
            print(f"[engine] live start failed ({exc}); falling back to simulator")
    threading.Thread(target=_simulator_loop, args=(store,), daemon=True).start()
    store.source = "SIMULATED"
    print("[engine] SIMULATED — no TXLINE_API_TOKEN")
    return store.source


def _simulator_loop(store) -> None:
    """Replay simulated World Cup matches into the store (offline demo)."""
    import time

    from .simulate import simulate_match_timeline

    while True:
        engine = PunditEngine()
        seeds = [3, 11, 17, 23]
        timelines = {
            f"SIM_M{i+1:02d}": simulate_match_timeline(f"SIM_M{i+1:02d}", seed=s, pair_index=i)
            for i, s in enumerate(seeds)
        }
        for minute in range(0, 91):
            for fid, frames in timelines.items():
                f = frames[minute]
                fav = min(f.prices, key=f.prices.get)
                store.matches[fid] = {
                    "fixture_id": fid, "home_team": f.home_team, "away_team": f.away_team,
                    "minute": f.minute, "home_goals": f.home_goals, "away_goals": f.away_goals,
                    "prices": {k: round(v, 2) for k, v in f.prices.items()},
                    "favourite": fav, "status": "live",
                }
                for m in engine.observe(f):
                    store.push_message({
                        "fixture_id": fid, "match": f"{f.home_team} v {f.away_team}",
                        "minute": m.minute, "kind": m.kind, "text": m.text, "speech": m.speech,
                    })
            time.sleep(0.5)
        time.sleep(2.0)


def _extract_score(ev: dict, info: dict) -> tuple[int, int, int, tuple[str, str] | None] | None:
    """Best-effort parse of a Scores event into (home_goals, away_goals, minute, event).

    Soccer score lives under participant total scores -> Total -> {Goals, RedCards, ...}.
    Defensive: TxLINE's scores payload nests deeply and we validate it against a live
    match; until then this tolerates missing fields and simply returns None.
    """
    action = ev.get("action") or {}
    score = action.get("Score") or ev.get("Score") or {}
    p1 = (score.get("Participant1") or {}).get("Total") or {}
    p2 = (score.get("Participant2") or {}).get("Total") or {}
    if not p1 and not p2:
        return None
    g1, g2 = int(p1.get("Goals", 0)), int(p2.get("Goals", 0))
    hg, ag = (g1, g2) if info["p1home"] else (g2, g1)
    clock = action.get("Clock") or ev.get("Clock") or {}
    minute = int(clock.get("Minutes", clock.get("minute", 0)) or 0)
    # detect event type from the action tag if present
    event: tuple[str, str] | None = None
    tag = str(action.get("type") or action.get("Type") or "").lower()
    scorer = info["home"] if (g1 > g2) == info["p1home"] else info["away"]
    if "goal" in tag:
        event = ("goal", scorer)
    elif "red" in tag:
        event = ("red_card", scorer)
    return hg, ag, minute, event
