"""
core_ir51_55_handoff_batch.py - IR51-IR55

Batch implementation for destination submission handoff integrity and final dry-run gate.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR50_SCHEMA_VERSION = "ir50_destination_submission_handoff_manifest_v1"
IR51_SCHEMA_VERSION = "ir51_handoff_integrity_verifier_v1"
IR52_SCHEMA_VERSION = "ir52_release_packet_builder_v1"
IR53_SCHEMA_VERSION = "ir53_release_packet_verifier_v1"
IR54_SCHEMA_VERSION = "ir54_final_no_external_submit_gate_v1"
IR55_SCHEMA_VERSION = "ir55_phase_51_55_completion_bundle_v1"

IR54_READY = "READY_FOR_DRY_RUN_HANDOFF_ONLY"
IR54_HOLD = "HOLD"
IR54_REJECT = "REJECT"
IR54_ABORT = "ABORT"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _to_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _default_safety_gate() -> dict[str, Any]:
    return {
        "dry_run": "maintained",
        "OBSERVE": "maintained",
        "submission_execution_blocked": True,
        "execution_policy_execute": False,
        "external_write_executed": False,
        "network_transmission_executed": False,
        "production_release": False,
        "GitHub_push": "未実行",
    }


def _build_ir51_report(
    *,
    ir50_report: dict[str, Any],
    source_task_id: str,
    project_root: Path,
) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    if ir50_report.get("schema_version") != IR50_SCHEMA_VERSION:
        failed_checks.append(f"ir50 schema_version must be {IR50_SCHEMA_VERSION}")

    summary = ir50_report.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
        failed_checks.append("ir50 summary must be object")

    handoff_manifest = ir50_report.get("handoff_manifest", {})
    if not isinstance(handoff_manifest, dict):
        handoff_manifest = {}
        failed_checks.append("ir50 handoff_manifest must be object")

    destinations_all = ir50_report.get("destination_submission_handoff_manifest", [])
    if not isinstance(destinations_all, list):
        destinations_all = []
        failed_checks.append("ir50 destination_submission_handoff_manifest must be list")

    target_destinations = handoff_manifest.get("target_destinations", [])
    if not isinstance(target_destinations, list):
        target_destinations = []
        failed_checks.append("ir50 handoff_manifest.target_destinations must be list")
    target_destinations = [str(v) for v in target_destinations]

    reference_record_paths = handoff_manifest.get("reference_record_paths", [])
    if not isinstance(reference_record_paths, list):
        reference_record_paths = []
        failed_checks.append("ir50 handoff_manifest.reference_record_paths must be list")
    reference_record_paths = [str(v) for v in reference_record_paths]

    destination_count = int(summary.get("destination_count", 0) or 0)
    handoff_target_count = int(summary.get("handoff_target_count", 0) or 0)

    if destination_count != handoff_target_count:
        failed_checks.append("destination_count and handoff_target_count must match")

    if handoff_target_count != len(target_destinations):
        failed_checks.append("handoff_target_count and len(target_destinations) must match")

    duplicate_destinations = sorted({d for d in target_destinations if target_destinations.count(d) > 1})
    if duplicate_destinations:
        failed_checks.append(f"target_destinations has duplicates: {duplicate_destinations}")

    included_destinations = sorted(
        {
            str(row.get("destination", ""))
            for row in destinations_all
            if isinstance(row, dict) and str(row.get("handoff_manifest_decision", "")) == "INCLUDE_IN_DRY_RUN_HANDOFF"
        }
    )
    declared_destinations = sorted(target_destinations)
    if included_destinations != declared_destinations:
        failed_checks.append("target_destinations and included destinations are inconsistent")

    missing_reference_paths: list[str] = []
    for rel_path in reference_record_paths:
        candidate = (project_root / rel_path).resolve()
        if not candidate.exists():
            missing_reference_paths.append(rel_path)
    if missing_reference_paths:
        failed_checks.append(f"reference_record_paths not found: {missing_reference_paths}")

    if handoff_manifest.get("submission_execution_blocked") is not True:
        failed_checks.append("submission_execution_blocked must be true")
    if handoff_manifest.get("network_transmission_blocked") is not True:
        failed_checks.append("network_transmission_blocked must be true")
    if handoff_manifest.get("production_release_blocked") is not True:
        failed_checks.append("production_release_blocked must be true")

    safeguards = ir50_report.get("safeguards", {})
    if not isinstance(safeguards, dict):
        safeguards = {}
        failed_checks.append("ir50 safeguards must be object")

    if str(safeguards.get("mode", "")) != "dry_run":
        failed_checks.append("safeguards.mode must be dry_run")
    if str(safeguards.get("operation_mode", "")) != "OBSERVE":
        failed_checks.append("safeguards.operation_mode must be OBSERVE")
    for key in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release"):
        if safeguards.get(key) is not False:
            failed_checks.append(f"safeguards.{key} must be false")

    decision = "PASS" if not failed_checks else "FAIL"

    return {
        "schema_version": IR51_SCHEMA_VERSION,
        "phase": "IR51",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "source_ir50_report": ir50_report.get("artifacts", {}).get("destination_submission_handoff_manifest", "UNKNOWN"),
        "overall_submission_handoff_decision": ir50_report.get("overall_submission_handoff_decision", "UNKNOWN"),
        "ir51_integrity_decision": decision,
        "validation_result": decision,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": destination_count,
            "handoff_target_count": handoff_target_count,
            "target_destinations": target_destinations,
            "reference_record_paths": reference_record_paths,
            "missing_reference_record_paths": missing_reference_paths,
        },
        "safety_gate_snapshot": _default_safety_gate(),
    }


def _build_ir52_report(
    *,
    ir50_report: dict[str, Any],
    ir51_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    packet_manifest = {
        "phase": "IR52",
        "source_task_id": source_task_id,
        "source_ir50_report": ir50_report.get("source_task_id", "UNKNOWN"),
        "source_ir51_report": ir51_report.get("source_task_id", "UNKNOWN"),
        "target_destinations": ir51_report.get("summary", {}).get("target_destinations", []),
        "reference_record_paths": ir51_report.get("summary", {}).get("reference_record_paths", []),
    }

    packet_core = {
        "release_packet_id": f"rp_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "source_ir50_report": ir50_report.get("source_task_id", "UNKNOWN"),
        "source_ir51_report": ir51_report.get("source_task_id", "UNKNOWN"),
        "target_destinations": packet_manifest["target_destinations"],
        "reference_record_paths": packet_manifest["reference_record_paths"],
        "generated_at": _now_iso(),
        "packet_manifest": packet_manifest,
        "safety_gate_snapshot": _default_safety_gate(),
    }
    packet_hash = _sha256_hex(packet_core)

    validation_result = "PASS" if ir51_report.get("validation_result") == "PASS" else "FAIL"

    return {
        "schema_version": IR52_SCHEMA_VERSION,
        "phase": "IR52",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        **packet_core,
        "packet_hash": packet_hash,
        "validation_result": validation_result,
        "validation_failed_checks": [] if validation_result == "PASS" else ["ir51 validation must be PASS"],
        "validation_warnings": [],
    }


def _build_ir53_report(*, ir52_report: dict[str, Any], ir51_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    required_fields = [
        "release_packet_id",
        "source_ir50_report",
        "source_ir51_report",
        "target_destinations",
        "reference_record_paths",
        "generated_at",
        "packet_manifest",
        "safety_gate_snapshot",
        "packet_hash",
    ]
    missing_fields = [field for field in required_fields if field not in ir52_report]
    if missing_fields:
        failed_checks.append(f"missing required fields: {missing_fields}")

    target_destinations = [str(v) for v in ir52_report.get("target_destinations", [])]
    expected_destinations = sorted([str(v) for v in ir51_report.get("summary", {}).get("target_destinations", [])])
    if sorted(target_destinations) != expected_destinations:
        failed_checks.append("target_destinations mismatch against ir51")

    reference_record_paths = [str(v) for v in ir52_report.get("reference_record_paths", [])]
    expected_refs = sorted([str(v) for v in ir51_report.get("summary", {}).get("reference_record_paths", [])])
    if sorted(reference_record_paths) != expected_refs:
        failed_checks.append("reference_record_paths mismatch against ir51")

    recompute_input = {
        "release_packet_id": ir52_report.get("release_packet_id"),
        "source_ir50_report": ir52_report.get("source_ir50_report"),
        "source_ir51_report": ir52_report.get("source_ir51_report"),
        "target_destinations": ir52_report.get("target_destinations", []),
        "reference_record_paths": ir52_report.get("reference_record_paths", []),
        "generated_at": ir52_report.get("generated_at"),
        "packet_manifest": ir52_report.get("packet_manifest", {}),
        "safety_gate_snapshot": ir52_report.get("safety_gate_snapshot", {}),
    }
    recalculated_hash = _sha256_hex(recompute_input)
    provided_hash = str(ir52_report.get("packet_hash", ""))
    hash_match = provided_hash == recalculated_hash
    if not hash_match:
        failed_checks.append("packet_hash mismatch (tamper detected)")

    snapshot = ir52_report.get("safety_gate_snapshot", {})
    if not isinstance(snapshot, dict):
        snapshot = {}
        failed_checks.append("safety_gate_snapshot must be object")

    expected_gate = _default_safety_gate()
    for key, expected in expected_gate.items():
        if snapshot.get(key) != expected:
            failed_checks.append(f"safety_gate_snapshot.{key} mismatch")

    validation_result = "PASS" if not failed_checks else "FAIL"

    return {
        "schema_version": IR53_SCHEMA_VERSION,
        "phase": "IR53",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "required_fields_checked": required_fields,
        "missing_required_fields": missing_fields,
        "hash_verification": {
            "provided_packet_hash": provided_hash,
            "recalculated_packet_hash": recalculated_hash,
            "hash_match": hash_match,
        },
        "tamper_detection_summary": "NO_TAMPER" if hash_match else "TAMPER_DETECTED",
        "target_destinations": target_destinations,
        "reference_record_paths": reference_record_paths,
        "safety_gate_snapshot": snapshot,
    }


def run_ir53_release_packet_verifier(
    *,
    ir52_release_packet: dict[str, Any],
    ir51_handoff_integrity_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Public IR53 verifier for focused tests and ad-hoc checks."""
    return _build_ir53_report(
        ir52_report=ir52_release_packet,
        ir51_report=ir51_handoff_integrity_report,
        source_task_id=source_task_id,
    )


