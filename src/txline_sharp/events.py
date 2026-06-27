"""Pundit event engine.

Turns a stream of live match frames (score + current odds) into human, broadcast-
style commentary — the messages an "AI Pundit" Telegram bot sends to fans:

  - GOAL      -> what happened + how the market reacted
  - RED CARD  -> momentum swing + market reaction
  - SHARP ODDS SHIFT (no on-pitch event) -> "smart money" is moving

Each PunditMessage carries both display text (for Telegram) and a plain-text
variant (for TTS). The engine is deterministic: same frames -> same messages.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .mathx import fair_probs


@dataclass
class LiveFrame:
    """One instant of a match: the clock, the score, and the current 1X2 prices."""
    fixture_id: str
    home_team: str
    away_team: str
    ts: float
    minute: int
    home_goals: int
    away_goals: int
    prices: dict[str, float]              # selection -> decimal odds
    event: tuple[str, str] | None = None  # ("goal"|"red_card", team) or None


@dataclass
class PunditMessage:
    fixture_id: str
    minute: int
    kind: str            # "goal" | "red_card" | "sharp_shift"
    text: str            # Telegram markdown
    speech: str          # plain text for TTS


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 83 -> '83rd', 11 -> '11th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _fav(prices: dict[str, float], home: str, away: str) -> str:
    """Human label for the current favourite by lowest decimal odds."""
    sel = min(prices, key=prices.get)
    return {"HOME": home, "AWAY": away, "DRAW": "the draw"}[sel]


def _pct(prices: dict[str, float], selection: str) -> int:
    keys = list(prices.keys())
    fp = dict(zip(keys, fair_probs([prices[k] for k in keys])))
    return round(fp[selection] * 100)


class PunditEngine:
    """Stateful, deterministic commentary generator over LiveFrames."""

    def __init__(
        self,
        shift_threshold: float = 0.035,  # 3.5pp fair-prob move...
        window_s: float = 240.0,         # ...accumulated over up to 4 minutes
        min_window_s: float = 25.0,      # need at least this much elapsed to judge
        cooldown_s: float = 600.0,       # one alert per selection per 10 min
    ) -> None:
        self.shift_threshold = shift_threshold
        self.window_s = window_s
        self.min_window_s = min_window_s
        self.cooldown_s = cooldown_s
        self._prev: dict[str, dict[str, float]] = {}
        # per fixture: rolling (ts, fair_probs, decimal_prices)
        self._hist: dict[str, deque] = {}
        self._last_shift: dict[tuple[str, str], float] = {}

    def observe(self, f: LiveFrame) -> list[PunditMessage]:
        msgs: list[PunditMessage] = []
        prev = self._prev.get(f.fixture_id)

        if f.event is not None:
            kind, team = f.event
            if kind == "goal":
                msgs.append(self._goal(f, team, prev))
            elif kind == "red_card":
                msgs.append(self._red_card(f, team, prev))
        else:
            shift = self._sharp_shift(f)
            if shift is not None:
                msgs.append(shift)

        self._prev[f.fixture_id] = dict(f.prices)
        return msgs

    # --- message builders -------------------------------------------------
    def _goal(self, f: LiveFrame, team: str, prev: dict[str, float] | None) -> PunditMessage:
        score = f"{f.home_goals}-{f.away_goals}"
        fav = _fav(f.prices, f.home_team, f.away_team)
        move = self._move_phrase(f, prev)
        text = (
            f"⚽ *GOAL!* {team} score — {f.home_team} {score} {f.away_team} ({f.minute}').\n"
            f"Market reaction: {move} {fav} now favoured "
            f"(~{_pct(f.prices, 'HOME')}% {f.home_team})."
        )
        speech = (
            f"Goal! {team} score. {f.home_team} {f.home_goals}, {f.away_team} {f.away_goals}, "
            f"in the {_ordinal(f.minute)} minute. The market now favours {fav}."
        )
        return PunditMessage(f.fixture_id, f.minute, "goal", text, speech)

    def _red_card(self, f: LiveFrame, team: str, prev: dict[str, float] | None) -> PunditMessage:
        fav = _fav(f.prices, f.home_team, f.away_team)
        text = (
            f"🟥 *RED CARD!* {team} down to 10 men ({f.minute}').\n"
            f"The market swings — {fav} now favoured "
            f"(~{_pct(f.prices, 'HOME')}% {f.home_team})."
        )
        speech = (
            f"Red card! {team} are down to ten men in the {_ordinal(f.minute)} minute. "
            f"The market now favours {fav}."
        )
        return PunditMessage(f.fixture_id, f.minute, "red_card", text, speech)

    def _sharp_shift(self, f: LiveFrame) -> PunditMessage | None:
        keys = list(f.prices.keys())
        now = dict(zip(keys, fair_probs([f.prices[k] for k in keys])))

        hist = self._hist.setdefault(f.fixture_id, deque())
        hist.append((f.ts, now, dict(f.prices)))
        while hist and f.ts - hist[0][0] > self.window_s:
            hist.popleft()
        if len(hist) < 2:
            return None
        base_ts, base, base_prices = hist[0]
        if f.ts - base_ts < self.min_window_s:
            return None

        sel = max(keys, key=lambda k: now[k] - base[k])
        delta = now[sel] - base[sel]
        if delta < self.shift_threshold:
            return None
        last = self._last_shift.get((f.fixture_id, sel))
        if last is not None and f.ts - last < self.cooldown_s:
            return None
        self._last_shift[(f.fixture_id, sel)] = f.ts

        label = {"HOME": f.home_team, "AWAY": f.away_team, "DRAW": "the draw"}[sel]
        o_before, o_after = base_prices[sel], f.prices[sel]
        pre = f.minute <= 0
        when = "pre-match" if pre else f"{f.minute}'"
        when_s = "before kick-off" if pre else f"in the {_ordinal(f.minute)} minute"
        text = (
            f"📈 *Sharp money* on {label} ({when}) — the price is being backed "
            f"{o_before:.2f} → {o_after:.2f}. Smart money sees ~{round(now[sel]*100)}% now."
        )
        speech = (
            f"Sharp money is backing {label} {when_s}. "
            f"The odds moved from {o_before:.2f} to {o_after:.2f}."
        )
        return PunditMessage(f.fixture_id, f.minute, "sharp_shift", text, speech)

    @staticmethod
    def _move_phrase(f: LiveFrame, prev: dict[str, float] | None) -> str:
        if not prev:
            return "prices reset,"
        return "odds swung,"
