from __future__ import annotations

import json
from pathlib import Path

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


DEFAULT_MOCK_SERVER_OPERATIONAL_CHECK_PATH = (
    DEFAULT_REPORT_DIR / "mock_server_operational_check_latest.json"
)


def write_mock_server_operational_check_json(
    payload: dict,
    output_path: Path | None = None,
) -> str:
    path = output_path or DEFAULT_MOCK_SERVER_OPERATIONAL_CHECK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)
