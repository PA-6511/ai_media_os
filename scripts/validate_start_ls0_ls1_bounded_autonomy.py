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


def validate(route: dict, charter: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    require(route.get("route_id") == "START-LS/SR", "route_id must be START-LS/SR", errors)
    require(route.get("current_phase_pack") == "LS-0_LS-1", "current_phase_pack must be LS-0_LS-1", errors)
    require(route.get("execution_mode") == "DRY_RUN_ONLY", "route execution_mode must be DRY_RUN_ONLY", errors)
    require(route.get("production_status") == "NO_GO", "route production_status must be NO_GO", errors)

    baseline = route.get("baseline", {})
    require(baseline.get("source_phase") == "Phase 8-50B", "baseline source_phase must be Phase 8-50B", errors)
    require(
        baseline.get("source_status") == "PHASE8_50B_HARDENING_PASS_DRY_RUN_ONLY",
        "baseline source_status must be PHASE8_50B_HARDENING_PASS_DRY_RUN_ONLY",
        errors,
    )
    require(baseline.get("next_action") == "KEEP_HOLD_AND_MONITOR", "baseline next_action must be KEEP_HOLD_AND_MONITOR", errors)
    require(baseline.get("next_phase_lock") == "NOT_STARTED_LOCKED", "baseline next_phase_lock must be NOT_STARTED_LOCKED", errors)

    safety_flags = route.get("safety_flags", {})
    for key in REQUIRED_FALSE_FLAGS:
        require(safety_flags.get(key) is False, f"route safety flag {key} must be false", errors)

    require(safety_flags.get("phase_forward_execution_allowed") is False, "phase_forward_execution_allowed must be false", errors)
    require(safety_flags.get("credential_secret_output_allowed") is False, "credential_secret_output_allowed must be false", errors)

    phases = {item.get("phase"): item for item in route.get("ls_phases", [])}
    require("LS-0" in phases, "LS-0 must exist", errors)
    require("LS-1" in phases, "LS-1 must exist", errors)
    for phase_name in ("LS-0", "LS-1"):
        require(phases.get(phase_name, {}).get("execution_allowed") is False, f"{phase_name} execution_allowed must be false", errors)

    require(charter.get("charter_id") == "CORE_BLOCK_BOUNDED_AUTONOMY_CHARTER_V1", "unexpected charter_id", errors)
    require(charter.get("status") == "DESIGN_ONLY_NO_EXECUTION", "charter status must be DESIGN_ONLY_NO_EXECUTION", errors)

    core_role = charter.get("core_ai_role", {})
    require(core_role.get("primary_role") == "manager_administrator", "Core AI primary_role must be manager_administrator", errors)
    require(core_role.get("not_role") == "ruler_governor", "Core AI not_role must be ruler_governor", errors)

    block_role = charter.get("block_ai_role", {})
    require(block_role.get("primary_role") == "domain_autonomous_operator", "Block AI primary_role must be domain_autonomous_operator", errors)
    require("as freely as possible" in block_role.get("autonomy_principle", ""), "Block AI autonomy principle must preserve freedom", errors)

    audit_role = charter.get("audit_block_ai_role", {})
    require(audit_role.get("primary_role") == "read_only_balance_observer", "Audit Block AI must be read_only_balance_observer", errors)
    require(audit_role.get("improvement_application_requires_human_approval") is True, "Audit improvement must require human approval", errors)

    guards = charter.get("execution_guards", {})
    for key in REQUIRED_FALSE_FLAGS:
        require(guards.get(key) is False, f"charter execution guard {key} must be false", errors)

    principles = " ".join(charter.get("fixed_principles", []))
    require("manager/administrator" in principles, "fixed principles must state Core AI is manager/administrator", errors)
    require("not a ruler/governor" in principles, "fixed principles must state Core AI is not ruler/governor", errors)
    require("Human approval" in principles, "fixed principles must require Human approval for audit improvements", errors)

    return not errors, errors


def write_report(result: dict, output_report: Path) -> None:
    checks = result["checks"]
    lines = [
        "# START-LS LS-0 / LS-1 Bounded Autonomy Charter Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        "",
        "## Locked Scope",
        "",
        "- LS-0: 8-50B Baseline Lock",
        "- LS-1: Minimum Bounded Autonomy Charter",
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
        "## Governance Principle",
        "",
        "Core AI is fixed as a manager/administrator, not a ruler/governor.",
        "Block AI autonomy is preserved within approved domain and safety boundaries.",
        "Audit Block AI observes Core AI balance as read-only by default.",
        "Audit improvement application requires Human approval.",
        "",
        "## Next Phase",
        "",
        "Next recommended phase: LS-2 Core AI minimal block status registry.",
        "",
    ]
    output_report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-policy", default="config/start_ls_route_policy.json")
    parser.add_argument("--charter", default="core_ai/config/bounded_autonomy_charter.json")
    parser.add_argument("--output", default="exchange/logs/start_ls0_ls1_bounded_autonomy_result.json")
    parser.add_argument("--report", default="reports/start_ls0_ls1_bounded_autonomy_charter_report.md")
    args = parser.parse_args()

    route_path = Path(args.route_policy)
    charter_path = Path(args.charter)
    output_path = Path(args.output)
    report_path = Path(args.report)

    route = load_json(route_path)
    charter = load_json(charter_path)
    ok, errors = validate(route, charter)

    result = {
        "phase_pack": "START-LS LS-0/LS-1",
        "status": "PASS_DESIGN_ONLY_NO_EXECUTION" if ok else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "checks": {
            "amazon_api_call_allowed": False,
            "wordpress_write_allowed": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "publish_allowed": False,
            "approval_token_consumed": False,
            "core_ai_role": "manager_administrator_not_ruler_governor",
            "block_ai_autonomy": "preserved_within_approved_boundaries",
            "audit_block_ai": "read_only_balance_observer",
            "human_approval_required_for_audit_improvements": True,
        },
        "errors": errors,
        "next_phase": {
            "phase": "LS-2",
            "name": "Core AI minimal block status registry",
            "execution_allowed": False,
            "recommended_next_action": "IMPLEMENT_REGISTRY_DESIGN_ONLY",
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