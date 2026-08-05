#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/slack_approval_action.json"
DEFAULT_INPUT_EXAMPLE = ROOT / "exchange/human_review/slack_approval_action.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/slack_approval_action_validation_result.json"

ALLOWED_ACTIONS = {"approved", "request_fix", "rejected", "abort"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _abort(reason: str) -> dict:
    return {
        "package_type": "slack_approval_action_validation_result",
        "status": "ABORT",
        "reason": reason,
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "production_status": "NO_GO",
        "created_at": _now_iso(),
    }


def _fail(reason: str) -> dict:
    return {
        "package_type": "slack_approval_action_validation_result",
        "status": "FAIL",
        "reason": reason,
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "production_status": "NO_GO",
        "created_at": _now_iso(),
    }


def _map_action(action: str) -> tuple[str, str]:
    if action == "approved":
        return "PASS", "record_approval_evidence"
    if action == "request_fix":
        return "WARN", "request_fix"
    if action == "rejected":
        return "FAIL", "stop"
    return "ABORT", "abort"


def validate_slack_approval_action_payload(payload: dict) -> dict:
    required = ["action", "decision_id", "reason", "source"]
    missing = [key for key in required if key not in payload]
    if missing:
        return _fail(f"missing required fields: {missing}")

    if not isinstance(payload.get("reason"), str) or payload["reason"].strip() == "":
        return _fail("reason must be a non-empty string")

    if payload.get("source") != "slack_button_dry_run":
        return _fail("source must be slack_button_dry_run")

    action = str(payload.get("action"))
    if action not in ALLOWED_ACTIONS:
        return _fail(f"action must be one of {sorted(ALLOWED_ACTIONS)}")

    # DRY_RUN / NO_GO 制約（値が存在する場合は厳格に確認）
    if "mode" in payload and payload.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")

    if "execution" in payload and payload.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")

    if "human_approval_required" in payload and payload.get("human_approval_required") is not True:
        return _abort("human_approval_required must be true")

    if "production_status" in payload and payload.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if payload.get(flag) is True:
            return _abort(f"{flag}=true is forbidden")

    for flag in ["wordpress_write_executed", "slack_notification_executed", "github_actions_triggered"]:
        if payload.get(flag) is True:
            return _abort(f"{flag}=true is forbidden in DRY_RUN")

    status, next_step = _map_action(action)
    return {
        "package_type": "slack_approval_action_validation_result",
        "status": status,
        "reason": "slack approval action is valid",
        "action": action,
        "decision_id": payload.get("decision_id"),
        "review_reason": payload.get("reason"),
        "source": payload.get("source"),
        "next_step": next_step,
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "production_status": "NO_GO",
        "created_at": _now_iso(),
    }


def _resolve_input_path(path: str | None) -> Path:
    if path:
        return Path(path)
    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT
    return DEFAULT_INPUT_EXAMPLE


def validate_slack_approval_action(input_path: str | None = None, output_path: str | None = None) -> dict:
    resolved_input = _resolve_input_path(input_path)
    resolved_output = Path(output_path or DEFAULT_OUTPUT)

    if not resolved_input.exists():
        result = _abort(f"slack_approval_action file not found: {resolved_input}")
    else:
        payload = _load_json(resolved_input)
        result = validate_slack_approval_action_payload(payload)

    result["input_path"] = str(resolved_input)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(resolved_output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Slack approval dry-run action JSON.")
    parser.add_argument("input", nargs="?", default=None, help="Input JSON path")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path (default: exchange/logs/slack_approval_action_validation_result.json)",
    )
    args = parser.parse_args()

    result = validate_slack_approval_action(input_path=args.input, output_path=args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())