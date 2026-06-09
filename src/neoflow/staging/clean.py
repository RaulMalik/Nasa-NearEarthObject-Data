"""Flatten the nested NEO feed into one cleaned row per close approach."""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from ..config import PATHS, Settings
from ..ingest.nasa_api import RAW_PATH

log = logging.getLogger("neoflow.staging")

STAGED_PATH = PATHS.staged / "close_approaches.parquet"


def _f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _flatten(chunks: list) -> pd.DataFrame:
    rows = []
    for chunk in chunks:
        for day, objects in chunk.get("near_earth_objects", {}).items():
            for neo in objects:
                meters = neo.get("estimated_diameter", {}).get("meters", {})
                d_min = _f(meters.get("estimated_diameter_min"))
                d_max = _f(meters.get("estimated_diameter_max"))
                both_nan = np.isnan(d_min) and np.isnan(d_max)
                d_mean = np.nan if both_nan else np.nanmean([d_min, d_max])
                for ca in neo.get("close_approach_data") or [{}]:
                    vel, miss = ca.get("relative_velocity", {}), ca.get("miss_distance", {})
                    rows.append(
                        {
                            "neo_id": neo.get("id"),
                            "neo_reference_id": neo.get("neo_reference_id"),
                            "name": neo.get("name"),
                            "nasa_jpl_url": neo.get("nasa_jpl_url"),
                            "absolute_magnitude_h": _f(neo.get("absolute_magnitude_h")),
                            "est_diameter_min_m": d_min,
                            "est_diameter_max_m": d_max,
                            "est_diameter_mean_m": d_mean,
                            "is_potentially_hazardous": bool(neo.get("is_potentially_hazardous_asteroid")),
                            "is_sentry_object": bool(neo.get("is_sentry_object")),
                            "close_approach_date": ca.get("close_approach_date") or day,
                            "approach_datetime": ca.get("close_approach_date_full"),
                            "relative_velocity_kmh": _f(vel.get("kilometers_per_hour")),
                            "relative_velocity_kps": _f(vel.get("kilometers_per_second")),
                            "miss_distance_km": _f(miss.get("kilometers")),
                            "miss_distance_lunar": _f(miss.get("lunar")),
                            "miss_distance_au": _f(miss.get("astronomical")),
                            "orbiting_body": ca.get("orbiting_body"),
                        }
                    )
    return pd.DataFrame(rows)


def clean_frame(df: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    df = df.copy()
    df["close_approach_date"] = pd.to_datetime(df["close_approach_date"], errors="coerce")
    df = df.dropna(subset=["est_diameter_mean_m", "miss_distance_km", "relative_velocity_kmh",
                           "close_approach_date"])
    start, end = pd.Timestamp(settings.window.start), pd.Timestamp(settings.window.end)
    df = df[(df["close_approach_date"] >= start) & (df["close_approach_date"] < end)]
    df = df[df["miss_distance_lunar"] <= settings.cleaning.max_miss_distance_lunar]
    df = df.drop_duplicates(subset=["neo_id", "approach_datetime", "miss_distance_km"])
    return df.sort_values(["close_approach_date", "miss_distance_km"]).reset_index(drop=True)


def run_staging(settings: Settings) -> dict:
    PATHS.staged.mkdir(parents=True, exist_ok=True)
    chunks = json.loads(RAW_PATH.read_text())
    df = _flatten(chunks)
    raw_total = len(df)
    df = clean_frame(df, settings)

    df.to_parquet(STAGED_PATH, index=False)
    summary = {
        "rows_raw": int(raw_total),
        "rows_clean": int(len(df)),
        "rows_removed": int(raw_total - len(df)),
        "path": str(STAGED_PATH),
    }
    log.info("staged %d/%d close approaches", summary["rows_clean"], summary["rows_raw"])
    return summary
