"""Composite close-approach risk score from size, proximity, velocity and the hazard flag."""
from __future__ import annotations

import logging

import numpy as np

from ..config import Settings
from ..duck import connect

log = logging.getLogger("neoflow.risk")


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = np.nanmin(x), np.nanmax(x)
    if not np.isfinite(lo) or hi == lo:
        return np.zeros_like(x, dtype=float)
    return (x - lo) / (hi - lo)


def run_risk(settings: Settings) -> dict:
    con = connect()
    df = con.execute(
        """SELECT f.approach_id, f.neo_id, n.name, f.close_approach_date,
                  f.est_diameter_mean_m, f.miss_distance_km, f.miss_distance_lunar,
                  f.relative_velocity_kmh, f.is_potentially_hazardous
           FROM fact_close_approach f JOIN dim_neo n USING (neo_id)"""
    ).df()

    w = settings.risk
    df["size_factor"] = _minmax(np.log10(df["est_diameter_mean_m"].to_numpy()))
    df["proximity_factor"] = _minmax(-np.log10(df["miss_distance_lunar"].to_numpy() + 0.1))
    df["velocity_factor"] = _minmax(df["relative_velocity_kmh"].to_numpy())
    df["hazard_factor"] = df["is_potentially_hazardous"].astype(float)
    df["risk_score"] = (
        w.w_size * df["size_factor"]
        + w.w_proximity * df["proximity_factor"]
        + w.w_velocity * df["velocity_factor"]
        + w.w_hazard * df["hazard_factor"]
    ) * 100
    df["risk_score"] = df["risk_score"].round(2)

    ranking = df.sort_values("risk_score", ascending=False).head(100)

    con.register("risk_df", df)
    con.execute("CREATE OR REPLACE TABLE mart_close_approach_risk AS SELECT * FROM risk_df")
    con.register("rank_df", ranking)
    con.execute("CREATE OR REPLACE TABLE mart_risk_ranking AS SELECT * FROM rank_df")
    con.close()

    log.info("risk scored %d approaches | max=%.1f median=%.1f",
             len(df), df["risk_score"].max(), df["risk_score"].median())
    return {"scored": int(len(df)), "max_risk": float(df["risk_score"].max())}
