#!/usr/bin/env python3
"""Build a review-only Slack worker release rebinding bundle.

This builder creates no approval and grants no production, deployment, runtime,
database, credential, or network authority.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

try:
    from scripts.lib.secure_release_file_reader import (
        ReleaseFileError,
        read_secure_release_file,
        resolve_secure_source_path,
    )
    from scripts.validate_slack_worker_release_manifest_candidate import (
        validate_candidate_files,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    from lib.secure_release_file_reader import (  # type: ignore[no-redef]
        ReleaseFileError,
        read_secure_release_file,
        resolve_secure_source_path,
    )
    from validate_slack_worker_release_manifest_candidate import (  # type: ignore
        validate_candidate_files,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config/slack_worker_release_rebinding_review_policy.json"
REVIEW_REQUEST_ROOT = (
    REPO_ROOT / "exchange/review_requests/slack_worker_release_rebinding"
)
DEFAULT_CANDIDATE_ROOT = Path("/tmp/db-safe-tst-5b-candidate-20260724-02")


class ReviewBundleBlocked(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def pretty_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def load_json_bytes(data: bytes, code: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewBundleBlocked(code) from exc
    if not isinstance(value, dict):
        raise ReviewBundleBlocked(code)
    return value


def secure_repo_bytes(path: Path, *, expected_sha256: str | None = None) -> bytes:
    try:
        return read_secure_release_file(
            path,
            allowed_root=REPO_ROOT,
            expected_sha256=expected_sha256,
        ).data
    except ReleaseFileError as exc:
        raise ReviewBundleBlocked(exc.code) from exc


def git_object_type(commit: str) -> str:
    result = subprocess.run(
        ["git", "cat-file", "-t", commit],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise ReviewBundleBlocked("BASELINE_COMMIT_NOT_FOUND")
    return result.stdout.strip()


def git_source(commit: str, relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def sensitive_literal_present(data: bytes) -> bool:
    patterns = (
        rb"xox[baprs]-[A-Za-z0-9_-]{8,}",
        rb"xapp-[A-Za-z0-9_-]{8,}",
        rb"sk-[A-Za-z0-9_-]{12,}",
        rb"AKIA[A-Z0-9]{16}",
        rb"authorization:\s*bearer\s+[A-Za-z0-9._~+/-]{8,}",
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        rb"SLACK_(?:BOT|APP)_TOKEN\s*=\s*[^\s]+",
    )
    return any(re.search(pattern, data, flags=re.IGNORECASE) for pattern in patterns)


def source_diff_document(
    *,
    relative: str,
    baseline_commit: str,
    expected_baseline_sha: str | None,
    expected_current_sha: str,
) -> dict[str, Any]:
    _, current_path = resolve_secure_source_path(REPO_ROOT, relative)
    current = secure_repo_bytes(current_path, expected_sha256=expected_current_sha)
    baseline = git_source(baseline_commit, relative)
    if expected_baseline_sha is None:
        if baseline is not None:
            raise ReviewBundleBlocked(f"NEW_SOURCE_EXISTS_IN_BASELINE:{relative}")
        baseline = b""
        change_type = "ADDED"
        old_path = "/dev/null"
    else:
        if baseline is None:
            raise ReviewBundleBlocked(f"BASELINE_SOURCE_MISSING:{relative}")
        if sha256_bytes(baseline) != expected_baseline_sha:
            raise ReviewBundleBlocked(f"BASELINE_SOURCE_SHA_MISMATCH:{relative}")
        change_type = "MODIFIED"
        old_path = f"a/{relative}@{baseline_commit}"
    if b"\0" in baseline or b"\0" in current:
        raise ReviewBundleBlocked(f"BINARY_SOURCE_REJECTED:{relative}")
    try:
        old_text = baseline.decode("utf-8")
        new_text = current.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewBundleBlocked(f"SOURCE_UTF8_REQUIRED:{relative}") from exc
    unified = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=old_path,
            tofile=f"b/{relative}@working-tree",
            lineterm="\n",
        )
    )
    unified_bytes = unified.encode("utf-8")
    if sensitive_literal_present(unified_bytes):
        raise ReviewBundleBlocked(f"SENSITIVE_LITERAL_IN_DIFF:{relative}")
    added = sum(
        line.startswith("+") and not line.startswith("+++")
        for line in unified.splitlines()
    )
    deleted = sum(
        line.startswith("-") and not line.startswith("---")
        for line in unified.splitlines()
    )
    return {
        "schema_version": "slack_worker_source_diff_schema_candidate_v1",
        "schema_status": "SCHEMA_CANDIDATE_NOT_ACTIVE",
        "source_path": relative,
        "change_type": change_type,
        "old_path": old_path,
        "new_path": f"b/{relative}@working-tree",
        "baseline_commit": baseline_commit,
        "old_sha256": expected_baseline_sha,
        "current_sha256": expected_current_sha,
        "added_line_count": added,
        "deleted_line_count": deleted,
        "unified_diff_sha256": sha256_bytes(unified_bytes),
        "generated_source": (
            "READ_ONLY_GIT_SHOW_AND_SECURE_CURRENT_WORKTREE_FD"
            if expected_baseline_sha is not None
            else "BASELINE_ABSENCE_VERIFIED_BY_READ_ONLY_GIT_SHOW_AND_SECURE_CURRENT_WORKTREE_FD"
        ),
        "secret_literal_scan_passed": True,
        "truncated": False,
        "binary": False,
        "unified_diff": unified,
    }


def collect_test_evidence(
    policy: dict[str, Any], created_at: str
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for unit in policy["review_units"]:
        nodes = [item[0] for item in unit["test_nodes"]]
        execution = subprocess.run(
            ["python3", "-m", "pytest", "-q", *nodes, "--maxfail=1"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if execution.returncode != 0:
            raise ReviewBundleBlocked(f"TEST_EVIDENCE_FAILED:{unit['unit_id']}")
        records: list[dict[str, Any]] = []
        for node, purpose in unit["test_nodes"]:
            test_path = node.split("::", 1)[0]
            test_sha = sha256_bytes(secure_repo_bytes(REPO_ROOT / test_path))
            records.append(
                {
                    "test_node_id": node,
                    "purpose": purpose,
                    "result": "PASS",
                    "test_source_sha256": test_sha,
                    "evidence_generated_at": created_at,
                    "network_used": False,
                    "production_database_used": False,
                    "credential_content_read": False,
                }
            )
        result[unit["unit_id"]] = records
    return result


def synthetic_test_evidence(
    policy: dict[str, Any], created_at: str
) -> dict[str, list[dict[str, Any]]]:
    """Test-only evidence shape; production generation uses actual pytest runs."""

    result: dict[str, list[dict[str, Any]]] = {}
    for unit in policy["review_units"]:
        result[unit["unit_id"]] = [
            {
                "test_node_id": node,
                "purpose": purpose,
                "result": "PASS",
                "test_source_sha256": sha256_bytes(
                    secure_repo_bytes(REPO_ROOT / node.split("::", 1)[0])
                ),
                "evidence_generated_at": created_at,
                "network_used": False,
                "production_database_used": False,
                "credential_content_read": False,
            }
            for node, purpose in unit["test_nodes"]
        ]
    return result


def build_documents(
    candidate_root: Path,
    *,
    created_at: str,
    test_evidence: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    policy = load_json_bytes(secure_repo_bytes(POLICY_PATH), "REVIEW_POLICY_INVALID")
    if git_object_type(policy["baseline_commit"]) != "commit":
        raise ReviewBundleBlocked("BASELINE_OBJECT_NOT_COMMIT")

    candidate_path = candidate_root / "candidate-manifest.json"
    closure_path = candidate_root / "dependency-closure.json"
    downstream_path = candidate_root / "downstream-rebinding-plan.json"
    validation = validate_candidate_files(
        candidate_path, closure_path, downstream_path
    )
    try:
        candidate_snapshot = read_secure_release_file(
            candidate_path,
            allowed_root=candidate_root,
            expected_sha256=policy["candidate_manifest_sha256"],
        )
        closure_snapshot = read_secure_release_file(
            closure_path, allowed_root=candidate_root
        )
        downstream_snapshot = read_secure_release_file(
            downstream_path, allowed_root=candidate_root
        )
    except ReleaseFileError as exc:
        raise ReviewBundleBlocked(exc.code) from exc
    candidate = load_json_bytes(candidate_snapshot.data, "CANDIDATE_INVALID")
    downstream = load_json_bytes(downstream_snapshot.data, "DOWNSTREAM_INVALID")
    production_bytes = secure_repo_bytes(
        REPO_ROOT / policy["production_manifest"]["path"],
        expected_sha256=policy["production_manifest"]["sha256"],
    )

    evidence = test_evidence or collect_test_evidence(policy, created_at)
    diff_documents: dict[str, dict[str, Any]] = {}
    for relative, binding in policy["source_contract"].items():
        diff_documents[relative] = source_diff_document(
            relative=relative,
            baseline_commit=policy["baseline_commit"],
            expected_baseline_sha=binding["baseline_sha256"],
            expected_current_sha=binding["current_sha256"],
        )

    source_to_diff_path = {
        relative: "source-diffs/" + relative.replace("/", "__") + ".diff.json"
        for relative in diff_documents
    }
    payloads: dict[str, bytes] = {
        "candidate-manifest.json": candidate_snapshot.data,
        "dependency-closure.json": closure_snapshot.data,
        "downstream-rebinding-plan.json": downstream_snapshot.data,
    }
    validation_document = {
        "schema_version": "slack_worker_candidate_validation_result_schema_candidate_v1",
        "schema_status": "SCHEMA_CANDIDATE_NOT_ACTIVE",
        **validation,
        "validated_at": created_at,
        "validated_candidate_source_path": str(candidate_path),
        "persistent_snapshot_path": "candidate-manifest.json",
        "validator_path": "scripts/validate_slack_worker_release_manifest_candidate.py",
        "validator_sha256": sha256_bytes(
            secure_repo_bytes(
                REPO_ROOT / "scripts/validate_slack_worker_release_manifest_candidate.py"
            )
        ),
        "release_status": "CANDIDATE_NOT_APPROVED",
        "review_bundle_status": "READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
        "production_release": False,
        "production_manifest_replacement_allowed": False,
    }
    payloads["candidate-validation-result.json"] = pretty_bytes(validation_document)
    for relative, document in diff_documents.items():
        payloads[source_to_diff_path[relative]] = pretty_bytes(document)

    packet_paths: dict[str, str] = {}
    template_paths: dict[str, str] = {}
    for unit in policy["review_units"]:
        unit_id = unit["unit_id"]
        packet_path = f"review-units/{unit_id}.review-packet.json"
        packet_paths[unit_id] = packet_path
        sources = [
            {
                "path": relative,
                "old_sha256": policy["source_contract"][relative][
                    "baseline_sha256"
                ],
                "current_sha256": policy["source_contract"][relative][
                    "current_sha256"
                ],
                "diff_path": source_to_diff_path[relative],
                "diff_sha256": sha256_bytes(
                    payloads[source_to_diff_path[relative]]
                ),
            }
            for relative in unit["sources"]
        ]
        packet = {
            "schema_version": "slack_worker_review_unit_packet_schema_candidate_v1",
            "schema_status": "SCHEMA_CANDIDATE_NOT_ACTIVE",
            "release_status": "CANDIDATE_NOT_APPROVED",
            "review_bundle_status": "READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
            "candidate_id": candidate["candidate_id"],
            "unit_id": unit_id,
            "change_category": unit["change_category"],
            "sources": sources,
            "intended_behavior": unit["intended_behavior"],
            "changed_public_runtime_interfaces": unit[
                "changed_public_runtime_interfaces"
            ],
            "review_dimensions": unit["review_dimensions"],
            "rollback_considerations": unit["rollback_considerations"],
            "related_tests": evidence[unit_id],
            "security_impact": unit["security_impact"],
            "data_integrity_impact": unit["data_integrity_impact"],
            "performance_impact": unit["performance_impact"],
            "known_limitations": unit["known_limitations"],
            "unresolved_issues": unit["unresolved_issues"],
            "test_evidence_gaps": unit["test_evidence_gaps"],
            "risk_matrix": unit["risk_matrix"],
            "human_review_checklist": unit["human_review_checklist"],
            "human_decision_required": True,
            "recommended_decision": "REVIEW_REQUIRED",
            "review_status": "NOT_REVIEWED",
            "approval_status": "NOT_ISSUED",
            "production_release": False,
            "production_approval_created": False,
            "deployment_allowed": False,
            "runtime_execution_allowed": False,
            "production_manifest_replacement_allowed": False,
        }
        payloads[packet_path] = pretty_bytes(packet)
        packet_sha = sha256_bytes(payloads[packet_path])
        template_path = f"decision-templates/{unit_id}.decision-template.json"
        template_paths[unit_id] = template_path
        template = {
            "schema_version": "slack_worker_review_decision_template_schema_candidate_v1",
            "schema_status": "SCHEMA_CANDIDATE_NOT_ACTIVE",
            "review_unit_id": unit_id,
            "candidate_id": candidate["candidate_id"],
            "review_packet_sha256": packet_sha,
            "decision": None,
            "allowed_decisions": ["APPROVE", "REJECT", "HOLD"],
            "reviewer": None,
            "reviewed_at": None,
            "reason": None,
            "conditions": [],
            "expiration": None,
            "single_use": True,
            "approval_issued": False,
            "production_manifest_update_allowed": False,
            "deployment_allowed": False,
        }
        payloads[template_path] = pretty_bytes(template)

    summary = (
        "# Slack Worker Release Rebinding Review Bundle\n\n"
        "Status: `READY_FOR_HUMAN_REVIEW_NOT_APPROVED`  \n"
        "Release status: `CANDIDATE_NOT_APPROVED`  \n"
        "Production release: `false`  \n"
        "Production approval created: `false`  \n"
        "Deployment/runtime execution allowed: `false` / `false`\n\n"
        f"Candidate: `{candidate['candidate_id']}`  \n"
        f"Candidate SHA-256: `{candidate_snapshot.sha256}`  \n"
        f"Baseline commit: `{policy['baseline_commit']}`\n\n"
        "The three review units are independent. Decision templates are blank; "
        "this bundle does not constitute approval. Review the complete five "
        "unified diffs, risk matrices, evidence gaps, and checklists before "
        "recording any future human decision.\n"
    ).encode("utf-8")
    payloads["human-review-summary.md"] = summary

    bundle_id = (
        "slack-worker-release-rebinding-review-SCHEMA-CANDIDATE-"
        + candidate_snapshot.sha256[:12]
    )
    review_unit_hashes = {
        unit: sha256_bytes(payloads[path]) for unit, path in packet_paths.items()
    }
    diff_hashes = {
        relative: sha256_bytes(payloads[path])
        for relative, path in source_to_diff_path.items()
    }
    template_hashes = {
        unit: sha256_bytes(payloads[path]) for unit, path in template_paths.items()
    }
    expected_files = sorted([*payloads, "review-bundle-manifest.json"])
    manifest = {
        "schema_version": "slack_worker_release_review_bundle_schema_candidate_v1",
        "schema_status": "SCHEMA_CANDIDATE_NOT_ACTIVE",
        "review_bundle_id": bundle_id,
        "review_bundle_status": "READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "candidate_id": candidate["candidate_id"],
        "candidate_manifest_path": "candidate-manifest.json",
        "candidate_manifest_sha256": candidate_snapshot.sha256,
        "candidate_validator_result_path": "candidate-validation-result.json",
        "candidate_validator_result_sha256": sha256_bytes(
            payloads["candidate-validation-result.json"]
        ),
        "dependency_closure_path": "dependency-closure.json",
        "dependency_closure_sha256": closure_snapshot.sha256,
        "downstream_plan_path": "downstream-rebinding-plan.json",
        "downstream_plan_sha256": downstream_snapshot.sha256,
        "downstream_plan_content_sha256": downstream[
            "downstream_rebinding_plan_sha256"
        ],
        "production_manifest_path": policy["production_manifest"]["path"],
        "production_manifest_sha256": sha256_bytes(production_bytes),
        "baseline_commit": policy["baseline_commit"],
        "runtime_closure_source_count": 17,
        "review_unit_count": 3,
        "review_unit_paths": packet_paths,
        "review_unit_sha256": review_unit_hashes,
        "diff_paths": source_to_diff_path,
        "diff_sha256": diff_hashes,
        "decision_template_paths": template_paths,
        "decision_template_sha256": template_hashes,
        "immutable_historical_evidence_count": 2,
        "production_release": False,
        "production_approval_created": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "production_manifest_replacement_allowed": False,
        "human_decision_required": True,
        "human_decision_recorded": False,
        "created_at": created_at,
        "generated_by": {
            "path": "scripts/build_slack_worker_release_rebinding_review_bundle.py",
            "sha256": sha256_bytes(
                secure_repo_bytes(
                    REPO_ROOT
                    / "scripts/build_slack_worker_release_rebinding_review_bundle.py"
                )
            ),
        },
        "update_policy": policy["governance"]["update_policy"],
        "expected_files": expected_files,
        "human_summary_path": "human-review-summary.md",
        "human_summary_sha256": sha256_bytes(summary),
    }
    payloads["review-bundle-manifest.json"] = pretty_bytes(manifest)
    return {
        "policy": policy,
        "candidate": candidate,
        "manifest": manifest,
        "payloads": payloads,
    }


def validate_output_root(
    path: Path,
    candidate_id: str,
    *,
    review_request_root: Path = REVIEW_REQUEST_ROOT,
) -> Path:
    absolute = path.absolute()
    expected = review_request_root / candidate_id
    if absolute != expected.absolute():
        raise ReviewBundleBlocked("REVIEW_BUNDLE_OUTPUT_PATH_INVALID")
    if absolute.exists() or os.path.lexists(absolute):
        raise ReviewBundleBlocked("REVIEW_BUNDLE_OVERWRITE_REJECTED")
    return absolute


def write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def generate(
    candidate_root: Path,
    *,
    created_at: str,
    output_root: Path | None = None,
    test_evidence: dict[str, list[dict[str, Any]]] | None = None,
    review_request_root: Path = REVIEW_REQUEST_ROOT,
) -> dict[str, Any]:
    documents = build_documents(
        candidate_root, created_at=created_at, test_evidence=test_evidence
    )
    candidate_id = documents["candidate"]["candidate_id"]
    destination = validate_output_root(
        output_root or review_request_root / candidate_id,
        candidate_id,
        review_request_root=review_request_root,
    )
    destination.mkdir(parents=True, mode=0o700)
    for relative, payload in documents["payloads"].items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_exclusive(target, payload)
    for directory in sorted(
        {destination, *(path.parent for path in destination.rglob("*"))},
        key=lambda value: len(value.parts),
        reverse=True,
    ):
        descriptor = os.open(directory, os.O_RDONLY | os.O_CLOEXEC)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    manifest_path = destination / "review-bundle-manifest.json"
    return {
        "result": "READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
        "review_bundle_root": str(destination),
        "review_bundle_manifest": str(manifest_path),
        "review_bundle_manifest_sha256": sha256_bytes(
            documents["payloads"]["review-bundle-manifest.json"]
        ),
        "candidate_id": candidate_id,
        "candidate_manifest_sha256": documents["manifest"][
            "candidate_manifest_sha256"
        ],
        "review_unit_count": 3,
        "source_diff_count": 5,
        "decision_template_count": 3,
        "production_approval_created": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--created-at")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    created_at = args.created_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    try:
        result = generate(
            args.candidate_root,
            created_at=created_at,
            output_root=args.output_root,
        )
    except ReviewBundleBlocked as exc:
        print(f"SLACK_WORKER_RELEASE_REVIEW_BUNDLE: BLOCKED ({exc})")
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
