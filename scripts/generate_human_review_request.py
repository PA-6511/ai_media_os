#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/logs/validation_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/human_review/review_required.json"

REVIEW_OPTIONS = [
    "APPROVE_DRY_RUN_ONLY",
    "REQUEST_FIX",
    "REJECT",
    "ABORT",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str):
    return {
        "status": "ABORT",
        "reason": reason,
        "review_required_generated": False,
    }


def validate_validation_result(data: dict):
    if data.get("mode") != "CONNECTION_TEST":
        return abort_result("mode must be CONNECTION_TEST")

    if data.get("execution") != "DRY_RUN":
        return abort_result("execution must be DRY_RUN")

    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden")

    for flag in [
        "wordpress_write_executed",
        "slack_notification_executed",
        "github_actions_triggered",
    ]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in DRY_RUN")

    return {
        "status": "PASS",
        "reason": "validation_result is safe for human_review generation",
    }


def build_review_request(data: dict, input_path: Path):
    overall_status = data.get("overall_status", "FAIL")
    results = data.get("results", [])

    return {
        "package_type": "human_review_request",
        "source": "exchange_connection_dry_run",
        "target": "human_operator",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "review_status": "REQUIRED",
        "overall_status": overall_status,
        "review_reason": f"overall_status={overall_status}; human review is required before any next step.",
        "review_options": REVIEW_OPTIONS,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "summary": {
            "result_count": len(results),
            "statuses": [
                {
                    "package_type": r.get("package_type"),
                    "status": r.get("status"),
                    "issues": r.get("issues", []),
                }
                for r in results
            ],
        },
        "source_validation_result": str(input_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "next_step": "human_operator_decision",
    }


def generate_review_request(input_path=None, output_path=None, overwrite=False):
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        return abort_result(f"validation_result not found: {input_path}")

    if output_path.exists() and not overwrite:
        return abort_result(f"review_required already exists: {output_path}")

    data = load_json(input_path)
    validation = validate_validation_result(data)
    if validation["status"] == "ABORT":
        return validation

    overall_status = data.get("overall_status", "FAIL")

    if overall_status == "PASS" and data.get("human_review_required") is not True:
        return {
            "status": "PASS",
            "reason": "human_review_required is false; no review file generated",
            "review_required_generated": False,
        }

    review_request = build_review_request(data, input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(review_request, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "status": overall_status,
        "reason": "review_required.json generated",
        "review_required_generated": True,
        "output_path": str(output_path),
    }


def main():
    result = generate_review_request()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
