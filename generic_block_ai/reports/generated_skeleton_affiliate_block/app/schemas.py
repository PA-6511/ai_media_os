"""Practical input/output schemas for generated affiliate block skeleton."""

AFFILIATE_INPUT_SCHEMA = {
    "version": "affiliate_input_v1",
    "required_fields": [
        "source",
        "title",
        "asin",
        "url",
        "campaign_type",
        "risk_flags",
    ],
}

AFFILIATE_OUTPUT_SCHEMA = {
    "version": "affiliate_candidate_v1",
    "fields": [
        "article_candidate",
        "review_required",
        "affiliate_disclosure",
        "blocked_reason",
        "risk_flags",
    ],
}
