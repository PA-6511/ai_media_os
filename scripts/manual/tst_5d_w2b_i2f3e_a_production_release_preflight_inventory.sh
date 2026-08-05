#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
FINAL_REVIEW_ROOT_REL="${I2E_ROOT_REL}/i2f3d-c-slack-runtime-human-rereview-20260725T170114-498322"
R4_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r4-shadow-candidate-validation-20260725T153121-489639"
R3_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r3-complete-shadow-graph-20260725T152341-488959"
SLACK_TEST_ROOT_REL="${I2E_ROOT_REL}/i2f3d-b-slack-hold-offline-tests-20260725T164615-497367"

FINAL_RESULT="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/result.json"
FINAL_DECISION_SET="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/final-human-review-decision-set.json"
SLACK_REREVIEW_RECORD="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/human-decisions/UNIT_SLACK_RUNTIME.human-rereview-decision.json"
REREVIEW_VALIDATION="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/slack-human-rereview-validation.json"
REREVIEW_APPROVAL="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/human-slack-rereview-approval-verbatim.txt"
REREVIEW_MANIFEST="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/rereview-evidence-manifest.txt"

R4_RESULT="${REPO_ROOT}/${R4_ROOT_REL}/result.json"
R3_RESULT="${REPO_ROOT}/${R3_ROOT_REL}/result.json"
SLACK_TEST_RESULT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/result.json"

EXPECTED_FINAL_RESULT_SHA="2fe36ba4cdd0c84a61b3ac3f9f81912e7dc8549b43c2a54923214d7f588c97e6"
EXPECTED_FINAL_DECISION_SET_SHA="9b28a2581535f6e2d12b811a61b7ff67777d4199f8db3edd3fda1f729e29ed30"
EXPECTED_SLACK_REREVIEW_RECORD_SHA="01c765549f3805a941cab6b411b20b387c421ab30929141b5565f68e05223900"
EXPECTED_REREVIEW_VALIDATION_SHA="efaa0b57de73594124590fbd931a5c56f6177a0b2bc8bd57d25417e3f4829652"
EXPECTED_REREVIEW_APPROVAL_SHA="ce3ea99d0acb86a4c839450010ca67de7e66ce9173c67bf5d5dc78c9eaed1b5f"
EXPECTED_REREVIEW_MANIFEST_SHA="6a291a85581a87738fc1072f662dbdfd0f4994496ff360bff009f1d913050399"

EXPECTED_R4_RESULT_SHA="eb3e7f8ff7fbd2ab77179515d3b06ed3da4644d4347e437bf7f7abde2bfa14d2"
EXPECTED_R3_RESULT_SHA="a99f495ec37c1daa2936d63e9d67f6aaac346b1836e3d1e1ce83fa7f1774daf4"
EXPECTED_SLACK_TEST_RESULT_SHA="732840292f5c551d589ea8e9459fc677c9df0380fb4ef1f18d5eafa2f1c33ce0"

R4_CANDIDATE_ROOT="/tmp/tst-5d-w2b-i2f3b-r4-candidate-20260725T153121-489639"
CANDIDATE_MANIFEST="${R4_CANDIDATE_ROOT}/candidate-manifest.json"
DEPENDENCY_CLOSURE="${R4_CANDIDATE_ROOT}/dependency-closure.json"
DOWNSTREAM_PLAN="${R4_CANDIDATE_ROOT}/downstream-rebinding-plan.json"

EXPECTED_CANDIDATE_MANIFEST_SHA="c882f2cb1afbfbe5215db61667a6c72feccc71bc84a558cdda792806d440f843"
EXPECTED_DEPENDENCY_CLOSURE_SHA="9eb8854b7b877cc927ca0350281f84d8dc3a8160f564982825f9f87f36ec79e9"
EXPECTED_DOWNSTREAM_PLAN_SHA="5fa8255966773bda7d35ba0d89b1f40c0f8b9a7df89b33578e3997f6cc22bed8"

PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

ACCESS_GUARD_SOURCE="${REPO_ROOT}/app/db/access_guard.py"
DB_CONFIG_SOURCE="${REPO_ROOT}/app/db/config.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
DB_SESSION_SOURCE="${REPO_ROOT}/app/db/session.py"
SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"
WORKFLOW_MIGRATION="${REPO_ROOT}/migrations/versions/00241611109d_add_unique_wordpress_post_id.py"
SLACK_SHADOW_TEST_SNAPSHOT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/shadow-test-snapshot/test_slack_approval_socket_hold_remediation_offline.py"

EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

EXPECTED_ACCESS_GUARD_SHA="1584ac2975a39433fbf4670bbd2ea9974870866f6193cf8036f9528e72669583"
EXPECTED_DB_CONFIG_SHA="5eeef8af4343d1e16412df40945f19667ee0f41dcbdea4a9f74386f12f7ddd59"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_DB_SESSION_SHA="0d6a0c2de0f5ab4691eae5d1dc311bf7d800461b7949d5ef1895fbc4b5b1d818"
EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_SLACK_SHADOW_TEST_SHA="5f4bc6709120998383543f346e504c4ab2c408c0dfd7219d1ff3f8a236a83184"

EXPECTED_CANDIDATE_ID="slack-worker-CANDIDATE-NOT-APPROVED-668ab8855ad6"
EXPECTED_REVIEW_BUNDLE_ID="slack-worker-release-rebinding-review-SCHEMA-CANDIDATE-c882f2cb1afb"

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

require_file_sha "$FINAL_RESULT" "$EXPECTED_FINAL_RESULT_SHA"
require_file_sha "$FINAL_DECISION_SET" "$EXPECTED_FINAL_DECISION_SET_SHA"
require_file_sha \
    "$SLACK_REREVIEW_RECORD" \
    "$EXPECTED_SLACK_REREVIEW_RECORD_SHA"
require_file_sha \
    "$REREVIEW_VALIDATION" \
    "$EXPECTED_REREVIEW_VALIDATION_SHA"
require_file_sha "$REREVIEW_APPROVAL" "$EXPECTED_REREVIEW_APPROVAL_SHA"
require_file_sha "$REREVIEW_MANIFEST" "$EXPECTED_REREVIEW_MANIFEST_SHA"

require_file_sha "$R4_RESULT" "$EXPECTED_R4_RESULT_SHA"
require_file_sha "$R3_RESULT" "$EXPECTED_R3_RESULT_SHA"
require_file_sha "$SLACK_TEST_RESULT" "$EXPECTED_SLACK_TEST_RESULT_SHA"

require_file_sha \
    "$CANDIDATE_MANIFEST" \
    "$EXPECTED_CANDIDATE_MANIFEST_SHA"
require_file_sha \
    "$DEPENDENCY_CLOSURE" \
    "$EXPECTED_DEPENDENCY_CLOSURE_SHA"
require_file_sha "$DOWNSTREAM_PLAN" "$EXPECTED_DOWNSTREAM_PLAN_SHA"

require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

require_file_sha "$ACCESS_GUARD_SOURCE" "$EXPECTED_ACCESS_GUARD_SHA"
require_file_sha "$DB_CONFIG_SOURCE" "$EXPECTED_DB_CONFIG_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$DB_SESSION_SOURCE" "$EXPECTED_DB_SESSION_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"
require_file_sha \
    "$SLACK_SHADOW_TEST_SNAPSHOT" \
    "$EXPECTED_SLACK_SHADOW_TEST_SHA"

if [[ ! -f "$WORKFLOW_MIGRATION" ]]; then
    printf 'ERROR=WORKFLOW_MIGRATION_MISSING:%s\n' "$WORKFLOW_MIGRATION" >&2
    exit 1
fi

WORKFLOW_MIGRATION_SHA="$(sha256_file "$WORKFLOW_MIGRATION")"
printf 'SHA_OBSERVED=%s:%s\n' \
    "$WORKFLOW_MIGRATION" \
    "$WORKFLOW_MIGRATION_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3e-a-production-release-preflight-inventory-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p "$EVIDENCE_ROOT"

PREFLIGHT_JSON="${EVIDENCE_ROOT}/production-release-preflight-inventory.json"
MANIFEST_ANALYSIS="${EVIDENCE_ROOT}/manifest-binding-analysis.json"
GIT_PATH_STATUS="${EVIDENCE_ROOT}/known-path-git-status.txt"
RELEASE_GATE_MATRIX="${EVIDENCE_ROOT}/production-release-gate-matrix.json"
PREFLIGHT_TEXT="${EVIDENCE_ROOT}/production-release-preflight-summary.txt"

