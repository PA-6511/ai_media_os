from pathlib import Path

from generic_block_ai.app.block_contract import BlockManifest
from generic_block_ai.app.safety_guard import load_policy
from generic_block_ai.app.task_constraint_filter import filter_task_candidates


def _manifest_and_policy() -> tuple[BlockManifest, dict]:
    manifest = BlockManifest.from_json_file(Path("generic_block_ai/block_manifest.json"))
    policy = load_policy(Path("generic_block_ai/config/policy.json"))
    return manifest, policy


def test_constraint_filter_rejects_missing_target() -> None:
    manifest, policy = _manifest_and_policy()
    candidates = [
        {
            "candidate_id": "candidate_1",
            "action_type": "collect_data",
            "classification": "allow",
            "impact_score": 55,
            "risk_score": 25,
            "confidence_score": 85,
            "priority_score": 65,
            "action": {"type": "collect_data"},
        }
    ]

    accepted, rejected = filter_task_candidates(candidates, manifest=manifest, policy=policy)
    assert accepted == []
    assert len(rejected) == 1
    assert any(reason["code"] == "missing_mandatory_context" for reason in rejected[0]["rejection_reasons"])


def test_constraint_filter_rejects_high_risk_low_priority() -> None:
    manifest, policy = _manifest_and_policy()
    candidates = [
        {
            "candidate_id": "candidate_1",
            "action_type": "delete_block",
            "classification": "block",
            "impact_score": 45,
            "risk_score": 90,
            "confidence_score": 20,
            "priority_score": 20,
            "action": {"type": "delete_block", "target": "generic_block"},
        }
    ]

    accepted, rejected = filter_task_candidates(candidates, manifest=manifest, policy=policy)
    assert accepted == []
    assert len(rejected) == 1
    assert any(reason["code"] == "forbidden_action" for reason in rejected[0]["rejection_reasons"])
    assert any(reason["code"] == "high_risk_low_priority" for reason in rejected[0]["rejection_reasons"])


def test_constraint_filter_accepts_valid_candidate() -> None:
    manifest, policy = _manifest_and_policy()
    candidates = [
        {
            "candidate_id": "candidate_1",
            "action_type": "collect_data",
            "classification": "allow",
            "impact_score": 60,
            "risk_score": 25,
            "confidence_score": 85,
            "priority_score": 68,
            "action": {"type": "collect_data", "target": "source_a"},
        }
    ]

    accepted, rejected = filter_task_candidates(candidates, manifest=manifest, policy=policy)
    assert len(accepted) == 1
    assert rejected == []