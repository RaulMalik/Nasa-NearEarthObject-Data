"""Deterministic synthetic NEO feed used for offline runs and tests.

Emits the same nested JSON shape as the NASA feed so staging is identical.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import numpy as np

from ..config import PATHS, Settings
from .nasa_api import RAW_PATH

log = logging.getLogger("neoflow.ingest")

_LUNAR_KM = 384_400.0
_AU_KM = 149_597_870.7


def _neo(rng, idx: int, day: str) -> dict:
    d_min = float(np.round(rng.lognormal(4.0, 0.9), 1))      # metres
    d_max = float(np.round(d_min * rng.uniform(1.5, 2.4), 1))
    mean = (d_min + d_max) / 2
    kps = float(np.round(rng.uniform(4, 32), 4))
    lunar = float(np.round(rng.lognormal(2.2, 1.0), 4))
    km = lunar * _LUNAR_KM
    hazard_p = min(0.9, mean / 1200 + (lunar < 20) * 0.15)
    return {
        "id": f"S{idx:07d}",
        "neo_reference_id": f"S{idx:07d}",
        "name": f"(2024 SY{idx})",
        "nasa_jpl_url": "https://example.org/neo",
        "absolute_magnitude_h": float(np.round(rng.uniform(17, 28), 2)),
        "estimated_diameter": {
            "meters": {"estimated_diameter_min": d_min, "estimated_diameter_max": d_max}
        },
        "is_potentially_hazardous_asteroid": bool(rng.random() < hazard_p),
        "is_sentry_object": bool(rng.random() < 0.01),
        "close_approach_data": [
            {
                "close_approach_date": day,
                "close_approach_date_full": f"{day} {rng.integers(0, 24):02d}:00",
                "relative_velocity": {
                    "kilometers_per_second": str(kps),
                    "kilometers_per_hour": str(round(kps * 3600, 1)),
                },
                "miss_distance": {
                    "astronomical": str(round(km / _AU_KM, 6)),
                    "lunar": str(lunar),
                    "kilometers": str(round(km, 1)),
                },
                "orbiting_body": "Earth",
            }
        ],
    }


def ingest_synthetic(settings: Settings, seed: int = 7) -> dict:
    PATHS.raw.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    start, stop = date.fromisoformat(settings.window.start), date.fromisoformat(settings.window.end)

    chunk, neo_by_date, idx, day = {}, {}, 0, start
    while day < stop:
        n = int(rng.poisson(8)) + 1
        neo_by_date[day.isoformat()] = [_neo(rng, idx + i, day.isoformat()) for i in range(n)]
        idx += n
        day += timedelta(days=1)

    chunk = {"element_count": idx, "near_earth_objects": neo_by_date}
    RAW_PATH.write_text(json.dumps([chunk]))
    log.info("synthetic feed: %d approaches over %d days", idx, len(neo_by_date))
    return {"source": "synthetic", "chunks": 1}
