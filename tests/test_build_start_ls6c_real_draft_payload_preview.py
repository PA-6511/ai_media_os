import json
from pathlib import Path

from scripts import build_start_ls6c_real_draft_payload_preview as builder


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict:
    return json.loads(Path("config/start_ls6c_real_draft_payload_rebuild_dry_run_policy.json").read_text(encoding="utf-8"))


def valid_input() -> dict:
    return {
        "phase": "LS-6C",
        "input_status": "ACTUAL_MANUAL_INPUT",
        "item": {
            "title": "実作品名",
            "author": "実著者名",
            "volume": "1",
            "release_date": "2026-06-21",
            "asin": "B0ABCDEF12",
            "affiliate_tag": "yourtag-22",
            "summary": "作品の短い紹介文。",
            "purchase_url": "https://www.amazon.co.jp/dp/B0ABCDEF12?tag=yourtag-22",
            "category": "巻数ガイド",
            "tags": ["新刊", "電子書籍"],
        },
    }


def run_build(tmp_path: Path, input_payload: dict | None) -> dict:
    policy_path = tmp_path / "policy.json"
    input_path = tmp_path / "real_input.json"
    output_path = tmp_path / "out.json"
    write_json(policy_path, valid_policy())
    if input_payload is not None:
        write_json(input_path, input_payload)
    result = builder.run_builder(policy_path, input_path, output_path)
    return result


def test_missing_actual_input_not_ready(tmp_path: Path):
    result = run_build(tmp_path, None)
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY"


def test_valid_actual_input_ready(tmp_path: Path):
    result = run_build(tmp_path, valid_input())
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY"
    assert result["payload_ready"] is True


def test_manual_required_left_not_ready(tmp_path: Path):
    payload = valid_input()
    payload["item"]["title"] = "MANUAL_REQUIRED"
    result = run_build(tmp_path, payload)
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY"


def test_sample_contains_not_ready(tmp_path: Path):
    payload = valid_input()
    payload["item"]["author"] = "Sample Author"
    result = run_build(tmp_path, payload)
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY"


def test_exampletag_not_ready(tmp_path: Path):
    payload = valid_input()
    payload["item"]["affiliate_tag"] = "exampletag-22"
    payload["item"]["purchase_url"] = "https://www.amazon.co.jp/dp/B0ABCDEF12?tag=exampletag-22"
    result = run_build(tmp_path, payload)
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY"


def test_purchase_url_without_tag_not_ready(tmp_path: Path):
    payload = valid_input()
    payload["item"]["purchase_url"] = "https://www.amazon.co.jp/dp/B0ABCDEF12"
    result = run_build(tmp_path, payload)
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY"


def test_uncategorized_not_ready(tmp_path: Path):
    payload = valid_input()
    payload["item"]["category"] = "未分類"
    result = run_build(tmp_path, payload)
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY"


def test_content_uses_html_link_not_markdown(tmp_path: Path):
    result = run_build(tmp_path, valid_input())
    content = result["payloads"][0]["content"]
    assert "<a href=" in content
    assert "[Amazon" not in content
    assert "](https://" not in content


def test_no_wordpress_and_no_post119_update(tmp_path: Path):
    result = run_build(tmp_path, valid_input())
    assert result["wordpress_api_call_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["post119_update_executed"] is False
