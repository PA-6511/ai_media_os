#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/human_decision.json"
DEFAULT_INPUT_EXAMPLE = ROOT / "exchange/human_review/human_decision.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/human_decision_result.json"

ALLOWED_DECISIONS = {
    "APPROVE_DRY_RUN_ONLY",
    "REQUEST_FIX",
    "REJECT",
    "ABORT",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def result_abort(reason: str):
    return {
        "package_type": "human_decision_result",
        "source": "read_human_review_decision",
        "target": "core_consensus_ai",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": "ABORT",
        "status": "ABORT",
        "reason": reason,
        "next_step": "abort",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_safety_flags(data: dict):
    if data.get("mode") != "CONNECTION_TEST":
        return result_abort("mode must be CONNECTION_TEST")

    if data.get("execution") != "DRY_RUN":
        return result_abort("execution must be DRY_RUN")

    if data.get("human_approval_required") is not True:
        return result_abort("human_approval_required must be true")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return result_abort(f"{flag}=true is forbidden")

    for flag in [
        "wordpress_write_executed",
        "slack_notification_executed",
        "github_actions_triggered",
    ]:
        if data.get(flag) is True:
            return result_abort(f"{flag}=true is forbidden in DRY_RUN")

    return None


def map_decision(decision: str):
    if decision == "APPROVE_DRY_RUN_ONLY":
        return {
            "status": "PASS",
            "next_step": "record_dry_run_evidence",
            "reason": "approved for DRY_RUN evidence only",
        }

    if decision == "REQUEST_FIX":
        return {
            "status": "WARN",
            "next_step": "request_fix",
            "reason": "human requested fixes before next step",
        }

    if decision == "REJECT":
        return {
            "status": "FAIL",
            "next_step": "stop",
            "reason": "human rejected the review request",
        }

    if decision == "ABORT":
        return {
            "status": "ABORT",
            "next_step": "abort",
            "reason": "human selected ABORT",
        }

    return {
        "status": "ABORT",
        "next_step": "abort",
        "reason": f"unknown decision: {decision}",
    }


def resolve_input_path(input_path=None) -> Path:
    if input_path:
        return Path(input_path)
    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT
    return DEFAULT_INPUT_EXAMPLE


def read_human_decision(input_path=None, output_path=None):
    input_path = resolve_input_path(input_path)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = result_abort(f"human_decision not found: {input_path}")
    else:
        data = load_json(input_path)
        safety_error = validate_safety_flags(data)

        if safety_error:
            result = safety_error
        else:
            decision = str(data.get("decision"))
            mapped = map_decision(decision) if decision in ALLOWED_DECISIONS else map_decision(decision)

            result = {
                "package_type": "human_decision_result",
                "source": "read_human_review_decision",
                "target": "core_consensus_ai",
                "mode": "CONNECTION_TEST",
                "execution": "DRY_RUN",
                "human_approval_required": True,
                "decision": decision,
                "status": mapped["status"],
                "reason": mapped["reason"],
                "next_step": mapped["next_step"],
                "auto_post": False,
                "auto_update": False,
                "auto_delete": False,
                "auto_export": False,
                "wordpress_write_executed": False,
                "slack_notification_executed": False,
                "github_actions_triggered": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return result


def main():
    result = read_human_decision()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
