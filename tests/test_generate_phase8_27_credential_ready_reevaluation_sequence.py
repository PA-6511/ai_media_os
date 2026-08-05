"""Tests for generate_phase8_27_credential_ready_reevaluation_sequence."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_27_credential_ready_reevaluation_sequence import (  # noqa: E402
    generate_credential_ready_reevaluation_sequence,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-27",
        "name": "credential_ready_reevaluation_sequence_policy",
        "policy_status": "REEVALUATION_PLAN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "reevaluation_plan_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "auto_post": False,
        "target_item_count": 1,
        "required_evidence": ["exchange/logs/phase8_26_credential_provisioned_declaration_result.json"],
        "ready_declaration_status": "CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        "not_ready_declaration_status": "CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
        "planned_reevaluation_steps_if_ready": ["Phase 8-17 environment-only credential presence smoke check"],
        "planned_steps_if_not_ready": ["Keep NO_GO"],
        "forbidden_command_patterns": [
            "curl -X POST",
            "curl -u",
            "requests.post(",
            "wp post create",
            "wp-json/wp/v2/posts",
            "export WORDPRESS_APP_PASSWORD=",
            "WORDPRESS_APP_PASSWORD=",
        ],
        "allowed_next_step": "Phase 8-28 manual rerun dry command checklist",
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    evidence_status: str = "CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
    evidence_missing: bool = False,
    evidence_secret_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    if not evidence_missing:
        logs = tmp_path / "exchange" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "phase8_26_credential_provisioned_declaration_result.json").write_text(
            json.dumps({"status": evidence_status, "secret_values_written": evidence_secret_written}),
            encoding="utf-8",
        )

    return generate_credential_ready_reevaluation_sequence(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_provisioned_ready(tmp_path):
    result = run_case(tmp_path, evidence_status="CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT")
    assert result["status"] == "REEVALUATION_SEQUENCE_READY_BUT_NOT_EXECUTED"


def test_not_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "REEVALUATION_SEQUENCE_NOT_READY_CREDENTIALS_MISSING"


def test_evidence_missing_not_ready(tmp_path):
    result = run_case(tmp_path, evidence_missing=True)
    assert result["status"] == "REEVALUATION_SEQUENCE_NOT_READY"


def test_evidence_abort_abort(tmp_path):
    result = run_case(tmp_path, evidence_status="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_abort(tmp_path):
    result = run_case(tmp_path, evidence_secret_written=True)
    assert result["status"] == "ABORT"


def test_reevaluation_plan_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["reevaluation_plan_is_execution_permission"] = True
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


def test_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_planned_step_contains_curl_post_abort(tmp_path):
    p = base_policy()
    p["planned_reevaluation_steps_if_ready"] = ["curl -X POST https://example.com"]
    result = run_case(tmp_path, policy=p, evidence_status="CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT")
    assert result["status"] == "ABORT"


def test_planned_step_contains_password_assignment_abort(tmp_path):
    p = base_policy()
    p["planned_reevaluation_steps_if_ready"] = ["WORDPRESS_APP_PASSWORD=abc python3 x.py"]
    result = run_case(tmp_path, policy=p, evidence_status="CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT")
    assert result["status"] == "ABORT"
