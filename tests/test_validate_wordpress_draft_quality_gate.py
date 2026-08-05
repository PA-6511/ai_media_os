import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_wordpress_draft_quality_gate import run_validation, validate_quality_gate


def base_config() -> dict:
    return {
        "phase": "Phase 6-6",
        "production_status": "NO_GO",
        "wordpress_write_executed": False,
        "required_fields": ["title", "body", "product_name", "affiliate_links", "cta", "category", "tags", "pr_notice"],
        "body_rules": {"min_chars": 50, "max_chars_warning": 10000, "must_include_product_name": True},
        "pr_notice_rules": {
            "required": True,
            "accepted_phrases": ["PR", "広告", "アフィリエイト広告を利用しています", "本記事には広告が含まれます"],
        },
        "cta_rules": {"required": True, "min_cta_count": 1, "require_url": True},
        "affiliate_link_rules": {
            "required": True,
            "min_link_count": 1,
            "allowed_schemes": ["https"],
            "reject_schemes": ["http", "javascript", "data", "file"],
        },
        "html_safety_rules": {"reject_tags": ["script", "iframe", "object", "embed"], "reject_inline_event_handlers": True},
        "expression_rules": {"reject_exaggerated_claims": ["絶対に稼げる", "必ず儲かる", "100%保証", "公式より安いと断定", "違法無料"]},
    }


def base_candidate() -> dict:
    body = "PR：本記事には広告が含まれます。サンプル漫画の紹介文です。" * 8
    return {
        "title": "サンプル漫画 1巻 セール紹介",
        "product_name": "サンプル漫画",
        "body": body,
        "pr_notice": "PR：本記事には広告が含まれます。",
        "affiliate_links": [{"store": "amazon", "url": "https://example.com/a"}],
        "cta": [{"label": "Amazonで見る", "url": "https://example.com/a"}],
        "category": "電子書籍",
        "tags": ["漫画", "セール"],
    }


def test_example_candidate_passes():
    result = validate_quality_gate(base_config(), base_candidate())
    assert result["status"] == "PASS_DRY_RUN_ONLY"


def test_missing_pr_notice_fails():
    candidate = copy.deepcopy(base_candidate())
    candidate["pr_notice"] = ""
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] in {"FAIL", "ABORT"}


def test_body_too_short_fails():
    cfg = base_config()
    cfg["body_rules"]["min_chars"] = 9999
    result = validate_quality_gate(cfg, base_candidate())
    assert result["status"] == "FAIL"


def test_affiliate_links_empty_fails():
    candidate = copy.deepcopy(base_candidate())
    candidate["affiliate_links"] = []
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "FAIL"


def test_cta_empty_fails():
    candidate = copy.deepcopy(base_candidate())
    candidate["cta"] = []
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "FAIL"


def test_http_url_aborts():
    candidate = copy.deepcopy(base_candidate())
    candidate["affiliate_links"][0]["url"] = "http://example.com/a"
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "ABORT"


def test_javascript_url_aborts():
    candidate = copy.deepcopy(base_candidate())
    candidate["cta"][0]["url"] = "javascript:alert(1)"
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "ABORT"


def test_script_tag_aborts():
    candidate = copy.deepcopy(base_candidate())
    candidate["body"] += " <script>alert(1)</script>"
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "ABORT"


def test_onerror_aborts():
    candidate = copy.deepcopy(base_candidate())
    candidate["body"] += " <img src=x onerror=alert(1)>"
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "ABORT"


def test_exaggerated_claim_aborts():
    candidate = copy.deepcopy(base_candidate())
    candidate["body"] += " 絶対に稼げる"
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "ABORT"


def test_product_name_not_in_body_fails():
    candidate = copy.deepcopy(base_candidate())
    candidate["body"] = candidate["body"].replace("サンプル漫画", "別作品")
    result = validate_quality_gate(base_config(), candidate)
    assert result["status"] == "FAIL"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg.json"
        cand = Path(td) / "candidate.json"
        out = Path(td) / "out.json"
        cfg.write_text(json.dumps(base_config(), ensure_ascii=False, indent=2), encoding="utf-8")
        cand.write_text(json.dumps(base_candidate(), ensure_ascii=False, indent=2), encoding="utf-8")
        result = run_validation(cfg, cand, out)
        assert result["status"] == "PASS_DRY_RUN_ONLY"
        assert out.exists()
