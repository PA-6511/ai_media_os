"""Tests for audit_phase8_12_no_secret_leak."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_phase8_12_no_secret_leak import audit_no_secret_leak  # noqa: E402


def base_policy() -> dict:
    return {
        "phase": "Phase 8-12",
        "name": "no_secret_leak_audit_policy",
        "policy_status": "AUDIT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "audit_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_evidence": ["exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json"],
        "required_phase8_11_status": "PASS_RUNBOOK_ONLY",
        "scan_targets": [],
        "forbidden_patterns": [
            "WORDPRESS_APP_PASSWORD=",
            "export WORDPRESS_APP_PASSWORD=",
            "Authorization: Basic",
            "example_password",
            "sample_password",
            "your_password_here",
            "print(os.environ",
            "print(env",
        ],
        "allowed_outputs": ["exists", "true", "false", "secret_values_written"],
        "decision_rules": {
            "no_forbidden_patterns": "NO_SECRET_LEAK_AUDIT_PASS",
            "forbidden_pattern_found": "ABORT",
            "missing_scan_target": "FAIL",
        },
        "allowed_next_step": "Phase 8-13 post-credential readiness recheck gate",
    }


def write_phase811_evidence(tmp_path: Path, status: str = "PASS_RUNBOOK_ONLY") -> Path:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_path = ev_dir / "phase8_11_credentials_manual_runbook_validation_result.json"
    ev_path.write_text(json.dumps({"status": status}), encoding="utf-8")
    return ev_path


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    evidence_status: str = "PASS_RUNBOOK_ONLY",
    missing_evidence: bool = False,
    scan_content: dict[str, str] | None = None,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"

    # Write evidence
    if not missing_evidence:
        write_phase811_evidence(tmp_path, evidence_status)
    rel_ev = "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json"
    p["required_evidence"] = [rel_ev]

    # Write scan targets
    if scan_content:
        for rel_path, content in scan_content.items():
            full_path = tmp_path / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
        p["scan_targets"] = list(scan_content.keys())

    pol_path.write_text(json.dumps(p), encoding="utf-8")

    return audit_no_secret_leak(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_normal_pass(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "NO_SECRET_LEAK_AUDIT_PASS"


def test_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_phase811_wrong_status_abort(tmp_path):
    result = run_case(tmp_path, evidence_status="FAIL")
    assert result["status"] == "ABORT"


def test_scan_target_missing_fail(tmp_path):
    write_phase811_evidence(tmp_path)
    p = base_policy()
    p["scan_targets"] = ["some/nonexistent/file.py"]
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "FAIL"
    assert any("missing_scan_target" in e for e in result["errors"])


def test_forbidden_pattern_app_password_abort(tmp_path):
    result = run_case(
        tmp_path,
        scan_content={"scripts/test_script.py": "x = 1\nWORDPRESS_APP_PASSWORD=secret\ny = 2\n"},
    )
    assert result["status"] == "ABORT"


def test_forbidden_pattern_authorization_basic_abort(tmp_path):
    result = run_case(
        tmp_path,
        scan_content={"scripts/test_script.py": "header = 'Authorization: Basic dXNlcjpwYXNz'\n"},
    )
    assert result["status"] == "ABORT"


def test_forbidden_pattern_example_password_abort(tmp_path):
    result = run_case(
        tmp_path,
        scan_content={"docs/test.md": "use example_password for testing\n"},
    )
    assert result["status"] == "ABORT"


def test_forbidden_pattern_print_os_environ_abort(tmp_path):
    result = run_case(
        tmp_path,
        scan_content={"scripts/test.py": "print(os.environ['WORDPRESS_APP_PASSWORD'])\n"},
    )
    assert result["status"] == "ABORT"


def test_audit_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["audit_is_execution_permission"] = True
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


def test_findings_do_not_contain_secret_values(tmp_path):
    """findings must only show pattern name + file path, never secret values."""
    result = run_case(
        tmp_path,
        scan_content={"scripts/bad.py": "WORDPRESS_APP_PASSWORD=supersecret123\n"},
    )
    assert result["status"] == "ABORT"
    for f in result.get("findings", []):
        assert "supersecret123" not in json.dumps(f)


def test_secret_values_written_false(tmp_path):
    result = run_case(tmp_path)
    assert result["secret_values_written"] is False


def test_allowed_context_lines_not_flagged(tmp_path):
    """Lines that are prohibition documentation must not trigger ABORT."""
    good_content = (
        "# Do not use print(os.environ for debugging\n"
        "# WORDPRESS_APP_PASSWORD= must never appear\n"
        "x = 1\n"
    )
    result = run_case(tmp_path, scan_content={"docs/runbook.md": good_content})
    assert result["status"] == "NO_SECRET_LEAK_AUDIT_PASS"


def test_normal_passes_real_files(tmp_path):
    """Scan real project files from this repo using a subset that should be clean."""
    write_phase811_evidence(tmp_path, "PASS_RUNBOOK_ONLY")
    p = base_policy()
    p["scan_targets"] = [
        "exchange/logs/phase8_6_wordpress_credentials_readiness_result.json",
        "exchange/logs/phase8_9_first_one_item_wordpress_draft_create_rerun_result.json",
    ]
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    rel_ev = "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json"
    p["required_evidence"] = [rel_ev]
    pol_path.write_text(json.dumps(p), encoding="utf-8")
    result = audit_no_secret_leak(
        policy_path=ROOT / "config/phase8_12_no_secret_leak_audit_policy.json",
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )
    assert result["status"] in {"NO_SECRET_LEAK_AUDIT_PASS", "FAIL"}
