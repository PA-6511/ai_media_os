from __future__ import annotations

# report_history_loader.py
# daily_report_YYYYMMDD.json の履歴を読み込むユーティリティ。

import json
import re
from pathlib import Path
from typing import Any


REPORT_FILE_PATTERN = re.compile(r"^daily_report_(\d{8})\.json$")


def list_daily_report_jsons(report_dir: Path) -> list[Path]:
    """daily_report_YYYYMMDD.json を日付昇順で返す。"""
    if not report_dir.exists() or not report_dir.is_dir():
        return []

    dated_paths: list[tuple[str, Path]] = []
    for path in report_dir.glob("daily_report_*.json"):
        matched = REPORT_FILE_PATTERN.match(path.name)
        if matched:
            dated_paths.append((matched.group(1), path))

    dated_paths.sort(key=lambda x: x[0])
    return [path for _, path in dated_paths]


def _load_report(path: Path) -> dict[str, Any]:
    """単一レポートJSONを読み込む。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"daily_report JSON が不正です: {path} ({exc})") from exc
    except OSError as exc:
        raise OSError(f"daily_report の読み込みに失敗しました: {path} ({exc})") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"daily_report の形式が不正です: {path}")

    return payload


def load_recent_reports(report_dir: Path, days: int = 7) -> list[dict[str, Any]]:
    """直近 days 件の日次レポートを返す。"""
    paths = list_daily_report_jsons(report_dir)
    if not paths:
        return []

    selected = paths[-days:] if days > 0 else paths
    reports: list[dict[str, Any]] = []
    for path in selected:
        reports.append(_load_report(path))
    return reports
