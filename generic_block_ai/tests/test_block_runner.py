import json
from pathlib import Path

from generic_block_ai.app.block_runner import GenericBlockRunner


def test_block_runner_routes_needs_review_to_human_review() -> None:
    runner = GenericBlockRunner(
        Path("generic_block_ai/block_manifest.json"),
        Path("generic_block_ai/config/policy.json"),
    )

    result = runner.run(
        requested_actions=[
            {"type": "collect_data", "target": "source_a"},
            {"type": "propose_deployment_plan", "target": "ops"},
        ],
        persist_human_review_artifacts=False,
    )

    assert result["status"] == "success"
    assert result["decision"] == "human_review"
    assert len(result["actions"]) == 1
    assert len(result["needs_review_actions"]) == 1
    assert result["needs_review_actions"][0]["type"] == "propose_deployment_plan"
    assert any(rc["classification"] == "needs_review" for rc in result["reason_codes"])
    assert result["review_required_fields"] == ["type", "target", "justification"]
    assert "quality_metrics" in result
    assert result["quality_metrics"]["details"]["proposal_validation_result"] == "NOT_RUN"
    assert "review_decision" in result
    assert result["review_decision"]["recommended_decision"] in {
        "RECOMMEND_APPROVE_DRY_RUN_ONLY",
        "RECOMMEND_REJECT",
        "REQUIRE_HUMAN_REVIEW",
        "BLOCKED_BY_POLICY",
    }
    assert result["review_decision"]["safeguards"]["actual_auto_approve"] is False
    assert "policy_versioning" in result
    assert len(result["policy_versioning"]["policy_hash"]) == 64
    assert result["policy_versioning"]["history_path"] is None
    assert result["policy_versioning"]["external_write_executed"] is False
    assert "signoff_audit" in result
    assert result["signoff_audit"]["path"] is None
    assert result["signoff_audit"]["external_write_executed"] is False
    assert result["signoff_audit"]["record"]["signoff"]["actor"] == "generic_block_ai"
    assert (
        result["signoff_audit"]["record"]["decision_context"]["policy"]["policy_hash"]
        == result["policy_versioning"]["policy_hash"]
    )


def test_block_runner_blocked_action_keeps_human_review() -> None:
    runner = GenericBlockRunner(
        Path("generic_block_ai/block_manifest.json"),
        Path("generic_block_ai/config/policy.json"),
    )

    result = runner.run(
        requested_actions=[{"type": "delete_block", "target": "generic_block"}],
        persist_human_review_artifacts=False,
    )

    assert result["status"] == "blocked"
    assert result["decision"] == "human_review"
    assert result["review_decision"]["recommended_decision"] == "BLOCKED_BY_POLICY"


def test_block_runner_configuration_error_contains_review_context(tmp_path: Path) -> None:
    manifest = json.loads(Path("generic_block_ai/block_manifest.json").read_text(encoding="utf-8"))
    manifest["operation_mode"] = "ACTIVE"

    local_manifest = tmp_path / "block_manifest.json"
    local_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    runner = GenericBlockRunner(local_manifest, Path("generic_block_ai/config/policy.json"))
    result = runner.run(requested_actions=[], persist_human_review_artifacts=False)

    assert result["status"] == "error"
    assert result["decision"] == "human_review"
    assert result["reason_codes"][0]["reason"] == "configuration_rejected"
    assert result["review_required_fields"] == ["manifest", "policy"]


def test_block_runner_writes_human_review_artifacts_when_enabled(tmp_path: Path) -> None:
    source_manifest = Path("generic_block_ai/block_manifest.json")
    local_manifest = tmp_path / "block_manifest.json"
    local_manifest.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    runner = GenericBlockRunner(local_manifest, Path("generic_block_ai/config/policy.json"))
    result = runner.run(
        requested_actions=[
            {"type": "collect_data", "target": "source_a"},
            {"type": "propose_deployment_plan", "target": "ops"},
        ],
        source_task_id="IR1-T4-001",
        persist_human_review_artifacts=True,
    )

    assert result["decision"] == "human_review"
    assert "review_artifacts" in result
    review_queue_path = Path(result["review_artifacts"]["review_queue_path"])
    evidence_path = Path(result["review_artifacts"]["evidence_path"])
    assert review_queue_path.exists()
    assert evidence_path.exists()
    assert result["review_artifacts"]["external_write_executed"] is False
    assert "quality_metrics" in result
    assert result["quality_metrics"]["details"]["proposal_validation_result"] == "PASS"
    assert result["quality_metrics"]["review_readiness"] in {"ready", "needs_attention", "not_ready"}
    assert "review_decision" in result
    assert result["review_decision"]["safeguards"]["actual_auto_execute"] is False
    assert result["review_decision"]["safeguards"]["production_release"] is False
    assert "policy_versioning" in result
    assert Path(result["policy_versioning"]["history_path"]).exists()
    assert result["policy_versioning"]["external_write_executed"] is False
    assert "signoff_audit" in result
    assert Path(result["signoff_audit"]["path"]).exists()
    assert result["signoff_audit"]["external_write_executed"] is False
    assert result["signoff_audit"]["record"]["signoff"]["actor"] == "generic_block_ai"
    assert result["signoff_audit"]["record"]["signoff"]["recommended_decision"] in {
        "RECOMMEND_APPROVE_DRY_RUN_ONLY",
        "RECOMMEND_REJECT",
        "REQUIRE_HUMAN_REVIEW",
        "BLOCKED_BY_POLICY",
    }


def test_block_runner_does_not_write_human_review_artifacts_when_disabled(tmp_path: Path) -> None:
    source_manifest = Path("generic_block_ai/block_manifest.json")
    local_manifest = tmp_path / "block_manifest.json"
    local_manifest.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    runner = GenericBlockRunner(local_manifest, Path("generic_block_ai/config/policy.json"))
    result = runner.run(
        requested_actions=[
            {"type": "collect_data", "target": "source_a"},
            {"type": "propose_deployment_plan", "target": "ops"},
        ],
        source_task_id="IR1-T4-002",
        persist_human_review_artifacts=False,
    )

    assert result["decision"] == "human_review"
    assert "review_artifacts" not in result


def test_block_runner_applies_quality_metrics_thresholds_from_policy(tmp_path: Path) -> None:
    source_manifest = Path("generic_block_ai/block_manifest.json")
    local_manifest = tmp_path / "block_manifest.json"
    local_manifest.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    source_policy = json.loads(Path("generic_block_ai/config/policy.json").read_text(encoding="utf-8"))
    source_policy["quality_metrics"]["readiness_min_quality_score"] = 95
    source_policy["quality_metrics"]["readiness_min_risk_balance"] = 95
    local_policy = tmp_path / "policy.json"
    local_policy.write_text(json.dumps(source_policy, ensure_ascii=False, indent=2), encoding="utf-8")

    runner = GenericBlockRunner(local_manifest, local_policy)
    result = runner.run(
        requested_actions=[
            {"type": "collect_data", "target": "source_a"},
            {"type": "propose_deployment_plan", "target": "ops"},
        ],
        source_task_id="IR2-T5-001",
        persist_human_review_artifacts=True,
    )

    assert result["decision"] == "human_review"
    assert result["quality_metrics"]["review_readiness"] == "needs_attention"
    assert result["quality_metrics"]["details"]["policy"]["readiness_min_quality_score"] == 95
    assert result["quality_metrics"]["details"]["policy"]["readiness_min_risk_balance"] == 95