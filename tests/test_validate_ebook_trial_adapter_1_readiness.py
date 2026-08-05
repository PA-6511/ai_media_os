import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_ebook_trial_adapter_1_readiness import validate


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_gap_found_for_current_proposal_shape(tmp_path: Path):
    request = tmp_path / "exchange/examples/adapter_req.json"
    output = tmp_path / "exchange/logs/adapter_result.json"

    _write(
        request,
        {
            "proposals": [
                {
                    "source": "ebook_affiliate_block",
                    "action": "generate_article",
                    "title": "人気ファンタジー漫画ランキング",
                    "target": "人気ファンタジー漫画ランキング",
                    "priority": 0.68,
                    "reason": "人気ジャンル",
                    "metadata": {
                        "genre": "ファンタジー",
                        "work_title": "辺境ギルド運営録",
                        "opportunity_type": "popular_genre",
                    },
                }
            ]
        },
    )

    result = validate(request_path=request, output_path=output)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_1_GAP_FOUND_BLOCKED_NO_EXECUTION"
    assert "affiliate_disclosure_present" in result["gap_items"]
    assert result["wordpress_write_executed"] is False
    assert result["executed_external_changes"] == 0


def test_ready_when_required_flags_present(tmp_path: Path):
    request = tmp_path / "exchange/examples/adapter_req.json"
    output = tmp_path / "exchange/logs/adapter_result.json"

    _write(
        request,
        {
            "proposals": [
                {
                    "title": "候補A",
                    "target": "候補A",
                    "reason": "検証用",
                    "priority": 0.9,
                    "target_item_selected": True,
                    "target_item_schema_valid": True,
                    "target_item_duplicate_check_passed": True,
                    "affiliate_disclosure_present": True,
                    "pr_label_present": True,
                    "cta_policy_checked": True,
                    "category_tag_policy_checked": True,
                }
            ]
        },
    )

    result = validate(request_path=request, output_path=output)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_1_READY_FOR_PREFLIGHT_CONTRACT_NO_EXECUTION"
    assert result["gap_items"] == []


def test_blocked_when_no_candidate(tmp_path: Path):
    request = tmp_path / "exchange/examples/adapter_req.json"
    output = tmp_path / "exchange/logs/adapter_result.json"
    _write(request, {"proposals": []})

    result = validate(request_path=request, output_path=output)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_1_BLOCKED_NO_CANDIDATE_NO_EXECUTION"
    assert result["candidate_count"] == 0


def test_safety_flags_stay_false(tmp_path: Path):
    request = tmp_path / "exchange/examples/adapter_req.json"
    output = tmp_path / "exchange/logs/adapter_result.json"
    _write(request, {"proposals": []})

    result = validate(request_path=request, output_path=output)
    for key in (
        "execution_allowed",
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "publish_allowed",
        "rollback_executed",
        "freeze_executed",
    ):
        assert result[key] is False
    assert result["executed_external_changes"] == 0
