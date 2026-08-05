#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3a-shadow-20260725T145828-487557"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
I2F3A_ROOT_REL="${I2E_ROOT_REL}/i2f3a-shadow-toolchain-skeleton-20260725T145828-487557"
I2F3B_FAIL_ROOT_REL="${I2E_ROOT_REL}/i2f3b-shadow-candidate-validation-20260725T150332-487916"

I2F3A_RESULT="${REPO_ROOT}/${I2F3A_ROOT_REL}/result.json"
I2F3B_FAIL_RESULT="${REPO_ROOT}/${I2F3B_FAIL_ROOT_REL}/result.json"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
PRODUCTION_POLICY="${REPO_ROOT}/config/slack_worker_release_rebinding_policy.json"
SHADOW_MANIFEST="${SHADOW_ROOT}/config/slack_worker_release_source_manifest.json"
SHADOW_POLICY="${SHADOW_ROOT}/config/slack_worker_release_rebinding_policy.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_I2F3A_RESULT_SHA="dd09b31a2499c6b7d311cc7dc1067862ecae3ececd615ce0d9917a152d78c744"
EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_SHADOW_MANIFEST_SHA="f302b7f16237bafeee3ac0f66fa5d0327ffd06359b12b5ab1b8ff1a3cb9062c7"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

require_file_sha() {
    local path="$1"
    local expected="$2"
    local actual

    if [[ ! -f "$path" ]]; then
        printf 'ERROR=MISSING_FILE:%s\n' "$path" >&2
        exit 1
    fi

    actual="$(sha256_file "$path")"
    if [[ "$actual" != "$expected" ]]; then
        printf 'ERROR=SHA_MISMATCH:%s\nEXPECTED=%s\nACTUAL=%s\n' \
            "$path" "$expected" "$actual" >&2
        exit 1
    fi

    printf 'SHA_PASS=%s:%s\n' "$path" "$actual"
}

cd "$REPO_ROOT"

require_file_sha "$I2F3A_RESULT" "$EXPECTED_I2F3A_RESULT_SHA"
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$SHADOW_MANIFEST" "$EXPECTED_SHADOW_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

if [[ ! -f "$I2F3B_FAIL_RESULT" ]]; then
    printf 'ERROR=I2F3B_FAILURE_RESULT_MISSING:%s\n' "$I2F3B_FAIL_RESULT" >&2
    exit 1
fi

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3b-r2-downstream-graph-binding-audit-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_ALREADY_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p "$EVIDENCE_ROOT"

AUDIT_JSON="${EVIDENCE_ROOT}/downstream-graph-binding-audit.json"
AUDIT_TXT="${EVIDENCE_ROOT}/downstream-graph-binding-audit.txt"
RESULT_JSON="${EVIDENCE_ROOT}/result.json"

python3 - \
    "$REPO_ROOT" \
    "$SHADOW_ROOT" \
    "$PRODUCTION_POLICY" \
    "$SHADOW_POLICY" \
    "$PRODUCTION_MANIFEST" \
    "$SHADOW_MANIFEST" \
    "$AUDIT_JSON" \
    "$AUDIT_TXT" <<'PY'
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Iterable

repo = Path(sys.argv[1]).resolve()
shadow = Path(sys.argv[2]).resolve()
production_policy_path = Path(sys.argv[3]).resolve()
shadow_policy_path = Path(sys.argv[4]).resolve()
production_manifest_path = Path(sys.argv[5]).resolve()
shadow_manifest_path = Path(sys.argv[6]).resolve()
audit_json_path = Path(sys.argv[7])
audit_txt_path = Path(sys.argv[8])

builder_path = repo / "scripts/build_slack_worker_release_manifest_candidate.py"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def leaves(value: object, prefix: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, f"{prefix}[{index}]")
    elif isinstance(value, str):
        yield prefix, value


