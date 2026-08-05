import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase6_hardening_preflight_report import run_report


def base_config() -> dict:
    return {
        "phase": "Phase 6-9",
        "name": "phase6_hardening_preflight_gate",
        "gate_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "required_evidence": [
            "exchange/logs/phase6_5_execution_spec_validation_result.json",
            "exchange/logs/phase6_6_quality_gate_validation_result.json",
            "exchange/logs/phase6_7_slack_approval_dry_run_result.json",
            "exchange/logs/phase6_8_runbook_validation_result.json",
        ],
        "acceptable_statuses": ["PASS", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY_WITH_WARN"],
        "warn_statuses": ["WARN"],
        "reject_statuses": ["FAIL", "ABORT"],
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_write_executed": False,
            "bulk_execution": False,
            "vps_self_builder_execution": False,
        },
        "allowed_next_step": "Phase 7 design or ELIGIBLE single controlled run preparation only",
        "blocked_next_steps": ["auto_publish"],
    }


def create_files(root: Path, statuses: list[str]):
    paths = [
        root / "exchange/logs/phase6_5_execution_spec_validation_result.json",
        root / "exchange/logs/phase6_6_quality_gate_validation_result.json",
        root / "exchange/logs/phase6_7_slack_approval_dry_run_result.json",
        root / "exchange/logs/phase6_8_runbook_validation_result.json",
    ]
    for p, status in zip(paths, statuses):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"status": status}, ensure_ascii=False, indent=2), encoding="utf-8")


def write_config(root: Path, cfg: dict) -> Path:
    path = root / "config/phase6_hardening_preflight_gate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_all_pass_returns_pass_dry_run_only():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        write_config(root, cfg)
        create_files(root, ["PASS_DRY_RUN_ONLY", "PASS", "PASS_DRY_RUN_ONLY_WITH_WARN", "PASS_DRY_RUN_ONLY"])
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        import generate_phase6_hardening_preflight_report as mod
        old_root = mod.ROOT
        mod.ROOT = root
        try:
            result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        finally:
            mod.ROOT = old_root

        assert result["overall_status"] == "PASS_DRY_RUN_ONLY"


def test_warn_mixed_returns_pass_with_warn():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        write_config(root, cfg)
        create_files(root, ["PASS_DRY_RUN_ONLY", "WARN", "PASS_DRY_RUN_ONLY", "PASS"])
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        import generate_phase6_hardening_preflight_report as mod
        old_root = mod.ROOT
        mod.ROOT = root
        try:
            result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        finally:
            mod.ROOT = old_root

        assert result["overall_status"] == "PASS_DRY_RUN_ONLY_WITH_WARN"


def test_fail_mixed_returns_fail():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        write_config(root, cfg)
        create_files(root, ["PASS", "FAIL", "PASS", "PASS"])
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        import generate_phase6_hardening_preflight_report as mod
        old_root = mod.ROOT
        mod.ROOT = root
        try:
            result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        finally:
            mod.ROOT = old_root

        assert result["overall_status"] == "FAIL"


def test_abort_mixed_returns_abort():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        write_config(root, cfg)
        create_files(root, ["PASS", "ABORT", "PASS", "PASS"])
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        import generate_phase6_hardening_preflight_report as mod
        old_root = mod.ROOT
        mod.ROOT = root
        try:
            result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        finally:
            mod.ROOT = old_root

        assert result["overall_status"] == "ABORT"


def test_missing_evidence_returns_fail():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        write_config(root, cfg)
        create_files(root, ["PASS", "PASS", "PASS", "PASS"])
        (root / "exchange/logs/phase6_8_runbook_validation_result.json").unlink()
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        import generate_phase6_hardening_preflight_report as mod
        old_root = mod.ROOT
        mod.ROOT = root
        try:
            result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        finally:
            mod.ROOT = old_root

        assert result["overall_status"] == "FAIL"


def test_dangerous_operation_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        cfg["dangerous_operations"]["auto_post"] = True
        write_config(root, cfg)
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        assert result["overall_status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        cfg["wordpress_write_executed"] = True
        write_config(root, cfg)
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        assert result["overall_status"] == "ABORT"


def test_production_status_not_no_go_aborts():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = base_config()
        cfg["production_status"] = "GO"
        write_config(root, cfg)
        out_json = root / "exchange/logs/r.json"
        out_md = root / "exchange/logs/r.md"

        result = run_report(root / "config/phase6_hardening_preflight_gate.json", out_json, out_md)
        assert result["overall_status"] == "ABORT"
