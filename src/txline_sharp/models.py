"""Normalized internal schema.

Both the live TxLINE adapter and the simulator emit these types, so the detector,
grader, anchor and API layers are identical regardless of data source. When we
capture real SSE events, we map their fields onto these — nothing downstream changes.
"""
from __future__ import annotations

from pydantic import BaseModel


class OddsUpdate(BaseModel):
    fixture_id: str
    competition: str          # e.g. "FIFA World Cup 2026"
    market: str               # e.g. "1X2"
    selection: str            # e.g. "HOME" | "DRAW" | "AWAY"
    price: float              # decimal odds, > 1.0
    ts: float                 # epoch seconds


class MarketTick(BaseModel):
    """All selections of one market at one instant — the unit the detector consumes."""
    fixture_id: str
    competition: str
    market: str
    ts: float
    prices: dict[str, float]  # selection -> decimal odds


class ScoreUpdate(BaseModel):
    fixture_id: str
    ts: float
    home: int
    away: int
    minute: int
    status: str               # "scheduled" | "live" | "final"


class FinalResult(BaseModel):
    fixture_id: str
    home: int
    away: int

    @property
    def outcome_1x2(self) -> str:
        if self.home > self.away:
            return "HOME"
        if self.home < self.away:
            return "AWAY"
        return "DRAW"
