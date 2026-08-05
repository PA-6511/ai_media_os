#!/usr/bin/env python3
"""EBOOK-TRIAL-ADAPTER-5: Phase 8-38 request mapping confirmation (DRY_RUN)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/ebook_trial_adapter_5_phase8_38_request_mapping_policy.json"
REQUEST = ROOT / "exchange/examples/ebook_trial_adapter_5_phase8_38_request_mapping_request.example.json"
OUTPUT = ROOT / "exchange/logs/ebook_trial_adapter_5_phase8_38_request_mapping_result.json"


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
        "phase": "EBOOK-TRIAL-ADAPTER-5",
        "phase_name": "Phase 8-38 Request Mapping Confirmation / DRY_RUN",
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
        "mapping_missing_keys": [],
        "mapping_false_flags": [],
        "adapter3_evidence_exists": False,
        "adapter4_evidence_exists": False,
        "adapter3_status": None,
        "adapter4_status": None,
        "mapped_request_output": None,
    }

    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "EBOOK_TRIAL_ADAPTER_5_ABORT_INPUT_LOAD_ERROR_NO_EXECUTION",
            "policy_violations": [f"input_load_error: {exc}"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    violations: list[str] = []
    missing_keys: list[str] = []
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
    adapter4_path = root / str(policy.get("adapter4_evidence_path", ""))
    adapter3_path = root / str(policy.get("adapter3_evidence_path", ""))
    template_path = root / str(policy.get("phase8_38_template_path", ""))

    adapter4_status = None
    adapter3_status = None
    completion_payload: dict[str, Any] = {}
    template: dict[str, Any] = {}

    if not adapter4_path.exists():
        violations.append("adapter4_evidence_missing")
    else:
        try:
            adapter4_status = str(_load_json(adapter4_path).get("status"))
        except Exception:
            violations.append("adapter4_evidence_unreadable")

    if not adapter3_path.exists():
        violations.append("adapter3_evidence_missing")
    else:
        try:
            adapter3_data = _load_json(adapter3_path)
            adapter3_status = str(adapter3_data.get("status"))
            cp = adapter3_data.get("completion_payload", {})
            completion_payload = cp if isinstance(cp, dict) else {}
        except Exception:
            violations.append("adapter3_evidence_unreadable")

    if not template_path.exists():
        violations.append("phase8_38_template_missing")
    else:
        try:
            t = _load_json(template_path)
            template = t if isinstance(t, dict) else {}
        except Exception:
            violations.append("phase8_38_template_unreadable")

    if adapter4_status and adapter4_status != str(policy.get("adapter4_required_status", "")):
        violations.append("adapter4_status_not_matched")
    if adapter3_status and adapter3_status != str(policy.get("adapter3_required_status", "")):
        violations.append("adapter3_status_not_matched")

    mapped_request = None
    mapped_output_rel = str(request.get("mapped_request_output") or "exchange/logs/ebook_trial_adapter_5_phase8_38_mapped_request.json")
    mapped_output_path = root / mapped_output_rel

    if not violations:
        mapped_request = dict(template)
        mapped_request["mode"] = "CONNECTION_TEST"
        mapped_request["execution"] = "DRY_RUN"
        mapped_request["production_status"] = "NO_GO"
        mapped_request["human_approval_present"] = False

        for key in policy.get("required_mapped_true_flags", []):
            if key not in completion_payload:
                missing_keys.append(str(key))
            mapped_request[str(key)] = bool(completion_payload.get(key, False))

        mapped_request["one_shot_lock_exists_simulated"] = bool(request.get("one_shot_lock_exists_simulated", False))

        for flag in policy.get("required_false_flags", []):
            mapped_request[str(flag)] = False

        for key in ("title", "target", "reason"):
            val = completion_payload.get(key)
            if not isinstance(val, str) or not val.strip():
                missing_keys.append(key)

        for key in policy.get("required_mapped_true_flags", []):
            if mapped_request.get(str(key)) is not True:
                false_flags.append(str(key))

    status = "EBOOK_TRIAL_ADAPTER_5_PHASE8_38_REQUEST_MAPPING_PASS_DRY_RUN_NO_EXECUTION"
    if violations:
        status = "EBOOK_TRIAL_ADAPTER_5_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    elif missing_keys or false_flags:
        status = "EBOOK_TRIAL_ADAPTER_5_BLOCKED_MAPPING_MISMATCH_NO_EXECUTION"

    if status.endswith("PASS_DRY_RUN_NO_EXECUTION") and mapped_request is not None:
        mapped_output_path.parent.mkdir(parents=True, exist_ok=True)
        mapped_output_path.write_text(json.dumps(mapped_request, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        **base,
        "status": status,
        "policy_violations": violations,
        "mapping_missing_keys": sorted(set(missing_keys)),
        "mapping_false_flags": sorted(set(false_flags)),
        "adapter3_evidence_exists": adapter3_path.exists(),
        "adapter4_evidence_exists": adapter4_path.exists(),
        "adapter3_status": adapter3_status,
        "adapter4_status": adapter4_status,
        "mapped_request_output": mapped_output_rel if status.endswith("PASS_DRY_RUN_NO_EXECUTION") else None,
        "next_step": "KEEP_DRY_RUN_AND_VALIDATE_PHASE8_38_REQUEST_ONLY" if status.endswith("PASS_DRY_RUN_NO_EXECUTION") else "FIX_MAPPING_OR_INPUT_AND_REVALIDATE",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "EBOOK_TRIAL_ADAPTER_5_PHASE8_38_REQUEST_MAPPING_PASS_DRY_RUN_NO_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
