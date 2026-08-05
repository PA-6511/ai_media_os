#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
I2F0_ROOT_REL="${I2E_ROOT_REL}/approval-rebinding-preparation-only-20260725T142358-486003"
I2F2_ROOT_REL="${I2E_ROOT_REL}/i2f2-shadow-contract-design-20260725T144825-486854"
I2F3A_ROOT_REL="${I2E_ROOT_REL}/i2f3a-shadow-toolchain-skeleton-20260725T145828-487557"

APPROVAL_PATH="${REPO_ROOT}/${I2F0_ROOT_REL}/human-approval.json"
I2F2_RESULT_PATH="${REPO_ROOT}/${I2F2_ROOT_REL}/result.json"
I2F3A_RESULT_PATH="${REPO_ROOT}/${I2F3A_ROOT_REL}/result.json"
I2F3A_SNAPSHOT_MANIFEST="${REPO_ROOT}/${I2F3A_ROOT_REL}/shadow-snapshot-manifest.txt"

EXPECTED_APPROVAL_SHA="a73ec08108e1add5e6aaeadd5f85e34798af237f18ced24b09bfeae2d3129026"
EXPECTED_I2F2_RESULT_SHA="2315a6e62b78c62aae09df9f8f38efeb87eb35fe272940837aff81a03a08ce72"
EXPECTED_I2F3A_RESULT_SHA="dd09b31a2499c6b7d311cc7dc1067862ecae3ececd615ce0d9917a152d78c744"
EXPECTED_I2F3A_SNAPSHOT_MANIFEST_SHA="6b3db0e4516d2f14ae6c173467896e7b9979f56f2903af2c4d174916457e8ba5"

SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3a-shadow-20260725T145828-487557"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
MANIFEST_PATH="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
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

require_file_sha "$APPROVAL_PATH" "$EXPECTED_APPROVAL_SHA"
require_file_sha "$I2F2_RESULT_PATH" "$EXPECTED_I2F2_RESULT_SHA"
require_file_sha "$I2F3A_RESULT_PATH" "$EXPECTED_I2F3A_RESULT_SHA"
require_file_sha \
    "$I2F3A_SNAPSHOT_MANIFEST" \
    "$EXPECTED_I2F3A_SNAPSHOT_MANIFEST_SHA"
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha "$MANIFEST_PATH" "$EXPECTED_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

if [[ ! -d "$SHADOW_ROOT" ]]; then
    printf 'ERROR=SHADOW_ROOT_MISSING:%s\n' "$SHADOW_ROOT" >&2
    exit 1
fi

while read -r expected relative; do
    [[ -n "$expected" && -n "$relative" ]] || continue
    actual_path="${SHADOW_ROOT}/${relative#./}"
    require_file_sha "$actual_path" "$expected"
done < "$I2F3A_SNAPSHOT_MANIFEST"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
CANDIDATE_ROOT="/tmp/tst-5d-w2b-i2f3b-candidate-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3b-shadow-candidate-validation-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$CANDIDATE_ROOT" ]]; then
    printf 'ERROR=CANDIDATE_ROOT_ALREADY_EXISTS:%s\n' "$CANDIDATE_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_ALREADY_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p "$EVIDENCE_ROOT/candidate-snapshot"

BUILDER_LOG="${EVIDENCE_ROOT}/candidate-builder.txt"
VALIDATOR_LOG="${EVIDENCE_ROOT}/candidate-validator.txt"
SEMANTIC_RESULT="${EVIDENCE_ROOT}/candidate-semantic-validation.json"
RESULT_JSON="${EVIDENCE_ROOT}/result.json"

set +e
(
    cd "$SHADOW_ROOT"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$SHADOW_ROOT" \
    python3 \
        "$SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
        --output-dir "$CANDIDATE_ROOT"
) >"$BUILDER_LOG" 2>&1
BUILDER_RC=$?
set -e

cat "$BUILDER_LOG"

