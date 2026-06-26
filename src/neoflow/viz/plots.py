"""Figures rendered straight from the warehouse marts."""
from __future__ import annotations

import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ..config import PATHS, Settings  # noqa: E402
from ..duck import connect  # noqa: E402

log = logging.getLogger("neoflow.viz")
HAZARD = "#C70039"
SAFE = "#C9CDD2"


def _q(sql: str):
    con = connect(read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def size_distribution():
    df = _q("SELECT size_bin_m, approaches, hazardous_count FROM mart_size_distribution ORDER BY size_bin_m")
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(df["size_bin_m"], df["approaches"], width=42, color=SAFE, label="all")
    ax.bar(df["size_bin_m"], df["hazardous_count"], width=42, color=HAZARD, label="hazardous")
    ax.set_title("Close approaches by estimated diameter")
    ax.set_xlabel("Diameter bin (m, 1000 = 1000+)")
    ax.set_ylabel("Approaches")
    ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def hazard_by_size():
    df = _q("SELECT size_band, hazardous_share_pct FROM mart_hazard_summary ORDER BY size_band")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(df["size_band"], df["hazardous_share_pct"], color=HAZARD)
    ax.set_title("Hazardous share rises with size")
    ax.set_ylabel("% potentially hazardous")
    ax.tick_params(axis="x", rotation=20)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def daily_approaches():
    df = _q("SELECT date, approaches, hazardous_count FROM mart_daily_neo ORDER BY date")
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(df["date"], df["approaches"], color="#2C7FB8", linewidth=1.6, label="approaches")
    ax.plot(df["date"], df["hazardous_count"], color=HAZARD, linewidth=1.6, label="hazardous")
    ax.set_title("Daily close approaches")
    ax.set_ylabel("Count")
    ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def size_vs_distance():
    df = _q(
        "SELECT est_diameter_mean_m, miss_distance_km, is_potentially_hazardous "
        "FROM mart_close_approach_risk"
    )
    haz = df[df["is_potentially_hazardous"]]
    safe = df[~df["is_potentially_hazardous"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(safe["est_diameter_mean_m"], safe["miss_distance_km"], s=10, color=SAFE,
               alpha=0.5, label="not hazardous")
    ax.scatter(haz["est_diameter_mean_m"], haz["miss_distance_km"], s=22, color=HAZARD,
               alpha=0.85, edgecolor="white", linewidth=0.3, label="potentially hazardous")
    ax.axvline(140, color="#888", linestyle=":", linewidth=1)
    ax.text(140, ax.get_ylim()[1], " 140 m", color="#888", va="top", fontsize=9)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Estimated diameter (m, log)")
    ax.set_ylabel("Miss distance (km, log)")
    ax.set_title("NEO size vs close-approach distance")
    ax.legend(frameon=False, loc="lower left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def risk_top(n: int = 12):
    df = _q(f"SELECT name, risk_score FROM mart_risk_ranking ORDER BY risk_score DESC LIMIT {n}").iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(df["name"], df["risk_score"], color=HAZARD)
    ax.set_title(f"Top {n} close approaches by composite risk score")
    ax.set_xlabel("Risk score (0-100)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def interactive_scatter():
    try:
        import plotly.express as px
    except ImportError:
        return None
    df = _q(
        "SELECT name, est_diameter_mean_m, miss_distance_km, relative_velocity_kmh, "
        "risk_score, is_potentially_hazardous FROM mart_close_approach_risk"
    )
    df["Hazardous"] = df["is_potentially_hazardous"].map(
        {True: "Potentially hazardous", False: "Not hazardous"}
    )
    fig = px.scatter(
        df, x="est_diameter_mean_m", y="miss_distance_km", color="Hazardous", size="risk_score",
        hover_name="name", log_x=True, log_y=True,
        color_discrete_map={"Potentially hazardous": HAZARD, "Not hazardous": SAFE},
        labels={"est_diameter_mean_m": "Diameter (m)", "miss_distance_km": "Miss distance (km)"},
        title="NEO close approaches: size vs distance (bubble = risk score)",
    )
    fig.update_layout(template="plotly_white")
    return fig


def render_all(settings: Settings) -> dict:
    PATHS.figures.mkdir(parents=True, exist_ok=True)
    figs = {
        "size_distribution": size_distribution(),
        "hazard_by_size": hazard_by_size(),
        "daily_approaches": daily_approaches(),
        "size_vs_distance": size_vs_distance(),
        "risk_top": risk_top(),
    }
    saved = []
    for name, fig in figs.items():
        fig.savefig(PATHS.figures / f"{name}.png", dpi=130, bbox_inches="tight")
        plt.close(fig)
        saved.append(f"{name}.png")

    scatter = interactive_scatter()
    if scatter is not None:
        scatter.write_html(PATHS.figures / "size_vs_distance.html", include_plotlyjs="cdn")
        saved.append("size_vs_distance.html")

    log.info("rendered %d figures -> %s", len(saved), PATHS.figures)
    return {"figures": saved}
