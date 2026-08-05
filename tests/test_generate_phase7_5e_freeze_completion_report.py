import json
import tempfile
from pathlib import Path

from scripts.generate_phase7_5e_freeze_completion_report import build_report, build_md


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _seed(base: Path):
    p75e = base / "p75e.json"
    p75d = base / "p75d.json"
    p75c = base / "p75c.json"

    _write(
        p75e,
        {
            "status": "PASS",
            "decision": "FREEZE",
            "reviewer_is_human": True,
            "manual_decision_recorded": True,
        },
    )
    _write(p75d, {"status": "PASS"})
    _write(p75c, {"wordpress_write_executed": False})
    return p75e, p75d, p75c


def test_build_report_pass_with_freeze():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75e, p75d, p75c = _seed(td)
        report = build_report(p75e, p75d, p75c)
        assert report["status"] == "PASS"
        assert report["freeze_confirmed"] is True
        assert report["current_decision"] == "FREEZE"
        assert report["live_execution_allowed"] is False
        assert report["wordpress_write_executed"] is False


def test_abort_when_decision_not_freeze():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75e, p75d, p75c = _seed(td)
        _write(p75e, {"status": "PASS", "decision": "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"})
        report = build_report(p75e, p75d, p75c)
        assert report["status"] == "ABORT"


def test_abort_when_phase7_5d_not_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75e, p75d, p75c = _seed(td)
        _write(p75d, {"status": "ABORT"})
        report = build_report(p75e, p75d, p75c)
        assert report["status"] == "ABORT"


def test_abort_when_phase7_5c_write_executed_true():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75e, p75d, p75c = _seed(td)
        _write(p75c, {"wordpress_write_executed": True})
        report = build_report(p75e, p75d, p75c)
        assert report["status"] == "ABORT"


def test_md_contains_freeze_summary():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75e, p75d, p75c = _seed(td)
        report = build_report(p75e, p75d, p75c)
        md = build_md(report)
        assert "FREEZE" in md
        assert "NO_GO" in md
        assert "wordpress_write_executed" in md


def test_no_go_flags_are_false_on_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75e, p75d, p75c = _seed(td)
        report = build_report(p75e, p75d, p75c)
        assert report["production_status"] == "NO_GO"
        assert report["wordpress_draft_creation"] == "NO_GO"
        assert report["wordpress_post_enabled"] is False
        assert report["real_write_enabled"] is False
        assert report["wordpress_write_executed"] is False
        assert report["auto_post"] is False
        assert report["auto_update"] is False
        assert report["auto_delete"] is False
        assert report["auto_export"] is False
