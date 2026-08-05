#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "freeze_control_phase_s1.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "freeze_control_phase_s1_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "freeze_control_phase_s1_validation_result.md"

REQUIRED_KEYS = {
    "freeze_enabled": True,
    "freeze_state": "NO_GO_LOCKED",
    "allow_external_api": False,
    "allow_wordpress_write": False,
    "allow_scheduler": False,
    "allow_auto_retry": False,
    "allow_block_ai_execution": False,
    "allow_self_builder_execution": False,
    "wordpress_publish_allowed": False,
    "wordpress_update_allowed": False,
    "wordpress_delete_allowed": False,
    "slack_live_notification_allowed": False,
    "human_approval_required": True,
    "mode": "CONNECTION_TEST",
    "execution": "DRY_RUN",
    "production_status": "NO_GO",
}

COMMON_ABORT_TRUE_KEYS = [
    "publish_allowed",
    "wordpress_write_executed",
    "auto_execute",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
]

FORBIDDEN_UNLOCK_KEYS = {
    "unlock_token",
    "production_unlock",
    "production_unlock_token",
    "freeze_unlock_token",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def _scan_unlock_tokens(node: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            lower_key = str(key).lower()
            next_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_UNLOCK_KEYS:
                if value not in (None, "", False, 0, []):
                    found.append(next_path)
            if "unlock" in lower_key and "token" in lower_key:
                if value not in (None, "", False, 0, []):
                    found.append(next_path)
            found.extend(_scan_unlock_tokens(value, next_path))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            next_path = f"{path}[{idx}]"
            found.extend(_scan_unlock_tokens(value, next_path))
    return found


def validate_freeze_control_phase_s1(data: dict[str, Any]) -> dict[str, Any]:
    fail_reasons: list[str] = []
    abort_reasons: list[str] = []
    warnings: list[str] = []

    for key, expected in REQUIRED_KEYS.items():
        if key not in data:
            fail_reasons.append(f"missing required key: {key}")
            continue
        actual = data.get(key)
        if isinstance(expected, bool):
            if not isinstance(actual, bool):
                fail_reasons.append(f"{key} must be bool")
                continue
        if actual != expected:
            if key in {
                "allow_external_api",
                "allow_wordpress_write",
                "allow_scheduler",
                "allow_auto_retry",
                "allow_block_ai_execution",
                "allow_self_builder_execution",
                "wordpress_publish_allowed",
                "wordpress_update_allowed",
                "wordpress_delete_allowed",
                "slack_live_notification_allowed",
            } and actual is True:
                abort_reasons.append(f"{key}=true is prohibited")
            elif key == "freeze_enabled" and actual is False:
                abort_reasons.append("freeze_enabled=false is prohibited")
            elif key == "execution" and actual == "LIVE":
                abort_reasons.append("execution=LIVE is prohibited")
            elif key == "production_status" and actual == "GO":
                abort_reasons.append("production_status=GO is prohibited")
            else:
                fail_reasons.append(f"{key} must be {expected!r}, got {actual!r}")

    for key in COMMON_ABORT_TRUE_KEYS:
        if data.get(key) is True:
            abort_reasons.append(f"{key}=true is prohibited")

    execution = data.get("execution")
    if execution == "LIVE":
        abort_reasons.append("execution=LIVE is prohibited")

    production_status = data.get("production_status")
    if production_status == "GO":
        abort_reasons.append("production_status=GO is prohibited")

    unlock_hits = _scan_unlock_tokens(data)
    if unlock_hits:
        abort_reasons.append(f"unlock token detected: {unlock_hits}")

    if abort_reasons:
        validator_result = "ABORT"
    elif fail_reasons:
        validator_result = "FAIL"
    elif warnings:
        validator_result = "WARN"
    else:
        validator_result = "PASS"

    all_dangerous_actions_blocked = all(data.get(key) is False for key in [
        "allow_external_api",
        "allow_wordpress_write",
        "allow_scheduler",
        "allow_auto_retry",
        "allow_block_ai_execution",
        "allow_self_builder_execution",
        "wordpress_publish_allowed",
        "wordpress_update_allowed",
        "wordpress_delete_allowed",
        "slack_live_notification_allowed",
    ])

    return {
        "phase_id": "PHASE_S1",
        "validator": "validate_freeze_control_phase_s1",
        "validator_result": validator_result,
        "phase_status": "PASS_DRY_RUN_ONLY" if validator_result in {"PASS", "WARN"} else "BLOCKED",
        "freeze_state": data.get("freeze_state"),
        "all_dangerous_actions_blocked": all_dangerous_actions_blocked,
        "execution": data.get("execution"),
        "production_status": data.get("production_status"),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "human_approval_required": data.get("human_approval_required"),
        "dry_run": data.get("execution") == "DRY_RUN",
        "no_go": data.get("production_status") == "NO_GO",
        "warnings": warnings,
        "fail_reasons": fail_reasons,
        "abort_reasons": abort_reasons,
        "timestamp": _now_iso(),
        "next_step": "maintain_freeze_until_human_approval" if validator_result in {"PASS", "WARN"} else "manual_security_review",
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Freeze Control Phase S-1 Validation",
        "",
        f"- validator_result: {result.get('validator_result')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- freeze_state: {result.get('freeze_state')}",
        f"- all_dangerous_actions_blocked: {result.get('all_dangerous_actions_blocked')}",
        f"- DRY_RUN: {result.get('dry_run')}",
        f"- NO_GO: {result.get('no_go')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## warnings",
    ]
    if result.get("warnings"):
        for item in result["warnings"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## fail_reasons"])
    if result.get("fail_reasons"):
        for item in result["fail_reasons"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## abort_reasons"])
    if result.get("abort_reasons"):
        for item in result["abort_reasons"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def _write_result(result: dict[str, Any]) -> None:
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD_PATH.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    try:
        data = _load_json(CONFIG_PATH)
        result = validate_freeze_control_phase_s1(data)
    except Exception as exc:
        result = {
            "phase_id": "PHASE_S1",
            "validator": "validate_freeze_control_phase_s1",
            "validator_result": "ABORT",
            "phase_status": "BLOCKED",
            "freeze_state": "NO_GO_LOCKED",
            "all_dangerous_actions_blocked": True,
            "execution": "DRY_RUN",
            "production_status": "NO_GO",
            "wordpress_write_executed": False,
            "human_approval_required": True,
            "dry_run": True,
            "no_go": True,
            "warnings": [],
            "fail_reasons": [],
            "abort_reasons": [f"validator_exception: {exc}"],
            "timestamp": _now_iso(),
            "next_step": "manual_security_review",
        }

    _write_result(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