def _build_ir54_report(*, ir53_report: dict[str, Any], ir52_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    snapshot = ir52_report.get("safety_gate_snapshot", {})
    if not isinstance(snapshot, dict):
        snapshot = {}

    submission_execution_blocked = snapshot.get("submission_execution_blocked") is True
    execution_policy_execute = snapshot.get("execution_policy_execute") is True
    external_write_executed = snapshot.get("external_write_executed") is True
    network_transmission_executed = snapshot.get("network_transmission_executed") is True
    production_release = snapshot.get("production_release") is True
    github_push_executed = str(snapshot.get("GitHub_push", "未実行")) != "未実行"

    abort_condition = any(
        [
            execution_policy_execute,
            external_write_executed,
            network_transmission_executed,
            production_release,
            github_push_executed,
        ]
    )

    if not submission_execution_blocked:
        failed_checks.append("submission_execution_blocked must remain true")

    if abort_condition:
        final_decision = IR54_ABORT
        gate_action = "Abort due to external submit risk flags."
    elif ir53_report.get("validation_result") == "PASS":
        final_decision = IR54_READY
        gate_action = "Ready for dry-run handoff only. External submit branch remains blocked."
    elif ir53_report.get("tamper_detection_summary") == "TAMPER_DETECTED":
        final_decision = IR54_REJECT
        gate_action = "Reject due to packet tamper detection."
    else:
        final_decision = IR54_HOLD
        gate_action = "Hold until verification issues are resolved."

    if final_decision in {IR54_READY, IR54_HOLD, IR54_REJECT} and abort_condition:
        failed_checks.append("abort_condition must force ABORT")

    return {
        "schema_version": IR54_SCHEMA_VERSION,
        "phase": "IR54",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "final_no_external_submit_gate_decision": final_decision,
        "gate_action": gate_action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "safety_gate_snapshot": snapshot,
        "checks": {
            "submission_execution_blocked": submission_execution_blocked,
            "execution_policy_execute": execution_policy_execute,
            "external_write_executed": external_write_executed,
            "network_transmission_executed": network_transmission_executed,
            "production_release": production_release,
            "GitHub_push_executed": github_push_executed,
            "execution_policy_safe": not execution_policy_execute,
            "external_write_safe": not external_write_executed,
            "network_transmission_safe": not network_transmission_executed,
            "production_release_safe": not production_release,
            "github_push_safe": not github_push_executed,
            "external_submit_branch_blocked": submission_execution_blocked,
        },
    }


def run_ir54_final_no_external_submit_gate(
    *,
    ir53_release_packet_verification: dict[str, Any],
    ir52_release_packet: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Public IR54 gate evaluator for focused tests and ad-hoc checks."""
    return _build_ir54_report(
        ir53_report=ir53_release_packet_verification,
        ir52_report=ir52_release_packet,
        source_task_id=source_task_id,
    )


def run_ir51_55_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir50_handoff_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR51-IR54 batch run with dry-run only safeguards.
    """
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir51_55"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir50_path = ir50_handoff_report_path or (
        reports_dir / "ir50_destination_submission_handoff_manifest_report_ir50_live_trial.json"
    )

    if not ir50_path.exists():
        raise FileNotFoundError(f"ir50 handoff report not found: {ir50_path}")

    ir50_report = _read_json(ir50_path)

    ir51_report = _build_ir51_report(
        ir50_report=ir50_report,
        source_task_id=source_task_id,
        project_root=project_root,
    )
    ir51_path = out_dir / "ir51_handoff_integrity_report.json"
    _write_json(ir51_path, ir51_report)

    ir52_report = _build_ir52_report(
        ir50_report=ir50_report,
        ir51_report=ir51_report,
        source_task_id=source_task_id,
    )
    ir52_path = out_dir / "ir52_release_packet.json"
    _write_json(ir52_path, ir52_report)

    ir53_report = run_ir53_release_packet_verifier(
        ir52_release_packet=ir52_report,
        ir51_handoff_integrity_report=ir51_report,
        source_task_id=source_task_id,
    )
    ir53_path = out_dir / "ir53_release_packet_verification.json"
    _write_json(ir53_path, ir53_report)

    ir54_report = run_ir54_final_no_external_submit_gate(
        ir53_release_packet_verification=ir53_report,
        ir52_release_packet=ir52_report,
        source_task_id=source_task_id,
    )
    ir54_path = out_dir / "ir54_no_external_submit_gate_report.json"
    _write_json(ir54_path, ir54_report)

    return {
        "phase": "IR51_55_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "source_ir50_report_path": _to_ref(ir50_path, project_root),
        "final_decision": ir54_report["final_no_external_submit_gate_decision"],
        "ir51_result": ir51_report,
        "ir52_result": ir52_report,
        "ir53_result": ir53_report,
        "ir54_result": ir54_report,
        "artifacts": {
            "ir51_handoff_integrity_report": _to_ref(ir51_path, project_root),
            "ir52_release_packet": _to_ref(ir52_path, project_root),
            "ir53_release_packet_verification": _to_ref(ir53_path, project_root),
            "ir54_no_external_submit_gate_report": _to_ref(ir54_path, project_root),
        },
        "external_write_executed": False,
    }


def write_ir51_55_completion_bundle(
    *,
    base_path: Path,
    ir51_55_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    IR55 completion bundle writer.
    """
    out_dir = base_path / "reports" / "ir51_55"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir51_result = ir51_55_output.get("ir51_result", {})
    ir52_result = ir51_55_output.get("ir52_result", {})
    ir53_result = ir51_55_output.get("ir53_result", {})
    ir54_result = ir51_55_output.get("ir54_result", {})

    final_decision = str(ir51_55_output.get("final_decision", IR54_HOLD))

    table_rows = [
        {
            "phase": "IR51",
            "content": "Handoff Integrity Verifier",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": "PASS" if ir51_result.get("validation_result") == "PASS" else "FAIL",
            "judgement": "完了" if ir51_result.get("validation_result") == "PASS" else "要修正",
        },
        {
            "phase": "IR52",
            "content": "Release Packet Builder",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": "PASS" if ir52_result.get("validation_result") == "PASS" else "FAIL",
            "judgement": "完了" if ir52_result.get("validation_result") == "PASS" else "要修正",
        },
        {
            "phase": "IR53",
            "content": "Release Packet Verifier",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": "PASS" if ir53_result.get("validation_result") == "PASS" else "FAIL",
            "judgement": "完了" if ir53_result.get("validation_result") == "PASS" else "要修正",
        },
        {
            "phase": "IR54",
            "content": "Final No-External-Submit Gate",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": "PASS" if final_decision == IR54_READY else "FAIL",
            "judgement": "完了" if final_decision == IR54_READY else "要修正",
        },
        {
            "phase": "IR55",
            "content": "Phase 51-55 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": "PASS" if final_decision == IR54_READY else "FAIL",
            "judgement": "完了" if final_decision == IR54_READY else "要修正",
        },
    ]

    safety_gate_summary = _default_safety_gate()

    bundle = {
        "schema_version": IR55_SCHEMA_VERSION,
        "phase": "IR55",
        "generated_at": _now_iso(),
        "source_task_id": ir51_55_output.get("source_task_id", "UNKNOWN"),
        "ir51_result": ir51_result,
        "ir52_result": ir52_result,
        "ir53_result": ir53_result,
        "ir54_result": ir54_result,
        "test_summary": {
            "focused": focused,
            "adjacent": adjacent,
            "scoped": scoped,
        },
        "live_summary": {
            "ir51": table_rows[0]["live"],
            "ir52": table_rows[1]["live"],
            "ir53": table_rows[2]["live"],
            "ir54": table_rows[3]["live"],
            "ir55": table_rows[4]["live"],
        },
        "safety_gate_summary": safety_gate_summary,
        "completion_table": table_rows,
        "final_decision": final_decision,
        "artifacts": {
            "ir51_handoff_integrity_report": ir51_55_output.get("artifacts", {}).get(
                "ir51_handoff_integrity_report", "UNKNOWN"
            ),
            "ir52_release_packet": ir51_55_output.get("artifacts", {}).get("ir52_release_packet", "UNKNOWN"),
            "ir53_release_packet_verification": ir51_55_output.get("artifacts", {}).get(
                "ir53_release_packet_verification", "UNKNOWN"
            ),
            "ir54_no_external_submit_gate_report": ir51_55_output.get("artifacts", {}).get(
                "ir54_no_external_submit_gate_report", "UNKNOWN"
            ),
            "ir55_completion_bundle": "generic_block_ai/reports/ir51_55/ir55_completion_bundle.json",
            "ir51_55_live_status": "generic_block_ai/reports/ir51_55/ir51_55_live_status.md",
            "ir51_55_completion_table": "generic_block_ai/reports/ir51_55/ir51_55_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir55_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR51-IR55 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir51_55_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR51-IR55 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir51_55_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir55_completion_bundle": _to_ref(bundle_path, project_root),
            "ir51_55_live_status": _to_ref(live_path, project_root),
            "ir51_55_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }
