#!/usr/bin/env python3
"""Fail-closed integrity validation for a review-only rebinding bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

try:
    from scripts import build_slack_worker_release_rebinding_review_bundle as builder
    from scripts.lib.secure_release_file_reader import (
        ReleaseFileError,
        read_secure_release_file,
    )
    from scripts.validate_slack_worker_release_bundle_contract import (
        validate_production_manifest_contract,
    )
    from scripts.validate_slack_worker_release_manifest_candidate import (
        CandidateValidationError,
        validate_candidate_document,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    import build_slack_worker_release_rebinding_review_bundle as builder  # type: ignore
    from lib.secure_release_file_reader import (  # type: ignore[no-redef]
        ReleaseFileError,
        read_secure_release_file,
    )
    from validate_slack_worker_release_bundle_contract import (  # type: ignore
        validate_production_manifest_contract,
    )
    from validate_slack_worker_release_manifest_candidate import (  # type: ignore
        CandidateValidationError,
        validate_candidate_document,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRITY_ERROR = "SLACK_WORKER_RELEASE_REVIEW_BUNDLE_INTEGRITY_FAILED"


class ReviewBundleIntegrityError(ValueError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(INTEGRITY_ERROR)


def fail(detail: str) -> None:
    raise ReviewBundleIntegrityError(detail)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def decode(data: bytes, detail: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewBundleIntegrityError(detail) from exc
    if not isinstance(value, dict):
        fail(detail)
    return value


def tree_files(root: Path) -> set[str]:
    try:
        root_meta = os.lstat(root)
    except OSError as exc:
        raise ReviewBundleIntegrityError("ROOT_MISSING") from exc
    if stat.S_ISLNK(root_meta.st_mode) or not stat.S_ISDIR(root_meta.st_mode):
        fail("ROOT_INVALID")
    files: set[str] = set()

    def visit(directory: Path) -> None:
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise ReviewBundleIntegrityError("TREE_SCAN_FAILED") from exc
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            path = Path(entry.path)
            if stat.S_ISLNK(metadata.st_mode):
                fail("SYMLINK_REJECTED")
            if stat.S_ISDIR(metadata.st_mode):
                visit(path)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                fail("NON_REGULAR_FILE_REJECTED")
            if metadata.st_nlink != 1:
                fail("HARDLINK_REJECTED")
            files.add(path.relative_to(root).as_posix())

    visit(root)
    return files


def secure_bundle_file(root: Path, relative: str) -> bytes:
    try:
        return read_secure_release_file(
            root / relative, allowed_root=root, expected_path=root / relative
        ).data
    except ReleaseFileError as exc:
        raise ReviewBundleIntegrityError(exc.code) from exc


def require_false(document: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if document.get(field) is not False:
            fail(f"FLAG_NOT_FALSE:{field}")


def validate(root: Path) -> dict[str, Any]:
    absolute_root = root.absolute()
    files = tree_files(absolute_root)
    manifest_bytes = secure_bundle_file(absolute_root, "review-bundle-manifest.json")
    manifest = decode(manifest_bytes, "MANIFEST_INVALID")
    if manifest.get("schema_status") != "SCHEMA_CANDIDATE_NOT_ACTIVE":
        fail("SCHEMA_STATUS_INVALID")
    if manifest.get("review_bundle_status") != (
        "READY_FOR_HUMAN_REVIEW_NOT_APPROVED"
    ) or manifest.get("release_status") != "CANDIDATE_NOT_APPROVED":
        fail("BUNDLE_STATUS_INVALID")
    expected_files = manifest.get("expected_files")
    if not isinstance(expected_files, list) or set(expected_files) != files:
        fail("MANIFEST_FILE_SET_MISMATCH")
    require_false(
        manifest,
        (
            "production_release",
            "production_approval_created",
            "deployment_allowed",
            "runtime_execution_allowed",
            "production_manifest_replacement_allowed",
            "human_decision_recorded",
        ),
    )
    if manifest.get("human_decision_required") is not True:
        fail("HUMAN_DECISION_REQUIREMENT_INVALID")
    if manifest.get("baseline_commit") != builder.load_json_bytes(
        builder.secure_repo_bytes(builder.POLICY_PATH), "POLICY_INVALID"
    )["baseline_commit"]:
        fail("BASELINE_COMMIT_INVALID")

    payload_by_path = {
        relative: secure_bundle_file(absolute_root, relative)
        for relative in files
        if relative != "review-bundle-manifest.json"
    }
    for data in [manifest_bytes, *payload_by_path.values()]:
        if builder.sensitive_literal_present(data):
            fail("SENSITIVE_LITERAL_REJECTED")

    candidate_path = manifest.get("candidate_manifest_path")
    if candidate_path != "candidate-manifest.json":
        fail("CANDIDATE_PATH_INVALID")
    candidate_bytes = payload_by_path[candidate_path]
    if sha256_bytes(candidate_bytes) != manifest.get("candidate_manifest_sha256"):
        fail("CANDIDATE_SHA_MISMATCH")
    candidate = decode(candidate_bytes, "CANDIDATE_INVALID")

    production_path = REPO_ROOT / manifest.get("production_manifest_path", "")
    try:
        production_snapshot = read_secure_release_file(
            production_path,
            allowed_root=REPO_ROOT,
            expected_sha256=manifest.get("production_manifest_sha256"),
        )
    except ReleaseFileError as exc:
        raise ReviewBundleIntegrityError("PRODUCTION_MANIFEST_SHA_MISMATCH") from exc
    production = decode(production_snapshot.data, "PRODUCTION_MANIFEST_INVALID")
    production_id = production.get("release_id_candidate")
    try:
        validate_candidate_document(candidate, production_release_id=production_id)
    except CandidateValidationError as exc:
        raise ReviewBundleIntegrityError(
            f"CANDIDATE_CONTRACT_INVALID:{exc.code}"
        ) from exc
    if candidate.get("candidate_id") != manifest.get("candidate_id"):
        fail("CANDIDATE_ID_MISMATCH")
    if candidate.get("candidate_id") == production_id:
        fail("PRODUCTION_ID_IMPERSONATION")
    try:
        validate_production_manifest_contract(candidate)
    except SystemExit as exc:
        if str(exc) != "CANDIDATE_MANIFEST_NOT_VALID_AS_PRODUCTION_RELEASE":
            fail("PRODUCTION_CONTRACT_SEPARATION_INVALID")
    else:
        fail("CANDIDATE_ACCEPTED_AS_PRODUCTION")

    validation_path = manifest.get("candidate_validator_result_path")
    validation_bytes = payload_by_path.get(validation_path, b"")
    if sha256_bytes(validation_bytes) != manifest.get(
        "candidate_validator_result_sha256"
    ):
        fail("CANDIDATE_VALIDATION_RESULT_SHA_MISMATCH")
    validation_result = decode(validation_bytes, "VALIDATION_RESULT_INVALID")
    if validation_result.get("result") != "PASS_CANDIDATE_NOT_APPROVED":
        fail("CANDIDATE_VALIDATION_RESULT_INVALID")
    require_false(
        validation_result,
        (
            "deployment_allowed",
            "runtime_execution_allowed",
            "production_approval_created",
            "production_release",
            "production_manifest_replacement_allowed",
        ),
    )

    downstream_path = manifest.get("downstream_plan_path")
    downstream_bytes = payload_by_path.get(downstream_path, b"")
    if sha256_bytes(downstream_bytes) != manifest.get("downstream_plan_sha256"):
        fail("DOWNSTREAM_PLAN_SHA_MISMATCH")
    downstream = decode(downstream_bytes, "DOWNSTREAM_PLAN_INVALID")
    if (
        downstream.get("downstream_candidate_count") != 19
        or downstream.get("direct_immutable_evidence_count") != 2
    ):
        fail("DOWNSTREAM_PLAN_COUNT_INVALID")

    audit = candidate.get("source_audit", [])
    changed_sources = {
        item.get("path")
        for item in audit
        if isinstance(item, dict) and item.get("change") in {"MODIFIED", "ADDED"}
    }
    unchanged_sources = {
        item.get("path")
        for item in audit
        if isinstance(item, dict) and item.get("change") == "UNCHANGED"
    }
    unit_paths = manifest.get("review_unit_paths")
    unit_hashes = manifest.get("review_unit_sha256")
    if (
        manifest.get("review_unit_count") != 3
        or not isinstance(unit_paths, dict)
        or set(unit_paths)
        != {"UNIT_DB_SAFETY", "UNIT_WORKFLOW_STATE", "UNIT_SLACK_RUNTIME"}
    ):
        fail("REVIEW_UNIT_SET_INVALID")
    assigned: list[str] = []
    packet_hashes: dict[str, str] = {}
    for unit_id, path in unit_paths.items():
        data = payload_by_path.get(path, b"")
        digest = sha256_bytes(data)
        packet_hashes[unit_id] = digest
        if not isinstance(unit_hashes, dict) or unit_hashes.get(unit_id) != digest:
            fail("REVIEW_PACKET_SHA_MISMATCH")
        packet = decode(data, "REVIEW_PACKET_INVALID")
        if packet.get("unit_id") != unit_id:
            fail("REVIEW_UNIT_ID_MISMATCH")
        if packet.get("review_status") != "NOT_REVIEWED":
            fail("REVIEW_STATUS_INVALID")
        if packet.get("approval_status") != "NOT_ISSUED":
            fail("APPROVAL_STATUS_INVALID")
        require_false(
            packet,
            (
                "production_release",
                "production_approval_created",
                "deployment_allowed",
                "runtime_execution_allowed",
                "production_manifest_replacement_allowed",
            ),
        )
        sources = packet.get("sources")
        if not isinstance(sources, list):
            fail("REVIEW_PACKET_SOURCE_INVALID")
        assigned.extend(item.get("path") for item in sources if isinstance(item, dict))
        evidence = packet.get("related_tests")
        if not isinstance(evidence, list) or not evidence:
            fail("TEST_EVIDENCE_MISSING")
        for item in evidence:
            if (
                item.get("result") != "PASS"
                or item.get("network_used") is not False
                or item.get("production_database_used") is not False
                or item.get("credential_content_read") is not False
            ):
                fail("TEST_EVIDENCE_INVALID")
    if len(assigned) != len(set(assigned)):
        fail("REVIEW_SOURCE_DUPLICATE")
    if set(assigned) != changed_sources or set(assigned) & unchanged_sources:
        fail("REVIEW_SOURCE_COVERAGE_INVALID")

    diff_paths = manifest.get("diff_paths")
    diff_hashes = manifest.get("diff_sha256")
    if not isinstance(diff_paths, dict) or set(diff_paths) != changed_sources:
        fail("DIFF_SET_INVALID")
    policy = builder.load_json_bytes(
        builder.secure_repo_bytes(builder.POLICY_PATH), "POLICY_INVALID"
    )
    for source, path in diff_paths.items():
        data = payload_by_path.get(path, b"")
        if not isinstance(diff_hashes, dict) or diff_hashes.get(source) != sha256_bytes(
            data
        ):
            fail("DIFF_SHA_MISMATCH")
        document = decode(data, "DIFF_INVALID")
        if (
            document.get("source_path") != source
            or document.get("baseline_commit") != manifest.get("baseline_commit")
            or document.get("truncated") is not False
            or document.get("binary") is not False
            or document.get("secret_literal_scan_passed") is not True
        ):
            fail("DIFF_CONTRACT_INVALID")
        unified = document.get("unified_diff")
        if not isinstance(unified, str) or sha256_bytes(
            unified.encode("utf-8")
        ) != document.get("unified_diff_sha256"):
            fail("DIFF_CONTENT_SHA_MISMATCH")
        binding = policy["source_contract"][source]
        expected = builder.source_diff_document(
            relative=source,
            baseline_commit=policy["baseline_commit"],
            expected_baseline_sha=binding["baseline_sha256"],
            expected_current_sha=binding["current_sha256"],
        )
        if document != expected:
            fail("DIFF_PROVENANCE_MISMATCH")

    template_paths = manifest.get("decision_template_paths")
    template_hashes = manifest.get("decision_template_sha256")
    if not isinstance(template_paths, dict) or set(template_paths) != set(unit_paths):
        fail("DECISION_TEMPLATE_SET_INVALID")
    for unit_id, path in template_paths.items():
        data = payload_by_path.get(path, b"")
        if not isinstance(template_hashes, dict) or template_hashes.get(
            unit_id
        ) != sha256_bytes(data):
            fail("DECISION_TEMPLATE_SHA_MISMATCH")
        template = decode(data, "DECISION_TEMPLATE_INVALID")
        if (
            template.get("review_unit_id") != unit_id
            or template.get("candidate_id") != candidate.get("candidate_id")
            or template.get("review_packet_sha256") != packet_hashes[unit_id]
            or template.get("allowed_decisions") != ["APPROVE", "REJECT", "HOLD"]
            or template.get("decision") is not None
            or template.get("reviewer") is not None
            or template.get("reviewed_at") is not None
            or template.get("reason") is not None
            or template.get("conditions") != []
            or template.get("expiration") is not None
            or template.get("single_use") is not True
            or template.get("approval_issued") is not False
            or template.get("production_manifest_update_allowed") is not False
            or template.get("deployment_allowed") is not False
        ):
            fail("DECISION_TEMPLATE_NOT_UNFILLED")

    summary_path = manifest.get("human_summary_path")
    summary = payload_by_path.get(summary_path, b"")
    if sha256_bytes(summary) != manifest.get("human_summary_sha256"):
        fail("HUMAN_SUMMARY_SHA_MISMATCH")

    return {
        "result": "PASS_READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
        "review_bundle_root": str(absolute_root),
        "review_bundle_manifest_sha256": sha256_bytes(manifest_bytes),
        "candidate_id": candidate["candidate_id"],
        "candidate_manifest_sha256": sha256_bytes(candidate_bytes),
        "source_diff_count": 5,
        "source_diff_provenance_verified": True,
        "review_unit_count": 3,
        "decision_template_count": 3,
        "decision_templates_unfilled": True,
        "human_decision_recorded": False,
        "production_approval_created": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate(args.bundle_root)
    except ReviewBundleIntegrityError as exc:
        print(f"{INTEGRITY_ERROR}: {exc.detail}")
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
