from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_phase_sec_0_completion_report import build_report


def test_phase_sec_0_completion_report_passes_design_only() -> None:
    report = build_report()

    assert report["phase_id"] == "PHASE_SEC_0"
    assert report["status"] == "PASS_DESIGN_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["execution"] == "DRY_RUN"
    assert report["human_approval_required"] is True
    assert report["validation_status"] == "PASS"


def test_phase_sec_0_completion_report_restricts_dangerous_operations() -> None:
    report = build_report()
    restricted = report["restricted_operations"]

    assert restricted["wordpress_write"] == "NO_GO"
    assert restricted["wordpress_update"] == "NO_GO"
    assert restricted["wordpress_delete"] == "NO_GO"
    assert restricted["github_push"] == "NO_GO"
    assert restricted["external_api_execution"] == "NO_GO"
    assert restricted["automatic_recovery"] == "NO_GO"
    assert restricted["automatic_rollback"] == "NO_GO"
    assert restricted["vps_migration"] == "NO_GO"
    assert restricted["modify_env"] == "NO_GO"
    assert restricted["modify_secrets"] == "NO_GO"


def test_phase_sec_0_completion_report_has_next_candidates() -> None:
    report = build_report()

    assert "Phase-Sec 1 Emergency Freeze Flag Design" in report["next_candidates"]
    assert "Phase-Sec 6 Recovery Core Design" in report["next_candidates"]
