import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_7_manual_publish_immediate_pre_execution_go_freeze_decision_design_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_6() -> dict:
    return {
        "package_type": "phase10_6_manual_publish_pre_execution_confirmation_design_report",
        "phase": "Phase 10-6",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "pre_execution_confirmation_design": {
            "checklist_count": 10,
            "token_expiry_minutes": 30,
            "max_publish_count": 1,
            "target_scope": "draft_to_publish_only",
        },
    }


def _run(p10_6: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_6 = tdp / "p10_6.json"
        out_json = tdp / "p10_7.json"
        out_md = tdp / "p10_7.md"

        _write(i10_6, p10_6)

        result = generate_report(i10_6, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_7_pass_with_phase10_6_input():
    result, report, _ = _run(_base_10_6())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_7_design_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["go_freeze_decision_design"]["default_decision"] == "FREEZE_KEEP_NO_GO"


def test_phase10_7_aborts_when_phase10_6_not_pass():
    p10_6 = _base_10_6()
    p10_6["status"] = "ABORT"

    result, report, _ = _run(p10_6)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_7_aborts_when_decision_mismatch():
    p10_6 = _base_10_6()
    p10_6["current_decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, report, _ = _run(p10_6)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_7_aborts_when_publish_candidate_unlocked_true():
    p10_6 = _base_10_6()
    p10_6["publish_candidate_unlocked_for_operator"] = True

    result, report, _ = _run(p10_6)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_7_aborts_on_draft_mismatch():
    p10_6 = _base_10_6()
    p10_6["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_6)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_7_generates_markdown_on_pass():
    _, report, md = _run(_base_10_6())

    assert report["status"] == "PASS"
    assert "Phase 10-7" in md
    assert "FREEZE_KEEP_NO_GO" in md
    assert "GO_PUBLISH_ONE_TIME_MANUAL_ONLY" in md
    assert "NO_GO" in md