git status --short -- \
    app/db/access_guard.py \
    app/db/config.py \
    app/db/repositories/workflow_state_repository.py \
    app/db/session.py \
    scripts/run_slack_approval_socket.py \
    migrations/versions/00241611109d_add_unique_wordpress_post_id.py \
    config/slack_worker_release_source_manifest.json \
    > "$GIT_PATH_STATUS"

python3 - \
    "$FINAL_DECISION_SET" \
    "$FINAL_RESULT" \
    "$CANDIDATE_MANIFEST" \
    "$DEPENDENCY_CLOSURE" \
    "$DOWNSTREAM_PLAN" \
    "$PRODUCTION_MANIFEST" \
    "$WORKFLOW_MIGRATION" \
    "$SLACK_SHADOW_TEST_SNAPSHOT" \
    "$PREFLIGHT_JSON" \
    "$MANIFEST_ANALYSIS" \
    "$RELEASE_GATE_MATRIX" \
    "$PREFLIGHT_TEXT" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

final_set_path = Path(sys.argv[1]).resolve()
final_result_path = Path(sys.argv[2]).resolve()
candidate_manifest_path = Path(sys.argv[3]).resolve()
dependency_closure_path = Path(sys.argv[4]).resolve()
downstream_plan_path = Path(sys.argv[5]).resolve()
production_manifest_path = Path(sys.argv[6]).resolve()
workflow_migration_path = Path(sys.argv[7]).resolve()
slack_shadow_test_path = Path(sys.argv[8]).resolve()
preflight_path = Path(sys.argv[9])
manifest_analysis_path = Path(sys.argv[10])
gate_matrix_path = Path(sys.argv[11])
summary_path = Path(sys.argv[12])
expected_candidate_id = sys.argv[13]
expected_review_bundle_id = sys.argv[14]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk_strings(value: Any, prefix: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{prefix}[{index}]")


final_set = load_json(final_set_path)
final_result = load_json(final_result_path)
candidate_manifest = load_json(candidate_manifest_path)
dependency_closure = load_json(dependency_closure_path)
downstream_plan = load_json(downstream_plan_path)
production_manifest = load_json(production_manifest_path)

if final_set.get("candidate_id") != expected_candidate_id:
    raise SystemExit("FINAL_SET_CANDIDATE_ID_MISMATCH")
if final_set.get("review_bundle_id") != expected_review_bundle_id:
    raise SystemExit("FINAL_SET_REVIEW_BUNDLE_ID_MISMATCH")
if final_set.get("record_status") != "ALL_REVIEW_UNITS_APPROVED_REVIEW_ONLY":
    raise SystemExit("FINAL_SET_RECORD_STATUS_INVALID")
if final_set.get("overall_review_canonical_decision") != "APPROVE":
    raise SystemExit("FINAL_REVIEW_NOT_APPROVED")
if final_set.get("overall_review_scope") != "SOURCE_AND_REBINDING_REVIEW_ONLY":
    raise SystemExit("FINAL_REVIEW_SCOPE_INVALID")
if final_set.get("production_release_decision") != "HOLD":
    raise SystemExit("PRODUCTION_RELEASE_NOT_HOLD")
if final_set.get("release_status") != "CANDIDATE_NOT_APPROVED":
    raise SystemExit("RELEASE_STATUS_INVALID")

decisions = final_set.get("decisions")
if not isinstance(decisions, dict):
    raise SystemExit("FINAL_DECISIONS_INVALID")

expected_decisions = {
    "UNIT_DB_SAFETY": "APPROVE",
    "UNIT_WORKFLOW_STATE": "APPROVE_WITH_CONDITIONS",
    "UNIT_SLACK_RUNTIME": "APPROVE",
}
for unit_id, label in expected_decisions.items():
    item = decisions.get(unit_id)
    if not isinstance(item, dict):
        raise SystemExit(f"FINAL_DECISION_MISSING:{unit_id}")
    if item.get("requested_decision_label") != label:
        raise SystemExit(f"FINAL_DECISION_INVALID:{unit_id}")

if final_result.get("result") != (
    "PASS_W2B_I2F3D_C_SLACK_RUNTIME_APPROVAL_RECORDED"
):
    raise SystemExit("FINAL_RESULT_INVALID")

review_state = final_result.get("review_state")
production_state = final_result.get("production_state")
if not isinstance(review_state, dict) or not isinstance(production_state, dict):
    raise SystemExit("FINAL_RESULT_STATE_INVALID")
if review_state.get("all_review_units_approved") is not True:
    raise SystemExit("ALL_REVIEW_UNITS_NOT_APPROVED")
if production_state.get("production_release_decision") != "HOLD":
    raise SystemExit("FINAL_PRODUCTION_DECISION_INVALID")

for key in (
    "production_approval_created",
    "production_manifest_update_allowed",
    "production_database_access_allowed",
    "production_migration_allowed",
    "deployment_allowed",
    "slack_worker_start_allowed",
    "runtime_execution_allowed",
    "external_network_allowed",
):
    if production_state.get(key) is not False:
        raise SystemExit(f"PRODUCTION_BOUNDARY_NOT_FALSE:{key}")

known_sources = {
    "app/db/access_guard.py": (
        "1584ac2975a39433fbf4670bbd2ea9974870866f6193cf8036f9528e72669583"
    ),
    "app/db/config.py": (
        "5eeef8af4343d1e16412df40945f19667ee0f41dcbdea4a9f74386f12f7ddd59"
    ),
    "app/db/repositories/workflow_state_repository.py": (
        "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
    ),
    "app/db/session.py": (
        "0d6a0c2de0f5ab4691eae5d1dc311bf7d800461b7949d5ef1895fbc4b5b1d818"
    ),
    "scripts/run_slack_approval_socket.py": (
        "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
    ),
}

production_strings = list(walk_strings(production_manifest))
candidate_strings = list(walk_strings(candidate_manifest))
closure_strings = list(walk_strings(dependency_closure))
plan_strings = list(walk_strings(downstream_plan))


def occurrences(items: list[tuple[str, str]], token: str) -> list[str]:
    return [path for path, value in items if token in value]


source_binding_analysis: dict[str, Any] = {}
for source_path, current_sha in known_sources.items():
    source_binding_analysis[source_path] = {
        "current_sha256": current_sha,
        "production_manifest_path_occurrences": occurrences(
            production_strings, source_path
        ),
        "production_manifest_current_sha_occurrences": occurrences(
            production_strings, current_sha
        ),
        "candidate_manifest_path_occurrences": occurrences(
            candidate_strings, source_path
        ),
        "candidate_manifest_current_sha_occurrences": occurrences(
            candidate_strings, current_sha
        ),
        "dependency_closure_path_occurrences": occurrences(
            closure_strings, source_path
        ),
        "downstream_plan_path_occurrences": occurrences(
            plan_strings, source_path
        ),
    }

production_manifest_contains_all_current_shas = all(
    item["production_manifest_current_sha_occurrences"]
    for item in source_binding_analysis.values()
)
candidate_manifest_contains_all_current_shas = all(
    item["candidate_manifest_current_sha_occurrences"]
    for item in source_binding_analysis.values()
)

manifest_analysis = {
    "schema_version": "1.0",
    "production_manifest": {
        "path": str(production_manifest_path),
        "sha256": sha(production_manifest_path),
    },
    "candidate_manifest": {
        "path": str(candidate_manifest_path),
        "sha256": sha(candidate_manifest_path),
    },
    "source_binding_analysis": source_binding_analysis,
    "production_manifest_contains_all_current_source_shas": (
        production_manifest_contains_all_current_shas
    ),
    "candidate_manifest_contains_all_current_source_shas": (
        candidate_manifest_contains_all_current_shas
    ),
    "production_manifest_rebind_preparation_required": (
        not production_manifest_contains_all_current_shas
    ),
    "production_manifest_update_performed": False,
}
write_json(manifest_analysis_path, manifest_analysis)

gates = [
    {
        "gate_id": "GATE_PRODUCTION_MANIFEST_REBIND",
        "status": "NOT_APPROVED",
        "required_before_release": True,
        "current_observation": (
            "Production manifest does not bind every reviewed current source SHA."
            if not production_manifest_contains_all_current_shas
            else "Production manifest already contains every reviewed current source SHA."
        ),
        "action_performed": False,
    },
    {
        "gate_id": "GATE_WORKFLOW_MIGRATION_APPLICATION",
        "status": "NOT_APPROVED",
        "required_before_release": True,
        "current_observation": (
            f"Migration file exists with SHA-256 {sha(workflow_migration_path)}; "
            "application is not approved."
        ),
        "action_performed": False,
    },
    {
        "gate_id": "GATE_PRODUCTION_DATABASE_PREFLIGHT",
        "status": "NOT_APPROVED",
        "required_before_release": True,
        "current_observation": (
            "Production database was hash-checked only; no SQL connection or "
            "schema inspection was performed."
        ),
        "action_performed": False,
    },
    {
        "gate_id": "GATE_SHADOW_TEST_PROMOTION_DECISION",
        "status": "NOT_DECIDED",
        "required_before_release": False,
        "current_observation": (
            "Slack HOLD remediation regression test exists only as immutable "
            f"shadow evidence with SHA-256 {sha(slack_shadow_test_path)}."
        ),
        "action_performed": False,
    },
    {
        "gate_id": "GATE_DEPLOYMENT",
        "status": "NOT_APPROVED",
        "required_before_release": True,
        "current_observation": "Deployment remains explicitly prohibited.",
        "action_performed": False,
    },
    {
        "gate_id": "GATE_SLACK_WORKER_START",
        "status": "NOT_APPROVED",
        "required_before_release": True,
        "current_observation": "Slack Worker start remains explicitly prohibited.",
        "action_performed": False,
    },
    {
        "gate_id": "GATE_EXTERNAL_NETWORK",
        "status": "NOT_APPROVED",
        "required_before_release": True,
        "current_observation": "External network access remains explicitly prohibited.",
        "action_performed": False,
    },
    {
        "gate_id": "GATE_PRODUCTION_APPROVAL",
        "status": "NOT_CREATED",
        "required_before_release": True,
        "current_observation": "No production approval record exists.",
        "action_performed": False,
    },
]

required_blocking_gates = [
    gate["gate_id"]
    for gate in gates
    if gate["required_before_release"] and gate["status"] != "APPROVED"
]

gate_matrix = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-A",
    "result": "PASS_PRODUCTION_RELEASE_GATE_INVENTORY_READY",
    "gates": gates,
    "required_blocking_gate_count": len(required_blocking_gates),
    "required_blocking_gates": required_blocking_gates,
    "production_release_ready": False,
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(gate_matrix_path, gate_matrix)

preflight = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-A",
    "result": "PASS_PRODUCTION_RELEASE_PREFLIGHT_INVENTORY_READY",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "review_state": {
        "all_review_units_approved": True,
        "overall_review_decision": "APPROVE_WITH_CONDITIONS",
        "overall_review_canonical_decision": "APPROVE",
        "scope": "SOURCE_AND_REBINDING_REVIEW_ONLY",
    },
    "production_state": {
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "production_release_ready": False,
        "required_blocking_gate_count": len(required_blocking_gates),
        "required_blocking_gates": required_blocking_gates,
    },
    "inputs": {
        "final_decision_set_sha256": sha(final_set_path),
        "final_result_sha256": sha(final_result_path),
        "candidate_manifest_sha256": sha(candidate_manifest_path),
        "dependency_closure_sha256": sha(dependency_closure_path),
        "downstream_plan_sha256": sha(downstream_plan_path),
        "production_manifest_sha256": sha(production_manifest_path),
        "workflow_migration_sha256": sha(workflow_migration_path),
        "slack_shadow_test_sha256": sha(slack_shadow_test_path),
    },
    "manifest_analysis": {
        "production_manifest_contains_all_current_source_shas": (
            production_manifest_contains_all_current_shas
        ),
        "candidate_manifest_contains_all_current_source_shas": (
            candidate_manifest_contains_all_current_shas
        ),
        "production_manifest_rebind_preparation_required": (
            not production_manifest_contains_all_current_shas
        ),
    },
    "execution": {
        "source_modified": False,
        "production_manifest_modified": False,
        "production_database_opened": False,
        "production_database_sql_connection_used": False,
        "migration_applied": False,
        "test_promoted_to_repository": False,
        "pytest_executed": False,
        "deployment_performed": False,
        "slack_worker_started": False,
        "external_network_used": False,
        "production_approval_created": False,
    },
    "next_gate": "HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_SCOPE",
}
write_json(preflight_path, preflight)

