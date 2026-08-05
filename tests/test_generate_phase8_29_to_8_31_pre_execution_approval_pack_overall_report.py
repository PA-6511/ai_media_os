import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, check=True, env=env)


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("WORDPRESS_BASE_URL", None)
    env.pop("WORDPRESS_USERNAME", None)
    env.pop("WORDPRESS_APP_PASSWORD", None)
    return env


def test_overall_pack_credentials_ready():
    env = _base_env()
    env["WORDPRESS_BASE_URL"] = "https://example.invalid"
    env["WORDPRESS_USERNAME"] = "operator"
    env["WORDPRESS_APP_PASSWORD"] = "dummy-secret-value"

    _run(["python3", str(ROOT / "scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py")], env=env)
    _run(["python3", str(ROOT / "scripts/validate_phase8_30_final_preflight_before_single_controlled_draft_creation.py")], env=env)
    _run(["python3", str(ROOT / "scripts/validate_phase8_31_human_execution_approval_validation_handoff.py")], env=env)
    _run(["python3", str(ROOT / "scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py")], env=env)

    report_json = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert payload["pack_status"] == "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_READY_NO_EXECUTION"
    assert payload["credentials_ready"] is True
    assert payload["all_no_execution"] is True
    assert payload["all_no_secret_leak"] is True


def test_overall_pack_credentials_not_ready():
    env = _base_env()
    _run(["python3", str(ROOT / "scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py")], env=env)
    _run(["python3", str(ROOT / "scripts/validate_phase8_30_final_preflight_before_single_controlled_draft_creation.py")], env=env)
    _run(["python3", str(ROOT / "scripts/validate_phase8_31_human_execution_approval_validation_handoff.py")], env=env)
    _run(["python3", str(ROOT / "scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py")], env=env)

    report_json = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert payload["pack_status"] == "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert payload["credentials_not_ready"] is True
    assert payload["all_no_execution"] is True


def test_overall_pack_not_pass_when_one_phase_aborts():
    source = ROOT / "exchange/logs/phase8_29_credential_readiness_recheck_no_secret_leak_gate_result.json"
    if not source.exists():
        _run(["python3", str(ROOT / "scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py")])
    original = source.read_text(encoding="utf-8")
    try:
        payload = json.loads(original)
        payload["final_status"] = "ABORT_POLICY_VIOLATION"
        source.write_text(json.dumps(payload), encoding="utf-8")

        proc = subprocess.run(
            ["python3", str(ROOT / "scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py")],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0

        report_json = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
        report_payload = json.loads(report_json.read_text(encoding="utf-8"))
        assert not report_payload["pack_status"].startswith("PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS")
    finally:
        source.write_text(original, encoding="utf-8")


def test_reports_do_not_include_secret_values():
    secret = "TOP_SECRET_SAMPLE_123"
    env = _base_env()
    env["WORDPRESS_BASE_URL"] = "https://example.invalid"
    env["WORDPRESS_USERNAME"] = "operator"
    env["WORDPRESS_APP_PASSWORD"] = secret

    _run(["python3", str(ROOT / "scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py")], env=env)
    _run(["python3", str(ROOT / "scripts/validate_phase8_30_final_preflight_before_single_controlled_draft_creation.py")], env=env)
    _run(["python3", str(ROOT / "scripts/validate_phase8_31_human_execution_approval_validation_handoff.py")], env=env)
    _run(["python3", str(ROOT / "scripts/generate_phase8_29_credential_readiness_recheck_no_secret_leak_gate_report.py")], env=env)
    _run(["python3", str(ROOT / "scripts/generate_phase8_30_final_preflight_before_single_controlled_draft_creation_report.py")], env=env)
    _run(["python3", str(ROOT / "scripts/generate_phase8_31_human_execution_approval_validation_handoff_report.py")], env=env)
    _run(["python3", str(ROOT / "scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py")], env=env)

    report_json = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
    report_md = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.md"
    content_json = report_json.read_text(encoding="utf-8")
    content_md = report_md.read_text(encoding="utf-8")

    assert secret not in content_json
    assert secret not in content_md


def test_markdown_contains_required_lines():
    _run(["python3", str(ROOT / "scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_30_final_preflight_before_single_controlled_draft_creation.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_31_human_execution_approval_validation_handoff.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py")])

    report_md = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.md"
    md = report_md.read_text(encoding="utf-8")
    assert "Phase 8-29〜8-31" in md
    assert "credential recheck" in md
    assert "final preflight" in md
    assert "human execution approval" in md
    assert "WordPress API call not executed" in md
    assert "WordPress write not executed" in md
    assert "draft creation not executed" in md
    assert "production remains NO_GO" in md
