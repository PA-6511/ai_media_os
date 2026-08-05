import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_13_execute_live_final_human_authorization_gate_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_12() -> dict:
    return {
        "package_type": "phase10_12_manual_live_execution_readiness_review_report",
        "phase": "Phase 10-12",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "manual_live_execution_readiness_review": {
            "readiness_review_passed": True,
        },
    }


def _run(p10_12: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_12 = tdp / "p10_12.json"
        out_json = tdp / "p10_13.json"
        out_md = tdp / "p10_13.md"

        _write(i10_12, p10_12)

        result = generate_report(i10_12, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_13_pass_with_phase10_12_input():
    result, report, _ = _run(_base_10_12())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_13_gate_status"] == "PASS"
    assert report["execute_live_final_human_authorization_gate"]["default_authorization"] == "DENY"
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False


def test_phase10_13_aborts_when_phase10_12_not_pass():
    p10_12 = _base_10_12()
    p10_12["status"] = "ABORT"

    result, report, _ = _run(p10_12)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_13_aborts_when_readiness_not_passed():
    p10_12 = _base_10_12()
    p10_12["manual_live_execution_readiness_review"]["readiness_review_passed"] = False

    result, report, _ = _run(p10_12)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_13_aborts_on_draft_mismatch():
    p10_12 = _base_10_12()
    p10_12["target_draft_status"] = "publish"

    result, report, _ = _run(p10_12)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_13_generates_markdown_on_pass():
    _, report, md = _run(_base_10_12())

    assert report["status"] == "PASS"
    assert "Phase 10-13" in md
    assert "default_authorization" in md
    assert "NO_GO" in md
