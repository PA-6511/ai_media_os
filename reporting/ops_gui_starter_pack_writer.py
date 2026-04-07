from __future__ import annotations

import json
from pathlib import Path

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR
from reporting.ops_gui_starter_pack_builder import build_ops_gui_starter_pack


DEFAULT_FILENAME = "ops_gui_starter_pack_latest.json"


def write_ops_gui_starter_pack(output_dir: Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / DEFAULT_FILENAME
    payload = build_ops_gui_starter_pack()
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
