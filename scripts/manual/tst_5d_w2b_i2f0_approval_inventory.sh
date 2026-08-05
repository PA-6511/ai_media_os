#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
EVIDENCE_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_ROOT_REL}"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
MANIFEST_PATH="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

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

    printf 'SHA_PASS=%s:%s\n' "${path#${REPO_ROOT}/}" "$actual"
}

cd "$REPO_ROOT"

if [[ ! -d "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_NOT_FOUND:%s\n' "$EVIDENCE_ROOT_REL" >&2
    exit 1
fi

require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha "$MANIFEST_PATH" "$EXPECTED_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
OUTPUT_REL="${EVIDENCE_ROOT_REL}/approval-rebinding-preparation-only-${RUN_ID}"
OUTPUT_DIR="${REPO_ROOT}/${OUTPUT_REL}"

if [[ -e "$OUTPUT_DIR" ]]; then
    printf 'ERROR=OUTPUT_ALREADY_EXISTS:%s\n' "$OUTPUT_REL" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

APPROVAL_JSON="${OUTPUT_DIR}/human-approval.json"
INVENTORY_TXT="${OUTPUT_DIR}/preparation-tool-inventory.txt"
RESULT_JSON="${OUTPUT_DIR}/approval-inventory-result.json"

cat > "$APPROVAL_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-0",
  "decision": "APPROVE_REBINDING_PREPARATION_ONLY",
  "decision_source": "explicit_human_approval",
  "approved": true,
  "approval_consumed_for": [
    "new_candidate_manifest_preparation",
    "dependency_closure_preparation",
    "downstream_rebinding_plan_preparation",
    "review_bundle_preparation"
  ],
  "explicitly_not_approved": [
    "production_manifest_update",
    "production_database_connection_or_write",
    "production_migration",
    "deployment",
    "wordpress_network",
    "x_network",
    "slack_network",
    "slack_worker_start",
    "automatic_approval"
  ],
  "parent_evidence": {
    "evidence_root": "${EVIDENCE_ROOT_REL}",
    "classification_sha256": "7448610ca8aea22b35a36464ac9714708a29c3b00ba4d68bd7461625b0fdf9c0",
    "rereview_packet_sha256": "dc45ace8147fe74619c7856b33f6ec5667b536f3031ed01524e8aaadf4d89cdc",
    "evidence_manifest_sha256": "8fa64fc423e730ade63638c65f72d54fd3053912846b487d1d2825b8ac324b22"
  },
  "production_boundary": {
    "source_write_allowed": false,
    "manifest_write_allowed": false,
    "database_connection_allowed": false,
    "database_write_allowed": false,
    "migration_allowed": false,
    "deployment_allowed": false,
    "external_network_allowed": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "preparation_gate": "APPROVED",
  "recorded_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

{
    printf 'PHASE=TST-5D-W2B-I2F-0\n'
    printf 'PURPOSE=READ_ONLY_TOOL_DISCOVERY_FOR_REBINDING_PREPARATION\n'
    printf 'REPO_ROOT=%s\n\n' "$REPO_ROOT"

    printf '[MATCHING_FILES]\n'
    find scripts config tests app exchange \
        -type f \
        \( \
            -iname '*slack*worker*release*' -o \
            -iname '*manifest*candidate*' -o \
            -iname '*dependency*closure*' -o \
            -iname '*downstream*rebinding*' -o \
            -iname '*review*bundle*' -o \
            -iname '*rebinding*policy*' \
        \) \
        -print 2>/dev/null \
        | LC_ALL=C sort

    printf '\n[MATCHING_PYTHON_ENTRYPOINTS]\n'
    find scripts -maxdepth 2 -type f -name '*.py' -print0 2>/dev/null \
        | xargs -0 -r grep -IlE \
            'candidate-manifest|dependency-closure|downstream-rebinding-plan|release_rebinding|manifest_candidate' \
        | LC_ALL=C sort

    printf '\n[USAGE_LINES]\n'
    while IFS= read -r file; do
        [[ -n "$file" ]] || continue
        printf '\n--- %s ---\n' "$file"
        grep -nE \
            'argparse|ArgumentParser|add_argument|POLICY_PATH|MANIFEST_PATH|CANDIDATE|DEPENDENCY|DOWNSTREAM|REVIEW_BUNDLE|if __name__' \
            "$file" 2>/dev/null \
            | head -n 120 || true
    done < <(
        find scripts -maxdepth 2 -type f -name '*.py' -print0 2>/dev/null \
            | xargs -0 -r grep -IlE \
                'candidate-manifest|dependency-closure|downstream-rebinding-plan|release_rebinding|manifest_candidate' \
            | LC_ALL=C sort
    )

    printf '\n[RELEVANT_FILE_SHA256]\n'
    while IFS= read -r file; do
        [[ -f "$file" ]] || continue
        sha256sum "$file"
    done < <(
        find scripts config tests app \
            -type f \
            \( \
                -iname '*slack*worker*release*' -o \
                -iname '*manifest*candidate*' -o \
                -iname '*dependency*closure*' -o \
                -iname '*downstream*rebinding*' -o \
                -iname '*review*bundle*' -o \
                -iname '*rebinding*policy*' \
            \) \
            -print 2>/dev/null \
            | LC_ALL=C sort
    )
} > "$INVENTORY_TXT"

APPROVAL_SHA="$(sha256_file "$APPROVAL_JSON")"
INVENTORY_SHA="$(sha256_file "$INVENTORY_TXT")"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
MANIFEST_AFTER="$(sha256_file "$MANIFEST_PATH")"
DB_AFTER="$(sha256_file "$DB_PATH")"

if [[ "$SOURCE_AFTER" != "$EXPECTED_SOURCE_SHA" ]]; then
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
    exit 1
fi
if [[ "$MANIFEST_AFTER" != "$EXPECTED_MANIFEST_SHA" ]]; then
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
fi
if [[ "$DB_AFTER" != "$EXPECTED_DB_SHA" ]]; then
    printf 'ERROR=PRODUCTION_DB_CONTENT_CHANGED\n' >&2
    exit 1
fi

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-0",
  "result": "PASS_W2B_I2F0_APPROVAL_RECORDED_AND_INVENTORY_READY",
  "approval": {
    "decision": "APPROVE_REBINDING_PREPARATION_ONLY",
    "preparation_gate": "APPROVED",
    "unit_workflow_state": "HOLD_FOR_PRODUCTION",
    "approval_record_sha256": "${APPROVAL_SHA}"
  },
  "inventory": {
    "path": "${OUTPUT_REL}/preparation-tool-inventory.txt",
    "sha256": "${INVENTORY_SHA}"
  },
  "production_safety": {
    "source_changed": false,
    "manifest_changed": false,
    "database_content_changed": false,
    "database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "output_root": "${OUTPUT_REL}",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F0_APPROVAL_RECORDED_AND_INVENTORY_READY\n'
printf 'PREPARATION_GATE=APPROVED\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'APPROVAL_RECORD_SHA=%s\n' "$APPROVAL_SHA"
printf 'INVENTORY_SHA=%s\n' "$INVENTORY_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'OUTPUT_ROOT=%s\n' "$OUTPUT_REL"
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
