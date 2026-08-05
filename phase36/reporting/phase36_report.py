"""Phase36 JSON report writer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_phase36_report(payload: dict[str, Any], output_path: str) -> dict[str, Any]:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "phase": "36",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": payload.get("can_execute", False),
        "execute_allowed": False,
        **payload,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(out)}
