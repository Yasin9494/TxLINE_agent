"""Grade signals against final results.

A "steam" signal (fair prob of a selection rising sharply) is read as a prediction
that the selection will WIN. A "drift" (prob falling) predicts it will NOT win.
We grade each signal once the match is final and track hit-rate plus a flat-stake
ROI using the fair odds at signal time.
"""
from __future__ import annotations

from dataclasses import dataclass

from .detector import Signal
from .mathx import prob_to_fair_odds
from .models import FinalResult


@dataclass
class GradedSignal:
    signal: Signal
    predicted: str          # selection the signal backs
    won: bool
    pnl_units: float        # flat 1-unit stake, settled at fair odds


def grade(signal: Signal, result: FinalResult) -> GradedSignal:
    if signal.market != "1X2":
        raise ValueError(f"grading only supports 1X2, got {signal.market}")
    outcome = result.outcome_1x2

    if signal.direction == "steam":
        predicted = signal.selection
        won = outcome == predicted
        # settle the 1-unit stake at the fair odds implied right after the move
        fair_odds = prob_to_fair_odds(signal.prob_after)
        pnl = (fair_odds - 1.0) if won else -1.0
    else:  # drift: bet against the selection
        predicted = f"NOT_{signal.selection}"
        won = outcome != signal.selection
        fair_odds = prob_to_fair_odds(1.0 - signal.prob_after)
        pnl = (fair_odds - 1.0) if won else -1.0

    return GradedSignal(signal=signal, predicted=predicted, won=won, pnl_units=round(pnl, 4))


@dataclass
class Scorecard:
    n: int = 0
    wins: int = 0
    pnl_units: float = 0.0

    def add(self, g: GradedSignal) -> None:
        self.n += 1
        self.wins += int(g.won)
        self.pnl_units += g.pnl_units

    @property
    def hit_rate(self) -> float:
        return self.wins / self.n if self.n else 0.0

    @property
    def roi(self) -> float:
        return self.pnl_units / self.n if self.n else 0.0
