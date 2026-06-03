"""Typed, file-driven configuration for the NEO platform."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "settings.yaml"


class IngestConfig(BaseModel):
    source: str = "live"
    api_base: str = "https://api.nasa.gov/neo/rest/v1/feed"
    chunk_days: int = 7


class WindowConfig(BaseModel):
    start: str = "2024-01-01"
    end: str = "2024-07-01"


class CleaningConfig(BaseModel):
    max_miss_distance_lunar: float = 200.0


class RiskConfig(BaseModel):
    w_size: float = 0.40
    w_proximity: float = 0.35
    w_velocity: float = 0.15
    w_hazard: float = 0.10


class AnomalyConfig(BaseModel):
    contamination: float = 0.02


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEO_",
        env_file=str(ROOT / ".env"),
        env_nested_delimiter="__",
        extra="ignore",
    )

    project_name: str = "nasa-neo-risk-platform"
    nasa_api_key: str = Field(
        "DEMO_KEY", validation_alias=AliasChoices("NASA_API_KEY", "NEO_NASA_API_KEY")
    )
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    window: WindowConfig = Field(default_factory=WindowConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)


class Paths:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.data = root / "data"
        self.raw = self.data / "raw"
        self.staged = self.data / "staged"
        self.marts = self.data / "marts"
        self.exports = root / "exports"
        self.bi = self.exports / "bi"
        self.figures = self.exports / "figures"
        self.reports = root / "reports"
        self.quality = self.reports / "data_quality"
        self.warehouse = self.exports / "warehouse.duckdb"
        self.sql = root / "sql"

    def ensure(self) -> Paths:
        for p in (self.raw, self.staged, self.marts, self.bi, self.figures, self.quality):
            p.mkdir(parents=True, exist_ok=True)
        return self


PATHS = Paths()


def _load_yaml(path: Path) -> dict:
    if path.exists():
        with open(path) as fh:
            return yaml.safe_load(fh) or {}
    return {}


@lru_cache(maxsize=8)
def get_settings(config_path: str | None = None) -> Settings:
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    return Settings(**_load_yaml(path))
