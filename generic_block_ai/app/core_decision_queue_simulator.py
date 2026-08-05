"""
core_decision_queue_simulator.py - IR12

Core AI receiver dry-run output is converted into queue items and audited
without executing any external action.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR11_SCHEMA_VERSION = "ir11_core_receiver_v1"
IR12_SCHEMA_VERSION = "ir12_core_decision_queue_v1"

_QUEUE_RULES: dict[str, dict[str, Any]] = {
    "PASS": {
        "core_receive_rule": "ACCEPT_DRY_RUN_REVIEW_QUEUE",
        "queue_state": "READY_FOR_DRY_RUN_REVIEW",
        "hold_reason": None,
        "requires_human_review": False,
        "evidence_preservation_required": False,
    },
    "WARN": {
        "core_receive_rule": "HUMAN_REVIEW_REQUIRED",
        "queue_state": "WAITING_HUMAN_REVIEW",
        "hold_reason": "warn_requires_human_review",
        "requires_human_review": True,
        "evidence_preservation_required": False,
    },
    "FAIL": {
        "core_receive_rule": "REJECT_AND_KEEP_NO_GO",
        "queue_state": "REJECTED_NO_GO",
        "hold_reason": "quality_gate_failed",
        "requires_human_review": True,
        "evidence_preservation_required": True,
    },
    "ABORT": {
        "core_receive_rule": "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE",
        "queue_state": "ABORT_EVIDENCE_LOCKED",
        "hold_reason": "abort_locked_policy_or_legal",
        "requires_human_review": True,
        "evidence_preservation_required": True,
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_task_id(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown_task"


def _normalize_judgment(value: Any) -> str:
    text = str(value or "WARN").upper()
    return text if text in _QUEUE_RULES else "WARN"


def validate_ir11_receiver_report_for_queue(
    receiver_report: dict[str, Any],
) -> dict[str, Any]:
    """
    IR12-T1
    Validate receiver output before queue conversion.
    """
    failed: list[str] = []
    warnings: list[str] = []

    if receiver_report.get("schema_version") != IR11_SCHEMA_VERSION:
        failed.append(f"schema_version must be {IR11_SCHEMA_VERSION}")

    judgment = _normalize_judgment(receiver_report.get("quality_gate_judgment"))
    expected_rule = _QUEUE_RULES[judgment]["core_receive_rule"]
    if receiver_report.get("core_receive_rule") != expected_rule:
        failed.append("core_receive_rule does not match quality_gate_judgment")

    receiver_validation = receiver_report.get("validation_result")
    if receiver_validation not in {"PASS", "WARN"}:
        failed.append("receiver validation_result must be PASS or WARN")

    safeguards = receiver_report.get("safeguards", {})
    if safeguards.get("external_write_executed") is not False:
        failed.append("safeguards.external_write_executed must be false")
    if safeguards.get("actual_auto_execute") is not False:
        failed.append("safeguards.actual_auto_execute must be false")
    if safeguards.get("production_release") is not False:
        failed.append("safeguards.production_release must be false")

    if safeguards.get("mode") != "dry_run":
        warnings.append("safeguards.mode is not dry_run")
    if safeguards.get("operation_mode") != "OBSERVE":
        warnings.append("safeguards.operation_mode is not OBSERVE")

    result = "FAIL" if failed else ("WARN" if warnings else "PASS")
    return {
        "result": result,
        "failed_checks": failed,
        "warnings": warnings,
        "quality_gate_judgment": judgment,
        "expected_core_receive_rule": expected_rule,
    }


def build_core_decision_queue_item(
    *,
    receiver_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """
    IR12-T2/T3
    Convert receiver output into a queue item and deterministic state transitions.
    """
    validation = validate_ir11_receiver_report_for_queue(receiver_report)
    judgment = validation["quality_gate_judgment"]
    rule = _QUEUE_RULES[judgment]
    task_id = _safe_task_id(source_task_id)
    queue_item_id = f"queue_{task_id}_{judgment.lower()}"
    now = _now_iso()

    transitions = [
        {
            "from": "NEW",
            "to": "RECEIVED",
            "event": "receiver_report_ingested",
            "at": now,
        },
        {
            "from": "RECEIVED",
            "to": rule["queue_state"],
            "event": f"judgment_{judgment.lower()}_mapped",
            "at": now,
        },
    ]

    queue_item = {
        "queue_item_id": queue_item_id,
        "source_task_id": source_task_id,
        "quality_gate_judgment": judgment,
        "core_receive_rule": rule["core_receive_rule"],
        "queue_state": rule["queue_state"],
        "hold_reason": rule["hold_reason"],
        "requires_human_review": rule["requires_human_review"],
        "evidence_preservation_required": rule["evidence_preservation_required"],
        "execution_allowed": False,
        "created_at": now,
        "updated_at": now,
    }

    return {
        "queue_item": queue_item,
        "state_transitions": transitions,
        "validation": validation,
    }


def _append_queue_audit_log(
    *,
    audit_log_path: Path,
    queue_item: dict[str, Any],
    source_task_id: str,
) -> None:
    event = {
        "event": "queue_item_recorded",
        "at": _now_iso(),
        "queue_item_id": queue_item.get("queue_item_id"),
        "source_task_id": source_task_id,
        "quality_gate_judgment": queue_item.get("quality_gate_judgment"),
        "queue_state": queue_item.get("queue_state"),
        "execution_triggered": False,
        "external_write_executed": False,
        "production_release": False,
    }
    with audit_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_ir12_core_decision_queue_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    receiver_report: dict[str, Any],
) -> dict[str, Any]:
    """
    IR12-T1/T2/T3/T4
    Queue simulation only. No execution, no external writes.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    queue_output = build_core_decision_queue_item(
        receiver_report=receiver_report,
        source_task_id=source_task_id,
    )

    queue_item = queue_output["queue_item"]
    validation = queue_output["validation"]
    transitions = queue_output["state_transitions"]

    audit_log_path = reports_dir / "ir12_core_decision_queue_audit.log"
    _append_queue_audit_log(
        audit_log_path=audit_log_path,
        queue_item=queue_item,
        source_task_id=source_task_id,
    )

    report = {
        "schema_version": IR12_SCHEMA_VERSION,
        "phase": "IR12",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "quality_gate_judgment": queue_item["quality_gate_judgment"],
        "core_receive_rule": queue_item["core_receive_rule"],
        "queue_item": queue_item,
        "state_transitions": transitions,
        "queue_validation_result": validation["result"],
        "queue_validation_failed_checks": validation["failed_checks"],
        "queue_validation_warnings": validation["warnings"],
        "execution_policy": {
            "execute": False,
            "reason": "ir12_queue_simulation_audit_only",
        },
        "audit_log_path": str(audit_log_path),
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    task_key = _safe_task_id(source_task_id)
    path = reports_dir / f"ir12_core_decision_queue_{task_key}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(path),
        "queue_report": report,
        "audit_log_path": str(audit_log_path),
        "external_write_executed": False,
    }


