import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_12_manual_live_execution_readiness_review_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_11() -> dict:
    return {
        "package_type": "phase10_11_post_execution_evidence_and_relock_confirmation_design_report",
        "phase": "Phase 10-11",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "post_execution_evidence_and_relock_design": {
            "relock_mandatory": True,
        },
    }


def _run(p10_11: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_11 = tdp / "p10_11.json"
        out_json = tdp / "p10_12.json"
        out_md = tdp / "p10_12.md"

        _write(i10_11, p10_11)

        result = generate_report(i10_11, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_12_pass_with_phase10_11_input():
    result, report, _ = _run(_base_10_11())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_12_review_status"] == "PASS"
    assert report["manual_live_execution_readiness_review"]["readiness_review_passed"] is True
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False


def test_phase10_12_aborts_when_phase10_11_not_pass():
    p10_11 = _base_10_11()
    p10_11["status"] = "ABORT"

    result, report, _ = _run(p10_11)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_12_aborts_when_relock_not_mandatory():
    p10_11 = _base_10_11()
    p10_11["post_execution_evidence_and_relock_design"]["relock_mandatory"] = False

    result, report, _ = _run(p10_11)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_12_aborts_on_draft_mismatch():
    p10_11 = _base_10_11()
    p10_11["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_11)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_12_generates_markdown_on_pass():
    _, report, md = _run(_base_10_11())

    assert report["status"] == "PASS"
    assert "Phase 10-12" in md
    assert "readiness_review_passed" in md
    assert "NO_GO" in md
