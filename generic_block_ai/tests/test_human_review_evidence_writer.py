from pathlib import Path

from generic_block_ai.app.evidence_index_validator import validate_evidence_index
from generic_block_ai.app.human_review_evidence_writer import write_human_review_artifacts
from generic_block_ai.app.review_queue_validator import validate_review_queue


def _sample_result() -> dict:
    return {
        "decision": "human_review",
        "summary": "planned=2, allowed=1, blocked=0, needs_review=1",
        "actions": [{"type": "collect_data", "target": "source_a"}],
        "blocked_actions": [],
        "needs_review_actions": [{"type": "propose_deployment_plan", "target": "ops"}],
        "reason_codes": [
            {
                "action_type": "propose_deployment_plan",
                "classification": "needs_review",
                "reason": "unknown_action_type",
            }
        ],
        "review_required_fields": ["type", "target", "justification"],
        "meta": {"block_id": "generic_block", "version": "0.1.0"},
    }


def test_writer_creates_local_artifacts_with_required_fields(tmp_path: Path) -> None:
    output = write_human_review_artifacts(
        base_path=tmp_path,
        block_result=_sample_result(),
        source_task_id="IR1-T3-001",
    )

    queue_path = Path(output["review_queue_path"])
    evidence_path = Path(output["evidence_path"])

    assert queue_path.exists()
    assert evidence_path.exists()
    assert output["external_write_executed"] is False

    review_payload = output["review_queue"]["queue_entries"][0]["review_payload"]
    assert review_payload["decision"] == "human_review"
    assert "needs_review_actions" in review_payload
    assert "blocked_actions" in review_payload
    assert "reason_codes" in review_payload
    assert review_payload["production_status"] == "NO_GO"
    assert review_payload["external_write_executed"] is False


def test_writer_output_passes_review_and_evidence_validators(tmp_path: Path) -> None:
    output = write_human_review_artifacts(
        base_path=tmp_path,
        block_result=_sample_result(),
        source_task_id="IR1-T3-VAL",
    )

    review_result = validate_review_queue(output["review_queue"])
    evidence_result = validate_evidence_index(output["evidence_index"])

    assert review_result.result == "PASS"
    assert evidence_result.result == "PASS"