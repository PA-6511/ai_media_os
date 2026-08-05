#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
PREFLIGHT_ROOT_REL="${I2E_ROOT_REL}/i2f3e-a-production-release-preflight-inventory-20260725T170659-498762"
FINAL_REVIEW_ROOT_REL="${I2E_ROOT_REL}/i2f3d-c-slack-runtime-human-rereview-20260725T170114-498322"
SLACK_TEST_ROOT_REL="${I2E_ROOT_REL}/i2f3d-b-slack-hold-offline-tests-20260725T164615-497367"

PREFLIGHT_RESULT="${REPO_ROOT}/${PREFLIGHT_ROOT_REL}/result.json"
PREFLIGHT_INVENTORY="${REPO_ROOT}/${PREFLIGHT_ROOT_REL}/production-release-preflight-inventory.json"
MANIFEST_BINDING_ANALYSIS="${REPO_ROOT}/${PREFLIGHT_ROOT_REL}/manifest-binding-analysis.json"
RELEASE_GATE_MATRIX="${REPO_ROOT}/${PREFLIGHT_ROOT_REL}/production-release-gate-matrix.json"
PREFLIGHT_EVIDENCE_MANIFEST="${REPO_ROOT}/${PREFLIGHT_ROOT_REL}/preflight-evidence-manifest.txt"

FINAL_REVIEW_RESULT="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/result.json"
FINAL_DECISION_SET="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/final-human-review-decision-set.json"

SLACK_TEST_RESULT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/result.json"
SLACK_TEST_SNAPSHOT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/shadow-test-snapshot/test_slack_approval_socket_hold_remediation_offline.py"

EXPECTED_PREFLIGHT_RESULT_SHA="31264f0f9e7a29143571c3b063264d61693d547505cea458ec8b1ca4ca0cbb7c"
EXPECTED_PREFLIGHT_INVENTORY_SHA="bb86596b43ff809f30882bcde204fc22bd16bd1f33b45f0481605bd15da47b4e"
EXPECTED_MANIFEST_BINDING_ANALYSIS_SHA="5ff85888e61353208f6e7fb19acf9f6ee37d19350f83b3abbb4fc2c792030ace"
EXPECTED_RELEASE_GATE_MATRIX_SHA="07c0532976ceba772532466a0e397de398dcf9aec29cf90e0295619ba705c46d"
EXPECTED_PREFLIGHT_EVIDENCE_MANIFEST_SHA="e8cd39a3c864cecc4dfc41b47513216c875d5063fd0b83f2a6238c0cada13b83"

EXPECTED_FINAL_REVIEW_RESULT_SHA="2fe36ba4cdd0c84a61b3ac3f9f81912e7dc8549b43c2a54923214d7f588c97e6"
EXPECTED_FINAL_DECISION_SET_SHA="9b28a2581535f6e2d12b811a61b7ff67777d4199f8db3edd3fda1f729e29ed30"

EXPECTED_SLACK_TEST_RESULT_SHA="732840292f5c551d589ea8e9459fc677c9df0380fb4ef1f18d5eafa2f1c33ce0"
EXPECTED_SLACK_TEST_SNAPSHOT_SHA="5f4bc6709120998383543f346e504c4ab2c408c0dfd7219d1ff3f8a236a83184"

R4_CANDIDATE_ROOT="/tmp/tst-5d-w2b-i2f3b-r4-candidate-20260725T153121-489639"
CANDIDATE_MANIFEST="${R4_CANDIDATE_ROOT}/candidate-manifest.json"
DEPENDENCY_CLOSURE="${R4_CANDIDATE_ROOT}/dependency-closure.json"
DOWNSTREAM_PLAN="${R4_CANDIDATE_ROOT}/downstream-rebinding-plan.json"

EXPECTED_CANDIDATE_MANIFEST_SHA="c882f2cb1afbfbe5215db61667a6c72feccc71bc84a558cdda792806d440f843"
EXPECTED_DEPENDENCY_CLOSURE_SHA="9eb8854b7b877cc927ca0350281f84d8dc3a8160f564982825f9f87f36ec79e9"
EXPECTED_DOWNSTREAM_PLAN_SHA="5fa8255966773bda7d35ba0d89b1f40c0f8b9a7df89b33578e3997f6cc22bed8"

PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"
WORKFLOW_MIGRATION="${REPO_ROOT}/migrations/versions/00241611109d_add_unique_wordpress_post_id.py"

ACCESS_GUARD_SOURCE="${REPO_ROOT}/app/db/access_guard.py"
DB_CONFIG_SOURCE="${REPO_ROOT}/app/db/config.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
DB_SESSION_SOURCE="${REPO_ROOT}/app/db/session.py"
SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"

EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_WORKFLOW_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"

EXPECTED_ACCESS_GUARD_SHA="1584ac2975a39433fbf4670bbd2ea9974870866f6193cf8036f9528e72669583"
EXPECTED_DB_CONFIG_SHA="5eeef8af4343d1e16412df40945f19667ee0f41dcbdea4a9f74386f12f7ddd59"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_DB_SESSION_SHA="0d6a0c2de0f5ab4691eae5d1dc311bf7d800461b7949d5ef1895fbc4b5b1d818"
EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"

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