summary_lines = [
    "RESULT=PASS_PRODUCTION_RELEASE_PREFLIGHT_INVENTORY_READY",
    "ALL_REVIEW_UNITS_APPROVED=true",
    "OVERALL_REVIEW_DECISION=APPROVE_WITH_CONDITIONS",
    "OVERALL_REVIEW_SCOPE=SOURCE_AND_REBINDING_REVIEW_ONLY",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "RELEASE_STATUS=CANDIDATE_NOT_APPROVED",
    "PRODUCTION_RELEASE_READY=false",
    f"REQUIRED_BLOCKING_GATE_COUNT={len(required_blocking_gates)}",
    (
        "PRODUCTION_MANIFEST_CONTAINS_ALL_CURRENT_SOURCE_SHAS="
        + str(production_manifest_contains_all_current_shas).lower()
    ),
    (
        "CANDIDATE_MANIFEST_CONTAINS_ALL_CURRENT_SOURCE_SHAS="
        + str(candidate_manifest_contains_all_current_shas).lower()
    ),
    (
        "PRODUCTION_MANIFEST_REBIND_PREPARATION_REQUIRED="
        + str(not production_manifest_contains_all_current_shas).lower()
    ),
    f"WORKFLOW_MIGRATION_SHA={sha(workflow_migration_path)}",
    "PRODUCTION_MANIFEST_MODIFIED=false",
    "PRODUCTION_DB_OPENED=false",
    "PRODUCTION_DB_SQL_CONNECTION_USED=false",
    "PRODUCTION_MIGRATION_APPLIED=false",
    "REPOSITORY_TEST_PROMOTED=false",
    "PYTEST_EXECUTED=false",
    "DEPLOYMENT_PERFORMED=false",
    "SLACK_WORKER_STARTED=false",
    "EXTERNAL_NETWORK_USED=false",
    "PRODUCTION_APPROVAL_CREATED=false",
    "NEXT_GATE=HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_SCOPE",
]
summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
PY

