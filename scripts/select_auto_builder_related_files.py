#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/auto_builder_related_file_selector_policy.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/ab_t3_related_file_selector_result.json"
DEFAULT_REPORT = ROOT / "reports/ab_t3_related_file_selector_report.md"
DEFAULT_TARGET = ROOT / "scripts/build_auto_builder_copilot_prompt_compression.py"

REQUIRED_TOP_KEYS = {
    "phase",
    "status",
    "purpose",
    "execution_mode",
    "production_status",
    "safety_state",
    "selection_rules",
    "output_mode",
    "allowed_outputs",
    "forbidden_outputs",
    "copilot_send_allowed",
    "external_api_call_allowed",
    "wordpress_api_call_allowed",
    "credential_read_allowed",
    "credential_output_allowed",
    "production_write_allowed",
    "destructive_operation_allowed",
    "next_phase",
}

REQUIRED_RULE_KEYS = {
    "max_related_files",
    "max_lines_per_file",
    "prefer_same_directory",
    "prefer_matching_test_file",
    "prefer_matching_config",
    "exclude_patterns",
    "selection_priority",
    "minimum_score",
}

REQUIRED_PRIORITY = [
    "target_file",
    "matching_test",
    "matching_config",
    "same_directory",
    "shared_module",
    "documentation",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--target-file", default=str(DEFAULT_TARGET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_excluded(path: Path, root: Path, patterns: list[str]) -> bool:
    rel = path.relative_to(root).as_posix()
    for pattern in patterns:
        if pattern.endswith("/") and pattern in rel:
            return True
        if "*" in pattern and path.match(pattern):
            return True
        if pattern in rel:
            return True
    return False


def candidate_files(root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if is_excluded(path, root, patterns):
            continue
        files.append(path)
    return files


def reason_score(path: Path, target: Path, root: Path) -> tuple[float, str]:
    rel = path.relative_to(root).as_posix()
    target_rel = target.relative_to(root).as_posix() if target.exists() else target.as_posix()

    if rel == target_rel:
        return 1.00, "target_file"

    stem = target.stem
    if rel == f"tests/test_{stem}.py":
        return 0.95, "matching_test"

    if rel.startswith("config/") and "auto_builder" in rel and stem.replace("select_", "") in rel:
        return 0.90, "matching_config"

    if path.parent == target.parent:
        return 0.80, "same_directory"

    if "auto_builder" in rel and rel.startswith("scripts/"):
        return 0.70, "shared_module"

    if rel.lower().endswith(".md"):
        return 0.60, "documentation"

    return 0.0, ""


def validate_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = sorted(REQUIRED_TOP_KEYS - set(policy.keys()))
    if missing:
        errors.append(f"missing required top keys: {missing}")

    if policy.get("phase") != "AB-T3":
        errors.append("phase must be AB-T3")
    if policy.get("status") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        errors.append("status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    if policy.get("purpose") != "related_file_selector":
        errors.append("purpose must be related_file_selector")
    if policy.get("execution_mode") != "DESIGN_ONLY":
        errors.append("execution_mode must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if policy.get("safety_state") != "DRY_RUN_ONLY":
        errors.append("safety_state must be DRY_RUN_ONLY")
    if policy.get("output_mode") != "RELATED_FILE_LIST_ONLY":
        errors.append("output_mode must be RELATED_FILE_LIST_ONLY")

    for flag in [
        "copilot_send_allowed",
        "external_api_call_allowed",
        "wordpress_api_call_allowed",
        "credential_read_allowed",
        "credential_output_allowed",
        "production_write_allowed",
        "destructive_operation_allowed",
    ]:
        if policy.get(flag) is not False:
            errors.append(f"{flag} must be false")

    rules = policy.get("selection_rules")
    if not isinstance(rules, dict):
        errors.append("selection_rules must be object")
        return errors

    missing_rule = sorted(REQUIRED_RULE_KEYS - set(rules.keys()))
    if missing_rule:
        errors.append(f"missing selection_rules keys: {missing_rule}")

    if rules.get("max_related_files") != 5:
        errors.append("selection_rules.max_related_files must be 5")
    if rules.get("max_lines_per_file") != 120:
        errors.append("selection_rules.max_lines_per_file must be 120")

    if rules.get("prefer_same_directory") is not True:
        errors.append("selection_rules.prefer_same_directory must be true")
    if rules.get("prefer_matching_test_file") is not True:
        errors.append("selection_rules.prefer_matching_test_file must be true")
    if rules.get("prefer_matching_config") is not True:
        errors.append("selection_rules.prefer_matching_config must be true")

    if not isinstance(rules.get("exclude_patterns"), list) or not rules.get("exclude_patterns"):
        errors.append("selection_rules.exclude_patterns must be non-empty list")

    if rules.get("selection_priority") != REQUIRED_PRIORITY:
        errors.append("selection_rules.selection_priority mismatch")

    min_score = rules.get("minimum_score")
    if not isinstance(min_score, (int, float)) or min_score != 0.5:
        errors.append("selection_rules.minimum_score must be 0.50")

    next_phase = policy.get("next_phase")
    if not isinstance(next_phase, dict):
        errors.append("next_phase must be object")
    else:
        if next_phase.get("phase") != "AB-T4":
            errors.append("next_phase.phase must be AB-T4")
        if next_phase.get("execution_allowed") is not False:
            errors.append("next_phase.execution_allowed must be false")

    return errors


def build_related_file_list(root: Path, target: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    rules = policy["selection_rules"]
    min_score = float(rules["minimum_score"])
    max_files = int(rules["max_related_files"])
    patterns = list(rules["exclude_patterns"])

    ranked: list[tuple[float, str, Path]] = []
    for path in candidate_files(root, patterns):
        score, reason = reason_score(path, target, root)
        if score >= min_score:
            ranked.append((score, reason, path))

    # prioritize by declared priority, then score
    order = {name: idx for idx, name in enumerate(rules["selection_priority"])}
    ranked.sort(key=lambda item: (order.get(item[1], 999), -item[0], item[2].as_posix()))

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for score, reason, path in ranked:
        rel = path.relative_to(root).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        result.append(
            {
                "path": rel,
                "selection_score": round(score, 2),
                "selection_reason": reason,
            }
        )
        if len(result) >= max_files:
            break
    return result


def build_result(policy: dict[str, Any], target_file: str, related_files: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    rules = policy["selection_rules"]
    blocked = all(
        policy.get(key) is False
        for key in [
            "copilot_send_allowed",
            "external_api_call_allowed",
            "wordpress_api_call_allowed",
            "credential_read_allowed",
            "credential_output_allowed",
            "production_write_allowed",
            "destructive_operation_allowed",
        ]
    )
    final_status = "PASS_DESIGN_ONLY_NO_EXECUTION" if not errors and blocked else "NOT_READY"

    return {
        "phase": "AB-T3",
        "final_status": final_status,
        "execution_mode": policy.get("execution_mode"),
        "production_status": policy.get("production_status"),
        "safety_state": policy.get("safety_state"),
        "max_related_files": rules.get("max_related_files"),
        "max_lines_per_file": rules.get("max_lines_per_file"),
        "selection_rules_loaded": isinstance(policy.get("selection_rules"), dict),
        "excluded_patterns_loaded": isinstance(rules.get("exclude_patterns"), list) and len(rules.get("exclude_patterns", [])) > 0,
        "selector_ready": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "target_file": target_file,
        "generated_related_file_list": related_files,
        "forbidden_operations_all_blocked": blocked,
        "next_phase": policy.get("next_phase", {}),
        "ready_for_ab_t4": final_status == "PASS_DESIGN_ONLY_NO_EXECUTION",
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(report_path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# AB-T3 Related File Selector Report",
        "",
        f"- phase: {result['phase']}",
        f"- final_status: {result['final_status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- safety_state: {result['safety_state']}",
        f"- selector_ready: {result['selector_ready']}",
        f"- forbidden_operations_all_blocked: {result['forbidden_operations_all_blocked']}",
        f"- target_file: {result['target_file']}",
        "",
        "## Related Files",
    ]
    for item in result["generated_related_file_list"]:
        lines.append(f"- {item['path']} | score={item['selection_score']} | reason={item['selection_reason']}")

    lines.extend(
        [
            "",
            "## Next Phase",
            f"- phase: {result['next_phase'].get('phase')}",
            f"- name: {result['next_phase'].get('name')}",
            f"- execution_allowed: {result['next_phase'].get('execution_allowed')}",
            "",
            "## Errors",
        ]
    )

    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")

    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(policy_path: Path, target_file: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    policy = load_json(policy_path)
    errors = validate_policy(policy)

    target = target_file if target_file.is_absolute() else ROOT / target_file
    related_files = build_related_file_list(ROOT, target, policy)

    result = build_result(
        policy=policy,
        target_file=(target.relative_to(ROOT).as_posix() if target.exists() else target.as_posix()),
        related_files=related_files,
        errors=errors,
    )

    write_json(output_path, result)
    write_report(report_path, result)
    return result


def main() -> int:
    args = parse_args()
    result = run(Path(args.policy), Path(args.target_file), Path(args.output), Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
