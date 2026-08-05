#!/usr/bin/env python3
"""Validate TST-5D-W1 supplemental evidence without using runtime systems."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any


ERROR_CODE = "WORKFLOW_STATE_HOLD_CLEARANCE_EVIDENCE_INTEGRITY_FAILED"
EXPECTED_STATUS = "WORKFLOW_STATE_HOLD_CLEARANCE_EVIDENCE_READY"
EXPECTED_UNIT = "UNIT_WORKFLOW_STATE"
REQUIRED_EVIDENCE_FILES = {
    "test-results.json",
    "workflow-state-contract-review.json",
    "failure-injection-results.json",
    "duplicate-post-id-results.json",
    "slack-approval-mutation-boundary-results.json",
    "human-readable-summary.md",
}
SECRET_PATTERNS = (
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class EvidenceIntegrityError(ValueError):
    pass


def _fail(detail: str) -> None:
    raise EvidenceIntegrityError(f"{ERROR_CODE}: {detail}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON {path.name}: {exc}")
    if not isinstance(value, dict):
        _fail(f"JSON root must be an object: {path.name}")
    return value


def _regular_file(path: Path, *, root: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(f"cannot stat {path}: {exc}")
    if stat.S_ISLNK(metadata.st_mode):
        _fail(f"symlink is forbidden: {path.relative_to(root)}")
    if not stat.S_ISREG(metadata.st_mode):
        _fail(f"non-regular evidence file: {path.relative_to(root)}")
    if metadata.st_nlink != 1:
        _fail(f"hard-linked evidence file: {path.relative_to(root)}")


def _scan_tree(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        _fail("evidence root must be a real directory")
    files: set[str] = set()
    for directory, directory_names, file_names in os.walk(
        root, followlinks=False
    ):
        directory_path = Path(directory)
        for name in directory_names:
            child = directory_path / name
            if child.is_symlink():
                _fail(f"symlink directory is forbidden: {child.relative_to(root)}")
        for name in file_names:
            child = directory_path / name
            _regular_file(child, root=root)
            files.add(child.relative_to(root).as_posix())
    return files


def _safe_repo_file(repo_root: Path, relative_value: Any, label: str) -> Path:
    if not isinstance(relative_value, str) or not relative_value:
        _fail(f"{label} path missing")
    relative = Path(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        _fail(f"unsafe {label} path")
    path = repo_root / relative
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing or unsafe")
    return path


def _require_false(document: dict[str, Any], field: str) -> None:
    if document.get(field) is not False:
        _fail(f"{field} must be false")


def _require_true(document: dict[str, Any], field: str) -> None:
    if document.get(field) is not True:
        _fail(f"{field} must be true")


def _validate_test_results(
    manifest: dict[str, Any], test_results: dict[str, Any]
) -> None:
    targeted = test_results.get("targeted")
    if not isinstance(targeted, dict):
        _fail("targeted test results missing")
    node_results = targeted.get("node_results")
    if not isinstance(node_results, list) or not node_results:
        _fail("targeted node results missing")
    observed_nodes: list[str] = []
    status_counts: dict[str, int] = {}
    for entry in node_results:
        if not isinstance(entry, dict):
            _fail("targeted node result must be an object")
        node_id = entry.get("node_id")
        status_value = entry.get("status")
        if not isinstance(node_id, str) or not node_id:
            _fail("targeted node ID missing")
        if status_value not in {"passed", "failed"}:
            _fail(f"invalid targeted status for {node_id}")
        observed_nodes.append(node_id)
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
    if len(observed_nodes) != len(set(observed_nodes)):
        _fail("duplicate targeted node ID")
    if manifest.get("test_node_ids") != observed_nodes:
        _fail("manifest test node IDs do not match results")
    expected_counts = {
        "passed": status_counts.get("passed", 0),
        "failed": status_counts.get("failed", 0),
        "total": len(observed_nodes),
    }
    if targeted.get("counts") != expected_counts:
        _fail("targeted test counts do not match node results")
    if manifest.get("test_result_counts") != expected_counts:
        _fail("manifest test counts do not match node results")

    repeats = test_results.get("fault_injection_repeat_results")
    if not isinstance(repeats, list) or len(repeats) < 2:
        _fail("fault injection must be repeated in separate processes")
    if any(
        not isinstance(entry, dict)
        or entry.get("status") != "passed"
        or entry.get("process_isolated") is not True
        for entry in repeats
    ):
        _fail("fault injection repeat result is incomplete")


def _validate_semantics(
    manifest: dict[str, Any],
    duplicate: dict[str, Any],
    contract: dict[str, Any],
    failures: dict[str, Any],
    slack: dict[str, Any],
) -> None:
    if manifest.get("review_unit_id") != EXPECTED_UNIT:
        _fail("review unit mismatch")
    if manifest.get("prior_decision") != "HOLD":
        _fail("prior decision must remain HOLD")
    if manifest.get("evidence_status") != EXPECTED_STATUS:
        _fail("evidence status mismatch")
    _require_true(manifest, "human_rereview_required")
    for field in (
        "automatic_approval",
        "production_rebinding_allowed",
        "deployment_allowed",
        "production_database_used",
        "wordpress_network_used",
        "slack_network_used",
        "credential_content_read",
    ):
        _require_false(manifest, field)
    gaps = manifest.get("identified_gaps")
    required_gaps = {
        "DUPLICATE_POST_ID_NOT_REJECTED",
        "BOUND_OR_PUBLISHED_POST_ID_REPLACEMENT_NOT_REJECTED",
        "POST_ID_LENGTH_NOT_ENFORCED",
    }
    if not isinstance(gaps, list) or not required_gaps.issubset(set(gaps)):
        _fail("known implementation gaps are missing")

    observed = duplicate.get("observed")
    if not isinstance(observed, dict):
        _fail("duplicate observation missing")
    if observed.get("different_workflow_duplicate_persisted") is not True:
        _fail("duplicate reproduction must disclose persisted duplicate")
    if duplicate.get("duplicate_rejection_satisfied") is not False:
        _fail("duplicate rejection must not be reported as satisfied")
    if duplicate.get("implementation_gap_reported") is not True:
        _fail("duplicate implementation gap must be reported")
    for field in (
        "original_workflow_unchanged",
        "approval_states_unchanged",
        "history_unchanged",
        "same_workflow_same_id_idempotent",
    ):
        _require_true(duplicate, field)

    invalid = contract.get("invalid_post_id_checks")
    state_protection = contract.get("state_protection_checks")
    if not isinstance(invalid, dict) or not isinstance(state_protection, dict):
        _fail("contract check maps missing")
    for field in (
        "zero_rejected",
        "negative_rejected",
        "bool_rejected",
        "empty_rejected",
        "whitespace_rejected",
        "decimal_rejected",
        "nonnumeric_rejected",
    ):
        _require_true(invalid, field)
    if invalid.get("extreme_length_rejected") is not False:
        _fail("extreme post ID acceptance must be disclosed")
    _require_true(invalid, "extreme_length_gap_reported")
    if state_protection.get("service_preflight_protected") is not True:
        _fail("service preflight result missing")
    if state_protection.get("direct_published_replacement_rejected") is not False:
        _fail("direct published replacement gap must be disclosed")
    _require_true(state_protection, "direct_repository_gap_reported")

    checks = failures.get("checks")
    if not isinstance(checks, dict):
        _fail("failure-injection checks missing")
    for field in (
        "flush_rollback_executed",
        "commit_rollback_executed",
        "reopened_session_verified",
        "workflow_row_unchanged_after_failure",
        "post_id_unchanged_after_failure",
        "workflow_state_unchanged_after_failure",
        "history_absent_after_failure",
        "approval_unchanged_after_failure",
        "no_partial_state_only_update",
        "no_partial_post_id_only_update",
        "no_partial_approval_only_update",
        "session_recovered",
        "retry_succeeded",
        "history_not_duplicated",
    ):
        _require_true(checks, field)

    slack_checks = slack.get("checks")
    if not isinstance(slack_checks, dict):
        _fail("Slack boundary checks missing")
    for field in (
        "malformed_decision_rejected",
        "wrong_workflow_request_rejected",
        "replay_rejected",
        "unexpected_post_id_ignored",
        "unexpected_field_cannot_mutate",
        "request_binding_enforced",
        "wordpress_post_id_unchanged",
        "network_unused",
    ):
        _require_true(slack_checks, field)


def validate_evidence(
    evidence_root: Path,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    evidence_root = evidence_root.resolve(strict=False)
    repo_root = repo_root.resolve(strict=True)
    actual_files = _scan_tree(evidence_root)
    expected_files = REQUIRED_EVIDENCE_FILES | {"evidence-manifest.json"}
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        extra = sorted(actual_files - expected_files)
        _fail(f"evidence file set mismatch: missing={missing}, extra={extra}")

    manifest_path = evidence_root / "evidence-manifest.json"
    manifest = _read_json(manifest_path)
    evidence_files = manifest.get("evidence_files")
    if not isinstance(evidence_files, dict):
        _fail("evidence_files map missing")
    if set(evidence_files) != REQUIRED_EVIDENCE_FILES:
        _fail("manifest evidence file set mismatch")
    for relative, expected_sha in evidence_files.items():
        path = evidence_root / relative
        if not isinstance(expected_sha, str) or _sha256(path) != expected_sha:
            _fail(f"evidence SHA mismatch: {relative}")

    bindings = (
        ("prior_decision_artifact_path", "prior_decision_artifact_sha256"),
        ("production_manifest_path", "production_manifest_sha256"),
        ("production_source_path", "production_source_sha256"),
    )
    for path_field, sha_field in bindings:
        path = _safe_repo_file(repo_root, manifest.get(path_field), path_field)
        if manifest.get(sha_field) != _sha256(path):
            _fail(f"repository binding SHA mismatch: {path_field}")

    source_bindings = manifest.get("test_source_bindings")
    if not isinstance(source_bindings, list) or not source_bindings:
        _fail("test source bindings missing")
    source_paths: list[str] = []
    for binding in source_bindings:
        if not isinstance(binding, dict):
            _fail("test source binding must be an object")
        path = _safe_repo_file(repo_root, binding.get("path"), "test source")
        if binding.get("sha256") != _sha256(path):
            _fail("test source SHA mismatch")
        source_paths.append(binding["path"])
    if manifest.get("test_source_paths") != source_paths:
        _fail("test source path list mismatch")
    if manifest.get("test_source_sha256") != [
        binding["sha256"] for binding in source_bindings
    ]:
        _fail("test source SHA list mismatch")

    if manifest.get("test_database_type") not in {
        "sqlite:///:memory:",
        "tmp_path_new_sqlite",
    }:
        _fail("test database is not memory/tmp isolated")

    decision = _read_json(
        _safe_repo_file(
            repo_root,
            manifest.get("prior_decision_artifact_path"),
            "prior decision artifact",
        )
    )
    serialized_decision = json.dumps(decision, sort_keys=True)
    if "UNIT_WORKFLOW_STATE" not in serialized_decision or "HOLD" not in serialized_decision:
        _fail("prior decision artifact does not bind workflow HOLD")

    test_results = _read_json(evidence_root / "test-results.json")
    contract = _read_json(evidence_root / "workflow-state-contract-review.json")
    failures = _read_json(evidence_root / "failure-injection-results.json")
    duplicate = _read_json(evidence_root / "duplicate-post-id-results.json")
    slack = _read_json(
        evidence_root / "slack-approval-mutation-boundary-results.json"
    )
    _validate_test_results(manifest, test_results)
    _validate_semantics(manifest, duplicate, contract, failures, slack)

    for relative in sorted(actual_files):
        content = (evidence_root / relative).read_text(
            encoding="utf-8", errors="strict"
        )
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            _fail(f"secret-like literal found: {relative}")

    return {
        "error_code": None,
        "evidence_status": manifest["evidence_status"],
        "integrity": "PASS",
        "review_decision": "HOLD",
        "automatic_approval": False,
        "human_rereview_required": True,
        "validated_file_count": len(actual_files),
        "evidence_manifest_sha256": _sha256(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    arguments = parser.parse_args()
    try:
        result = validate_evidence(
            arguments.evidence_root,
            repo_root=arguments.repo_root,
        )
    except EvidenceIntegrityError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