require_file_sha "$PREFLIGHT_RESULT" "$EXPECTED_PREFLIGHT_RESULT_SHA"
require_file_sha "$PREFLIGHT_INVENTORY" "$EXPECTED_PREFLIGHT_INVENTORY_SHA"
require_file_sha \
    "$MANIFEST_BINDING_ANALYSIS" \
    "$EXPECTED_MANIFEST_BINDING_ANALYSIS_SHA"
require_file_sha "$RELEASE_GATE_MATRIX" "$EXPECTED_RELEASE_GATE_MATRIX_SHA"
require_file_sha \
    "$PREFLIGHT_EVIDENCE_MANIFEST" \
    "$EXPECTED_PREFLIGHT_EVIDENCE_MANIFEST_SHA"

require_file_sha \
    "$FINAL_REVIEW_RESULT" \
    "$EXPECTED_FINAL_REVIEW_RESULT_SHA"
require_file_sha "$FINAL_DECISION_SET" "$EXPECTED_FINAL_DECISION_SET_SHA"

require_file_sha "$SLACK_TEST_RESULT" "$EXPECTED_SLACK_TEST_RESULT_SHA"
require_file_sha \
    "$SLACK_TEST_SNAPSHOT" \
    "$EXPECTED_SLACK_TEST_SNAPSHOT_SHA"

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
require_file_sha \
    "$WORKFLOW_MIGRATION" \
    "$EXPECTED_WORKFLOW_MIGRATION_SHA"

require_file_sha "$ACCESS_GUARD_SOURCE" "$EXPECTED_ACCESS_GUARD_SHA"
require_file_sha "$DB_CONFIG_SOURCE" "$EXPECTED_DB_CONFIG_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$DB_SESSION_SOURCE" "$EXPECTED_DB_SESSION_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3e-b-production-release-preparation-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3e-b-production-release-preparation-packet-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$SHADOW_ROOT" ]]; then
    printf 'ERROR=SHADOW_ROOT_EXISTS:%s\n' "$SHADOW_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p \
    "$SHADOW_ROOT/packet" \
    "$EVIDENCE_ROOT/packet-snapshot"

APPROVAL_VERBATIM="${SHADOW_ROOT}/packet/human-approval-verbatim.txt"

cat > "$APPROVAL_VERBATIM" <<'TXT'
承認：
APPROVE_PRODUCTION_RELEASE_PREPARATION_ONLY

承認範囲：
production manifest rebind案、
migration・DB preflight・deployment・rollback・Slack Worker運用の
準備資料を一意なshadow／evidence領域に生成することのみ承認する。

Slack HOLD解除用shadow testのrepository昇格については、
実施せず、昇格要否と最小差分案の作成のみ承認する。

禁止事項：
production manifest変更、production DB接続、SQL実行、
production migration適用、source/test変更、deployment、
Slack Worker起動、外部通信、production approval作成、
production release承認は引き続き禁止する。
TXT

python3 - \
    "$REPO_ROOT" \
    "$PREFLIGHT_RESULT" \
    "$PREFLIGHT_INVENTORY" \
    "$MANIFEST_BINDING_ANALYSIS" \
    "$RELEASE_GATE_MATRIX" \
    "$FINAL_DECISION_SET" \
    "$CANDIDATE_MANIFEST" \
    "$DEPENDENCY_CLOSURE" \
    "$DOWNSTREAM_PLAN" \
    "$PRODUCTION_MANIFEST" \
    "$WORKFLOW_MIGRATION" \
    "$SLACK_TEST_SNAPSHOT" \
    "$SHADOW_ROOT/packet" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PY'
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

repo = Path(sys.argv[1]).resolve()
preflight_result_path = Path(sys.argv[2]).resolve()
preflight_inventory_path = Path(sys.argv[3]).resolve()
manifest_analysis_path = Path(sys.argv[4]).resolve()
release_gate_matrix_path = Path(sys.argv[5]).resolve()
final_decision_set_path = Path(sys.argv[6]).resolve()
candidate_manifest_path = Path(sys.argv[7]).resolve()
dependency_closure_path = Path(sys.argv[8]).resolve()
downstream_plan_path = Path(sys.argv[9]).resolve()
production_manifest_path = Path(sys.argv[10]).resolve()
workflow_migration_path = Path(sys.argv[11]).resolve()
slack_test_snapshot_path = Path(sys.argv[12]).resolve()
packet_root = Path(sys.argv[13]).resolve()
expected_candidate_id = sys.argv[14]
expected_review_bundle_id = sys.argv[15]


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


