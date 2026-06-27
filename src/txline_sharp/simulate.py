"""Deterministic feed simulator.

Replays realistic 1X2 odds movements for World Cup fixtures so the full pipeline
(detect -> anchor -> grade) runs end-to-end without live access. The hackathon
explicitly allows simulated feeds; seeding makes every run reproducible (and
therefore auditable), which is the same property we want from the detector.

Model per fixture:
  - a hidden "true" win/draw/away probability vector that random-walks slowly,
  - occasional injected sharp moves (a sudden shift in true prob = "sharp money"),
  - published decimal odds = fair odds inflated by a fixed overround (the vig),
  - a final score sampled from the closing true probabilities.
"""
from __future__ import annotations

import random
from collections.abc import Iterator

from .events import LiveFrame
from .mathx import prob_to_fair_odds
from .models import FinalResult, MarketTick

COMPETITION = "FIFA World Cup 2026"
SELECTIONS = ("HOME", "DRAW", "AWAY")

TEAM_PAIRS = [
    ("Brazil", "Argentina"),
    ("France", "England"),
    ("Spain", "Germany"),
    ("Portugal", "Netherlands"),
    ("Croatia", "Morocco"),
    ("USA", "Mexico"),
]


def _apply_overround(fair: dict[str, float], overround: float) -> dict[str, float]:
    """Inflate fair probs into published decimal odds carrying a bookmaker margin."""
    inflated = {s: p * (1.0 + overround) for s, p in fair.items()}
    return {s: round(prob_to_fair_odds(p), 3) for s, p in inflated.items()}


def _normalise(v: dict[str, float]) -> dict[str, float]:
    total = sum(v.values())
    return {k: x / total for k, x in v.items()}


def simulate_fixture(
    fixture_id: str,
    *,
    seed: int,
    start_ts: int = 1_780_000_000,
    ticks: int = 90,
    step_s: int = 30,
    overround: float = 0.05,
    sharp_at: int | None = 45,
    sharp_shift: float = 0.18,
) -> tuple[list[MarketTick], FinalResult]:
    """Produce a stream of MarketTicks plus the final result for one fixture."""
    rng = random.Random(seed)
    # initial true probabilities
    true = _normalise({s: rng.uniform(0.2, 0.5) for s in SELECTIONS})

    out: list[MarketTick] = []
    for i in range(ticks):
        # slow random walk
        true = _normalise({s: max(0.02, p + rng.uniform(-0.01, 0.01)) for s, p in true.items()})
        # injected sharp move: shift mass toward HOME (steam) at a known tick
        if sharp_at is not None and i == sharp_at:
            true["HOME"] += sharp_shift
            true = _normalise(true)

        prices = _apply_overround(true, overround)
        out.append(
            MarketTick(
                fixture_id=fixture_id,
                competition=COMPETITION,
                market="1X2",
                ts=start_ts + i * step_s,
                prices=prices,
            )
        )

    # sample a final result from the closing true probabilities
    roll = rng.random()
    cum, outcome = 0.0, "DRAW"
    for s in SELECTIONS:
        cum += true[s]
        if roll <= cum:
            outcome = s
            break
    home, away = {"HOME": (2, 1), "DRAW": (1, 1), "AWAY": (0, 1)}[outcome]
    return out, FinalResult(fixture_id=fixture_id, home=home, away=away)


def simulate_match_timeline(
    fixture_id: str,
    *,
    seed: int,
    pair_index: int | None = None,
    start_ts: int = 1_780_000_000,
    overround: float = 0.05,
) -> list[LiveFrame]:
    """Minute-by-minute LiveFrames for one match: clock, score, odds, and events.

    Goals shift the hidden true probabilities toward the scoring side; a possible
    red card shifts them away from the penalised side. Odds follow. Occasionally a
    pure market move (sharp money) happens with no on-pitch event.
    """
    rng = random.Random(seed)
    idx = pair_index if pair_index is not None else seed
    home_team, away_team = TEAM_PAIRS[idx % len(TEAM_PAIRS)]
    true = _normalise({s: rng.uniform(0.25, 0.45) for s in SELECTIONS})

    # schedule events on the match clock
    n_goals = rng.choices([0, 1, 2, 3], weights=[2, 4, 3, 1])[0]
    goal_minutes = sorted(rng.sample(range(3, 89), n_goals)) if n_goals else []
    red_minute = rng.choice(range(20, 80)) if rng.random() < 0.35 else None
    sharp_minute = rng.choice(range(10, 85)) if rng.random() < 0.7 else None

    frames: list[LiveFrame] = []
    hg = ag = 0
    for minute in range(0, 91):
        event: tuple[str, str] | None = None

        if minute in goal_minutes:
            scorer_home = rng.random() < true["HOME"] / (true["HOME"] + true["AWAY"])
            if scorer_home:
                hg += 1
                true["HOME"] += 0.18
                team = home_team
            else:
                ag += 1
                true["AWAY"] += 0.18
                team = away_team
            true = _normalise(true)
            event = ("goal", team)
        elif red_minute is not None and minute == red_minute:
            penalised_home = rng.random() < 0.5
            if penalised_home:
                true["HOME"] = max(0.05, true["HOME"] - 0.12)
                team = home_team
            else:
                true["AWAY"] = max(0.05, true["AWAY"] - 0.12)
                team = away_team
            true = _normalise(true)
            event = ("red_card", team)
        elif sharp_minute is not None and minute == sharp_minute:
            # pure market move: no on-pitch event, but smart money shifts the line
            true["HOME"] += 0.10
            true = _normalise(true)
        else:
            true = _normalise({s: max(0.03, p + rng.uniform(-0.01, 0.01)) for s, p in true.items()})

        frames.append(
            LiveFrame(
                fixture_id=fixture_id,
                home_team=home_team,
                away_team=away_team,
                ts=start_ts + minute * 60,
                minute=minute,
                home_goals=hg,
                away_goals=ag,
                prices=_apply_overround(true, overround),
                event=event,
            )
        )
    return frames


def simulate_slate(n: int = 12, *, base_seed: int = 100) -> Iterator[tuple[str, list[MarketTick], FinalResult]]:
    """A slate of fixtures, each deterministically seeded."""
    for k in range(n):
        fid = f"WC2026_M{k + 1:02d}"
        ticks, result = simulate_fixture(fid, seed=base_seed + k, sharp_at=40 + (k % 5) * 3)
        yield fid, ticks, result
