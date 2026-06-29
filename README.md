# NASA NEO Risk Platform

An end-to-end data platform over NASA's Near-Earth-Object (NEO) feed. It ingests
close-approach data from the NASA API, cleans and validates it, models a DuckDB
**star schema**, computes a **composite close-approach risk score**, runs a
**size↔hazard statistical test** and **anomaly detection**, and publishes
**BI-ready marts** for Tableau / Power BI.

Same engineering backbone as a production analytics service: config-driven,
tested, layered, with data-quality contracts and a clean serving layer.

## Architecture

```
                ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌────────────┐
NASA NEO API ─▶ │ ingest  │─▶ │ staging  │─▶ │ warehouse │─▶ │ BI exports │
(7-day chunks)  │ (bronze)│   │ (silver) │   │  (gold)   │   │ csv/parquet│
                └─────────┘   └────┬─────┘   └─────┬─────┘   │  + duckdb  │
                                   │               │         └────────────┘
                             ┌─────▼─────┐   ┌─────▼──────────────┐
                             │ quality   │   │ analytics          │
                             │ (pandera) │   │ risk · stats ·     │
                             └───────────┘   │ anomaly            │
                                             └────────────────────┘
```

- **Bronze** `data/raw/neo_raw.json`: raw feed responses (or synthetic).
- **Silver** `data/staged/close_approaches.parquet`: one cleaned row per close approach.
- **Gold** `exports/warehouse.duckdb`: star schema + analytics marts.
- **Serving** `exports/bi/`: every table as CSV + Parquet, with a connection guide.

## Data model (star schema)

| table | grain | notes |
| --- | --- | --- |
| `fact_close_approach` | one approach | velocity, miss distance, size, hazard flag |
| `dim_neo` | one object | size, magnitude, sentry/hazard flags |
| `dim_date` | one day | calendar attributes |
| `mart_daily_neo` | day | counts, size, hazard share, closest miss |
| `mart_hazard_summary` | size band | hazard rate by size |
| `mart_size_distribution` | size bin | histogram (hazardous overlay) |
| `mart_monthly_neo` | month | rollup |
| `mart_close_approach_risk` | approach | risk components + score |
| `mart_risk_ranking` | approach | top-100 by risk score |
| `mart_hazard_stats` | test | point-biserial r, Mann-Whitney U |
| `mart_neo_anomalies` | approach | flagged outliers + reasons |

## Quickstart

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env          # add your NASA_API_KEY (DEMO_KEY also works)
source .venv/bin/activate

neoflow run-all               # full pipeline (live API)
neoflow run-all --source synthetic   # fully offline
```

Run any stage on its own: `neoflow ingest|stage|quality|warehouse|risk|stats|anomaly|viz|export`.

Configuration: [`config/settings.yaml`](config/settings.yaml) (date window, risk
weights, …); the API key is read from `.env` (`NASA_API_KEY`) and never logged.

## Analytics

- **Risk score**: each close approach gets a 0-100 score combining size,
  proximity (inverse miss distance), velocity and the hazard flag, with
  configurable weights. Drives `mart_risk_ranking`.
- **Statistics**: point-biserial correlation and Mann-Whitney U test of whether
  hazardous objects are systematically larger (`mart_hazard_stats`).
- **Anomaly detection**: `IsolationForest` over size/distance/velocity plus
  physical rules (very large / very close / very fast).

## Data quality

`neoflow quality` validates the full table against a pandera contract and writes
metrics (row counts, null rates, ranges, hazard share, freshness) to
`reports/data_quality/`.

## Tests

```bash
pytest          # synthetic + in-memory, no network
ruff check src
```
