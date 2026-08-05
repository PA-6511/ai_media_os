#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "exchange/logs/human_review_diff.json"
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


def _collect_paths(before: object, after: object, base: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before.keys()) | set(after.keys()))
        paths: list[str] = []
        for key in keys:
            path = f"{base}.{key}" if base else key
            paths.extend(_collect_paths(before.get(key), after.get(key), path))
        return paths

    if isinstance(before, list) and isinstance(after, list):
        if before == after:
            return []
        return [base or "$"]

    if before != after:
        return [base or "$"]

    return []


def _get_by_path(payload: object, path: str):
    if path == "$":
        return payload
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _find_dangerous(payload: dict, label: str) -> list[str]:
    reasons: list[str] = []

    if payload.get("execution") == "LIVE":
        reasons.append(f"{label}.execution=LIVE is forbidden")

    for key in DANGEROUS_TRUE_FLAGS:
        if payload.get(key) is True:
            reasons.append(f"{label}.{key}=true is forbidden")

    side_effect_policy = payload.get("side_effect_policy")
    if isinstance(side_effect_policy, dict):
        for key in DANGEROUS_TRUE_FLAGS:
            if side_effect_policy.get(key) is True:
                reasons.append(f"{label}.side_effect_policy.{key}=true is forbidden")

    return reasons


def build_human_review_diff(before_json: dict, after_json: dict, reviewer_note: str = "") -> dict:
    dangerous = _find_dangerous(before_json, "before_json") + _find_dangerous(after_json, "after_json")
    changed_paths = _collect_paths(before_json, after_json)
    changed_fields = [
        {
            "path": path,
            "before": _get_by_path(before_json, path),
            "after": _get_by_path(after_json, path),
        }
        for path in changed_paths
    ]

    if dangerous:
        return {
            "package_type": "human_review_diff",
            "mode": "CONNECTION_TEST",
            "execution": "DRY_RUN",
            "human_review_required": True,
            "production_status": "NO_GO",
            "status": "ABORT",
            "reason": "dangerous operation detected",
            "before_json": before_json,
            "after_json": after_json,
            "changed_fields": changed_fields,
            "reviewer_note": reviewer_note,
            "details": dangerous,
            "created_at": _now_iso(),
        }

    return {
        "package_type": "human_review_diff",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_review_required": True,
        "production_status": "NO_GO",
        "status": "PASS",
        "reason": "human review diff captured",
        "before_json": before_json,
        "after_json": after_json,
        "changed_fields": changed_fields,
        "reviewer_note": reviewer_note,
        "created_at": _now_iso(),
    }


def generate_human_review_diff(
    before_path: Path,
    after_path: Path,
    output_path: Path | None = None,
    reviewer_note: str = "",
    overwrite: bool = False,
) -> dict:
    if output_path is not None and output_path.exists() and not overwrite:
        return {
            "status": "ABORT",
            "reason": f"output already exists: {output_path}",
            "review_diff_generated": False,
            "production_status": "NO_GO",
            "human_review_required": True,
            "created_at": _now_iso(),
        }

    before_json = _load_json(before_path)
    after_json = _load_json(after_path)
    diff = build_human_review_diff(before_json, after_json, reviewer_note=reviewer_note)
    diff["source_before"] = str(before_path)
    diff["source_after"] = str(after_path)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
        diff["output_path"] = str(output_path)

    diff["review_diff_generated"] = True
    return diff


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate human review diff JSON from before/after payloads.")
    parser.add_argument("before", help="Path to AI proposal JSON")
    parser.add_argument("after", help="Path to human-corrected JSON")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output file path (default: exchange/logs/human_review_diff.json)",
    )
    parser.add_argument("--reviewer-note", default="", help="Free text reviewer note")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output if exists")
    args = parser.parse_args()

    result = generate_human_review_diff(
        before_path=Path(args.before),
        after_path=Path(args.after),
        output_path=Path(args.output),
        reviewer_note=args.reviewer_note,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "ABORT":
        return 2
    if result["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())