if [[ "$BUILDER_RC" -ne 0 ]]; then
    SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
    MANIFEST_AFTER="$(sha256_file "$MANIFEST_PATH")"
    DB_AFTER="$(sha256_file "$DB_PATH")"

    cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3B",
  "result": "BLOCKED_W2B_I2F3B_SHADOW_CANDIDATE_GENERATION",
  "builder_exit_code": ${BUILDER_RC},
  "candidate_root": "${CANDIDATE_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "candidate_generation_performed": false,
  "candidate_validation_performed": false,
  "review_bundle_generation_performed": false,
  "safety": {
    "production_source_changed": $([[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] && echo false || echo true),
    "production_manifest_changed": $([[ "$MANIFEST_AFTER" == "$EXPECTED_MANIFEST_SHA" ]] && echo false || echo true),
    "production_database_content_changed": $([[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] && echo false || echo true),
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION"
}
JSON

    printf '\nRESULT=BLOCKED_W2B_I2F3B_SHADOW_CANDIDATE_GENERATION\n'
    printf 'BUILDER_EXIT_CODE=%s\n' "$BUILDER_RC"
    printf 'CANDIDATE_ROOT=%s\n' "$CANDIDATE_ROOT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'FAILED_EVIDENCE_PRESERVED=true\n'
    printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
    exit "$BUILDER_RC"
fi

CANDIDATE_PATH="${CANDIDATE_ROOT}/candidate-manifest.json"
CLOSURE_PATH="${CANDIDATE_ROOT}/dependency-closure.json"
DOWNSTREAM_PATH="${CANDIDATE_ROOT}/downstream-rebinding-plan.json"

for path in "$CANDIDATE_PATH" "$CLOSURE_PATH" "$DOWNSTREAM_PATH"; do
    if [[ ! -f "$path" ]]; then
        printf 'ERROR=CANDIDATE_OUTPUT_MISSING:%s\n' "$path" >&2
        exit 1
    fi
    python3 -m json.tool "$path" >/dev/null
done

set +e
(
    cd "$SHADOW_ROOT"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$SHADOW_ROOT" \
    python3 \
        "$SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
        --candidate "$CANDIDATE_PATH" \
        --closure "$CLOSURE_PATH" \
        --downstream-plan "$DOWNSTREAM_PATH"
) >"$VALIDATOR_LOG" 2>&1
VALIDATOR_RC=$?
set -e

cat "$VALIDATOR_LOG"

if [[ "$VALIDATOR_RC" -ne 0 ]]; then
    cp --preserve=mode,timestamps \
        "$CANDIDATE_PATH" \
        "$EVIDENCE_ROOT/candidate-snapshot/candidate-manifest.json"
    cp --preserve=mode,timestamps \
        "$CLOSURE_PATH" \
        "$EVIDENCE_ROOT/candidate-snapshot/dependency-closure.json"
    cp --preserve=mode,timestamps \
        "$DOWNSTREAM_PATH" \
        "$EVIDENCE_ROOT/candidate-snapshot/downstream-rebinding-plan.json"

    SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
    MANIFEST_AFTER="$(sha256_file "$MANIFEST_PATH")"
    DB_AFTER="$(sha256_file "$DB_PATH")"

    cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3B",
  "result": "BLOCKED_W2B_I2F3B_SHADOW_CANDIDATE_VALIDATION",
  "builder_exit_code": ${BUILDER_RC},
  "validator_exit_code": ${VALIDATOR_RC},
  "candidate_root": "${CANDIDATE_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "candidate_generation_performed": true,
  "candidate_validation_performed": true,
  "candidate_validation_passed": false,
  "review_bundle_generation_performed": false,
  "safety": {
    "production_source_changed": $([[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] && echo false || echo true),
    "production_manifest_changed": $([[ "$MANIFEST_AFTER" == "$EXPECTED_MANIFEST_SHA" ]] && echo false || echo true),
    "production_database_content_changed": $([[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] && echo false || echo true),
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION"
}
JSON

    printf '\nRESULT=BLOCKED_W2B_I2F3B_SHADOW_CANDIDATE_VALIDATION\n'
    printf 'BUILDER_EXIT_CODE=%s\n' "$BUILDER_RC"
    printf 'VALIDATOR_EXIT_CODE=%s\n' "$VALIDATOR_RC"
    printf 'CANDIDATE_ROOT=%s\n' "$CANDIDATE_ROOT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'FAILED_EVIDENCE_PRESERVED=true\n'
    printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
    exit "$VALIDATOR_RC"
fi

python3 - \
    "$CANDIDATE_PATH" \
    "$CLOSURE_PATH" \
    "$DOWNSTREAM_PATH" \
    "$BUILDER_LOG" \
    "$VALIDATOR_LOG" \
    "$SEMANTIC_RESULT" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

candidate_path = Path(sys.argv[1])
closure_path = Path(sys.argv[2])
downstream_path = Path(sys.argv[3])
builder_log_path = Path(sys.argv[4])
validator_log_path = Path(sys.argv[5])
result_path = Path(sys.argv[6])

workflow = "app/db/repositories/workflow_state_repository.py"
expected_changed = {
    "app/db/access_guard.py",
    "app/db/config.py",
    "app/db/session.py",
    "scripts/run_slack_approval_socket.py",
}
expected_absorbed = {workflow}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def load_log_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise SystemExit(f"LOG_JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


candidate = load(candidate_path)
closure = load(closure_path)
downstream = load(downstream_path)
builder_result = load_log_json(builder_log_path)
validator_result = load_log_json(validator_log_path)

audit = candidate.get("source_audit", [])
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
review_units = candidate.get("review_units", [])
review_by_name = {
    item.get("unit"): item for item in review_units if isinstance(item, dict)
}
assigned = {
    source
    for unit in review_units
    if isinstance(unit, dict)
    for source in unit.get("sources", [])
    if isinstance(source, str)
}

checks = {
    "builder_result_pass": builder_result.get("result")
    == "PASS_DRY_RUN_CANDIDATE_NOT_APPROVED",
    "validator_result_pass": validator_result.get("result")
    == "PASS_CANDIDATE_NOT_APPROVED",
    "candidate_release_status_not_approved": candidate.get("release_status")
    == "CANDIDATE_NOT_APPROVED",
    "candidate_deployment_false": candidate.get("deployment_allowed") is False,
    "candidate_runtime_false": candidate.get("runtime_execution_allowed") is False,
    "candidate_production_approval_false": candidate.get(
        "production_approval_created"
    )
    is False,
    "candidate_source_count_17": candidate.get("source_file_count") == 17,
    "changed_sources_are_four": changed == expected_changed,
    "unchanged_source_count_13": len(unchanged) == 13,
    "workflow_is_baseline_absorbed": workflow in unchanged,
    "review_unit_count_3": len(review_units) == 3,
    "workflow_review_unit_present": "UNIT_WORKFLOW_STATE" in review_by_name,
    "all_five_review_sources_assigned": assigned == expected_changed | expected_absorbed,
    "workflow_unit_role_absorbed": review_by_name.get("UNIT_WORKFLOW_STATE", {}).get(
        "candidate_change_role"
    )
    == "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW",
    "closure_has_no_unresolved_dynamic_dependency": closure.get(
        "unresolved_dynamic_dependencies"
    )
    == [],
    "downstream_release_status_not_approved": downstream.get("release_status")
    == "CANDIDATE_NOT_APPROVED",
    "downstream_deployment_false": downstream.get("deployment_allowed") is False,
    "downstream_runtime_false": downstream.get("runtime_execution_allowed") is False,
}

failed = sorted(name for name, passed in checks.items() if not passed)

result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3B",
    "result": (
        "PASS_SHADOW_CANDIDATE_SEMANTIC_VALIDATION"
        if not failed
        else "FAIL_SHADOW_CANDIDATE_SEMANTIC_VALIDATION"
    ),
    "candidate_id": candidate.get("candidate_id"),
    "counts": {
        "candidate_source_count": candidate.get("source_file_count"),
        "candidate_changed_source_count": len(changed),
        "candidate_unchanged_source_count": len(unchanged),
        "baseline_absorbed_source_count": len(expected_absorbed & unchanged),
        "review_unit_count": len(review_units),
        "human_review_source_count": len(assigned),
        "downstream_candidate_count": downstream.get("downstream_candidate_count"),
    },
    "changed_sources": sorted(changed),
    "baseline_absorbed_sources": sorted(expected_absorbed & unchanged),
    "checks": checks,
    "failed_checks": failed,
    "sha256": {
        "candidate_manifest": sha(candidate_path),
        "dependency_closure": sha(closure_path),
        "downstream_rebinding_plan": sha(downstream_path),
        "candidate_builder_log": sha(builder_log_path),
        "candidate_validator_log": sha(validator_log_path),
    },
    "production_approval_created": False,
    "deployment_allowed": False,
    "runtime_execution_allowed": False,
    "review_bundle_generation_performed": False,
}

result_path.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)

if failed:
    raise SystemExit("SEMANTIC_VALIDATION_FAILED:" + ",".join(failed))
PY

cp --preserve=mode,timestamps \
    "$CANDIDATE_PATH" \
    "$EVIDENCE_ROOT/candidate-snapshot/candidate-manifest.json"
cp --preserve=mode,timestamps \
    "$CLOSURE_PATH" \
    "$EVIDENCE_ROOT/candidate-snapshot/dependency-closure.json"
cp --preserve=mode,timestamps \
    "$DOWNSTREAM_PATH" \
    "$EVIDENCE_ROOT/candidate-snapshot/downstream-rebinding-plan.json"

CANDIDATE_SHA="$(sha256_file "$CANDIDATE_PATH")"
CLOSURE_SHA="$(sha256_file "$CLOSURE_PATH")"
DOWNSTREAM_SHA="$(sha256_file "$DOWNSTREAM_PATH")"
BUILDER_LOG_SHA="$(sha256_file "$BUILDER_LOG")"
VALIDATOR_LOG_SHA="$(sha256_file "$VALIDATOR_LOG")"
SEMANTIC_SHA="$(sha256_file "$SEMANTIC_RESULT")"

CANDIDATE_ID="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["candidate_id"])' \
        "$CANDIDATE_PATH"
)"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
MANIFEST_AFTER="$(sha256_file "$MANIFEST_PATH")"
DB_AFTER="$(sha256_file "$DB_PATH")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$MANIFEST_AFTER" == "$EXPECTED_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CONTENT_CHANGED\n' >&2
    exit 1
}

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3B",
  "result": "PASS_W2B_I2F3B_SHADOW_CANDIDATE_VALIDATED",
  "approval_scope": "APPROVE_SHADOW_CONTRACT_IMPLEMENTATION_ONLY",
  "shadow_root": "${SHADOW_ROOT}",
  "candidate_root": "${CANDIDATE_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "candidate": {
    "candidate_id": "${CANDIDATE_ID}",
    "candidate_manifest_sha256": "${CANDIDATE_SHA}",
    "dependency_closure_sha256": "${CLOSURE_SHA}",
    "downstream_rebinding_plan_sha256": "${DOWNSTREAM_SHA}",
    "candidate_changed_source_count": 4,
    "candidate_unchanged_source_count": 13,
    "baseline_absorbed_source_count": 1,
    "review_unit_count": 3,
    "human_review_source_count": 5,
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_approval_created": false,
    "deployment_allowed": false,
    "runtime_execution_allowed": false
  },
  "validation": {
    "builder_exit_code": ${BUILDER_RC},
    "validator_exit_code": ${VALIDATOR_RC},
    "builder_log_sha256": "${BUILDER_LOG_SHA}",
    "validator_log_sha256": "${VALIDATOR_LOG_SHA}",
    "semantic_validation_sha256": "${SEMANTIC_SHA}"
  },
  "execution": {
    "candidate_generation_performed": true,
    "candidate_validation_performed": true,
    "candidate_validation_passed": true,
    "review_bundle_generation_performed": false,
    "review_bundle_validation_performed": false
  },
  "safety": {
    "production_source_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "next_phase": "TST-5D-W2B-I2F-3C_SHADOW_REVIEW_BUNDLE_GENERATION_AND_VALIDATION",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3B_SHADOW_CANDIDATE_VALIDATED\n'
printf 'CANDIDATE_ID=%s\n' "$CANDIDATE_ID"
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'CANDIDATE_ROOT=%s\n' "$CANDIDATE_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'CANDIDATE_MANIFEST_SHA=%s\n' "$CANDIDATE_SHA"
printf 'DEPENDENCY_CLOSURE_SHA=%s\n' "$CLOSURE_SHA"
printf 'DOWNSTREAM_REBINDING_PLAN_SHA=%s\n' "$DOWNSTREAM_SHA"
printf 'SEMANTIC_VALIDATION_SHA=%s\n' "$SEMANTIC_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'CANDIDATE_CHANGED_SOURCE_COUNT=4\n'
printf 'CANDIDATE_UNCHANGED_SOURCE_COUNT=13\n'
printf 'BASELINE_ABSORBED_SOURCE_COUNT=1\n'
printf 'REVIEW_UNIT_COUNT=3\n'
printf 'HUMAN_REVIEW_SOURCE_COUNT=5\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'DEPLOYMENT_ALLOWED=false\n'
printf 'RUNTIME_EXECUTION_ALLOWED=false\n'
printf 'CANDIDATE_GENERATION_PERFORMED=true\n'
printf 'CANDIDATE_VALIDATION_PASSED=true\n'
printf 'REVIEW_BUNDLE_GENERATION_PERFORMED=false\n'
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3C_SHADOW_REVIEW_BUNDLE_GENERATION_AND_VALIDATION\n'
