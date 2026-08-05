"""Tests for generate_phase8_18_rerun_readiness_transition_report."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_18_rerun_readiness_transition_report import (  # noqa: E402
    generate_rerun_readiness_transition_report,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-18",
        "name": "rerun_readiness_transition_policy",
        "policy_status": "TRANSITION_REPORT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "transition_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_16_credential_operator_confirmation_result.json",
            "exchange/logs/phase8_17_env_credential_presence_smoke_check_result.json",
        ],
        "ready_statuses": {
            "phase8_16": "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT",
            "phase8_17": "ENV_CREDENTIALS_PRESENT_NO_SECRET_OUTPUT",
        },
        "not_ready_statuses": [
            "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT",
            "ENV_CREDENTIALS_MISSING_NO_SECRET_OUTPUT",
        ],
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "allowed_next_step_if_ready": "Phase 8-19 controlled rerun command plan for Phase 8-6 to Phase 8-10",
        "allowed_next_step_if_not_ready": "Keep NO_GO, provision credentials manually, then rerun Phase 8-16",
    }


def _write_evidences(
    tmp_path: Path,
    p816: str = "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT",
    p817: str = "ENV_CREDENTIALS_PRESENT_NO_SECRET_OUTPUT",
    secret_values_written: bool = False,
) -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_16_credential_operator_confirmation_result.json").write_text(
        json.dumps({"status": p816, "secret_values_written": secret_values_written}),
        encoding="utf-8",
    )
    (ev_dir / "phase8_17_env_credential_presence_smoke_check_result.json").write_text(
        json.dumps({"status": p817, "secret_values_written": secret_values_written}),
        encoding="utf-8",
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    p816: str = "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT",
    p817: str = "ENV_CREDENTIALS_PRESENT_NO_SECRET_OUTPUT",
    missing_evidence: bool = False,
    secret_values_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    if not missing_evidence:
        _write_evidences(tmp_path, p816, p817, secret_values_written)

    return generate_rerun_readiness_transition_report(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_all_ready_status_ready(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED"


def test_operator_not_ready_status_not_ready_credentials(tmp_path):
    result = run_case(tmp_path, p816="CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "RERUN_SEQUENCE_NOT_READY_CREDENTIALS_MISSING"


def test_env_missing_status_not_ready_credentials(tmp_path):
    result = run_case(tmp_path, p817="ENV_CREDENTIALS_MISSING_NO_SECRET_OUTPUT")
    assert result["status"] == "RERUN_SEQUENCE_NOT_READY_CREDENTIALS_MISSING"


def test_evidence_missing_status_not_ready(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "RERUN_SEQUENCE_NOT_READY"


def test_evidence_abort_status_abort(tmp_path):
    result = run_case(tmp_path, p816="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_true_abort(tmp_path):
    result = run_case(tmp_path, secret_values_written=True)
    assert result["status"] == "ABORT"


def test_transition_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["transition_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_wordpress_api_call_allowed_true_abort(tmp_path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_abort(tmp_path):
    p = base_policy()
    p["wordpress_write_executed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_auto_post_true_abort(tmp_path):
    p = base_policy()
    p["dangerous_operations"]["auto_post"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"
