import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n9_post_reboot_recovery_simulation import run_simulation


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_all_scenarios(tmp_path: Path):
    policy = tmp_path / "config/policy.json"
    request = tmp_path / "exchange/examples/request.json"
    output = tmp_path / "exchange/logs/result.json"

    _write(policy, {
        "scenario_templates": {
            "service_check_after_reboot": {
                "expected_action": "verify_all_services_alive",
                "recommended_action": "run_health_probe_on_each_service",
                "recovery_steps": ["check nginx", "check wp-api"],
            }
        }
    })
    _write(request, {"scenarios": ["service_check_after_reboot"]})

    result = run_simulation(policy, request, output)
    assert result["status"] == "PASS"
    assert result["system_restart_executed"] is False
    assert result["reboot_executed"] is False
    assert result["shutdown_executed"] is False
    assert output.exists()


def test_fail_unknown_scenario(tmp_path: Path):
    policy = tmp_path / "config/policy.json"
    request = tmp_path / "exchange/examples/request.json"
    output = tmp_path / "exchange/logs/result.json"

    _write(policy, {"scenario_templates": {}})
    _write(request, {"scenarios": ["unknown_scenario"]})

    result = run_simulation(policy, request, output)
    assert result["status"] == "FAIL"
