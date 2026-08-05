from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.replay_security_isolation_event_simulation_phase_s4_2 import (  # noqa: E402
    replay_security_isolation_event_simulation_phase_s4_2,
)


CONFIG_PATH = ROOT / "config" / "security_isolation_event_simulation_phase_s4_2.json"
S4_1_OVERALL_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_normal_replay_pass(tmp_path: Path) -> None:
    result = replay_security_isolation_event_simulation_phase_s4_2(
        config_path=CONFIG_PATH,
        s4_1_overall_path=S4_1_OVERALL_PATH,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "PASS"
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["simulation_status"] == "SIMULATION_ONLY"
    assert result["recommendation_mode"] == "RECOMMENDATION_ONLY"
    assert result["isolation_execution_policy"] == "NO_ISOLATION_EXECUTION"
    assert result["scenario_count"] == 7
    assert result["matched_expected_count"] == 7
    assert result["mismatched_expected_count"] == 0
    assert result["simulation_only"] is True
    assert result["recommendation_only"] is True
    assert result["isolation_recommendation_detected"] is True
    assert result["freeze_recommendation_detected"] is True
    assert result["human_review_recommendation_detected"] is True
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["network_policy_applied"] is False
    assert result["container_stop_executed"] is False
    assert result["process_kill_executed"] is False
    assert result["firewall_applied"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["state_change_executed"] is False

    actuals = {row["scenario_id"]: row["actual_decision"] for row in result["scenario_results"]}
    assert actuals["S4_2_SCENARIO_1"] == "BLOCK_ROUTE"
    assert actuals["S4_2_SCENARIO_2"] == "BLOCK_ROUTE"
    assert actuals["S4_2_SCENARIO_3"] == "DENY_CAPABILITY"
    assert actuals["S4_2_SCENARIO_4"] == "DENY_CAPABILITY"
    assert actuals["S4_2_SCENARIO_5"] == "DENY_CAPABILITY"
    assert actuals["S4_2_SCENARIO_6"] == "FREEZE_RECOMMEND"
    assert actuals["S4_2_SCENARIO_7"] == "FREEZE_RECOMMEND"


def test_execution_flag_enabled_abort(tmp_path: Path) -> None:
    config = _load_json(CONFIG_PATH)
    config["actions"]["network_policy_apply"] = True
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    result = replay_security_isolation_event_simulation_phase_s4_2(
        config_path=config_path,
        s4_1_overall_path=S4_1_OVERALL_PATH,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "ABORT"


def test_expected_mismatch_fail(tmp_path: Path) -> None:
    config = _load_json(CONFIG_PATH)
    config["simulation_scenarios"][0]["expected"]["decision"] = "DENY_CAPABILITY"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    result = replay_security_isolation_event_simulation_phase_s4_2(
        config_path=config_path,
        s4_1_overall_path=S4_1_OVERALL_PATH,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "FAIL"


def test_s4_1_not_pass_dry_run_only_fail(tmp_path: Path) -> None:
    s4_1_overall = _load_json(S4_1_OVERALL_PATH)
    s4_1_overall["final_status"] = "ISOLATION_POLICY_REVIEW_REQUIRED"
    s4_1_overall_path = tmp_path / "s4_1_overall.json"
    s4_1_overall_path.write_text(json.dumps(s4_1_overall, ensure_ascii=False, indent=2), encoding="utf-8")

    result = replay_security_isolation_event_simulation_phase_s4_2(
        config_path=CONFIG_PATH,
        s4_1_overall_path=s4_1_overall_path,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "FAIL"
