"""Schema smoke-tests for generated affiliate block skeleton."""

from app.schemas import AFFILIATE_INPUT_SCHEMA, AFFILIATE_OUTPUT_SCHEMA


def test_input_schema_required_fields():
    required = {
        "source",
        "title",
        "asin",
        "url",
        "campaign_type",
        "risk_flags",
    }
    assert AFFILIATE_INPUT_SCHEMA["version"] == "affiliate_input_v1"
    assert required.issubset(set(AFFILIATE_INPUT_SCHEMA["required_fields"]))


def test_output_schema_fields():
    fields = {
        "article_candidate",
        "review_required",
        "affiliate_disclosure",
        "blocked_reason",
        "risk_flags",
    }
    assert AFFILIATE_OUTPUT_SCHEMA["version"] == "affiliate_candidate_v1"
    assert fields.issubset(set(AFFILIATE_OUTPUT_SCHEMA["fields"]))
