import json
import tempfile
from pathlib import Path

from scripts.run_wordpress_single_draft_create_execution_dry_run import run_dry_run

ROOT = Path(__file__).resolve().parents[1]
VALID_P71 = ROOT / "exchange/logs/phase7_1_pre_release_checklist_validation_result.json"
VALID_CANDIDATE = ROOT / "exchange/outgoing/wordpress_draft_candidate.example.json"


def _p71_pass(td: str) -> Path:
    """Phase 7-1 PASS ダミーを作成して返す"""
    p = Path(td) / "p71.json"
    p.write_text(
        json.dumps({
            "status": "PASS",
            "wordpress_post_enabled": False,
            "real_write_enabled": False,
        }),
        encoding="utf-8",
    )
    return p


def _candidate(td: str) -> Path:
    """draft candidate ダミーを作成して返す"""
    p = Path(td) / "candidate.json"
    p.write_text(
        json.dumps({
            "title_candidate": "テスト下書き候補",
            "content_html_candidate": "<p>テスト本文</p>",
            "category_candidates": ["電子書籍"],
            "tag_candidates": ["Kindle"],
            "source_builder": {},
            "wordpress_write_executed": False,
            "created_at": "2026-05-05T00:00:00+00:00",
        }),
        encoding="utf-8",
    )
    return p


def test_valid_dry_run_passes():
    with tempfile.TemporaryDirectory() as td:
        p71 = _p71_pass(td)
        cand = _candidate(td)
        out_log = Path(td) / "result.json"
        out_payload = Path(td) / "payload.json"

        result = run_dry_run(p71, cand, out_log, out_payload)

        assert result["status"] == "PASS"
        assert result["dry_run_completed"] is True
        assert result["wordpress_post_enabled"] is False
        assert result["real_write_enabled"] is False
        assert result["production_status"] == "NO_GO"
        assert result["wordpress_draft_creation"] == "NO_GO"
        assert result["wordpress_write_executed"] is False


def test_phase7_1_not_pass_aborts():
    with tempfile.TemporaryDirectory() as td:
        p71 = Path(td) / "p71.json"
        p71.write_text(
            json.dumps({"status": "ABORT", "wordpress_post_enabled": False, "real_write_enabled": False}),
            encoding="utf-8",
        )
        cand = _candidate(td)
        result = run_dry_run(p71, cand, Path(td) / "r.json", Path(td) / "p.json")
        assert result["status"] == "ABORT"


def test_wordpress_post_enabled_true_in_p71_aborts():
    with tempfile.TemporaryDirectory() as td:
        p71 = Path(td) / "p71.json"
        p71.write_text(
            json.dumps({"status": "PASS", "wordpress_post_enabled": True, "real_write_enabled": False}),
            encoding="utf-8",
        )
        cand = _candidate(td)
        result = run_dry_run(p71, cand, Path(td) / "r.json", Path(td) / "p.json")
        assert result["status"] == "ABORT"


def test_candidate_wordpress_write_executed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        p71 = _p71_pass(td)
        cand = Path(td) / "bad_cand.json"
        cand.write_text(
            json.dumps({
                "title_candidate": "x",
                "content_html_candidate": "",
                "category_candidates": [],
                "tag_candidates": [],
                "source_builder": {},
                "wordpress_write_executed": True,
            }),
            encoding="utf-8",
        )
        result = run_dry_run(p71, cand, Path(td) / "r.json", Path(td) / "p.json")
        assert result["status"] == "ABORT"


def test_payload_contains_draft_status_and_no_post_flag():
    with tempfile.TemporaryDirectory() as td:
        p71 = _p71_pass(td)
        cand = _candidate(td)
        out_log = Path(td) / "result.json"
        out_payload = Path(td) / "payload.json"

        run_dry_run(p71, cand, out_log, out_payload)

        assert out_payload.exists()
        payload = json.loads(out_payload.read_text(encoding="utf-8"))
        assert payload["dry_run"] is True
        assert payload["wordpress_post_must_not_be_called"] is True
        assert payload["status"] == "draft"


def test_run_dry_run_writes_log_with_no_go_flags():
    with tempfile.TemporaryDirectory() as td:
        p71 = _p71_pass(td)
        cand = _candidate(td)
        out_log = Path(td) / "result.json"
        out_payload = Path(td) / "payload.json"

        result = run_dry_run(p71, cand, out_log, out_payload)

        assert out_log.exists()
        saved = json.loads(out_log.read_text(encoding="utf-8"))
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
