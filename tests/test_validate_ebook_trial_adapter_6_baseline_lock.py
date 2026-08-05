import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_ebook_trial_adapter_6_baseline_lock import validate


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/ebook_trial_adapter_6_baseline_lock_policy.json")
    request = _load(ROOT / "exchange/examples/ebook_trial_adapter_6_baseline_lock_request.example.json")

    for key, rel in list(policy["required_reports"].items()):
        if key == "adapter1":
            policy["required_reports"][key] = "exchange/logs/a1.json"
        elif key == "adapter2":
            policy["required_reports"][key] = "exchange/logs/a2.json"
        elif key == "adapter3":
            policy["required_reports"][key] = "exchange/logs/a3.json"
        elif key == "adapter4":
            policy["required_reports"][key] = "exchange/logs/a4.json"
        elif key == "adapter5":
            policy["required_reports"][key] = "exchange/logs/a5.json"
        elif key == "adapter5_mapped_request":
            policy["required_reports"][key] = "exchange/logs/a5_mapped.json"

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"

    _write(policy_path, policy)
    _write(request_path, request)

    false_flags = {
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
    }

    _write(
        tmp_path / "exchange/logs/a1.json",
        {
            "status": "EBOOK_TRIAL_ADAPTER_1_GAP_FOUND_BLOCKED_NO_EXECUTION",
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/a2.json",
        {
            "status": "EBOOK_TRIAL_ADAPTER_2_MISSING_FIELD_COMPLETION_DESIGN_PASS_DRY_RUN",
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/a3.json",
        {
            "status": "EBOOK_TRIAL_ADAPTER_3_COMPLETION_PAYLOAD_BUILT_DRY_RUN_NO_EXECUTION",
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/a4.json",
        {
            "status": "EBOOK_TRIAL_ADAPTER_4_PREFLIGHT_CONTRACT_PASS_DRY_RUN_NO_EXECUTION",
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/a5.json",
        {
            "status": "EBOOK_TRIAL_ADAPTER_5_PHASE8_38_REQUEST_MAPPING_PASS_DRY_RUN_NO_EXECUTION",
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/a5_mapped.json",
        {
            "mode": "CONNECTION_TEST",
            "execution": "DRY_RUN",
            "production_status": "NO_GO",
            **false_flags,
        },
    )

    return policy_path, request_path, output_path


def test_pass_when_all_reports_and_statuses_match(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "EBOOK_TRIAL_ADAPTER_6_BASELINE_LOCK_PASS_HOLD_NO_EXECUTION"
    assert result["baseline_locked"] is True
    assert result["hold_state"] == "HOLD"


def test_abort_when_report_missing(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    (tmp_path / "exchange/logs/a3.json").unlink(missing_ok=True)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "EBOOK_TRIAL_ADAPTER_6_ABORT_MISSING_EVIDENCE_NO_EXECUTION"
    assert "adapter3" in result["missing_reports"]


def test_abort_when_status_mismatch(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    bad = _load(tmp_path / "exchange/logs/a4.json")
    bad["status"] = "BAD_STATUS"
    _write(tmp_path / "exchange/logs/a4.json", bad)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_6_ABORT_STATUS_MISMATCH_NO_EXECUTION"
    assert any(x.startswith("adapter4:") for x in result["status_mismatches"])


def test_no_execution_invariants_true_on_pass(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["no_go_invariants_ok"] is True
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
