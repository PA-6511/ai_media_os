import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_11_post_execution_evidence_and_relock_confirmation_design_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_10() -> dict:
    return {
        "package_type": "phase10_10_default_stop_guard_confirmation_report",
        "phase": "Phase 10-10",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "default_stop_guard_confirmation": {
            "confirmed_default_stop": True,
            "confirmed_live_requires_explicit_flag": True,
            "confirmed_live_is_blocked_without_flag": True,
        },
    }


def _run(p10_10: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_10 = tdp / "p10_10.json"
        out_json = tdp / "p10_11.json"
        out_md = tdp / "p10_11.md"

        _write(i10_10, p10_10)

        result = generate_report(i10_10, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_11_pass_with_phase10_10_input():
    result, report, _ = _run(_base_10_10())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_11_design_status"] == "PASS"
    assert report["post_execution_evidence_and_relock_design"]["relock_mandatory"] is True
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False


def test_phase10_11_aborts_when_phase10_10_not_pass():
    p10_10 = _base_10_10()
    p10_10["status"] = "ABORT"

    result, report, _ = _run(p10_10)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_11_aborts_when_default_stop_not_confirmed():
    p10_10 = _base_10_10()
    p10_10["default_stop_guard_confirmation"]["confirmed_default_stop"] = False

    result, report, _ = _run(p10_10)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_11_aborts_when_live_flag_requirement_not_confirmed():
    p10_10 = _base_10_10()
    p10_10["default_stop_guard_confirmation"]["confirmed_live_requires_explicit_flag"] = False

    result, report, _ = _run(p10_10)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_11_aborts_when_wordpress_write_true():
    p10_10 = _base_10_10()
    p10_10["wordpress_write_executed"] = True

    result, report, _ = _run(p10_10)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_11_generates_markdown_on_pass():
    _, report, md = _run(_base_10_10())

    assert report["status"] == "PASS"
    assert "Phase 10-11" in md
    assert "relock_mandatory" in md
    assert "NO_GO" in md
