"""End-to-end demo on simulated data: simulate -> detect -> grade -> scorecard.

Run:  python scripts/demo_pipeline.py
No live access required. Proves the full decision pipeline works deterministically.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from txline_sharp.detector import DetectorConfig, SharpDetector  # noqa: E402
from txline_sharp.grading import Scorecard, grade  # noqa: E402
from txline_sharp.mathx import fair_probs  # noqa: E402
from txline_sharp.simulate import simulate_slate  # noqa: E402


def main() -> int:
    detector = SharpDetector(DetectorConfig(prob_threshold=0.05, velocity_window_s=120))
    card = Scorecard()
    signals = []

    for fid, ticks, result in simulate_slate(n=4):
        for tick in ticks:
            fair = dict(zip(tick.prices.keys(), fair_probs(list(tick.prices.values()))))
            for sel, p in fair.items():
                sig = detector.update(fid, tick.market, sel, tick.ts, p)
                if sig:
                    signals.append((sig, result))
        print(f"{fid}: final {result.home}-{result.away} ({result.outcome_1x2})")

    print(f"\nDetected {len(signals)} sharp signal(s):")
    for sig, result in signals:
        g = grade(sig, result)
        card.add(g)
        flag = "WIN " if g.won else "LOSS"
        print(
            f"  [{flag}] {sig.fixture_id} {sig.selection} {sig.direction} "
            f"d={sig.delta:+.3f} in {int(sig.window_s)}s -> backs {g.predicted} "
            f"pnl={g.pnl_units:+.3f}u"
        )

    print(
        f"\nScorecard: n={card.n} hit_rate={card.hit_rate:.1%} "
        f"pnl={card.pnl_units:+.3f}u roi={card.roi:+.1%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
