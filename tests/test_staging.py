from neoflow.staging.clean import _flatten, clean_frame


def test_flatten_columns(raw_chunks):
    df = _flatten(raw_chunks)
    assert len(df) == 100
    for col in ("neo_id", "est_diameter_mean_m", "miss_distance_km",
                "relative_velocity_kmh", "is_potentially_hazardous"):
        assert col in df.columns


def test_clean_filters(raw_chunks, settings):
    df = _flatten(raw_chunks)
    df.loc[0, "est_diameter_mean_m"] = None
    df.loc[1, "miss_distance_lunar"] = 9999.0
    out = clean_frame(df, settings)
    assert out["est_diameter_mean_m"].notna().all()
    assert (out["miss_distance_lunar"] <= settings.cleaning.max_miss_distance_lunar).all()
    assert out["close_approach_date"].notna().all()
    assert len(out) < len(df)
