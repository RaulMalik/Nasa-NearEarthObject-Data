from __future__ import annotations

try:
    from pandera.pandas import Check, Column, DataFrameSchema
except ModuleNotFoundError:  # pandera < 0.20
    from pandera import Check, Column, DataFrameSchema


def approaches_schema() -> DataFrameSchema:
    return DataFrameSchema(
        {
            "neo_id": Column(str, nullable=False),
            "name": Column(str, nullable=False),
            "absolute_magnitude_h": Column(float, Check.in_range(5, 40), nullable=True, coerce=True),
            "est_diameter_min_m": Column(float, Check.gt(0), coerce=True),
            "est_diameter_max_m": Column(float, Check.gt(0), coerce=True),
            "est_diameter_mean_m": Column(float, Check.gt(0), coerce=True),
            "is_potentially_hazardous": Column(bool, coerce=True),
            "is_sentry_object": Column(bool, coerce=True),
            "close_approach_date": Column("datetime64[ns]", nullable=False, coerce=True),
            "relative_velocity_kmh": Column(float, Check.gt(0), coerce=True),
            "miss_distance_km": Column(float, Check.gt(0), coerce=True),
            "miss_distance_lunar": Column(float, Check.ge(0), coerce=True),
        },
        strict=False,
        coerce=True,
    )
