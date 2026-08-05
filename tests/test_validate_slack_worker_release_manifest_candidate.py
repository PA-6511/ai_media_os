from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts import build_slack_worker_release_manifest_candidate as builder
from scripts import validate_slack_worker_release_manifest_candidate as validator


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ID = builder.load_json(
    ROOT / "config/slack_worker_release_source_manifest.json"
)["release_id_candidate"]


def manifest() -> dict:
    return deepcopy(builder.build_candidate_documents()["candidate_manifest"])


def assert_rejected(value: dict, code: str) -> None:
    with pytest.raises(validator.CandidateValidationError, match=code):
        validator.validate_candidate_document(
            value, production_release_id=PRODUCTION_ID
        )


def test_generated_candidate_and_all_bound_documents_pass(tmp_path: Path) -> None:
    output = tmp_path / "candidate"
    builder.generate(output)
    result = validator.validate_candidate_files(
        output / "candidate-manifest.json",
        output / "dependency-closure.json",
        output / "downstream-rebinding-plan.json",
    )
    assert result["result"] == "PASS_CANDIDATE_NOT_APPROVED"
    assert result["dependency_closure_source_count"] == 17
    assert result["production_unrecorded_required_source_count"] == 1
    assert result["candidate_unrecorded_required_source_count"] == 0
    assert result["review_unit_count"] == 3
    assert result["downstream_candidate_count"] == 19
    assert result["immutable_evidence_excluded"] == 2
    assert result["rebinding_graph_acyclic"] is True


def test_status_violation_is_rejected() -> None:
    value = manifest()
    value["release_status"] = "APPROVED"
    assert_rejected(value, "CANDIDATE_RELEASE_STATUS_INVALID")


def test_deployment_true_is_rejected() -> None:
    value = manifest()
    value["deployment_allowed"] = True
    assert_rejected(value, "CANDIDATE_DEPLOYMENT_MUST_BE_FALSE")


def test_runtime_execution_true_is_rejected() -> None:
    value = manifest()
    value["runtime_execution_allowed"] = True
    assert_rejected(value, "CANDIDATE_RUNTIME_EXECUTION_MUST_BE_FALSE")


def test_production_approval_true_is_rejected() -> None:
    value = manifest()
    value["production_approval_created"] = True
    assert_rejected(value, "CANDIDATE_PRODUCTION_APPROVAL_MUST_BE_FALSE")


def test_production_id_impersonation_is_rejected() -> None:
    value = manifest()
    value["candidate_id"] = PRODUCTION_ID
    assert_rejected(value, "CANDIDATE_ID_INVALID|CANDIDATE_PRODUCTION_ID_IMPERSONATION")


def test_access_guard_omission_is_rejected() -> None:
    value = manifest()
    value["source_files"] = [
        item
        for item in value["source_files"]
        if item["path"] != "app/db/access_guard.py"
    ]
    value["source_file_count"] = 16
    assert_rejected(value, "CANDIDATE_SOURCE_COUNT_INVALID|CANDIDATE_ACCESS_GUARD_MISSING")


def test_review_unit_omission_is_rejected() -> None:
    value = manifest()
    value["review_units"].pop()
    assert_rejected(value, "CANDIDATE_REVIEW_UNIT_COUNT_INVALID")


def test_duplicate_source_is_rejected() -> None:
    value = manifest()
    value["source_files"][-1] = deepcopy(value["source_files"][0])
    assert_rejected(value, "CANDIDATE_DUPLICATE_SOURCE_PATH")


def test_unresolved_dependency_is_rejected() -> None:
    value = manifest()
    value["unresolved_dynamic_dependencies"] = [{"call": "dynamic"}]
    assert_rejected(value, "CANDIDATE_UNRESOLVED_DEPENDENCY")


def test_candidate_outside_tmp_is_rejected() -> None:
    with pytest.raises(
        validator.CandidateValidationError,
        match="CANDIDATE_ROOT_MUST_BE_BELOW_TMP",
    ):
        validator.validate_candidate_files(
            ROOT / "candidate-manifest.json",
            ROOT / "dependency-closure.json",
            ROOT / "downstream-rebinding-plan.json",
        )


def test_validator_and_graph_contracts_are_sha_bound() -> None:
    value = manifest()
    bindings = value["validator_contract"]
    assert bindings["contract_status"] == "HARDENED_DB_SAFE_TST_5B"
    assert bindings["expected_candidate_validation_result"] == (
        "PASS_CANDIDATE_NOT_APPROVED"
    )
    assert {item["path"] for item in bindings["files"]} == {
        "scripts/lib/secure_release_file_reader.py",
        "scripts/validate_slack_worker_release_bundle_contract.py",
        "scripts/validate_slack_worker_release_manifest_candidate.py",
        "scripts/build_slack_worker_release_manifest_candidate.py",
    }
    graph = value["downstream_rebinding_plan_binding"]
    assert graph["total_rebinding_chain_count"] == 21
    assert graph["downstream_candidate_count"] == 19
    assert graph["immutable_evidence_excluded"] == 2
