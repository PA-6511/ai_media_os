import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n5_recovery_simulation import run_simulation


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_when_all_scenarios_have_template(tmp_path: Path):
    policy = tmp_path / "config/policy.json"
    request = tmp_path / "exchange/examples/request.json"
    output = tmp_path / "exchange/logs/result.json"

    _write_json(
        policy,
        {
            "scenario_templates": {
                "nginx_down": {
                    "expected_action": "a",
                    "recommended_action": "b",
                    "recovery_steps": ["c"],
                }
            }
        },
    )
    _write_json(request, {"scenarios": ["nginx_down"]})

    result = run_simulation(policy, request, output)
    assert result["status"] == "PASS"
    assert result["scenario_count"] == 1


def test_fail_when_scenario_template_missing(tmp_path: Path):
    policy = tmp_path / "config/policy.json"
    request = tmp_path / "exchange/examples/request.json"
    output = tmp_path / "exchange/logs/result.json"

    _write_json(policy, {"scenario_templates": {}})
    _write_json(request, {"scenarios": ["unknown"]})

    result = run_simulation(policy, request, output)
    assert result["status"] == "FAIL"
