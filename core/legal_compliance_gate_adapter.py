"""Legal & Compliance Gate adapter for Core integration (Phase L-3).

This module only provides a connection point and payload transformation.
It does not change Core final decision logic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from legal_compliance_gate_ai.core.legal_compliance_scanner import (
    load_registry,
    scan_legal_compliance,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "legal_compliance_gate_ai" / "config" / "legal_risk_registry.json"
)
DEFAULT_OBSERVATION_DIR = REPO_ROOT / "reports" / "legal_compliance_gate_observations"

_VALID_DECISION_STATUSES = {"PASS", "WARN", "FAIL", "ABORT"}


def _derive_risk_level(scan_status: str, detected_risks: list[dict[str, Any]]) -> str:
    if scan_status == "ABORT":
        return "CRITICAL"

    severities = {str(r.get("severity", "")).upper() for r in detected_risks}
    if "CRITICAL" in severities:
        return "CRITICAL"
    if "HIGH" in severities:
        return "HIGH"
    if "MEDIUM" in severities:
        return "MEDIUM"
    return "LOW"


def _to_decision_status(legal_status: str) -> str:
    # Keep decision_package-compatible statuses while preserving legal status separately.
    if legal_status == "LEGAL_REVIEW_REQUIRED":
        return "WARN"
    if legal_status in _VALID_DECISION_STATUSES:
        return legal_status
    return "FAIL"


def run_legal_compliance_gate_for_core(
    input_payload: dict[str, Any],
    *,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Run Legal Gate scan and convert to a Core decision_package-like payload."""
    registry = load_registry(str(registry_path or DEFAULT_REGISTRY_PATH))
    scan_result = scan_legal_compliance(input_payload, registry)
    return build_legal_gate_decision_package(scan_result)


def build_legal_gate_decision_package(scan_result: dict[str, Any]) -> dict[str, Any]:
    """Build a Core-facing decision_package-like dict from legal scan output."""
    legal_status = str(scan_result.get("status", "FAIL"))
    decision_status = _to_decision_status(legal_status)
    detected_risks = scan_result.get("detected_risks", [])
    if not isinstance(detected_risks, list):
        detected_risks = []

    required_actions = scan_result.get("required_actions", [])
    if not isinstance(required_actions, list):
        required_actions = []

    human_review_required = bool(scan_result.get("human_review_required", False))
    if legal_status in {"LEGAL_REVIEW_REQUIRED", "ABORT", "FAIL"}:
        human_review_required = True

    return {
        "package_type": "decision_package",
        "source": "legal_compliance_gate_ai",
        "target": str(scan_result.get("source_block_id") or "core_ai"),
        "mode": "CONNECTION_TEST",
        "execution": str(scan_result.get("execution") or "DRY_RUN").upper(),
        "risk_level": _derive_risk_level(legal_status, detected_risks),
        "human_approval_required": human_review_required,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "decision": {
            "status": decision_status,
            "reason": "legal_compliance_gate_signal",
            "requires_human_review": human_review_required,
            "core_final_decision_required": True,
        },
        "legal_gate": {
            "status": legal_status,
            "detected_risks": detected_risks,
            "required_actions": required_actions,
            "human_review_required": human_review_required,
            "core_final_decision_required": True,
            "task_id": scan_result.get("task_id"),
            "block_id": scan_result.get("block_id", "legal_compliance_gate_ai"),
        },
        "integration_notes": {
            "connection_phase": "L-3",
            "adapter_only": True,
            "core_decision_logic_changed": False,
            "human_review_route_ready": legal_status
            in {"LEGAL_REVIEW_REQUIRED", "ABORT", "FAIL", "WARN"},
        },
    }


def _pick_representative_proposal(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    if not proposals:
        return {}
    return max(proposals, key=lambda row: float(row.get("priority", 0.0)))


def build_legal_scan_input_from_core_input(core_input: dict[str, Any]) -> dict[str, Any]:
    proposals_raw = core_input.get("proposals", [])
    proposals = proposals_raw if isinstance(proposals_raw, list) else []
    representative = _pick_representative_proposal([p for p in proposals if isinstance(p, dict)])

    metadata = representative.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    signals = metadata.get("signals", [])
    if not isinstance(signals, list):
        signals = []

    external_services = metadata.get("external_services", [])
    if not isinstance(external_services, list):
        external_services = []

    policy_sources = metadata.get("policy_sources", [])
    if not isinstance(policy_sources, list):
        policy_sources = []

    return {
        "task_id": str(representative.get("task_id") or representative.get("item_id") or "core_input_observation"),
        "source_block_id": str(representative.get("block_name") or "core_input"),
        "operation_type": "core_input_observation",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "content_summary": str(representative.get("reason") or "core_input_observation"),
        "signals": signals,
        "external_services": external_services,
        "contains_personal_data": bool(metadata.get("contains_personal_data", False)),
        "contains_secret_like_text": bool(metadata.get("contains_secret_like_text", False)),
        "disclosure_checked": bool(metadata.get("disclosure_checked", False)),
        "policy_sources": policy_sources,
    }


def observe_legal_gate_in_core_input(
    core_input: dict[str, Any],
    *,
    event_id: str,
    registry_path: Path | None = None,
    output_dir: Path | None = None,
    logger: Any | None = None,
) -> dict[str, Any]:
    """Observe Core input with Legal Gate in log-only mode.

    This never alters Core decision logic. It only appends a decision_package-like
    record for monitoring and stores an immutable report.
    """
    input_payload = build_legal_scan_input_from_core_input(core_input)
    decision_package = run_legal_compliance_gate_for_core(
        input_payload,
        registry_path=registry_path,
    )

    # Append for downstream observability without changing runtime behavior.
    decision_packages = core_input.get("decision_packages")
    if not isinstance(decision_packages, list):
        decision_packages = []
        core_input["decision_packages"] = decision_packages
    decision_packages.append(decision_package)

    snapshot = {
        "event_id": event_id,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOG_ONLY",
        "execution": "DRY_RUN",
        "core_flow_impact": "NONE",
        "core_decision_logic_changed": False,
        "decision_package": decision_package,
    }

    target_dir = Path(output_dir or DEFAULT_OBSERVATION_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_dir / f"legal_gate_observation_{event_id}.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    snapshot["report_path"] = str(report_path)
    if logger is not None:
        logger.info(
            "[Runtime] legal gate observed (log-only) status=%s decision_status=%s event_id=%s",
            decision_package.get("legal_gate", {}).get("status"),
            decision_package.get("decision", {}).get("status"),
            event_id,
        )
    return snapshot