def write_ir12_completion_report(
    *,
    base_path: Path,
    ir12_outputs: list[dict[str, Any]],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR12-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    judgments: list[str] = []
    states: dict[str, int] = {}
    report_paths: list[str] = []
    audit_log_path: str | None = None

    for output in ir12_outputs:
        if not isinstance(output, dict):
            continue
        report_paths.append(output.get("path", "UNKNOWN"))
        if output.get("audit_log_path"):
            audit_log_path = output.get("audit_log_path")
        queue_report = output.get("queue_report", {})
        judgment = str(queue_report.get("quality_gate_judgment", "UNKNOWN"))
        judgments.append(judgment)
        state = str(queue_report.get("queue_item", {}).get("queue_state", "UNKNOWN"))
        states[state] = states.get(state, 0) + 1

    completion_report = {
        "phase": "Implementation Restart Phase 12",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR12_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "summary": {
            "processed_judgments": judgments,
            "unique_judgments": sorted(set(judgments)),
            "queue_state_counts": states,
            "execution_triggered": False,
        },
        "artifacts": {
            "queue_reports": report_paths,
            "audit_log": audit_log_path,
            "completion_report": "reports/implementation_restart_phase12_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase12_completion_report.json"
    out_path.write_text(json.dumps(completion_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion_report,
        "external_write_executed": False,
    }
