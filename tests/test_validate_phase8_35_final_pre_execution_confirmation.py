import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_35_final_pre_execution_confirmation import validate_phase8_35  # noqa: E402


P2931 = "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
P3234 = "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prepare(tmp_path: Path, patch_policy: dict | None = None, patch_request: dict | None = None, patch2931: dict | None = None, patch3234: dict | None = None):
    policy = _load(ROOT / "config/phase8_35_final_pre_execution_confirmation_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_35_final_pre_execution_confirmation_request.example.json")
    v2931 = _load(ROOT / P2931)
    v3234 = _load(ROOT / P3234)

    if patch_policy:
        policy.update(patch_policy)
    if patch_request:
        request.update(patch_request)
    if patch2931:
        v2931.update(patch2931)
    if patch3234:
        v3234.update(patch3234)

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / P2931).parent.mkdir(parents=True, exist_ok=True)

    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")
    (tmp_path / P2931).write_text(json.dumps(v2931), encoding="utf-8")
    (tmp_path / P3234).write_text(json.dumps(v3234), encoding="utf-8")

    return validate_phase8_35(policy_path=policy_path, request_path=request_path, output_json_path=output_path)


def test_credentials_ready_gate_pass(tmp_path):
    payload = _prepare(
        tmp_path,
        patch2931={
            "pack_status": "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_READY_NO_EXECUTION",
            "credentials_ready": True,
            "credentials_not_ready": False,
        },
    )
    assert payload["final_status"] == "PHASE8_35_FINAL_CONFIRMATION_READY_FOR_DRY_RUN_HANDOFF_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_attempted"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["wordpress_draft_created"] is False
    assert payload["next_step"] == "phase8_36_one_shot_draft_creation_dry_run_handoff"


def test_credentials_not_ready(tmp_path):
    payload = _prepare(tmp_path)
    assert payload["final_status"] == "PHASE8_35_FINAL_CONFIRMATION_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert payload["credentials_not_ready"] is True
    assert payload["execution_allowed"] is False
    assert payload["next_step"] == "stop_and_repeat_credential_provisioning_then_phase8_29_to_8_31"


def test_phase3234_missing_evidence(tmp_path):
    payload = _prepare(tmp_path)
    (tmp_path / P3234).unlink(missing_ok=True)
    payload = validate_phase8_35(
        policy_path=tmp_path / "config/policy.json",
        request_path=tmp_path / "exchange/examples/request.json",
        output_json_path=tmp_path / "exchange/logs/result2.json",
    )
    assert payload["final_status"] == "ABORT_MISSING_EVIDENCE"


def test_phase2931_missing_evidence(tmp_path):
    payload = _prepare(tmp_path)
    (tmp_path / P2931).unlink(missing_ok=True)
    payload = validate_phase8_35(
        policy_path=tmp_path / "config/policy.json",
        request_path=tmp_path / "exchange/examples/request.json",
        output_json_path=tmp_path / "exchange/logs/result3.json",
    )
    assert payload["final_status"] == "ABORT_MISSING_EVIDENCE"


def test_required_false_flags_true_abort(tmp_path):
    payload = _prepare(tmp_path, patch_policy={"execution_allowed": True})
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_production_status_not_nogo_abort(tmp_path):
    payload = _prepare(tmp_path, patch_request={"production_status": "GO"})
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_execution_not_dry_run_abort(tmp_path):
    payload = _prepare(tmp_path, patch_request={"execution": "LIVE"})
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_target_item_count_not_one_abort(tmp_path):
    payload = _prepare(tmp_path, patch_request={"target_item_count": 2})
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


@pytest.mark.parametrize(
    "dangerous_value",
    [
        "Authorization: Bearer dummy",
        "Basic abc",
        "password=dummy",
    ],
)
def test_secret_leak_risk_abort(tmp_path, dangerous_value):
    payload = _prepare(tmp_path, patch_request={"next_step_if_ready": dangerous_value})
    assert payload["final_status"] == "ABORT_SECRET_LEAK_RISK"


def test_no_secret_value_in_result_and_report(monkeypatch):
    secret = "TOP_SECRET_SAMPLE_123"
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", secret)
    payload = validate_phase8_35()
    dumped = json.dumps(payload, ensure_ascii=False)
    assert secret not in dumped

    import subprocess

    subprocess.run(["python3", str(ROOT / "scripts/generate_phase8_35_final_pre_execution_confirmation_report.py")], check=True)
    report_json = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.json"
    report_md = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.md"
    assert secret not in report_json.read_text(encoding="utf-8")
    assert secret not in report_md.read_text(encoding="utf-8")
