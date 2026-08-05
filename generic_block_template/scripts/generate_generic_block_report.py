#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_generic_block_template import check_template
from run_generic_controlled_once import run_once

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
JSON_REPORT = LOG_DIR / "generic_block_report.json"
MD_REPORT = LOG_DIR / "generic_block_report.md"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _overall(statuses: List[str]) -> str:
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "WARN" for s in statuses):
        return "WARN"
    return "PASS"


def generate_report() -> Dict[str, Any]:
    template_check = check_template(ROOT)
    run_result = run_once("sample_block")
    ranking_module = _load_module("ranking_dry_run_block", ROOT / "blocks/ranking_dry_run_block/run.py")
    ranking_result = ranking_module.run_block()

    top_item = None
    if ranking_result.get("ranking_preview"):
        item = ranking_result["ranking_preview"][0]
        top_item = {
            "item_id": item.get("item_id", ""),
            "title": item.get("title", ""),
            "ranking_score": item.get("ranking_score", 0),
            "rank": item.get("rank", 0),
        }

    statuses = [
        template_check.get("status", "FAIL"),
        run_result.get("status", "FAIL"),
        ranking_result.get("status", "FAIL"),
    ]
    overall = _overall(statuses)

    report = {
        "status": overall,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "ranking_preview_status": ranking_result.get("status", "FAIL"),
        "ranking_preview_top_item": top_item,
        "ranking_input_source": ranking_result.get("input_source", ""),
        "ranking_input_item_count": ranking_result.get("input_item_count", 0),
        "checks": {
            "template": template_check,
            "controlled_once": run_result,
            "ranking_preview": ranking_result,
        },
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Generic Block Template Report v1",
        "",
        f"- status: {overall}",
        f"- generated_at: {report['generated_at']}",
        "- production_status: NO_GO",
        "",
        "## Template Check",
        f"- status: {template_check.get('status', 'FAIL')}",
        f"- errors: {', '.join(template_check.get('errors', [])) or 'none'}",
        f"- warnings: {', '.join(template_check.get('warnings', [])) or 'none'}",
        "",
        "## Controlled Run",
        f"- status: {run_result.get('status', 'FAIL')}",
        f"- target_block: {run_result.get('target_block', 'unknown')}",
        f"- mode: {run_result.get('mode', 'unknown')}",
        "",
        "## Ranking Preview",
        f"- ranking_preview_status: {report.get('ranking_preview_status', 'FAIL')}",
        f"- ranking_input_source: {report.get('ranking_input_source', '')}",
        f"- ranking_input_item_count: {report.get('ranking_input_item_count', 0)}",
        f"- ranking_preview_top_item: {(top_item or {}).get('title', 'none')}",
    ]
    MD_REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = generate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
