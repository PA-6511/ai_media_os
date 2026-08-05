#!/usr/bin/env python3
"""Evaluate Phase 7-3 VPS connection stability samples."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "exchange/logs/vps_stability_samples.example.json"
OUTPUT = ROOT / "exchange/logs/vps_connection_stability_evaluation_result.json"


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_3_vps_connection_stability_evaluation_result",
        "phase": "Phase 7-3",
        "status": "ABORT",
        "reason": reason,
        "overall_status": "ABORT",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _status_rank(status: str) -> int:
    order = {
        "PASS_DRY_RUN_ONLY": 0,
        "WARN_DRY_RUN_ONLY": 1,
        "FAIL_DRY_RUN_ONLY": 2,
        "ABORT": 3,
    }
    return order.get(status, 3)


def _merge_status(base: str, new: str) -> str:
    return new if _status_rank(new) > _status_rank(base) else base


def evaluate(samples_data: dict) -> dict:
    samples = samples_data.get("samples", [])
    if not isinstance(samples, list):
        return _abort("samples must be a list")

    if samples_data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")

    if len(samples) == 0:
        return _abort("samples must not be empty")

    tcp_pass = 0
    tcp_fail = 0
    ssh_auth_fail = 0
    ssh_banner_fail = 0
    latency_values = []
    packet_values = []

    for idx, sample in enumerate(samples):
        if sample.get("secrets_exposed") is True:
            return _abort(f"sample[{idx}] secrets_exposed=true is forbidden")
        if sample.get("remote_write_executed") is True:
            return _abort(f"sample[{idx}] remote_write_executed=true is forbidden")
        if sample.get("remote_command_executed") is True:
            return _abort(f"sample[{idx}] remote_command_executed=true is forbidden")

        tcp = sample.get("tcp_22_result")
        if tcp == "PASS":
            tcp_pass += 1
        elif tcp == "FAIL":
            tcp_fail += 1

        if sample.get("ssh_auth_dry_run_result") == "FAIL":
            ssh_auth_fail += 1
        if sample.get("ssh_banner_result") == "FAIL":
            ssh_banner_fail += 1

        latency = sample.get("latency_ms")
        if not isinstance(latency, (int, float)) or latency < 0:
            return _abort(f"sample[{idx}] latency_ms must be >= 0")
        latency_values.append(float(latency))

        packet = sample.get("packet_loss_percent")
        if not isinstance(packet, (int, float)) or packet < 0 or packet > 100:
            return _abort(f"sample[{idx}] packet_loss_percent must be between 0 and 100")
        packet_values.append(float(packet))

    sample_count = len(samples)
    tcp_fail_rate = (tcp_fail / sample_count) * 100
    tcp_pass_rate = (tcp_pass / sample_count) * 100
    avg_latency = sum(latency_values) / sample_count
    avg_packet_loss = sum(packet_values) / sample_count

    overall = "PASS_DRY_RUN_ONLY"
    reasons = []

    if sample_count < 5:
        overall = _merge_status(overall, "WARN_DRY_RUN_ONLY")
        reasons.append("sample_count is less than 5")

    if tcp_pass_rate < 90:
        overall = _merge_status(overall, "WARN_DRY_RUN_ONLY")
        reasons.append("tcp_22 PASS rate is below 90%")

    if tcp_fail >= 1:
        overall = _merge_status(overall, "WARN_DRY_RUN_ONLY")
        reasons.append("tcp_22 has at least one FAIL")

    if tcp_fail_rate >= 30:
        overall = _merge_status(overall, "FAIL_DRY_RUN_ONLY")
        reasons.append("tcp_22 FAIL rate is 30% or higher")

    if ssh_auth_fail >= 1:
        overall = _merge_status(overall, "WARN_DRY_RUN_ONLY")
        reasons.append("ssh_auth_dry_run has at least one FAIL")

    if avg_packet_loss >= 5:
        overall = _merge_status(overall, "WARN_DRY_RUN_ONLY")
        reasons.append("average packet loss is 5% or higher")

    if avg_packet_loss >= 20:
        overall = _merge_status(overall, "FAIL_DRY_RUN_ONLY")
        reasons.append("average packet loss is 20% or higher")

    if avg_latency >= 300:
        overall = _merge_status(overall, "WARN_DRY_RUN_ONLY")
        reasons.append("average latency is 300ms or higher")

    if avg_latency >= 1000:
        overall = _merge_status(overall, "FAIL_DRY_RUN_ONLY")
        reasons.append("average latency is 1000ms or higher")

    result = {
        "package_type": "phase7_3_vps_connection_stability_evaluation_result",
        "phase": "Phase 7-3",
        "status": "PASS",
        "overall_status": overall,
        "sample_count": sample_count,
        "tcp_22_pass_rate": round(tcp_pass_rate, 2),
        "tcp_22_fail_count": tcp_fail,
        "tcp_22_fail_rate": round(tcp_fail_rate, 2),
        "ssh_auth_dry_run_fail_count": ssh_auth_fail,
        "ssh_banner_fail_count": ssh_banner_fail,
        "average_latency_ms": round(avg_latency, 2),
        "average_packet_loss_percent": round(avg_packet_loss, 2),
        "production_status": "NO_GO",
        "human_review_required": True,
        "reasons": reasons,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def run_evaluation(input_path: Path = INPUT, output_path: Path = OUTPUT) -> dict:
    if not input_path.exists():
        return _abort(f"input not found: {input_path}")

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _abort(f"invalid JSON: {exc}")

    result = evaluate(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_evaluation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("overall_status") != "ABORT" else 1


if __name__ == "__main__":
    raise SystemExit(main())