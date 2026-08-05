import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase9_4_publish_go_redecision_no_go_maintenance_overall_report import generate_report


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_9_1() -> dict:
    return {
        "package_type": "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result",
        "phase": "Phase 9-1",
        "status": "PASS",
        "runbook_generated": True,
        "target_draft_id": 110,
        "target_draft_status": "draft",
        "decision": "KEEP_NO_GO",
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
    }


def _base_9_2() -> dict:
    return {
        "package_type": "phase9_2_publish_go_redecision_input_gate_result",
        "phase": "Phase 9-2",
        "status": "PASS",
        "decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "production_status": "NO_GO",
        "wordpress_publish_execution": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "publish_candidate_unlocked_for_operator": False,
    }


def _base_9_3() -> dict:
    return {
        "package_type": "phase9_3_keep_no_go_input_gate_completion_report",
        "phase": "Phase 9-3",
        "status": "PASS",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
    }


def _run(p91: dict, p92: dict, p93: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i91 = tdp / "p91.json"
        i92 = tdp / "p92.json"
        i93 = tdp / "p93.json"
        out_json = tdp / "p94.json"
        out_md = tdp / "p94.md"

        _write(i91, p91)
        _write(i92, p92)
        _write(i93, p93)

        result = generate_report(i91, i92, i93, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase9_4_pass_with_keep_no_go_inputs():
    result, report, _ = _run(_base_9_1(), _base_9_2(), _base_9_3())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase9_2_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["next_step"] == "maintain_no_go_or_manual_publish_go_redecision"


def test_phase9_4_aborts_when_phase9_2_decision_not_keep_no_go():
    p91 = _base_9_1()
    p92 = _base_9_2()
    p93 = _base_9_3()
    p92["decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, report, _ = _run(p91, p92, p93)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase9_4_aborts_when_publish_candidate_unlocked_true():
    p91 = _base_9_1()
    p92 = _base_9_2()
    p93 = _base_9_3()
    p92["publish_candidate_unlocked_for_operator"] = True

    result, report, _ = _run(p91, p92, p93)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase9_4_aborts_on_forbidden_true_flag():
    p91 = _base_9_1()
    p92 = _base_9_2()
    p93 = _base_9_3()
    p92["vps_self_builder_executed"] = True

    result, report, _ = _run(p91, p92, p93)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase9_4_aborts_on_draft_id_mismatch():
    p91 = _base_9_1()
    p92 = _base_9_2()
    p93 = _base_9_3()
    p93["wordpress_draft_id"] = 999

    result, report, _ = _run(p91, p92, p93)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase9_4_generates_markdown_on_pass():
    _, report, md = _run(_base_9_1(), _base_9_2(), _base_9_3())

    assert report["status"] == "PASS"
    assert "Phase 9-4" in md
    assert "KEEP_NO_GO" in md
    assert "NO_GO" in md
