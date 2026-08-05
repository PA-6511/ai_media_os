from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts import build_slack_worker_release_manifest_candidate as candidate


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/slack_worker_release_source_manifest.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_candidate_detects_complete_current_delta_and_dependency_closure() -> None:
    documents = candidate.build_candidate_documents()
    closure = documents["dependency_closure"]
    manifest = documents["candidate_manifest"]
    audit = manifest["source_audit"]

    assert closure["source_count"] == 17
    assert closure["unresolved_dynamic_dependencies"] == []
    assert {item["path"] for item in closure["sources"]} == {
        item["path"] for item in manifest["source_files"]
    }
    assert sum(item["change"] == "UNCHANGED" for item in audit) == 12
    assert sum(item["change"] == "MODIFIED" for item in audit) == 4
    assert sum(item["change"] == "ADDED" for item in audit) == 1
    assert {
        item["path"] for item in audit if item["change"] == "MODIFIED"
    } == {
        "app/db/config.py",
        "app/db/repositories/workflow_state_repository.py",
        "app/db/session.py",
        "scripts/run_slack_approval_socket.py",
    }
    access_guard = next(
        item for item in audit if item["path"] == "app/db/access_guard.py"
    )
    assert access_guard["change"] == "ADDED"
    assert access_guard["candidate_decision"] == "ADD_REQUIRED_SOURCE"
    assert access_guard["runtime_closure_member"] is True


def test_review_units_are_separate_and_not_approved() -> None:
    manifest = candidate.build_candidate_documents()["candidate_manifest"]
    units = {item["unit"]: item for item in manifest["review_units"]}

    assert set(units) == {
        "UNIT_DB_SAFETY",
        "UNIT_WORKFLOW_STATE",
        "UNIT_SLACK_RUNTIME",
    }
    assert units["UNIT_DB_SAFETY"]["sources"] == [
        "app/db/access_guard.py",
        "app/db/config.py",
        "app/db/session.py",
    ]
    assert units["UNIT_WORKFLOW_STATE"]["change_category"] == (
        "WORDPRESS_STATE_RECONCILIATION_CHANGE"
    )
    assert units["UNIT_SLACK_RUNTIME"]["change_category"] == (
        "SLACK_RUNTIME_LIFECYCLE_CHANGE"
    )
    assert all(item["approval_status"] == "NOT_APPROVED" for item in units.values())
    assert all(len(item["review_unit_sha256"]) == 64 for item in units.values())


def test_candidate_is_non_deployable_and_deterministic() -> None:
    first = candidate.build_candidate_documents()
    second = candidate.build_candidate_documents()
    manifest = first["candidate_manifest"]

    assert first["candidate_manifest_bytes"] == second["candidate_manifest_bytes"]
    assert first["candidate_manifest_sha256"] == second["candidate_manifest_sha256"]
    assert first["downstream_rebinding_plan"] == second["downstream_rebinding_plan"]
    assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"
    assert manifest["candidate_id"].startswith(
        "slack-worker-CANDIDATE-NOT-APPROVED-"
    )
    assert manifest["formal_release_id_issued"] is False
    assert manifest["deployment_allowed"] is False
    assert manifest["runtime_execution_allowed"] is False
    assert manifest["production_approval_created"] is False
    assert manifest["review_incomplete_source_count"] == 5


def test_generate_writes_only_below_tmp_and_preserves_manifest(tmp_path: Path) -> None:
    output = tmp_path / "candidate"
    before = file_sha256(MANIFEST)

    result = candidate.generate(output)

    assert result["result"] == "PASS_DRY_RUN_CANDIDATE_NOT_APPROVED"
    assert Path(result["output_directory"]).is_relative_to(Path("/tmp"))
    assert {path.name for path in output.iterdir()} == {
        "candidate-manifest.json",
        "dependency-closure.json",
        "downstream-rebinding-plan.json",
    }
    assert stat_mode(output) == "0700"
    assert all(stat_mode(path) == "0600" for path in output.iterdir())
    assert file_sha256(MANIFEST) == before
    assert result["production_manifest_modified"] is False
    assert result["production_downstream_artifacts_modified"] is False


def stat_mode(path: Path) -> str:
    return f"{path.stat().st_mode & 0o7777:04o}"


def test_production_manifest_output_is_rejected() -> None:
    with pytest.raises(candidate.CandidateBlocked, match="PRODUCTION_MANIFEST_OUTPUT_REJECTED"):
        candidate.validate_output_directory(MANIFEST)


def test_non_tmp_and_direct_tmp_outputs_are_rejected() -> None:
    with pytest.raises(candidate.CandidateBlocked, match="OUTPUT_MUST_BE_BELOW_TMP"):
        candidate.validate_output_directory(ROOT / "candidate-output")
    with pytest.raises(candidate.CandidateBlocked, match="DIRECT_TMP_OUTPUT_REJECTED"):
        candidate.validate_output_directory(Path("/tmp"))