def find_associated_objects(
    value: Any,
    *,
    source_path: str,
    source_sha: str,
    prefix: str = "$",
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        strings = [child for child in value.values() if isinstance(child, str)]
        if source_path in strings or source_sha in strings:
            found.append(
                {
                    "json_pointer": prefix,
                    "contains_source_path": source_path in strings,
                    "contains_current_sha256": source_sha in strings,
                    "keys": sorted(str(key) for key in value),
                }
            )
        for key, child in value.items():
            found.extend(
                find_associated_objects(
                    child,
                    source_path=source_path,
                    source_sha=source_sha,
                    prefix=f"{prefix}.{key}",
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                find_associated_objects(
                    child,
                    source_path=source_path,
                    source_sha=source_sha,
                    prefix=f"{prefix}[{index}]",
                )
            )
    return found


preflight_result = load_json(preflight_result_path)
preflight_inventory = load_json(preflight_inventory_path)
manifest_analysis = load_json(manifest_analysis_path)
release_gate_matrix = load_json(release_gate_matrix_path)
final_decision_set = load_json(final_decision_set_path)
candidate_manifest = load_json(candidate_manifest_path)
dependency_closure = load_json(dependency_closure_path)
downstream_plan = load_json(downstream_plan_path)
production_manifest = load_json(production_manifest_path)

if preflight_result.get("result") != (
    "PASS_W2B_I2F3E_A_PRODUCTION_RELEASE_PREFLIGHT_INVENTORY_READY"
):
    raise SystemExit("PREFLIGHT_RESULT_INVALID")
if preflight_result.get("candidate_id") != expected_candidate_id:
    raise SystemExit("PREFLIGHT_CANDIDATE_ID_MISMATCH")
if preflight_result.get("review_bundle_id") != expected_review_bundle_id:
    raise SystemExit("PREFLIGHT_REVIEW_BUNDLE_ID_MISMATCH")

if preflight_result.get("production_state", {}).get(
    "production_release_decision"
) != "HOLD":
    raise SystemExit("PRODUCTION_RELEASE_NOT_HOLD")
if preflight_result.get("production_state", {}).get(
    "production_release_ready"
) is not False:
    raise SystemExit("PRODUCTION_RELEASE_READY_UNEXPECTED")

if final_decision_set.get("record_status") != (
    "ALL_REVIEW_UNITS_APPROVED_REVIEW_ONLY"
):
    raise SystemExit("FINAL_REVIEW_STATUS_INVALID")
if final_decision_set.get("overall_review_scope") != (
    "SOURCE_AND_REBINDING_REVIEW_ONLY"
):
    raise SystemExit("FINAL_REVIEW_SCOPE_INVALID")
if final_decision_set.get("production_release_decision") != "HOLD":
    raise SystemExit("FINAL_PRODUCTION_RELEASE_NOT_HOLD")

if manifest_analysis.get(
    "production_manifest_rebind_preparation_required"
) is not True:
    raise SystemExit("MANIFEST_REBIND_PREPARATION_NOT_REQUIRED")
if manifest_analysis.get(
    "candidate_manifest_contains_all_current_source_shas"
) is not True:
    raise SystemExit("CANDIDATE_MANIFEST_BINDING_INCOMPLETE")

if release_gate_matrix.get("production_release_ready") is not False:
    raise SystemExit("RELEASE_GATE_MATRIX_READY_UNEXPECTED")
if release_gate_matrix.get("production_release_decision") != "HOLD":
    raise SystemExit("RELEASE_GATE_MATRIX_HOLD_INVALID")

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


def occurrences(items: list[tuple[str, str]], token: str) -> list[str]:
    return [path for path, value in items if token in value]


rebind_operations: list[dict[str, Any]] = []
for source_path, current_sha in known_sources.items():
    prod_path_occurrences = occurrences(production_strings, source_path)
    prod_sha_occurrences = occurrences(production_strings, current_sha)
    candidate_path_occurrences = occurrences(candidate_strings, source_path)
    candidate_sha_occurrences = occurrences(candidate_strings, current_sha)
    candidate_objects = find_associated_objects(
        candidate_manifest,
        source_path=source_path,
        source_sha=current_sha,
    )

    if prod_path_occurrences and prod_sha_occurrences:
        action = "VERIFY_EXISTING_BINDING"
    elif prod_path_occurrences:
        action = "REBIND_EXISTING_SOURCE"
    else:
        action = "ADD_SOURCE_BINDING"

    rebind_operations.append(
        {
            "source_path": source_path,
            "current_sha256": current_sha,
            "proposed_action": action,
            "production_manifest_path_occurrences": prod_path_occurrences,
            "production_manifest_current_sha_occurrences": prod_sha_occurrences,
            "candidate_manifest_path_occurrences": candidate_path_occurrences,
            "candidate_manifest_current_sha_occurrences": candidate_sha_occurrences,
            "candidate_association_objects": candidate_objects,
            "executable": False,
            "human_review_required": True,
        }
    )

manifest_rebind_proposal = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-B",
    "proposal_type": "NON_EXECUTABLE_PRODUCTION_MANIFEST_REBIND_SPECIFICATION",
    "status": "PREPARATION_ONLY_NOT_APPROVED_FOR_APPLICATION",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "production_manifest": {
        "path": str(production_manifest_path.relative_to(repo)),
        "sha256": sha(production_manifest_path),
        "modified": False,
    },
    "candidate_manifest": {
        "path": str(candidate_manifest_path),
        "sha256": sha(candidate_manifest_path),
    },
    "preconditions": [
        "A separate explicit production-manifest update approval is required.",
        "The production manifest SHA must still equal the recorded preflight SHA.",
        "Every proposed source path and SHA must be revalidated immediately before application.",
        "No production DB connection, migration, deployment, worker start, or network operation may be bundled into the manifest update.",
        "Rollback must restore the exact prior production manifest bytes and SHA.",
    ],
    "proposed_source_binding_operations": rebind_operations,
    "draft_manifest_generated": False,
    "production_manifest_write_performed": False,
    "application_allowed": False,
}
write_json(
    packet_root / "production-manifest-rebind-proposal.json",
    manifest_rebind_proposal,
)

manifest_diff_lines = [
    "PRODUCTION MANIFEST REBIND PROPOSAL — NON-EXECUTABLE",
    "",
    f"Production manifest SHA: {sha(production_manifest_path)}",
    f"Candidate manifest SHA:  {sha(candidate_manifest_path)}",
    "",
]
for operation in rebind_operations:
    manifest_diff_lines.extend(
        [
            f"SOURCE: {operation['source_path']}",
            f"ACTION: {operation['proposed_action']}",
            f"TARGET_SHA256: {operation['current_sha256']}",
            (
                "PRODUCTION_PATH_POINTERS: "
                + json.dumps(
                    operation["production_manifest_path_occurrences"],
                    ensure_ascii=False,
                )
            ),
            (
                "CANDIDATE_PATH_POINTERS: "
                + json.dumps(
                    operation["candidate_manifest_path_occurrences"],
                    ensure_ascii=False,
                )
            ),
            "APPLICATION_ALLOWED: false",
            "",
        ]
    )
(packet_root / "production-manifest-rebind-proposed-diff.txt").write_text(
    "\n".join(manifest_diff_lines) + "\n",
    encoding="utf-8",
)

migration_text = workflow_migration_path.read_text(encoding="utf-8")
revision_match = re.search(
    r"^\s*revision\s*(?::[^=]+)?=\s*[\"']([^\"']+)[\"']",
    migration_text,
    re.MULTILINE,
)
down_revision_match = re.search(
    r"^\s*down_revision\s*(?::[^=]+)?=\s*[\"']([^\"']+)[\"']",
    migration_text,
    re.MULTILINE,
)
create_index_matches = re.findall(
    r"op\.create_index\((.*?)\)",
    migration_text,
    re.DOTALL,
)
drop_index_matches = re.findall(
    r"op\.drop_index\((.*?)\)",
    migration_text,
    re.DOTALL,
)

migration_plan = {
    "schema_version": "1.0",
    "status": "PLAN_ONLY_NOT_EXECUTED",
    "migration": {
        "path": str(workflow_migration_path.relative_to(repo)),
        "sha256": sha(workflow_migration_path),
        "revision": revision_match.group(1) if revision_match else None,
        "down_revision": (
            down_revision_match.group(1) if down_revision_match else None
        ),
        "create_index_call_count": len(create_index_matches),
        "drop_index_call_count": len(drop_index_matches),
        "source_contains_partial_unique_index_terms": all(
            token in migration_text
            for token in ("unique=True", "wordpress_post_id")
        ),
    },
    "preflight_checks": [
        "Confirm an independently restorable production DB backup and record its SHA-256.",
        "Confirm no duplicate non-NULL wordpress_post_id values exist.",
        "Run SQLite integrity_check and foreign_key_check in an explicitly approved read-only preflight window.",
        "Confirm the current Alembic revision exactly matches the migration down_revision.",
        "Confirm no unreviewed migration lies between current revision and the target revision.",
        "Confirm the production application and worker are stopped before any approved migration.",
    ],
    "planned_read_only_queries": [
        (
            "SELECT wordpress_post_id, COUNT(*) "
            "FROM ebook_items "
            "WHERE wordpress_post_id IS NOT NULL "
            "GROUP BY wordpress_post_id "
            "HAVING COUNT(*) > 1;"
        ),
        "PRAGMA integrity_check;",
        "PRAGMA foreign_key_check;",
        (
            "SELECT name, sql FROM sqlite_master "
            "WHERE type = 'index' AND tbl_name = 'ebook_items';"
        ),
    ],
    "application_plan": [
        "Acquire separate explicit production DB access and migration approval.",
        "Stop all application and worker writers.",
        "Verify production DB SHA and backup SHA immediately before migration.",
        "Apply only the reviewed Alembic revision.",
        "Run post-migration integrity, foreign-key, index, and application smoke checks.",
        "Do not start Slack Worker until an independent start approval is issued.",
    ],
    "rollback_plan": [
        "Stop all writers.",
        "Attempt the reviewed Alembic downgrade only when its safety is separately approved.",
        "If downgrade is unsafe or fails, restore the verified pre-migration DB backup atomically.",
        "Restore the pre-change production manifest bytes and verify the original SHA.",
        "Keep Slack Worker stopped and revoke release approval.",
    ],
    "production_database_opened": False,
    "sql_executed": False,
    "migration_applied": False,
    "application_allowed": False,
}
write_json(packet_root / "workflow-migration-preflight-plan.json", migration_plan)

db_preflight_plan = {
    "schema_version": "1.0",
    "status": "PLAN_ONLY_NO_DATABASE_CONNECTION",
    "production_database": {
        "path": "data/database/ebook_affiliate.db",
        "preflight_sha256": (
            "1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
        ),
    },
    "required_access_mode": "EXPLICITLY_APPROVED_READ_ONLY_PREFLIGHT",
    "required_controls": [
        "Copy the production DB to a unique read-only inspection file only after approval.",
        "Never run test code against the production DB path.",
        "Do not enable WAL or create sidecar files during read-only inspection.",
        "Record the DB SHA before and after inspection and require equality.",
        "Record SQLite version, schema version, Alembic version, table list, and index list.",
        "Reject the release on integrity, foreign-key, duplicate post-ID, or revision mismatch.",
    ],
    "inspection_outputs_required": [
        "database-sha-before.txt",
        "database-sha-after.txt",
        "sqlite-integrity-check.txt",
        "sqlite-foreign-key-check.txt",
        "alembic-current-revision.txt",
        "ebook-items-wordpress-post-id-duplicate-check.txt",
        "ebook-items-index-inventory.txt",
        "readonly-preflight-result.json",
    ],
    "production_database_opened": False,
    "production_database_sql_connection_used": False,
    "sql_executed": False,
    "inspection_performed": False,
}
write_json(packet_root / "production-db-readonly-preflight-plan.json", db_preflight_plan)

deployment_plan = {
    "schema_version": "1.0",
    "status": "PLAN_ONLY_NOT_DEPLOYED",
    "ordered_gates": [
        {
            "order": 1,
            "gate": "PRODUCTION_MANIFEST_REBIND_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
        {
            "order": 2,
            "gate": "PRODUCTION_DB_READONLY_PREFLIGHT_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
        {
            "order": 3,
            "gate": "PRODUCTION_MIGRATION_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
        {
            "order": 4,
            "gate": "DEPLOYMENT_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
        {
            "order": 5,
            "gate": "SLACK_WORKER_START_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
        {
            "order": 6,
            "gate": "EXTERNAL_NETWORK_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
        {
            "order": 7,
            "gate": "PRODUCTION_RELEASE_APPROVAL",
            "required": True,
            "currently_approved": False,
        },
    ],
    "deployment_sequence": [
        "Freeze writers and record process/service state.",
        "Verify source, candidate, manifest, DB, migration, and approval evidence SHAs.",
        "Apply only separately approved manifest update.",
        "Perform separately approved read-only DB preflight.",
        "Create and verify production DB backup.",
        "Apply only separately approved migration.",
        "Run offline/import/config smoke checks without external communication.",
        "Keep Slack Worker stopped until separate start and network approvals.",
        "Issue production release approval only after all gate evidence passes.",
    ],
    "rollback_sequence": [
        "Stop all writers and Slack Worker.",
        "Revoke production release approval.",
        "Restore prior production manifest bytes.",
        "Restore or downgrade the DB using the separately approved rollback method.",
        "Verify source, manifest, and DB SHAs.",
        "Run offline validation only.",
        "Return release status to HOLD and preserve all evidence.",
    ],
    "deployment_performed": False,
    "rollback_performed": False,
}
write_json(packet_root / "deployment-and-rollback-plan.json", deployment_plan)

slack_worker_plan = {
    "schema_version": "1.0",
    "status": "PLAN_ONLY_WORKER_NOT_STARTED",
    "pre_start_requirements": [
        "Production manifest update approval completed.",
        "Production DB preflight and migration evidence completed.",
        "Deployment approval completed.",
        "Slack Worker start approval completed.",
        "External network approval completed.",
        "Credential presence validated without printing token contents.",
        "Offline ImportError, default factory, lifecycle, and related tests remain PASS.",
    ],
    "planned_check_config_command": (
        "python3 scripts/run_slack_approval_socket.py --check-config"
    ),
    "planned_start_command": (
        "python3 scripts/run_slack_approval_socket.py --start"
    ),
    "planned_stop_behavior": [
        "SIGTERM enters the common controlled shutdown path.",
        "WorkerStopController.close_once prevents duplicate close calls.",
        "KeyboardInterrupt is treated as controlled shutdown.",
        "On any startup or runtime error, stop and retain evidence; do not auto-restart.",
    ],
    "observability_requirements": [
        "Log configuration presence only; never token values.",
        "Record process PID, source SHA, manifest SHA, DB SHA, and approval ID.",
        "Record start, readiness, stop request, handler close, and final exit code.",
        "Alert on unexpected network, DB, or approval-state boundary violation.",
    ],
    "worker_started": False,
    "external_network_used": False,
    "runtime_execution_allowed": False,
}
write_json(packet_root / "slack-worker-operation-plan.json", slack_worker_plan)

shadow_test_text = slack_test_snapshot_path.read_text(encoding="utf-8")
shadow_test_tree = ast.parse(shadow_test_text)
shadow_test_names = [
    node.name
    for node in shadow_test_tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name.startswith("test_")
]

promotion_assessment = {
    "schema_version": "1.0",
    "status": "ASSESSMENT_ONLY_NOT_PROMOTED",
    "source_shadow_test": {
        "path": str(slack_test_snapshot_path.relative_to(repo)),
        "sha256": sha(slack_test_snapshot_path),
        "test_count": len(shadow_test_names),
        "test_names": shadow_test_names,
    },
    "proposed_repository_target": (
        "tests/test_slack_approval_socket_hold_remediation_offline.py"
    ),
    "recommendation": "PROMOTE_IN_SEPARATE_TEST_ONLY_CHANGE_AFTER_EXPLICIT_APPROVAL",
    "rationale": [
        "The tests close the exact human-review HOLD conditions.",
        "Keeping them only in evidence does not protect future source changes.",
        "The proposed promotion changes tests only and does not alter runtime code.",
        "Promotion must preserve offline fake-factory and no-production-DB boundaries.",
    ],
    "minimal_diff": {
        "operation": "ADD_FILE_ONLY",
        "source_sha256": sha(slack_test_snapshot_path),
        "target_path": (
            "tests/test_slack_approval_socket_hold_remediation_offline.py"
        ),
        "runtime_source_change_required": False,
        "production_manifest_change_required_for_test_only_promotion": False,
    },
    "promotion_performed": False,
    "repository_test_created": False,
    "source_modified": False,
}
write_json(
    packet_root / "shadow-test-promotion-assessment.json",
    promotion_assessment,
)

approval_gate_checklist = {
    "schema_version": "1.0",
    "status": "PREPARATION_PACKET_READY_RELEASE_NOT_APPROVED",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "review_units": {
        "UNIT_DB_SAFETY": "APPROVE",
        "UNIT_WORKFLOW_STATE": "APPROVE_WITH_CONDITIONS",
        "UNIT_SLACK_RUNTIME": "APPROVE",
    },
    "production_release_gates": [
        {
            "gate": "PRODUCTION_MANIFEST_REBIND",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
        },
        {
            "gate": "PRODUCTION_DB_READONLY_PREFLIGHT",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
        },
        {
            "gate": "PRODUCTION_MIGRATION",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
        },
        {
            "gate": "TEST_PROMOTION",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
            "required_before_release": False,
        },
        {
            "gate": "DEPLOYMENT",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
        },
        {
            "gate": "SLACK_WORKER_START",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
        },
        {
            "gate": "EXTERNAL_NETWORK",
            "status": "NOT_APPROVED",
            "preparation_material_ready": True,
        },
        {
            "gate": "PRODUCTION_APPROVAL",
            "status": "NOT_CREATED",
            "preparation_material_ready": True,
        },
    ],
    "production_release_ready": False,
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_PACKET",
}
write_json(
    packet_root / "production-approval-gate-checklist.json",
    approval_gate_checklist,
)

readme = """# Production Release Preparation Packet

Status: PREPARATION ONLY / NOT APPROVED FOR APPLICATION

This packet contains non-executable review material for:
- production manifest rebinding
- production DB read-only preflight
- Workflow migration and rollback
- deployment and rollback sequencing
- Slack Worker start/stop controls
- shadow test promotion assessment
- production approval gates

Prohibited by the governing approval:
- production manifest modification
- production DB connection or SQL execution
- production migration
- source or test modification
- deployment
- Slack Worker start
- external network access
- production approval creation
- production release approval
"""
(packet_root / "README.md").write_text(readme, encoding="utf-8")

packet_files = sorted(
    path
    for path in packet_root.iterdir()
    if path.is_file() and path.name != "preparation-packet-manifest.json"
)

packet_manifest = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-B",
    "result": "PASS_PRODUCTION_RELEASE_PREPARATION_PACKET_READY",
    "status": "PREPARATION_ONLY_NOT_APPROVED_FOR_APPLICATION",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "inputs": {
        "preflight_result_sha256": sha(preflight_result_path),
        "preflight_inventory_sha256": sha(preflight_inventory_path),
        "manifest_binding_analysis_sha256": sha(manifest_analysis_path),
        "release_gate_matrix_sha256": sha(release_gate_matrix_path),
        "final_decision_set_sha256": sha(final_decision_set_path),
        "candidate_manifest_sha256": sha(candidate_manifest_path),
        "dependency_closure_sha256": sha(dependency_closure_path),
        "downstream_plan_sha256": sha(downstream_plan_path),
        "production_manifest_sha256": sha(production_manifest_path),
        "workflow_migration_sha256": sha(workflow_migration_path),
        "slack_shadow_test_sha256": sha(slack_test_snapshot_path),
    },
    "packet_files": [
        {
            "name": path.name,
            "sha256": sha(path),
            "size_bytes": path.stat().st_size,
        }
        for path in packet_files
    ],
    "packet_file_count": len(packet_files),
    "execution": {
        "production_manifest_modified": False,
        "production_database_opened": False,
        "production_database_sql_connection_used": False,
        "sql_executed": False,
        "production_migration_applied": False,
        "source_modified": False,
        "test_modified": False,
        "repository_test_promoted": False,
        "pytest_executed": False,
        "deployment_performed": False,
        "slack_worker_started": False,
        "external_network_used": False,
        "production_approval_created": False,
        "production_release_approved": False,
    },
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_PACKET",
}
write_json(packet_root / "preparation-packet-manifest.json", packet_manifest)
PY

python3 -m json.tool \
    "$SHADOW_ROOT/packet/production-manifest-rebind-proposal.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/workflow-migration-preflight-plan.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/production-db-readonly-preflight-plan.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/deployment-and-rollback-plan.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/slack-worker-operation-plan.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/shadow-test-promotion-assessment.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/production-approval-gate-checklist.json" \
    >/dev/null
python3 -m json.tool \
    "$SHADOW_ROOT/packet/preparation-packet-manifest.json" \
    >/dev/null

cp -a "$SHADOW_ROOT/packet/." "$EVIDENCE_ROOT/packet-snapshot/"

find "$SHADOW_ROOT/packet" -type f -exec chmod 0444 {} +
find "$EVIDENCE_ROOT/packet-snapshot" -type f -exec chmod 0444 {} +

SHADOW_PACKET_MANIFEST="${SHADOW_ROOT}/packet/preparation-packet-manifest.json"
EVIDENCE_PACKET_MANIFEST="${EVIDENCE_ROOT}/packet-snapshot/preparation-packet-manifest.json"

SHADOW_PACKET_MANIFEST_SHA="$(sha256_file "$SHADOW_PACKET_MANIFEST")"
EVIDENCE_PACKET_MANIFEST_SHA="$(sha256_file "$EVIDENCE_PACKET_MANIFEST")"

if [[ "$SHADOW_PACKET_MANIFEST_SHA" != "$EVIDENCE_PACKET_MANIFEST_SHA" ]]; then
    printf 'ERROR=PACKET_SNAPSHOT_MANIFEST_SHA_MISMATCH\n' >&2
    exit 1
fi

PACKET_FILE_COUNT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["packet_file_count"])' \
        "$SHADOW_PACKET_MANIFEST"
)"

SNAPSHOT_MANIFEST="${EVIDENCE_ROOT}/preparation-packet-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'preparation-packet-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$SNAPSHOT_MANIFEST"
chmod 0444 "$SNAPSHOT_MANIFEST"

SNAPSHOT_MANIFEST_SHA="$(sha256_file "$SNAPSHOT_MANIFEST")"

PREFLIGHT_RESULT_AFTER="$(sha256_file "$PREFLIGHT_RESULT")"
FINAL_DECISION_SET_AFTER="$(sha256_file "$FINAL_DECISION_SET")"
CANDIDATE_MANIFEST_AFTER="$(sha256_file "$CANDIDATE_MANIFEST")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"
WORKFLOW_MIGRATION_AFTER="$(sha256_file "$WORKFLOW_MIGRATION")"

ACCESS_GUARD_AFTER="$(sha256_file "$ACCESS_GUARD_SOURCE")"
DB_CONFIG_AFTER="$(sha256_file "$DB_CONFIG_SOURCE")"
WORKFLOW_SOURCE_AFTER="$(sha256_file "$WORKFLOW_SOURCE")"
DB_SESSION_AFTER="$(sha256_file "$DB_SESSION_SOURCE")"
SLACK_SOURCE_AFTER="$(sha256_file "$SLACK_SOURCE")"
SLACK_TEST_SNAPSHOT_AFTER="$(sha256_file "$SLACK_TEST_SNAPSHOT")"

[[ "$PREFLIGHT_RESULT_AFTER" == "$EXPECTED_PREFLIGHT_RESULT_SHA" ]] || {
    printf 'ERROR=PREFLIGHT_RESULT_CHANGED\n' >&2
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
[[ "$WORKFLOW_MIGRATION_AFTER" == "$EXPECTED_WORKFLOW_MIGRATION_SHA" ]] || {
    printf 'ERROR=WORKFLOW_MIGRATION_CHANGED\n' >&2
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
[[ "$SLACK_TEST_SNAPSHOT_AFTER" == "$EXPECTED_SLACK_TEST_SNAPSHOT_SHA" ]] || {
    printf 'ERROR=SLACK_TEST_SNAPSHOT_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3E-B",
  "result": "PASS_W2B_I2F3E_B_PRODUCTION_RELEASE_PREPARATION_PACKET_READY",
  "candidate_id": "${EXPECTED_CANDIDATE_ID}",
  "review_bundle_id": "${EXPECTED_REVIEW_BUNDLE_ID}",
  "shadow_root": "${SHADOW_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "packet": {
    "status": "PREPARATION_ONLY_NOT_APPROVED_FOR_APPLICATION",
    "packet_file_count": ${PACKET_FILE_COUNT},
    "shadow_packet_manifest_sha256": "${SHADOW_PACKET_MANIFEST_SHA}",
    "evidence_packet_manifest_sha256": "${EVIDENCE_PACKET_MANIFEST_SHA}",
    "evidence_manifest_sha256": "${SNAPSHOT_MANIFEST_SHA}"
  },
  "materials": {
    "production_manifest_rebind_proposal": true,
    "production_manifest_proposed_diff": true,
    "workflow_migration_preflight_plan": true,
    "production_db_readonly_preflight_plan": true,
    "deployment_and_rollback_plan": true,
    "slack_worker_operation_plan": true,
    "shadow_test_promotion_assessment": true,
    "production_approval_gate_checklist": true
  },
  "execution": {
    "production_manifest_modified": false,
    "production_database_opened": false,
    "production_database_sql_connection_used": false,
    "sql_executed": false,
    "production_migration_applied": false,
    "source_modified": false,
    "test_modified": false,
    "repository_test_promoted": false,
    "pytest_executed": false,
    "deployment_performed": false,
    "slack_worker_started": false,
    "external_network_used": false,
    "production_approval_created": false,
    "production_release_approved": false
  },
  "safety": {
    "preflight_result_changed": false,
    "final_decision_set_changed": false,
    "candidate_manifest_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "workflow_migration_changed": false,
    "access_guard_source_changed": false,
    "db_config_source_changed": false,
    "workflow_source_changed": false,
    "db_session_source_changed": false,
    "slack_source_changed": false,
    "slack_test_snapshot_changed": false
  },
  "production_release_decision": "HOLD",
  "release_status": "CANDIDATE_NOT_APPROVED",
  "next_gate": "HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_PACKET",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3E_B_PRODUCTION_RELEASE_PREPARATION_PACKET_READY\n'
printf 'CANDIDATE_ID=%s\n' "$EXPECTED_CANDIDATE_ID"
printf 'REVIEW_BUNDLE_ID=%s\n' "$EXPECTED_REVIEW_BUNDLE_ID"
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'PACKET_FILE_COUNT=%s\n' "$PACKET_FILE_COUNT"
printf 'PACKET_STATUS=PREPARATION_ONLY_NOT_APPROVED_FOR_APPLICATION\n'
printf 'SHADOW_PACKET_MANIFEST_SHA=%s\n' "$SHADOW_PACKET_MANIFEST_SHA"
printf 'EVIDENCE_PACKET_MANIFEST_SHA=%s\n' "$EVIDENCE_PACKET_MANIFEST_SHA"
printf 'PREPARATION_PACKET_EVIDENCE_MANIFEST_SHA=%s\n' "$SNAPSHOT_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'PRODUCTION_MANIFEST_REBIND_PROPOSAL_CREATED=true\n'
printf 'MIGRATION_PREFLIGHT_PLAN_CREATED=true\n'
printf 'PRODUCTION_DB_READONLY_PREFLIGHT_PLAN_CREATED=true\n'
printf 'DEPLOYMENT_ROLLBACK_PLAN_CREATED=true\n'
printf 'SLACK_WORKER_OPERATION_PLAN_CREATED=true\n'
printf 'SHADOW_TEST_PROMOTION_ASSESSMENT_CREATED=true\n'
printf 'PRODUCTION_APPROVAL_GATE_CHECKLIST_CREATED=true\n'
printf 'PRODUCTION_MANIFEST_MODIFIED=false\n'
printf 'PRODUCTION_DB_OPENED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'SQL_EXECUTED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'SOURCE_MODIFIED=false\n'
printf 'TEST_MODIFIED=false\n'
printf 'REPOSITORY_TEST_PROMOTED=false\n'
printf 'PYTEST_EXECUTED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'SLACK_WORKER_STARTED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'PRODUCTION_RELEASE_APPROVED=false\n'
printf 'PREFLIGHT_RESULT_CHANGED=false\n'
printf 'FINAL_DECISION_SET_CHANGED=false\n'
printf 'CANDIDATE_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'WORKFLOW_MIGRATION_CHANGED=false\n'
printf 'ACCESS_GUARD_SOURCE_CHANGED=false\n'
printf 'DB_CONFIG_SOURCE_CHANGED=false\n'
printf 'WORKFLOW_SOURCE_CHANGED=false\n'
printf 'DB_SESSION_SOURCE_CHANGED=false\n'
printf 'SLACK_SOURCE_CHANGED=false\n'
printf 'SLACK_TEST_SNAPSHOT_CHANGED=false\n'
printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'NEXT_GATE=HUMAN_REVIEW_PRODUCTION_RELEASE_PREPARATION_PACKET\n'
printf 'SCRIPT_EXIT_CODE=0\n'
