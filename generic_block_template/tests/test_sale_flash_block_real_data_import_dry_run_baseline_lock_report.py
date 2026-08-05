from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCK_ROOT = ROOT / "blocks/sale_flash_block"
SCRIPTS = BLOCK_ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_sfb11c_baseline_lock_pass(tmp_path: Path):
    lock = _load_module(
        "sfb11c_lock",
        SCRIPTS / "generate_real_data_import_dry_run_baseline_lock_report.py",
    )

    logs_dir = tmp_path / "logs"
    sfb11 = logs_dir / "real_sale_csv_import_report.json"
    sfb11b = logs_dir / "real_data_import_dry_run_evidence.json"
    sfb10b = logs_dir / "sale_flash_block_v1_pre_production_baseline_lock_report.json"

    _write_json(
        sfb11,
        {
            "status": "PASS",
            "phase": "SFB-11",
            "production_status": "NO_GO",
        },
    )
    _write_json(
        sfb11b,
        {
            "status": "PASS",
            "phase": "SFB-11B",
            "production_status": "NO_GO",
            "no_go_maintained": True,
            "fixture_diff": {"changed": True},
            "pipeline_dry_run": {
                "status": "PASS",
                "production_status": "NO_GO",
                "wordpress_write_executed": False,
                "external_api_called": False,
                "external_network_called": False,
            },
        },
    )
    _write_json(
        sfb10b,
        {
            "status": "PASS",
            "phase": "SFB-10B",
            "baseline_locked": True,
            "production_status": "NO_GO",
        },
    )

    policy = {
        "phase": "SFB-11C",
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "required_phase_logs": {
            "sfb11_real_data_import": str(sfb11),
            "sfb11b_real_data_evidence": str(sfb11b),
            "sfb10b_pre_production_baseline_lock": str(sfb10b),
        },
        "required_import_status": ["PASS", "WARN"],
        "required_evidence_status": ["PASS", "WARN"],
        "require_fixture_changed": True,
        "output_json": str(logs_dir / "sfb11c_report.json"),
        "output_markdown": str(logs_dir / "sfb11c_report.md"),
    }

    policy_path = tmp_path / "policy.json"
    _write_json(policy_path, policy)

    result = lock.generate_real_data_import_dry_run_baseline_lock_report(policy_json=policy_path)
    assert result["status"] == "PASS"
    assert result["phase"] == "SFB-11C"
    assert result["baseline_locked"] is True
    assert result["production_status"] == "NO_GO"


def test_sfb11c_baseline_lock_fail_when_evidence_missing(tmp_path: Path):
    lock = _load_module(
        "sfb11c_lock_fail",
        SCRIPTS / "generate_real_data_import_dry_run_baseline_lock_report.py",
    )

    logs_dir = tmp_path / "logs"
    sfb11 = logs_dir / "real_sale_csv_import_report.json"
    sfb10b = logs_dir / "sale_flash_block_v1_pre_production_baseline_lock_report.json"

    _write_json(
        sfb11,
        {
            "status": "PASS",
            "phase": "SFB-11",
            "production_status": "NO_GO",
        },
    )
    _write_json(
        sfb10b,
        {
            "status": "PASS",
            "phase": "SFB-10B",
            "baseline_locked": True,
            "production_status": "NO_GO",
        },
    )

    policy = {
        "phase": "SFB-11C",
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "required_phase_logs": {
            "sfb11_real_data_import": str(sfb11),
            "sfb11b_real_data_evidence": "logs/missing_evidence.json",
            "sfb10b_pre_production_baseline_lock": str(sfb10b),
        },
        "required_import_status": ["PASS", "WARN"],
        "required_evidence_status": ["PASS", "WARN"],
        "require_fixture_changed": True,
        "output_json": str(logs_dir / "sfb11c_report_fail.json"),
        "output_markdown": str(logs_dir / "sfb11c_report_fail.md"),
    }

    policy_path = tmp_path / "policy_fail.json"
    _write_json(policy_path, policy)

    result = lock.generate_real_data_import_dry_run_baseline_lock_report(policy_json=policy_path)
    assert result["status"] == "FAIL"
    assert result["baseline_locked"] is False
    assert "sfb11b_real_data_evidence" in result["checks"]["missing_reports"]
