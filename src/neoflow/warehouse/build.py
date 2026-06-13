"""Build the DuckDB star schema (dims + fact) and run the mart SQL files."""
from __future__ import annotations

import logging

from ..config import PATHS, Settings
from ..duck import connect
from ..staging.clean import STAGED_PATH

log = logging.getLogger("neoflow.warehouse")


def _build_dims_and_fact(con, settings: Settings) -> None:
    w = settings.window
    con.execute(f"CREATE OR REPLACE VIEW stg_approaches AS SELECT * FROM read_parquet('{STAGED_PATH}')")

    con.execute(f"""
        CREATE OR REPLACE TABLE dim_date AS
        WITH spine AS (
            SELECT CAST(d AS DATE) AS date
            FROM range(DATE '{w.start}', DATE '{w.end}', INTERVAL 1 DAY) t(d)
        )
        SELECT
            CAST(strftime(date, '%Y%m%d') AS INTEGER) AS date_key,
            date,
            EXTRACT(year FROM date) AS year,
            EXTRACT(month FROM date) AS month,
            monthname(date) AS month_name,
            isodow(date) - 1 AS weekday,
            dayname(date) AS weekday_name
        FROM spine
    """)

    con.execute("""
        CREATE OR REPLACE TABLE dim_neo AS
        SELECT
            neo_id,
            arbitrary(name) AS name,
            max(absolute_magnitude_h) AS absolute_magnitude_h,
            max(est_diameter_min_m) AS est_diameter_min_m,
            max(est_diameter_max_m) AS est_diameter_max_m,
            max(est_diameter_mean_m) AS est_diameter_mean_m,
            bool_or(is_sentry_object) AS is_sentry_object,
            bool_or(is_potentially_hazardous) AS is_potentially_hazardous,
            arbitrary(nasa_jpl_url) AS nasa_jpl_url,
            count(*) AS approach_count
        FROM stg_approaches
        GROUP BY neo_id
    """)

    con.execute("""
        CREATE OR REPLACE TABLE fact_close_approach AS
        SELECT
            row_number() OVER () AS approach_id,
            neo_id,
            CAST(strftime(close_approach_date, '%Y%m%d') AS INTEGER) AS date_key,
            close_approach_date,
            approach_datetime,
            relative_velocity_kmh, relative_velocity_kps,
            miss_distance_km, miss_distance_lunar, miss_distance_au,
            est_diameter_mean_m,
            is_potentially_hazardous, is_sentry_object,
            orbiting_body
        FROM stg_approaches
    """)


def run_warehouse(settings: Settings) -> dict:
    con = connect()
    _build_dims_and_fact(con, settings)
    for path in sorted((PATHS.sql / "marts").glob("*.sql")):
        con.execute(path.read_text())
        log.info("built %s", path.stem)

    tables = [r[0] for r in con.execute("SELECT table_name FROM duckdb_tables() ORDER BY 1").fetchall()]
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    con.close()
    log.info("warehouse tables: %s", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return {"tables": counts}
