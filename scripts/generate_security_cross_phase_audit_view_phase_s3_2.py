#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_phase_s3_1_common import load_json, now_iso  # noqa: E402


CONFIG_PATH = ROOT / "config" / "security_cross_phase_audit_view_phase_s3_2.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_cross_phase_audit_view_phase_s3_2_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_cross_phase_audit_view_phase_s3_2_result.md"


def _flatten_required_evidence(required_evidence_files: dict[str, list[str]]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for phase_name, paths in required_evidence_files.items():
        for rel in paths:
            items.append((phase_name, rel))
    return items


def _safe_get(data: dict, key: str, default=None):
    return data.get(key, default)


def generate_security_cross_phase_audit_view_phase_s3_2(
    config_path: Path = CONFIG_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict:
    config = load_json(Path(config_path))
    required_items = _flatten_required_evidence(config.get("required_evidence_files", {}))
    required_evidence_count = len(required_items)

    audited_phases = list(config.get("audit_scope", []))
    missing_evidence_files: list[str] = []
    phase_summaries: dict[str, dict] = {}
    invariant_results: dict[str, object] = {}
    violated_invariants: list[str] = []
    warnings: list[str] = []
    fail_reasons: list[str] = []
    abort_reasons: list[str] = []
    found_evidence_count = 0

    required_invariants = config.get("required_invariants", {})
    for invariant_key, expected_value in required_invariants.items():
        invariant_results[invariant_key] = expected_value

    config_required_checks = {
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "audit_view_only": True,
        "recommendation_only": True,
        "executor_action_allowed": False,
    }
    for key, expected in config_required_checks.items():
        if config.get(key) != expected:
            abort_reasons.append(f"config.{key} must be {expected!r}")

    config_action_keys = [
        "auto_freeze_execute",
        "auto_revoke_execute",
        "auto_isolation_execute",
        "wordpress_api_call_execute",
        "external_api_call_execute",
        "state_change_execute",
    ]
    for key in config_action_keys:
        if config.get("actions", {}).get(key) is True:
            abort_reasons.append(f"config.actions.{key}=true is prohibited")

    for key in [
        "production_status",
        "execution",
        "human_approval_required",
        "executor_action_allowed",
        "audit_view_only",
        "recommendation_only",
    ]:
        if key in required_invariants:
            expected = required_invariants[key]
            if key == "production_status" and expected != "NO_GO":
                abort_reasons.append(f"required_invariants.{key} must be 'NO_GO'")
            if key == "execution" and expected != "DRY_RUN":
                abort_reasons.append(f"required_invariants.{key} must be 'DRY_RUN'")
            if key == "human_approval_required" and expected is not True:
                abort_reasons.append(f"required_invariants.{key} must be true")
            if key == "executor_action_allowed" and expected is not False:
                abort_reasons.append(f"required_invariants.{key} must be false")

    for key in [
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
        "freeze_executed",
        "revoke_executed",
        "isolation_executed",
    ]:
        if required_invariants.get(key) is not False:
            abort_reasons.append(f"required_invariants.{key} must be false")

    for phase_name, rel_path in required_items:
        path = ROOT / rel_path
        if not path.exists():
            missing_evidence_files.append(rel_path)
            continue
        found_evidence_count += 1
        try:
            payload = load_json(path)
        except Exception as exc:
            fail_reasons.append(f"json_parse_failed: {rel_path}: {exc}")
            continue

        phase_summaries.setdefault(phase_name, {})[rel_path] = {
            "phase_id": payload.get("phase_id"),
            "status": payload.get("status") or payload.get("validator_result") or payload.get("final_status") or payload.get("replay_result"),
        }

        for key, expected in required_invariants.items():
            if key in payload and payload.get(key) != expected:
                violated_invariants.append(f"{rel_path}:{key} expected {expected!r} got {payload.get(key)!r}")

        if payload.get("production_status") == "GO":
            abort_reasons.append(f"production_status=GO detected in {rel_path}")
        if payload.get("execution") == "LIVE":
            abort_reasons.append(f"execution=LIVE detected in {rel_path}")
        if payload.get("executor_action_allowed") is True:
            abort_reasons.append(f"executor_action_allowed=true detected in {rel_path}")
        if payload.get("freeze_executed") is True:
            abort_reasons.append(f"freeze_executed=true detected in {rel_path}")
        if payload.get("revoke_executed") is True:
            abort_reasons.append(f"revoke_executed=true detected in {rel_path}")
        if payload.get("isolation_executed") is True:
            abort_reasons.append(f"isolation_executed=true detected in {rel_path}")
        if payload.get("process_kill_executed") is True:
            abort_reasons.append(f"process_kill_executed=true detected in {rel_path}")
        if payload.get("scheduler_stop_executed") is True:
            abort_reasons.append(f"scheduler_stop_executed=true detected in {rel_path}")
        if payload.get("wordpress_write_executed") is True:
            abort_reasons.append(f"wordpress_write_executed=true detected in {rel_path}")
        if payload.get("external_api_call_executed") is True:
            abort_reasons.append(f"external_api_call_executed=true detected in {rel_path}")
        if payload.get("state_change_executed") is True:
            abort_reasons.append(f"state_change_executed=true detected in {rel_path}")
        if payload.get("publish_allowed") is True or payload.get("auto_post") is True or payload.get("auto_update") is True or payload.get("auto_delete") is True or payload.get("auto_export") is True:
            abort_reasons.append(f"publish/auto execution flag detected in {rel_path}")

    s3_1_path = ROOT / "exchange" / "logs" / "security_phase_s3_1_overall_result.json"
    s3_1_summary = {
        "event_count": 0,
        "matched_expected_count": 0,
        "mismatched_expected_count": 0,
        "freeze_recommendation_detected": False,
        "human_review_recommendation_detected": False,
    }
    if s3_1_path.exists():
        try:
            s3_1 = load_json(s3_1_path)
            s3_1_summary = {
                "event_count": int(_safe_get(s3_1, "event_count", 0)),
                "matched_expected_count": int(_safe_get(s3_1, "matched_expected_count", 0)),
                "mismatched_expected_count": int(_safe_get(s3_1, "mismatched_expected_count", 0)),
                "freeze_recommendation_detected": bool(_safe_get(s3_1, "freeze_recommendation_detected", False)),
                "human_review_recommendation_detected": bool(_safe_get(s3_1, "human_review_recommendation_detected", False)),
            }
            if s3_1_summary["event_count"] <= 0:
                fail_reasons.append("S-3.1 event_count must be > 0")
            if s3_1_summary["matched_expected_count"] != s3_1_summary["event_count"]:
                fail_reasons.append("S-3.1 matched_expected_count must equal event_count")
            if s3_1_summary["mismatched_expected_count"] != 0:
                fail_reasons.append("S-3.1 mismatched_expected_count must be 0")
            if not s3_1_summary["freeze_recommendation_detected"]:
                fail_reasons.append("S-3.1 freeze_recommendation_detected must be true")
            if not s3_1_summary["human_review_recommendation_detected"]:
                fail_reasons.append("S-3.1 human_review_recommendation_detected must be true")
        except Exception as exc:
            fail_reasons.append(f"json_parse_failed: {s3_1_path.relative_to(ROOT)}: {exc}")
    else:
        missing_evidence_files.append(str(s3_1_path.relative_to(ROOT)))

    s0_path = ROOT / "exchange" / "logs" / "security_baseline_phase_s0_validation_result.json"
    if s0_path.exists():
        try:
            s0 = load_json(s0_path)
        except Exception as exc:
            fail_reasons.append(f"json_parse_failed: {s0_path.relative_to(ROOT)}: {exc}")

    missing_evidence_count = len(missing_evidence_files)

    if abort_reasons:
        audit_result = "ABORT"
    elif missing_evidence_count > 0 or fail_reasons or violated_invariants:
        audit_result = "FAIL"
    elif warnings:
        audit_result = "WARN"
    else:
        audit_result = "PASS"

    if audit_result == "ABORT":
        final_status = "ABORT"
    elif audit_result == "PASS":
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "AUDIT_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S3_2",
        "phase_name": "cross_phase_security_audit_view",
        "audit_result": audit_result,
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "audit_view_only": True,
        "recommendation_only": True,
        "executor_action_allowed": False,
        "audited_phases": audited_phases,
        "required_evidence_count": required_evidence_count,
        "found_evidence_count": found_evidence_count,
        "missing_evidence_count": missing_evidence_count,
        "missing_evidence_files": missing_evidence_files,
        "phase_summaries": phase_summaries,
        "invariant_results": invariant_results,
        "violated_invariants": violated_invariants,
        "warnings": warnings,
        "fail_reasons": fail_reasons,
        "abort_reasons": abort_reasons,
        "s3_1_replay_summary": s3_1_summary,
        "state_change_executed": False,
        "freeze_executed": False,
        "revoke_executed": False,
        "isolation_executed": False,
        "process_kill_executed": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "timestamp": now_iso(),
        "next_step": "prepare_phase_s4_block_ai_isolation_design",
    }
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Cross-Phase Audit View Phase S-3.2 Result",
        "",
        f"- audit_result: {result.get('audit_result')}",
        f"- final_status: {result.get('final_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- audit_view_only: {result.get('audit_view_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- required_evidence_count: {result.get('required_evidence_count')}",
        f"- found_evidence_count: {result.get('found_evidence_count')}",
        f"- missing_evidence_count: {result.get('missing_evidence_count')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## audited_phases",
    ]
    for phase in result.get("audited_phases", []):
        lines.append(f"- {phase}")
    lines.extend(["", "## missing_evidence_files"])
    if result.get("missing_evidence_files"):
        for item in result["missing_evidence_files"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## s3_1_replay_summary"])
    for key, value in result.get("s3_1_replay_summary", {}).items():
        lines.append(f"- {key}: {value}")
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_cross_phase_audit_view_phase_s3_2()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["audit_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
