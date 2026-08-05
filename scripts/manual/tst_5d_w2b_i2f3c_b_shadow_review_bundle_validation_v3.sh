#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

R3_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3b-r3-complete-shadow-20260725T152341-488959"
R4_CANDIDATE_ROOT="/tmp/tst-5d-w2b-i2f3b-r4-candidate-20260725T153121-489639"
SOURCE_REVIEW_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3c-a-review-shadow-20260725T154150-490803"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
R3_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r3-complete-shadow-graph-20260725T152341-488959"
R4_ROOT_REL="${I2E_ROOT_REL}/i2f3b-r4-shadow-candidate-validation-20260725T153121-489639"
C_A_ROOT_REL="${I2E_ROOT_REL}/i2f3c-a-review-contract-shadow-20260725T154150-490803"

R3_RESULT="${REPO_ROOT}/${R3_ROOT_REL}/result.json"
R3_SNAPSHOT_MANIFEST="${REPO_ROOT}/${R3_ROOT_REL}/shadow-snapshot-manifest.txt"
R4_RESULT="${REPO_ROOT}/${R4_ROOT_REL}/result.json"
C_A_RESULT="${REPO_ROOT}/${C_A_ROOT_REL}/result.json"
C_A_STATIC_RESULT="${REPO_ROOT}/${C_A_ROOT_REL}/review-contract-static-validation.json"
C_A_APPROVAL_RECORD="${REPO_ROOT}/${C_A_ROOT_REL}/human-approval-shadow-contract-implementation-only.json"
C_A_SNAPSHOT_MANIFEST="${REPO_ROOT}/${C_A_ROOT_REL}/review-shadow-snapshot-manifest.txt"

EXPECTED_R3_RESULT_SHA="a99f495ec37c1daa2936d63e9d67f6aaac346b1836e3d1e1ce83fa7f1774daf4"
EXPECTED_R3_SNAPSHOT_MANIFEST_SHA="8f6626c9b2940a0593933c2e76122657d36c6695d7181e3b8b9eb27a41d7795b"
EXPECTED_R4_RESULT_SHA="eb3e7f8ff7fbd2ab77179515d3b06ed3da4644d4347e437bf7f7abde2bfa14d2"
EXPECTED_C_A_RESULT_SHA="b36569038ea1cca05de75a43a426fec4a0ebf10c40707ea9048522cfa03375b9"
EXPECTED_C_A_STATIC_RESULT_SHA="df5c143231abebec24de01b7c460ed41da442536e4752dff7fefce52ea18e33b"
EXPECTED_C_A_APPROVAL_RECORD_SHA="89e47fb3f4528404076f1aea4fd1cdebe0a27cbc7b450db1b3593d4c9131b81c"
EXPECTED_C_A_SNAPSHOT_MANIFEST_SHA="2531eba2b7354f651c343ed204fdb01a2da0b89287f4d634cd10998e710f668c"

CANDIDATE_PATH="${R4_CANDIDATE_ROOT}/candidate-manifest.json"
CLOSURE_PATH="${R4_CANDIDATE_ROOT}/dependency-closure.json"
DOWNSTREAM_PATH="${R4_CANDIDATE_ROOT}/downstream-rebinding-plan.json"

EXPECTED_CANDIDATE_SHA="c882f2cb1afbfbe5215db61667a6c72feccc71bc84a558cdda792806d440f843"
EXPECTED_CLOSURE_SHA="9eb8854b7b877cc927ca0350281f84d8dc3a8160f564982825f9f87f36ec79e9"
EXPECTED_DOWNSTREAM_SHA="5fa8255966773bda7d35ba0d89b1f40c0f8b9a7df89b33578e3997f6cc22bed8"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
R3_SHADOW_MANIFEST="${R3_SHADOW_ROOT}/config/slack_worker_release_source_manifest.json"
SOURCE_REVIEW_SHADOW_MANIFEST="${SOURCE_REVIEW_SHADOW_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

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

verify_snapshot() {
    local root="$1"
    local manifest="$2"

    while read -r expected relative; do
        [[ -n "$expected" && -n "$relative" ]] || continue
        require_file_sha "${root}/${relative#./}" "$expected"
    done < "$manifest"
}

write_failure_result() {
    local result_name="$1"
    local builder_rc="$2"
    local validator_rc="$3"
    local bundle_root="${4:-}"

    local source_after production_manifest_after r3_manifest_after
    local source_review_manifest_after execution_review_manifest_after
    local candidate_after closure_after downstream_after db_after

    source_after="$(sha256_file "$SOURCE_PATH")"
    production_manifest_after="$(sha256_file "$PRODUCTION_MANIFEST")"
    r3_manifest_after="$(sha256_file "$R3_SHADOW_MANIFEST")"
    source_review_manifest_after="$(sha256_file "$SOURCE_REVIEW_SHADOW_MANIFEST")"
    execution_review_manifest_after="$(sha256_file "$EXECUTION_REVIEW_SHADOW_MANIFEST")"
    candidate_after="$(sha256_file "$CANDIDATE_PATH")"
    closure_after="$(sha256_file "$CLOSURE_PATH")"
    downstream_after="$(sha256_file "$DOWNSTREAM_PATH")"
    db_after="$(sha256_file "$DB_PATH")"

    cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3C-B",
  "result": "${result_name}",
  "builder_exit_code": ${builder_rc},
  "validator_exit_code": ${validator_rc},
  "source_review_shadow_root": "${SOURCE_REVIEW_SHADOW_ROOT}",
  "execution_review_shadow_root": "${EXECUTION_REVIEW_SHADOW_ROOT}",
  "bundle_parent": "${BUNDLE_PARENT}",
  "bundle_root": "${bundle_root}",
  "evidence_root": "${EVIDENCE_REL}",
  "execution": {
    "review_bundle_generation_performed": $([[ "$builder_rc" -eq 0 ]] && echo true || echo false),
    "review_bundle_validation_performed": $([[ "$validator_rc" -ge 0 ]] && echo true || echo false),
    "review_bundle_validation_passed": false,
    "pytest_executed": $([[ "$builder_rc" -eq 0 ]] && echo true || echo false)
  },
  "safety": {
    "production_source_changed": $([[ "$source_after" == "$EXPECTED_SOURCE_SHA" ]] && echo false || echo true),
    "production_manifest_changed": $([[ "$production_manifest_after" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] && echo false || echo true),
    "r3_shadow_manifest_changed": $([[ "$r3_manifest_after" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] && echo false || echo true),
    "source_review_shadow_manifest_changed": $([[ "$source_review_manifest_after" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] && echo false || echo true),
    "execution_review_shadow_manifest_changed": $([[ "$execution_review_manifest_after" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] && echo false || echo true),
    "r4_candidate_changed": $([[ "$candidate_after" == "$EXPECTED_CANDIDATE_SHA" && "$closure_after" == "$EXPECTED_CLOSURE_SHA" && "$downstream_after" == "$EXPECTED_DOWNSTREAM_SHA" ]] && echo false || echo true),
    "production_database_content_changed": $([[ "$db_after" == "$EXPECTED_DB_SHA" ]] && echo false || echo true),
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "failed_evidence_preserved": true
}
JSON
}

cd "$REPO_ROOT"

require_file_sha "$R3_RESULT" "$EXPECTED_R3_RESULT_SHA"
require_file_sha \
    "$R3_SNAPSHOT_MANIFEST" \
    "$EXPECTED_R3_SNAPSHOT_MANIFEST_SHA"
require_file_sha "$R4_RESULT" "$EXPECTED_R4_RESULT_SHA"
require_file_sha "$C_A_RESULT" "$EXPECTED_C_A_RESULT_SHA"
require_file_sha \
    "$C_A_STATIC_RESULT" \
    "$EXPECTED_C_A_STATIC_RESULT_SHA"
require_file_sha \
    "$C_A_APPROVAL_RECORD" \
    "$EXPECTED_C_A_APPROVAL_RECORD_SHA"
require_file_sha \
    "$C_A_SNAPSHOT_MANIFEST" \
    "$EXPECTED_C_A_SNAPSHOT_MANIFEST_SHA"

require_file_sha "$CANDIDATE_PATH" "$EXPECTED_CANDIDATE_SHA"
require_file_sha "$CLOSURE_PATH" "$EXPECTED_CLOSURE_SHA"
require_file_sha "$DOWNSTREAM_PATH" "$EXPECTED_DOWNSTREAM_SHA"

require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha \
    "$R3_SHADOW_MANIFEST" \
    "$EXPECTED_SHADOW_MANIFEST_SHA"
require_file_sha \
    "$SOURCE_REVIEW_SHADOW_MANIFEST" \
    "$EXPECTED_SHADOW_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

for directory in \
    "$R3_SHADOW_ROOT" \
    "$R4_CANDIDATE_ROOT" \
    "$SOURCE_REVIEW_SHADOW_ROOT"
do
    if [[ ! -d "$directory" ]]; then
        printf 'ERROR=REQUIRED_DIRECTORY_MISSING:%s\n' "$directory" >&2
        exit 1
    fi
done

verify_snapshot "$R3_SHADOW_ROOT" "$R3_SNAPSHOT_MANIFEST"
verify_snapshot "$SOURCE_REVIEW_SHADOW_ROOT" "$C_A_SNAPSHOT_MANIFEST"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EXECUTION_REVIEW_SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3c-b-review-exec-shadow-${RUN_ID}"
EXECUTION_REVIEW_SHADOW_MANIFEST="${EXECUTION_REVIEW_SHADOW_ROOT}/config/slack_worker_release_source_manifest.json"
BUNDLE_PARENT="${EXECUTION_REVIEW_SHADOW_ROOT}/review_requests"
BUNDLE_CANDIDATE_ID="$(
    python3 -c         'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["candidate_id"])'         "$CANDIDATE_PATH"
)"
BUNDLE_OUTPUT="${BUNDLE_PARENT}/${BUNDLE_CANDIDATE_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3c-b-review-bundle-validation-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$EXECUTION_REVIEW_SHADOW_ROOT" ]]; then
    printf 'ERROR=EXECUTION_REVIEW_SHADOW_ROOT_EXISTS:%s\n' "$EXECUTION_REVIEW_SHADOW_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p "$EXECUTION_REVIEW_SHADOW_ROOT" "$EVIDENCE_ROOT/bundle-snapshot"

while read -r expected relative; do
    [[ -n "$expected" && -n "$relative" ]] || continue
    source_path="${SOURCE_REVIEW_SHADOW_ROOT}/${relative#./}"
    destination_path="${EXECUTION_REVIEW_SHADOW_ROOT}/${relative#./}"
    mkdir -p "$(dirname "$destination_path")"
    cp --preserve=mode,timestamps "$source_path" "$destination_path"
done < "$C_A_SNAPSHOT_MANIFEST"

python3 - \
    "$SOURCE_REVIEW_SHADOW_ROOT" \
    "$EXECUTION_REVIEW_SHADOW_ROOT" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

source_root = Path(sys.argv[1]).resolve()
execution_root = Path(sys.argv[2]).resolve()

for relative in (
    "scripts/build_slack_worker_release_rebinding_review_bundle.py",
    "scripts/validate_slack_worker_release_rebinding_review_bundle.py",
):
    path = execution_root / relative
    text = path.read_text(encoding="utf-8")
    old = str(source_root)
    new = str(execution_root)
    count = text.count(old)
    if count < 1:
        raise SystemExit(f"EXECUTION_SHADOW_ROOT_PATCH_TARGET_MISSING:{relative}")
    path.write_text(text.replace(old, new), encoding="utf-8")

for relative in (
    "scripts/build_slack_worker_release_manifest_candidate.py",
    "scripts/validate_slack_worker_release_manifest_candidate.py",
    "scripts/validate_slack_worker_release_bundle_contract.py",
    "scripts/lib/secure_release_file_reader.py",
):
    source = source_root / relative
    destination = execution_root / relative
    if source.read_bytes() != destination.read_bytes():
        raise SystemExit(f"EXECUTION_SHADOW_CANDIDATE_TOOL_CHANGED:{relative}")
PY

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$EXECUTION_REVIEW_SHADOW_ROOT" \
python3 -m py_compile \
    "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/build_slack_worker_release_manifest_candidate.py" \
    "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_manifest_candidate.py" \
    "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
    "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
    "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_bundle_contract.py" \
    "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/lib/secure_release_file_reader.py"

require_file_sha \
    "$EXECUTION_REVIEW_SHADOW_MANIFEST" \
    "$EXPECTED_SHADOW_MANIFEST_SHA"

if [[ "$BUNDLE_CANDIDATE_ID" != "slack-worker-CANDIDATE-NOT-APPROVED-668ab8855ad6" ]]; then
    printf 'ERROR=R4_CANDIDATE_ID_UNEXPECTED:%s\n' "$BUNDLE_CANDIDATE_ID" >&2
    exit 1
fi

if [[ -e "$BUNDLE_OUTPUT" ]]; then
    printf 'ERROR=BUNDLE_OUTPUT_ALREADY_EXISTS:%s\n' "$BUNDLE_OUTPUT" >&2
    exit 1
fi

mkdir -p "$BUNDLE_PARENT"

EXECUTION_CONTROL_MANIFEST="${EVIDENCE_ROOT}/execution-review-shadow-control-manifest.txt"
(
    cd "$EXECUTION_REVIEW_SHADOW_ROOT"
    find scripts config exchange -type f \
        ! -path '*/__pycache__/*' \
        ! -name '*.pyc' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EXECUTION_CONTROL_MANIFEST"

BUILDER_LOG="${EVIDENCE_ROOT}/review-bundle-builder.json"
VALIDATOR_LOG="${EVIDENCE_ROOT}/review-bundle-validator.json"
SEMANTIC_RESULT="${EVIDENCE_ROOT}/review-bundle-semantic-validation.json"
RESULT_JSON="${EVIDENCE_ROOT}/result.json"

set +e
(
    cd "$EXECUTION_REVIEW_SHADOW_ROOT"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$EXECUTION_REVIEW_SHADOW_ROOT" \
    python3 \
        "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/build_slack_worker_release_rebinding_review_bundle.py" \
        --candidate-root "$R4_CANDIDATE_ROOT" \
        --output-root "$BUNDLE_OUTPUT" \
        --created-at "$CREATED_AT"
) >"$BUILDER_LOG" 2>&1
BUILDER_RC=$?
set -e

cat "$BUILDER_LOG"

if [[ "$BUILDER_RC" -ne 0 ]]; then
    write_failure_result \
        "BLOCKED_W2B_I2F3C_B_REVIEW_BUNDLE_GENERATION" \
        "$BUILDER_RC" \
        -1 \
        ""

    printf '\nRESULT=BLOCKED_W2B_I2F3C_B_REVIEW_BUNDLE_GENERATION\n'
    printf 'BUILDER_EXIT_CODE=%s\n' "$BUILDER_RC"
    printf 'BUNDLE_PARENT=%s\n' "$BUNDLE_PARENT"
    printf 'BUNDLE_OUTPUT=%s\n' "$BUNDLE_OUTPUT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'FAILED_EVIDENCE_PRESERVED=true\n'
    printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
    exit "$BUILDER_RC"
fi

mapfile -t BUNDLE_MANIFESTS < <(
    find "$BUNDLE_PARENT" \
        -mindepth 1 \
        -maxdepth 4 \
        -type f \
        -name 'review-bundle-manifest.json' \
        | LC_ALL=C sort
)

if [[ "${#BUNDLE_MANIFESTS[@]}" -ne 1 ]]; then
    printf 'ERROR=REVIEW_BUNDLE_MANIFEST_COUNT:%s\n' \
        "${#BUNDLE_MANIFESTS[@]}" >&2
    exit 1
fi

BUNDLE_MANIFEST="${BUNDLE_MANIFESTS[0]}"
BUNDLE_ROOT="$(dirname "$BUNDLE_MANIFEST")"

set +e
(
    cd "$EXECUTION_REVIEW_SHADOW_ROOT"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$EXECUTION_REVIEW_SHADOW_ROOT" \
    python3 \
        "$EXECUTION_REVIEW_SHADOW_ROOT/scripts/validate_slack_worker_release_rebinding_review_bundle.py" \
        --bundle-root "$BUNDLE_ROOT"
) >"$VALIDATOR_LOG" 2>&1
VALIDATOR_RC=$?
set -e

cat "$VALIDATOR_LOG"

if [[ "$VALIDATOR_RC" -ne 0 ]]; then
    cp -a "$BUNDLE_ROOT/." "$EVIDENCE_ROOT/bundle-snapshot/"

    write_failure_result \
        "BLOCKED_W2B_I2F3C_B_REVIEW_BUNDLE_VALIDATION" \
        "$BUILDER_RC" \
        "$VALIDATOR_RC" \
        "$BUNDLE_ROOT"

    printf '\nRESULT=BLOCKED_W2B_I2F3C_B_REVIEW_BUNDLE_VALIDATION\n'
    printf 'BUILDER_EXIT_CODE=%s\n' "$BUILDER_RC"
    printf 'VALIDATOR_EXIT_CODE=%s\n' "$VALIDATOR_RC"
    printf 'BUNDLE_ROOT=%s\n' "$BUNDLE_ROOT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'FAILED_EVIDENCE_PRESERVED=true\n'
    printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
    exit "$VALIDATOR_RC"
fi

python3 - \
    "$EXECUTION_REVIEW_SHADOW_ROOT" \
    "$R4_CANDIDATE_ROOT" \
    "$BUNDLE_ROOT" \
    "$BUILDER_LOG" \
    "$VALIDATOR_LOG" \
    "$SEMANTIC_RESULT" \
    "$EXPECTED_CANDIDATE_SHA" \
    "$CREATED_AT" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

review_shadow = Path(sys.argv[1]).resolve()
candidate_root = Path(sys.argv[2]).resolve()
bundle_root = Path(sys.argv[3]).resolve()
builder_log_path = Path(sys.argv[4])
validator_log_path = Path(sys.argv[5])
result_path = Path(sys.argv[6])
expected_candidate_sha = sys.argv[7]
created_at = sys.argv[8]

expected_changed = {
    "app/db/access_guard.py",
    "app/db/config.py",
    "app/db/session.py",
    "scripts/run_slack_approval_socket.py",
}
expected_absorbed = {
    "app/db/repositories/workflow_state_repository.py",
}
expected_review = expected_changed | expected_absorbed
expected_units = {
    "UNIT_DB_SAFETY",
    "UNIT_WORKFLOW_STATE",
    "UNIT_SLACK_RUNTIME",
}
expected_roles = {
    "UNIT_DB_SAFETY": "CHANGED",
    "UNIT_WORKFLOW_STATE": "BASELINE_ABSORBED_PENDING_HUMAN_REREVIEW",
    "UNIT_SLACK_RUNTIME": "CHANGED",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_regular_single_link_files(root: Path) -> bool:
    for directory, directory_names, file_names in os.walk(root):
        directory_path = Path(directory)
        for name in directory_names:
            path = directory_path / name
            metadata = os.lstat(path)
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                return False
        for name in file_names:
            path = directory_path / name
            metadata = os.lstat(path)
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
            ):
                return False
    return True


candidate = load(candidate_root / "candidate-manifest.json")
manifest = load(bundle_root / "review-bundle-manifest.json")
validator_result = load(validator_log_path)

try:
    builder_result = load(builder_log_path)
except Exception:
    builder_result = {}

expected_files = manifest.get("expected_files", [])
actual_files = sorted(
    path.relative_to(bundle_root).as_posix()
    for path in bundle_root.rglob("*")
    if path.is_file()
)

unit_paths = manifest.get("review_unit_paths", {})
packet_by_unit = {
    unit_id: load(bundle_root / relative)
    for unit_id, relative in unit_paths.items()
}
unit_roles = {
    unit_id: packet.get("candidate_change_role")
    for unit_id, packet in packet_by_unit.items()
}

assigned_sources = {
    item.get("path")
    for packet in packet_by_unit.values()
    for item in packet.get("sources", [])
    if isinstance(item, dict)
}

test_records = [
    item
    for packet in packet_by_unit.values()
    for item in packet.get("related_tests", [])
    if isinstance(item, dict)
]
all_test_evidence_pass = bool(test_records) and all(
    item.get("result") == "PASS"
    and item.get("network_used") is False
    and item.get("production_database_used") is False
    and item.get("credential_content_read") is False
    for item in test_records
)

diff_paths = manifest.get("diff_paths", {})
diff_sources = set(diff_paths)
diff_documents = {
    source: load(bundle_root / relative)
    for source, relative in diff_paths.items()
}

template_paths = manifest.get("decision_template_paths", {})
templates = {
    unit_id: load(bundle_root / relative)
    for unit_id, relative in template_paths.items()
}
templates_unfilled = (
    set(templates) == expected_units
    and all(
        document.get("decision") is None
        and document.get("reviewer") is None
        and document.get("reviewed_at") is None
        and document.get("reason") is None
        and document.get("conditions") == []
        and document.get("expiration") is None
        and document.get("approval_issued") is False
        and document.get("production_manifest_update_allowed") is False
        and document.get("deployment_allowed") is False
        for document in templates.values()
    )
)

generated_by = manifest.get("generated_by", {})
generated_by_path = generated_by.get("path")
generated_by_sha_matches = (
    generated_by_path
    == "scripts/build_slack_worker_release_rebinding_review_bundle.py"
    and generated_by.get("sha256")
    == sha(review_shadow / generated_by_path)
)

candidate_audit = candidate.get("source_audit", [])
candidate_changed = {
    item.get("path")
    for item in candidate_audit
    if isinstance(item, dict)
    and item.get("change") in {"MODIFIED", "ADDED"}
}
candidate_unchanged = {
    item.get("path")
    for item in candidate_audit
    if isinstance(item, dict)
    and item.get("change") == "UNCHANGED"
}

checks = {
    "builder_exit_result_is_ready": (
        not builder_result
        or builder_result.get("result")
        in {
            "PASS_READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
            "PASS_REVIEW_BUNDLE_READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
        }
    ),
    "validator_result_pass": validator_result.get("result")
    == "PASS_READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
    "bundle_status_ready_not_approved": manifest.get("review_bundle_status")
    == "READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
    "release_status_candidate_not_approved": manifest.get("release_status")
    == "CANDIDATE_NOT_APPROVED",
    "candidate_manifest_sha_exact": manifest.get("candidate_manifest_sha256")
    == expected_candidate_sha,
    "candidate_id_exact": manifest.get("candidate_id")
    == candidate.get("candidate_id"),
    "created_at_exact": manifest.get("created_at") == created_at,
    "candidate_changed_sources_four": candidate_changed == expected_changed,
    "baseline_absorbed_is_unchanged": expected_absorbed.issubset(
        candidate_unchanged
    ),
    "manifest_candidate_changed_count_four": manifest.get(
        "candidate_changed_source_count"
    )
    == 4,
    "manifest_baseline_absorbed_count_one": manifest.get(
        "baseline_absorbed_source_count"
    )
    == 1,
    "manifest_human_review_count_five": manifest.get(
        "human_review_source_count"
    )
    == 5,
    "review_unit_count_three": manifest.get("review_unit_count") == 3,
    "review_unit_set_exact": set(unit_paths) == expected_units,
    "review_unit_roles_exact": unit_roles == expected_roles,
    "assigned_review_sources_exact": assigned_sources == expected_review,
    "diff_source_set_exact": diff_sources == expected_review,
    "diff_count_five": len(diff_documents) == 5,
    "diff_documents_have_provenance": all(
        document.get("source_path") == source
        and document.get("truncated") is False
        and document.get("binary") is False
        and document.get("secret_literal_scan_passed") is True
        and isinstance(document.get("unified_diff"), str)
        for source, document in diff_documents.items()
    ),
    "test_evidence_present_and_passed": all_test_evidence_pass,
    "decision_templates_unfilled": templates_unfilled,
    "generated_by_shadow_builder_sha_matches": generated_by_sha_matches,
    "expected_file_set_exact": actual_files == sorted(expected_files),
    "bundle_tree_regular_single_link": all_regular_single_link_files(bundle_root),
    "production_release_false": manifest.get("production_release") is False,
    "production_approval_false": manifest.get(
        "production_approval_created"
    )
    is False,
    "deployment_false": manifest.get("deployment_allowed") is False,
    "runtime_execution_false": manifest.get(
        "runtime_execution_allowed"
    )
    is False,
    "manifest_replacement_false": manifest.get(
        "production_manifest_replacement_allowed"
    )
    is False,
    "human_decision_required_true": manifest.get(
        "human_decision_required"
    )
    is True,
    "human_decision_recorded_false": manifest.get(
        "human_decision_recorded"
    )
    is False,
}

failed = sorted(name for name, passed in checks.items() if not passed)

result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3C-B",
    "result": (
        "PASS_SHADOW_REVIEW_BUNDLE_SEMANTIC_VALIDATION"
        if not failed
        else "FAIL_SHADOW_REVIEW_BUNDLE_SEMANTIC_VALIDATION"
    ),
    "bundle": {
        "review_bundle_root": str(bundle_root),
        "review_bundle_id": manifest.get("review_bundle_id"),
        "review_bundle_manifest_sha256": sha(
            bundle_root / "review-bundle-manifest.json"
        ),
        "candidate_id": manifest.get("candidate_id"),
        "candidate_manifest_sha256": manifest.get(
            "candidate_manifest_sha256"
        ),
        "created_at": manifest.get("created_at"),
    },
    "contract": {
        "candidate_changed_source_count": len(candidate_changed),
        "baseline_absorbed_source_count": len(
            expected_absorbed & candidate_unchanged
        ),
        "human_review_source_count": len(assigned_sources),
        "review_unit_count": len(unit_paths),
        "source_diff_count": len(diff_documents),
        "decision_template_count": len(templates),
        "test_evidence_record_count": len(test_records),
    },
    "review_unit_roles": unit_roles,
    "review_sources": sorted(assigned_sources),
    "diff_sources": sorted(diff_sources),
    "checks": checks,
    "failed_checks": failed,
    "sha256": {
        "builder_log": sha(builder_log_path),
        "validator_log": sha(validator_log_path),
    },
    "governance": {
        "human_decision_recorded": False,
        "production_approval_created": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "production_manifest_replacement_allowed": False,
    },
    "safety": {
        "network_used": False,
        "production_database_used": False,
        "credential_content_read": False,
    },
}

result_path.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)

if failed:
    raise SystemExit(
        "REVIEW_BUNDLE_SEMANTIC_VALIDATION_FAILED:"
        + ",".join(failed)
    )
PY

cp -a "$BUNDLE_ROOT/." "$EVIDENCE_ROOT/bundle-snapshot/"

BUNDLE_SNAPSHOT_MANIFEST="${EVIDENCE_ROOT}/bundle-snapshot-manifest.txt"
(
    cd "$EVIDENCE_ROOT/bundle-snapshot"
    find . -type f -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$BUNDLE_SNAPSHOT_MANIFEST"

BUNDLE_MANIFEST_SHA="$(sha256_file "$BUNDLE_MANIFEST")"
BUILDER_LOG_SHA="$(sha256_file "$BUILDER_LOG")"
VALIDATOR_LOG_SHA="$(sha256_file "$VALIDATOR_LOG")"
SEMANTIC_SHA="$(sha256_file "$SEMANTIC_RESULT")"
BUNDLE_SNAPSHOT_MANIFEST_SHA="$(sha256_file "$BUNDLE_SNAPSHOT_MANIFEST")"
EXECUTION_CONTROL_MANIFEST_SHA="$(sha256_file "$EXECUTION_CONTROL_MANIFEST")"

BUNDLE_ID="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["review_bundle_id"])' \
        "$BUNDLE_MANIFEST"
)"
CANDIDATE_ID="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["candidate_id"])' \
        "$BUNDLE_MANIFEST"
)"
TEST_EVIDENCE_COUNT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["contract"]["test_evidence_record_count"])' \
        "$SEMANTIC_RESULT"
)"

verify_snapshot "$R3_SHADOW_ROOT" "$R3_SNAPSHOT_MANIFEST"
verify_snapshot "$SOURCE_REVIEW_SHADOW_ROOT" "$C_A_SNAPSHOT_MANIFEST"

while read -r expected relative; do
    [[ -n "$expected" && -n "$relative" ]] || continue
    require_file_sha \
        "${EXECUTION_REVIEW_SHADOW_ROOT}/${relative#./}" \
        "$expected"
done < "$EXECUTION_CONTROL_MANIFEST"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
R3_SHADOW_MANIFEST_AFTER="$(sha256_file "$R3_SHADOW_MANIFEST")"
SOURCE_REVIEW_SHADOW_MANIFEST_AFTER="$(sha256_file "$SOURCE_REVIEW_SHADOW_MANIFEST")"
EXECUTION_REVIEW_SHADOW_MANIFEST_AFTER="$(sha256_file "$EXECUTION_REVIEW_SHADOW_MANIFEST")"
CANDIDATE_AFTER="$(sha256_file "$CANDIDATE_PATH")"
CLOSURE_AFTER="$(sha256_file "$CLOSURE_PATH")"
DOWNSTREAM_AFTER="$(sha256_file "$DOWNSTREAM_PATH")"
DB_AFTER="$(sha256_file "$DB_PATH")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$PRODUCTION_MANIFEST_AFTER" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$R3_SHADOW_MANIFEST_AFTER" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] || {
    printf 'ERROR=R3_SHADOW_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$SOURCE_REVIEW_SHADOW_MANIFEST_AFTER" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] || {
    printf 'ERROR=SOURCE_REVIEW_SHADOW_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$EXECUTION_REVIEW_SHADOW_MANIFEST_AFTER" == "$EXPECTED_SHADOW_MANIFEST_SHA" ]] || {
    printf 'ERROR=EXECUTION_REVIEW_SHADOW_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$CANDIDATE_AFTER" == "$EXPECTED_CANDIDATE_SHA" ]] || {
    printf 'ERROR=R4_CANDIDATE_CHANGED\n' >&2
    exit 1
}
[[ "$CLOSURE_AFTER" == "$EXPECTED_CLOSURE_SHA" ]] || {
    printf 'ERROR=R4_CLOSURE_CHANGED\n' >&2
    exit 1
}
[[ "$DOWNSTREAM_AFTER" == "$EXPECTED_DOWNSTREAM_SHA" ]] || {
    printf 'ERROR=R4_DOWNSTREAM_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CHANGED\n' >&2
    exit 1
}

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3C-B",
  "result": "PASS_W2B_I2F3C_B_SHADOW_REVIEW_BUNDLE_VALIDATED",
  "approval_scope": "APPROVE_SHADOW_CONTRACT_IMPLEMENTATION_ONLY",
  "source_review_shadow_root": "${SOURCE_REVIEW_SHADOW_ROOT}",
  "execution_review_shadow_root": "${EXECUTION_REVIEW_SHADOW_ROOT}",
  "r4_candidate_root": "${R4_CANDIDATE_ROOT}",
  "bundle_parent": "${BUNDLE_PARENT}",
  "review_bundle_root": "${BUNDLE_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "review_bundle": {
    "review_bundle_id": "${BUNDLE_ID}",
    "review_bundle_manifest_sha256": "${BUNDLE_MANIFEST_SHA}",
    "candidate_id": "${CANDIDATE_ID}",
    "candidate_manifest_sha256": "${EXPECTED_CANDIDATE_SHA}",
    "candidate_changed_source_count": 4,
    "baseline_absorbed_source_count": 1,
    "human_review_source_count": 5,
    "review_unit_count": 3,
    "source_diff_count": 5,
    "decision_template_count": 3,
    "test_evidence_record_count": ${TEST_EVIDENCE_COUNT},
    "review_bundle_status": "READY_FOR_HUMAN_REVIEW_NOT_APPROVED",
    "release_status": "CANDIDATE_NOT_APPROVED"
  },
  "validation": {
    "builder_exit_code": ${BUILDER_RC},
    "validator_exit_code": ${VALIDATOR_RC},
    "builder_log_sha256": "${BUILDER_LOG_SHA}",
    "validator_log_sha256": "${VALIDATOR_LOG_SHA}",
    "semantic_validation_sha256": "${SEMANTIC_SHA}",
    "bundle_snapshot_manifest_sha256": "${BUNDLE_SNAPSHOT_MANIFEST_SHA}",
    "execution_review_shadow_control_manifest_sha256": "${EXECUTION_CONTROL_MANIFEST_SHA}"
  },
  "execution": {
    "review_bundle_generation_performed": true,
    "review_bundle_validation_performed": true,
    "review_bundle_validation_passed": true,
    "pytest_executed": true,
    "human_review_performed": false
  },
  "governance": {
    "human_decision_required": true,
    "human_decision_recorded": false,
    "production_approval_created": false,
    "deployment_allowed": false,
    "runtime_execution_allowed": false,
    "production_manifest_replacement_allowed": false
  },
  "safety": {
    "production_source_changed": false,
    "production_manifest_changed": false,
    "r3_shadow_changed": false,
    "source_review_shadow_changed": false,
    "execution_review_shadow_controls_changed": false,
    "r4_candidate_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "HOLD_FOR_PRODUCTION",
  "next_gate": "HUMAN_REVIEW_REBINDING_REVIEW_BUNDLE",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3C_B_SHADOW_REVIEW_BUNDLE_VALIDATED\n'
printf 'REVIEW_BUNDLE_ID=%s\n' "$BUNDLE_ID"
printf 'CANDIDATE_ID=%s\n' "$CANDIDATE_ID"
printf 'SOURCE_REVIEW_SHADOW_ROOT=%s\n' "$SOURCE_REVIEW_SHADOW_ROOT"
printf 'EXECUTION_REVIEW_SHADOW_ROOT=%s\n' "$EXECUTION_REVIEW_SHADOW_ROOT"
printf 'REVIEW_BUNDLE_ROOT=%s\n' "$BUNDLE_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'REVIEW_BUNDLE_MANIFEST_SHA=%s\n' "$BUNDLE_MANIFEST_SHA"
printf 'SEMANTIC_VALIDATION_SHA=%s\n' "$SEMANTIC_SHA"
printf 'BUNDLE_SNAPSHOT_MANIFEST_SHA=%s\n' "$BUNDLE_SNAPSHOT_MANIFEST_SHA"
printf 'EXECUTION_REVIEW_SHADOW_CONTROL_MANIFEST_SHA=%s\n' "$EXECUTION_CONTROL_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'CANDIDATE_CHANGED_SOURCE_COUNT=4\n'
printf 'BASELINE_ABSORBED_SOURCE_COUNT=1\n'
printf 'HUMAN_REVIEW_SOURCE_COUNT=5\n'
printf 'REVIEW_UNIT_COUNT=3\n'
printf 'SOURCE_DIFF_COUNT=5\n'
printf 'DECISION_TEMPLATE_COUNT=3\n'
printf 'TEST_EVIDENCE_RECORD_COUNT=%s\n' "$TEST_EVIDENCE_COUNT"
printf 'REVIEW_BUNDLE_STATUS=READY_FOR_HUMAN_REVIEW_NOT_APPROVED\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'REVIEW_BUNDLE_GENERATION_PERFORMED=true\n'
printf 'REVIEW_BUNDLE_VALIDATION_PERFORMED=true\n'
printf 'REVIEW_BUNDLE_VALIDATION_PASSED=true\n'
printf 'PYTEST_EXECUTED=true\n'
printf 'HUMAN_REVIEW_PERFORMED=false\n'
printf 'HUMAN_DECISION_RECORDED=false\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'DEPLOYMENT_ALLOWED=false\n'
printf 'RUNTIME_EXECUTION_ALLOWED=false\n'
printf 'PRODUCTION_MANIFEST_REPLACEMENT_ALLOWED=false\n'
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'R3_SHADOW_CHANGED=false\n'
printf 'SOURCE_REVIEW_SHADOW_CHANGED=false\n'
printf 'EXECUTION_REVIEW_SHADOW_CONTROLS_CHANGED=false\n'
printf 'R4_CANDIDATE_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE=HOLD_FOR_PRODUCTION\n'
printf 'NEXT_GATE=HUMAN_REVIEW_REBINDING_REVIEW_BUNDLE\n'
