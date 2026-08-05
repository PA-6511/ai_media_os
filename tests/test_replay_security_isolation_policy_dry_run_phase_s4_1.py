from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.replay_security_isolation_policy_dry_run_phase_s4_1 import (  # noqa: E402
    replay_security_isolation_policy_dry_run_phase_s4_1,
)


CONFIG_PATH = ROOT / "config" / "security_isolation_policy_dry_run_validation_phase_s4_1.json"
BATCH_PATH = ROOT / "exchange" / "examples" / "security_isolation_policy_phase_s4_1_request_batch.example.json"
S4_OVERALL_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_normal_replay_pass(tmp_path: Path) -> None:
    result = replay_security_isolation_policy_dry_run_phase_s4_1(
        config_path=CONFIG_PATH,
        batch_path=BATCH_PATH,
        s4_overall_path=S4_OVERALL_PATH,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "PASS"
    assert result["phase_status"] == "DESIGN_ONLY"
    assert result["execution"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["isolation_recommendation_only"] is True
    assert result["isolation_execution_allowed"] is False
    assert result["isolation_executed"] is False
    assert result["executor_action_allowed"] is False
    assert result["request_count"] == 7
    assert result["matched_expected_count"] == 7
    assert result["mismatched_expected_count"] == 0
    assert result["isolation_recommendation_detected"] is True
    assert result["human_review_recommendation_detected"] is True
    assert result["s4_design_verified"] is True
    actuals = {row["request_id"]: row["actual_decision"] for row in result["request_results"]}
    assert actuals["unknown_block_connects_to_generic"] == "RECOMMEND_ISOLATION"
    assert actuals["restricted_to_production_core"] == "BLOCK_ROUTE"
    assert actuals["experimental_to_production_core"] == "BLOCK_ROUTE"
    assert actuals["ebook_wordpress_write"] == "DENY_CAPABILITY"
    assert actuals["self_builder_code_modify"] == "DENY_CAPABILITY"
    assert actuals["core_external_action_request"] == "DENY_CAPABILITY"
    assert actuals["core_proposal_to_generic"] == "ALLOW_PROPOSAL"


def test_batch_isolation_executed_abort(tmp_path: Path) -> None:
    batch = _load_json(BATCH_PATH)
    batch["actions"]["isolation_executed"] = True
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_isolation_policy_dry_run_phase_s4_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        s4_overall_path=S4_OVERALL_PATH,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "ABORT"


def test_expected_mismatch_fail(tmp_path: Path) -> None:
    batch = _load_json(BATCH_PATH)
    batch["requests"][0]["expected_decision"] = "ALLOW_PROPOSAL"
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_isolation_policy_dry_run_phase_s4_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        s4_overall_path=S4_OVERALL_PATH,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "FAIL"


def test_s4_overall_not_pass_design_only_fail(tmp_path: Path) -> None:
    s4_overall = _load_json(S4_OVERALL_PATH)
    s4_overall["final_status"] = "ISOLATION_DESIGN_REVIEW_REQUIRED"
    s4_overall_path = tmp_path / "s4.json"
    s4_overall_path.write_text(json.dumps(s4_overall, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_isolation_policy_dry_run_phase_s4_1(
        config_path=CONFIG_PATH,
        batch_path=BATCH_PATH,
        s4_overall_path=s4_overall_path,
        output_json_path=tmp_path / "result.json",
        output_md_path=tmp_path / "result.md",
    )
    assert result["replay_result"] == "FAIL"
