"""
test_validators.py  –  Phase 3.5-14〜16

proposal / review_queue / evidence_index の各 validator を検証します。
外部通信・実行・export は一切行いません。
"""

import pytest
from generic_block_ai.app.proposal_validator import validate_proposal
from generic_block_ai.app.review_queue_validator import validate_review_queue
from generic_block_ai.app.evidence_index_validator import validate_evidence_index


# ---------------------------------------------------------------------------
# 共通ヘルパー
# ---------------------------------------------------------------------------

def _valid_proposal() -> dict:
    return {
        "proposal": {
            "block_id": "generic_block",
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "estimated_impact": {
                "reversible": True,
                "requires_human_approval": True,
                "auto_execute_allowed": False,
            },
        },
        "safety_constraints": {
            "publish_content": False,
            "delete_data": False,
            "change_config": False,
            "observe_only": True,
            "forbidden_actions_checked": True,
        },
        "review_requirements": {"requires_human_approval": True},
        "status": {"state": "pending_review", "reviewer_decision": None},
    }


def _valid_queue() -> dict:
    return {
        "queue_metadata": {
            "block_id": "generic_block",
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "auto_process_allowed": False,
            "requires_human_approval": True,
        },
        "queue_policy": {
            "auto_approve": False,
            "escalation_enabled": False,
            "forbidden_auto_actions": [
                "auto_dequeue",
                "auto_execute",
                "auto_publish",
                "batch_approve_without_review",
            ],
        },
    }


def _valid_evidence_index() -> dict:
    return {
        "index_metadata": {
            "block_id": "generic_block",
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "auto_export_allowed": False,
            "requires_human_approval": True,
        },
        "export_policy": {
            "auto_export": False,
            "allowed_destinations": [],
            "forbidden_actions": [
                "auto_upload_to_external",
                "overwrite_existing_evidence",
                "delete_evidence",
                "export_without_approval",
            ],
        },
        "entries": [],
    }


# ---------------------------------------------------------------------------
# Phase 3.5-14: proposal validator
# ---------------------------------------------------------------------------

class TestProposalValidator:
    def test_valid_proposal_passes(self):
        r = validate_proposal(_valid_proposal())
        assert r.result == "PASS"

    def test_non_dry_run_mode_fails(self):
        data = _valid_proposal()
        data["proposal"]["mode"] = "live"
        r = validate_proposal(data)
        assert r.result == "FAIL"
        assert any("mode" in e for e in r.failed_checks)

    def test_non_observe_operation_mode_fails(self):
        data = _valid_proposal()
        data["proposal"]["operation_mode"] = "EXECUTE"
        r = validate_proposal(data)
        assert r.result == "FAIL"
        assert any("operation_mode" in e for e in r.failed_checks)

    def test_auto_execute_true_fails(self):
        data = _valid_proposal()
        data["proposal"]["estimated_impact"]["auto_execute_allowed"] = True
        r = validate_proposal(data)
        assert r.result == "FAIL"

    def test_requires_human_approval_false_fails(self):
        data = _valid_proposal()
        data["review_requirements"]["requires_human_approval"] = False
        r = validate_proposal(data)
        assert r.result == "FAIL"

    def test_publish_content_true_fails(self):
        data = _valid_proposal()
        data["safety_constraints"]["publish_content"] = True
        r = validate_proposal(data)
        assert r.result == "FAIL"

    def test_observe_only_false_fails(self):
        data = _valid_proposal()
        data["safety_constraints"]["observe_only"] = False
        r = validate_proposal(data)
        assert r.result == "FAIL"

    def test_auto_approved_decision_fails(self):
        data = _valid_proposal()
        data["status"]["reviewer_decision"] = "auto_approved"
        r = validate_proposal(data)
        assert r.result == "FAIL"


# ---------------------------------------------------------------------------
# Phase 3.5-15: review queue validator
# ---------------------------------------------------------------------------

class TestReviewQueueValidator:
    def test_valid_queue_passes(self):
        r = validate_review_queue(_valid_queue())
        assert r.result == "PASS"

    def test_non_dry_run_mode_fails(self):
        data = _valid_queue()
        data["queue_metadata"]["mode"] = "production"
        r = validate_review_queue(data)
        assert r.result == "FAIL"

    def test_non_observe_operation_mode_fails(self):
        data = _valid_queue()
        data["queue_metadata"]["operation_mode"] = "WRITE"
        r = validate_review_queue(data)
        assert r.result == "FAIL"

    def test_auto_process_true_fails(self):
        data = _valid_queue()
        data["queue_metadata"]["auto_process_allowed"] = True
        r = validate_review_queue(data)
        assert r.result == "FAIL"

    def test_auto_approve_true_fails(self):
        data = _valid_queue()
        data["queue_policy"]["auto_approve"] = True
        r = validate_review_queue(data)
        assert r.result == "FAIL"

    def test_missing_forbidden_action_warns(self):
        data = _valid_queue()
        data["queue_policy"]["forbidden_auto_actions"] = ["auto_dequeue"]
        r = validate_review_queue(data)
        assert r.result == "WARN"
        assert any("missing" in w for w in r.warnings)

    def test_escalation_enabled_warns(self):
        data = _valid_queue()
        data["queue_policy"]["escalation_enabled"] = True
        r = validate_review_queue(data)
        assert r.result == "WARN"


# ---------------------------------------------------------------------------
# Phase 3.5-16: evidence index validator
# ---------------------------------------------------------------------------

class TestEvidenceIndexValidator:
    def test_valid_index_passes(self):
        r = validate_evidence_index(_valid_evidence_index())
        assert r.result == "PASS"

    def test_non_dry_run_mode_fails(self):
        data = _valid_evidence_index()
        data["index_metadata"]["mode"] = "execute"
        r = validate_evidence_index(data)
        assert r.result == "FAIL"

    def test_auto_export_true_fails(self):
        data = _valid_evidence_index()
        data["index_metadata"]["auto_export_allowed"] = True
        r = validate_evidence_index(data)
        assert r.result == "FAIL"

    def test_auto_export_policy_true_fails(self):
        data = _valid_evidence_index()
        data["export_policy"]["auto_export"] = True
        r = validate_evidence_index(data)
        assert r.result == "FAIL"

    def test_deleted_entry_status_fails(self):
        data = _valid_evidence_index()
        data["entries"] = [{"evidence_id": "e1", "status": "deleted"}]
        r = validate_evidence_index(data)
        assert r.result == "FAIL"
        assert any("deleted" in e for e in r.failed_checks)

    def test_overwritten_entry_status_fails(self):
        data = _valid_evidence_index()
        data["entries"] = [{"evidence_id": "e2", "status": "overwritten"}]
        r = validate_evidence_index(data)
        assert r.result == "FAIL"

    def test_non_empty_destinations_warns(self):
        data = _valid_evidence_index()
        data["export_policy"]["allowed_destinations"] = ["s3://bucket"]
        r = validate_evidence_index(data)
        assert r.result == "WARN"

    def test_missing_forbidden_actions_warns(self):
        data = _valid_evidence_index()
        data["export_policy"]["forbidden_actions"] = []
        r = validate_evidence_index(data)
        assert r.result == "WARN"
