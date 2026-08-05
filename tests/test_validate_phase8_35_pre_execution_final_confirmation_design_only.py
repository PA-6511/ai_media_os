import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_35_pre_execution_final_confirmation_design_only import validate_phase8_35  # noqa: E402


PHASE2931 = "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
PHASE3234 = "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prepare_case(tmp_path: Path, *, patch_2931: dict | None = None, patch_3234: dict | None = None, patch_request: dict | None = None, patch_policy: dict | None = None):
    policy = _load(ROOT / "config/phase8_35_pre_execution_final_confirmation_design_only_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_35_pre_execution_final_confirmation_design_only_request.example.json")
    if patch_policy:
        policy.update(patch_policy)
    if patch_request:
        request.update(patch_request)

    phase2931 = _load(ROOT / PHASE2931)
    phase3234 = _load(ROOT / PHASE3234)
    if patch_2931:
        phase2931.update(patch_2931)
    if patch_3234:
        phase3234.update(patch_3234)

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / PHASE2931).parent.mkdir(parents=True, exist_ok=True)

    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")
    (tmp_path / PHASE2931).write_text(json.dumps(phase2931), encoding="utf-8")
    (tmp_path / PHASE3234).write_text(json.dumps(phase3234), encoding="utf-8")

    return validate_phase8_35(
        policy_path=policy_path,
        request_path=request_path,
        output_json_path=output_path,
    )


def test_normal_stop_when_credentials_not_ready(tmp_path):
    payload = _prepare_case(tmp_path)
    assert payload["phase8_29_to_8_31_pack_status"] == "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert payload["phase8_32_to_8_34_pack_status"] == "PHASE8_32_TO_8_34_ONE_SHOT_EXECUTION_GATE_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
    assert payload["credentials_not_ready"] is True
    assert payload["stop_required"] is True
    assert payload["final_status"] == "PRE_EXECUTION_FINAL_CONFIRMATION_STOP_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_attempted"] is False
    assert payload["wordpress_write_executed"] is False


def test_ready_still_no_execution(tmp_path):
    payload = _prepare_case(
        tmp_path,
        patch_2931={
            "pack_status": "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_READY_NO_EXECUTION",
            "credentials_ready": True,
            "credentials_not_ready": False,
        },
    )
    assert payload["credentials_ready"] is True
    assert payload["credentials_not_ready"] is False
    assert payload["stop_required"] is False
    assert payload["final_status"] == "PRE_EXECUTION_FINAL_CONFIRMATION_READY_FOR_PHASE8_36_DRY_RUN_HANDOFF_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_draft_created"] is False


def test_abort_when_gate_pack_not_pass(tmp_path):
    payload = _prepare_case(
        tmp_path,
        patch_3234={"pack_status": "ABORT_POLICY_VIOLATION"},
    )
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_abort_when_previous_pack_unknown(tmp_path):
    payload = _prepare_case(
        tmp_path,
        patch_2931={"pack_status": "UNKNOWN"},
    )
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_missing_evidence_abort(tmp_path):
    payload = _prepare_case(tmp_path)
    missing = tmp_path / PHASE3234
    missing.unlink(missing_ok=True)

    payload = validate_phase8_35(
        policy_path=tmp_path / "config/policy.json",
        request_path=tmp_path / "exchange/examples/request.json",
        output_json_path=tmp_path / "exchange/logs/result_rerun.json",
    )
    assert payload["final_status"] == "ABORT_MISSING_EVIDENCE"


@pytest.mark.parametrize(
    "dangerous_value",
    [
        "Authorization: Bearer dummy",
        "Basic abc",
        "password=dummy",
        "webhook=https://example.invalid",
    ],
)
def test_secret_leak_abort(tmp_path, dangerous_value):
    payload = _prepare_case(
        tmp_path,
        patch_request={"next_step_if_credentials_not_ready": dangerous_value},
    )
    assert payload["final_status"] == "ABORT_SECRET_LEAK_RISK"


def test_request_safety_flag_true_abort(tmp_path):
    payload = _prepare_case(
        tmp_path,
        patch_request={"wordpress_api_call_attempted": True},
    )
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_safe_value_no_false_positive(tmp_path):
    payload = _prepare_case(
        tmp_path,
        patch_request={"next_step_if_credentials_ready": "phase8_36_one_shot_draft_creation_dry_run_handoff"},
    )
    assert payload["final_status"] == "PRE_EXECUTION_FINAL_CONFIRMATION_STOP_CREDENTIALS_NOT_READY_NO_EXECUTION"
