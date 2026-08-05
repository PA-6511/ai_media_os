import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n7_cron_lock_guard_check import run_check


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_duplicate_guard_functional_no_lock(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write(policy, {"lock_path_pattern": "exchange/locks/test.lock", "stale_lock_threshold_seconds": 3600})
    _write(request, {
        "lock_path": "exchange/locks/test.lock",
        "stale_threshold_seconds": 3600,
        "simulate_duplicate": False,
    })

    result = run_check(policy, request, output)
    assert result["status"] == "PASS"
    assert result["duplicate_guard_functional"] is True
    assert result["lock_written"] is False
    assert result["lock_deleted"] is False
    assert output.exists()


def test_duplicate_detected_when_simulate_duplicate(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write(policy, {"lock_path_pattern": "exchange/locks/test.lock", "stale_lock_threshold_seconds": 3600})
    _write(request, {
        "lock_path": "exchange/locks/test.lock",
        "stale_threshold_seconds": 3600,
        "simulate_duplicate": True,
    })

    result = run_check(policy, request, output)
    assert result["status"] == "PASS"
    assert result["acquire_simulation"]["duplicate_detected"] is True


def test_lock_exists_is_detected(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"

    lock = tmp_path / "exchange/locks/test.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("99999", encoding="utf-8")

    _write(policy, {"lock_path_pattern": "exchange/locks/test.lock", "stale_lock_threshold_seconds": 3600})
    _write(request, {
        "lock_path": str(lock),
        "stale_threshold_seconds": 3600,
        "simulate_duplicate": False,
    })

    result = run_check(policy, request, output)
    assert result["status"] == "PASS"
    assert result["lock_state"]["lock_exists"] is True
    assert result["acquire_simulation"]["acquire_result"] == "BLOCKED"
