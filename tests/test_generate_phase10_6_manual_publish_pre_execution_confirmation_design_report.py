import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_6_manual_publish_pre_execution_confirmation_design_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_5() -> dict:
    return {
        "package_type": "phase10_5_manual_unlock_candidate_execution_guard_design_report",
        "phase": "Phase 10-5",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "execution_guard_design": {
            "target_scope": "draft_to_publish_only",
            "token_expiry_minutes": 30,
            "max_publish_count": 1,
            "relock_required_after_attempt": True,
            "execution_guard_checks_count": 5,
        },
    }


def _run(p10_5: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_5 = tdp / "p10_5.json"
        out_json = tdp / "p10_6.json"
        out_md = tdp / "p10_6.md"

        _write(i10_5, p10_5)

        result = generate_report(i10_5, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_6_pass_with_phase10_5_input():
    result, report, _ = _run(_base_10_5())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_6_design_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["pre_execution_confirmation_design"]["checklist_count"] == 10


def test_phase10_6_aborts_when_phase10_5_not_pass():
    p10_5 = _base_10_5()
    p10_5["status"] = "ABORT"

    result, report, _ = _run(p10_5)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_6_aborts_when_decision_mismatch():
    p10_5 = _base_10_5()
    p10_5["current_decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, report, _ = _run(p10_5)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_6_aborts_when_publish_candidate_unlocked_true():
    p10_5 = _base_10_5()
    p10_5["publish_candidate_unlocked_for_operator"] = True

    result, report, _ = _run(p10_5)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_6_aborts_on_draft_mismatch():
    p10_5 = _base_10_5()
    p10_5["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_5)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_6_generates_markdown_on_pass():
    _, report, md = _run(_base_10_5())

    assert report["status"] == "PASS"
    assert "Phase 10-6" in md
    assert "checklist_count: 10" in md
    assert "NO_GO" in md
    assert "draft_to_publish_only" in md
