import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_23_post_credentials_ready_credential_revalidation_design_only import (  # noqa: E402
    main as phase823_main,
)
from validate_phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only import (  # noqa: E402
    main as phase824_main,
)
from validate_phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only import (  # noqa: E402
    main as phase825_main,
)
from phase8_post_credentials_ready_pack_common import (  # noqa: E402
    validate_post_credentials_ready_design_phase,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase823_normal():
    assert phase823_main() == 0
    payload = _load(ROOT / "exchange/logs/phase8_23_post_credentials_ready_credential_revalidation_design_only_result.json")
    assert payload["final_status"] == "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_attempted"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["wordpress_draft_created"] is False
    assert payload["production_status"] == "NO_GO"


def test_phase824_normal():
    assert phase824_main() == 0
    payload = _load(ROOT / "exchange/logs/phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_result.json")
    assert payload["final_status"] == "DESIGN_ONLY_FINAL_EXECUTION_AUTHORIZATION_SPEC_READY_NO_EXECUTION"
    assert payload["approve_draft_create_only_currently_allowed"] is False
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_attempted"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["wordpress_draft_created"] is False


def test_phase825_normal():
    assert phase825_main() == 0
    payload = _load(ROOT / "exchange/logs/phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only_result.json")
    assert payload["final_status"] == "DESIGN_ONLY_ONE_SHOT_LOCK_ROLLBACK_EVIDENCE_SPEC_READY_NO_EXECUTION"
    assert payload["lock_created"] is False
    assert payload["rollback_executed"] is False
    assert payload["post_run_verification_executed"] is False
    assert payload["execution_allowed"] is False


def _tmp_case(
    tmp_path: Path,
    policy_name: str,
    request_name: str,
    pass_status: str,
    design_flags: dict,
    policy_patch: dict | None = None,
    request_patch: dict | None = None,
    phase816_status: str | None = None,
):
    src_policy = ROOT / "config" / policy_name
    src_request = ROOT / "exchange/examples" / request_name
    policy = _load(src_policy)
    request = _load(src_request)
    if policy_patch:
        policy.update(policy_patch)
    if request_patch:
        request.update(request_patch)

    p = tmp_path / "config" / "policy.json"
    r = tmp_path / "exchange" / "examples" / "request.json"
    out = tmp_path / "exchange" / "logs" / "result.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    r.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(policy), encoding="utf-8")
    r.write_text(json.dumps(request), encoding="utf-8")

    for rel in [
        "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json",
        "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json",
        "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json",
        "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json",
        "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json",
    ]:
        src = ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    if phase816_status is not None:
        result_path = (
            tmp_path
            / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json"
        )
        report_path = (
            tmp_path
            / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json"
        )
        result = _load(result_path)
        result.update(
            {
                "final_status": phase816_status,
                "credentials_ready": False,
                "missing_credential_keys": [
                    "WORDPRESS_BASE_URL",
                    "WORDPRESS_USERNAME",
                    "WORDPRESS_APP_PASSWORD",
                ],
            }
        )
        result_path.write_text(
            json.dumps(result),
            encoding="utf-8",
        )

        report = _load(report_path)
        report["final_status"] = phase816_status
        report["credentials_ready"] = False
        for credential in report.get("credentials", []):
            credential.update(
                {
                    "present": False,
                    "non_empty": False,
                    "status": "NOT_READY",
                }
            )
        report_path.write_text(
            json.dumps(report),
            encoding="utf-8",
        )

    return validate_post_credentials_ready_design_phase(
        policy_path=p,
        request_path=r,
        output_json_path=out,
        pass_status=pass_status,
        next_step_default="next",
        design_flags=copy.deepcopy(design_flags),
    )


def test_required_false_flag_true_abort(tmp_path):
    payload = _tmp_case(
        tmp_path,
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_policy.json",
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_request.example.json",
        "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION",
        {
            "credential_revalidation_design_only": True,
            "final_execution_authorization_design_only": False,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
        policy_patch={"execution_allowed": True},
    )
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"
    assert payload["execution_allowed"] is False


def test_missing_evidence_abort(tmp_path):
    payload = _tmp_case(
        tmp_path,
        "phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_policy.json",
        "phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_request.example.json",
        "DESIGN_ONLY_FINAL_EXECUTION_AUTHORIZATION_SPEC_READY_NO_EXECUTION",
        {
            "credential_revalidation_design_only": False,
            "final_execution_authorization_design_only": True,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
    )
    # Remove an evidence file and rerun
    missing_target = tmp_path / "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json"
    missing_target.unlink(missing_ok=True)
    payload = validate_post_credentials_ready_design_phase(
        policy_path=tmp_path / "config/policy.json",
        request_path=tmp_path / "exchange/examples/request.json",
        output_json_path=tmp_path / "exchange/logs/result2.json",
        pass_status="DESIGN_ONLY_FINAL_EXECUTION_AUTHORIZATION_SPEC_READY_NO_EXECUTION",
        next_step_default="next",
        design_flags={
            "credential_revalidation_design_only": False,
            "final_execution_authorization_design_only": True,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
    )
    assert payload["final_status"] == "ABORT_MISSING_EVIDENCE"
    assert payload["execution_allowed"] is False


@pytest.mark.parametrize(
    "dangerous_value",
    [
        "Authorization: Bearer dummy",
        "Basic abc",
        "password=dummy",
        "webhook=https://example.invalid",
    ],
)
def test_secret_like_value_abort(tmp_path, dangerous_value):
    payload = _tmp_case(
        tmp_path,
        "phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only_policy.json",
        "phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only_request.example.json",
        "DESIGN_ONLY_ONE_SHOT_LOCK_ROLLBACK_EVIDENCE_SPEC_READY_NO_EXECUTION",
        {
            "credential_revalidation_design_only": False,
            "final_execution_authorization_design_only": False,
            "one_shot_lock_design_only": True,
            "rollback_design_only": True,
            "post_run_evidence_design_only": True,
        },
        request_patch={"next_step_if_design_pass": dangerous_value},
    )
    assert payload["final_status"] == "ABORT_SECRET_LEAK_RISK"
    assert payload["execution_allowed"] is False


def test_safe_key_allowlist_no_false_positive(tmp_path):
    payload = _tmp_case(
        tmp_path,
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_policy.json",
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_request.example.json",
        "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION",
        {
            "credential_revalidation_design_only": True,
            "final_execution_authorization_design_only": False,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
    )
    assert payload["final_status"] == "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION"
    assert payload["secret_values_output"] is False
    assert payload["secret_values_written"] is False
    assert payload["secret_values_logged"] is False


def test_credentials_not_ready_does_not_fail_pack_logic(
    tmp_path,
    isolated_missing_credential_state,
):
    payload = _tmp_case(
        tmp_path,
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_policy.json",
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_request.example.json",
        "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION",
        {
            "credential_revalidation_design_only": True,
            "final_execution_authorization_design_only": False,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
        phase816_status=(
            "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"
        ),
    )
    assert payload["previous_phase8_16_final_status"] == "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"
    assert payload["final_status"] == "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_write_executed"] is False
    assert not isolated_missing_credential_state["path"].exists()
    assert isolated_missing_credential_state[
        "production_access_attempts"
    ] == []


def test_validator_does_not_leak_env_credentials(monkeypatch, tmp_path):
    secret = "VERY_SECRET_DUMMY_VALUE"
    monkeypatch.setenv("WP_APP_PASSWORD", secret)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.invalid/webhook/secret")

    payload = _tmp_case(
        tmp_path,
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_policy.json",
        "phase8_23_post_credentials_ready_credential_revalidation_design_only_request.example.json",
        "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION",
        {
            "credential_revalidation_design_only": True,
            "final_execution_authorization_design_only": False,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
    )

    dumped = json.dumps(payload, ensure_ascii=False)
    assert secret not in dumped
    assert "webhook/secret" not in dumped
    assert payload["final_status"] == "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION"
