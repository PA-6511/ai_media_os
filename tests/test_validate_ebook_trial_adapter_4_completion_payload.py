import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_ebook_trial_adapter_4_completion_payload import validate


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/ebook_trial_adapter_4_completion_payload_validation_policy.json")
    request = _load(ROOT / "exchange/examples/ebook_trial_adapter_4_completion_payload_validation_request.example.json")

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"
    adapter3_path = tmp_path / "exchange/logs/ebook_trial_adapter_3_completion_payload_builder_result.json"

    policy["adapter3_evidence_path"] = "exchange/logs/ebook_trial_adapter_3_completion_payload_builder_result.json"

    adapter3_payload = {
        "status": "EBOOK_TRIAL_ADAPTER_3_COMPLETION_PAYLOAD_BUILT_DRY_RUN_NO_EXECUTION",
        "completion_payload": {
            "title": "人気ファンタジー漫画ランキング",
            "target": "人気ファンタジー漫画ランキング",
            "reason": "人気ジャンル",
            "target_item_schema": {
                "schema_version": "trial_target_item_v1",
                "is_valid": True,
            },
            "duplicate_check": {
                "checked": True,
                "passed": True,
                "method": "dry_run_stub",
            },
            "target_item_selected": True,
            "target_item_schema_valid": True,
            "target_item_duplicate_check_passed": True,
            "affiliate_disclosure_present": True,
            "pr_label_present": True,
            "cta_policy_checked": True,
            "category_tag_policy_checked": True,
        },
    }

    _write(policy_path, policy)
    _write(request_path, request)
    _write(adapter3_path, adapter3_payload)
    return policy_path, request_path, output_path, adapter3_path


def test_pass_when_payload_matches_contract(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "EBOOK_TRIAL_ADAPTER_4_PREFLIGHT_CONTRACT_PASS_DRY_RUN_NO_EXECUTION"
    assert result["missing_contract_fields"] == []
    assert result["false_contract_flags"] == []


def test_blocked_when_contract_flag_false(tmp_path: Path):
    policy_path, request_path, output_path, adapter3_path = _prepare_case(tmp_path)
    payload = _load(adapter3_path)
    payload["completion_payload"]["pr_label_present"] = False
    _write(adapter3_path, payload)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_4_BLOCKED_CONTRACT_MISMATCH_NO_EXECUTION"
    assert "pr_label_present" in result["false_contract_flags"]


def test_abort_when_adapter3_evidence_missing(tmp_path: Path):
    policy_path, request_path, output_path, adapter3_path = _prepare_case(tmp_path)
    adapter3_path.unlink(missing_ok=True)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_4_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert "adapter3_evidence_missing" in result["policy_violations"]


def test_no_execution_flags_remain_false(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

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
