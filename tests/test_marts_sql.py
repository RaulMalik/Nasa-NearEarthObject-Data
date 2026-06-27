import duckdb
import pandas as pd

from neoflow.config import PATHS


def _seed(con):
    dim_neo = pd.DataFrame(
        {
            "neo_id": ["A", "B", "C"],
            "name": ["(A)", "(B)", "(C)"],
            "est_diameter_mean_m": [30.0, 200.0, 1500.0],
            "is_potentially_hazardous": [False, True, True],
        }
    )
    dim_date = pd.DataFrame(
        {
            "date_key": [20240101, 20240102],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "year": [2024, 2024],
            "month": [1, 1],
            "month_name": ["January", "January"],
        }
    )
    rows = [
        ("A", 20240101, 30.0, False, 5_000_000.0, 12.0, 40000.0),
        ("B", 20240101, 200.0, True, 800_000.0, 2.0, 90000.0),
        ("C", 20240102, 1500.0, True, 300_000.0, 0.8, 130000.0),
        ("A", 20240102, 30.0, False, 6_000_000.0, 15.0, 38000.0),
    ]
    fact = pd.DataFrame(
        rows,
        columns=["neo_id", "date_key", "est_diameter_mean_m", "is_potentially_hazardous",
                 "miss_distance_km", "miss_distance_lunar", "relative_velocity_kmh"],
    )
    fact["approach_id"] = range(len(fact))
    con.register("n", dim_neo)
    con.register("d", dim_date)
    con.register("f", fact)
    con.execute("CREATE TABLE dim_neo AS SELECT * FROM n")
    con.execute("CREATE TABLE dim_date AS SELECT * FROM d")
    con.execute("CREATE TABLE fact_close_approach AS SELECT * FROM f")


def test_marts_build_and_aggregate():
    con = duckdb.connect()
    _seed(con)
    for path in sorted((PATHS.sql / "marts").glob("*.sql")):
        con.execute(path.read_text())

    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    assert {"mart_daily_neo", "mart_hazard_summary", "mart_size_distribution",
            "mart_monthly_neo"} <= tables

    assert con.execute("SELECT sum(approaches) FROM mart_daily_neo").fetchone()[0] == 4
    assert con.execute("SELECT sum(approaches) FROM mart_size_distribution").fetchone()[0] == 4
    big = con.execute(
        "SELECT hazardous_share_pct FROM mart_hazard_summary WHERE size_band = '5. >1000 m'"
    ).fetchone()[0]
    assert big == 100.0
