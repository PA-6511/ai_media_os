import json
import tempfile
from pathlib import Path

from scripts.generate_wordpress_draft_candidate import generate_wordpress_draft_candidate


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_decision() -> dict:
    return {
        "package_type": "decision_package",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "requested_action": "propose_article_template_update",
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "self_builder_origin": {
            "type": "LOCAL_SELF_BUILDER",
            "location": "local",
            "execution_allowed": False,
            "vps_migration_ready": False,
        },
        "summary": "電子書籍セール紹介タイトル候補",
    }


def test_generates_candidate_and_result_pass():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out_c = base / "candidate.json"
        out_r = base / "result.json"
        _write(inp, _base_decision())

        result = generate_wordpress_draft_candidate(inp, out_c, out_r)

        assert result["status"] == "PASS"
        assert out_c.exists()
        assert out_r.exists()

        candidate = json.loads(out_c.read_text(encoding="utf-8"))
        assert candidate["package_type"] == "wordpress_draft_candidate"
        assert candidate["execution"] == "DRY_RUN"
        assert candidate["human_approval_required"] is True
        assert candidate["wordpress_write_executed"] is False
        assert candidate["auto_post"] is False
        assert candidate["auto_update"] is False
        assert candidate["auto_delete"] is False
        assert candidate["auto_export"] is False
        assert candidate["next_step"] == "human_review"


def test_execution_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out_c = base / "candidate.json"
        out_r = base / "result.json"
        payload = _base_decision()
        payload["execution"] = "LIVE"
        _write(inp, payload)

        result = generate_wordpress_draft_candidate(inp, out_c, out_r)
        assert result["status"] == "ABORT"
        assert out_c.exists() is False


def test_auto_post_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out_c = base / "candidate.json"
        out_r = base / "result.json"
        payload = _base_decision()
        payload["auto_post"] = True
        _write(inp, payload)

        result = generate_wordpress_draft_candidate(inp, out_c, out_r)
        assert result["status"] == "ABORT"
        assert out_c.exists() is False


def test_execution_allowed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out_c = base / "candidate.json"
        out_r = base / "result.json"
        payload = _base_decision()
        payload["self_builder_origin"]["execution_allowed"] = True
        _write(inp, payload)

        result = generate_wordpress_draft_candidate(inp, out_c, out_r)
        assert result["status"] == "ABORT"


def test_existing_output_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out_c = base / "candidate.json"
        out_r = base / "result.json"
        _write(inp, _base_decision())
        out_c.write_text("{}", encoding="utf-8")

        result = generate_wordpress_draft_candidate(inp, out_c, out_r)
        assert result["status"] == "ABORT"


def test_result_keeps_production_flags_false():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out_c = base / "candidate.json"
        out_r = base / "result.json"
        _write(inp, _base_decision())

        result = generate_wordpress_draft_candidate(inp, out_c, out_r)
        assert result["status"] == "PASS"

        saved = json.loads(out_r.read_text(encoding="utf-8"))
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
