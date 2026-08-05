import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase7_5_freeze_or_live_decision_report import (
    build_report,
    build_md,
    run_report,
)

FILES = [
    "phase7_1_eligible_single_controlled_run_policy_result.json",
    "phase7_2_approve_draft_create_only_pre_unlock_review_result.json",
    "phase7_3_single_draft_final_preflight_design_result.json",
    "phase7_4_execution_gate_no_go_freeze_result.json",
]


def seed_policy(base: Path) -> Path:
    cfg = base / "config/phase7_5_freeze_or_live_decision_policy.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        json.dumps(
            {
                "phase": "Phase 7-5",
                "name": "freeze_or_live_decision_policy",
                "policy_status": "DESIGN_ONLY",
                "production_status": "NO_GO",
                "mode": "CONNECTION_TEST",
                "execution": "DRY_RUN",
                "human_approval_required": True,
                "wordpress_draft_creation": "NO_GO",
                "wordpress_write_executed": False,
                "publish_allowed": False,
                "approve_draft_create_only_currently_allowed": False,
                "unlock_in_this_phase": False,
                "live_is_execution_permission": False,
                "required_phase7_evidence": [f"exchange/logs/{f}" for f in FILES],
                "acceptable_statuses": [
                    "PASS",
                    "PASS_DESIGN_ONLY",
                    "ELIGIBLE_DRY_RUN_ONLY",
                    "PASS_DRY_RUN_ONLY",
                    "PASS_DRY_RUN_ONLY_WITH_WARN",
                ],
                "decision_outputs": {
                    "all_pass_but_unlock_not_allowed": "LIVE_CANDIDATE_BUT_LOCKED",
                    "any_missing_evidence": "FREEZE_MAINTAINED",
                    "any_fail_or_abort": "FREEZE_MAINTAINED",
                    "any_dangerous_flag_true": "ABORT",
                },
                "dangerous_operations": {
                    "auto_post": False,
                    "auto_update": False,
                    "auto_delete": False,
                    "auto_export": False,
                    "publish_allowed": False,
                    "wordpress_write_executed": False,
                    "wordpress_rest_api_post": False,
                    "wordpress_rest_api_put": False,
                    "wordpress_rest_api_patch": False,
                    "wordpress_rest_api_delete": False,
                    "bulk_execution": False,
                    "external_write": False,
                    "vps_self_builder_execution": False,
                },
                "allowed_next_step": "Phase 7-6 human approval evidence package design only",
                "blocked_next_steps": ["wordpress_draft_create"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return cfg


def seed_logs(logs_dir: Path, statuses: list[str] | None = None):
    logs_dir.mkdir(parents=True, exist_ok=True)
    values = statuses or [
        "ELIGIBLE_DRY_RUN_ONLY",
        "PASS_DESIGN_ONLY",
        "PASS_DESIGN_ONLY",
        "PASS_DESIGN_ONLY",
    ]
    for idx, fname in enumerate(FILES):
        (logs_dir / fname).write_text(json.dumps({"status": values[idx]}), encoding="utf-8")


def test_all_ok_live_candidate_but_locked():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        logs = base / "exchange/logs"
        seed_logs(logs)
        report = build_report(logs, policy)
        assert report["status"] == "LIVE_CANDIDATE_BUT_LOCKED"


def test_missing_evidence_freeze_maintained():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        logs = base / "exchange/logs"
        seed_logs(logs)
        (logs / FILES[0]).unlink()
        report = build_report(logs, policy)
        assert report["status"] == "FREEZE_MAINTAINED"


def test_abort_evidence_freeze_maintained():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        logs = base / "exchange/logs"
        seed_logs(logs, ["ELIGIBLE_DRY_RUN_ONLY", "ABORT", "PASS_DESIGN_ONLY", "PASS_DESIGN_ONLY"])
        report = build_report(logs, policy)
        assert report["status"] == "FREEZE_MAINTAINED"


def test_approve_flag_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        payload = json.loads(policy.read_text(encoding="utf-8"))
        payload["approve_draft_create_only_currently_allowed"] = True
        policy.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logs = base / "exchange/logs"
        seed_logs(logs)
        report = build_report(logs, policy)
        assert report["status"] == "ABORT"


def test_unlock_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        payload = json.loads(policy.read_text(encoding="utf-8"))
        payload["unlock_in_this_phase"] = True
        policy.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logs = base / "exchange/logs"
        seed_logs(logs)
        report = build_report(logs, policy)
        assert report["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        payload = json.loads(policy.read_text(encoding="utf-8"))
        payload["wordpress_write_executed"] = True
        policy.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logs = base / "exchange/logs"
        seed_logs(logs)
        report = build_report(logs, policy)
        assert report["status"] == "ABORT"


def test_publish_allowed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        payload = json.loads(policy.read_text(encoding="utf-8"))
        payload["publish_allowed"] = True
        policy.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logs = base / "exchange/logs"
        seed_logs(logs)
        report = build_report(logs, policy)
        assert report["status"] == "ABORT"


def test_dangerous_auto_post_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        payload = json.loads(policy.read_text(encoding="utf-8"))
        payload["dangerous_operations"]["auto_post"] = True
        policy.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logs = base / "exchange/logs"
        seed_logs(logs)
        report = build_report(logs, policy)
        assert report["status"] == "ABORT"


def test_run_report_writes_outputs():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy = seed_policy(base)
        logs = base / "exchange/logs"
        seed_logs(logs)
        out_json = base / "out.json"
        out_md = base / "out.md"
        report = run_report(logs, out_json, out_md, policy)
        saved = json.loads(out_json.read_text(encoding="utf-8"))
        assert out_md.exists()
        assert saved["status"] == "LIVE_CANDIDATE_BUT_LOCKED"
        assert saved["live_is_execution_permission"] is False
        assert "Phase 7-5 Freeze-or-Live Decision Report" in build_md(report)
