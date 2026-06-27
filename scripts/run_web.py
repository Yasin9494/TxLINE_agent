"""Start the AI Pundit web dashboard.

Run:  python scripts/run_web.py
Then open http://127.0.0.1:8000 in your browser.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("txline_sharp.api:app", host="127.0.0.1", port=8000, reload=False)
