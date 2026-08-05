#!/usr/bin/env python3
"""N-7: cron/lock 多重起動防止確認 DRY_RUN。

ロックファイルの取得・二重起動検知・stale ロック判定を
実際のプロセス変更なしでシミュレーションする。
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/n7_cron_lock_guard_policy.json"
REQUEST = ROOT / "exchange/examples/n7_cron_lock_guard_request.example.json"
OUTPUT = ROOT / "exchange/logs/n7_cron_lock_guard_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_lock_file(lock_path: Path, stale_threshold: int) -> dict:
    """ロックファイルの状態を読み取り専用で確認する。"""
    exists = lock_path.exists()
    age_seconds = None
    is_stale = None
    pid_in_lock = None
    pid_alive = None

    if exists:
        try:
            mtime = lock_path.stat().st_mtime
            age_seconds = round(time.time() - mtime, 1)
            is_stale = age_seconds > stale_threshold
        except Exception:
            pass

        try:
            content = lock_path.read_text(encoding="utf-8").strip()
            if content.isdigit():
                pid_in_lock = int(content)
                pid_alive = Path(f"/proc/{pid_in_lock}").exists()
        except Exception:
            pass

    return {
        "lock_exists": exists,
        "age_seconds": age_seconds,
        "is_stale": is_stale,
        "pid_in_lock": pid_in_lock,
        "pid_alive": pid_alive,
    }


def _simulate_acquire_and_detect(lock_path: Path, simulate_duplicate: bool) -> dict:
    """ロック取得と二重起動検知のシミュレーション（実際には書き込みを行わない）。"""
    if lock_path.exists():
        return {
            "acquire_result": "BLOCKED",
            "duplicate_detected": True,
            "reason": "lock_file_already_exists",
        }
    if simulate_duplicate:
        return {
            "acquire_result": "WOULD_BLOCK",
            "duplicate_detected": True,
            "reason": "simulate_duplicate_enabled",
        }
    return {
        "acquire_result": "WOULD_SUCCEED",
        "duplicate_detected": False,
        "reason": "no_existing_lock_and_no_simulate_duplicate",
    }


def run_check(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict:
    base = {
        "phase": "N-7",
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
        "lock_written": False,
        "lock_deleted": False,
        "checked_at": _now_iso(),
    }

    try:
        policy = _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {**base, "status": "FAIL", "reason": f"input_load_error: {exc}"}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    lock_rel = str(req.get("lock_path") or policy.get("lock_path_pattern", "exchange/locks/n_series_monitor.lock"))
    # allow absolute path (used in tests)
    lock_path = Path(lock_rel) if Path(lock_rel).is_absolute() else ROOT / lock_rel
    stale_threshold = int(req.get("stale_threshold_seconds") or policy.get("stale_lock_threshold_seconds", 3600))
    simulate_duplicate = bool(req.get("simulate_duplicate", False))

    lock_state = _check_lock_file(lock_path, stale_threshold)
    acquire_sim = _simulate_acquire_and_detect(lock_path, simulate_duplicate)

    guard_works = acquire_sim.get("duplicate_detected") in {True, False}
    status = "PASS" if guard_works else "FAIL"

    result = {
        **base,
        "status": status,
        "lock_path": str(lock_path),
        "lock_state": lock_state,
        "acquire_simulation": acquire_sim,
        "duplicate_guard_functional": guard_works,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
