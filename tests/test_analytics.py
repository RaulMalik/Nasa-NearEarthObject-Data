import numpy as np
import pandas as pd

from neoflow.analytics.anomaly import _rule_reasons
from neoflow.analytics.risk import _minmax


def test_minmax_scales_to_unit():
    out = _minmax(np.array([0.0, 5.0, 10.0]))
    assert out[0] == 0.0 and out[-1] == 1.0 and abs(out[1] - 0.5) < 1e-9


def test_minmax_constant_is_zero():
    assert (_minmax(np.array([3.0, 3.0, 3.0])) == 0).all()


def test_anomaly_rules_flag_known():
    df = pd.DataFrame(
        {
            "est_diameter_mean_m": [100.0, 2000.0, 50.0, 50.0],
            "miss_distance_lunar": [10.0, 10.0, 0.5, 10.0],
            "relative_velocity_kmh": [5e4, 5e4, 5e4, 2e5],
        }
    )
    r = _rule_reasons(df)
    assert r.iloc[0] == ""
    assert "very_large" in r.iloc[1]
    assert "very_close" in r.iloc[2]
    assert "very_fast" in r.iloc[3]
