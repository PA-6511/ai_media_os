from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_OPS_API_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_api_payload_latest.json"


def write_ops_api_payload_json(payload: dict, output_path: Path | None = None) -> str:
    """API 向け運用統合 payload を JSON で保存する。"""
    path = output_path or DEFAULT_OPS_API_PAYLOAD_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)