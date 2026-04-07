from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from reporting.artifact_integrity_checker import run_integrity_checks


def _format_pretty(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    checks = result.get("checks", [])

    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("Artifact Integrity Check")
    lines.append("=" * 80)
    lines.append(f"overall: {summary.get('overall', 'UNKNOWN')}")
    lines.append(
        "counts: "
        f"PASS={summary.get('pass_count', 0)} "
        f"WARNING={summary.get('warning_count', 0)} "
        f"FAIL={summary.get('fail_count', 0)}"
    )
    lines.append("")

    for i, item in enumerate(checks, 1):
        level = item.get("level", "UNKNOWN")
        check = item.get("check", "")
        msg = item.get("message", "")
        target = item.get("target")
        details = item.get("details") or {}

        lines.append(f"[{i:02}] {level:7} {check}")
        lines.append(f"     message: {msg}")
        if target:
            lines.append(f"     target : {target}")
        if details:
            lines.append(f"     details: {json.dumps(details, ensure_ascii=False)}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="成果物整合性チェックを実行する")
    parser.add_argument(
        "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="表示形式 (pretty/json)",
    )
    args = parser.parse_args(argv)

    try:
        result = run_integrity_checks()
        summary = result.get("summary", {})

        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(_format_pretty(result))

        if summary.get("overall") == "FAIL":
            return 2
        if summary.get("overall") == "WARNING":
            return 1
        return 0
    except Exception as exc:
        print(f"artifact integrity check failed: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
