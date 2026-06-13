#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root_str = str(REPO_ROOT)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

from auto_builder_block_ai.src.low_token_dev_mode import build_status_report

OUTPUT_PATH = REPO_ROOT / "reports/level5/auto_builder_level5_status_report.json"


def generate_level5_status_report(output_path: Path | None = None) -> dict:
    destination = Path(output_path or OUTPUT_PATH)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = build_status_report()
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = generate_level5_status_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())