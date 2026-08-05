#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_release_policy.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_1_design_validation_result.json"

REQUIRED_TOP_LEVEL = {
    "phase",
    "policy_name",
    "mode",
    "execution",
    "policy_status",
    "production_status",
    "wordpress_draft_creation",
    "release_constraints",
    "pre_abort_conditions",
    "write_preflight_required_checks",
    "post_write_evidence_spec",
    "forbidden_during_phase6_1",
}

REQUIRED_FORBIDDEN = {
    "wordpress_rest_post",
    "wordpress_rest_put_patch",
    "publish_post",
    "update_existing_post",
    "delete_post",
    "bulk_posting",
    "cron_automation",
    "github_actions_trigger",
    "slack_production_notification",
    "vps_self_builder_execution",
    "env_secret_auto_edit",
}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_1_design_validation_result",
        "status": "ABORT",
        "reason": reason,
        "design_ready": False,
        "phase": "Phase 6-1",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_policy(data: dict) -> dict:
    missing = REQUIRED_TOP_LEVEL - set(data.keys())
    if missing:
        return _abort(f"missing required top-level fields: {sorted(missing)}")

    if data.get("phase") != "Phase 6-1":
        return _abort("phase must be Phase 6-1")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("policy_status") != "DESIGN_ONLY":
        return _abort("policy_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")

    constraints = data.get("release_constraints", {})
    required_constraints = {
        "single_item_only": True,
        "draft_only": True,
        "non_public_only": True,
        "requires_human_approval": True,
        "requires_quality_validation": True,
        "requires_affiliate_url_check": True,
        "requires_pr_label_check": True,
        "max_items_per_run": 1,
    }
    for key, expected in required_constraints.items():
        if constraints.get(key) != expected:
            return _abort(f"release_constraints.{key} must be {expected!r}")

    forbidden = set(data.get("forbidden_during_phase6_1", []))
    missing_forbidden = REQUIRED_FORBIDDEN - forbidden
    if missing_forbidden:
        return _abort(f"missing forbidden actions: {sorted(missing_forbidden)}")

    result = {
        "package_type": "phase6_1_design_validation_result",
        "status": "PASS",
        "reason": "phase6-1 design policy is valid and remains NO_GO for production actions",
        "design_ready": True,
        "phase": "Phase 6-1",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase6_2_preflight_gate_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"policy file not found: {input_path}")
    else:
        result = validate_policy(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
