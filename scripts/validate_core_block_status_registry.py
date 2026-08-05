#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FALSE_FLAGS = [
    "amazon_api_call_allowed",
    "wordpress_write_allowed",
    "x_api_call_allowed",
    "x_post_allowed",
    "publish_allowed",
    "approval_token_consumed",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(policy: dict, registry: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    require(policy.get("policy_id") == "CORE_BLOCK_STATUS_REGISTRY_POLICY_V1", "policy_id must be CORE_BLOCK_STATUS_REGISTRY_POLICY_V1", errors)
    require(policy.get("phase_pack") == "LS-2", "phase_pack must be LS-2", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)

    required_registry = policy.get("required_registry", {})
    for key, value in required_registry.items():
        require(registry.get(key) == value, f"registry {key} must be {value}", errors)

    safety_flags = policy.get("safety_flags", {})
    for key in REQUIRED_FALSE_FLAGS:
        require(safety_flags.get(key) is False, f"policy safety flag {key} must be false", errors)
        require(registry.get(key) is False, f"registry flag {key} must be false", errors)

    require(safety_flags.get("phase_forward_execution_allowed") is False, "phase_forward_execution_allowed must be false", errors)
    require(safety_flags.get("credential_secret_output_allowed") is False, "credential_secret_output_allowed must be false", errors)

    return not errors, errors


def write_report(result: dict, output_report: Path) -> None:
    checks = result["checks"]
    lines = [
        "# LS-2 Core AI Minimal Status Registry Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        "",
        "## Locked Registry",
        "",
        f"- block_ai: {checks['block_ai']}",
        f"- current_phase: {checks['current_phase']}",
        f"- next_action: {checks['next_action']}",
        f"- next_phase: {checks['next_phase']}",
        f"- next_phase_lock: {checks['next_phase_lock']}",
        "",
        "## Safety Confirmation",
        "",
        f"- amazon_api_call_allowed: {checks['amazon_api_call_allowed']}",
        f"- wordpress_write_allowed: {checks['wordpress_write_allowed']}",
        f"- x_api_call_allowed: {checks['x_api_call_allowed']}",
        f"- x_post_allowed: {checks['x_post_allowed']}",
        f"- publish_allowed: {checks['publish_allowed']}",
        f"- approval_token_consumed: {checks['approval_token_consumed']}",
        "",
        "## Next Phase",
        "",
        "Next recommended phase: LS-3 Core AI status observer linkage design only.",
        "",
    ]
    output_report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="core_ai/policies/core_block_status_registry_policy.json")
    parser.add_argument("--registry", default="core_ai/registries/block_status_registry.json")
    parser.add_argument("--output", default="exchange/logs/start_ls2_core_block_status_registry_result.json")
    parser.add_argument("--report", default="reports/start_ls2_core_block_status_registry_report.md")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    registry_path = Path(args.registry)
    output_path = Path(args.output)
    report_path = Path(args.report)

    policy = load_json(policy_path)
    registry = load_json(registry_path)
    ok, errors = validate(policy, registry)

    result = {
        "phase_pack": "LS-2",
        "status": policy.get("decision_rules", {}).get("registry_matches_required_state", "PASS_DESIGN_ONLY_NO_EXECUTION") if ok else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "checks": {
            "block_ai": registry.get("block_ai"),
            "current_phase": registry.get("current_phase"),
            "next_action": registry.get("next_action"),
            "next_phase": registry.get("next_phase"),
            "next_phase_lock": registry.get("next_phase_lock"),
            "amazon_api_call_allowed": False,
            "wordpress_write_allowed": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "publish_allowed": False,
            "approval_token_consumed": False,
        },
        "errors": errors,
        "next_phase": {
            "phase": "LS-3",
            "name": "Core AI status observer linkage",
            "execution_allowed": False,
            "recommended_next_action": "IMPLEMENT_OBSERVER_LINKAGE_DESIGN_ONLY",
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, report_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())