python3 -m json.tool "$PREFLIGHT_JSON" >/dev/null
python3 -m json.tool "$MANIFEST_ANALYSIS" >/dev/null
python3 -m json.tool "$RELEASE_GATE_MATRIX" >/dev/null

cat "$PREFLIGHT_TEXT"

PREFLIGHT_JSON_SHA="$(sha256_file "$PREFLIGHT_JSON")"
MANIFEST_ANALYSIS_SHA="$(sha256_file "$MANIFEST_ANALYSIS")"
GIT_PATH_STATUS_SHA="$(sha256_file "$GIT_PATH_STATUS")"
RELEASE_GATE_MATRIX_SHA="$(sha256_file "$RELEASE_GATE_MATRIX")"
PREFLIGHT_TEXT_SHA="$(sha256_file "$PREFLIGHT_TEXT")"

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/preflight-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'preflight-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"
chmod 0444 "$EVIDENCE_MANIFEST"

EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"

BLOCKING_GATE_COUNT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["production_state"]["required_blocking_gate_count"])' \
        "$PREFLIGHT_JSON"
)"
PRODUCTION_MANIFEST_COMPLETE="$(
    python3 -c \
        'import json,sys; print(str(json.load(open(sys.argv[1], encoding="utf-8"))["manifest_analysis"]["production_manifest_contains_all_current_source_shas"]).lower())' \
        "$PREFLIGHT_JSON"
)"
CANDIDATE_MANIFEST_COMPLETE="$(
    python3 -c \
        'import json,sys; print(str(json.load(open(sys.argv[1], encoding="utf-8"))["manifest_analysis"]["candidate_manifest_contains_all_current_source_shas"]).lower())' \
        "$PREFLIGHT_JSON"
)"
MANIFEST_REBIND_REQUIRED="$(
    python3 -c \
        'import json,sys; print(str(json.load(open(sys.argv[1], encoding="utf-8"))["manifest_analysis"]["production_manifest_rebind_preparation_required"]).lower())' \
        "$PREFLIGHT_JSON"
)"

