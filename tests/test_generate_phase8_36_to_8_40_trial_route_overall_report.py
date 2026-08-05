import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_phase8_36_to_8_40_trial_route_overall_report import generate_report


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _blocked_status(key: str) -> str:
    mapping = {
        "phase8_29_to_8_31": "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION",
        "phase8_35": "BLOCKED_CREDENTIALS_MISSING",
        "phase8_36": "PHASE8_36_DRY_RUN_HANDOFF_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION",
        "phase8_37": "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION",
        "phase8_38": "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION",
        "phase8_39": "PHASE8_39_ABORT_ROLLBACK_FREEZE_SIMULATION_PASS_NO_EXECUTION",
        "n1_n5": "N_SERIES_1_TO_5_OVERALL_PASS_DRY_RUN_ONLY",
        "n6_n10": "N6_TO_N10_SERIES_OVERALL_PASS_DRY_RUN_ONLY",
    }
    return mapping.get(key, "UNKNOWN")


def _ready_status(key: str) -> str:
    mapping = {
        "phase8_29_to_8_31": "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS",
        "phase8_35": "PHASE8_35_FINAL_READY_APPROVED_NO_EXECUTION",
        "phase8_36": "PHASE8_36_DRY_RUN_HANDOFF_READY_NO_EXECUTION",
        "phase8_37": "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION",
        "phase8_38": "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_READY_NO_EXECUTION",
        "phase8_39": "PHASE8_39_ABORT_ROLLBACK_FREEZE_SIMULATION_PASS_NO_EXECUTION",
        "n1_n5": "N_SERIES_1_TO_5_OVERALL_PASS_DRY_RUN_ONLY",
        "n6_n10": "N6_TO_N10_SERIES_OVERALL_PASS_DRY_RUN_ONLY",
    }
    return mapping.get(key, "PASS")


EVIDENCE_KEYS = [
    "phase8_29_to_8_31", "phase8_35", "phase8_36", "phase8_37",
    "phase8_38", "phase8_39", "n1_n5", "n6_n10",
]


def test_blocked_credentials(tmp_path: Path):
    evidence_paths = {}
    for key in EVIDENCE_KEYS:
        p = tmp_path / f"{key}.json"
        _write(p, {"status": _blocked_status(key)})
        evidence_paths[key] = p

    out_j = tmp_path / "report.json"
    out_m = tmp_path / "report.md"
    result = generate_report(evidence_paths, out_j, out_m)

    assert result["overall_status"] == "PHASE8_36_TO_8_40_TRIAL_ROUTE_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert result["ready_for_first_trial_execution"] is False
    assert result["production_status"] == "NO_GO"
    assert result["executed_external_changes"] == 0
    assert result["credentials_ready"] is False
    assert out_j.exists()
    assert out_m.exists()


def test_missing_evidence(tmp_path: Path):
    # Only provide some evidence, others missing
    evidence_paths: dict[str, Path] = {}
    for key in EVIDENCE_KEYS:
        evidence_paths[key] = tmp_path / f"MISSING_{key}.json"  # none exist

    out_j = tmp_path / "report.json"
    out_m = tmp_path / "report.md"
    result = generate_report(evidence_paths, out_j, out_m)

    assert "BLOCKED" in result["overall_status"]
    assert result["ready_for_first_trial_execution"] is False


def test_ready_case(tmp_path: Path):
    evidence_paths = {}
    for key in EVIDENCE_KEYS:
        p = tmp_path / f"{key}.json"
        _write(p, {"status": _ready_status(key)})
        evidence_paths[key] = p

    out_j = tmp_path / "report.json"
    out_m = tmp_path / "report.md"
    result = generate_report(evidence_paths, out_j, out_m)

    assert result["overall_status"] == "PHASE8_36_TO_8_40_TRIAL_ROUTE_READY_FOR_FIRST_ONE_ITEM_TRIAL_NO_EXECUTION"
    assert result["credentials_ready"] is True
    assert result["ready_for_first_trial_execution"] is False  # always False in DRY_RUN


def test_safety_flags(tmp_path: Path):
    evidence_paths = {}
    for key in EVIDENCE_KEYS:
        p = tmp_path / f"{key}.json"
        _write(p, {"status": _blocked_status(key)})
        evidence_paths[key] = p

    out_j = tmp_path / "report.json"
    out_m = tmp_path / "report.md"
    result = generate_report(evidence_paths, out_j, out_m)

    for key in (
        "wordpress_write_executed", "wordpress_draft_created",
        "rollback_executed", "freeze_executed",
        "slack_message_sent",
        "secret_values_output", "secret_lengths_output",
    ):
        assert result[key] is False, f"{key} should be False"
    assert result["executed_external_changes"] == 0
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"
