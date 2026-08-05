from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_phase_s4_1_overall_result import (  # noqa: E402
    generate_security_phase_s4_1_overall_result,
)
from scripts.replay_security_isolation_policy_dry_run_phase_s4_1 import (  # noqa: E402
    replay_security_isolation_policy_dry_run_phase_s4_1,
)


def _build_replay(tmp_path: Path, replay_result: str, mismatched: int = 0) -> Path:
    result = replay_security_isolation_policy_dry_run_phase_s4_1(
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    result["replay_result"] = replay_result
    result["mismatched_expected_count"] = mismatched
    (tmp_path / "replay.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp_path / "replay.json"


def test_overall_pass_dry_run_only(tmp_path: Path) -> None:
    replay_path = _build_replay(tmp_path, "PASS", 0)
    result = generate_security_phase_s4_1_overall_result(
        replay_result_path=replay_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["isolation_recommendation_only"] is True
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["executor_action_allowed"] is False
    assert result["network_policy_applied"] is False
    assert result["container_stop_executed"] is False
    assert result["process_kill_executed"] is False
    assert result["firewall_applied"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["state_change_executed"] is False


def test_overall_review_required_on_mismatch(tmp_path: Path) -> None:
    replay_path = _build_replay(tmp_path, "FAIL", 1)
    result = generate_security_phase_s4_1_overall_result(
        replay_result_path=replay_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ISOLATION_POLICY_REVIEW_REQUIRED"


def test_overall_abort(tmp_path: Path) -> None:
    replay_path = _build_replay(tmp_path, "ABORT", 0)
    result = generate_security_phase_s4_1_overall_result(
        replay_result_path=replay_path,
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "ABORT"