FINAL_RESULT_AFTER="$(sha256_file "$FINAL_RESULT")"
FINAL_DECISION_SET_AFTER="$(sha256_file "$FINAL_DECISION_SET")"
CANDIDATE_MANIFEST_AFTER="$(sha256_file "$CANDIDATE_MANIFEST")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"

ACCESS_GUARD_AFTER="$(sha256_file "$ACCESS_GUARD_SOURCE")"
DB_CONFIG_AFTER="$(sha256_file "$DB_CONFIG_SOURCE")"
WORKFLOW_SOURCE_AFTER="$(sha256_file "$WORKFLOW_SOURCE")"
DB_SESSION_AFTER="$(sha256_file "$DB_SESSION_SOURCE")"
SLACK_SOURCE_AFTER="$(sha256_file "$SLACK_SOURCE")"
WORKFLOW_MIGRATION_AFTER="$(sha256_file "$WORKFLOW_MIGRATION")"

[[ "$FINAL_RESULT_AFTER" == "$EXPECTED_FINAL_RESULT_SHA" ]] || {
    printf 'ERROR=FINAL_RESULT_CHANGED\n' >&2
    exit 1
}
[[ "$FINAL_DECISION_SET_AFTER" == "$EXPECTED_FINAL_DECISION_SET_SHA" ]] || {
    printf 'ERROR=FINAL_DECISION_SET_CHANGED\n' >&2
    exit 1
}
[[ "$CANDIDATE_MANIFEST_AFTER" == "$EXPECTED_CANDIDATE_MANIFEST_SHA" ]] || {
    printf 'ERROR=CANDIDATE_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$PRODUCTION_MANIFEST_AFTER" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CHANGED\n' >&2
    exit 1
}

