"""Deterministic odds math. No randomness, no hidden state — fully auditable.

Conventions:
  - Decimal odds (e.g. 2.50). price <= 1.0 is invalid.
  - Implied probability of a single price = 1 / price (includes the bookmaker margin).
  - For a market, raw implied probs sum to > 1; the excess is the "vig" (overround).
    We normalise them to sum to 1 to get the fair, vig-removed probability.
"""
from __future__ import annotations


def implied_prob(decimal_odds: float) -> float:
    """Raw implied probability from a single decimal price (margin included)."""
    if decimal_odds <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {decimal_odds}")
    return 1.0 / decimal_odds


def overround(prices: list[float]) -> float:
    """Bookmaker margin for a market: sum of raw implied probs minus 1."""
    return sum(implied_prob(p) for p in prices) - 1.0


def fair_probs(prices: list[float]) -> list[float]:
    """Vig-removed (normalised-to-1) probabilities for a market's selections."""
    raw = [implied_prob(p) for p in prices]
    total = sum(raw)
    if total <= 0:
        raise ValueError("non-positive probability total")
    return [p / total for p in raw]


def prob_to_fair_odds(prob: float) -> float:
    """Fair decimal odds from a (vig-removed) probability."""
    if not 0.0 < prob < 1.0:
        raise ValueError(f"probability must be in (0,1), got {prob}")
    return 1.0 / prob
