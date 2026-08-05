#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_execution_spec.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_5_execution_spec_validation_result.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_execution_spec(data: dict) -> dict:
    errors = []
    warnings = []

    if data.get("phase") != "Phase 6-5":
        errors.append("phase must be Phase 6-5")
    if data.get("spec_status") != "DESIGN_ONLY":
        errors.append("spec_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if data.get("mode") != "CONNECTION_TEST":
        errors.append("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        errors.append("execution must be DRY_RUN")
    if data.get("human_approval_required") is not True:
        errors.append("human_approval_required must be true")
    if data.get("wordpress_draft_creation") != "NO_GO":
        errors.append("wordpress_draft_creation must be NO_GO")
    if data.get("wordpress_write_executed") is not False:
        errors.append("wordpress_write_executed must be false")

    rest = data.get("wordpress_rest_api", {})
    for key in ["post_allowed", "put_allowed", "patch_allowed", "delete_allowed"]:
        if rest.get(key) is not False:
            errors.append(f"wordpress_rest_api.{key} must be false")

    dangerous = data.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            errors.append(f"dangerous_operations.{key} must be false")

    token = data.get("future_reserved_decision_token", {})
    if token.get("token") != "APPROVE_DRAFT_CREATE_ONLY":
        errors.append("future_reserved_decision_token.token must be APPROVE_DRAFT_CREATE_ONLY")
    if token.get("currently_allowed") is not False:
        errors.append("future_reserved_decision_token.currently_allowed must be false")

    limit = data.get("single_item_limit", {})
    if limit.get("enabled") is not True:
        errors.append("single_item_limit.enabled must be true")
    if limit.get("max_items") != 1:
        errors.append("single_item_limit.max_items must be 1")
    if limit.get("bulk_run_allowed") is not False:
        errors.append("single_item_limit.bulk_run_allowed must be false")

    scope = data.get("allowed_future_scope", {})
    if scope.get("create_wordpress_draft_only") is not True:
        errors.append("allowed_future_scope.create_wordpress_draft_only must be true")
    for key in ["publish", "update_existing_post", "delete_post", "export"]:
        if scope.get(key) is not False:
            errors.append(f"allowed_future_scope.{key} must be false")

    status = "PASS_DRY_RUN_ONLY" if not errors else "ABORT"

    return {
        "phase": "Phase 6-5",
        "status": status,
        "production_status": data.get("production_status", "NO_GO"),
        "wordpress_draft_creation": data.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "checked_at": _now_iso(),
        "errors": errors,
        "warnings": warnings,
        "next_step": "phase6_6_quality_gate_validation" if status == "PASS_DRY_RUN_ONLY" else "fix_phase6_5_execution_spec"
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = {
            "phase": "Phase 6-5",
            "status": "ABORT",
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "checked_at": _now_iso(),
            "errors": [f"config not found: {input_path}"],
            "warnings": [],
            "next_step": "create_phase6_5_execution_spec"
        }
    else:
        result = validate_execution_spec(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_DRY_RUN_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
