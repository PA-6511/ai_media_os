import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_candidate import run_validation, validate_candidate


def _write(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_candidate() -> dict:
    return {
        "package_type": "wordpress_draft_candidate",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "title_candidate": "電子書籍セール紹介タイトル候補（PR）",
        "content_html_candidate": "<p>PR: セール紹介です。</p><a href=\"https://example.com/book?tag=abc-22\">link</a>",
        "category_candidates": ["電子書籍", "セール"],
        "tag_candidates": ["Kindle", "漫画", "セール"],
        "next_step": "human_review",
    }


def test_valid_candidate_returns_pass_or_warn():
    result = validate_candidate(base_candidate())
    assert result["status"] in {"PASS", "WARN"}


def test_execution_live_aborts():
    payload = base_candidate()
    payload["execution"] = "LIVE"
    result = validate_candidate(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    payload = base_candidate()
    payload["auto_post"] = True
    result = validate_candidate(payload)
    assert result["status"] == "ABORT"


def test_html_script_fails():
    payload = base_candidate()
    payload["content_html_candidate"] = "<script>alert('x')</script>"
    result = validate_candidate(payload)
    assert result["status"] == "FAIL"


def test_empty_categories_fail():
    payload = base_candidate()
    payload["category_candidates"] = []
    result = validate_candidate(payload)
    assert result["status"] == "FAIL"


def test_empty_tags_fail():
    payload = base_candidate()
    payload["tag_candidates"] = []
    result = validate_candidate(payload)
    assert result["status"] == "FAIL"


def test_missing_pr_label_warns():
    payload = base_candidate()
    payload["content_html_candidate"] = "<p>紹介文です。</p><a href=\"https://example.com/book?tag=abc-22\">link</a>"
    result = validate_candidate(payload)
    assert result["status"] in {"WARN", "FAIL"}
    assert result["quality_checks"]["pr_label"] == "WARN"


def test_non_http_url_fails():
    payload = base_candidate()
    payload["content_html_candidate"] = "<p>PR</p><a href=\"ftp://example.com/file\">bad</a>"
    result = validate_candidate(payload)
    assert result["status"] == "FAIL"


def test_result_file_is_generated():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        input_path = base / "candidate.json"
        output_path = base / "result.json"
        _write(input_path, base_candidate())

        result = run_validation(input_path, output_path)
        assert output_path.exists()
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["package_type"] == "wordpress_draft_candidate_validation_result"
        assert saved["execution"] == "DRY_RUN"
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] in {"PASS", "WARN", "FAIL"}
