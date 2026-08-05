#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/wordpress_draft_candidate_review.json"
DEFAULT_INPUT_EXAMPLE = ROOT / "exchange/human_review/wordpress_draft_candidate_review.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/wordpress_draft_candidate_review_result.json"

ALLOWED_DECISIONS = {
    "APPROVE_DRY_RUN_ONLY",
    "REQUEST_FIX",
    "REJECT",
    "ABORT",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _base_result(status: str, decision: str, reason: str, next_step: str) -> dict:
    return {
        "package_type": "wordpress_draft_candidate_review_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": decision,
        "status": status,
        "reason": reason,
        "next_step": next_step,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def abort_result(reason: str) -> dict:
    return _base_result(
        status="ABORT",
        decision="ABORT",
        reason=reason,
        next_step="abort",
    )


def resolve_input_path(input_path: Path | None = None) -> Path:
    if input_path is not None:
        return Path(input_path)
    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT
    return DEFAULT_INPUT_EXAMPLE


def validate_safety_flags(data: dict) -> dict | None:
    if data.get("mode") != "CONNECTION_TEST":
        return abort_result("mode must be CONNECTION_TEST")

    if data.get("execution") != "DRY_RUN":
        return abort_result("execution must be DRY_RUN")

    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden")

    for flag in ["wordpress_write_executed", "slack_notification_executed", "github_actions_triggered"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in DRY_RUN")

    return None


def map_decision(decision: str) -> dict:
    if decision == "APPROVE_DRY_RUN_ONLY":
        return _base_result(
            status="PASS",
            decision=decision,
            reason="approved for draft candidate dry-run flow only",
            next_step="record_draft_candidate_approval_evidence",
        )

    if decision == "REQUEST_FIX":
        return _base_result(
            status="WARN",
            decision=decision,
            reason="human requested fixes for draft candidate",
            next_step="request_fix",
        )

    if decision == "REJECT":
        return _base_result(
            status="FAIL",
            decision=decision,
            reason="human rejected draft candidate",
            next_step="stop",
        )

    if decision == "ABORT":
        return _base_result(
            status="ABORT",
            decision=decision,
            reason="human selected ABORT",
            next_step="abort",
        )

    return abort_result(f"unknown decision: {decision}")


def read_wordpress_draft_candidate_review(
    input_path: Path | None = None,
    output_path: Path | None = None,
) -> dict:
    input_path = resolve_input_path(input_path)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = abort_result(f"review file not found: {input_path}")
    else:
        data = load_json(input_path)
        safety_error = validate_safety_flags(data)
        if safety_error:
            result = safety_error
        else:
            decision = str(data.get("decision"))
            if decision not in ALLOWED_DECISIONS:
                result = abort_result(f"unknown decision: {decision}")
            else:
                result = map_decision(decision)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = read_wordpress_draft_candidate_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "ABORT":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
