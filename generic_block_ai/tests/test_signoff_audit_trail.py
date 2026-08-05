import json
from pathlib import Path

from generic_block_ai.app.signoff_audit_trail import build_signoff_audit_record, write_signoff_audit_log


def _sample_result() -> dict:
    return {
        "status": "success",
        "decision": "human_review",
        "review_decision": {
            "recommended_decision": "RECOMMEND_APPROVE_DRY_RUN_ONLY",
            "reason": "review_readiness=ready",
        },
        "quality_metrics": {
            "quality_score": 72,
            "risk_balance": 61,
            "review_readiness": "ready",
        },
        "policy_versioning": {
            "version": "v1.0.0",
            "environment": "dev",
            "policy_hash": "a" * 64,
        },
    }


def test_build_signoff_audit_record_contains_identity_and_decision() -> None:
    record = build_signoff_audit_record(
        block_result=_sample_result(),
        source_task_id="IR3-T3-001",
        signoff_actor="reviewer_alpha",
    )

    assert record["signoff"]["actor"] == "reviewer_alpha"
    assert record["signoff"]["recommended_decision"] == "RECOMMEND_APPROVE_DRY_RUN_ONLY"
    assert record["decision_context"]["policy"]["policy_hash"] == "a" * 64
    assert record["safeguards"]["external_write_executed"] is False


def test_write_signoff_audit_log_creates_local_json(tmp_path: Path) -> None:
    output = write_signoff_audit_log(
        base_path=tmp_path,
        block_result=_sample_result(),
        source_task_id="IR3-T3-002",
        signoff_actor="reviewer_beta",
    )
    path = Path(output["path"])
    assert path.exists()

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["signoff"]["actor"] == "reviewer_beta"
    assert loaded["decision_context"]["quality_metrics"]["review_readiness"] == "ready"
    assert output["external_write_executed"] is False