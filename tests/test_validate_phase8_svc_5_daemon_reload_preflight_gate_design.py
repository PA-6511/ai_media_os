import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_svc_5_daemon_reload_preflight_gate_design import (  # noqa: E402
    validate_daemon_reload_preflight_design,
)


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_policy() -> dict:
    return {
        "design_only": True,
        "required_runbook_sections": [
            "## 1. Purpose",
            "## 3. Preconditions",
            "## 12. Next Step",
        ],
        "forbidden_patterns": [
            "systemctl daemon-reload",
            "systemctl start",
            "requests.post(",
            "wp-json",
        ],
        "activation_actions": {
            "daemon_reload_executed": False,
            "systemctl_enable_executed": False,
            "systemctl_start_executed": False,
            "systemctl_restart_executed": False,
        },
        "execution_actions": {
            "credential_env_created": False,
            "secret_input_executed": False,
            "phase8_29_to_8_40_rerun_executed": False,
            "wordpress_api_call_attempted": False,
            "wordpress_draft_created": False,
            "wordpress_publish_executed": False,
        },
        "allowed_next_step": "NEXT",
    }


def _good_runbook() -> str:
    return """# Phase 8-SVC-5: Daemon-Reload Preflight Gate Design

## 1. Purpose
Design only.

## 3. Preconditions
SVC-3 and SVC-4 should pass.

## 12. Next Step
Proceed to SVC-6.
"""


def test_pass(tmp_path: Path):
    policy = tmp_path / "config/policy.json"
    runbook = tmp_path / "docs/runbook.md"
    output = tmp_path / "exchange/logs/result.json"
    _write_json(policy, _base_policy())
    runbook.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text(_good_runbook(), encoding="utf-8")

    result = validate_daemon_reload_preflight_design(policy, runbook, output)
    assert result["status"] == "PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK"


def test_fail_missing_section(tmp_path: Path):
    policy = tmp_path / "config/policy.json"
    runbook = tmp_path / "docs/runbook.md"
    output = tmp_path / "exchange/logs/result.json"
    _write_json(policy, _base_policy())
    runbook.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text("## 1. Purpose\nOnly\n", encoding="utf-8")

    result = validate_daemon_reload_preflight_design(policy, runbook, output)
    assert result["status"] == "FAIL"
    assert result["missing_sections"]


def test_fail_policy_violation(tmp_path: Path):
    policy = _base_policy()
    policy["activation_actions"]["daemon_reload_executed"] = True

    policy_path = tmp_path / "config/policy.json"
    runbook = tmp_path / "docs/runbook.md"
    output = tmp_path / "exchange/logs/result.json"
    _write_json(policy_path, policy)
    runbook.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text(_good_runbook(), encoding="utf-8")

    result = validate_daemon_reload_preflight_design(policy_path, runbook, output)
    assert result["status"] == "FAIL"
    assert any("daemon_reload_executed" in item for item in result["policy_violations"])


def test_abort_forbidden_executable_line(tmp_path: Path):
    policy_path = tmp_path / "config/policy.json"
    runbook = tmp_path / "docs/runbook.md"
    output = tmp_path / "exchange/logs/result.json"
    _write_json(policy_path, _base_policy())
    runbook.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text(_good_runbook() + "\nsystemctl daemon-reload\n", encoding="utf-8")

    result = validate_daemon_reload_preflight_design(policy_path, runbook, output)
    assert result["status"] == "ABORT"
    assert result["forbidden_hits"]
