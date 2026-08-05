import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n6_continuous_monitoring_dry_run import run_simulation


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_with_low_fail_rate(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write(policy, {
        "simulated_duration_hours": 24,
        "check_interval_minutes": 60,
        "expected_check_count": 24,
        "acceptable_fail_rate_percent": 5,
        "check_targets": ["dns", "https"],
    })
    _write(request, {"simulated_duration_hours": 24, "check_interval_minutes": 60, "seed": 42})

    result = run_simulation(policy, request, output)
    assert result["status"] == "PASS"
    assert result["actual_check_count"] == 24
    assert result["actual_long_run_executed"] is False
    assert output.exists()


def test_safety_flags(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write(policy, {
        "simulated_duration_hours": 2,
        "check_interval_minutes": 60,
        "expected_check_count": 2,
        "acceptable_fail_rate_percent": 50,
        "check_targets": ["dns"],
    })
    _write(request, {"simulated_duration_hours": 2, "check_interval_minutes": 60, "seed": 0})

    result = run_simulation(policy, request, output)
    assert result["production_status"] == "NO_GO"
    assert result["wordpress_write_executed"] is False
    assert result["external_state_change"] is False
