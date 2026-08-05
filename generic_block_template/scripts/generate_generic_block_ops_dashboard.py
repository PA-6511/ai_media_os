#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
BLOCKS_DIR = ROOT / "blocks"
FILTER_POLICY_PATH = ROOT / "config/dashboard_filter_policy.json"

SCAFFOLD_HISTORY_PATH = LOG_DIR / "scaffold_generation_history.json"
CONTROLLED_RUN_PATH = LOG_DIR / "generic_controlled_once_result.json"
RANKING_PREVIEW_PATH = LOG_DIR / "ranking_dry_run_preview.json"
JSON_OUT = LOG_DIR / "generic_block_ops_dashboard.json"
MD_OUT = LOG_DIR / "generic_block_ops_dashboard.md"


def _load_json_or_default(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _list_generated_blocks() -> List[str]:
    if not BLOCKS_DIR.exists():
        return []
    return sorted([child.name for child in BLOCKS_DIR.iterdir() if child.is_dir()])


def _load_filter_policy(path: Path = FILTER_POLICY_PATH) -> tuple[str, Dict[str, Any]]:
    if not path.exists():
        return "FAIL", {"enabled": False, "exclude_exact": [], "exclude_globs": []}

    payload = _load_json_or_default(path, {})
    if not isinstance(payload, dict):
        return "FAIL", {"enabled": False, "exclude_exact": [], "exclude_globs": []}

    exclude_exact = payload.get("exclude_exact", [])
    exclude_globs = payload.get("exclude_globs", [])
    enabled = payload.get("enabled", False)

    if not isinstance(exclude_exact, list) or not isinstance(exclude_globs, list) or not isinstance(enabled, bool):
        return "FAIL", {"enabled": False, "exclude_exact": [], "exclude_globs": []}

    return "PASS", {
        "enabled": enabled,
        "exclude_exact": [str(item) for item in exclude_exact],
        "exclude_globs": [str(item) for item in exclude_globs],
    }


def _filter_generated_blocks(block_names: List[str], policy: Dict[str, Any]) -> tuple[List[str], List[str]]:
    if policy.get("enabled") is not True:
        return list(block_names), []

    exact = set(policy.get("exclude_exact", []))
    globs = list(policy.get("exclude_globs", []))
    filtered: List[str] = []
    excluded: List[str] = []

    for name in block_names:
        matched = name in exact or any(fnmatch.fnmatch(name, pattern) for pattern in globs)
        if matched:
            excluded.append(name)
        else:
            filtered.append(name)

    return filtered, excluded


def _filter_scaffold_history(history: List[Dict[str, Any]], policy: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if policy.get("enabled") is not True:
        return list(history), []

    exact = set(policy.get("exclude_exact", []))
    globs = list(policy.get("exclude_globs", []))
    filtered: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for entry in history:
        block_name = str(entry.get("block_name", ""))
        target_dir = str(entry.get("target_dir", ""))

        matched_name = block_name in exact or any(fnmatch.fnmatch(block_name, pattern) for pattern in globs)
        is_temp = target_dir.startswith("/tmp/")

        if matched_name or is_temp:
            excluded_entry = dict(entry)
            reasons: List[str] = []
            if matched_name:
                reasons.append("matched_filter_policy")
            if is_temp:
                reasons.append("temporary_target_dir")
            excluded_entry["excluded_reasons"] = reasons
            excluded.append(excluded_entry)
        else:
            filtered.append(entry)

    return filtered, excluded


def _extract_no_go_items(generated_blocks: List[str], controlled_once: Dict[str, Any], ranking_preview: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for block_name in generated_blocks:
        items.append({"type": "generated_block", "name": block_name, "production_status": "NO_GO"})

    if controlled_once:
        items.append(
            {
                "type": "controlled_run",
                "name": controlled_once.get("target_block") or controlled_once.get("block_id") or "unknown",
                "production_status": controlled_once.get("production_status", "UNKNOWN"),
            }
        )

    if ranking_preview:
        items.append(
            {
                "type": "ranking_preview",
                "name": ranking_preview.get("block_id", "ranking_dry_run_block"),
                "production_status": ranking_preview.get("production_status", "UNKNOWN"),
            }
        )

    return items


def _build_block_status_summary(
    generated_blocks_raw: List[str],
    generated_blocks_filtered: List[str],
    excluded_blocks: List[str],
    controlled_once: Dict[str, Any],
    ranking_preview: Dict[str, Any],
) -> List[Dict[str, Any]]:
    filtered_set = set(generated_blocks_filtered)
    excluded_set = set(excluded_blocks)
    controlled_target = controlled_once.get("target_block") or controlled_once.get("block_id") or ""
    controlled_status = controlled_once.get("status", "NOT_RUN") if controlled_once else "NOT_RUN"
    ranking_target = ranking_preview.get("block_id", "")
    ranking_status = ranking_preview.get("status", "NOT_RUN") if ranking_preview else "NOT_RUN"

    summary: List[Dict[str, Any]] = []
    for block_name in generated_blocks_raw:
        visible = block_name in filtered_set
        block_controlled_status = controlled_status if block_name == controlled_target else "NOT_RUN"
        block_ranking_status = ranking_status if block_name == ranking_target else "NOT_RUN"

        if block_name in excluded_set:
            no_go_reason = "filtered_by_policy"
        elif block_name == ranking_target:
            no_go_reason = "ranking_preview_dry_run_only"
        elif block_name == controlled_target:
            no_go_reason = "controlled_run_dry_run_only"
        else:
            no_go_reason = "template_no_go_default"

        summary.append(
            {
                "block_name": block_name,
                "visible": visible,
                "scaffolded": True,
                "controlled_run_status": block_controlled_status,
                "ranking_preview_status": block_ranking_status,
                "production_status": "NO_GO",
                "no_go_reason": no_go_reason,
            }
        )

    return summary


def generate_dashboard() -> Dict[str, Any]:
    scaffold_history = _load_json_or_default(SCAFFOLD_HISTORY_PATH, [])
    if not isinstance(scaffold_history, list):
        scaffold_history = []

    controlled_once = _load_json_or_default(CONTROLLED_RUN_PATH, {})
    if not isinstance(controlled_once, dict):
        controlled_once = {}

    ranking_preview = _load_json_or_default(RANKING_PREVIEW_PATH, {})
    if not isinstance(ranking_preview, dict):
        ranking_preview = {}

    generated_blocks_raw = _list_generated_blocks()
    filter_status, filter_policy = _load_filter_policy()
    generated_blocks_filtered, excluded_blocks = _filter_generated_blocks(generated_blocks_raw, filter_policy)
    scaffold_history_filtered, scaffold_history_excluded = _filter_scaffold_history(scaffold_history, filter_policy)
    no_go_items = _extract_no_go_items(generated_blocks_filtered, controlled_once, ranking_preview)
    block_status_summary = _build_block_status_summary(
        generated_blocks_raw,
        generated_blocks_filtered,
        excluded_blocks,
        controlled_once,
        ranking_preview,
    )

    dashboard = {
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "filter_status": filter_status,
        "scaffold_generation_history_count": len(scaffold_history_filtered),
        "scaffold_generation_history_raw_count": len(scaffold_history),
        "scaffold_generation_history_filtered_count": len(scaffold_history_filtered),
        "scaffold_generation_history_excluded_count": len(scaffold_history_excluded),
        "generated_blocks": generated_blocks_filtered,
        "generated_blocks_raw": generated_blocks_raw,
        "generated_blocks_filtered": generated_blocks_filtered,
        "excluded_blocks": excluded_blocks,
        "block_status_summary": block_status_summary,
        "controlled_run_status": controlled_once.get("status", "UNKNOWN"),
        "controlled_run_target": controlled_once.get("target_block") or controlled_once.get("block_id") or "unknown",
        "ranking_preview_status": ranking_preview.get("status", "UNKNOWN"),
        "ranking_preview_top_item": (ranking_preview.get("ranking_preview") or [{}])[0],
        "ranking_input_source": ranking_preview.get("input_source", ""),
        "ranking_input_item_count": ranking_preview.get("input_item_count", 0),
        "no_go_items": no_go_items,
        "evidence": {
            "dashboard_filter_policy": filter_policy,
            "scaffold_generation_history": scaffold_history_filtered,
            "scaffold_generation_history_raw": scaffold_history,
            "scaffold_generation_history_excluded": scaffold_history_excluded,
            "controlled_run": controlled_once,
            "ranking_preview": ranking_preview,
        },
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Generic Block Ops Dashboard v1",
        "",
        f"- status: {dashboard['status']}",
        f"- generated_at: {dashboard['generated_at']}",
        f"- production_status: {dashboard['production_status']}",
        f"- filter_status: {dashboard['filter_status']}",
        f"- scaffold_generation_history_count: {dashboard['scaffold_generation_history_count']}",
        f"- scaffold_generation_history_raw_count: {dashboard['scaffold_generation_history_raw_count']}",
        f"- scaffold_generation_history_excluded_count: {dashboard['scaffold_generation_history_excluded_count']}",
        f"- controlled_run_status: {dashboard['controlled_run_status']}",
        f"- controlled_run_target: {dashboard['controlled_run_target']}",
        f"- ranking_preview_status: {dashboard['ranking_preview_status']}",
        f"- ranking_input_source: {dashboard['ranking_input_source']}",
        f"- ranking_input_item_count: {dashboard['ranking_input_item_count']}",
        f"- ranking_preview_top_item: {dashboard['ranking_preview_top_item'].get('title', 'none')}",
        "",
        "## Generated Blocks",
    ]
    for block_name in generated_blocks_filtered:
        lines.append(f"- {block_name}")

    lines.extend(["", "## Raw Generated Blocks"])
    for block_name in generated_blocks_raw:
        lines.append(f"- {block_name}")

    lines.extend(["", "## Excluded Blocks"])
    for block_name in excluded_blocks:
        lines.append(f"- {block_name}")

    lines.extend(["", "## Excluded Scaffold History"])
    for entry in scaffold_history_excluded:
        lines.append(
            f"- block_name={entry.get('block_name', '')} target_dir={entry.get('target_dir', '')} reasons={','.join(entry.get('excluded_reasons', []))}"
        )

    lines.extend([
        "",
        "## Block Status Summary",
        "| block_name | visible | scaffolded | controlled_run_status | ranking_preview_status | production_status | no_go_reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for item in block_status_summary:
        lines.append(
            f"| {item['block_name']} | {item['visible']} | {item['scaffolded']} | {item['controlled_run_status']} | {item['ranking_preview_status']} | {item['production_status']} | {item['no_go_reason']} |"
        )

    lines.extend(["", "## NO_GO Items"])
    for item in no_go_items:
        lines.append(f"- type={item['type']} name={item['name']} production_status={item['production_status']}")

    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dashboard


def main() -> int:
    dashboard = generate_dashboard()
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))
    return 0 if dashboard.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
