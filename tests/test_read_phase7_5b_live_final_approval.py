import json
import tempfile
from pathlib import Path

from scripts.read_phase7_5b_live_final_approval import run_read

ROOT = Path(__file__).resolve().parents[1]
VALID_P75A = ROOT / "exchange/logs/phase7_5_freeze_or_live_decision_report.json"

REMAINING_ALL_TRUE = {
    "live_01_payload_title_content": True,
    "live_02_content_url": True,
    "live_03_affiliate_tag": True,
    "live_04_pr_notation": True,
    "live_05_wp_user_role_editor": True,
    "live_06_status_draft_only": True,
    "live_07_rollback_plan": True,
    "live_08_token_valid_within_30min": True,
}

VALID_CONSTRAINTS = {
    "one_time_only": True,
    "expires_minutes": 30,
    "post_status": "draft",
    "post_count_limit": 1,
    "publish_allowed": False,
    "update_allowed": False,
    "delete_allowed": False,
    "export_allowed": False,
}


def _p75a(td: str) -> Path:
    p = Path(td) / "p75a.json"
    p.write_text(json.dumps({
        "phase7_5_decision": "FREEZE_RECOMMENDED",
        "live_execution_allowed": False,
    }), encoding="utf-8")
    return p


def _review(td: str,
            token: str = "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME",
            remaining: dict | None = None,
            constraints: dict | None = None,
            **overrides) -> Path:
    data = {
        "reviewer_is_human": True,
        "approval_token": token,
        "decision": token,
        "remaining_items_confirmed": remaining if remaining is not None else REMAINING_ALL_TRUE,
        "token_constraints": constraints if constraints is not None else VALID_CONSTRAINTS,
        "reviewed_at": "2026-05-05T15:00:00+09:00",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        **overrides,
    }
    p = Path(td) / "review.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_valid_approval_passes():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_read(_review(td), _p75a(td), out)
        assert result["status"] == "PASS"
        assert result["approval_token"] == "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME"
        assert result["approval_token_valid"] is True
        assert result["all_remaining_items_confirmed"] is True
        assert result["token_constraints_valid"] is True
        assert result["wordpress_post_enabled"] is False
        assert result["real_write_enabled"] is False
        assert result["production_status"] == "NO_GO"
        assert result["wordpress_draft_creation"] == "NO_GO"
        assert result["wordpress_write_executed"] is False


def test_forbidden_token_approve_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        rev = _review(td, token="APPROVE_SINGLE_DRAFT_CREATE_LIVE",
                      decision="APPROVE_SINGLE_DRAFT_CREATE_LIVE")
        result = run_read(rev, _p75a(td), Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_any_remaining_item_false_aborts():
    incomplete = {**REMAINING_ALL_TRUE, "live_03_affiliate_tag": False}
    with tempfile.TemporaryDirectory() as td:
        rev = _review(td, remaining=incomplete)
        result = run_read(rev, _p75a(td), Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_publish_allowed_true_in_constraints_aborts():
    bad_constraints = {**VALID_CONSTRAINTS, "publish_allowed": True}
    with tempfile.TemporaryDirectory() as td:
        rev = _review(td, constraints=bad_constraints)
        result = run_read(rev, _p75a(td), Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_post_status_not_draft_aborts():
    bad_constraints = {**VALID_CONSTRAINTS, "post_status": "publish"}
    with tempfile.TemporaryDirectory() as td:
        rev = _review(td, constraints=bad_constraints)
        result = run_read(rev, _p75a(td), Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_run_read_writes_output_with_no_go_flags():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_read(_review(td), _p75a(td), out)
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
        assert saved["next_step"] == "phase7_5c_single_draft_create_live_post"
        assert result["status"] == "PASS"
