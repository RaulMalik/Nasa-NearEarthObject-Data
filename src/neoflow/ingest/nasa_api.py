"""Fetch NASA Near-Earth-Object close-approach data from the NEO feed API."""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

import requests

from ..config import PATHS, Settings

log = logging.getLogger("neoflow.ingest")

RAW_PATH = PATHS.raw / "neo_raw.json"


def _chunks(start: str, end: str, days: int):
    cur, stop = date.fromisoformat(start), date.fromisoformat(end)
    while cur < stop:
        chunk_end = min(cur + timedelta(days=days - 1), stop - timedelta(days=1))
        yield cur.isoformat(), chunk_end.isoformat()
        cur = chunk_end + timedelta(days=1)


_KEY_RE = re.compile(r"(api_key=)[^&\"\s]+")


def _sanitize(obj):
    """Drop noisy link blocks and redact the API key from any embedded URL."""
    if isinstance(obj, dict):
        obj.pop("links", None)
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, str):
        return _KEY_RE.sub(r"\1REDACTED", obj)
    return obj


def fetch_feed(api_base: str, start_date: str, end_date: str, api_key: str, timeout: int = 60) -> dict:
    resp = requests.get(
        api_base,
        params={"start_date": start_date, "end_date": end_date, "api_key": api_key},
        timeout=timeout,
    )
    resp.raise_for_status()
    return _sanitize(resp.json())


def ingest_live(settings: Settings, force: bool = False) -> dict:
    PATHS.raw.mkdir(parents=True, exist_ok=True)
    if RAW_PATH.exists() and not force:
        chunks = json.loads(RAW_PATH.read_text())
        log.info("cached %s (%d chunks)", RAW_PATH.name, len(chunks))
        return {"source": "live", "chunks": len(chunks)}

    chunks = []
    for start, end in _chunks(settings.window.start, settings.window.end, settings.ingest.chunk_days):
        data = fetch_feed(settings.ingest.api_base, start, end, settings.nasa_api_key)
        chunks.append(data)
        log.info("fetched %s..%s (%s objects)", start, end, data.get("element_count", "?"))

    RAW_PATH.write_text(json.dumps(chunks))
    log.info("saved %s (%d chunks)", RAW_PATH.name, len(chunks))
    return {"source": "live", "chunks": len(chunks)}
