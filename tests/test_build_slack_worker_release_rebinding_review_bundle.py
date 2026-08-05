from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import build_slack_worker_release_rebinding_review_bundle as builder


CANDIDATE_ROOT = Path("/tmp/db-safe-tst-5b-candidate-20260724-02")
CREATED_AT = "2026-07-24T00:00:00Z"


def documents() -> dict:
    policy = builder.load_json_bytes(
        builder.secure_repo_bytes(builder.POLICY_PATH), "POLICY_INVALID"
    )
    evidence = builder.synthetic_test_evidence(policy, CREATED_AT)
    return builder.build_documents(
        CANDIDATE_ROOT, created_at=CREATED_AT, test_evidence=evidence
    )


def test_master_manifest_is_review_only_and_complete() -> None:
    manifest = documents()["manifest"]
    assert manifest["schema_status"] == "SCHEMA_CANDIDATE_NOT_ACTIVE"
    assert manifest["review_bundle_status"] == (
        "READY_FOR_HUMAN_REVIEW_NOT_APPROVED"
    )
    assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"
    assert manifest["review_unit_count"] == 3
    assert len(manifest["diff_paths"]) == 5
    assert len(manifest["decision_template_paths"]) == 3
    assert manifest["production_release"] is False
    assert manifest["production_approval_created"] is False
    assert manifest["deployment_allowed"] is False
    assert manifest["runtime_execution_allowed"] is False
    assert manifest["production_manifest_replacement_allowed"] is False
    assert manifest["human_decision_required"] is True
    assert manifest["human_decision_recorded"] is False


def test_candidate_and_downstream_are_exact_persistent_snapshots() -> None:
    built = documents()
    payloads = built["payloads"]
    assert payloads["candidate-manifest.json"] == (
        CANDIDATE_ROOT / "candidate-manifest.json"
    ).read_bytes()
    assert payloads["dependency-closure.json"] == (
        CANDIDATE_ROOT / "dependency-closure.json"
    ).read_bytes()
    assert payloads["downstream-rebinding-plan.json"] == (
        CANDIDATE_ROOT / "downstream-rebinding-plan.json"
    ).read_bytes()


def test_all_five_diffs_are_full_and_provenance_bound() -> None:
    built = documents()
    policy = built["policy"]
    manifest = built["manifest"]
    assert set(manifest["diff_paths"]) == set(policy["source_contract"])
    for source, path in manifest["diff_paths"].items():
        document = json.loads(built["payloads"][path])
        binding = policy["source_contract"][source]
        assert document["baseline_commit"] == policy["baseline_commit"]
        assert document["old_sha256"] == binding["baseline_sha256"]
        assert document["current_sha256"] == binding["current_sha256"]
        assert document["truncated"] is False
        assert document["binary"] is False
        assert document["secret_literal_scan_passed"] is True
        assert document["unified_diff"].startswith("--- ")
        assert hashlib.sha256(
            document["unified_diff"].encode()
        ).hexdigest() == document["unified_diff_sha256"]


def test_access_guard_is_an_added_source_from_verified_baseline_absence() -> None:
    built = documents()
    path = built["manifest"]["diff_paths"]["app/db/access_guard.py"]
    diff = json.loads(built["payloads"][path])
    assert diff["change_type"] == "ADDED"
    assert diff["old_path"] == "/dev/null"
    assert diff["old_sha256"] is None
    assert diff["deleted_line_count"] == 0
    assert diff["added_line_count"] > 0


def test_review_units_are_independent_and_not_reviewed() -> None:
    built = documents()
    expected = {
        "UNIT_DB_SAFETY": 3,
        "UNIT_WORKFLOW_STATE": 1,
        "UNIT_SLACK_RUNTIME": 1,
    }
    assigned = []
    for unit, path in built["manifest"]["review_unit_paths"].items():
        packet = json.loads(built["payloads"][path])
        assert len(packet["sources"]) == expected[unit]
        assigned.extend(item["path"] for item in packet["sources"])
        assert packet["review_status"] == "NOT_REVIEWED"
        assert packet["approval_status"] == "NOT_ISSUED"
        assert packet["recommended_decision"] == "REVIEW_REQUIRED"
        assert packet["human_decision_required"] is True
        assert set(packet["risk_matrix"].values()) <= {
            "LOW",
            "MEDIUM",
            "HIGH",
            "UNKNOWN",
        }
        assert packet["human_review_checklist"]
    assert len(assigned) == len(set(assigned)) == 5


