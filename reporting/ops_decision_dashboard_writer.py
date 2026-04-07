from __future__ import annotations

from pathlib import Path

from reporting.ops_decision_dashboard_builder import DEFAULT_OUTPUT_PATH


def write_ops_decision_dashboard(html: str) -> str:
    """運用判定ダッシュボードHTMLを保存し、出力パスを返す。"""
    output_path = DEFAULT_OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
