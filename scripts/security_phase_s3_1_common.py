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
        raise ValueError("json input must be a JSON object")
    return data


def write_result(json_path: Path, md_path: Path, result: dict[str, Any], title: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"- phase_id: {result.get('phase_id')}",
        f"- phase_name: {result.get('phase_name')}",
        f"- replay_result: {result.get('replay_result', result.get('validator_result'))}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- detector_only: {result.get('detector_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- event_count: {result.get('event_count')}",
        f"- matched_expected_count: {result.get('matched_expected_count')}",
        f"- mismatched_expected_count: {result.get('mismatched_expected_count')}",
        f"- freeze_recommendation_detected: {result.get('freeze_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- state_change_executed: {result.get('state_change_executed')}",
        f"- freeze_executed: {result.get('freeze_executed')}",
        f"- revoke_executed: {result.get('revoke_executed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- process_kill_executed: {result.get('process_kill_executed')}",
        f"- scheduler_stop_executed: {result.get('scheduler_stop_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- external_api_call_executed: {result.get('external_api_call_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## event_results",
    ]
    for item in result.get("event_results", []):
        lines.append(
            f"- {item.get('event_id')}: actual={item.get('actual_result')} expected={item.get('expected_result')} freeze_recommendation={item.get('freeze_recommendation')} human_review_recommendation={item.get('human_review_recommendation')}"
        )
    for section in ["warnings", "fail_reasons", "abort_reasons"]:
        lines.extend(["", f"## {section}"])
        values = result.get(section, [])
        if values:
            for value in values:
                lines.append(f"- {value}")
        else:
            lines.append("- none")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_scheduler_event(event: dict[str, Any], thresholds: dict[str, Any]) -> tuple[str, bool, bool, list[str]]:
    reasons: list[str] = []
    freeze = False
    human = False
    severity = "PASS"

    metrics = [
        ("retry_count", int(event.get("retry_count", 0)), "retry_count"),
        ("queue_depth", int(event.get("queue_depth", 0)), "queue_depth"),
        ("cron_runs_per_hour", int(event.get("cron_runs_per_hour", 0)), "cron_runs_per_hour"),
        ("duplicate_runs", int(event.get("duplicate_runs", 0)), "duplicate_run"),
    ]

    for metric_name, value, threshold_prefix in metrics:
        warn_v = int(thresholds[f"{threshold_prefix}_warn"])
        fail_v = int(thresholds[f"{threshold_prefix}_fail"])
        abort_v = int(thresholds[f"{threshold_prefix}_abort"])
        if value >= abort_v:
            severity = "ABORT"
            reasons.append(f"{metric_name}>=abort")
        elif value >= fail_v and severity != "ABORT":
            severity = "FAIL"
            reasons.append(f"{metric_name}>=fail")
        elif value >= warn_v and severity not in {"ABORT", "FAIL"}:
            severity = "WARN"
            reasons.append(f"{metric_name}>=warn")

    if severity in {"WARN", "FAIL", "ABORT"}:
        human = True
    if severity in {"FAIL", "ABORT"}:
        freeze = True
    if int(event.get("retry_count", 0)) >= int(thresholds["retry_count_warn"]):
        freeze = True
    return severity, freeze, human, reasons


def evaluate_wordpress_event(event: dict[str, Any]) -> tuple[str, bool, bool, list[str]]:
    intent = str(event.get("intent", ""))
    if event.get("wordpress_write_executed") is True:
        return "ABORT", False, False, ["wordpress_write_executed=true"]
    if intent in {"draft_create_intent", "publish_intent", "update_intent", "delete_intent", "bulk_write_intent"}:
        return "FAIL", True, True, [intent]
    if intent and intent != "none":
        return "WARN", False, True, [intent]
    return "PASS", False, False, []


def evaluate_external_api_event(event: dict[str, Any], known_intents: set[str], denied_intents: set[str]) -> tuple[str, bool, bool, list[str]]:
    intent = str(event.get("intent", ""))
    if event.get("external_api_call_executed") is True:
        return "ABORT", False, False, ["external_api_call_executed=true"]
    if intent in denied_intents:
        return "FAIL", True, True, [intent]
    if intent in known_intents:
        return "PASS", False, False, []
    if intent:
        return "WARN", False, True, [intent]
    return "PASS", False, False, []


def evaluate_env_event(event: dict[str, Any], denied_intents: set[str], observe_intents: set[str]) -> tuple[str, bool, bool, list[str]]:
    if event.get("secret_value_output_allowed") is True:
        return "ABORT", False, False, ["secret_value_output_allowed=true"]
    if event.get("env_file_content_output_allowed") is True:
        return "ABORT", False, False, ["env_file_content_output_allowed=true"]
    if event.get("token_value_output_allowed") is True:
        return "ABORT", False, False, ["token_value_output_allowed=true"]

    intent = str(event.get("intent", ""))
    if intent in denied_intents:
        freeze = intent in {"secret_value_echo", "env_file_content_read", "token_value_echo", "plaintext_secret_logging", "prod_secret_usage_without_human_approval"}
        return "FAIL", freeze, True, [intent]
    if intent in observe_intents:
        return "PASS", False, False, []
    if intent:
        return "WARN", False, True, [intent]
    return "PASS", False, False, []


def evaluate_process_event(event: dict[str, Any]) -> tuple[str, bool, bool, list[str]]:
    intent = str(event.get("intent", ""))
    if event.get("process_kill_executed") is True:
        return "ABORT", False, False, ["process_kill_executed=true"]
    if event.get("systemctl_executed") is True:
        return "ABORT", False, False, ["systemctl_executed=true"]
    if event.get("cron_stop_executed") is True:
        return "ABORT", False, False, ["cron_stop_executed=true"]
    if intent == "unexpected_python_worker":
        return "WARN", False, True, [intent]
    if intent == "duplicated_runner":
        return "FAIL", True, True, [intent]
    if intent == "unknown_long_running_process":
        return "WARN", False, True, [intent]
    if intent == "unexpected_shell_command":
        return "FAIL", True, True, [intent]
    if intent:
        return "WARN", False, True, [intent]
    return "PASS", False, False, []
