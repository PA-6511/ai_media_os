#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_8_single_draft_create_simulation_policy.json"
DEFAULT_INPUT = ROOT / "exchange/examples/phase7_8_single_draft_create_simulation_input.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_8_single_draft_create_simulation_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_8_single_draft_create_simulation_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _is_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def run_simulation(
    policy_path: Path = DEFAULT_POLICY,
    input_path: Path = DEFAULT_INPUT,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    input_path = Path(input_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    policy = _load_json(policy_path) if policy_path.exists() else {}
    payload_input = _load_json(input_path) if input_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not input_path.exists():
        errors.append(f"missing_input: {input_path}")

    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("payload_write_allowed") is not False:
        safety_violations.append("payload_write_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")
    if policy.get("approve_draft_create_only_currently_allowed") is not False:
        safety_violations.append("approve_draft_create_only_currently_allowed must be false")
    if policy.get("unlock_in_this_phase") is not False:
        safety_violations.append("unlock_in_this_phase must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    root = _resolve_root(policy_path)
    readiness_status = None
    missing_readiness = False
    for rel in policy.get("required_evidence", []):
        p = root / rel
        if not p.exists():
            missing_readiness = True
            continue
        data = _load_json(p)
        readiness_status = data.get("status") or data.get("overall_status")

    if payload_input.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    flags = payload_input.get("safety_flags", {})
    for key in [
        "wordpress_write_executed",
        "publish_allowed",
        "wordpress_api_call_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "bulk_execution",
        "external_write",
        "vps_self_builder_execution",
    ]:
        if flags.get(key) is not False:
            safety_violations.append(f"safety_flags.{key} must be false")

    affiliate_links = payload_input.get("affiliate_links", [])
    for idx, item in enumerate(affiliate_links):
        if not _is_https(str(item.get("url", ""))):
            safety_violations.append(f"affiliate_links[{idx}].url must be https")

    body = str(payload_input.get("body", ""))
    if not body.strip():
        errors.append("body is required")
    if "PR" not in body and "広告" not in body:
        errors.append("body must include PR/広告 notation")

    if safety_violations:
        status = "ABORT"
    elif missing_readiness:
        status = "NOT_READY"
    elif readiness_status == "ABORT":
        status = "ABORT"
    elif readiness_status != policy.get("required_readiness_status"):
        status = "NOT_READY"
    elif errors:
        status = "FAIL"
    else:
        status = "SIMULATION_PASS_DRY_RUN_ONLY"

    simulated_payload = {}
    if status == "SIMULATION_PASS_DRY_RUN_ONLY" and policy.get("payload_generation_allowed") is True:
        simulated_payload = {
            "candidate_id": payload_input.get("candidate_id"),
            "title": payload_input.get("title"),
            "content": payload_input.get("body"),
            "status": "draft_candidate_simulation_only",
            "category": payload_input.get("category"),
            "tags": payload_input.get("tags", []),
            "affiliate_links": payload_input.get("affiliate_links", []),
            "cta": payload_input.get("cta", []),
        }

    result = {
        "phase": "Phase 7-8",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "target_item_count": payload_input.get("target_item_count"),
        "simulation_only": bool(policy.get("simulation_only", True)),
        "readiness_status": readiness_status,
        "simulated_wordpress_payload": simulated_payload,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 7-9 Phase 7 pre-unlock overall completion report"),
        "blocked_operations": [
            "wordpress_rest_post",
            "wordpress_rest_put",
            "wordpress_rest_patch",
            "wordpress_rest_delete",
            "wordpress_publish",
            "wordpress_update",
            "wordpress_delete",
        ],
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-8 Single Draft Create Simulation Report",
        "",
        "## Purpose",
        "- Execute one-item draft-create simulation in DRY_RUN without any WordPress API call.",
        "",
        "## Readiness Evidence",
        f"- readiness_status: {result.get('readiness_status')}",
        "",
        "## Simulated Payload",
        f"- status: {result.get('simulated_wordpress_payload', {}).get('status')}",
        f"- title: {result.get('simulated_wordpress_payload', {}).get('title')}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        "",
        "## Blocked Operations",
    ]
    for item in result.get("blocked_operations", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = run_simulation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"SIMULATION_PASS_DRY_RUN_ONLY", "NOT_READY", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
