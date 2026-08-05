import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_9_single_publish_manual_execution_script_implementation_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_8() -> dict:
    return {
        "package_type": "phase10_8_manual_publish_command_dry_run_payload_validation_report",
        "phase": "Phase 10-8",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "dry_run_payload_validation_design": {
            "dry_run_only": True,
            "payload_checks_count": 7,
            "token_expiry_minutes": 30,
            "max_publish_count": 1,
        },
    }


def _run(p10_8: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_8 = tdp / "p10_8.json"
        out_json = tdp / "p10_9.json"
        out_md = tdp / "p10_9.md"

        _write(i10_8, p10_8)

        result = generate_report(i10_8, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_9_pass_with_phase10_8_input():
    result, report, _ = _run(_base_10_8())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_9_implementation_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["script_implementation"]["default_runtime_mode"] == "DRY_RUN_STOP"
    assert report["script_implementation"]["live_execution_flag"] == "--execute-live"


def test_phase10_9_aborts_when_phase10_8_not_pass():
    p10_8 = _base_10_8()
    p10_8["status"] = "ABORT"

    result, report, _ = _run(p10_8)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_9_aborts_when_decision_mismatch():
    p10_8 = _base_10_8()
    p10_8["current_decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, report, _ = _run(p10_8)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_9_aborts_when_publish_candidate_unlocked_true():
    p10_8 = _base_10_8()
    p10_8["publish_candidate_unlocked_for_operator"] = True

    result, report, _ = _run(p10_8)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_9_aborts_on_draft_mismatch():
    p10_8 = _base_10_8()
    p10_8["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_8)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_9_generates_markdown_on_pass():
    _, report, md = _run(_base_10_8())

    assert report["status"] == "PASS"
    assert "Phase 10-9" in md
    assert "DRY_RUN_STOP" in md
    assert "--execute-live" in md
    assert "NO_GO" in md
