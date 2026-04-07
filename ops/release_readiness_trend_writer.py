from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_TREND_MD_PATH = DEFAULT_REPORT_DIR / "release_readiness_trend_latest.md"
DEFAULT_TREND_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_trend_latest.json"


def _line(value: Any, fallback: str = "N/A") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def write_release_readiness_trend_md(summary: dict, output_path: Path | None = None) -> str:
    """release readiness 日次トレンドを Markdown で保存する。"""
    path = output_path or DEFAULT_TREND_MD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = summary.get("recent_days") if isinstance(summary.get("recent_days"), list) else []

    lines: list[str] = []
    lines.append("# AI Media OS Release Readiness Trend")
    lines.append("")
    lines.append(f"generated_at: {_line(summary.get('generated_at'))}")
    lines.append(f"total_days: {_line(summary.get('total_days'))}")
    lines.append(f"latest_decision: {_line(summary.get('latest_decision'))}")
    lines.append("")
    lines.append("## Decision Counts")
    lines.append("")
    lines.append(f"- release_count: {_line(summary.get('release_count'))}")
    lines.append(f"- review_count: {_line(summary.get('review_count'))}")
    lines.append(f"- hold_count: {_line(summary.get('hold_count'))}")
    lines.append("")
    lines.append("## Recent Days")
    lines.append("")

    if rows:
        lines.append("| date | decision | health_score | anomaly_overall |")
        lines.append("|---|---|---:|---|")
        for row in rows:
            lines.append(
                "| "
                f"{_line(row.get('date'))} | "
                f"{_line(row.get('decision'))} | "
                f"{_line(row.get('health_score'))} | "
                f"{_line(row.get('anomaly_overall'))} |"
            )
    else:
        lines.append("- (no recent day records)")

    lines.append("")
    source = summary.get("source") if isinstance(summary.get("source"), dict) else {}
    lines.append("## Source")
    lines.append("")
    lines.append(f"- history_path: {_line(source.get('history_path'))}")
    lines.append(f"- history_records: {_line(source.get('history_records'))}")
    lines.append(f"- limit_days: {_line(source.get('limit_days'))}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_release_readiness_trend_json(summary: dict, output_path: Path | None = None) -> str:
    """release readiness 日次トレンドを JSON で保存する。"""
    path = output_path or DEFAULT_TREND_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
