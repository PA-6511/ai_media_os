from generic_block_ai.app.affiliate_practical_schema import (
    evaluate_affiliate_candidate_quality,
    validate_affiliate_candidate_outputs,
    validate_affiliate_input_records,
)


def test_validate_affiliate_input_records_pass() -> None:
    records = [
        {
            "source": "official_api",
            "title": "Item A",
            "asin": "B0PASS0001",
            "url": "https://example.com/item/a",
            "campaign_type": "standard",
            "risk_flags": [],
        }
    ]
    result = validate_affiliate_input_records(records)
    assert result.result == "PASS"


def test_validate_affiliate_input_records_fail_missing_fields() -> None:
    records = [{"source": "official_api", "title": "Item A"}]
    result = validate_affiliate_input_records(records)
    assert result.result == "FAIL"
    assert any("required" in c for c in result.failed_checks)


def test_validate_affiliate_candidate_outputs_pass() -> None:
    candidates = [
        {
            "article_candidate": {
                "title": "Item A",
                "summary": "Draft",
                "source": "official_api",
                "asin": "B0PASS0001",
                "url": "https://example.com/item/a",
                "campaign_type": "standard",
            },
            "review_required": False,
            "affiliate_disclosure": "This content may include affiliate links.",
            "blocked_reason": None,
            "risk_flags": [],
        }
    ]
    result = validate_affiliate_candidate_outputs(candidates)
    assert result.result == "PASS"


def test_validate_affiliate_candidate_outputs_fail_bad_type() -> None:
    candidates = [
        {
            "article_candidate": "not-object",
            "review_required": "yes",
            "affiliate_disclosure": "disclosure",
            "blocked_reason": None,
            "risk_flags": [],
        }
    ]
    result = validate_affiliate_candidate_outputs(candidates)
    assert result.result == "FAIL"
    assert any("article_candidate" in c for c in result.failed_checks)


def test_evaluate_affiliate_candidate_quality_warn_with_risk() -> None:
    candidates = [
        {
            "article_candidate": {
                "title": "Item B",
                "summary": "Draft",
                "source": "approved_feed",
                "asin": "B0WARN0002",
                "url": "https://example.com/item/b",
                "campaign_type": "standard",
            },
            "review_required": True,
            "affiliate_disclosure": "This content may include affiliate links.",
            "blocked_reason": None,
            "risk_flags": ["price_volatility"],
        }
    ]
    result = evaluate_affiliate_candidate_quality(candidates)
    assert result.status == "WARN"
    assert result.summary["warn_count"] == 1


def test_evaluate_affiliate_candidate_quality_abort_on_policy_violation() -> None:
    candidates = [
        {
            "article_candidate": {
                "title": "Risk Item",
                "summary": "Draft",
                "source": "unknown_feed",
                "asin": "B0ABRT0003",
                "url": "https://example.com/item/risk",
                "campaign_type": "standard",
            },
            "review_required": True,
            "affiliate_disclosure": "This content may include affiliate links.",
            "blocked_reason": None,
            "risk_flags": ["policy_violation"],
        }
    ]
    result = evaluate_affiliate_candidate_quality(candidates)
    assert result.status == "ABORT"
    assert result.summary["abort_count"] == 1