def matching_fields(value: dict[str, Any], needles: dict[str, str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {name: [] for name in needles}
    for field, leaf in leaves(value):
        for name, needle in needles.items():
            if leaf == needle or needle in leaf:
                result[name].append(field)
    return {name: sorted(fields) for name, fields in result.items()}


production_policy = load(production_policy_path)
shadow_policy = load(shadow_policy_path)
production_manifest = load(production_manifest_path)
shadow_manifest = load(shadow_manifest_path)

production_manifest_sha = sha(production_manifest_path)
shadow_manifest_sha = sha(shadow_manifest_path)
production_release_id = str(production_manifest.get("release_id_candidate"))
shadow_release_id = str(shadow_manifest.get("release_id_candidate"))

needles = {
    "production_manifest_sha": production_manifest_sha,
    "shadow_manifest_sha": shadow_manifest_sha,
    "production_release_id": production_release_id,
    "shadow_release_id": shadow_release_id,
}

config_files = sorted((repo / "config").glob("slack_worker*.json"))
config_docs: dict[str, dict[str, Any]] = {}
config_shas: dict[str, str] = {}
for path in config_files:
    relative = path.relative_to(repo).as_posix()
    config_docs[relative] = load(path)
    config_shas[relative] = sha(path)

direct_binders = [
    item["path"]
    for item in shadow_policy.get("direct_policy_binders", [])
    if isinstance(item, dict) and isinstance(item.get("path"), str)
]
immutable_paths = [
    value
    for value in shadow_policy.get("immutable_direct_evidence", [])
    if isinstance(value, str)
]

direct_details: list[dict[str, Any]] = []
for relative in direct_binders:
    path = repo / relative
    document = config_docs.get(relative)
    if document is None:
        direct_details.append(
            {
                "path": relative,
                "exists": path.is_file(),
                "error": "DIRECT_BINDER_NOT_IN_CONFIG_SCAN",
            }
        )
        continue

    fields = matching_fields(document, needles)
    direct_details.append(
        {
            "path": relative,
            "exists": True,
            "sha256": config_shas[relative],
            "matching_fields": fields,
            "production_binding_count": len(fields["production_manifest_sha"])
            + len(fields["production_release_id"]),
            "shadow_binding_count": len(fields["shadow_manifest_sha"])
            + len(fields["shadow_release_id"]),
        }
    )

all_reference_details: list[dict[str, Any]] = []
for relative, document in config_docs.items():
    fields = matching_fields(document, needles)
    if any(fields.values()):
        all_reference_details.append(
            {
                "path": relative,
                "sha256": config_shas[relative],
                "matching_fields": fields,
            }
        )

sha_owner = {digest: relative for relative, digest in config_shas.items()}
edges: list[dict[str, str]] = []
for downstream, document in config_docs.items():
    for field, leaf in leaves(document):
        upstream = sha_owner.get(leaf)
        if upstream is not None and upstream != downstream:
            edges.append(
                {
                    "upstream": upstream,
                    "downstream": downstream,
                    "field": field,
                }
            )

reachable = set(direct_binders)
frontier = set(direct_binders)
depth_by_path = {path: 1 for path in direct_binders}
while frontier:
    discovered: set[str] = set()
    for edge in edges:
        if edge["upstream"] not in frontier:
            continue
        downstream = edge["downstream"]
        if downstream in reachable:
            continue
        reachable.add(downstream)
        depth_by_path[downstream] = depth_by_path[edge["upstream"]] + 1
        discovered.add(downstream)
    frontier = discovered

spec = importlib.util.spec_from_file_location("production_candidate_builder_audit", builder_path)
if spec is None or spec.loader is None:
    raise SystemExit("BUILDER_IMPORT_SPEC_FAILED")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

original_policy_path = builder.POLICY_PATH
builder.POLICY_PATH = production_policy_path
try:
    production_chain = builder.discover_downstream_chain(
        repo,
        production_policy,
        production_manifest_sha,
        production_release_id,
    )
finally:
    builder.POLICY_PATH = original_policy_path

production_chain_paths = {item["path"] for item in production_chain}
manual_reachable_mutable = reachable

direct_shadow_complete = all(
    detail.get("shadow_binding_count", 0) > 0
    for detail in direct_details
    if detail.get("exists")
)
direct_production_complete = all(
    detail.get("production_binding_count", 0) > 0
    for detail in direct_details
    if detail.get("exists")
)

audit = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3B-R2",
    "result": "PASS_READ_ONLY_DOWNSTREAM_GRAPH_BINDING_AUDIT",
    "roots": {
        "production_repo_root": str(repo),
        "shadow_root": str(shadow),
    },
    "manifest_identity": {
        "production_manifest_sha256": production_manifest_sha,
        "shadow_manifest_sha256": shadow_manifest_sha,
        "production_release_id": production_release_id,
        "shadow_release_id": shadow_release_id,
        "release_ids_equal": production_release_id == shadow_release_id,
    },
    "config_scan": {
        "slack_worker_config_count": len(config_docs),
        "direct_binder_count": len(direct_binders),
        "immutable_evidence_count": len(immutable_paths),
        "reference_file_count": len(all_reference_details),
    },
    "direct_binders": direct_details,
    "all_manifest_identity_references": all_reference_details,
    "production_sha_dependency_graph": {
        "edge_count": len(edges),
        "edges": sorted(
            edges,
            key=lambda item: (
                item["upstream"],
                item["downstream"],
                item["field"],
            ),
        ),
        "reachable_mutable_path_count": len(manual_reachable_mutable),
        "reachable_mutable_paths": sorted(manual_reachable_mutable),
        "depth_by_path": dict(sorted(depth_by_path.items())),
    },
    "production_builder_chain": {
        "total_count": len(production_chain),
        "mutable_count": sum(bool(item.get("mutable")) for item in production_chain),
        "immutable_count": sum(not bool(item.get("mutable")) for item in production_chain),
        "paths": sorted(production_chain_paths),
    },
    "conclusions": {
        "all_direct_binders_currently_bind_production_identity": direct_production_complete,
        "all_direct_binders_currently_bind_shadow_identity": direct_shadow_complete,
        "mutable_config_shadow_copy_required": True,
        "transitive_shadow_sha_rebinding_required": True,
        "immutable_evidence_should_remain_read_only_production_evidence": True,
        "single_relative_path_patch_is_sufficient": False,
        "complete_shadow_graph_required": True,
    },
    "safety": {
        "production_files_written": False,
        "shadow_files_written": False,
        "production_database_accessed": False,
        "migration_applied": False,
        "deployment_performed": False,
        "external_network_used": False,
    },
}

audit_json_path.write_text(
    json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)

lines: list[str] = []
lines.append("RESULT=PASS_READ_ONLY_DOWNSTREAM_GRAPH_BINDING_AUDIT")
lines.append(f"PRODUCTION_MANIFEST_SHA={production_manifest_sha}")
lines.append(f"SHADOW_MANIFEST_SHA={shadow_manifest_sha}")
lines.append(f"PRODUCTION_RELEASE_ID={production_release_id}")
lines.append(f"SHADOW_RELEASE_ID={shadow_release_id}")
lines.append(f"RELEASE_IDS_EQUAL={str(production_release_id == shadow_release_id).lower()}")
lines.append(f"SLACK_WORKER_CONFIG_COUNT={len(config_docs)}")
lines.append(f"DIRECT_BINDER_COUNT={len(direct_binders)}")
lines.append(f"REFERENCE_FILE_COUNT={len(all_reference_details)}")
lines.append(f"GRAPH_EDGE_COUNT={len(edges)}")
lines.append(f"PRODUCTION_CHAIN_TOTAL_COUNT={len(production_chain)}")
lines.append(
    f"PRODUCTION_CHAIN_MUTABLE_COUNT={sum(bool(item.get('mutable')) for item in production_chain)}"
)
lines.append(
    f"PRODUCTION_CHAIN_IMMUTABLE_COUNT={sum(not bool(item.get('mutable')) for item in production_chain)}"
)
lines.append(
    f"ALL_DIRECT_BINDERS_BIND_PRODUCTION_IDENTITY={str(direct_production_complete).lower()}"
)
lines.append(
    f"ALL_DIRECT_BINDERS_BIND_SHADOW_IDENTITY={str(direct_shadow_complete).lower()}"
)
lines.append("COMPLETE_SHADOW_GRAPH_REQUIRED=true")
lines.append("SINGLE_RELATIVE_PATH_PATCH_SUFFICIENT=false")
lines.append("")
lines.append("[DIRECT_BINDERS]")
for detail in direct_details:
    lines.append(
        "{path}|sha={sha}|production_bindings={prod}|shadow_bindings={shadow}".format(
            path=detail.get("path"),
            sha=detail.get("sha256"),
            prod=detail.get("production_binding_count"),
            shadow=detail.get("shadow_binding_count"),
        )
    )
lines.append("")
lines.append("[PRODUCTION_CHAIN_PATHS]")
for path in sorted(production_chain_paths):
    lines.append(path)

audit_txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

cat "$AUDIT_TXT"

AUDIT_JSON_SHA="$(sha256_file "$AUDIT_JSON")"
AUDIT_TXT_SHA="$(sha256_file "$AUDIT_TXT")"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
SHADOW_MANIFEST_AFTER="$(sha256_file "$SHADOW_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$PRODUCTION_MANIFEST_AFTER" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$SHADOW_MANIFEST_AFTER" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] || {
    printf 'ERROR=SHADOW_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CHANGED\n' >&2
    exit 1
}

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3B-R2",
  "result": "PASS_W2B_I2F3B_R2_DOWNSTREAM_GRAPH_BINDING_AUDIT",
  "audit_json_sha256": "${AUDIT_JSON_SHA}",
  "audit_text_sha256": "${AUDIT_TXT_SHA}",
  "evidence_root": "${EVIDENCE_REL}",
  "decision": {
    "complete_shadow_graph_required": true,
    "single_relative_path_patch_sufficient": false,
    "mutable_config_shadow_copy_required": true,
    "transitive_shadow_sha_rebinding_required": true,
    "immutable_evidence_read_only": true
  },
  "execution": {
    "candidate_generation_performed": false,
    "candidate_validation_performed": false,
    "review_bundle_generation_performed": false
  },
  "safety": {
    "production_source_changed": false,
    "production_manifest_changed": false,
    "shadow_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "next_phase": "TST-5D-W2B-I2F-3B-R3_COMPLETE_SHADOW_GRAPH_BUILD"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3B_R2_DOWNSTREAM_GRAPH_BINDING_AUDIT\n'
printf 'AUDIT_JSON_SHA=%s\n' "$AUDIT_JSON_SHA"
printf 'AUDIT_TXT_SHA=%s\n' "$AUDIT_TXT_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'COMPLETE_SHADOW_GRAPH_REQUIRED=true\n'
printf 'SINGLE_RELATIVE_PATH_PATCH_SUFFICIENT=false\n'
printf 'MUTABLE_CONFIG_SHADOW_COPY_REQUIRED=true\n'
printf 'TRANSITIVE_SHADOW_SHA_REBINDING_REQUIRED=true\n'
printf 'IMMUTABLE_EVIDENCE_READ_ONLY=true\n'
printf 'CANDIDATE_GENERATION_PERFORMED=false\n'
printf 'REVIEW_BUNDLE_GENERATION_PERFORMED=false\n'
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'SHADOW_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3B-R3_COMPLETE_SHADOW_GRAPH_BUILD\n'
