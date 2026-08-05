import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_14_pre_execution_final_freeze_release_judgment_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_13() -> dict:
    return {
        "package_type": "phase10_13_execute_live_final_human_authorization_gate_report",
        "phase": "Phase 10-13",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "execute_live_final_human_authorization_gate": {
            "default_authorization": "DENY",
            "required_authorization_token": "APPROVE_EXECUTE_LIVE_ONE_TIME_MANUAL_ONLY",
        },
    }


def _run(p10_13: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_13 = tdp / "p10_13.json"
        out_json = tdp / "p10_14.json"
        out_md = tdp / "p10_14.md"

        _write(i10_13, p10_13)

        result = generate_report(i10_13, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_14_pass_with_phase10_13_input():
    result, report, _ = _run(_base_10_13())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_14_judgment_status"] == "PASS"
    assert report["phase10_14_final_judgment"] == "KEEP_NO_GO"
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False


def test_phase10_14_aborts_when_phase10_13_not_pass():
    p10_13 = _base_10_13()
    p10_13["status"] = "ABORT"

    result, report, _ = _run(p10_13)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_14_aborts_when_default_authorization_not_deny():
    p10_13 = _base_10_13()
    p10_13["execute_live_final_human_authorization_gate"]["default_authorization"] = "ALLOW"

    result, report, _ = _run(p10_13)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_14_aborts_on_draft_id_mismatch():
    p10_13 = _base_10_13()
    p10_13["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_13)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_14_generates_markdown_on_pass():
    _, report, md = _run(_base_10_13())

    assert report["status"] == "PASS"
    assert "Phase 10-14" in md
    assert "phase10_14_final_judgment" in md
    assert "NO_GO" in md
