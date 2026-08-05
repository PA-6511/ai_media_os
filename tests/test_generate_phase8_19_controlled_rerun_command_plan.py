"""Tests for generate_phase8_19_controlled_rerun_command_plan."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_19_controlled_rerun_command_plan import (  # noqa: E402
    generate_controlled_rerun_command_plan,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-19",
        "name": "controlled_rerun_command_plan_policy",
        "policy_status": "COMMAND_PLAN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "command_plan_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": ["exchange/logs/phase8_18_rerun_readiness_transition_report.json"],
        "ready_status": "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED",
        "not_ready_statuses": [
            "RERUN_SEQUENCE_NOT_READY_CREDENTIALS_MISSING",
            "RERUN_SEQUENCE_NOT_READY",
        ],
        "planned_commands_if_ready": [
            "python3 scripts/validate_phase8_6_wordpress_credentials_readiness.py"
        ],
        "planned_commands_if_not_ready": [
            "python3 scripts/validate_phase8_13_post_credential_readiness_recheck.py"
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
        "allowed_next_step_if_ready": "Phase 8-20 final pre-rerun lock and handoff report",
        "allowed_next_step_if_not_ready": "Keep NO_GO and do not rerun Phase 8-6 to Phase 8-10",
    }


def _write_evidence(tmp_path: Path, p818: str = "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED") -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_18_rerun_readiness_transition_report.json").write_text(
        json.dumps({"status": p818}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    p818: str = "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED",
    missing_evidence: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    if not missing_evidence:
        _write_evidence(tmp_path, p818)

    return generate_controlled_rerun_command_plan(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "RERUN_COMMAND_PLAN_READY_BUT_NOT_EXECUTED"


def test_not_ready_credentials_status(tmp_path):
    result = run_case(tmp_path, p818="RERUN_SEQUENCE_NOT_READY_CREDENTIALS_MISSING")
    assert result["status"] == "RERUN_COMMAND_PLAN_NOT_READY_CREDENTIALS_MISSING"


def test_evidence_missing_not_ready_status(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "RERUN_COMMAND_PLAN_NOT_READY"


def test_command_plan_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["command_plan_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_commands_executed_in_this_phase_true_abort(tmp_path):
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


def test_forbidden_curl_post_abort(tmp_path):
    p = base_policy()
    p["planned_commands_if_ready"] = ["curl -X POST https://example.com"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_forbidden_wordpress_app_password_abort(tmp_path):
    p = base_policy()
    p["planned_commands_if_ready"] = ["WORDPRESS_APP_PASSWORD=abc python3 x.py"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_forbidden_wp_json_posts_abort(tmp_path):
    p = base_policy()
    p["planned_commands_if_ready"] = ["echo wp-json/wp/v2/posts"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"
