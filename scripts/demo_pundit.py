"""Demo: what the AI Pundit bot would post during a live match (dry run, no Telegram).

Run:  python scripts/demo_pundit.py
Replays a simulated World Cup match minute-by-minute and prints every message the
bot would send. Swap the simulator for the live TxLINE feed and the same messages
go out to Telegram.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from txline_sharp.events import PunditEngine  # noqa: E402
from txline_sharp.simulate import simulate_match_timeline  # noqa: E402


def _pick_lively_seed() -> int:
    """Find a deterministic seed that yields an eventful match (goals + a card/shift)."""
    for seed in range(50):
        frames = simulate_match_timeline("probe", seed=seed)
        goals = sum(1 for f in frames if f.event and f.event[0] == "goal")
        cards = sum(1 for f in frames if f.event and f.event[0] == "red_card")
        if goals >= 2 and cards >= 1:
            return seed
    return 0


def main() -> int:
    seed = _pick_lively_seed()
    frames = simulate_match_timeline("WC2026_M01", seed=seed)
    home, away = frames[0].home_team, frames[0].away_team
    print(f"=== {home} vs {away}  (simulated TxLINE feed, seed={seed}) ===\n")

    engine = PunditEngine()
    sent = 0
    for f in frames:
        for msg in engine.observe(f):
            sent += 1
            print(msg.text)
            print(f"   🔊 TTS: {msg.speech}\n")

    final = frames[-1]
    print(f"=== FULL TIME: {home} {final.home_goals}-{final.away_goals} {away} "
          f"| {sent} pundit messages sent ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
