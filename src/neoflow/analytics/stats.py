"""Test whether NEO size is associated with the potentially-hazardous flag."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from ..config import Settings
from ..duck import connect

log = logging.getLogger("neoflow.stats")


def run_stats(settings: Settings) -> dict:
    con = connect()
    df = con.execute(
        "SELECT est_diameter_mean_m, is_potentially_hazardous FROM fact_close_approach"
    ).df()

    size = df["est_diameter_mean_m"].to_numpy(dtype=float)
    hazard = df["is_potentially_hazardous"].to_numpy(dtype=float)
    log_size = np.log10(size)

    r_pb, p_pb = stats.pointbiserialr(hazard, log_size)
    haz, safe = log_size[hazard == 1], log_size[hazard == 0]
    if len(haz) and len(safe):
        u_stat, p_u = stats.mannwhitneyu(haz, safe, alternative="two-sided")
    else:
        u_stat, p_u = np.nan, np.nan

    rows = [
        {"method": "Point-biserial r (hazard vs log10 size)", "statistic": round(float(r_pb), 4),
         "p_value": float(p_pb), "detail": "correlation between size and the hazard flag"},
        {"method": "Mann-Whitney U (log size: hazardous vs safe)", "statistic": float(u_stat),
         "p_value": float(p_u), "detail": "distribution shift in size between groups"},
        {"method": "Median diameter hazardous (m)",
         "statistic": round(float(10 ** np.median(haz)) if len(haz) else np.nan, 1),
         "p_value": np.nan, "detail": "typical size of hazardous approaches"},
        {"method": "Median diameter non-hazardous (m)",
         "statistic": round(float(10 ** np.median(safe)) if len(safe) else np.nan, 1),
         "p_value": np.nan, "detail": "typical size of non-hazardous approaches"},
    ]
    out = pd.DataFrame(rows)

    con.register("stats_df", out)
    con.execute("CREATE OR REPLACE TABLE mart_hazard_stats AS SELECT * FROM stats_df")
    con.close()

    log.info("hazard~size: point-biserial r=%.3f (p=%.1e)", r_pb, p_pb)
    return {"point_biserial_r": round(float(r_pb), 4), "p_value": float(p_pb)}
