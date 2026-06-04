import logging

from ..config import PATHS, Settings
from .nasa_api import ingest_live
from .synthetic import ingest_synthetic

log = logging.getLogger("neoflow.ingest")


def run_ingest(settings: Settings) -> dict:
    PATHS.ensure()
    if settings.ingest.source == "synthetic":
        return ingest_synthetic(settings)
    try:
        return ingest_live(settings)
    except Exception as exc:
        log.warning("live ingest failed (%s); falling back to synthetic", exc)
        return ingest_synthetic(settings)
