"""Tests for generate_phase8_25_final_manual_rerun_handoff_package."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_25_final_manual_rerun_handoff_package import (  # noqa: E402
    generate_final_manual_rerun_handoff_package,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-25",
        "name": "final_manual_rerun_handoff_package_policy",
        "policy_status": "FINAL_HANDOFF_PACKAGE_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "handoff_package_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_21_manual_credential_completion_checklist_result.json",
            "exchange/logs/phase8_22_credential_ready_path_switch_result.json",
            "exchange/logs/phase8_23_pre_rerun_safety_snapshot.json",
            "exchange/logs/phase8_24_operator_go_no_go_result.json",
        ],
        "ready_statuses": {
            "phase8_21": "PASS_CHECKLIST_ONLY",
            "phase8_22": "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
            "phase8_23": "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED",
            "phase8_24": "OPERATOR_GO_RECORDED_FOR_HANDOFF_ONLY",
        },
        "blocked_statuses": [
            "CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS",
            "SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING",
            "OPERATOR_NO_GO_CREDENTIALS_MISSING",
        ],
        "planned_manual_commands_if_ready": [
            "python3 scripts/validate_phase8_6_wordpress_credentials_readiness.py"
        ],
        "forbidden_command_patterns": [
            "curl -X POST",
            "curl -u",
            "requests.post(",
            "wp post create",
            "wp-json/wp/v2/posts",
            "export WORDPRESS_APP_PASSWORD=",
            "WORDPRESS_APP_PASSWORD=",
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
            "commands_executed_in_this_phase": False,
        },
        "allowed_next_step_if_ready": "Human operator may manually rerun Phase 8-6 to Phase 8-10 commands exactly once",
        "allowed_next_step_if_blocked": "Keep NO_GO and do not rerun until credentials are ready",
    }


def _write_evidences(
    tmp_path: Path,
    p821: str = "PASS_CHECKLIST_ONLY",
    p822: str = "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
    p823: str = "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED",
    p824: str = "OPERATOR_GO_RECORDED_FOR_HANDOFF_ONLY",
    secret_values_written: bool = False,
) -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "phase8_21_manual_credential_completion_checklist_result.json": {"status": p821, "secret_values_written": secret_values_written},
        "phase8_22_credential_ready_path_switch_result.json": {"status": p822, "secret_values_written": secret_values_written},
        "phase8_23_pre_rerun_safety_snapshot.json": {"status": p823, "secret_values_written": secret_values_written},
        "phase8_24_operator_go_no_go_result.json": {"status": p824, "secret_values_written": secret_values_written},
    }
    for fname, payload in payloads.items():
        (ev_dir / fname).write_text(json.dumps(payload), encoding="utf-8")


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    p821: str = "PASS_CHECKLIST_ONLY",
    p822: str = "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
    p823: str = "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED",
    p824: str = "OPERATOR_GO_RECORDED_FOR_HANDOFF_ONLY",
    missing_evidence: bool = False,
    secret_values_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    if not missing_evidence:
        _write_evidences(tmp_path, p821, p822, p823, p824, secret_values_written)

    return generate_final_manual_rerun_handoff_package(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_all_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "READY_FOR_OPERATOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"


def test_credentials_missing_status(tmp_path):
    result = run_case(tmp_path, p822="CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS")
    assert result["status"] == "HANDOFF_BLOCKED_CREDENTIALS_MISSING"


def test_operator_no_go_status(tmp_path):
    result = run_case(tmp_path, p824="OPERATOR_NO_GO_CREDENTIALS_MISSING")
    assert result["status"] == "HANDOFF_BLOCKED_CREDENTIALS_MISSING"


def test_evidence_missing_status(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "HANDOFF_NOT_READY"


def test_evidence_abort_status(tmp_path):
    result = run_case(tmp_path, p823="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_abort(tmp_path):
    result = run_case(tmp_path, secret_values_written=True)
    assert result["status"] == "ABORT"


def test_handoff_package_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["handoff_package_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    p = base_policy()
    p["commands_executed_in_this_phase"] = True
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


def test_forbidden_curl_post_abort(tmp_path):
    p = base_policy()
    p["planned_manual_commands_if_ready"] = ["curl -X POST https://example.com"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_forbidden_password_assignment_abort(tmp_path):
    p = base_policy()
    p["planned_manual_commands_if_ready"] = ["WORDPRESS_APP_PASSWORD=abc python3 x.py"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_forbidden_wp_json_abort(tmp_path):
    p = base_policy()
    p["planned_manual_commands_if_ready"] = ["echo wp-json/wp/v2/posts"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"
