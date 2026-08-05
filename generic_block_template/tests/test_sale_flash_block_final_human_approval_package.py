from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCK_ROOT = ROOT / "blocks/sale_flash_block"
SCRIPTS = BLOCK_ROOT / "scripts"
CONFIG = BLOCK_ROOT / "config"
LOGS = BLOCK_ROOT / "logs"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sfb7_final_human_approval_package_generation():
    run = _load_module("sfb7_run", BLOCK_ROOT / "run.py")
    package = _load_module("sfb7_package", SCRIPTS / "generate_final_human_approval_package.py")

    policy = json.loads((CONFIG / "final_human_approval_package_policy.json").read_text(encoding="utf-8"))
    assert policy["phase"] == "SFB-7"
    assert policy["mode"] == "DRY_RUN"
    assert policy["production_status"] == "NO_GO"
    assert policy["wordpress_write_allowed"] is False

    run_result = run.run_block()
    assert run_result["status"] in {"PASS", "WARN"}

    payload = package.generate_final_human_approval_package()
    assert payload["status"] == "PASS"
    assert payload["phase"] == "SFB-7"
    assert payload["mode"] == "DRY_RUN"
    assert payload["production_status"] == "NO_GO"

    assert payload["baseline_locked"] is True
    assert payload["final_human_gate_status"] == "READY_FOR_FINAL_HUMAN_GATE"
    assert payload["human_approval_consumed"] is False
    assert payload["human_approval_unconsumed"] is True

    assert payload["wordpress_dry_run_execution_gate"] == "READY_FOR_DRY_RUN_ONLY"
    assert payload["production_write_blocked"] is True
    assert payload["decision"]["allow_wordpress_dry_run_execution"] is True
    assert payload["decision"]["allow_production_wordpress_write"] is False

    assert payload["external_api_called"] is False
    assert payload["external_network_called"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["publish_executed"] is False
    assert payload["update_executed"] is False
    assert payload["delete_executed"] is False
    assert payload["export_executed"] is False

    assert (LOGS / "final_human_approval_package.json").exists()
    assert (LOGS / "final_human_approval_package.md").exists()

    md_text = (LOGS / "final_human_approval_package.md").read_text(encoding="utf-8")
    assert "# Final Human Approval Package" in md_text
    assert "- production_status: NO_GO" in md_text
    assert "- wordpress_dry_run_execution_gate: READY_FOR_DRY_RUN_ONLY" in md_text
