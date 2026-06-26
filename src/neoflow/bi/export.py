"""Export every warehouse table to CSV + Parquet for Tableau / Power BI."""
from __future__ import annotations

import json
import logging

from ..config import PATHS, Settings
from ..duck import connect

log = logging.getLogger("neoflow.bi")

_GUIDE = """# Connecting Tableau / Power BI

Produced by `neoflow export`.

## Option A — DuckDB warehouse (single file)
`exports/warehouse.duckdb` holds the star schema (`dim_neo`, `dim_date`,
`fact_close_approach`) and every `mart_*`. Connect via the DuckDB connector/ODBC.

## Option B — flat extracts (works everywhere)
`exports/bi/*.parquet` and `*.csv` — one file per table; use the Parquet/CSV/folder connector.

## Suggested first views
- Distribution: `mart_size_distribution` `approaches` vs `size_bin_m`, hazardous overlaid.
- Hazard by size: `mart_hazard_summary` `hazardous_share_pct` by `size_band`.
- Trend: `mart_daily_neo` `approaches` / `hazardous_count` over `date`.
- Risk leaderboard: `mart_risk_ranking` top `risk_score` (name, diameter, miss distance).
- Scatter: `mart_close_approach_risk` diameter vs miss distance, colour by hazard, size by `risk_score`.
- Stats: `mart_hazard_stats` (point-biserial r, Mann-Whitney U).
"""


def run_export(settings: Settings, csv_row_limit: int = 1_000_000) -> dict:
    PATHS.bi.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    tables = [r[0] for r in con.execute("SELECT table_name FROM duckdb_tables() ORDER BY 1").fetchall()]
    manifest = {}
    for t in tables:
        cols = [c[0] for c in con.execute(f"DESCRIBE {t}").fetchall()]
        rows = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        con.execute(f"COPY {t} TO '{PATHS.bi / (t + '.parquet')}' (FORMAT PARQUET)")
        formats = ["parquet"]
        if rows <= csv_row_limit:
            con.execute(f"COPY {t} TO '{PATHS.bi / (t + '.csv')}' (HEADER, DELIMITER ',')")
            formats.append("csv")
        manifest[t] = {"rows": int(rows), "columns": cols, "formats": formats}
    con.close()

    (PATHS.bi / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (PATHS.bi / "CONNECT.md").write_text(_GUIDE)
    log.info("exported %d tables to %s", len(tables), PATHS.bi)
    return {"tables": len(tables), "path": str(PATHS.bi)}
