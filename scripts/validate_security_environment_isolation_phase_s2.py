#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_abort_conditions_shared_s2 import evaluate_shared_abort_conditions

CONFIG_PATH = ROOT / "config" / "security_environment_isolation_phase_s2.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_environment_isolation_phase_s2_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_environment_isolation_phase_s2_validation_result.md"

EXPECTED_ENV_FILES = {
    "dev": ".env.dev",
    "stage": ".env.stage",
    "prod": ".env.prod",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def validate_security_environment_isolation_phase_s2(data: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    fail_reasons: list[str] = []
    abort_reasons: list[str] = evaluate_shared_abort_conditions(data)

    if data.get("phase_id") != "PHASE_S2":
        fail_reasons.append("phase_id must be PHASE_S2")
    if data.get("status") != "DESIGN_ONLY":
        fail_reasons.append("status must be DESIGN_ONLY")
    if data.get("execution") != "DRY_RUN":
        fail_reasons.append("execution must be DRY_RUN")
    if data.get("production_status") != "NO_GO":
        fail_reasons.append("production_status must be NO_GO")
    if data.get("human_approval_required") is not True:
        fail_reasons.append("human_approval_required must be true")

    environments = data.get("environments")
    if not isinstance(environments, dict):
        fail_reasons.append("environments must be object")
    else:
        for env_name, env_file in EXPECTED_ENV_FILES.items():
            env_data = environments.get(env_name)
            if not isinstance(env_data, dict):
                fail_reasons.append(f"environments.{env_name} must be object")
                continue
            if env_data.get("env_file") != env_file:
                fail_reasons.append(f"environments.{env_name}.env_file must be {env_file}")
            if not isinstance(env_data.get("env_file"), str):
                fail_reasons.append(f"environments.{env_name}.env_file must be str")
            if env_data.get("writable") is not False:
                fail_reasons.append(f"environments.{env_name}.writable must be false")
            if env_data.get("external_write_allowed") is not False:
                fail_reasons.append(f"environments.{env_name}.external_write_allowed must be false")

    rules = data.get("rules")
    if not isinstance(rules, dict):
        fail_reasons.append("rules must be object")
    else:
        for key in [
            "env_cross_reference_forbidden",
            "prod_secret_usage_without_human_approval_forbidden",
            "plaintext_secret_logging_forbidden",
            "secret_value_echo_forbidden",
        ]:
            if rules.get(key) is not True:
                fail_reasons.append(f"rules.{key} must be true")

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        fail_reasons.append("evidence must be object")
    else:
        for key in [
            "secrets_inventory_required",
            "credential_owner_required",
            "rotation_policy_reference_required",
        ]:
            if evidence.get(key) is not True:
                fail_reasons.append(f"evidence.{key} must be true")

    if abort_reasons:
        validator_result = "ABORT"
    elif fail_reasons:
        validator_result = "FAIL"
    elif warnings:
        validator_result = "WARN"
    else:
        validator_result = "PASS"

    result = {
        "phase_id": "PHASE_S2",
        "validator": "validate_security_environment_isolation_phase_s2",
        "validator_result": validator_result,
        "phase_status": "PASS_DESIGN_ONLY" if validator_result in {"PASS", "WARN"} else "BLOCKED",
        "DRY_RUN": data.get("execution") == "DRY_RUN",
        "NO_GO": data.get("production_status") == "NO_GO",
        "production_status": data.get("production_status"),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "timestamp": _now_iso(),
        "next_step": "validate_security_read_only_policy_phase_s2" if validator_result in {"PASS", "WARN"} else "manual_security_review",
    }
    return result


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Security Environment Isolation Phase S-2 Validation",
        "",
        f"- validator_result: {result.get('validator_result')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- DRY_RUN: {result.get('DRY_RUN')}",
        f"- NO_GO: {result.get('NO_GO')}",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
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
    return "\n".join(lines) + "\n"


def _write_result(result: dict[str, Any]) -> None:
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD_PATH.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    try:
        data = _load_json(CONFIG_PATH)
        result = validate_security_environment_isolation_phase_s2(data)
    except Exception as exc:
        result = {
            "phase_id": "PHASE_S2",
            "validator": "validate_security_environment_isolation_phase_s2",
            "validator_result": "ABORT",
            "phase_status": "BLOCKED",
            "DRY_RUN": True,
            "NO_GO": True,
            "production_status": "NO_GO",
            "wordpress_write_executed": False,
            "abort_reasons": [f"validator_exception: {exc}"],
            "fail_reasons": [],
            "warnings": [],
            "timestamp": _now_iso(),
            "next_step": "manual_security_review",
        }

    _write_result(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
