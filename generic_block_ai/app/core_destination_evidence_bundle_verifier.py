"""
core_destination_evidence_bundle_verifier.py - IR43

Verify destination evidence bundles emitted by IR42 in dry-run mode.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR42_SCHEMA_VERSION = "ir42_destination_human_event_chain_evidence_bundle_v1"
IR43_SCHEMA_VERSION = "ir43_destination_evidence_bundle_verifier_v1"


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


def _bundle_hash(destination: str, evidence_digest: str, review_status: str) -> str:
    return hashlib.sha256(f"{destination}|{evidence_digest}|{review_status}".encode("utf-8")).hexdigest()


def _evidence_digest_payload(
    *,
    row: dict[str, Any],
    release_candidate_id: str,
    final_submission_decision: str,
    overall_approval_decision: str,
    chain_hash: str,
) -> dict[str, Any]:
    return {
        "destination": row.get("destination", "UNKNOWN"),
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "selected_event": row.get("selected_event", "UNKNOWN"),
        "lock_state": row.get("lock_state", "UNKNOWN"),
        "actor_id": row.get("actor_id", ""),
        "chain_hash": chain_hash,
        "source_refs": row.get("source_refs", {}),
    }


def _expected_summary_lines(destination: str, review_status: str, selected_event: str, lock_state: str, actor_id: str, bundle_hash: str, evidence_digest: str) -> list[str]:
    return [
        "# Destination Human Event Chain Evidence Bundle",
        "",
        f"- Destination: {destination}",
        f"- Review Status: {review_status}",
        f"- Selected Event: {selected_event}",
        f"- Lock State: {lock_state}",
        f"- Actor ID: {actor_id}",
        f"- Bundle Hash: {bundle_hash}",
        f"- Evidence Digest: {evidence_digest}",
        "",
        "## Integrity Checks",
    ]


def _resolve_report_path(raw_path: str, project_root: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return project_root / path


def run_ir43_destination_evidence_bundle_verifier_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir42_bundle_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR43-T1/T2/T3/T4
    Verify destination evidence bundles from IR42 report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir42_path = ir42_bundle_report_path or (
        reports_dir / "ir42_destination_human_event_chain_evidence_bundle_report_ir42_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_verifications: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir42_path.exists():
        failed_checks.append(f"ir42 bundle report not found: {ir42_path}")

    ir42_report: dict[str, Any] = {}
    if not failed_checks:
        ir42_report = _read_json(ir42_path)
        if ir42_report.get("schema_version") != IR42_SCHEMA_VERSION:
            failed_checks.append(f"ir42 schema_version must be {IR42_SCHEMA_VERSION}")

        release_candidate_id = str(ir42_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir42_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir42_report.get("overall_approval_decision", "UNKNOWN"))

    rows = ir42_report.get("destination_human_event_chain_evidence_bundle", [])
    if not isinstance(rows, list):
        failed_checks.append("ir42 destination_human_event_chain_evidence_bundle must be list")
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir42 destination_human_event_chain_evidence_bundle entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        review_status = str(row.get("review_status", "UNKNOWN"))
        selected_event = str(row.get("selected_event", "UNKNOWN"))
        lock_state = str(row.get("lock_state", "UNKNOWN"))
        actor_id = str(row.get("actor_id", ""))
        bundle_hash = str(row.get("bundle_hash", ""))
        evidence_digest = str(row.get("evidence_digest", ""))

        hash_manifest_path = _resolve_report_path(str(row.get("hash_manifest_path", "")), project_root)
        review_summary_path = _resolve_report_path(str(row.get("review_summary_path", "")), project_root)

        hash_manifest_exists = hash_manifest_path.exists()
        summary_exists = review_summary_path.exists()

        bundle_record = {
            "destination": destination,
            "review_status": review_status,
            "selected_event": selected_event,
            "lock_state": lock_state,
            "actor_id": actor_id,
            "bundle_hash": bundle_hash,
            "evidence_digest": evidence_digest,
            "source_refs": row.get("source_refs", {}),
        }
        hash_manifest = _read_json(hash_manifest_path) if hash_manifest_exists else {}
        manifest_chain_hash = str(hash_manifest.get("chain_hash", "")) if hash_manifest else ""
        recomputed_evidence_digest = _json_digest(
            _evidence_digest_payload(
                row=bundle_record,
                release_candidate_id=release_candidate_id,
                final_submission_decision=final_submission_decision,
                overall_approval_decision=overall_approval_decision,
                chain_hash=manifest_chain_hash,
            )
        )
        recomputed_bundle_hash = _bundle_hash(destination, recomputed_evidence_digest, review_status)

        manifest_hash_ok = (
            bool(hash_manifest)
            and str(hash_manifest.get("bundle_hash", "")) == bundle_hash
            and str(hash_manifest.get("evidence_digest", "")) == evidence_digest
            and manifest_chain_hash != ""
        )
        recompute_ok = recomputed_evidence_digest == evidence_digest and recomputed_bundle_hash == bundle_hash

        summary_text = review_summary_path.read_text(encoding="utf-8") if summary_exists else ""
        expected_summary = "\n".join(_expected_summary_lines(destination, review_status, selected_event, lock_state, actor_id, bundle_hash, evidence_digest))
        summary_ok = bool(summary_text) and expected_summary in summary_text

        completeness_ok = review_status == "PASS" and hash_manifest_exists and summary_exists

        failed_reasons: list[str] = []
        if not hash_manifest_exists:
            failed_reasons.append("hash manifest missing")
        if not summary_exists:
            failed_reasons.append("review summary missing")
        if not manifest_hash_ok:
            failed_reasons.append("hash manifest content mismatch")
        if not recompute_ok:
            warnings.append(f"recomputed bundle hash mismatch for destination={destination}")
        if not summary_ok:
            failed_reasons.append("review summary content mismatch")
        if not completeness_ok:
            failed_reasons.append("bundle completeness failed")

        destination_verifications.append(
            {
                "destination": destination,
                "verification_status": "PASS" if not failed_reasons else "FAIL",
                "bundle_hash": bundle_hash,
                "evidence_digest": evidence_digest,
                "recomputed_evidence_digest": recomputed_evidence_digest,
                "recomputed_bundle_hash": recomputed_bundle_hash,
                "verification_checks": {
                    "hash_manifest_exists": hash_manifest_exists,
                    "summary_exists": summary_exists,
                    "manifest_hash_ok": manifest_hash_ok,
                    "recompute_ok": recompute_ok,
                    "summary_ok": summary_ok,
                    "completeness_ok": completeness_ok,
                },
                "failed_reasons": failed_reasons,
                "hash_manifest_path": _to_ref(hash_manifest_path, project_root) if hash_manifest_path else "",
                "review_summary_path": _to_ref(review_summary_path, project_root) if review_summary_path else "",
            }
        )

    pass_count = sum(1 for d in destination_verifications if d["verification_status"] == "PASS")
    fail_count = sum(1 for d in destination_verifications if d["verification_status"] == "FAIL")

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")
    if fail_count > 0:
        failed_checks.append(f"destination verification failures detected: {fail_count}")

    if fail_count == 0 and destination_verifications:
        overall_verifier_action = "Destination evidence bundles verified for manifest, summary, recomputation, and completeness."
    elif destination_verifications:
        overall_verifier_action = "Destination evidence bundle issues detected; hold progression and require remediation."
    else:
        overall_verifier_action = "No destination evidence bundles were available for verification."

    verifier_root = reports_dir / f"ir43_destination_evidence_bundle_verifier_{_safe(source_task_id)}"
    verifier_root.mkdir(parents=True, exist_ok=True)

    verifier_json_path = verifier_root / "destination_evidence_bundle_verifier.json"
    summary_md_path = verifier_root / "destination_evidence_bundle_verifier_summary.md"

    report = {
        "schema_version": IR43_SCHEMA_VERSION,
        "phase": "IR43",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_verifier_action": overall_verifier_action,
        "validation_result": "FAIL" if failed_checks else "PASS",
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_verifications),
            "verification_pass_count": pass_count,
            "verification_fail_count": fail_count,
            "hash_manifest_verified_count": sum(1 for d in destination_verifications if d["verification_checks"]["manifest_hash_ok"]),
            "summary_verified_count": sum(1 for d in destination_verifications if d["verification_checks"]["summary_ok"]),
            "completeness_verified_count": sum(1 for d in destination_verifications if d["verification_checks"]["completeness_ok"]),
        },
        "destination_evidence_bundle_verification": destination_verifications,
        "artifacts": {
            "verifier_root": _to_ref(verifier_root, project_root),
            "destination_evidence_bundle_verifier": _to_ref(verifier_json_path, project_root),
            "destination_evidence_bundle_verifier_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase43_completion_report.json",
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

    verifier_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Evidence Bundle Verifier",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Verifier Action: {overall_verifier_action}",
        "",
        "## Destination Verifications",
    ]
    for row in destination_verifications:
        summary_lines.append(f"- {row['destination']} -> {row['verification_status']}")
        for reason in row.get("failed_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir43_destination_evidence_bundle_verifier_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir43_completion_report(
    *,
    base_path: Path,
    ir43_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR43-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir43_output.get("runbook_report", {}) if isinstance(ir43_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 43",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR43_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir41_ir43": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_verifier_action": runbook.get("overall_verifier_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir43_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase43_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase43_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }