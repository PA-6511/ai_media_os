from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ops.release_readiness_writer import DEFAULT_HISTORY_PATH


def load_release_readiness_history(
    limit: int = 10,
    path: Path | None = None,
) -> list[dict]:
    """release_readiness_history.jsonl から最新limit件を返す（新しい順）。"""
    target = path or DEFAULT_HISTORY_PATH
    if not target.exists() or not target.is_file():
        return []

    try:
        raw_lines = [
            line for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return []

    rows: list[dict] = []
    for line in raw_lines:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue

    if limit > 0:
        rows = rows[-limit:]

    return list(reversed(rows))


def format_release_readiness_history(rows: list[dict]) -> str:
    """release readiness 履歴を人間向けテキストに整形する。"""
    if not rows:
        return "release readiness history: (no records found)"

    lines: list[str] = []
    lines.append(f"Release Readiness History ({len(rows)} records)")
    lines.append("=" * 72)

    for i, row in enumerate(rows, start=1):
        lines.append(f"#{i}  {row.get('generated_at', 'N/A')}")
        lines.append(
            f"   decision={row.get('decision', 'N/A')} "
            f"anomaly={row.get('anomaly_overall', 'N/A')} "
            f"health={row.get('health_score', 'N/A')}({row.get('health_grade', 'N/A')})"
        )
        lines.append(
            f"   retry={row.get('retry_queued', 'N/A')} "
            f"integrity={row.get('integrity_overall', 'N/A')}"
        )
        lines.append(f"   archive={row.get('latest_archive', 'N/A')}")
        lines.append(f"   action={row.get('recommended_action', 'N/A')}")
        if i < len(rows):
            lines.append("-" * 72)

    lines.append("=" * 72)
    return "\n".join(lines)
