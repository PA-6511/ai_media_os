#!/usr/bin/env python3
"""EBOOK-TRIAL-ADAPTER-4: Completion payload validation (preflight contract check)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/ebook_trial_adapter_4_completion_payload_validation_policy.json"
REQUEST = ROOT / "exchange/examples/ebook_trial_adapter_4_completion_payload_validation_request.example.json"
OUTPUT = ROOT / "exchange/logs/ebook_trial_adapter_4_completion_payload_validation_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def validate(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_path = Path(output_path)

    base = {
        "phase": "EBOOK-TRIAL-ADAPTER-4",
        "phase_name": "Completion Payload Validation / Preflight Contract Check",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "executed_external_changes": 0,
        "validated_at": _now_iso(),
        "policy_violations": [],
        "missing_contract_fields": [],
        "false_contract_flags": [],
        "adapter3_evidence_exists": False,
        "adapter3_status": None,
        "contract_payload_checked": False,
    }

    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "EBOOK_TRIAL_ADAPTER_4_ABORT_INPUT_LOAD_ERROR_NO_EXECUTION",
            "policy_violations": [f"input_load_error: {exc}"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    violations: list[str] = []
    missing_fields: list[str] = []
    false_flags: list[str] = []

    if request.get("mode") != "CONNECTION_TEST":
        violations.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        violations.append("request.production_status must be NO_GO")
    if request.get("design_only") is not True:
        violations.append("request.design_only must be true")

    for flag in policy.get("required_false_flags", []):
        if request.get(flag) is not False:
            violations.append(f"request.{flag} must be false")

    root = _resolve_root(policy_path)
    adapter3_path = root / str(policy.get("adapter3_evidence_path", ""))
    adapter3_status = None
    completion_payload: dict[str, Any] = {}
    if not adapter3_path.exists():
        violations.append("adapter3_evidence_missing")
    else:
        try:
            adapter3_data = _load_json(adapter3_path)
            adapter3_status = str(adapter3_data.get("status"))
            completion_payload = adapter3_data.get("completion_payload", {})
            if not isinstance(completion_payload, dict):
                completion_payload = {}
        except Exception:
            violations.append("adapter3_evidence_unreadable")

    required_adapter3_status = str(policy.get("adapter3_required_status", ""))
    if adapter3_status is not None and adapter3_status != required_adapter3_status:
        violations.append("adapter3_status_not_matched")

    required_scalars = [str(x) for x in policy.get("required_scalar_fields", [])]
    required_flags = [str(x) for x in policy.get("required_contract_flags", [])]

    if completion_payload:
        for key in required_scalars:
            val = completion_payload.get(key)
            if not isinstance(val, str) or not val.strip():
                missing_fields.append(key)

        schema = completion_payload.get("target_item_schema")
        if not isinstance(schema, dict):
            missing_fields.append("target_item_schema")
        elif str(schema.get("schema_version", "")).strip() == "":
            missing_fields.append("target_item_schema.schema_version")

        dup = completion_payload.get("duplicate_check")
        if not isinstance(dup, dict):
            missing_fields.append("duplicate_check")

        for flag in required_flags:
            if flag not in completion_payload:
                missing_fields.append(flag)
                continue
            if completion_payload.get(flag) is not True:
                false_flags.append(flag)
    else:
        if "adapter3_evidence_missing" not in violations and "adapter3_evidence_unreadable" not in violations:
            violations.append("completion_payload_missing")

    status = "EBOOK_TRIAL_ADAPTER_4_PREFLIGHT_CONTRACT_PASS_DRY_RUN_NO_EXECUTION"
    if violations:
        status = "EBOOK_TRIAL_ADAPTER_4_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    elif missing_fields or false_flags:
        status = "EBOOK_TRIAL_ADAPTER_4_BLOCKED_CONTRACT_MISMATCH_NO_EXECUTION"

    result = {
        **base,
        "status": status,
        "policy_violations": violations,
        "missing_contract_fields": missing_fields,
        "false_contract_flags": false_flags,
        "adapter3_evidence_exists": adapter3_path.exists(),
        "adapter3_status": adapter3_status,
        "contract_payload_checked": bool(completion_payload),
        "next_step": "READY_FOR_PHASE8_38_REQUEST_MAPPING_DRY_RUN_ONLY" if status.endswith("PASS_DRY_RUN_NO_EXECUTION") else "FIX_CONTRACT_OR_INPUT_AND_REVALIDATE",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "EBOOK_TRIAL_ADAPTER_4_PREFLIGHT_CONTRACT_PASS_DRY_RUN_NO_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
