import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_phase8_credential_ready_route_no_execution import (
    EXPECTED_OVERALL_STATUS,
    run_route,
)


def test_run_route_success_with_mocked_commands(tmp_path, monkeypatch):
    output = tmp_path / "exchange/logs/result.json"
    overall = tmp_path / "exchange/logs/phase8_36_to_8_40_trial_route_overall_report.json"
    overall.parent.mkdir(parents=True, exist_ok=True)
    overall.write_text(
        json.dumps({"overall_status": EXPECTED_OVERALL_STATUS}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    from scripts import run_phase8_credential_ready_route_no_execution as mod

    monkeypatch.setattr(mod, "OVERALL_REPORT_JSON", overall)
    monkeypatch.setattr(
        mod,
        "_run_command",
        lambda script: {"script": script, "returncode": 0, "stdout_tail": "", "stderr_tail": ""},
    )

    result = run_route(commands=[["scripts/a.py"], ["scripts/b.py"]], output_json_path=output)

    assert result["status"] == "SVC2_VALIDATOR_ROUTE_PASS_READY_REACHED_NO_EXECUTION"
    assert result["scripts_failed"] == 0
    assert result["ready_reached"] is True
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"
    assert output.exists()


def test_run_route_fail_on_script_error(tmp_path, monkeypatch):
    output = tmp_path / "exchange/logs/result.json"

    from scripts import run_phase8_credential_ready_route_no_execution as mod

    calls = {"n": 0}

    def _fake_run(script: str):
        calls["n"] += 1
        return {
            "script": script,
            "returncode": 1 if calls["n"] == 2 else 0,
            "stdout_tail": "",
            "stderr_tail": "err" if calls["n"] == 2 else "",
        }

    monkeypatch.setattr(mod, "_run_command", _fake_run)
    monkeypatch.setattr(mod, "_read_overall_status", lambda: "SOMETHING_ELSE")

    result = run_route(commands=[["scripts/a.py"], ["scripts/b.py"]], output_json_path=output)

    assert result["status"] == "SVC2_VALIDATOR_ROUTE_FAIL_SCRIPT_ERROR_NO_EXECUTION"
    assert result["scripts_failed"] == 1
    assert result["wordpress_write_executed"] is False
    assert result["systemctl_restart_executed"] is False


def test_default_commands_are_validator_report_only():
    from scripts import run_phase8_credential_ready_route_no_execution as mod

    for item in mod.DEFAULT_COMMANDS:
        script = item[0]
        assert script.startswith("scripts/")
        assert script.endswith(".py")
        # allow only generate/validate/run_phase8_39 simulation in this route
        assert (
            "/generate_" in f"/{script}" or
            "/validate_" in f"/{script}" or
            script == "scripts/run_phase8_39_abort_rollback_freeze_simulation.py"
        )
        assert "wordpress_draft_create" not in script
        assert "publish" not in script or "preflight_before_single_controlled_draft_creation" in script
