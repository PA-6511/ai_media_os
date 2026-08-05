"""Tests for generate_phase8_23_pre_rerun_safety_snapshot."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_23_pre_rerun_safety_snapshot import (  # noqa: E402
    generate_pre_rerun_safety_snapshot,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-23",
        "name": "pre_rerun_safety_snapshot_policy",
        "policy_status": "SNAPSHOT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "snapshot_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_21_manual_credential_completion_checklist_result.json",
            "exchange/logs/phase8_22_credential_ready_path_switch_result.json",
        ],
        "required_phase8_21_status": "PASS_CHECKLIST_ONLY",
        "ready_status": "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
        "not_ready_status": "CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS",
        "snapshot_required_flags": {
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
        "allowed_next_step": "Phase 8-24 operator GO/NO-GO decision for manual rerun sequence",
    }


def _write_evidence(
    tmp_path: Path,
    p821: str = "PASS_CHECKLIST_ONLY",
    p822: str = "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
    secret_values_written: bool = False,
) -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_21_manual_credential_completion_checklist_result.json").write_text(
        json.dumps({"status": p821, "secret_values_written": secret_values_written}), encoding="utf-8"
    )
    (ev_dir / "phase8_22_credential_ready_path_switch_result.json").write_text(
        json.dumps({"status": p822, "secret_values_written": secret_values_written}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    p821: str = "PASS_CHECKLIST_ONLY",
    p822: str = "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
    missing_evidence: bool = False,
    secret_values_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")
    if not missing_evidence:
        _write_evidence(tmp_path, p821, p822, secret_values_written)

    return generate_pre_rerun_safety_snapshot(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED"


def test_not_ready_credentials_status(tmp_path):
    result = run_case(tmp_path, p822="CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS")
    assert result["status"] == "SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING"


def test_evidence_missing_status(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "SAFETY_SNAPSHOT_NOT_READY"


def test_evidence_abort_status_abort(tmp_path):
    result = run_case(tmp_path, p822="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_abort(tmp_path):
    result = run_case(tmp_path, secret_values_written=True)
    assert result["status"] == "ABORT"


def test_snapshot_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["snapshot_is_execution_permission"] = True
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
    p["snapshot_required_flags"]["auto_post"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"
