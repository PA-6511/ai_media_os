#!/usr/bin/env python3
"""Validate a non-deployable Slack worker release candidate below /tmp."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts import build_slack_worker_release_manifest_candidate as builder
    from scripts.lib.secure_release_file_reader import (
        ReleaseFileError,
        read_secure_release_file,
        resolve_secure_source_path,
    )
    from scripts.validate_slack_worker_release_bundle_contract import (
        load_production_manifest,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    import build_slack_worker_release_manifest_candidate as builder  # type: ignore
    from lib.secure_release_file_reader import (  # type: ignore[no-redef]
        ReleaseFileError,
        read_secure_release_file,
        resolve_secure_source_path,
    )
    from validate_slack_worker_release_bundle_contract import (  # type: ignore
        load_production_manifest,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = Path("/tmp").resolve()
EXPECTED_REVIEW_UNITS = {
    "UNIT_DB_SAFETY": {
        "app/db/access_guard.py",
        "app/db/config.py",
        "app/db/session.py",
    },
    "UNIT_WORKFLOW_STATE": {
        "app/db/repositories/workflow_state_repository.py",
    },
    "UNIT_SLACK_RUNTIME": {"scripts/run_slack_approval_socket.py"},
}
EXPECTED_CHANGED_SOURCES = set().union(*EXPECTED_REVIEW_UNITS.values())


class CandidateValidationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def fail(code: str) -> None:
    raise CandidateValidationError(code)


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail("CANDIDATE_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def decode_json(data: bytes, code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateValidationError(code) from exc
    if not isinstance(value, dict):
        fail(code)
    return value


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(builder.canonical_bytes(value)).hexdigest()


def validate_candidate_document(
    candidate: dict[str, Any],
    *,
    production_release_id: str,
) -> None:
    """Validate the semantic contract before any approval interpretation."""

    if candidate.get("schema_version") != "slack_worker_release_manifest_candidate_v1":
        fail("CANDIDATE_SCHEMA_INVALID")
    if candidate.get("release_status") != "CANDIDATE_NOT_APPROVED":
        fail("CANDIDATE_RELEASE_STATUS_INVALID")
    if candidate.get("deployment_allowed") is not False:
        fail("CANDIDATE_DEPLOYMENT_MUST_BE_FALSE")
    if candidate.get("runtime_execution_allowed") is not False:
        fail("CANDIDATE_RUNTIME_EXECUTION_MUST_BE_FALSE")
    if candidate.get("production_approval_created") is not False:
        fail("CANDIDATE_PRODUCTION_APPROVAL_MUST_BE_FALSE")
    if candidate.get("formal_release_id_issued") is not False:
        fail("CANDIDATE_FORMAL_RELEASE_ID_MUST_BE_FALSE")

    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str):
        fail("CANDIDATE_ID_INVALID")
    normalized_id = candidate_id.upper().replace("_", "-")
    if "CANDIDATE" not in normalized_id or "NOT-APPROVED" not in normalized_id:
        fail("CANDIDATE_ID_INVALID")
    if candidate_id == production_release_id or production_release_id in candidate_id:
        fail("CANDIDATE_PRODUCTION_ID_IMPERSONATION")

    sources = candidate.get("source_files")
    if not isinstance(sources, list):
        fail("CANDIDATE_SOURCE_LIST_INVALID")
    paths = [item.get("path") for item in sources if isinstance(item, dict)]
    if len(paths) != len(sources) or any(not isinstance(path, str) for path in paths):
        fail("CANDIDATE_SOURCE_LIST_INVALID")
    if len(paths) != len(set(paths)):
        fail("CANDIDATE_DUPLICATE_SOURCE_PATH")
    if paths != sorted(paths):
        fail("CANDIDATE_SOURCE_ORDER_INVALID")
    if candidate.get("source_file_count") != 17 or len(paths) != 17:
        fail("CANDIDATE_SOURCE_COUNT_INVALID")
    if "app/db/access_guard.py" not in paths:
        fail("CANDIDATE_ACCESS_GUARD_MISSING")
    if candidate.get("unresolved_dynamic_dependencies") != []:
        fail("CANDIDATE_UNRESOLVED_DEPENDENCY")

    units = candidate.get("review_units")
    if not isinstance(units, list) or len(units) != 3:
        fail("CANDIDATE_REVIEW_UNIT_COUNT_INVALID")
    by_name = {
        unit.get("unit"): unit for unit in units if isinstance(unit, dict)
    }
    if set(by_name) != set(EXPECTED_REVIEW_UNITS):
        fail("CANDIDATE_REVIEW_UNIT_SET_INVALID")
    assigned: list[str] = []
    for name, expected_sources in EXPECTED_REVIEW_UNITS.items():
        unit = by_name[name]
        actual_sources = unit.get("sources")
        if not isinstance(actual_sources, list) or set(actual_sources) != expected_sources:
            fail(f"CANDIDATE_REVIEW_UNIT_SOURCE_INVALID:{name}")
        assigned.extend(actual_sources)
        if unit.get("approval_status") != "NOT_APPROVED":
            fail(f"CANDIDATE_REVIEW_UNIT_APPROVAL_INVALID:{name}")
        if unit.get("review_required") is not True:
            fail(f"CANDIDATE_REVIEW_REQUIRED_INVALID:{name}")
        for field in ("purpose", "security_impact", "runtime_impact"):
            if not isinstance(unit.get(field), str) or not unit[field].strip():
                fail(f"CANDIDATE_REVIEW_IMPACT_MISSING:{name}:{field}")
    if len(assigned) != len(set(assigned)) or set(assigned) != EXPECTED_CHANGED_SOURCES:
        fail("CANDIDATE_REVIEW_SOURCE_PARTITION_INVALID")

    audit = candidate.get("source_audit")
    if not isinstance(audit, list):
        fail("CANDIDATE_SOURCE_AUDIT_INVALID")
    changed = {
        item.get("path")
        for item in audit
        if isinstance(item, dict) and item.get("change") in {"MODIFIED", "ADDED"}
    }
    unchanged = {
        item.get("path")
        for item in audit
        if isinstance(item, dict) and item.get("change") == "UNCHANGED"
    }
    if changed != EXPECTED_CHANGED_SOURCES or len(unchanged) != 12:
        fail("CANDIDATE_SOURCE_CHANGE_CLASSIFICATION_INVALID")
    if unchanged & set(assigned):
        fail("CANDIDATE_UNCHANGED_SOURCE_REVIEW_MISCLASSIFIED")

    content = {
        key: value
        for key, value in candidate.items()
        if key not in {"candidate_id", "candidate_manifest_content_sha256"}
    }
    content_sha = canonical_sha256(content)
    if candidate.get("candidate_manifest_content_sha256") != content_sha:
        fail("CANDIDATE_CONTENT_SHA_INVALID")
    if not candidate_id.endswith(content_sha[:12]):
        fail("CANDIDATE_ID_DIGEST_BINDING_INVALID")


def graph_is_acyclic(artifacts: list[dict[str, Any]]) -> bool:
    nodes = {item["path"] for item in artifacts}
    indegree = {path: 0 for path in nodes}
    outgoing = {path: set() for path in nodes}
    for item in artifacts:
        target = item["path"]
        for upstream in item.get("upstream_dependencies", []):
            if upstream in nodes and target not in outgoing[upstream]:
                outgoing[upstream].add(target)
                indegree[target] += 1
    queue = sorted(path for path, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        path = queue.pop(0)
        visited += 1
        for target in sorted(outgoing[path]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
                queue.sort()
    return visited == len(nodes)


def validate_candidate_files(
    candidate_path: Path,
    closure_path: Path,
    downstream_path: Path,
    *,
    repository_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    root = candidate_path.absolute().parent
    try:
        root.relative_to(TMP_ROOT)
    except ValueError as exc:
        raise CandidateValidationError("CANDIDATE_ROOT_MUST_BE_BELOW_TMP") from exc
    if root == TMP_ROOT:
        fail("CANDIDATE_ROOT_MUST_BE_EXPLICIT")
    if candidate_path.absolute() != root / "candidate-manifest.json":
        fail("CANDIDATE_PATH_INVALID")
    if closure_path.absolute() != root / "dependency-closure.json":
        fail("CANDIDATE_CLOSURE_PATH_INVALID")
    if downstream_path.absolute() != root / "downstream-rebinding-plan.json":
        fail("CANDIDATE_DOWNSTREAM_PATH_INVALID")

    try:
        candidate_snapshot = read_secure_release_file(
            candidate_path, allowed_root=root, expected_path=root / candidate_path.name
        )
        closure_snapshot = read_secure_release_file(
            closure_path, allowed_root=root, expected_path=root / closure_path.name
        )
        downstream_snapshot = read_secure_release_file(
            downstream_path, allowed_root=root, expected_path=root / downstream_path.name
        )
    except ReleaseFileError as exc:
        raise CandidateValidationError(exc.code) from exc

    candidate = decode_json(candidate_snapshot.data, "CANDIDATE_JSON_INVALID")
    closure = decode_json(closure_snapshot.data, "CANDIDATE_CLOSURE_JSON_INVALID")
    plan = decode_json(downstream_snapshot.data, "CANDIDATE_DOWNSTREAM_JSON_INVALID")

    lowered_candidate_bytes = candidate_snapshot.data.lower()
    for forbidden in (
        b"slack_bot_token",
        b"slack_app_token",
        b"credential_value",
        b"secret_value",
        b"authorization: bearer",
        b"xoxb-",
        b"xapp-",
    ):
        if forbidden in lowered_candidate_bytes:
            fail("CANDIDATE_SENSITIVE_LITERAL_REJECTED")

    production, _production_sha = load_production_manifest(
        repository_root,
        repository_root / "config/slack_worker_release_source_manifest.json",
    )
    validate_candidate_document(
        candidate, production_release_id=production["release_id_candidate"]
    )

    if closure.get("source_count") != 17:
        fail("CANDIDATE_CLOSURE_SOURCE_COUNT_INVALID")
    if closure.get("unresolved_dynamic_dependencies") != []:
        fail("CANDIDATE_CLOSURE_UNRESOLVED_DEPENDENCY")
    closure_content = {
        key: value
        for key, value in closure.items()
        if key != "dependency_closure_sha256"
    }
    if closure.get("dependency_closure_sha256") != canonical_sha256(closure_content):
        fail("CANDIDATE_CLOSURE_SHA_INVALID")
    if candidate.get("dependency_closure_sha256") != closure.get(
        "dependency_closure_sha256"
    ):
        fail("CANDIDATE_CLOSURE_BINDING_INVALID")

    candidate_paths = {item["path"] for item in candidate["source_files"]}
    closure_paths = {item["path"] for item in closure["sources"]}
    production_paths = {item["path"] for item in production["source_files"]}
    if candidate_paths != closure_paths:
        fail("CANDIDATE_CLOSURE_SOURCE_SET_INVALID")
    if len(closure_paths - production_paths) != 1:
        fail("PRODUCTION_UNRECORDED_REQUIRED_SOURCE_COUNT_INVALID")

    for item in candidate["source_files"]:
        try:
            relative, source_path = resolve_secure_source_path(
                repository_root, item["path"]
            )
            snapshot = read_secure_release_file(
                source_path,
                allowed_root=repository_root,
                expected_sha256=item["sha256"],
            )
        except ReleaseFileError as exc:
            raise CandidateValidationError(f"{exc.code}:{item['path']}") from exc
        if snapshot.size != item["size"] or relative != item["path"]:
            fail(f"CANDIDATE_SOURCE_METADATA_INVALID:{item['path']}")

    if plan.get("schema_version") != (
        "slack_worker_downstream_rebinding_plan_candidate_v1"
    ):
        fail("CANDIDATE_DOWNSTREAM_SCHEMA_INVALID")
    if plan.get("release_status") != "CANDIDATE_NOT_APPROVED":
        fail("CANDIDATE_DOWNSTREAM_STATUS_INVALID")
    if plan.get("deployment_allowed") is not False or plan.get(
        "runtime_execution_allowed"
    ) is not False:
        fail("CANDIDATE_DOWNSTREAM_EXECUTION_BOUNDARY_INVALID")
    plan_content = {
        key: value
        for key, value in plan.items()
        if key != "downstream_rebinding_plan_sha256"
    }
    if plan.get("downstream_rebinding_plan_sha256") != canonical_sha256(plan_content):
        fail("CANDIDATE_DOWNSTREAM_SHA_INVALID")
    if plan.get("candidate_manifest_sha256") != candidate_snapshot.sha256:
        fail("CANDIDATE_DOWNSTREAM_MANIFEST_BINDING_INVALID")
    artifacts = plan.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 21:
        fail("CANDIDATE_DOWNSTREAM_ARTIFACT_COUNT_INVALID")
    mutable = [item for item in artifacts if item.get("mutable") is True]
    immutable = [item for item in artifacts if item.get("mutable") is False]
    if len(mutable) != 19 or len(immutable) != 2:
        fail("CANDIDATE_DOWNSTREAM_MUTABILITY_COUNT_INVALID")
    if not graph_is_acyclic(artifacts) or plan.get("circular_dependency_detected") is not False:
        fail("CANDIDATE_DOWNSTREAM_GRAPH_CYCLE")
    order_by_path = {
        item["path"]: item.get("required_update_order") for item in artifacts
    }
    if not all(isinstance(value, int) for value in order_by_path.values()) or sorted(
        order_by_path.values()
    ) != list(range(1, 22)):
        fail("CANDIDATE_DOWNSTREAM_UPDATE_ORDER_INVALID")
    for item in artifacts:
        if any(
            upstream in order_by_path
            and order_by_path[upstream] >= order_by_path[item["path"]]
            for upstream in item.get("upstream_dependencies", [])
        ):
            fail("CANDIDATE_DOWNSTREAM_UPDATE_ORDER_INVALID")
    if any(item.get("atomic_write_requirement") is not True for item in mutable):
        fail("CANDIDATE_DOWNSTREAM_ATOMIC_WRITE_INVALID")
    if any(not isinstance(item.get("rollback_source"), dict) for item in artifacts):
        fail("CANDIDATE_DOWNSTREAM_ROLLBACK_INVALID")
    if any(
        item.get("candidate_action")
        != "PRESERVE_IMMUTABLE_HISTORICAL_EVIDENCE"
        or item.get("resulting_candidate_artifact_sha256") is not None
        for item in immutable
    ):
        fail("CANDIDATE_IMMUTABLE_EVIDENCE_EXCLUSION_INVALID")
    graph_binding = candidate.get("downstream_rebinding_plan_binding")
    if not isinstance(graph_binding, dict) or graph_binding.get(
        "rebinding_graph_contract_sha256"
    ) != plan.get("rebinding_graph_contract_sha256"):
        fail("CANDIDATE_DOWNSTREAM_GRAPH_BINDING_INVALID")

    regenerated = builder.build_candidate_documents(repository_root)
    if regenerated["candidate_manifest_bytes"] != candidate_snapshot.data:
        fail("CANDIDATE_NOT_CURRENT_DETERMINISTIC_BUILD")
    if regenerated["dependency_closure"] != closure:
        fail("CANDIDATE_CLOSURE_NOT_CURRENT_DETERMINISTIC_BUILD")
    if regenerated["downstream_rebinding_plan"] != plan:
        fail("CANDIDATE_DOWNSTREAM_NOT_CURRENT_DETERMINISTIC_BUILD")

    return {
        "result": "PASS_CANDIDATE_NOT_APPROVED",
        "candidate_manifest": str(candidate_path),
        "candidate_manifest_sha256": candidate_snapshot.sha256,
        "candidate_release_status": candidate["release_status"],
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "production_approval_created": False,
        "dependency_closure_source_count": 17,
        "unresolved_dynamic_dependencies": 0,
        "production_unrecorded_required_source_count": 1,
        "candidate_unrecorded_required_source_count": 0,
        "review_unit_count": 3,
        "downstream_candidate_count": 19,
        "immutable_evidence_excluded": 2,
        "rebinding_graph_acyclic": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--downstream-plan", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate_candidate_files(
            args.candidate, args.closure, args.downstream_plan
        )
    except CandidateValidationError as exc:
        print(f"SLACK_WORKER_RELEASE_CANDIDATE_VALIDATION: FAIL ({exc.code})")
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
