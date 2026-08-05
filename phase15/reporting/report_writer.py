from __future__ import annotations

import json
from pathlib import Path


def write_report(report: dict, output_path: str) -> dict:
    """Write report as JSON, creating parent directories if needed."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "output_path": str(path),
    }
