from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_OPS_TIMESTAMPS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_timestamps_latest.json"


def write_ops_timestamps_json(payload: dict, output_path: Path | None = None) -> str:
    """運用成果物の更新時刻サマリー JSON を保存する。"""
    path = output_path or DEFAULT_OPS_TIMESTAMPS_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
