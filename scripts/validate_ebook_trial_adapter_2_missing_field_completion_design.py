#!/usr/bin/env python3
"""EBOOK-TRIAL-ADAPTER-2: Missing Field Completion Design validator (DRY_RUN only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/ebook_trial_adapter_2_missing_field_completion_design_policy.json"
REQUEST = ROOT / "exchange/examples/ebook_trial_adapter_2_missing_field_completion_design_request.example.json"
OUTPUT = ROOT / "exchange/logs/ebook_trial_adapter_2_missing_field_completion_design_result.json"


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
        "phase": "EBOOK-TRIAL-ADAPTER-2",
        "phase_name": "Missing Field Completion Design / DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "design_only": True,
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
        "missing_field_design": [],
        "invalid_layer_design": [],
        "adapter1_evidence_exists": False,
        "adapter1_status": None,
    }

    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "EBOOK_TRIAL_ADAPTER_2_ABORT_INPUT_LOAD_ERROR_NO_EXECUTION",
            "policy_violations": [f"input_load_error: {exc}"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    violations: list[str] = []
    missing_design: list[str] = []
    invalid_layers: list[str] = []

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
    adapter1_rel = str(policy.get("adapter1_evidence_path", ""))
    adapter1_path = root / adapter1_rel
    adapter1_status = None
    if adapter1_path.exists():
        try:
            adapter1_status = str(_load_json(adapter1_path).get("status"))
        except Exception:
            adapter1_status = None

    required_adapter1_status = str(policy.get("adapter1_required_status", ""))
    if not adapter1_path.exists():
        violations.append("adapter1_evidence_missing")
    elif adapter1_status != required_adapter1_status:
        violations.append("adapter1_status_not_matched")

    field_design = request.get("field_design", {})
    if not isinstance(field_design, dict):
        field_design = {}

    required_fields = [str(x) for x in policy.get("required_fields", [])]
    allowed_generation_layers = {str(x) for x in policy.get("allowed_generation_layers", [])}
    allowed_validation_layers = {str(x) for x in policy.get("allowed_validation_layers", [])}

    for field in required_fields:
        spec = field_design.get(field)
        if not isinstance(spec, dict):
            missing_design.append(field)
            continue

        gen = str(spec.get("generation_layer", ""))
        val = str(spec.get("validation_layer", ""))
        lock_rule = str(spec.get("lock_rule", "")).strip()

        if gen not in allowed_generation_layers:
            invalid_layers.append(f"{field}.generation_layer")
        if val not in allowed_validation_layers:
            invalid_layers.append(f"{field}.validation_layer")
        if not lock_rule:
            violations.append(f"{field}.lock_rule must be non-empty")

    status = "EBOOK_TRIAL_ADAPTER_2_MISSING_FIELD_COMPLETION_DESIGN_PASS_DRY_RUN"
    if violations:
        status = "EBOOK_TRIAL_ADAPTER_2_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    elif missing_design or invalid_layers:
        status = "EBOOK_TRIAL_ADAPTER_2_BLOCKED_DESIGN_INCOMPLETE_NO_EXECUTION"

    result = {
        **base,
        "status": status,
        "policy_violations": violations,
        "missing_field_design": missing_design,
        "invalid_layer_design": invalid_layers,
        "adapter1_evidence_exists": adapter1_path.exists(),
        "adapter1_status": adapter1_status,
        "required_fields": required_fields,
        "designed_fields": sorted(field_design.keys()),
        "next_step": "KEEP_DRY_RUN_AND_UPDATE_ADAPTER_1_INPUT_BUILDER" if status.endswith("PASS_DRY_RUN") else "FIX_DESIGN_ONLY_AND_REVALIDATE",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "EBOOK_TRIAL_ADAPTER_2_MISSING_FIELD_COMPLETION_DESIGN_PASS_DRY_RUN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
