import json
import tempfile
from pathlib import Path

from scripts.read_phase7_5e_manual_go_freeze_decision import run_read


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _phase7_5d_ok(path: Path):
    _write(path, {"status": "PASS"})


def _review_base() -> dict:
    return {
        "reviewer": "human_reviewer",
        "reviewer_is_human": True,
        "manual_confirmation": {
            "runbook_reviewed": True,
            "scope_one_time_only_confirmed": True,
            "status_draft_only_confirmed": True,
            "no_publish_update_delete_export_confirmed": True,
            "rollback_procedure_confirmed": True,
            "token_and_expiry_confirmed": True,
        },
        "fix_requests": [],
        "reviewed_at": "2026-05-05T15:00:00+09:00",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
    }


def test_manual_go_passes_when_all_confirmed():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75d = td / "p75d.json"
        review = td / "review.json"
        out = td / "result.json"

        _phase7_5d_ok(p75d)
        r = _review_base()
        r["decision"] = "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
        _write(review, r)

        result = run_read(review, p75d, out)
        assert result["status"] == "PASS"
        assert result["decision"] == "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
        assert result["all_manual_confirmation_passed"] is True
        assert result["next_step"] == "manual_execute_phase7_5c_with_execute_live"


def test_freeze_passes_even_if_not_all_confirmed():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75d = td / "p75d.json"
        review = td / "review.json"
        out = td / "result.json"

        _phase7_5d_ok(p75d)
        r = _review_base()
        r["decision"] = "FREEZE"
        r["manual_confirmation"]["token_and_expiry_confirmed"] = False
        _write(review, r)

        result = run_read(review, p75d, out)
        assert result["status"] == "PASS"
        assert result["decision"] == "FREEZE"
        assert result["next_step"] == "freeze_or_rework"


def test_invalid_decision_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75d = td / "p75d.json"
        review = td / "review.json"
        out = td / "result.json"

        _phase7_5d_ok(p75d)
        r = _review_base()
        r["decision"] = "GO"
        _write(review, r)

        result = run_read(review, p75d, out)
        assert result["status"] == "ABORT"


def test_manual_go_with_incomplete_confirmation_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75d = td / "p75d.json"
        review = td / "review.json"
        out = td / "result.json"

        _phase7_5d_ok(p75d)
        r = _review_base()
        r["decision"] = "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
        r["manual_confirmation"]["runbook_reviewed"] = False
        _write(review, r)

        result = run_read(review, p75d, out)
        assert result["status"] == "ABORT"


def test_reviewer_not_human_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75d = td / "p75d.json"
        review = td / "review.json"
        out = td / "result.json"

        _phase7_5d_ok(p75d)
        r = _review_base()
        r["decision"] = "REQUEST_FIX"
        r["reviewer_is_human"] = False
        _write(review, r)

        result = run_read(review, p75d, out)
        assert result["status"] == "ABORT"


def test_output_no_go_flags_on_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75d = td / "p75d.json"
        review = td / "review.json"
        out = td / "result.json"

        _phase7_5d_ok(p75d)
        r = _review_base()
        r["decision"] = "REQUEST_FIX"
        _write(review, r)

        result = run_read(review, p75d, out)
        saved = json.loads(out.read_text(encoding="utf-8"))

        assert result["status"] == "PASS"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_post_enabled"] is False
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
