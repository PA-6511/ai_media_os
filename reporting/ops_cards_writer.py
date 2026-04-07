from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_OPS_CARDS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"


def write_ops_cards_json(cards: dict, output_path: Path | None = None) -> str:
    """GUI カード一覧 JSON を保存する。"""
    path = output_path or DEFAULT_OPS_CARDS_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
