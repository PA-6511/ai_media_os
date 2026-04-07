from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_OPS_NOTIFICATION_SETTINGS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_notification_settings_latest.json"


def write_ops_notification_settings_json(payload: dict, output_path: Path | None = None) -> str:
    path = output_path or DEFAULT_OPS_NOTIFICATION_SETTINGS_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)