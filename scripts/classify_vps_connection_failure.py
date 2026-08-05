#!/usr/bin/env python3
"""Classify Phase 7-4 VPS connection failure patterns."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "config/vps_connection_failure_taxonomy.json"
EVALUATION = ROOT / "exchange/logs/vps_connection_stability_evaluation_result.json"
CONNECTIVITY = ROOT / "exchange/logs/vps_connectivity_check.example.json"
OUTPUT = ROOT / "exchange/logs/vps_connection_failure_classification_result.json"


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_4_vps_connection_failure_classification_result",
        "phase": "Phase 7-4",
        "status": "ABORT",
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def classify(
    taxonomy_path: Path = TAXONOMY,
    evaluation_path: Path = EVALUATION,
    connectivity_path: Path = CONNECTIVITY,
    output_path: Path = OUTPUT,
) -> dict:
    for required in (taxonomy_path, evaluation_path):
        if not required.exists():
            return _abort(f"required file not found: {required}")

    taxonomy = _load(taxonomy_path)
    evaluation = _load(evaluation_path)
    connectivity = _load(connectivity_path) if connectivity_path.exists() else {}

    constraints = taxonomy.get("constraints", {})
    if constraints.get("auto_remediation_enabled") is not False:
        return _abort("auto_remediation_enabled must be false")

    categories = []
    status = evaluation.get("overall_status")

    if status == "ABORT":
        categories.append("LOCAL_CLIENT_ISSUE")
    else:
        tcp_fail_rate = float(evaluation.get("tcp_22_fail_rate", 0))
        avg_latency = float(evaluation.get("average_latency_ms", 0))
        avg_packet = float(evaluation.get("average_packet_loss_percent", 0))
        ssh_auth_fail = int(evaluation.get("ssh_auth_dry_run_fail_count", 0))
        ssh_banner_fail = int(evaluation.get("ssh_banner_fail_count", 0))

        if tcp_fail_rate >= 30:
            categories.append("TCP_22_BLOCKED")
        if tcp_fail_rate >= 90:
            categories.append("NETWORK_UNREACHABLE")
        if ssh_auth_fail >= 1:
            categories.append("SSH_AUTH_FAILED")
        if ssh_banner_fail >= 1:
            categories.append("SSH_BANNER_TIMEOUT")
        if avg_latency >= 300:
            categories.append("HIGH_LATENCY")
        if avg_packet >= 5:
            categories.append("PACKET_LOSS")

        reason = str(connectivity.get("reason", "")).lower()
        alias = str(connectivity.get("target_host_alias", "")).lower()
        if "dns" in reason or "host alias" in reason or "mismatch" in reason or alias == "":
            categories.append("DNS_OR_HOST_ALIAS_MISMATCH")

    if not categories:
        categories = ["UNKNOWN"]

    unique_categories = []
    for item in categories:
        if item not in unique_categories:
            unique_categories.append(item)

    result = {
        "package_type": "phase7_4_vps_connection_failure_classification_result",
        "phase": "Phase 7-4",
        "status": "PASS",
        "production_status": "NO_GO",
        "human_review_required": True,
        "classification_is_estimation_only": True,
        "auto_remediation_executed": False,
        "forbidden_operations_executed": False,
        "classification": unique_categories,
        "source_overall_status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = classify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())