"""Runner smoke-tests for generated affiliate block skeleton."""

from app.runner import run_affiliate_block_dryrun


def test_runner_returns_dry_run_human_review():
    result = run_affiliate_block_dryrun({"task_candidates": [{"id": 1}, {"id": 2}]})
    assert result["status"] == "success"
    assert result["decision"] == "human_review"
    assert result["mode"] == "dry_run"
    assert result["operation_mode"] == "OBSERVE"


def test_runner_preserves_safeguards_false():
    result = run_affiliate_block_dryrun({})
    assert result["safeguards"]["actual_auto_execute"] is False
    assert result["safeguards"]["actual_auto_approve"] is False
    assert result["safeguards"]["external_write_executed"] is False
    assert result["safeguards"]["production_release"] is False


def test_runner_supports_practical_records_schema():
    result = run_affiliate_block_dryrun(
        {
            "records": [
                {
                    "source": "official_api",
                    "title": "Sample Product",
                    "asin": "B000TEST01",
                    "url": "https://example.com/p/1",
                    "campaign_type": "seasonal",
                    "risk_flags": [],
                }
            ]
        }
    )
    assert result["input_schema"]["version"] == "affiliate_input_v1"
    assert result["output_schema"]["version"] == "affiliate_candidate_v1"
    assert len(result["affiliate_candidates"]) == 1
    assert "article_candidate" in result["affiliate_candidates"][0]
