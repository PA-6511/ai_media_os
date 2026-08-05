"""
affiliate_integration_trial.py — IR7

Generated affiliate block skeleton を block package として固定し、
affiliate_block -> generic_block_ai -> core_ai の DRY_RUN 接続試験を提供します。

外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .affiliate_practical_schema import (
    evaluate_affiliate_candidate_quality,
    validate_affiliate_candidate_outputs,
    validate_affiliate_input_records,
)
from .block_runner import GenericBlockRunner
from .connection_dryrun_validator import validate_connection_dryrun
from .core_ai_handshake_package import build_core_ai_handshake_package

AFFILIATE_BLOCK_ID = "affiliate_block"
IR7_SCHEMA_VERSION = "ir7_integration_v1"
IR8_SCHEMA_VERSION = "ir8_practical_v1"
IR9_SCHEMA_VERSION = "ir9_quality_gate_v1"
IR10_SCHEMA_VERSION = "ir10_core_phase_decision_v1"

REQUIRED_AFFILIATE_PACKAGE_FILES = [
    "block_manifest.json",
    "config/policy.json",
    "app/schemas.py",
    "app/runner.py",
    "tests/test_schemas.py",
    "tests/test_runner.py",
    "_skeleton_summary.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_generated_runner(generated_dir: Path):
    runner_path = generated_dir / "app" / "runner.py"
    namespace: dict[str, Any] = {}
    exec(runner_path.read_text(encoding="utf-8"), namespace)
    run_fn = namespace.get("run_affiliate_block_dryrun")
    if not callable(run_fn):
        raise ValueError("generated runner does not expose run_affiliate_block_dryrun")
    return run_fn


def freeze_generated_affiliate_block_package(
    *,
    base_path: Path,
    block_id: str = AFFILIATE_BLOCK_ID,
) -> dict[str, Any]:
    """
    generated_skeleton_affiliate_block を正式 block package descriptor に固定する。
    出力は reports/affiliate_block_package_descriptor.json。
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    generated_dir = reports_dir / f"generated_skeleton_{block_id}"
    files_present: list[str] = []
    missing_files: list[str] = []
    checksums: dict[str, str] = {}

    for rel in REQUIRED_AFFILIATE_PACKAGE_FILES:
        p = generated_dir / rel
        if p.exists():
            files_present.append(rel)
            checksums[rel] = _sha256_text(p.read_text(encoding="utf-8"))
        else:
            missing_files.append(rel)

    status = "OK" if not missing_files else "ERROR"

    descriptor = {
        "_meta": {
            "schema_version": IR7_SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "phase": "IR7-T1",
            "status": status,
        },
        "package": {
            "block_id": block_id,
            "source_dir": str(generated_dir),
            "required_files": list(REQUIRED_AFFILIATE_PACKAGE_FILES),
            "files_present": files_present,
            "missing_files": missing_files,
            "checksums": checksums,
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    path = reports_dir / "affiliate_block_package_descriptor.json"
    path.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "descriptor": descriptor,
        "external_write_executed": False,
    }


def build_handshake_from_affiliate_runner_result(
    runner_result: dict[str, Any],
    *,
    source_task_id: str,
) -> dict[str, Any]:
    """
    generated affiliate runner の payload を core_ai handshake package に変換する。
    """
    candidates = runner_result.get("affiliate_candidates")
    if not isinstance(candidates, list):
        fallback = runner_result.get("recommended_candidates", [])
        candidates = fallback if isinstance(fallback, list) else []
    candidate_count = len(candidates)
    recommended_decision = (
        "RECOMMEND_APPROVE_DRY_RUN_ONLY" if candidate_count > 0 else "REQUIRE_HUMAN_REVIEW"
    )

    score = 70 if candidate_count > 0 else 55
    risk_balance = 65 if candidate_count > 0 else 50
    summary_text = str(runner_result.get("summary", ""))
    policy_hash = _sha256_text(f"affiliate_runner::{summary_text}::{candidate_count}")

    mapped_block_result: dict[str, Any] = {
        "status": runner_result.get("status", "success"),
        "decision": runner_result.get("decision", "human_review"),
        "summary": summary_text,
        "review_decision": {
            "recommended_decision": recommended_decision,
            "reason": "mapped_from_generated_affiliate_runner",
        },
        "quality_metrics": {
            "quality_score": score,
            "risk_balance": risk_balance,
            "review_readiness": "ready" if candidate_count > 0 else "not_ready",
        },
        "policy_versioning": {
            "version": "ir7-affiliate-runner-mapped",
            "policy_hash": policy_hash,
        },
        "signoff_audit": {
            "record": {
                "signoff": {
                    "actor": "affiliate_block_generated_runner",
                }
            }
        },
        "meta": {
            "block_id": AFFILIATE_BLOCK_ID,
            "version": "0.1.0",
        },
    }

    handshake_package = build_core_ai_handshake_package(
        mapped_block_result,
        source_task_id=source_task_id,
        block_id=AFFILIATE_BLOCK_ID,
        version="0.1.0",
    )
    validation = validate_connection_dryrun(handshake_package)

    return {
        "handshake_package": handshake_package,
        "validation_result": validation.result,
        "validation_failed_checks": validation.failed_checks,
        "validation_warnings": validation.warnings,
        "external_write_executed": False,
    }


def run_affiliate_generic_core_dryrun_trial(
    *,
    base_path: Path,
    source_task_id: str,
    affiliate_input_payload: dict[str, Any] | None = None,
    generic_runtime_base_path: Path | None = None,
    persist_human_review_artifacts: bool = True,
) -> dict[str, Any]:
    """
    三者 DRY_RUN 接続試験:
    affiliate_block (generated runner) -> generic_block_ai -> core_ai(handshake)
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = affiliate_input_payload or {"task_candidates": []}
    generated_dir = reports_dir / f"generated_skeleton_{AFFILIATE_BLOCK_ID}"

    freeze_output = freeze_generated_affiliate_block_package(base_path=base_path)
    if freeze_output["descriptor"]["_meta"]["status"] != "OK":
        return {
            "_meta": {
                "schema_version": IR7_SCHEMA_VERSION,
                "phase": "IR7-T3",
                "generated_at": _now_iso(),
                "status": "ERROR",
            },
            "freeze_package": freeze_output,
            "external_write_executed": False,
        }

    run_affiliate = _load_generated_runner(generated_dir)
    affiliate_result = run_affiliate(payload)

    handshake_from_affiliate = build_handshake_from_affiliate_runner_result(
        affiliate_result,
        source_task_id=f"{source_task_id}_affiliate",
    )

    generic_root = generic_runtime_base_path or base_path
    generic_runner = GenericBlockRunner(
        manifest_path=generic_root / "block_manifest.json",
        policy_path=generic_root / "config" / "policy.json",
    )

    recommended = affiliate_result.get("recommended_candidates", [])
    requested_actions: list[dict[str, Any]] = []
    if isinstance(recommended, list):
        for index, cand in enumerate(recommended):
            requested_actions.append(
                {
                    "type": "analyze",
                    "target": f"affiliate_candidate_{index}",
                    "justification": "generated affiliate candidate triage",
                    "payload": cand,
                }
            )

    generic_result = generic_runner.run(
        requested_actions=requested_actions,
        source_task_id=f"{source_task_id}_generic",
        persist_human_review_artifacts=persist_human_review_artifacts,
        signoff_actor="ir7_integration_trial",
    )

    connection_statuses = {
        "affiliate_to_core": handshake_from_affiliate["handshake_package"]["connection_status"],
        "generic_to_core": generic_result.get("core_ai_handshake", {}).get("connection_status"),
    }

    trial_result = {
        "_meta": {
            "schema_version": IR7_SCHEMA_VERSION,
            "phase": "IR7-T3",
            "generated_at": _now_iso(),
            "status": "OK",
        },
        "freeze_package": {
            "path": freeze_output["path"],
            "status": freeze_output["descriptor"]["_meta"]["status"],
        },
        "affiliate_stage": {
            "result": affiliate_result,
            "runner_to_core_handshake": {
                "connection_status": handshake_from_affiliate["handshake_package"]["connection_status"],
                "validation_result": handshake_from_affiliate["validation_result"],
                "validation_failed_checks": handshake_from_affiliate["validation_failed_checks"],
            },
        },
        "generic_stage": {
            "requested_actions_count": len(requested_actions),
            "result": {
                "status": generic_result.get("status"),
                "decision": generic_result.get("decision"),
                "core_ai_handshake": generic_result.get("core_ai_handshake"),
            },
        },
        "connection_statuses": connection_statuses,
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir7_three_party_dryrun_{source_task_id}.json"
    out_path.write_text(json.dumps(trial_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out_path),
        "trial_result": trial_result,
        "external_write_executed": False,
    }


def run_generic_affiliate_generic_core_roundtrip_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    affiliate_records: list[dict[str, Any]],
    generic_runtime_base_path: Path | None = None,
    persist_human_review_artifacts: bool = True,
) -> dict[str, Any]:
    """
    IR8-T4:
    generic_block_ai -> affiliate_block -> generic_block_ai -> core_ai の往復 DRY_RUN。
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    freeze_output = freeze_generated_affiliate_block_package(base_path=base_path)
    if freeze_output["descriptor"]["_meta"]["status"] != "OK":
        return {
            "_meta": {
                "schema_version": IR8_SCHEMA_VERSION,
                "phase": "IR8-T4",
                "generated_at": _now_iso(),
                "status": "ERROR",
                "reason": "affiliate_package_not_ready",
            },
            "freeze_package": freeze_output,
            "external_write_executed": False,
        }

    input_validation = validate_affiliate_input_records(affiliate_records)
    if input_validation.result == "FAIL":
        return {
            "_meta": {
                "schema_version": IR8_SCHEMA_VERSION,
                "phase": "IR8-T4",
                "generated_at": _now_iso(),
                "status": "ERROR",
                "reason": "invalid_affiliate_input_schema",
            },
            "input_validation": {
                "result": input_validation.result,
                "failed_checks": input_validation.failed_checks,
                "warnings": input_validation.warnings,
            },
            "external_write_executed": False,
        }

    generic_root = generic_runtime_base_path or base_path
    generic_runner = GenericBlockRunner(
        manifest_path=generic_root / "block_manifest.json",
        policy_path=generic_root / "config" / "policy.json",
    )

    pre_actions = [
        {
            "type": "analyze",
            "target": f"pre_affiliate_input_{idx}",
            "justification": "pre-screen affiliate practical records",
            "payload": rec,
        }
        for idx, rec in enumerate(affiliate_records)
    ]
    pre_generic = generic_runner.run(
        requested_actions=pre_actions,
        source_task_id=f"{source_task_id}_pre_generic",
        persist_human_review_artifacts=persist_human_review_artifacts,
        signoff_actor="ir8_roundtrip_pre_generic",
    )

    generated_dir = reports_dir / f"generated_skeleton_{AFFILIATE_BLOCK_ID}"
    run_affiliate = _load_generated_runner(generated_dir)
    affiliate_result = run_affiliate({"records": affiliate_records})

    candidates = affiliate_result.get("affiliate_candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    candidate_validation = validate_affiliate_candidate_outputs(candidates)
    quality_gate = evaluate_affiliate_candidate_quality(candidates)

    affiliate_to_core = build_handshake_from_affiliate_runner_result(
        affiliate_result,
        source_task_id=f"{source_task_id}_affiliate",
    )

    post_actions: list[dict[str, Any]] = []
    quality_items = {item["index"]: item for item in quality_gate.items}
    blocked_or_low = {"FAIL", "ABORT"}
    blocked_indexes = {
        index
        for index, item in quality_items.items()
        if item.get("decision") in blocked_or_low
    }

    for idx, cand in enumerate(candidates):
        if idx in blocked_indexes:
            continue
        post_actions.append(
            {
                "type": "analyze",
                "target": f"post_affiliate_candidate_{idx}",
                "justification": "post-process affiliate candidate for core handoff",
                "payload": cand,
            }
        )
    post_generic = generic_runner.run(
        requested_actions=post_actions,
        source_task_id=f"{source_task_id}_post_generic",
        persist_human_review_artifacts=persist_human_review_artifacts,
        signoff_actor="ir8_roundtrip_post_generic",
    )

    roundtrip_judgment = quality_gate.status
    if input_validation.result == "FAIL" or candidate_validation.result == "FAIL":
        roundtrip_judgment = "FAIL"
    if affiliate_to_core["validation_result"] == "FAIL":
        roundtrip_judgment = "ABORT"

    result = {
        "_meta": {
            "schema_version": IR9_SCHEMA_VERSION,
            "phase": "IR9-T3",
            "generated_at": _now_iso(),
            "status": "OK",
        },
        "freeze_package": {
            "path": freeze_output["path"],
            "status": freeze_output["descriptor"]["_meta"]["status"],
        },
        "input_validation": {
            "result": input_validation.result,
            "failed_checks": input_validation.failed_checks,
            "warnings": input_validation.warnings,
        },
        "pre_generic": {
            "status": pre_generic.get("status"),
            "decision": pre_generic.get("decision"),
            "core_ai_handshake": pre_generic.get("core_ai_handshake"),
        },
        "affiliate": {
            "result": affiliate_result,
            "candidate_validation": {
                "result": candidate_validation.result,
                "failed_checks": candidate_validation.failed_checks,
                "warnings": candidate_validation.warnings,
            },
            "quality_gate": {
                "status": quality_gate.status,
                "summary": quality_gate.summary,
                "items": quality_gate.items,
                "warnings": quality_gate.warnings,
            },
            "runner_to_core_handshake": {
                "connection_status": affiliate_to_core["handshake_package"]["connection_status"],
                "validation_result": affiliate_to_core["validation_result"],
                "validation_failed_checks": affiliate_to_core["validation_failed_checks"],
            },
        },
        "post_generic": {
            "status": post_generic.get("status"),
            "decision": post_generic.get("decision"),
            "core_ai_handshake": post_generic.get("core_ai_handshake"),
            "requested_actions_count": len(post_actions),
            "blocked_candidates_count": len(blocked_indexes),
        },
        "quality_gate_judgment": roundtrip_judgment,
        "connection_statuses": {
            "affiliate_to_core": affiliate_to_core["handshake_package"]["connection_status"],
            "pre_generic_to_core": pre_generic.get("core_ai_handshake", {}).get("connection_status"),
            "post_generic_to_core": post_generic.get("core_ai_handshake", {}).get("connection_status"),
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir8_roundtrip_dryrun_{source_task_id}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out_path),
        "roundtrip_result": result,
        "external_write_executed": False,
    }


def write_ir9_completion_report(
    *,
    base_path: Path,
    roundtrip_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR9-T5 completion report を生成する。
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    rr = roundtrip_output.get("roundtrip_result", {}) if isinstance(roundtrip_output, dict) else {}
    quality_gate = rr.get("affiliate", {}).get("quality_gate", {}) if isinstance(rr, dict) else {}

    report = {
        "phase": "Implementation Restart Phase 9",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR9_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "quality_gate": {
            "overall_status": quality_gate.get("status", "UNKNOWN"),
            "summary": quality_gate.get("summary", {}),
            "warnings": quality_gate.get("warnings", []),
        },
        "roundtrip_judgment": rr.get("quality_gate_judgment", "UNKNOWN"),
        "safeguards": rr.get("safeguards", {}),
        "artifacts": {
            "roundtrip": roundtrip_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase9_completion_report.json",
        },
    }

    out_path = reports_dir / "implementation_restart_phase9_completion_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out_path),
        "completion_report": report,
        "external_write_executed": False,
    }


def _normalize_quality_judgment(value: Any) -> str:
    text = str(value or "WARN").upper()
    return text if text in {"PASS", "WARN", "FAIL", "ABORT"} else "WARN"


def _map_quality_to_core_rule(quality_gate_judgment: str) -> dict[str, str]:
    mapping = {
        "PASS": {
            "recommended_decision": "RECOMMEND_APPROVE_DRY_RUN_ONLY",
            "core_receive_rule": "ACCEPT_DRY_RUN_REVIEW_QUEUE",
            "reason": "quality_gate_passed",
        },
        "WARN": {
            "recommended_decision": "REQUIRE_HUMAN_REVIEW",
            "core_receive_rule": "HUMAN_REVIEW_REQUIRED",
            "reason": "quality_gate_warn_requires_human_review",
        },
        "FAIL": {
            "recommended_decision": "RECOMMEND_REJECT",
            "core_receive_rule": "REJECT_AND_KEEP_NO_GO",
            "reason": "quality_gate_failed",
        },
        "ABORT": {
            "recommended_decision": "BLOCKED_BY_POLICY",
            "core_receive_rule": "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE",
            "reason": "quality_gate_abort_policy_or_legal",
        },
    }
    return mapping[quality_gate_judgment]


def _extract_quality_metrics(roundtrip_result: dict[str, Any]) -> dict[str, Any]:
    quality_gate = roundtrip_result.get("affiliate", {}).get("quality_gate", {})
    summary = quality_gate.get("summary", {}) if isinstance(quality_gate, dict) else {}
    items = quality_gate.get("items", []) if isinstance(quality_gate, dict) else []
    scores = [int(item.get("quality_score", 0)) for item in items if isinstance(item, dict)]
    avg_score = int(sum(scores) / len(scores)) if scores else 0

    abort_count = int(summary.get("abort_count", 0) or 0)
    fail_count = int(summary.get("fail_count", 0) or 0)
    warn_count = int(summary.get("warn_count", 0) or 0)
    pass_count = int(summary.get("pass_count", 0) or 0)
    candidate_count = int(summary.get("candidate_count", len(scores)) or len(scores))

    risk_balance = max(0, 100 - (abort_count * 50 + fail_count * 30 + warn_count * 10))
    review_readiness = "ready" if abort_count == 0 and fail_count == 0 else "not_ready"
    if warn_count > 0 and review_readiness == "ready":
        review_readiness = "needs_human_review"

    return {
        "quality_score": avg_score,
        "risk_balance": risk_balance,
        "review_readiness": review_readiness,
        "candidate_count": candidate_count,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "abort_count": abort_count,
    }


def build_ir10_core_phase_decision_package(
    *,
    roundtrip_output: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """
    IR10-T1/T2:
    IR9 quality_gate_judgment を Core AI phase decision package に変換。
    """
    roundtrip_result = roundtrip_output.get("roundtrip_result", {})
    quality_gate_judgment = _normalize_quality_judgment(roundtrip_result.get("quality_gate_judgment"))
    rule = _map_quality_to_core_rule(quality_gate_judgment)
    metrics = _extract_quality_metrics(roundtrip_result)

    quality_gate = roundtrip_result.get("affiliate", {}).get("quality_gate", {})
    policy_hash = _sha256_text(
        json.dumps(
            {
                "source_task_id": source_task_id,
                "judgment": quality_gate_judgment,
                "summary": quality_gate.get("summary", {}),
                "items": quality_gate.get("items", []),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    block_result = {
        "status": "success",
        "decision": "human_review",
        "summary": f"ir10 mapped from quality_gate_judgment={quality_gate_judgment}",
        "review_decision": {
            "recommended_decision": rule["recommended_decision"],
            "reason": rule["reason"],
        },
        "quality_metrics": {
            "quality_score": metrics["quality_score"],
            "risk_balance": metrics["risk_balance"],
            "review_readiness": metrics["review_readiness"],
        },
        "policy_versioning": {
            "version": "ir10-quality-gate-mapping-v1",
            "policy_hash": policy_hash,
        },
        "signoff_audit": {
            "record": {
                "signoff": {
                    "actor": "ir10_phase_decision_mapper",
                }
            }
        },
        "meta": {
            "block_id": AFFILIATE_BLOCK_ID,
            "version": "0.1.0",
        },
    }

    handshake_package = build_core_ai_handshake_package(
        block_result,
        source_task_id=f"{source_task_id}_ir10",
        block_id=AFFILIATE_BLOCK_ID,
        version="0.1.0",
    )
    validation = validate_connection_dryrun(handshake_package)

    return {
        "schema_version": IR10_SCHEMA_VERSION,
        "quality_gate_judgment": quality_gate_judgment,
        "mapping_rule": rule,
        "quality_metrics_snapshot": metrics,
        "core_phase_decision_package": handshake_package,
        "validation_result": validation.result,
        "validation_failed_checks": validation.failed_checks,
        "validation_warnings": validation.warnings,
        "external_write_executed": False,
    }


def run_ir10_phase_decision_package_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    roundtrip_output: dict[str, Any],
) -> dict[str, Any]:
    """
    IR10-T1/T2/T3/T4:
    - IR9 judgment -> Core AI phase decision package
    - WARN 時 human_review package 自動生成
    - ABORT 時 evidence/audit 強制保存
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    package_output = build_ir10_core_phase_decision_package(
        roundtrip_output=roundtrip_output,
        source_task_id=source_task_id,
    )

    decision_path = reports_dir / f"ir10_core_phase_decision_package_{source_task_id}.json"
    decision_path.write_text(json.dumps(package_output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    judgment = package_output["quality_gate_judgment"]
    human_review_path: str | None = None
    abort_evidence_path: str | None = None

    if judgment == "WARN":
        human_review_package = {
            "schema_version": IR10_SCHEMA_VERSION,
            "phase": "IR10-T3",
            "generated_at": _now_iso(),
            "status": "PENDING_HUMAN_REVIEW",
            "source_task_id": source_task_id,
            "quality_gate_judgment": judgment,
            "required_actions": [
                "review_warn_candidates",
                "approve_or_reject_decision_package",
            ],
            "safeguards": {
                "mode": "dry_run",
                "operation_mode": "OBSERVE",
                "external_write_executed": False,
                "actual_auto_execute": False,
                "production_release": False,
            },
        }
        p = reports_dir / f"ir10_human_review_package_{source_task_id}.json"
        p.write_text(json.dumps(human_review_package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        human_review_path = str(p)

    if judgment == "ABORT":
        abort_bundle = {
            "schema_version": IR10_SCHEMA_VERSION,
            "phase": "IR10-T4",
            "generated_at": _now_iso(),
            "status": "ABORT_LOCKED",
            "source_task_id": source_task_id,
            "reason": "quality_gate_abort_policy_or_legal",
            "evidence_lock": {
                "required": True,
                "allow_delete": False,
                "allow_overwrite": False,
            },
            "audit_must_preserve": [
                "roundtrip_output",
                "quality_gate_items",
                "core_phase_decision_package",
            ],
            "safeguards": {
                "mode": "dry_run",
                "operation_mode": "OBSERVE",
                "external_write_executed": False,
                "actual_auto_execute": False,
                "production_release": False,
            },
        }
        p = reports_dir / f"ir10_abort_evidence_bundle_{source_task_id}.json"
        p.write_text(json.dumps(abort_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        abort_evidence_path = str(p)

    return {
        "path": str(decision_path),
        "decision_package": package_output,
        "human_review_package_path": human_review_path,
        "abort_evidence_bundle_path": abort_evidence_path,
        "external_write_executed": False,
    }


def write_ir10_completion_report(
    *,
    base_path: Path,
    ir10_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR10-T5 completion report を生成する。
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    decision_package = ir10_output.get("decision_package", {}) if isinstance(ir10_output, dict) else {}
    report = {
        "phase": "Implementation Restart Phase 10",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR10_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "quality_gate_judgment": decision_package.get("quality_gate_judgment", "UNKNOWN"),
        "core_receive_rule": decision_package.get("mapping_rule", {}).get("core_receive_rule", "UNKNOWN"),
        "validation_result": decision_package.get("validation_result", "UNKNOWN"),
        "artifacts": {
            "ir10_phase_decision_package": ir10_output.get("path", "UNKNOWN"),
            "human_review_package": ir10_output.get("human_review_package_path"),
            "abort_evidence_bundle": ir10_output.get("abort_evidence_bundle_path"),
            "completion_report": "reports/implementation_restart_phase10_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase10_completion_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out_path),
        "completion_report": report,
        "external_write_executed": False,
    }


def write_ir8_practical_runbook(*, base_path: Path) -> dict[str, Any]:
    """
    IR8-T4 向け practical dry-run runbook を出力する。
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    runbook = {
        "_meta": {
            "schema_version": "runbook_v1",
            "phase": "IR8-T4",
            "generated_at": _now_iso(),
            "status": "READY",
        },
        "objective": "practical affiliate records roundtrip dry-run",
        "steps": [
            {
                "step": 1,
                "name": "freeze generated affiliate package",
                "action": "freeze_generated_affiliate_block_package(base_path)",
                "pass_condition": "status == OK",
            },
            {
                "step": 2,
                "name": "validate input records schema",
                "action": "validate_affiliate_input_records(records)",
                "pass_condition": "result in {PASS, WARN}",
            },
            {
                "step": 3,
                "name": "run roundtrip dry-run",
                "action": "run_generic_affiliate_generic_core_roundtrip_dryrun(...) ",
                "pass_condition": "roundtrip_result._meta.status == OK",
            },
            {
                "step": 4,
                "name": "full regression",
                "action": "python3 -m pytest -q generic_block_ai/tests",
                "pass_condition": "all tests pass",
            },
        ],
        "abort_conditions": [
            "input_validation.result == FAIL",
            "candidate_validation.result == FAIL",
            "any core_ai_handshake.validation_result == FAIL",
            "external_write_executed == true",
        ],
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    path = reports_dir / "ir8_generated_affiliate_practical_runbook.json"
    path.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "runbook": runbook, "external_write_executed": False}


def write_ir7_integration_runbook(*, base_path: Path) -> dict[str, Any]:
    """
    IR7-T4 接続試験 runbook を JSON で出力する。
    """
    runbook = {
        "_meta": {
            "schema_version": "runbook_v1",
            "phase": "IR7-T4",
            "generated_at": _now_iso(),
            "status": "READY",
        },
        "objective": "generated affiliate block skeleton integration dry-run",
        "steps": [
            {
                "step": 1,
                "name": "freeze generated package",
                "action": "freeze_generated_affiliate_block_package(base_path)",
                "pass_condition": "descriptor._meta.status == OK",
            },
            {
                "step": 2,
                "name": "runner payload to handshake",
                "action": "build_handshake_from_affiliate_runner_result(runner_result, source_task_id)",
                "pass_condition": "validation_result == PASS",
            },
            {
                "step": 3,
                "name": "three-party dry-run trial",
                "action": "run_affiliate_generic_core_dryrun_trial(base_path, source_task_id)",
                "pass_condition": "trial_result._meta.status == OK",
            },
            {
                "step": 4,
                "name": "regression",
                "action": "python3 -m pytest -q generic_block_ai/tests",
                "pass_condition": "all tests pass",
            },
        ],
        "abort_conditions": [
            "freeze package status != OK",
            "handshake validation_result == FAIL",
            "generic core_ai_handshake.validation_result == FAIL",
            "external_write_executed == true",
        ],
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "ir7_generated_affiliate_integration_runbook.json"
    path.write_text(json.dumps(runbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "runbook": runbook, "external_write_executed": False}
