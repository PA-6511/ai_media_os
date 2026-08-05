"""
core_destination_human_event_chain_evidence_bundle.py - IR42

Bundle destination-level human event chain evidence from IR39, IR40, and IR41
in dry-run mode.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR39_SCHEMA_VERSION = "ir39_human_approval_event_simulator_for_destinations_v1"
IR40_SCHEMA_VERSION = "ir40_human_event_audit_replay_for_destinations_v1"
IR41_SCHEMA_VERSION = "ir41_destination_human_event_chain_integrity_v1"
IR42_SCHEMA_VERSION = "ir42_destination_human_event_chain_evidence_bundle_v1"

EVENT_APPROVE = "APPROVE"
EVENT_REQUEST_FIX = "REQUEST_FIX"
EVENT_REJECT = "REJECT"
EVENT_ABORT_ACK = "ABORT_ACK"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _to_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _json_digest(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _expected_state(event: str) -> str:
    return {
        EVENT_APPROVE: "EVIDENCE_LOCKED_APPROVED",
        EVENT_REQUEST_FIX: "EVIDENCE_LOCKED_NEEDS_FIX",
        EVENT_REJECT: "EVIDENCE_LOCKED_REJECTED",
        EVENT_ABORT_ACK: "EVIDENCE_LOCKED_ABORT_ACKED",
    }.get(event, "EVIDENCE_LOCKED_NEEDS_FIX")


def _chain_hash(destination: str, sequence_no: int, event: str, actor_id: str, lock_state: str) -> str:
    material = f"{destination}|{sequence_no}|{event}|{actor_id}|{lock_state}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _bundle_hash(destination: str, evidence_digest: str, review_status: str) -> str:
    return hashlib.sha256(f"{destination}|{evidence_digest}|{review_status}".encode("utf-8")).hexdigest()


def _chain_hash_from_ir41(destination: str, ir41_row: dict[str, Any] | None) -> str:
    if not ir41_row:
        return ""
    chain_rows = ir41_row.get("chain", [])
    if not isinstance(chain_rows, list) or not chain_rows:
        return ""
    chain_row = chain_rows[0]
    if not isinstance(chain_row, dict):
        return ""
    material = f"{destination}|{int(chain_row.get('sequence_no', 0))}|{str(chain_row.get('event', ''))}|{str(chain_row.get('actor_id', ''))}|{str(chain_row.get('lock_state', ''))}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def run_ir42_destination_human_event_chain_evidence_bundle_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir39_event_report_path: Path | None = None,
    ir40_replay_report_path: Path | None = None,
    ir41_chain_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR42-T1/T2/T3/T4
    Build destination evidence bundles from IR39, IR40, and IR41 reports.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir39_path = ir39_event_report_path or (
        reports_dir / "ir39_human_approval_event_simulator_for_destinations_report_ir39_live_trial.json"
    )
    ir40_path = ir40_replay_report_path or (
        reports_dir / "ir40_human_event_audit_replay_for_destinations_report_ir40_live_trial.json"
    )
    ir41_path = ir41_chain_report_path or (
        reports_dir / "ir41_destination_human_event_chain_integrity_report_ir41_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_bundles: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir39_path.exists():
        failed_checks.append(f"ir39 event report not found: {ir39_path}")
    if not ir40_path.exists():
        failed_checks.append(f"ir40 replay report not found: {ir40_path}")
    if not ir41_path.exists():
        failed_checks.append(f"ir41 chain report not found: {ir41_path}")

    ir39_report: dict[str, Any] = {}
    ir40_report: dict[str, Any] = {}
    ir41_report: dict[str, Any] = {}

    if not failed_checks:
        ir39_report = _read_json(ir39_path)
        ir40_report = _read_json(ir40_path)
        ir41_report = _read_json(ir41_path)

        if ir39_report.get("schema_version") != IR39_SCHEMA_VERSION:
            failed_checks.append(f"ir39 schema_version must be {IR39_SCHEMA_VERSION}")
        if ir40_report.get("schema_version") != IR40_SCHEMA_VERSION:
            failed_checks.append(f"ir40 schema_version must be {IR40_SCHEMA_VERSION}")
        if ir41_report.get("schema_version") != IR41_SCHEMA_VERSION:
            failed_checks.append(f"ir41 schema_version must be {IR41_SCHEMA_VERSION}")

        release_candidate_id = str(ir41_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir41_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir41_report.get("overall_approval_decision", "UNKNOWN"))

    ir39_rows = ir39_report.get("destination_human_event_simulation", [])
    ir40_rows = ir40_report.get("destination_human_event_audit_replay", [])
    ir41_rows = ir41_report.get("destination_human_event_chain_integrity", [])

    if not isinstance(ir39_rows, list):
        failed_checks.append("ir39 destination_human_event_simulation must be list")
        ir39_rows = []
    if not isinstance(ir40_rows, list):
        failed_checks.append("ir40 destination_human_event_audit_replay must be list")
        ir40_rows = []
    if not isinstance(ir41_rows, list):
        failed_checks.append("ir41 destination_human_event_chain_integrity must be list")
        ir41_rows = []

    ir39_by_destination: dict[str, dict[str, Any]] = {}
    ir40_by_destination: dict[str, dict[str, Any]] = {}
    ir41_by_destination: dict[str, dict[str, Any]] = {}

    for row in ir39_rows:
        if isinstance(row, dict):
            ir39_by_destination[str(row.get("destination", "UNKNOWN"))] = row
    for row in ir40_rows:
        if isinstance(row, dict):
            ir40_by_destination[str(row.get("destination", "UNKNOWN"))] = row
    for row in ir41_rows:
        if isinstance(row, dict):
            ir41_by_destination[str(row.get("destination", "UNKNOWN"))] = row

    destination_names = sorted(set(ir39_by_destination) | set(ir40_by_destination) | set(ir41_by_destination))

    for destination in destination_names:
        ir39_row = ir39_by_destination.get(destination)
        ir40_row = ir40_by_destination.get(destination)
        ir41_row = ir41_by_destination.get(destination)

        failed_reasons: list[str] = []

        if ir39_row is None:
            failed_reasons.append("destination missing in ir39 event simulation")
        if ir40_row is None:
            failed_reasons.append("destination missing in ir40 replay audit")
        if ir41_row is None:
            failed_reasons.append("destination missing in ir41 chain integrity report")

        selected_event_ir39 = str(ir39_row.get("selected_event", "UNKNOWN")) if ir39_row else "UNKNOWN"
        selected_event_ir40 = str(ir40_row.get("selected_event", "UNKNOWN")) if ir40_row else "UNKNOWN"
        chain_rows = ir41_row.get("chain", []) if ir41_row else []
        chain_row = chain_rows[0] if isinstance(chain_rows, list) and chain_rows else {}
        selected_event_ir41 = str(chain_row.get("event", "UNKNOWN")) if isinstance(chain_row, dict) else "UNKNOWN"

        ir39_state = (
            str(ir39_row.get("state_transition", {}).get("to_state", "UNKNOWN"))
            if ir39_row and isinstance(ir39_row.get("state_transition"), dict)
            else "UNKNOWN"
        )
        ir40_state = (
            str(ir40_row.get("replay_trace", {}).get("to_state", "UNKNOWN"))
            if ir40_row and isinstance(ir40_row.get("replay_trace"), dict)
            else "UNKNOWN"
        )
        ir41_state = str(chain_row.get("lock_state", "UNKNOWN")) if isinstance(chain_row, dict) else "UNKNOWN"

        actor_id = str(chain_row.get("actor_id", "")) if isinstance(chain_row, dict) else ""
        chain_hash = str(chain_row.get("chain_hash", "")) if isinstance(chain_row, dict) else ""

        sequence_ok = bool(chain_row) and int(chain_row.get("sequence_no", 0)) == 1
        event_ok = selected_event_ir39 == selected_event_ir40 == selected_event_ir41 and selected_event_ir41 != "UNKNOWN"
        state_ok = ir39_state == ir40_state == ir41_state and ir41_state == _expected_state(selected_event_ir41)
        actor_ok = bool(actor_id)

        evidence_payload = {
            "destination": destination,
            "release_candidate_id": release_candidate_id,
            "final_submission_decision": final_submission_decision,
            "overall_approval_decision": overall_approval_decision,
            "selected_event": selected_event_ir41,
            "lock_state": ir41_state,
            "actor_id": actor_id,
            "chain_hash": chain_hash,
            "source_refs": {
                "ir39": _to_ref(ir39_path, project_root),
                "ir40": _to_ref(ir40_path, project_root),
                "ir41": _to_ref(ir41_path, project_root),
            },
        }
        evidence_digest = _json_digest(evidence_payload)
        bundle_status = "PASS" if sequence_ok and event_ok and state_ok and actor_ok and chain_hash == _chain_hash_from_ir41(destination, ir41_row) else "FAIL"
        bundle_hash = _bundle_hash(destination, evidence_digest, bundle_status)

        hash_ok = bool(chain_hash) and chain_hash == _chain_hash_from_ir41(destination, ir41_row)
        evidence_lock_ok = ir41_state.startswith("EVIDENCE_LOCKED_")

        if not sequence_ok:
            failed_reasons.append("sequence integrity failed for bundle assembly")
        if not event_ok:
            failed_reasons.append("event integrity failed across ir39/ir40/ir41")
        if not state_ok:
            failed_reasons.append("lock state integrity failed across ir39/ir40/ir41")
        if not actor_ok:
            failed_reasons.append("actor integrity failed: actor_id missing in chain entry")
        if not hash_ok:
            failed_reasons.append("chain hash integrity failed")
        if not evidence_lock_ok:
            failed_reasons.append("evidence lock continuity failed")

        review_status = "PASS" if not failed_reasons else "FAIL"
        bundle_dir = reports_dir / f"ir42_destination_human_event_chain_evidence_bundle_{_safe(destination)}_{_safe(source_task_id)}"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        bundle_manifest_path = bundle_dir / "destination_human_event_chain_evidence_bundle.json"
        hash_manifest_path = bundle_dir / "destination_human_event_chain_hash_manifest.json"
        review_summary_path = bundle_dir / "destination_human_event_chain_review_summary.md"

        bundle_record = {
            "destination": destination,
            "review_status": review_status,
            "selected_event": selected_event_ir41,
            "lock_state": ir41_state,
            "actor_id": actor_id,
            "bundle_hash": bundle_hash,
            "evidence_digest": evidence_digest,
            "source_refs": evidence_payload["source_refs"],
            "integrity_checks": {
                "sequence_ok": sequence_ok,
                "event_ok": event_ok,
                "state_ok": state_ok,
                "actor_ok": actor_ok,
                "hash_ok": hash_ok,
                "evidence_lock_ok": evidence_lock_ok,
            },
            "failed_reasons": failed_reasons,
            "hash_manifest_path": _to_ref(hash_manifest_path, project_root),
            "review_summary_path": _to_ref(review_summary_path, project_root),
        }
        destination_bundles.append(bundle_record)

        hash_manifest = {
            "destination": destination,
            "bundle_hash": bundle_hash,
            "evidence_digest": evidence_digest,
            "chain_hash": chain_hash,
            "review_status": review_status,
            "source_refs": evidence_payload["source_refs"],
            "generated_at": _now_iso(),
        }
        bundle_manifest_path.write_text(json.dumps(bundle_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hash_manifest_path.write_text(json.dumps(hash_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        review_summary_lines = [
            "# Destination Human Event Chain Evidence Bundle",
            "",
            f"- Destination: {destination}",
            f"- Review Status: {review_status}",
            f"- Selected Event: {selected_event_ir41}",
            f"- Lock State: {ir41_state}",
            f"- Actor ID: {actor_id}",
            f"- Bundle Hash: {bundle_hash}",
            f"- Evidence Digest: {evidence_digest}",
            "",
            "## Integrity Checks",
        ]
        for key, value in bundle_record["integrity_checks"].items():
            review_summary_lines.append(f"- {key}: {value}")
        if failed_reasons:
            review_summary_lines.extend(["", "## Failed Reasons"])
            for reason in failed_reasons:
                review_summary_lines.append(f"- {reason}")
        review_summary_path.write_text("\n".join(review_summary_lines) + "\n", encoding="utf-8")

    pass_count = sum(1 for d in destination_bundles if d["review_status"] == "PASS")
    fail_count = sum(1 for d in destination_bundles if d["review_status"] == "FAIL")

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")
    if fail_count > 0:
        failed_checks.append(f"destination evidence bundle failures detected: {fail_count}")

    if fail_count == 0 and destination_bundles:
        overall_bundle_action = "Destination evidence bundles verified across IR39, IR40, and IR41 with hash manifest and review summary fixed."
    elif destination_bundles:
        overall_bundle_action = "Destination evidence bundle issues detected; hold progression and require remediation."
    else:
        overall_bundle_action = "No destination evidence bundles were produced."

    bundle_root = reports_dir / f"ir42_destination_human_event_chain_evidence_bundle_{_safe(source_task_id)}"
    bundle_root.mkdir(parents=True, exist_ok=True)

    bundle_json_path = bundle_root / "destination_human_event_chain_evidence_bundle_report.json"
    summary_md_path = bundle_root / "destination_human_event_chain_evidence_bundle_summary.md"

    report = {
        "schema_version": IR42_SCHEMA_VERSION,
        "phase": "IR42",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_bundle_action": overall_bundle_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_bundles),
            "bundle_pass_count": pass_count,
            "bundle_fail_count": fail_count,
            "hash_manifest_count": len(destination_bundles),
            "review_summary_count": len(destination_bundles),
        },
        "destination_human_event_chain_evidence_bundle": destination_bundles,
        "artifacts": {
            "bundle_root": _to_ref(bundle_root, project_root),
            "destination_human_event_chain_evidence_bundle_report": _to_ref(bundle_json_path, project_root),
            "destination_human_event_chain_evidence_bundle_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase42_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    bundle_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Human Event Chain Evidence Bundle",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Bundle Action: {overall_bundle_action}",
        "",
        "## Destination Bundles",
    ]
    for row in destination_bundles:
        summary_lines.append(f"- {row['destination']} -> {row['review_status']}")
        for reason in row.get("failed_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir42_destination_human_event_chain_evidence_bundle_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir42_completion_report(
    *,
    base_path: Path,
    ir42_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR42-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir42_output.get("runbook_report", {}) if isinstance(ir42_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 42",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR42_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir40_ir42": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_bundle_action": runbook.get("overall_bundle_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir42_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase42_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase42_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }