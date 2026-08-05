#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
I2F0_ROOT_REL="${I2E_ROOT_REL}/approval-rebinding-preparation-only-20260725T142358-486003"
I2F0_ROOT="${REPO_ROOT}/${I2F0_ROOT_REL}"

APPROVAL_PATH="${I2F0_ROOT}/human-approval.json"
EXPECTED_APPROVAL_SHA="a73ec08108e1add5e6aaeadd5f85e34798af237f18ced24b09bfeae2d3129026"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
MANIFEST_PATH="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"
REBINDING_POLICY_PATH="${REPO_ROOT}/config/slack_worker_release_rebinding_policy.json"
REVIEW_POLICY_PATH="${REPO_ROOT}/config/slack_worker_release_rebinding_review_policy.json"

SHADOW_MANIFEST="/tmp/tst-5d-w2b-i2d-resume-shadow-20260725T131303/config/slack_worker_release_source_manifest.json"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_SHADOW_MANIFEST_SHA="f302b7f16237bafeee3ac0f66fa5d0327ffd06359b12b5ab1b8ff1a3cb9062c7"

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
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha "$MANIFEST_PATH" "$EXPECTED_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"
require_file_sha "$SHADOW_MANIFEST" "$EXPECTED_SHADOW_MANIFEST_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
OUTPUT_REL="${I2E_ROOT_REL}/i2f2-shadow-contract-design-${RUN_ID}"
OUTPUT_DIR="${REPO_ROOT}/${OUTPUT_REL}"

if [[ -e "$OUTPUT_DIR" ]]; then
    printf 'ERROR=OUTPUT_ALREADY_EXISTS:%s\n' "$OUTPUT_REL" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

DESIGN_JSON="${OUTPUT_DIR}/shadow-contract-design.json"
DELTA_JSON="${OUTPUT_DIR}/contract-delta-analysis.json"
WORKFLOW_JSON="${OUTPUT_DIR}/unit-workflow-state-fix1-review-contract.json"
IMPLEMENTATION_JSON="${OUTPUT_DIR}/shadow-implementation-plan.json"
SUMMARY_MD="${OUTPUT_DIR}/human-review-summary.md"
RESULT_JSON="${OUTPUT_DIR}/result.json"

python3 - "$REPO_ROOT" "$SHADOW_MANIFEST" "$OUTPUT_DIR" <<'PY'
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1])
shadow_manifest_path = Path(sys.argv[2])
out = Path(sys.argv[3])

source_rel = "app/db/repositories/workflow_state_repository.py"
source_path = repo / source_rel
production_manifest_path = repo / "config/slack_worker_release_source_manifest.json"
rebinding_policy_path = repo / "config/slack_worker_release_rebinding_policy.json"
review_policy_path = repo / "config/slack_worker_release_rebinding_review_policy.json"
candidate_validator_path = repo / "scripts/validate_slack_worker_release_manifest_candidate.py"
review_builder_path = repo / "scripts/build_slack_worker_release_rebinding_review_bundle.py"
review_validator_path = repo / "scripts/validate_slack_worker_release_rebinding_review_bundle.py"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entry_by_path(manifest: dict[str, Any], relative: str) -> dict[str, Any]:
    entries = manifest.get("source_files")
    if not isinstance(entries, list):
        raise SystemExit("SOURCE_FILES_INVALID")
    for item in entries:
        if isinstance(item, dict) and item.get("path") == relative:
            return item
    raise SystemExit(f"SOURCE_ENTRY_MISSING:{relative}")


production_manifest = load(production_manifest_path)
shadow_manifest = load(shadow_manifest_path)
rebinding_policy = load(rebinding_policy_path)
review_policy = load(review_policy_path)

production_entry = entry_by_path(production_manifest, source_rel)
shadow_entry = entry_by_path(shadow_manifest, source_rel)
actual_source_sha = sha(source_path)

source_contract = review_policy.get("source_contract", {})
if not isinstance(source_contract, dict):
    raise SystemExit("REVIEW_SOURCE_CONTRACT_INVALID")
workflow_old_contract = source_contract.get(source_rel)
if not isinstance(workflow_old_contract, dict):
    raise SystemExit("WORKFLOW_SOURCE_CONTRACT_MISSING")

candidate_validator_text = candidate_validator_path.read_text(encoding="utf-8")
review_builder_text = review_builder_path.read_text(encoding="utf-8")
review_validator_text = review_validator_path.read_text(encoding="utf-8")

candidate_source_count_match = re.search(
    r'candidate\.get\("source_file_count"\)\s*!=\s*(\d+)',
    candidate_validator_text,
)
unchanged_count_match = re.search(
    r'len\(unchanged\)\s*!=\s*(\d+)',
    candidate_validator_text,
)
review_source_diff_match = re.search(
    r'"source_diff_count"\s*:\s*(\d+)',
    review_builder_text,
)

old_candidate_source_count = int(candidate_source_count_match.group(1)) if candidate_source_count_match else None
old_unchanged_count = int(unchanged_count_match.group(1)) if unchanged_count_match else None
old_review_source_diff_count = int(review_source_diff_match.group(1)) if review_source_diff_match else None

changed_sources = [
    "app/db/access_guard.py",
    "app/db/config.py",
    "app/db/session.py",
    "scripts/run_slack_approval_socket.py",
]
baseline_absorbed_sources = [source_rel]
all_review_sources = [*changed_sources[:3], source_rel, changed_sources[3]]

design = {
    "schema_version": "slack_worker_shadow_contract_design_v1",
    "phase": "TST-5D-W2B-I2F-2",
    "status": "DESIGN_READY_NOT_EXECUTED_NOT_APPROVED_FOR_PRODUCTION",
    "contract_model": "FOUR_CANDIDATE_DELTAS_PLUS_ONE_BASELINE_ABSORBED_REVIEW_SOURCE",
    "candidate_baseline": {
        "type": "SHADOW_MANIFEST_ONLY",
        "path": str(shadow_manifest_path),
        "sha256": sha(shadow_manifest_path),
        "production_manifest_replacement_allowed": False,
    },
    "candidate_change_classification": {
        "candidate_changed_source_count": 4,
        "candidate_changed_sources": changed_sources,
        "baseline_absorbed_source_count": 1,
        "baseline_absorbed_sources": baseline_absorbed_sources,
        "candidate_unchanged_source_count": 13,
        "candidate_source_file_count": 17,
    },
    "human_review_contract": {
        "review_unit_count": 3,
        "review_units": [
            {
                "unit_id": "UNIT_DB_SAFETY",
                "candidate_change_role": "CHANGED",
                "sources": changed_sources[:3],
            },
            {
                "unit_id": "UNIT_WORKFLOW_STATE",
                "candidate_change_role": "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW",
                "sources": baseline_absorbed_sources,
            },
            {
                "unit_id": "UNIT_SLACK_RUNTIME",
                "candidate_change_role": "CHANGED",
                "sources": changed_sources[3:],
            },
        ],
        "human_review_source_diff_count": 5,
        "human_review_sources": all_review_sources,
        "production_approval_created": False,
        "human_decision_recorded": False,
    },
    "required_semantic_invariant": {
        "changed_sources_must_equal": changed_sources,
        "baseline_absorbed_sources_must_equal": baseline_absorbed_sources,
        "assigned_review_sources_must_equal": all_review_sources,
        "changed_and_baseline_absorbed_must_be_disjoint": True,
        "all_candidate_sources_partitioned": True,
    },
    "governance": {
        "preparation_gate": "APPROVED",
        "unit_workflow_state": "HOLD_FOR_PRODUCTION",
        "production_manifest_modified": False,
        "production_database_accessed": False,
        "migration_applied": False,
        "deployment_performed": False,
        "external_network_used": False,
    },
}

delta = {
    "schema_version": "slack_worker_contract_delta_analysis_v1",
    "phase": "TST-5D-W2B-I2F-2",
    "old_contract": {
        "candidate_expected_changed_source_count": 5,
        "candidate_expected_unchanged_source_count": old_unchanged_count,
        "candidate_source_file_count": old_candidate_source_count,
        "review_unit_count": 3,
        "review_source_diff_count": old_review_source_diff_count,
        "workflow_review_policy_current_sha256": workflow_old_contract.get("current_sha256"),
        "workflow_review_policy_baseline_sha256": workflow_old_contract.get("baseline_sha256"),
    },
    "observed_current_state": {
        "production_manifest_workflow_sha256": production_entry.get("sha256"),
        "shadow_manifest_workflow_sha256": shadow_entry.get("sha256"),
        "actual_workflow_source_sha256": actual_source_sha,
        "shadow_baseline_absorption_confirmed": shadow_entry.get("sha256") == actual_source_sha,
        "old_review_policy_current_sha_is_stale": workflow_old_contract.get("current_sha256") != actual_source_sha,
    },
    "new_shadow_contract": {
        "candidate_expected_changed_source_count": 4,
        "candidate_expected_unchanged_source_count": 13,
        "candidate_baseline_absorbed_source_count": 1,
        "candidate_source_file_count": 17,
        "review_unit_count": 3,
        "human_review_source_diff_count": 5,
    },
    "conclusion": {
        "production_contract_can_be_reused_unchanged": False,
        "policy_only_shadow_rebind_is_sufficient": False,
        "shadow_validator_required": True,
        "shadow_review_policy_required": True,
        "shadow_review_builder_required": True,
        "shadow_review_validator_required": True,
        "candidate_builder_constant_redirection_required": True,
    },
}

workflow_contract = {
    "schema_version": "unit_workflow_state_fix1_review_contract_v1",
    "phase": "TST-5D-W2B-I2F-2",
    "unit_id": "UNIT_WORKFLOW_STATE",
    "candidate_change_role": "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW",
    "source": {
        "path": source_rel,
        "production_manifest_sha256": production_entry.get("sha256"),
        "shadow_manifest_sha256": shadow_entry.get("sha256"),
        "current_sha256": actual_source_sha,
    },
    "intended_behavior": {
        "wordpress_post_id_domain": "POSITIVE_ASCII_DECIMAL_INTEGER_ONLY",
        "accepted_runtime_types": ["int", "ASCII_DIGIT_STRING"],
        "canonical_representation": "DECIMAL_WITHOUT_LEADING_ZERO",
        "maximum_digits": 20,
        "reject": [
            "bool",
            "zero",
            "negative",
            "plus_or_minus_sign",
            "decimal",
            "whitespace",
            "unicode_digits",
            "leading_zero",
            "more_than_20_digits",
        ],
        "none_semantics": "UNBOUND_INPUT_ONLY_AND_CANNOT_CLEAR_EXISTING_BINDING",
        "same_binding": "IDEMPOTENT",
        "ordinary_rebind": "FORBIDDEN",
        "ordinary_clear": "FORBIDDEN",
        "global_non_null_uniqueness": "REQUIRED",
        "repository_precheck": True,
        "partial_unique_index": True,
    },
    "external_error_contract": [
        "WORDPRESS_POST_ID_INVALID",
        "WORDPRESS_POST_ID_TOO_LONG",
        "WORDPRESS_POST_ID_ALREADY_BOUND",
        "WORDPRESS_POST_ID_REBIND_FORBIDDEN",
        "WORDPRESS_POST_ID_UNIQUENESS_CONFLICT",
    ],
    "supporting_artifacts": [
        {
            "path": "migrations/versions/00241611109d_add_unique_wordpress_post_id.py",
            "role": "SCHEMA_MIGRATION_SUPPORTING_EVIDENCE_NOT_APPLIED",
        },
        {
            "path": "tests/test_x_r13_wordpress_state_reconciliation.py",
            "role": "COMPATIBILITY_AND_STATE_RECONCILIATION_EVIDENCE",
        },
    ],
    "explicitly_rejected_obsolete_review_policy_statements": [
        "None clears the value",
        "cross-item uniqueness is not enforced",
        "current_sha256=ac3fbddee5d3edf3cfd3368d5e3ed1ed40a4ff13d8655ad44847c55d4596bdd7",
    ],
    "approval": {
        "human_rereview_required": True,
        "production_approval_created": False,
        "migration_approval_created": False,
        "unit_workflow_state": "HOLD_FOR_PRODUCTION",
    },
}

implementation = {
    "schema_version": "slack_worker_shadow_implementation_plan_v1",
    "phase": "TST-5D-W2B-I2F-2",
    "status": "PREPARATION_PLAN_ONLY_NOT_EXECUTED",
    "shadow_root_requirement": "/tmp/<unique-i2f3-shadow-root>",
    "required_shadow_files": [
        {
            "source": "config/slack_worker_release_source_manifest.json",
            "shadow_action": "USE_EXISTING_I2D_SHADOW_MANIFEST_AS_BASELINE",
            "production_write": False,
        },
        {
            "source": "config/slack_worker_release_rebinding_policy.json",
            "shadow_action": "COPY_AND_REBIND_TO_SHADOW_MANIFEST",
            "production_write": False,
        },
        {
            "source": "config/slack_worker_release_rebinding_review_policy.json",
            "shadow_action": "REBUILD_SOURCE_CONTRACT_AND_FIX1_REVIEW_SEMANTICS",
            "production_write": False,
        },
        {
            "source": "scripts/build_slack_worker_release_manifest_candidate.py",
            "shadow_action": "COPY_AND_REDIRECT_MODULE_CONSTANTS_TO_SHADOW_POLICY_AND_MANIFEST",
            "production_write": False,
        },
        {
            "source": "scripts/validate_slack_worker_release_manifest_candidate.py",
            "shadow_action": "COPY_AND_IMPLEMENT_4_CHANGED_PLUS_1_ABSORBED_CONTRACT",
            "production_write": False,
        },
        {
            "source": "scripts/build_slack_worker_release_rebinding_review_bundle.py",
            "shadow_action": "COPY_AND_IMPORT_SHADOW_VALIDATOR_KEEP_3_UNITS_AND_5_REVIEW_DIFFS",
            "production_write": False,
        },
        {
            "source": "scripts/validate_slack_worker_release_rebinding_review_bundle.py",
            "shadow_action": "COPY_AND_VALIDATE_BASELINE_ABSORPTION_METADATA",
            "production_write": False,
        },
    ],
    "execution_sequence_for_next_phase": [
        "create_unique_shadow_root",
        "copy_required_files_without_overwrite",
        "patch_shadow_constants_and_contracts",
        "run_json_and_python_syntax_validation",
        "run_targeted_shadow_unit_tests_only",
        "generate_candidate_below_unique_tmp_root",
        "validate_candidate_with_shadow_validator",
        "generate_review_bundle_to_shadow_review_request_root",
        "validate_review_bundle_with_shadow_validator",
        "snapshot_outputs_into_immutable_evidence",
    ],
    "prohibited": [
        "production_manifest_write",
        "production_policy_write",
        "production_source_write",
        "production_database_connection",
        "production_database_write",
        "migration_apply",
        "deployment",
        "wordpress_network",
        "x_network",
        "slack_network",
        "slack_worker_start",
        "automatic_approval",
    ],
    "next_gate": "HUMAN_REVIEW_SHADOW_CONTRACT_DESIGN",
}

for name, value in [
    ("shadow-contract-design.json", design),
    ("contract-delta-analysis.json", delta),
    ("unit-workflow-state-fix1-review-contract.json", workflow_contract),
    ("shadow-implementation-plan.json", implementation),
]:
    (out / name).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

summary = f"""# TST-5D-W2B-I2F-2 Shadow Contract Design

## Result

- Contract model: `4 candidate deltas + 1 baseline-absorbed review source`
- Candidate changed sources: `4`
- Candidate unchanged sources: `13`
- Baseline-absorbed sources: `1`
- Human review units: `3`
- Human review source diffs: `5`

## Critical correction

`source_diff_count=5` remains valid for human review because the FIX1 workflow source
still requires human rereview against the production baseline. It must not be counted
as a candidate delta against the shadow baseline.

## Required implementation boundary

Production builders, validators, and policies cannot be reused unchanged.
A complete shadow toolchain is required under a unique `/tmp` root.

## Safety

- Production source modified: `false`
- Production manifest modified: `false`
- Production database opened: `false`
- Migration applied: `false`
- Deployment performed: `false`
- External network used: `false`
- UNIT_WORKFLOW_STATE: `HOLD_FOR_PRODUCTION`
"""
(out / "human-review-summary.md").write_text(summary, encoding="utf-8")
PY

for file in \
    "$DESIGN_JSON" \
    "$DELTA_JSON" \
    "$WORKFLOW_JSON" \
    "$IMPLEMENTATION_JSON" \
    "$SUMMARY_MD"
do
    python3 -m json.tool "$file" >/dev/null 2>&1 || {
        if [[ "$file" != "$SUMMARY_MD" ]]; then
            printf 'ERROR=JSON_VALIDATION_FAILED:%s\n' "$file" >&2
            exit 1
        fi
    }
done

DESIGN_SHA="$(sha256_file "$DESIGN_JSON")"
DELTA_SHA="$(sha256_file "$DELTA_JSON")"
WORKFLOW_SHA="$(sha256_file "$WORKFLOW_JSON")"
IMPLEMENTATION_SHA="$(sha256_file "$IMPLEMENTATION_JSON")"
SUMMARY_SHA="$(sha256_file "$SUMMARY_MD")"

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
  "phase": "TST-5D-W2B-I2F-2",
  "result": "PASS_W2B_I2F2_SHADOW_CONTRACT_DESIGN_READY",
  "contract_model": "FOUR_CANDIDATE_DELTAS_PLUS_ONE_BASELINE_ABSORBED_REVIEW_SOURCE",
  "counts": {
    "candidate_changed_source_count": 4,
    "candidate_unchanged_source_count": 13,
    "baseline_absorbed_source_count": 1,
    "review_unit_count": 3,
    "human_review_source_diff_count": 5
  },
  "artifacts": {
    "shadow_contract_design_sha256": "${DESIGN_SHA}",
    "contract_delta_analysis_sha256": "${DELTA_SHA}",
    "workflow_fix1_review_contract_sha256": "${WORKFLOW_SHA}",
    "shadow_implementation_plan_sha256": "${IMPLEMENTATION_SHA}",
    "human_review_summary_sha256": "${SUMMARY_SHA}"
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
  "next_gate": "HUMAN_REVIEW_SHADOW_CONTRACT_DESIGN",
  "output_root": "${OUTPUT_REL}",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F2_SHADOW_CONTRACT_DESIGN_READY\n'
printf 'CONTRACT_MODEL=4_CHANGED_PLUS_1_BASELINE_ABSORBED\n'
printf 'CANDIDATE_CHANGED_SOURCE_COUNT=4\n'
printf 'CANDIDATE_UNCHANGED_SOURCE_COUNT=13\n'
printf 'BASELINE_ABSORBED_SOURCE_COUNT=1\n'
printf 'REVIEW_UNIT_COUNT=3\n'
printf 'HUMAN_REVIEW_SOURCE_DIFF_COUNT=5\n'
printf 'SHADOW_IMPLEMENTATION_REQUIRED=true\n'
printf 'DESIGN_SHA=%s\n' "$DESIGN_SHA"
printf 'DELTA_SHA=%s\n' "$DELTA_SHA"
printf 'WORKFLOW_CONTRACT_SHA=%s\n' "$WORKFLOW_SHA"
printf 'IMPLEMENTATION_PLAN_SHA=%s\n' "$IMPLEMENTATION_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'OUTPUT_ROOT=%s\n' "$OUTPUT_REL"
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_GATE=HUMAN_REVIEW_SHADOW_CONTRACT_DESIGN\n'
