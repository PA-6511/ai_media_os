import json
import tempfile
from pathlib import Path

from scripts.read_phase7_3_single_draft_create_final_approval import run_read

ROOT = Path(__file__).resolve().parents[1]
VALID_P72 = ROOT / "exchange/logs/phase7_2_single_draft_create_execution_dry_run_result.json"

CHECKLIST_ALL_TRUE = {
    "title_confirmed": True,
    "content_html_confirmed": True,
    "status_is_draft": True,
    "no_publish_no_future_no_pending": True,
    "affiliate_tag_confirmed": True,
    "content_url_confirmed": True,
    "pr_notation_confirmed": True,
    "category_confirmed": True,
    "tag_confirmed": True,
    "dry_run_true_confirmed": True,
    "wordpress_post_must_not_be_called_confirmed": True,
}


def _p72_pass(td: str) -> Path:
    p = Path(td) / "p72.json"
    p.write_text(
        json.dumps({"status": "PASS", "dry_run_completed": True}),
        encoding="utf-8",
    )
    return p


def _review(td: str, decision: str, checklist: dict | None = None) -> Path:
    r = Path(td) / "review.json"
    r.write_text(
        json.dumps({
            "reviewer_is_human": True,
            "decision": decision,
            "review_checklist": checklist if checklist is not None else CHECKLIST_ALL_TRUE,
            "fix_requests": [],
            "reviewed_at": "2026-05-05T15:00:00+09:00",
            "wordpress_post_enabled": False,
            "real_write_enabled": False,
            "wordpress_write_executed": False,
        }),
        encoding="utf-8",
    )
    return r


def test_approve_dry_run_only_passes():
    with tempfile.TemporaryDirectory() as td:
        p72 = _p72_pass(td)
        rev = _review(td, "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY")
        out = Path(td) / "result.json"

        result = run_read(rev, p72, out)

        assert result["status"] == "PASS"
        assert result["decision"] == "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY"
        assert result["wordpress_post_enabled"] is False
        assert result["real_write_enabled"] is False
        assert result["production_status"] == "NO_GO"
        assert result["wordpress_draft_creation"] == "NO_GO"
        assert result["wordpress_write_executed"] is False
        assert result["checklist_all_confirmed"] is True


def test_forbidden_decision_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        p72 = _p72_pass(td)
        rev = _review(td, "APPROVE_SINGLE_DRAFT_CREATE_LIVE")
        result = run_read(rev, p72, Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_approve_with_incomplete_checklist_aborts():
    incomplete = {**CHECKLIST_ALL_TRUE, "title_confirmed": False}
    with tempfile.TemporaryDirectory() as td:
        p72 = _p72_pass(td)
        rev = _review(td, "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY", incomplete)
        result = run_read(rev, p72, Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_reject_decision_passes_with_no_go():
    with tempfile.TemporaryDirectory() as td:
        p72 = _p72_pass(td)
        rev = _review(td, "REJECT")
        out = Path(td) / "result.json"
        result = run_read(rev, p72, out)
        assert result["status"] == "PASS"
        assert result["decision"] == "REJECT"
        assert result["wordpress_draft_creation"] == "NO_GO"
        assert result["next_step"] == "re_review_or_abort"


def test_wordpress_post_enabled_true_in_review_aborts():
    with tempfile.TemporaryDirectory() as td:
        p72 = _p72_pass(td)
        rev = Path(td) / "rev.json"
        rev.write_text(
            json.dumps({
                "reviewer_is_human": True,
                "decision": "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY",
                "review_checklist": CHECKLIST_ALL_TRUE,
                "fix_requests": [],
                "reviewed_at": "2026-05-05T15:00:00+09:00",
                "wordpress_post_enabled": True,
                "real_write_enabled": False,
                "wordpress_write_executed": False,
            }),
            encoding="utf-8",
        )
        result = run_read(rev, p72, Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_run_read_writes_output_with_no_go_flags():
    with tempfile.TemporaryDirectory() as td:
        p72 = _p72_pass(td)
        rev = _review(td, "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY")
        out = Path(td) / "result.json"

        result = run_read(rev, p72, out)

        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_post_enabled"] is False
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
