#!/usr/bin/env python3
"""N-6: 24時間相当連続監視 DRY_RUN シミュレーション。

実際の長時間稼働は行わない。policy で定義した間隔・回数を元に
期待チェックスケジュールを生成し、結果を証跡として出力する。
"""
import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/n6_continuous_monitoring_dry_run_policy.json"
REQUEST = ROOT / "exchange/examples/n6_continuous_monitoring_dry_run_request.example.json"
OUTPUT = ROOT / "exchange/logs/n6_continuous_monitoring_dry_run_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_simulation(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict:
    base = {
        "phase": "N-6",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "wordpress_post_created": False,
        "external_state_change": False,
        "executor_action_allowed": False,
        "network_observation_only": True,
        "communication_test_only": True,
        "actual_long_run_executed": False,
        "checked_at": _now_iso(),
    }

    try:
        policy = _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {**base, "status": "FAIL", "reason": f"input_load_error: {exc}", "schedule": []}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    simulated_hours = int(req.get("simulated_duration_hours") or policy.get("simulated_duration_hours", 24))
    interval_min = int(req.get("check_interval_minutes") or policy.get("check_interval_minutes", 60))
    expected_count = int(policy.get("expected_check_count", simulated_hours * 60 // interval_min))
    check_targets = policy.get("check_targets", [])
    fail_threshold = float(policy.get("acceptable_fail_rate_percent", 5)) / 100
    seed = req.get("seed", 0)
    rng = random.Random(seed)

    schedule = []
    fail_count = 0
    for i in range(expected_count):
        minute_offset = i * interval_min
        all_ok = rng.random() > 0.02  # 2% synthetic failure rate
        check_results = {
            t: "PASS" if all_ok else ("FAIL" if check_targets and t == check_targets[0] else "PASS")
            for t in check_targets
        }
        item_status = "PASS" if all_ok else "FAIL"
        if not all_ok:
            fail_count += 1
        schedule.append({
            "index": i,
            "simulated_offset_minutes": minute_offset,
            "check_results": check_results,
            "status": item_status,
        })

    actual_fail_rate = fail_count / expected_count if expected_count else 0
    status = "PASS" if actual_fail_rate <= fail_threshold else "FAIL"

    result = {
        **base,
        "status": status,
        "simulated_duration_hours": simulated_hours,
        "check_interval_minutes": interval_min,
        "expected_check_count": expected_count,
        "actual_check_count": len(schedule),
        "fail_count": fail_count,
        "fail_rate_percent": round(actual_fail_rate * 100, 2),
        "acceptable_fail_rate_percent": round(fail_threshold * 100, 2),
        "schedule": schedule,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_simulation()
    summary = {k: v for k, v in result.items() if k != "schedule"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
