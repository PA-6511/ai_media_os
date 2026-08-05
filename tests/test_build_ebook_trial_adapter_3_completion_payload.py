import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_ebook_trial_adapter_3_completion_payload import build


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/ebook_trial_adapter_3_completion_payload_builder_policy.json")
    request = _load(ROOT / "exchange/examples/ebook_trial_adapter_3_completion_payload_builder_request.example.json")

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"
    adapter2_path = tmp_path / "exchange/logs/ebook_trial_adapter_2_missing_field_completion_design_result.json"

    policy["adapter2_evidence_path"] = "exchange/logs/ebook_trial_adapter_2_missing_field_completion_design_result.json"

    _write(policy_path, policy)
    _write(request_path, request)
    _write(adapter2_path, {"status": "EBOOK_TRIAL_ADAPTER_2_MISSING_FIELD_COMPLETION_DESIGN_PASS_DRY_RUN"})
    return policy_path, request_path, output_path, adapter2_path


def test_builds_completion_payload_in_dry_run(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)

    result = build(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_3_COMPLETION_PAYLOAD_BUILT_DRY_RUN_NO_EXECUTION"
    assert result["payload_generated"] is True

    payload = result["completion_payload"]
    assert payload["target_item_selected"] is True
    assert payload["target_item_schema_valid"] is True
    assert payload["target_item_duplicate_check_passed"] is True
    assert payload["affiliate_disclosure_present"] is True
    assert payload["pr_label_present"] is True
    assert payload["cta_policy_checked"] is True
    assert payload["category_tag_policy_checked"] is True


def test_abort_when_adapter2_evidence_missing(tmp_path: Path):
    policy_path, request_path, output_path, adapter2_path = _prepare_case(tmp_path)
    adapter2_path.unlink(missing_ok=True)

    result = build(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_3_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert "adapter2_evidence_missing" in result["policy_violations"]
    assert result["payload_generated"] is False


def test_abort_when_safety_flag_true(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)
    request = _load(request_path)
    request["wordpress_write_allowed"] = True
    _write(request_path, request)

    result = build(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_3_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert any("wordpress_write_allowed" in v for v in result["policy_violations"])


def test_no_execution_invariants_always_false(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)

    result = build(policy_path=policy_path, request_path=request_path, output_path=output_path)
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
