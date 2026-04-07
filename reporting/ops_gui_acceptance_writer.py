from __future__ import annotations

import json
from pathlib import Path

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


DEFAULT_OPS_GUI_ACCEPTANCE_JSON_PATH = DEFAULT_REPORT_DIR / "ops_gui_acceptance_latest.json"


def write_ops_gui_acceptance_json(payload: dict, output_path: Path | None = None) -> str:
    path = output_path or DEFAULT_OPS_GUI_ACCEPTANCE_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)
