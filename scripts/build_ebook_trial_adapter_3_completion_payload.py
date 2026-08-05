#!/usr/bin/env python3
"""EBOOK-TRIAL-ADAPTER-3: Completion payload builder (DRY_RUN / NO_EXECUTION)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/ebook_trial_adapter_3_completion_payload_builder_policy.json"
REQUEST = ROOT / "exchange/examples/ebook_trial_adapter_3_completion_payload_builder_request.example.json"
OUTPUT = ROOT / "exchange/logs/ebook_trial_adapter_3_completion_payload_builder_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def build(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_path = Path(output_path)

    base = {
        "phase": "EBOOK-TRIAL-ADAPTER-3",
        "phase_name": "Completion Payload Builder / DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "design_only": True,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "executed_external_changes": 0,
        "built_at": _now_iso(),
        "policy_violations": [],
        "adapter2_evidence_exists": False,
        "adapter2_status": None,
        "payload_generated": False,
    }

    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "EBOOK_TRIAL_ADAPTER_3_ABORT_INPUT_LOAD_ERROR_NO_EXECUTION",
            "policy_violations": [f"input_load_error: {exc}"],
            "completion_payload": None,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    violations: list[str] = []

    if request.get("mode") != "CONNECTION_TEST":
        violations.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        violations.append("request.production_status must be NO_GO")
    if request.get("design_only") is not True:
        violations.append("request.design_only must be true")

    for flag in policy.get("required_false_flags", []):
        if request.get(flag) is not False:
            violations.append(f"request.{flag} must be false")

    root = _resolve_root(policy_path)
    adapter2_rel = str(policy.get("adapter2_evidence_path", ""))
    adapter2_path = root / adapter2_rel
    adapter2_status = None
    if adapter2_path.exists():
        try:
            adapter2_status = str(_load_json(adapter2_path).get("status"))
        except Exception:
            adapter2_status = None

    required_adapter2_status = str(policy.get("adapter2_required_status", ""))
    if not adapter2_path.exists():
        violations.append("adapter2_evidence_missing")
    elif adapter2_status != required_adapter2_status:
        violations.append("adapter2_status_not_matched")

    proposals = request.get("proposals", [])
    if not isinstance(proposals, list) or not proposals:
        violations.append("no_proposal_input")
        candidate: dict[str, Any] = {}
    else:
        candidate = proposals[0] if isinstance(proposals[0], dict) else {}

    completion_payload = None
    if not violations:
        fixed_defaults = dict(policy.get("fixed_defaults", {}))
        required_fields = [str(x) for x in policy.get("required_output_fields", [])]
        override = request.get("defaults_override", {})
        if not isinstance(override, dict):
            override = {}

        pr_label = str(override.get("pr_label") or "PR")
        completion_payload = {
            "mode": "CONNECTION_TEST",
            "execution": "DRY_RUN",
            "production_status": "NO_GO",
            "human_approval_present": False,
            "title": str(candidate.get("title") or ""),
            "target": str(candidate.get("target") or ""),
            "reason": str(candidate.get("reason") or ""),
            "priority": candidate.get("priority", 0.0),
            "source": str(candidate.get("source") or "ebook_affiliate_block"),
            "target_item_schema": {
                "schema_version": "trial_target_item_v1",
                "is_valid": True,
            },
            "affiliate_disclosure": "本記事にはアフィリエイトリンクを含みます。",
            "pr_label": pr_label,
            "duplicate_check": {
                "checked": True,
                "passed": True,
                "method": "dry_run_stub",
            },
        }
        for field in required_fields:
            completion_payload[field] = bool(fixed_defaults.get(field, True))

    status = "EBOOK_TRIAL_ADAPTER_3_ABORT_POLICY_VIOLATION_NO_EXECUTION" if violations else "EBOOK_TRIAL_ADAPTER_3_COMPLETION_PAYLOAD_BUILT_DRY_RUN_NO_EXECUTION"
    result = {
        **base,
        "status": status,
        "policy_violations": violations,
        "adapter2_evidence_exists": adapter2_path.exists(),
        "adapter2_status": adapter2_status,
        "payload_generated": completion_payload is not None,
        "completion_payload": completion_payload,
        "next_step": "KEEP_DRY_RUN_AND_VALIDATE_WITH_ADAPTER_1" if completion_payload else "FIX_POLICY_INPUT_AND_REBUILD",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = build()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "EBOOK_TRIAL_ADAPTER_3_COMPLETION_PAYLOAD_BUILT_DRY_RUN_NO_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
