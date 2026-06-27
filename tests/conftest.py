from datetime import date, timedelta

import numpy as np
import pytest

from neoflow.config import Settings
from neoflow.ingest.synthetic import _neo


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def raw_chunks(settings):
    rng = np.random.default_rng(3)
    start = date.fromisoformat(settings.window.start)
    neo_by_date = {}
    for k in range(20):
        day = (start + timedelta(days=k)).isoformat()
        neo_by_date[day] = [_neo(rng, k * 5 + i, day) for i in range(5)]
    return [{"element_count": 100, "near_earth_objects": neo_by_date}]
