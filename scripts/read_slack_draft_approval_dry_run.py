#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange/incoming/slack_draft_approval_dry_run.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_7_slack_approval_dry_run_result.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_slack_approval(data: dict) -> dict:
    errors = []
    warnings = []

    if data.get("source") != "SLACK_APPROVAL_DRY_RUN":
        errors.append("source must be SLACK_APPROVAL_DRY_RUN")
    if data.get("mode") != "CONNECTION_TEST":
        errors.append("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        errors.append("execution must be DRY_RUN")
    if data.get("human_approval_required") is not True:
        errors.append("human_approval_required must be true")

    if data.get("reserved_future_decision") != "APPROVE_DRAFT_CREATE_ONLY":
        errors.append("reserved_future_decision must be APPROVE_DRAFT_CREATE_ONLY")
    if data.get("reserved_future_decision_currently_allowed") is not False:
        errors.append("reserved_future_decision_currently_allowed must be false")

    if data.get("target_item_count") != 1:
        errors.append("target_item_count must be 1")
    if data.get("wordpress_draft_creation") != "NO_GO":
        errors.append("wordpress_draft_creation must be NO_GO")
    if data.get("wordpress_write_executed") is not False:
        errors.append("wordpress_write_executed must be false")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is not False:
            errors.append(f"{flag} must be false")

    if data.get("publish_allowed") is not False:
        errors.append("publish_allowed must be false")

    decision = str(data.get("decision", ""))
    if errors:
        status = "ABORT"
        next_step = "fix_phase6_7_slack_payload"
    elif decision == "APPROVE_DRY_RUN_ONLY":
        status = "PASS_DRY_RUN_ONLY"
        next_step = "phase6_8_runbook_validation"
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("human requested fix before next step")
        next_step = "apply_requested_fixes"
    elif decision == "REJECT":
        status = "FAIL"
        next_step = "stop_and_rework"
    elif decision == "ABORT":
        status = "ABORT"
        next_step = "abort"
    elif decision == "APPROVE_DRAFT_CREATE_ONLY":
        status = "ABORT"
        errors.append("APPROVE_DRAFT_CREATE_ONLY is reserved and not allowed in Phase 6-7")
        next_step = "keep_dry_run_only"
    else:
        status = "ABORT"
        errors.append(f"unknown decision: {decision}")
        next_step = "fix_decision_input"

    return {
        "phase": data.get("phase", "Phase 6-7"),
        "status": status,
        "decision": decision,
        "reserved_future_decision": data.get("reserved_future_decision"),
        "reserved_future_decision_currently_allowed": data.get("reserved_future_decision_currently_allowed"),
        "wordpress_draft_creation": data.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "errors": errors,
        "warnings": warnings,
        "next_step": next_step,
        "checked_at": _now_iso()
    }


def run_reader(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = {
            "phase": "Phase 6-7",
            "status": "ABORT",
            "decision": "ABORT",
            "reserved_future_decision": "APPROVE_DRAFT_CREATE_ONLY",
            "reserved_future_decision_currently_allowed": False,
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "errors": [f"input not found: {input_path}"],
            "warnings": [],
            "next_step": "create_phase6_7_input",
            "checked_at": _now_iso()
        }
    else:
        result = validate_slack_approval(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_reader()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_DRY_RUN_ONLY", "WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
