"""Validate the close-approach contract and compute full-table metrics."""
from __future__ import annotations

import json
import logging

import duckdb

from ..config import PATHS, Settings
from ..staging.clean import STAGED_PATH
from .schemas import approaches_schema

log = logging.getLogger("neoflow.quality")

_KEY_COLS = ["est_diameter_mean_m", "relative_velocity_kmh", "miss_distance_km",
             "miss_distance_lunar", "absolute_magnitude_h"]


def _metrics(con: duckdb.DuckDBPyConnection, src: str) -> dict:
    total = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
    null_rates = {}
    for col in _KEY_COLS:
        nulls = con.execute(f"SELECT count(*) - count({col}) FROM {src}").fetchone()[0]
        null_rates[col] = round(nulls / total, 4) if total else 0.0
    ranges = {}
    for col in _KEY_COLS:
        lo, hi = con.execute(f"SELECT min({col}), max({col}) FROM {src}").fetchone()
        ranges[col] = {"min": float(lo), "max": float(hi)}
    distinct_neos = con.execute(f"SELECT count(DISTINCT neo_id) FROM {src}").fetchone()[0]
    hazardous = con.execute(f"SELECT avg(is_potentially_hazardous::INT) FROM {src}").fetchone()[0]
    dmin, dmax = con.execute(
        f"SELECT min(close_approach_date), max(close_approach_date) FROM {src}"
    ).fetchone()
    return {
        "row_count": int(total),
        "distinct_neos": int(distinct_neos),
        "hazardous_share": round(float(hazardous), 4),
        "date_min": str(dmin),
        "date_max": str(dmax),
        "null_rates": null_rates,
        "ranges": ranges,
    }


def run_quality(settings: Settings) -> dict:
    PATHS.quality.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    src = f"read_parquet('{STAGED_PATH}')"
    metrics = _metrics(con, src)
    df = con.execute(f"SELECT * FROM {src}").df()
    con.close()

    contract = {"rows": len(df), "passed": True, "errors": []}
    try:
        approaches_schema().validate(df, lazy=True)
    except Exception as exc:
        contract["passed"] = False
        fc = getattr(exc, "failure_cases", None)
        contract["errors"] = (
            fc.groupby("check").size().reset_index(name="n").to_dict("records")
            if fc is not None else [{"check": str(exc)[:300]}]
        )

    report = {"status": "pass" if contract["passed"] else "fail", "metrics": metrics, "contract": contract}
    (PATHS.quality / "approaches_quality.json").write_text(json.dumps(report, indent=2, default=str))
    (PATHS.quality / "approaches_quality.md").write_text(_md(report))
    log.info("data quality: %s | rows=%s neos=%s hazardous=%.1f%%", report["status"],
             metrics["row_count"], metrics["distinct_neos"], metrics["hazardous_share"] * 100)
    return report


def _md(report: dict) -> str:
    m = report["metrics"]
    lines = [
        "# Close-approach data-quality report", "",
        f"**Status:** {report['status'].upper()}",
        f"**Rows:** {m['row_count']:,}  |  **Distinct NEOs:** {m['distinct_neos']:,}  "
        f"|  **Hazardous share:** {m['hazardous_share']:.1%}",
        f"**Date range:** {m['date_min']} → {m['date_max']}", "",
        "## Null rates", "| column | null rate |", "| --- | --- |",
    ]
    lines += [f"| {c} | {r:.2%} |" for c, r in m["null_rates"].items()]
    lines += ["", "## Ranges", "| column | min | max |", "| --- | --- | --- |"]
    lines += [f"| {c} | {v['min']:.3f} | {v['max']:.3f} |" for c, v in m["ranges"].items()]
    lines += ["", "## Contract (pandera)", f"- rows: {report['contract']['rows']:,}",
              f"- passed: {report['contract']['passed']}"]
    if report["contract"]["errors"]:
        lines += ["- failing checks:"] + [f"  - {e}" for e in report["contract"]["errors"]]
    return "\n".join(lines) + "\n"
