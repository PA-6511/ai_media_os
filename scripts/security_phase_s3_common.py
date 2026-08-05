#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def walk_items(node: Any, path: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = f"{path}.{key}" if path else str(key)
            items.append((next_path, value))
            items.extend(walk_items(value, next_path))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            next_path = f"{path}[{idx}]"
            items.append((next_path, value))
            items.extend(walk_items(value, next_path))
    return items


def evaluate_s3_abort_conditions(data: dict[str, Any]) -> list[str]:
    from scripts.security_abort_conditions_shared_s2 import evaluate_shared_abort_conditions

    reasons: list[str] = evaluate_shared_abort_conditions(data)

    top_level_abort_true_keys = [
        "freeze_execution_allowed",
        "revoke_execution_allowed",
        "isolation_execution_allowed",
        "process_kill_allowed",
        "scheduler_stop_allowed",
        "wordpress_write_allowed",
        "external_api_call_allowed",
        "freeze_executed",
        "revoke_executed",
        "isolation_executed",
        "process_kill_executed",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
        "systemctl_allowed",
        "systemctl_executed",
        "cron_stop_allowed",
        "cron_stop_executed",
        "secret_value_output_allowed",
        "env_file_content_output_allowed",
        "token_value_output_allowed",
    ]
    for key in top_level_abort_true_keys:
        if data.get(key) is True:
            reasons.append(f"{key}=true is prohibited")

    if data.get("detector_only") is False:
        reasons.append("detector_only=false is prohibited")
    if data.get("recommendation_only") is False:
        reasons.append("recommendation_only=false is prohibited")
    if data.get("executor_action_allowed") is True:
        reasons.append("executor_action_allowed=true is prohibited")

    for path, value in walk_items(data):
        key = path.split(".")[-1]
        if key in {
            "auto_freeze_execute",
            "auto_revoke_execute",
            "process_kill_execute",
            "scheduler_stop_execute",
            "external_api_call_execute",
            "wordpress_api_call_execute",
            "systemctl_execute",
            "cron_stop_execute",
        } and value is True:
            reasons.append(f"{path}=true is prohibited")

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped


def build_base_result(data: dict[str, Any], validator_name: str) -> dict[str, Any]:
    return {
        "phase_id": "PHASE_S3",
        "validator_name": validator_name,
        "validator_result": "PASS",
        "phase_status": "DESIGN_ONLY",
        "execution": data.get("execution", "DRY_RUN"),
        "production_status": data.get("production_status", "NO_GO"),
        "human_approval_required": bool(data.get("human_approval_required", True)),
        "detector_only": bool(data.get("detector_only", True)),
        "recommendation_only": bool(data.get("recommendation_only", True)),
        "executor_action_allowed": bool(data.get("executor_action_allowed", False)),
        "freeze_recommendation": False,
        "human_review_recommendation": False,
        "abort_reasons": [],
        "fail_reasons": [],
        "warnings": [],
        "state_change_executed": bool(data.get("state_change_executed", False)),
        "freeze_executed": bool(data.get("freeze_executed", False)),
        "revoke_executed": bool(data.get("revoke_executed", False)),
        "isolation_executed": bool(data.get("isolation_executed", False)),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "external_api_call_executed": bool(data.get("external_api_call_executed", False)),
        "timestamp": now_iso(),
        "next_step": "human_review_or_continue_observability_only",
    }


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    if result["abort_reasons"]:
        result["validator_result"] = "ABORT"
    elif result["fail_reasons"]:
        result["validator_result"] = "FAIL"
    elif result["warnings"]:
        result["validator_result"] = "WARN"
    else:
        result["validator_result"] = "PASS"
    result["timestamp"] = now_iso()
    return result


def write_result(json_path: Path, md_path: Path, result: dict[str, Any], title: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"- validator_name: {result.get('validator_name')}",
        f"- validator_result: {result.get('validator_result')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- detector_only: {result.get('detector_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- freeze_recommendation: {result.get('freeze_recommendation')}",
        f"- human_review_recommendation: {result.get('human_review_recommendation')}",
        f"- state_change_executed: {result.get('state_change_executed')}",
        f"- freeze_executed: {result.get('freeze_executed')}",
        f"- revoke_executed: {result.get('revoke_executed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- external_api_call_executed: {result.get('external_api_call_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
    ]
    for section in ["warnings", "fail_reasons", "abort_reasons"]:
        lines.extend(["", f"## {section}"])
        values = result.get(section, [])
        if values:
            for value in values:
                lines.append(f"- {value}")
        else:
            lines.append("- none")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
