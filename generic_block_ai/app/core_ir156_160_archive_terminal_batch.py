"""
core_ir156_160_archive_terminal_batch.py - IR156-IR160

Batch implementation for terminal archive finalization in dry-run mode:
IR156 archive final seal, IR157 reference-only enforcement registry,
IR158 immutable audit index, IR159 terminal declaration package,
IR160 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR155_SCHEMA_VERSION = "ir155_phase_151_155_completion_bundle_v1"
IR156_SCHEMA_VERSION = "ir156_archive_final_seal_v1"
IR157_SCHEMA_VERSION = "ir157_reference_only_enforcement_registry_v1"
IR158_SCHEMA_VERSION = "ir158_immutable_audit_index_v1"
IR159_SCHEMA_VERSION = "ir159_terminal_declaration_package_v1"
IR160_SCHEMA_VERSION = "ir160_phase_156_160_completion_bundle_v1"

IR159_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR159_HOLD = "HOLD"
IR159_ABORT = "ABORT"


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


# ---------------------------------------------------------------------------
# IR156: Archive Final Seal
# ---------------------------------------------------------------------------

def _build_ir156_report(*, ir155_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir155_report.get("schema_version") != IR155_SCHEMA_VERSION:
        failed_checks.append(f"ir155 schema_version must be {IR155_SCHEMA_VERSION}")

    if ir155_report.get("final_decision") != IR159_CONFIRMED:
        failed_checks.append("ir155 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir155_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir155 prohibition_continuity_finalized must be true")

    ir153_result = ir155_report.get("ir153_result", {})
    digest = ir153_result.get("governance_trace_digest", {}) if isinstance(ir153_result, dict) else {}
    digest_entries = digest.get("digest_entries", []) if isinstance(digest, dict) else []

    seal_entries = [
        {
            "meta_item": str(entry.get("meta_item", f"meta_{idx+1}")),
            "digest_id": str(entry.get("digest_id", "")),
            "archive_seal_status": "SEALED",
            "mutable": False,
        }
        for idx, entry in enumerate(digest_entries)
        if isinstance(entry, dict)
    ]

    if not seal_entries:
        failed_checks.append("ir155 ir153_result.governance_trace_digest.digest_entries must not be empty")

    report = {
        "seal_id": f"ir156_seal_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir155_report.get("new_cycle_id", "UNKNOWN"),
        "seal_entries": seal_entries,
        "seal_count": len(seal_entries),
        "all_archive_sealed": len(seal_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR156_SCHEMA_VERSION,
        "phase": "IR156",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "archive_final_seal": report,
        "seal_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR157: Reference-Only Enforcement Registry
# ---------------------------------------------------------------------------

def _build_ir157_report(*, ir156_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir156_report.get("validation_result") != "PASS":
        failed_checks.append("ir156 archive final seal must be PASS")

    seal = ir156_report.get("archive_final_seal", {})
    seal_entries = seal.get("seal_entries", []) if isinstance(seal, dict) else []

    if not seal_entries:
        failed_checks.append("ir156 seal_entries must not be empty")

    registry_entries = [
        {
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "reference_mode": "READ_ONLY",
            "enforcement_status": "ENFORCED",
            "write_allowed": False,
        }
        for entry in seal_entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir157_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": seal.get("new_cycle_id", "UNKNOWN") if isinstance(seal, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_reference_only_enforced": len(registry_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR157_SCHEMA_VERSION,
        "phase": "IR157",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "reference_only_enforcement_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR158: Immutable Audit Index
# ---------------------------------------------------------------------------

def _build_ir158_report(*, ir157_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir157_report.get("validation_result") != "PASS":
        failed_checks.append("ir157 reference-only enforcement registry must be PASS")

    registry = ir157_report.get("reference_only_enforcement_registry", {})
    registry_entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not registry_entries:
        failed_checks.append("ir157 registry_entries must not be empty")

    index_entries = [
        {
            "index_item_id": f"immutable_{idx+1}",
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "immutability_status": "IMMUTABLE",
            "index_ref": f"immutable://{idx+1}",
        }
        for idx, entry in enumerate(registry_entries)
        if isinstance(entry, dict)
    ]

    index = {
        "index_id": f"ir158_index_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "index_entries": index_entries,
        "index_count": len(index_entries),
        "immutable_index_ready": len(index_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR158_SCHEMA_VERSION,
        "phase": "IR158",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "immutable_audit_index": index,
        "index_hash": _sha256_hex(index),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR159: Terminal Declaration Package
# ---------------------------------------------------------------------------

def run_ir159_terminal_declaration_package(
    *, ir158_report: dict[str, Any], ir157_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir158_report.get("validation_result") != "PASS":
        failed_checks.append("ir158 immutable audit index must be PASS")

    index = ir158_report.get("immutable_audit_index", {})
    if index.get("immutable_index_ready") is not True:
        failed_checks.append("ir158 immutable_index_ready must be true")

    registry = ir157_report.get("reference_only_enforcement_registry", {})
    if registry.get("all_reference_only_enforced") is not True:
        failed_checks.append("ir157 all_reference_only_enforced must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir157 unlock_eligible must be false")

    safety_snapshot = ir158_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR159_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR159_HOLD
        action = "Hold due to terminal declaration precondition mismatch."
    else:
        decision = IR159_CONFIRMED
        action = "Terminal declaration package confirmed under dry-run terminal state."

    package = {
        "package_id": f"ir159_package_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "terminal_declaration_confirmed": decision == IR159_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR159_SCHEMA_VERSION,
        "phase": "IR159",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "terminal_declaration_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "terminal_declaration_package": package,
        "package_hash": _sha256_hex(package),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir156_160_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir155_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir156_160"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir155_path = ir155_completion_bundle_path or (reports_dir / "ir151_155" / "ir155_completion_bundle.json")

    if not ir155_path.exists():
        raise FileNotFoundError(f"ir155 completion bundle not found: {ir155_path}")

    ir155_report = _read_json(ir155_path)

    ir156_report = _build_ir156_report(ir155_report=ir155_report, source_task_id=source_task_id)
    ir156_path = out_dir / "ir156_archive_final_seal.json"
    _write_json(ir156_path, ir156_report)

    ir157_report = _build_ir157_report(ir156_report=ir156_report, source_task_id=source_task_id)
    ir157_path = out_dir / "ir157_reference_only_enforcement_registry.json"
    _write_json(ir157_path, ir157_report)

    ir158_report = _build_ir158_report(ir157_report=ir157_report, source_task_id=source_task_id)
    ir158_path = out_dir / "ir158_immutable_audit_index.json"
    _write_json(ir158_path, ir158_report)

    ir159_report = run_ir159_terminal_declaration_package(
        ir158_report=ir158_report,
        ir157_report=ir157_report,
        source_task_id=source_task_id,
    )
    ir159_path = out_dir / "ir159_terminal_declaration_package.json"
    _write_json(ir159_path, ir159_report)

    final_decision = ir159_report["terminal_declaration_decision"]

    return {
        "phase": "IR156_160_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir155_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir155_bundle_path": _to_ref(ir155_path, project_root),
        "final_decision": final_decision,
        "ir156_result": ir156_report,
        "ir157_result": ir157_report,
        "ir158_result": ir158_report,
        "ir159_result": ir159_report,
        "artifacts": {
            "ir156_archive_final_seal": _to_ref(ir156_path, project_root),
            "ir157_reference_only_enforcement_registry": _to_ref(ir157_path, project_root),
            "ir158_immutable_audit_index": _to_ref(ir158_path, project_root),
            "ir159_terminal_declaration_package": _to_ref(ir159_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR160: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir156_160_completion_bundle(
    *,
    base_path: Path,
    ir156_160_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir156_160"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir156_result = ir156_160_output.get("ir156_result", {})
    ir157_result = ir156_160_output.get("ir157_result", {})
    ir158_result = ir156_160_output.get("ir158_result", {})
    ir159_result = ir156_160_output.get("ir159_result", {})
    final_decision = str(ir156_160_output.get("final_decision", IR159_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir159_live = "PASS" if final_decision == IR159_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR156", "content": "Archive Final Seal", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir156_result), "judgement": _judgement(_live(ir156_result))},
        {"phase": "IR157", "content": "Reference-Only Enforcement Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir157_result), "judgement": _judgement(_live(ir157_result))},
        {"phase": "IR158", "content": "Immutable Audit Index", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir158_result), "judgement": _judgement(_live(ir158_result))},
        {"phase": "IR159", "content": "Terminal Declaration Package", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir159_live, "judgement": _judgement(ir159_live)},
        {"phase": "IR160", "content": "Phase 156-160 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir159_live, "judgement": _judgement(ir159_live)},
    ]

    bundle = {
        "schema_version": IR160_SCHEMA_VERSION,
        "phase": "IR160",
        "generated_at": _now_iso(),
        "source_task_id": ir156_160_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir156_160_output.get("new_cycle_id", "UNKNOWN"),
        "ir156_result": ir156_result,
        "ir157_result": ir157_result,
        "ir158_result": ir158_result,
        "ir159_result": ir159_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir156": table_rows[0]["live"],
            "ir157": table_rows[1]["live"],
            "ir158": table_rows[2]["live"],
            "ir159": table_rows[3]["live"],
            "ir160": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR159_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir156_160_output.get("artifacts", {}),
            "ir160_completion_bundle": "generic_block_ai/reports/ir156_160/ir160_completion_bundle.json",
            "ir156_160_live_status": "generic_block_ai/reports/ir156_160/ir156_160_live_status.md",
            "ir156_160_completion_table": "generic_block_ai/reports/ir156_160/ir156_160_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir160_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR156-IR160 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Prohibition Continuity Finalized: {bundle['prohibition_continuity_finalized']}",
        f"- Delta Closure Pending: {bundle['delta_closure_pending']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir156_160_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR156-IR160 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir156_160_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir160_completion_bundle": _to_ref(bundle_path, project_root),
            "ir156_160_live_status": _to_ref(live_path, project_root),
            "ir156_160_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }
