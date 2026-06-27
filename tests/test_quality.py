import pytest
from pandera.errors import SchemaError, SchemaErrors

from neoflow.quality.schemas import approaches_schema
from neoflow.staging.clean import _flatten, clean_frame


def test_contract_passes(raw_chunks, settings):
    df = clean_frame(_flatten(raw_chunks), settings)
    approaches_schema().validate(df)


def test_contract_fails(raw_chunks, settings):
    df = clean_frame(_flatten(raw_chunks), settings)
    df.loc[df.index[:5], "est_diameter_mean_m"] = -1.0
    with pytest.raises((SchemaError, SchemaErrors)):
        approaches_schema().validate(df)
