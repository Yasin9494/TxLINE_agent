"""Sharp-movement detector.

A "sharp" move is a fast, material shift in the vig-removed probability of a
selection. We track each (fixture, market, selection) as a small rolling state
and emit a Signal when BOTH:

  - magnitude: |Δ fair_prob| over the lookback window >= prob_threshold
  - velocity:  that change happened within velocity_window_s seconds

This is intentionally simple and deterministic so the logic is defensible and
every signal is reproducible from the raw event log.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Observation:
    ts: float          # event timestamp (epoch seconds)
    fair_prob: float   # vig-removed probability at this time


@dataclass
class Signal:
    fixture_id: str
    market: str
    selection: str
    ts: float
    prob_before: float
    prob_after: float
    delta: float           # prob_after - prob_before (signed)
    window_s: float        # how long the move took
    direction: str         # "steam" (prob up) | "drift" (prob down)


@dataclass
class DetectorConfig:
    prob_threshold: float = 0.05      # 5 percentage-point fair-prob move
    velocity_window_s: float = 120.0  # within 2 minutes
    history: int = 64                 # observations retained per selection
    cooldown_s: float = 300.0         # after a signal, suppress this key for 5 min


@dataclass
class SharpDetector:
    cfg: DetectorConfig = field(default_factory=DetectorConfig)
    _state: dict[tuple[str, str, str], deque[Observation]] = field(default_factory=dict)
    _last_signal: dict[tuple[str, str, str], float] = field(default_factory=dict)

    def update(
        self, fixture_id: str, market: str, selection: str, ts: float, fair_prob: float
    ) -> Signal | None:
        """Feed one normalised observation; return a Signal if a sharp move fires."""
        key = (fixture_id, market, selection)
        buf = self._state.setdefault(key, deque(maxlen=self.cfg.history))
        buf.append(Observation(ts, fair_prob))

        # cooldown: one sharp move should emit one signal, not one per tick
        last = self._last_signal.get(key)
        if last is not None and ts - last < self.cfg.cooldown_s:
            return None

        cutoff = ts - self.cfg.velocity_window_s
        # earliest observation still inside the velocity window
        ref: Observation | None = None
        for obs in buf:
            if obs.ts >= cutoff:
                ref = obs
                break
        if ref is None or ref.ts == ts:
            return None

        delta = fair_prob - ref.fair_prob
        if abs(delta) < self.cfg.prob_threshold:
            return None

        self._last_signal[key] = ts
        return Signal(
            fixture_id=fixture_id,
            market=market,
            selection=selection,
            ts=ts,
            prob_before=ref.fair_prob,
            prob_after=fair_prob,
            delta=delta,
            window_s=ts - ref.ts,
            direction="steam" if delta > 0 else "drift",
        )
