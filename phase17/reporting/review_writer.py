from __future__ import annotations

import json
from pathlib import Path


def write_review_package(package: dict, output_path: str) -> dict:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "PASS",
        "output_path": str(path),
        "package_status": package.get("status"),
    }
