import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_phase8_39_abort_rollback_freeze_simulation import run_simulation


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


ALL_SCENARIOS = [
    "credential_missing", "wordpress_auth_failed", "wordpress_timeout",
    "wordpress_5xx", "duplicate_item_detected", "missing_affiliate_disclosure",
    "pr_label_missing", "cta_policy_failed", "one_shot_lock_exists",
    "unexpected_api_write_attempt", "secret_output_detected",
    "post_creation_uncertain", "evidence_generation_failed",
]


def _make_policy(tmp: Path) -> Path:
    p = tmp / "config/policy.json"
    _write(p, {"simulation_scenarios": ALL_SCENARIOS})
    return p


def _make_request(tmp: Path, scenarios=None) -> Path:
    r = tmp / "exchange/examples/req.json"
    _write(r, {"mode": "CONNECTION_TEST", "execution": "DRY_RUN", "scenarios": scenarios or ALL_SCENARIOS})
    return r


def test_all_scenarios_pass(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path)
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = run_simulation(policy, request, out_r, out_j, out_m)
    assert result["status"] == "PHASE8_39_ABORT_ROLLBACK_FREEZE_SIMULATION_PASS_NO_EXECUTION"
    assert result["scenario_count"] == len(ALL_SCENARIOS)
    assert result["rollback_executed"] is False
    assert result["freeze_executed"] is False
    assert result["executed_external_changes"] == 0
    assert result["wordpress_write_executed"] is False
    assert result["slack_message_sent"] is False
    assert out_r.exists()


def test_unknown_scenario_causes_mismatch(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, scenarios=["unknown_scenario_xyz"])
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = run_simulation(policy, request, out_r, out_j, out_m)
    assert result["status"] == "ABORT_SIMULATION_EXPECTATION_MISMATCH_NO_EXECUTION"


def test_safety_flags_always_false(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, scenarios=["credential_missing"])
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = run_simulation(policy, request, out_r, out_j, out_m)
    for key in (
        "wordpress_write_executed", "wordpress_draft_created",
        "rollback_executed", "freeze_executed",
        "slack_message_sent", "system_restart_executed",
        "secret_values_output", "external_change_executed",
    ):
        assert result[key] is False, f"{key} should be False"
    assert result["executed_external_changes"] == 0


def test_each_scenario_no_external_change(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path)
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = run_simulation(policy, request, out_r, out_j, out_m)
    for sr in result["scenario_results"]:
        assert sr["external_change_executed"] is False
        assert sr["rollback_executed"] is False
        assert sr["freeze_executed"] is False
        assert sr["matched_expected"] is True