def test_test_evidence_is_node_specific_and_boundary_closed() -> None:
    built = documents()
    for path in built["manifest"]["review_unit_paths"].values():
        packet = json.loads(built["payloads"][path])
        assert packet["related_tests"]
        for evidence in packet["related_tests"]:
            assert "::test_" in evidence["test_node_id"]
            assert evidence["purpose"]
            assert evidence["result"] == "PASS"
            assert len(evidence["test_source_sha256"]) == 64
            assert evidence["evidence_generated_at"] == CREATED_AT
            assert evidence["network_used"] is False
            assert evidence["production_database_used"] is False
            assert evidence["credential_content_read"] is False


def test_evidence_gaps_are_explicit() -> None:
    built = documents()
    gaps = {}
    for unit, path in built["manifest"]["review_unit_paths"].items():
        gaps[unit] = json.loads(built["payloads"][path])["test_evidence_gaps"]
    assert all(gaps.values())
    assert any("ImportError" in gap for gap in gaps["UNIT_SLACK_RUNTIME"])
    assert any("duplicate" in gap for gap in gaps["UNIT_WORKFLOW_STATE"])


def test_decision_templates_are_unfilled_and_non_authorizing() -> None:
    built = documents()
    for unit, path in built["manifest"]["decision_template_paths"].items():
        template = json.loads(built["payloads"][path])
        assert template["review_unit_id"] == unit
        assert template["decision"] is None
        assert template["reviewer"] is None
        assert template["reviewed_at"] is None
        assert template["reason"] is None
        assert template["conditions"] == []
        assert template["expiration"] is None
        assert template["single_use"] is True
        assert template["approval_issued"] is False
        assert template["production_manifest_update_allowed"] is False
        assert template["deployment_allowed"] is False


def test_generate_is_exclusive_and_uses_candidate_namespace(tmp_path: Path) -> None:
    built = documents()
    candidate_id = built["candidate"]["candidate_id"]
    review_root = tmp_path / "review_requests"
    output = review_root / candidate_id
    result = builder.generate(
        CANDIDATE_ROOT,
        created_at=CREATED_AT,
        output_root=output,
        test_evidence=builder.synthetic_test_evidence(
            built["policy"], CREATED_AT
        ),
        review_request_root=review_root,
    )
    assert result["result"] == "READY_FOR_HUMAN_REVIEW_NOT_APPROVED"
    assert {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()} == set(
        built["manifest"]["expected_files"]
    )
    with pytest.raises(
        builder.ReviewBundleBlocked, match="REVIEW_BUNDLE_OVERWRITE_REJECTED"
    ):
        builder.generate(
            CANDIDATE_ROOT,
            created_at=CREATED_AT,
            output_root=output,
            test_evidence=builder.synthetic_test_evidence(
                built["policy"], CREATED_AT
            ),
            review_request_root=review_root,
        )


def test_output_outside_selected_review_namespace_is_rejected(
    tmp_path: Path,
) -> None:
    built = documents()
    with pytest.raises(
        builder.ReviewBundleBlocked, match="REVIEW_BUNDLE_OUTPUT_PATH_INVALID"
    ):
        builder.validate_output_root(
            tmp_path / "wrong",
            built["candidate"]["candidate_id"],
            review_request_root=tmp_path / "review_requests",
        )


def test_review_bundle_contains_no_sensitive_literal_value() -> None:
    built = documents()
    assert not any(
        builder.sensitive_literal_present(payload)
        for payload in built["payloads"].values()
    )
