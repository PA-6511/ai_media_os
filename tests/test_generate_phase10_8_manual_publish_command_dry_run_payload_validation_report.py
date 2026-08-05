import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_8_manual_publish_command_dry_run_payload_validation_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_7() -> dict:
    return {
        "package_type": "phase10_7_manual_publish_immediate_pre_execution_go_freeze_decision_design_report",
        "phase": "Phase 10-7",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "go_freeze_decision_design": {
            "default_decision": "FREEZE_KEEP_NO_GO",
            "token_expiry_minutes": 30,
            "max_publish_count": 1,
            "decision_checks_count": 6,
        },
    }


def _run(p10_7: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_7 = tdp / "p10_7.json"
        out_json = tdp / "p10_8.json"
        out_md = tdp / "p10_8.md"

        _write(i10_7, p10_7)

        result = generate_report(i10_7, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_8_pass_with_phase10_7_input():
    result, report, _ = _run(_base_10_7())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_8_design_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["dry_run_payload_validation_design"]["dry_run_only"] is True


def test_phase10_8_aborts_when_phase10_7_not_pass():
    p10_7 = _base_10_7()
    p10_7["status"] = "ABORT"

    result, report, _ = _run(p10_7)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_8_aborts_when_decision_mismatch():
    p10_7 = _base_10_7()
    p10_7["current_decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, report, _ = _run(p10_7)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_8_aborts_when_publish_candidate_unlocked_true():
    p10_7 = _base_10_7()
    p10_7["publish_candidate_unlocked_for_operator"] = True

    result, report, _ = _run(p10_7)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_8_aborts_on_draft_mismatch():
    p10_7 = _base_10_7()
    p10_7["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_7)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_8_generates_markdown_on_pass():
    _, report, md = _run(_base_10_7())

    assert report["status"] == "PASS"
    assert "Phase 10-8" in md
    assert "dry_run" in md
    assert "manual_publish_single_draft" in md
    assert "NO_GO" in md
