import json
import tempfile
from pathlib import Path

from scripts.generate_phase7_5f_keep_freeze_completion_report import build_report, build_md


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _seed(base: Path):
    p75f = base / "p75f.json"
    p75e = base / "p75e.json"
    p75c = base / "p75c.json"

    _write(
        p75f,
        {
            "status": "PASS",
            "decision": "KEEP_FREEZE",
            "phase7_5c_execution_unlocked_for_operator": False,
        },
    )
    _write(
        p75e,
        {
            "status": "PASS",
            "current_decision": "FREEZE",
        },
    )
    _write(
        p75c,
        {
            "wordpress_write_executed": False,
        },
    )
    return p75f, p75e, p75c


def test_build_report_pass_with_keep_freeze():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75f, p75e, p75c = _seed(td)
        report = build_report(p75f, p75e, p75c)
        assert report["status"] == "PASS"
        assert report["phase7_5f_decision"] == "KEEP_FREEZE"
        assert report["keep_freeze_confirmed"] is True
        assert report["live_execution_allowed"] is False
        assert report["phase7_5c_execution_unlocked_for_operator"] is False


def test_abort_when_phase7_5f_not_keep_freeze():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75f, p75e, p75c = _seed(td)
        _write(
            p75f,
            {
                "status": "PASS",
                "decision": "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME",
                "phase7_5c_execution_unlocked_for_operator": True,
            },
        )
        report = build_report(p75f, p75e, p75c)
        assert report["status"] == "ABORT"


def test_abort_when_unlocked_true():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75f, p75e, p75c = _seed(td)
        _write(
            p75f,
            {
                "status": "PASS",
                "decision": "KEEP_FREEZE",
                "phase7_5c_execution_unlocked_for_operator": True,
            },
        )
        report = build_report(p75f, p75e, p75c)
        assert report["status"] == "ABORT"


def test_abort_when_phase7_5e_not_freeze():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75f, p75e, p75c = _seed(td)
        _write(p75e, {"status": "PASS", "current_decision": "GO"})
        report = build_report(p75f, p75e, p75c)
        assert report["status"] == "ABORT"


def test_abort_when_phase7_5c_write_executed_true():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75f, p75e, p75c = _seed(td)
        _write(p75c, {"wordpress_write_executed": True})
        report = build_report(p75f, p75e, p75c)
        assert report["status"] == "ABORT"


def test_md_contains_keep_freeze_summary():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75f, p75e, p75c = _seed(td)
        report = build_report(p75f, p75e, p75c)
        md = build_md(report)
        assert "KEEP_FREEZE" in md
        assert "NO_GO" in md
        assert "phase7_5c_execution_unlocked_for_operator" in md