def test_existing_and_symlink_outputs_are_rejected(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(candidate.CandidateBlocked, match="OUTPUT_EXISTS_OVERWRITE_REJECTED"):
        candidate.validate_output_directory(existing)

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(candidate.CandidateBlocked, match="OUTPUT_SYMLINK_REJECTED"):
        candidate.validate_output_directory(link)


def test_duplicate_missing_traversal_and_absolute_sources_are_rejected(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(candidate.CandidateBlocked, match="DUPLICATE_SOURCE_PATH"):
        candidate.validate_source_paths(tmp_path, ["source.py", "source.py"])
    with pytest.raises(candidate.CandidateBlocked, match="SOURCE_MISSING"):
        candidate.validate_source_paths(tmp_path, ["missing.py"])
    with pytest.raises(candidate.CandidateBlocked, match="SOURCE_PATH_TRAVERSAL"):
        candidate.validate_source_paths(tmp_path, ["../outside.py"])
    with pytest.raises(candidate.CandidateBlocked, match="SOURCE_PATH_ABSOLUTE"):
        candidate.validate_source_paths(tmp_path, [str(source)])


def test_symlink_source_and_root_escape_are_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    link.symlink_to(outside)
    with pytest.raises(candidate.CandidateBlocked, match="SOURCE_SYMLINK"):
        candidate.validate_source_paths(tmp_path, ["linked.py"])


def test_unresolved_dynamic_dependency_blocks_candidate(tmp_path: Path) -> None:
    entrypoint = tmp_path / "entrypoint.py"
    entrypoint.write_text(
        "import importlib\n"
        "name = 'package.' + 'runtime'\n"
        "importlib.import_module(name)\n",
        encoding="utf-8",
    )
    closure = candidate.build_dependency_closure(tmp_path, ["entrypoint.py"])
    assert closure["unresolved_dynamic_dependencies"] == [
        {
            "call": "importlib.import_module",
            "line": 3,
            "module": "entrypoint",
        }
    ]
    with pytest.raises(candidate.CandidateBlocked, match="UNRESOLVED_DYNAMIC_DEPENDENCY"):
        candidate.require_resolved_dependencies(closure)


def test_import_kinds_and_entrypoint_evidence_are_recorded() -> None:
    closure = candidate.build_candidate_documents()["dependency_closure"]
    edges = closure["import_edges"]
    external = {item["module"]: item["kinds"] for item in closure["external_imports"]}

    assert any(
        item["from"] == "scripts/run_slack_approval_readiness.py"
        and item["to"] == "scripts/run_slack_approval_socket.py"
        and item["kind"] == "LAZY_RUNTIME_IMPORT"
        for item in edges
    )
    assert external["slack_bolt"] == ["OPTIONAL_IMPORT"]
    assert "app" not in external
    assert closure["subprocess_calls"] == []
    assert {
        item["path"] for item in closure["entrypoint_evidence"]
    } == {
        "config/slack_worker_release_source_manifest.json",
        "config/slack_worker_release_bundle_policy.json",
        "systemd/ai-media-os-slack-approval-readiness.service",
        "scripts/run_slack_approval_readiness.py",
    }


def test_downstream_chain_distinguishes_policy_and_immutable_evidence() -> None:
    plan = candidate.build_candidate_documents()["downstream_rebinding_plan"]

    assert plan["direct_policy_binder_count"] == 9
    assert plan["direct_immutable_evidence_count"] == 2
    assert plan["direct_binder_count"] == 11
    assert plan["indirect_binder_count"] == 10
    assert plan["total_rebinding_chain_count"] == 21
    assert plan["downstream_candidate_count"] == 19
    assert plan["circular_dependency_detected"] is False
    immutable = [item for item in plan["artifacts"] if not item["mutable"]]
    mutable = [item for item in plan["artifacts"] if item["mutable"]]
    assert len(immutable) == 2
    assert all(item["resulting_candidate_artifact_sha256"] is None for item in immutable)
    assert all(
        len(item["resulting_candidate_artifact_sha256"]) == 64 for item in mutable
    )
    assert all(item["atomic_write_requirement"] for item in mutable)


def test_candidate_contains_no_secret_values_or_secret_fields() -> None:
    documents = candidate.build_candidate_documents()
    rendered = documents["candidate_manifest_bytes"].decode("utf-8").lower()

    assert "slack_bot_token" not in rendered
    assert "slack_app_token" not in rendered
    assert "credential_value" not in rendered
    assert "secret_value" not in rendered
    assert documents["candidate_manifest"]["governance"][
        "sensitive_content_read"
    ] is False


def test_control_policy_does_not_activate_a_production_review() -> None:
    policy = json.loads(candidate.POLICY_PATH.read_text(encoding="utf-8"))

    assert policy["policy_status"] == "DESIGN_ONLY_NOT_APPROVED"
    assert policy["review_schema_candidate"]["name"] == (
        "SLACK_WORKER_RELEASE_REBINDING_REVIEW"
    )
    assert policy["review_schema_candidate"]["status"] == (
        "SCHEMA_CANDIDATE_NOT_ACTIVE"
    )
    assert policy["governance"]["production_review_created"] is False
    assert policy["governance"]["production_database_access_allowed"] is False
