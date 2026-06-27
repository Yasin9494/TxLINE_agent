"""TxLINE Server-Sent Events client for the live odds & scores feeds.

Endpoints (confirmed):
  GET /api/odds/stream
  GET /api/scores/stream
Headers: Authorization: Bearer <jwt>, X-Api-Token: <apiToken>, Accept: text/event-stream

The exact event JSON is not documented yet — until we capture real events with an
activated token, this client parses the generic SSE framing (`event:` / `data:`
lines separated by blank lines) and yields raw frames. `capture_raw()` dumps them
to disk so we can lock the normalized schema from ground truth.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx

from .auth import Session


@dataclass
class SSEFrame:
    event: str | None
    data: str

    def json(self) -> object | None:
        try:
            return json.loads(self.data)
        except (json.JSONDecodeError, ValueError):
            return None


def stream(
    base_url: str, session: Session, path: str, client: httpx.Client | None = None
) -> Iterator[SSEFrame]:
    """Yield SSE frames from a TxLINE stream path (e.g. '/api/odds/stream')."""
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30.0, read=None))
    headers = {**session.headers(), "Accept": "text/event-stream", "Cache-Control": "no-cache"}
    try:
        with client.stream("GET", f"{base_url}{path}", headers=headers) as resp:
            resp.raise_for_status()
            event: str | None = None
            data_lines: list[str] = []
            for line in resp.iter_lines():
                if line == "":  # frame boundary
                    if data_lines:
                        yield SSEFrame(event=event, data="\n".join(data_lines))
                    event, data_lines = None, []
                elif line.startswith(":"):  # comment / heartbeat
                    continue
                elif line.startswith("event:"):
                    event = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].lstrip())
    finally:
        if owns:
            client.close()


def capture_raw(base_url: str, session: Session, path: str, out: Path, limit: int = 200) -> int:
    """Dump up to `limit` raw frames to a JSONL file. Returns count captured."""
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for frame in stream(base_url, session, path):
            fh.write(json.dumps({"event": frame.event, "data": frame.data}) + "\n")
            n += 1
            if n >= limit:
                break
    return n
