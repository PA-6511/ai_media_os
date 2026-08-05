import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def test_overall_pack_pass_and_markdown_contents():
    _run(["python3", str(ROOT / "scripts/validate_phase8_23_post_credentials_ready_credential_revalidation_design_only.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only.py")])

    _run(["python3", str(ROOT / "scripts/generate_phase8_23_post_credentials_ready_credential_revalidation_design_only_report.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_report.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only_report.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.py")])

    report_json = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json"
    report_md = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.md"

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["pack_status"] == "PHASE8_23_TO_8_25_POST_CREDENTIALS_READY_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
    assert payload["all_design_only"] is True
    assert payload["all_no_execution"] is True
    assert payload["all_no_secret_leak"] is True

    md = report_md.read_text(encoding="utf-8")
    assert "Phase 8-23〜8-25" in md
    assert "DESIGN_ONLY" in md
    assert "WordPress API call not executed" in md
    assert "WordPress write not executed" in md
    assert "draft creation not executed" in md
    assert "production remains NO_GO" in md


def test_overall_pack_not_pass_when_one_phase_aborts(tmp_path):
    source = ROOT / "exchange/logs/phase8_23_post_credentials_ready_credential_revalidation_design_only_result.json"
    if not source.exists():
        _run(["python3", str(ROOT / "scripts/validate_phase8_23_post_credentials_ready_credential_revalidation_design_only.py")])
    original = source.read_text(encoding="utf-8")
    try:
        payload = json.loads(original)
        payload["final_status"] = "ABORT_POLICY_VIOLATION"
        source.write_text(json.dumps(payload), encoding="utf-8")

        proc = subprocess.run(
            ["python3", str(ROOT / "scripts/generate_phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.py")],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0

        report_json = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json"
        report_payload = json.loads(report_json.read_text(encoding="utf-8"))
        assert report_payload["pack_status"] != "PHASE8_23_TO_8_25_POST_CREDENTIALS_READY_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
    finally:
        source.write_text(original, encoding="utf-8")


def test_overall_report_does_not_include_secret_values(monkeypatch):
    secret = "TOP_SECRET_SAMPLE_123"
    monkeypatch.setenv("WP_APP_PASSWORD", secret)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.invalid/webhook/super-secret")

    _run(["python3", str(ROOT / "scripts/validate_phase8_23_post_credentials_ready_credential_revalidation_design_only.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.py")])

    report_json = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json"
    report_md = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.md"

    content_json = report_json.read_text(encoding="utf-8")
    content_md = report_md.read_text(encoding="utf-8")
    assert secret not in content_json
    assert secret not in content_md
    assert "webhook/super-secret" not in content_json
    assert "webhook/super-secret" not in content_md
