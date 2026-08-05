#!/usr/bin/env python3
"""Build manual review checklist markdown for Phase 8-50B."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "manual_affiliate_builder" / "manual_items.example.json"
DEFAULT_POLICY = ROOT / "manual_affiliate_builder" / "review_policy.json"
DEFAULT_OUTPUT = ROOT / "reports" / "phase8_50_manual_review_checklist.md"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_checklist(data: Dict[str, Any], policy: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Phase 8-50 Manual Review Checklist",
        "",
        f"- Generated at: {now}",
        f"- Phase: {data.get('phase', 'Phase 8-50-MANUAL')}",
        "- Execution Mode: DRY_RUN_ONLY",
        "- Production Status: NO_GO",
        "- Amazon API call allowed: false",
        "- WordPress write allowed: false",
        "- Publish allowed: false",
        "",
        "## Review Rules",
        "- This checklist is preview-only and no-execution.",
        "- 投稿禁止確認 must stay checked before any transition.",
        "- migration readiness確認 is documentation-only in Phase 8-50B.",
        "",
    ]

    required_checks = policy.get("required_item_checks", [])

    for idx, item in enumerate(data.get("items", []), start=1):
        lines.append(f"## Item {idx}: {item.get('title', 'N/A')}")
        lines.append(f"- ASIN: {item.get('asin', '')}")
        lines.append(f"- Author: {item.get('author', '')}")
        lines.append(f"- Volume: {item.get('volume', '')}")
        lines.append(f"- Release Date: {item.get('release_date', '')}")
        lines.append(f"- URL: {item.get('manual_affiliate_url', '')}")
        lines.append("")
        for check in required_checks:
            lines.append(f"- [ ] {check}")
        lines.append("")

    lines.append("## Final Decision")
    for opt in policy.get("final_decision_options", []):
        lines.append(f"- [ ] {opt}")

    lines.append("")
    lines.append("## Sign-off")
    lines.append("- Reviewer:")
    lines.append("- Reviewed at:")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build manual review checklist markdown")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input manual item JSON")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="Review policy JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output checklist markdown")
    args = parser.parse_args()

    try:
        data = load_json(Path(args.input))
        policy = load_json(Path(args.policy))
        checklist = build_checklist(data, policy)

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(checklist, encoding="utf-8")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "phase": "Phase 8-50B",
                    "execution_mode": "DRY_RUN_ONLY",
                    "production_status": "NO_GO",
                    "amazon_api_call_allowed": False,
                    "wordpress_write_allowed": False,
                    "output": str(output),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "phase": "Phase 8-50B",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
