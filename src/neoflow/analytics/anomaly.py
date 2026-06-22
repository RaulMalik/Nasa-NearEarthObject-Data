"""Flag unusual close approaches with IsolationForest plus simple physical rules."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..config import Settings
from ..duck import connect

log = logging.getLogger("neoflow.anomaly")


def _rule_reasons(df: pd.DataFrame) -> pd.Series:
    rules = {
        "very_large": df["est_diameter_mean_m"] > 1000,
        "very_close": df["miss_distance_lunar"] < 1,
        "very_fast": df["relative_velocity_kmh"] > 120_000,
    }
    reasons = [[] for _ in range(len(df))]
    for name, mask in rules.items():
        for i in np.where(mask.to_numpy())[0]:
            reasons[i].append(name)
    return pd.Series([",".join(r) for r in reasons], index=df.index)


def run_anomaly(settings: Settings) -> dict:
    con = connect()
    df = con.execute(
        """SELECT f.approach_id, f.neo_id, n.name, f.close_approach_date,
                  f.est_diameter_mean_m, f.miss_distance_lunar, f.relative_velocity_kmh,
                  f.is_potentially_hazardous
           FROM fact_close_approach f JOIN dim_neo n USING (neo_id)"""
    ).df()

    feats = np.column_stack(
        [
            np.log10(df["est_diameter_mean_m"]),
            np.log10(df["miss_distance_lunar"] + 0.1),
            df["relative_velocity_kmh"],
        ]
    )
    X = StandardScaler().fit_transform(feats)
    iso = IsolationForest(contamination=settings.anomaly.contamination, random_state=7, n_estimators=200)
    df["iso_outlier"] = iso.fit_predict(X) == -1
    df["anomaly_score"] = -iso.score_samples(X)
    df["rules"] = _rule_reasons(df)
    df["is_anomaly"] = df["iso_outlier"] | (df["rules"] != "")

    flagged = df[df["is_anomaly"]].sort_values("anomaly_score", ascending=False)
    con.register("anom_df", flagged)
    con.execute("CREATE OR REPLACE TABLE mart_neo_anomalies AS SELECT * FROM anom_df")
    con.close()

    log.info("anomalies: %d/%d (%.2f%%)", len(flagged), len(df), len(flagged) / len(df) * 100)
    return {"approaches": int(len(df)), "anomalies": int(len(flagged))}
