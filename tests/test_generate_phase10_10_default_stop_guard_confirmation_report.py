import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_10_default_stop_guard_confirmation_report import generate_report


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_9() -> dict:
    return {
        "package_type": "phase10_9_single_publish_manual_execution_script_implementation_report",
        "phase": "Phase 10-9",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "script_implementation": {
            "default_runtime_mode": "DRY_RUN_STOP",
            "live_execution_flag": "--execute-live",
            "live_execution_flag_default": False,
        },
    }


def _run(p10_9: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_9 = tdp / "p10_9.json"
        out_json = tdp / "p10_10.json"
        out_md = tdp / "p10_10.md"

        _write(i10_9, p10_9)

        result = generate_report(i10_9, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_10_pass_with_phase10_9_input():
    result, report, _ = _run(_base_10_9())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_10_confirmation_status"] == "PASS"
    assert report["default_stop_guard_confirmation"]["confirmed_default_stop"] is True
    assert report["default_stop_guard_confirmation"]["confirmed_live_requires_explicit_flag"] is True
    assert report["default_stop_guard_confirmation"]["confirmed_live_is_blocked_without_flag"] is True


def test_phase10_10_aborts_when_phase10_9_not_pass():
    p10_9 = _base_10_9()
    p10_9["status"] = "ABORT"

    result, report, _ = _run(p10_9)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_10_aborts_when_default_runtime_not_stop():
    p10_9 = _base_10_9()
    p10_9["script_implementation"]["default_runtime_mode"] = "LIVE"

    result, report, _ = _run(p10_9)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_10_aborts_when_live_flag_mismatch():
    p10_9 = _base_10_9()
    p10_9["script_implementation"]["live_execution_flag"] = "--live"

    result, report, _ = _run(p10_9)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_10_aborts_on_draft_mismatch():
    p10_9 = _base_10_9()
    p10_9["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_9)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_10_generates_markdown_on_pass():
    _, report, md = _run(_base_10_9())

    assert report["status"] == "PASS"
    assert "Phase 10-10" in md
    assert "default_stop_guard" in md
    assert "--execute-live" in md
    assert "NO_GO" in md
