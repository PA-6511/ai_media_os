from __future__ import annotations

import json

from reporting.status_badge_builder import DEFAULT_OUTPUT_HTML_PATH, DEFAULT_OUTPUT_JSON_PATH


def write_status_badge_json(badge: dict) -> str:
    """運用ステータスバッジJSONを保存し、出力パスを返す。"""
    output_path = DEFAULT_OUTPUT_JSON_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(badge, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)


def write_status_badge_html(html: str) -> str:
    """運用ステータスバッジHTML断片を保存し、出力パスを返す。"""
    output_path = DEFAULT_OUTPUT_HTML_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
