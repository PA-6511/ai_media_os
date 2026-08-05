#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "exchange/logs/decision_reason_validation_result.json"
ALLOWED_STATUS = {"PASS", "WARN", "FAIL", "ABORT"}
STRICT_REASON_STATUS = {"WARN", "FAIL", "ABORT"}
DANGEROUS_TRUE_FLAGS = {
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "wordpress_write",
    "external_send",
    "wordpress_write_executed",
    "slack_notification_executed",
    "github_actions_triggered",
    "vps_execution",
    "production_reflection",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_blank(value: object) -> bool:
    return not isinstance(value, str) or value.strip() == ""


def _find_dangerous_reasons(payload: dict) -> list[str]:
    reasons: list[str] = []

    if payload.get("execution") == "LIVE":
        reasons.append("execution=LIVE is forbidden")

    for key in DANGEROUS_TRUE_FLAGS:
        if payload.get(key) is True:
            reasons.append(f"{key}=true is forbidden")

    side_effect_policy = payload.get("side_effect_policy")
    if isinstance(side_effect_policy, dict):
        for key in DANGEROUS_TRUE_FLAGS:
            if side_effect_policy.get(key) is True:
                reasons.append(f"side_effect_policy.{key}=true is forbidden")

    return reasons


def validate_reason_payload(payload: dict, package_type: str = "unknown") -> dict:
    status = payload.get("status")
    reason = payload.get("reason")
    summary_reason = payload.get("summary_reason")
    dangerous = _find_dangerous_reasons(payload)

    if dangerous:
        return {
            "status": "ABORT",
            "reason": "dangerous operation detected",
            "package_type": package_type,
            "details": dangerous,
            "human_review_required": True,
            "production_status": "NO_GO",
            "created_at": _now_iso(),
        }

    if status not in ALLOWED_STATUS:
        return {
            "status": "FAIL",
            "reason": "status must be one of PASS/WARN/FAIL/ABORT",
            "package_type": package_type,
            "details": [f"status={status!r}"],
            "human_review_required": True,
            "production_status": "NO_GO",
            "created_at": _now_iso(),
        }

    if "reason" in payload and _is_blank(reason):
        return {
            "status": "FAIL",
            "reason": "reason must not be empty",
            "package_type": package_type,
            "details": ["reason is blank"],
            "human_review_required": True,
            "production_status": "NO_GO",
            "created_at": _now_iso(),
        }

    if status in STRICT_REASON_STATUS and _is_blank(reason):
        return {
            "status": "FAIL",
            "reason": f"reason is required when status={status}",
            "package_type": package_type,
            "details": ["reason missing for non-pass status"],
            "human_review_required": True,
            "production_status": "NO_GO",
            "created_at": _now_iso(),
        }

    if status == "PASS" and _is_blank(reason) and _is_blank(summary_reason):
        return {
            "status": "WARN",
            "reason": "PASS should include reason or summary_reason",
            "package_type": package_type,
            "details": ["reason and summary_reason are both missing"],
            "human_review_required": True,
            "production_status": "NO_GO",
            "created_at": _now_iso(),
        }

    return {
        "status": "PASS",
        "reason": "reason validation passed",
        "package_type": package_type,
        "details": [],
        "human_review_required": True,
        "production_status": "NO_GO",
        "created_at": _now_iso(),
    }


def validate_reason_file(input_path: Path, output_path: Path | None = None) -> dict:
    payload = _load_json(input_path)
    package_type = str(payload.get("package_type", "unknown"))
    result = validate_reason_payload(payload, package_type=package_type)
    result["input_path"] = str(input_path)

    if output_path is None:
        return result

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate reason fields in decision/review/approval packages.")
    parser.add_argument("input", help="Path to target JSON file")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to validation result JSON (default: exchange/logs/decision_reason_validation_result.json)",
    )
    args = parser.parse_args()

    result = validate_reason_file(Path(args.input), Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())