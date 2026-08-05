from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts.validate_tst_5d_w1_workflow_state_hold_clearance_evidence import (
    ERROR_CODE,
    EvidenceIntegrityError,
    validate_evidence,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _refresh_evidence_hashes(evidence_root: Path) -> None:
    manifest_path = evidence_root / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["evidence_files"] = {
        name: _sha256(evidence_root / name)
        for name in sorted(manifest["evidence_files"])
    }
    _write_json(manifest_path, manifest)


def _build_valid_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    evidence_root = repo_root / "evidence"
    source_path = repo_root / "app/source.py"
    test_path = repo_root / "tests/test_sample.py"
    decision_path = repo_root / "exchange/decision.json"
    production_manifest_path = repo_root / "config/manifest.json"
    for path in (source_path, test_path, decision_path, production_manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("SOURCE = 'fixture'\n", encoding="utf-8")
    test_path.write_text("def test_fixture(): pass\n", encoding="utf-8")
    _write_json(
        decision_path,
        {"review_unit": "UNIT_WORKFLOW_STATE", "decision": "HOLD"},
    )
    _write_json(production_manifest_path, {"release": "production"})
    evidence_root.mkdir(parents=True)

    test_results = {
        "targeted": {
            "counts": {"passed": 1, "failed": 0, "total": 1},
            "node_results": [
                {
                    "node_id": "tests/test_sample.py::test_fixture",
                    "status": "passed",
                }
            ],
        },
        "fault_injection_repeat_results": [
            {"run": 1, "status": "passed", "process_isolated": True},
            {"run": 2, "status": "passed", "process_isolated": True},
        ],
    }
    contract = {
        "invalid_post_id_checks": {
            "zero_rejected": True,
            "negative_rejected": True,
            "bool_rejected": True,
            "empty_rejected": True,
            "whitespace_rejected": True,
            "decimal_rejected": True,
            "nonnumeric_rejected": True,
            "extreme_length_rejected": False,
            "extreme_length_gap_reported": True,
        },
        "state_protection_checks": {
            "service_preflight_protected": True,
            "direct_published_replacement_rejected": False,
            "direct_repository_gap_reported": True,
        },
    }
    failures = {
        "checks": {
            "flush_rollback_executed": True,
            "commit_rollback_executed": True,
            "reopened_session_verified": True,
            "workflow_row_unchanged_after_failure": True,
            "post_id_unchanged_after_failure": True,
            "workflow_state_unchanged_after_failure": True,
            "history_absent_after_failure": True,
            "approval_unchanged_after_failure": True,
            "no_partial_state_only_update": True,
            "no_partial_post_id_only_update": True,
            "no_partial_approval_only_update": True,
            "session_recovered": True,
            "retry_succeeded": True,
            "history_not_duplicated": True,
        }
    }
    duplicate = {
        "observed": {"different_workflow_duplicate_persisted": True},
        "duplicate_rejection_satisfied": False,
        "implementation_gap_reported": True,
        "original_workflow_unchanged": True,
        "approval_states_unchanged": True,
        "history_unchanged": True,
        "same_workflow_same_id_idempotent": True,
    }
    slack = {
        "checks": {
            "malformed_decision_rejected": True,
            "wrong_workflow_request_rejected": True,
            "replay_rejected": True,
            "unexpected_post_id_ignored": True,
            "unexpected_field_cannot_mutate": True,
            "request_binding_enforced": True,
            "wordpress_post_id_unchanged": True,
            "network_unused": True,
        }
    }
    documents = {
        "test-results.json": test_results,
        "workflow-state-contract-review.json": contract,
        "failure-injection-results.json": failures,
        "duplicate-post-id-results.json": duplicate,
        "slack-approval-mutation-boundary-results.json": slack,
    }
    for name, document in documents.items():
        _write_json(evidence_root / name, document)
    (evidence_root / "human-readable-summary.md").write_text(
        "# Fixture\n\nHOLD remains in force.\n", encoding="utf-8"
    )

    evidence_files = {
        name: _sha256(evidence_root / name)
        for name in sorted(set(documents) | {"human-readable-summary.md"})
    }
    manifest = {
        "evidence_id": "TST-5D-W1-FIXTURE",
        "candidate_id": "candidate-fixture",
        "review_unit_id": "UNIT_WORKFLOW_STATE",
        "prior_decision_artifact_path": "exchange/decision.json",
        "prior_decision_artifact_sha256": _sha256(decision_path),
        "prior_decision": "HOLD",
        "production_manifest_path": "config/manifest.json",
        "production_manifest_sha256": _sha256(production_manifest_path),
        "production_source_path": "app/source.py",
        "production_source_sha256": _sha256(source_path),
        "test_source_paths": ["tests/test_sample.py"],
        "test_source_sha256": [_sha256(test_path)],
        "test_source_bindings": [
            {"path": "tests/test_sample.py", "sha256": _sha256(test_path)}
        ],
        "test_node_ids": ["tests/test_sample.py::test_fixture"],
        "test_result_counts": {"passed": 1, "failed": 0, "total": 1},
        "test_database_type": "tmp_path_new_sqlite",
        "production_database_used": False,
        "wordpress_network_used": False,
        "slack_network_used": False,
        "credential_content_read": False,
        "identified_gaps": [
            "DUPLICATE_POST_ID_NOT_REJECTED",
            "BOUND_OR_PUBLISHED_POST_ID_REPLACEMENT_NOT_REJECTED",
            "POST_ID_LENGTH_NOT_ENFORCED",
        ],
        "evidence_status": "WORKFLOW_STATE_HOLD_CLEARANCE_EVIDENCE_READY",
        "human_rereview_required": True,
        "automatic_approval": False,
        "production_rebinding_allowed": False,
        "deployment_allowed": False,
        "evidence_files": evidence_files,
    }
    _write_json(evidence_root / "evidence-manifest.json", manifest)
    return repo_root, evidence_root


def _mutate_json(evidence_root: Path, name: str, path: tuple[str, ...], value) -> None:
    artifact_path = evidence_root / name
    document = json.loads(artifact_path.read_text(encoding="utf-8"))
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    _write_json(artifact_path, document)
    _refresh_evidence_hashes(evidence_root)


SEMANTIC_ATTACKS = (
    ("duplicate-post-id-results.json", ("duplicate_rejection_satisfied",), True),
    ("failure-injection-results.json", ("checks", "history_not_duplicated"), False),
    ("failure-injection-results.json", ("checks", "no_partial_state_only_update"), False),
    ("failure-injection-results.json", ("checks", "no_partial_post_id_only_update"), False),
    ("failure-injection-results.json", ("checks", "no_partial_approval_only_update"), False),
    ("failure-injection-results.json", ("checks", "flush_rollback_executed"), False),
    ("failure-injection-results.json", ("checks", "reopened_session_verified"), False),
    ("workflow-state-contract-review.json", ("invalid_post_id_checks", "zero_rejected"), False),
    ("slack-approval-mutation-boundary-results.json", ("checks", "malformed_decision_rejected"), False),
    ("slack-approval-mutation-boundary-results.json", ("checks", "wrong_workflow_request_rejected"), False),
    ("slack-approval-mutation-boundary-results.json", ("checks", "replay_rejected"), False),
    ("evidence-manifest.json", ("production_database_used",), True),
    ("evidence-manifest.json", ("slack_network_used",), True),
    ("evidence-manifest.json", ("automatic_approval",), True),
)


def test_valid_evidence_passes(tmp_path: Path) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    result = validate_evidence(evidence_root, repo_root=repo_root)
    assert result["integrity"] == "PASS"
    assert result["review_decision"] == "HOLD"


@pytest.mark.parametrize(("name", "path", "value"), SEMANTIC_ATTACKS)
def test_semantic_adversarial_evidence_is_rejected(
    tmp_path: Path,
    name: str,
    path: tuple[str, ...],
    value,
) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    _mutate_json(evidence_root, name, path, value)
    with pytest.raises(EvidenceIntegrityError, match=ERROR_CODE):
        validate_evidence(evidence_root, repo_root=repo_root)


def test_prior_decision_approve_is_rejected_even_with_updated_binding(
    tmp_path: Path,
) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    decision_path = repo_root / "exchange/decision.json"
    _write_json(
        decision_path,
        {"review_unit": "UNIT_WORKFLOW_STATE", "decision": "APPROVE"},
    )
    manifest_path = evidence_root / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["prior_decision_artifact_sha256"] = _sha256(decision_path)
    _write_json(manifest_path, manifest)
    with pytest.raises(EvidenceIntegrityError, match=ERROR_CODE):
        validate_evidence(evidence_root, repo_root=repo_root)


def test_changed_decision_sha_is_rejected(tmp_path: Path) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    decision_path = repo_root / "exchange/decision.json"
    _write_json(
        decision_path,
        {"review_unit": "UNIT_WORKFLOW_STATE", "decision": "HOLD", "x": 1},
    )
    with pytest.raises(EvidenceIntegrityError, match=ERROR_CODE):
        validate_evidence(evidence_root, repo_root=repo_root)


def test_symlink_evidence_is_rejected(tmp_path: Path) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    summary = evidence_root / "human-readable-summary.md"
    target = tmp_path / "outside-summary.md"
    target.write_text(summary.read_text(encoding="utf-8"), encoding="utf-8")
    summary.unlink()
    summary.symlink_to(target)
    with pytest.raises(EvidenceIntegrityError, match=ERROR_CODE):
        validate_evidence(evidence_root, repo_root=repo_root)


def test_hard_link_evidence_is_rejected(tmp_path: Path) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    summary = evidence_root / "human-readable-summary.md"
    target = tmp_path / "hard-link-source.md"
    target.write_text(summary.read_text(encoding="utf-8"), encoding="utf-8")
    summary.unlink()
    os.link(target, summary)
    with pytest.raises(EvidenceIntegrityError, match=ERROR_CODE):
        validate_evidence(evidence_root, repo_root=repo_root)


def test_secret_like_literal_is_rejected_after_sha_rebinding(tmp_path: Path) -> None:
    repo_root, evidence_root = _build_valid_fixture(tmp_path)
    summary = evidence_root / "human-readable-summary.md"
    summary.write_text(
        "# Fixture\n\nxoxb-this-is-an-injected-secret-value\n",
        encoding="utf-8",
    )
    _refresh_evidence_hashes(evidence_root)
    with pytest.raises(EvidenceIntegrityError, match=ERROR_CODE):
        validate_evidence(evidence_root, repo_root=repo_root)