[[ "$ACCESS_GUARD_AFTER" == "$EXPECTED_ACCESS_GUARD_SHA" ]] || {
    printf 'ERROR=ACCESS_GUARD_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$DB_CONFIG_AFTER" == "$EXPECTED_DB_CONFIG_SHA" ]] || {
    printf 'ERROR=DB_CONFIG_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$WORKFLOW_SOURCE_AFTER" == "$EXPECTED_WORKFLOW_SOURCE_SHA" ]] || {
    printf 'ERROR=WORKFLOW_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$DB_SESSION_AFTER" == "$EXPECTED_DB_SESSION_SHA" ]] || {
    printf 'ERROR=DB_SESSION_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$SLACK_SOURCE_AFTER" == "$EXPECTED_SLACK_SOURCE_SHA" ]] || {
    printf 'ERROR=SLACK_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$WORKFLOW_MIGRATION_AFTER" == "$WORKFLOW_MIGRATION_SHA" ]] || {
    printf 'ERROR=WORKFLOW_MIGRATION_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3E-A",
  "result": "PASS_W2B_I2F3E_A_PRODUCTION_RELEASE_PREFLIGHT_INVENTORY_READY",
  "candidate_id": "${EXPECTED_CANDIDATE_ID}",
  "review_bundle_id": "${EXPECTED_REVIEW_BUNDLE_ID}",
  "evidence_root": "${EVIDENCE_REL}",
  "review_state": {
    "all_review_units_approved": true,
    "overall_review_decision": "APPROVE_WITH_CONDITIONS",
    "overall_review_scope": "SOURCE_AND_REBINDING_REVIEW_ONLY"
  },
  "production_state": {
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_release_ready": false,
    "required_blocking_gate_count": ${BLOCKING_GATE_COUNT}
  },
  "manifest_state": {
    "production_manifest_contains_all_current_source_shas": ${PRODUCTION_MANIFEST_COMPLETE},
    "candidate_manifest_contains_all_current_source_shas": ${CANDIDATE_MANIFEST_COMPLETE},
    "production_manifest_rebind_preparation_required": ${MANIFEST_REBIND_REQUIRED},
    "production_manifest_sha256": "${EXPECTED_PRODUCTION_MANIFEST_SHA}",
    "candidate_manifest_sha256": "${EXPECTED_CANDIDATE_MANIFEST_SHA}"
  },
  "migration_state": {
    "workflow_migration_path": "migrations/versions/00241611109d_add_unique_wordpress_post_id.py",
    "workflow_migration_sha256": "${WORKFLOW_MIGRATION_SHA}",
    "production_migration_allowed": false,
    "production_migration_applied": false
  },
  "artifacts": {
    "preflight_inventory_sha256": "${PREFLIGHT_JSON_SHA}",
    "manifest_binding_analysis_sha256": "${MANIFEST_ANALYSIS_SHA}",
    "known_path_git_status_sha256": "${GIT_PATH_STATUS_SHA}",
    "production_release_gate_matrix_sha256": "${RELEASE_GATE_MATRIX_SHA}",
    "preflight_summary_sha256": "${PREFLIGHT_TEXT_SHA}",
    "preflight_evidence_manifest_sha256": "${EVIDENCE_MANIFEST_SHA}"
  },
  "execution": {
    "source_modified": false,
    "production_manifest_modified": false,
    "production_database_opened": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "repository_test_promoted": false,
    "pytest_executed": false,
    "deployment_performed": false,
    "slack_worker_started": false,
    "external_network_used": false,
    "production_approval_created": false
  },
  "safety": {
    "final_result_changed": false,
    "final_decision_set_changed": false,
    "candidate_manifest_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "access_guard_source_changed": false,
    "db_config_source_changed": false,
    "workflow_source_changed": false,
    "db_session_source_changed": false,
    "slack_source_changed": false,
    "workflow_migration_changed": false
  },
  "next_gate": "HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_SCOPE",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3E_A_PRODUCTION_RELEASE_PREFLIGHT_INVENTORY_READY\n'
printf 'CANDIDATE_ID=%s\n' "$EXPECTED_CANDIDATE_ID"
printf 'REVIEW_BUNDLE_ID=%s\n' "$EXPECTED_REVIEW_BUNDLE_ID"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'ALL_REVIEW_UNITS_APPROVED=true\n'
printf 'OVERALL_REVIEW_DECISION=APPROVE_WITH_CONDITIONS\n'
printf 'OVERALL_REVIEW_SCOPE=SOURCE_AND_REBINDING_REVIEW_ONLY\n'
printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'PRODUCTION_RELEASE_READY=false\n'
printf 'REQUIRED_BLOCKING_GATE_COUNT=%s\n' "$BLOCKING_GATE_COUNT"
printf 'PRODUCTION_MANIFEST_CONTAINS_ALL_CURRENT_SOURCE_SHAS=%s\n' "$PRODUCTION_MANIFEST_COMPLETE"
printf 'CANDIDATE_MANIFEST_CONTAINS_ALL_CURRENT_SOURCE_SHAS=%s\n' "$CANDIDATE_MANIFEST_COMPLETE"
printf 'PRODUCTION_MANIFEST_REBIND_PREPARATION_REQUIRED=%s\n' "$MANIFEST_REBIND_REQUIRED"
printf 'WORKFLOW_MIGRATION_SHA=%s\n' "$WORKFLOW_MIGRATION_SHA"
printf 'PREFLIGHT_INVENTORY_SHA=%s\n' "$PREFLIGHT_JSON_SHA"
printf 'MANIFEST_BINDING_ANALYSIS_SHA=%s\n' "$MANIFEST_ANALYSIS_SHA"
printf 'RELEASE_GATE_MATRIX_SHA=%s\n' "$RELEASE_GATE_MATRIX_SHA"
printf 'PREFLIGHT_EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'SOURCE_MODIFIED=false\n'
printf 'PRODUCTION_MANIFEST_MODIFIED=false\n'
printf 'PRODUCTION_DB_OPENED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'REPOSITORY_TEST_PROMOTED=false\n'
printf 'PYTEST_EXECUTED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'SLACK_WORKER_STARTED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'FINAL_RESULT_CHANGED=false\n'
printf 'FINAL_DECISION_SET_CHANGED=false\n'
printf 'CANDIDATE_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'ACCESS_GUARD_SOURCE_CHANGED=false\n'
printf 'DB_CONFIG_SOURCE_CHANGED=false\n'
printf 'WORKFLOW_SOURCE_CHANGED=false\n'
printf 'DB_SESSION_SOURCE_CHANGED=false\n'
printf 'SLACK_SOURCE_CHANGED=false\n'
printf 'WORKFLOW_MIGRATION_CHANGED=false\n'
printf 'NEXT_GATE=HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_SCOPE\n'
printf 'SCRIPT_EXIT_CODE=0\n'
