import json
from pathlib import Path

from generic_block_ai.app.block_runner import GenericBlockRunner
from generic_block_ai.app.proposal_validator import validate_proposal
from generic_block_ai.app.review_package_builder import build_review_package, write_review_package


def _sample_block_result() -> dict:
    return {
        "summary": "planned=2, allowed=1, blocked=0, needs_review=1, candidates=2, filtered=1, rejected=1",
        "task_candidates": [
            {
                "candidate_id": "candidate_1",
                "action_type": "collect_data",
                "classification": "allow",
                "impact_score": 55,
                "risk_score": 25,
                "confidence_score": 85,
                "priority_score": 65,
                "action": {"type": "collect_data", "target": "source_a"},
            }
        ],
        "rejected_task_candidates": [
            {
                "candidate_id": "candidate_2",
                "action_type": "delete_block",
                "classification": "block",
                "impact_score": 45,
                "risk_score": 90,
                "confidence_score": 20,
                "priority_score": 20,
                "action": {"type": "delete_block", "target": "generic_block"},
                "rejection_reasons": [
                    {"code": "forbidden_action", "message": "action type is forbidden: delete_block"}
                ],
            }
        ],
        "reason_codes": [{"action_type": "collect_data", "classification": "allow", "reason": "capability_enabled"}],
        "review_required_fields": ["type", "target", "justification"],
        "meta": {"block_id": "generic_block", "version": "0.1.0"},
    }


def test_build_review_package_contains_required_review_fields() -> None:
    package = build_review_package(_sample_block_result(), source_task_id="IR2-T3-001")

    assert "review_package" in package
    rp = package["review_package"]
    assert "scope" in rp
    assert "non_goals" in rp
    assert "risk_assessment" in rp
    assert "guardrail_checks" in rp
    assert "rollback_conditions" in rp
    assert rp["approval_required"] is True

    result = validate_proposal(package)
    assert result.result == "PASS"


def test_write_review_package_creates_local_json(tmp_path: Path) -> None:
    output = write_review_package(
        base_path=tmp_path,
        block_result=_sample_block_result(),
        source_task_id="IR2-T3-002",
    )

    path = Path(output["path"])
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["proposal"]["mode"] == "dry_run"
    assert loaded["proposal"]["operation_mode"] == "OBSERVE"


def test_block_runner_includes_review_package_when_human_review(tmp_path: Path) -> None:
    source_manifest = Path("generic_block_ai/block_manifest.json")
    local_manifest = tmp_path / "block_manifest.json"
    local_manifest.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    runner = GenericBlockRunner(local_manifest, Path("generic_block_ai/config/policy.json"))
    result = runner.run(
        requested_actions=[
            {"type": "collect_data", "target": "source_a"},
            {"type": "propose_deployment_plan", "target": "ops"},
        ],
        source_task_id="IR2-T3-003",
        persist_human_review_artifacts=True,
    )

    assert result["decision"] == "human_review"
    assert "review_package" in result
    assert result["review_package"]["validation_result"] == "PASS"
    assert Path(result["review_package"]["path"]).exists()