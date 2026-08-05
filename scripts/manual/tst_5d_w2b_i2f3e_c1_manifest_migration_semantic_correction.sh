#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
C1_SOURCE_ROOT_REL="${I2E_ROOT_REL}/i2f3e-c-corrective-preparation-packet-20260725T174644-500176"
C1_SOURCE_PACKET_REL="${C1_SOURCE_ROOT_REL}/packet-snapshot"
C1_SOURCE_CANDIDATE_REL="${C1_SOURCE_ROOT_REL}/candidate-input-snapshot"

SOURCE_RESULT="${REPO_ROOT}/${C1_SOURCE_ROOT_REL}/result.json"
SOURCE_PACKET_MANIFEST="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/corrective-preparation-packet-manifest.json"
SOURCE_REBIND_SPEC="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/production-manifest-corrective-rebind-spec.json"
SOURCE_SHADOW_DRAFT="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/shadow-production-manifest-draft.json"
SOURCE_MANIFEST_VALIDATION="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/shadow-production-manifest-semantic-validation.json"
SOURCE_MIGRATION_SEMANTICS="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/migration-static-semantic-validation.json"
SOURCE_SAFE_ORDER="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/corrected-production-release-order.json"
SOURCE_BACKUP_PLAN="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/sqlite-backup-and-restore-rehearsal-plan.json"
SOURCE_TEST_ASSESSMENT="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/corrected-shadow-test-promotion-assessment.json"
SOURCE_TEST_CANDIDATE="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/test_slack_approval_socket_hold_remediation_offline.candidate.py"
SOURCE_TEST_DIFF="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/shadow-test-promotion-minimal.diff"
SOURCE_GATE_CHECKLIST="${REPO_ROOT}/${C1_SOURCE_PACKET_REL}/corrected-production-approval-gate-checklist.json"
SOURCE_EVIDENCE_MANIFEST="${REPO_ROOT}/${C1_SOURCE_ROOT_REL}/corrective-preparation-evidence-manifest.txt"

SOURCE_CANDIDATE_MANIFEST="${REPO_ROOT}/${C1_SOURCE_CANDIDATE_REL}/candidate-manifest.json"
SOURCE_DEPENDENCY_CLOSURE="${REPO_ROOT}/${C1_SOURCE_CANDIDATE_REL}/dependency-closure.json"
SOURCE_DOWNSTREAM_PLAN="${REPO_ROOT}/${C1_SOURCE_CANDIDATE_REL}/downstream-rebinding-plan.json"

EXPECTED_SOURCE_RESULT_SHA="6dee985fcb83cae31cb5affb2792e6b7f3ddb07672bb054cda5e20573cba6bd9"
EXPECTED_SOURCE_PACKET_MANIFEST_SHA="513788d96693576f1bd431e5a6bcf550604dab80ff061388728542375df0ed1c"
EXPECTED_SOURCE_REBIND_SPEC_SHA="8069c1dfc7bc21fe1105e632cd62a375b1c9444ad4a01844ea8db1ee76119443"
EXPECTED_SOURCE_SHADOW_DRAFT_SHA="c06208ac411afc35e054bf061c8a2729d6f3ae8b447f69fb678d67ec774771f7"
EXPECTED_SOURCE_MANIFEST_VALIDATION_SHA="66ad6479f8f96286f60bc60b8e8ca7f178db4323ca1d810718e520b8c2733b05"
EXPECTED_SOURCE_MIGRATION_SEMANTICS_SHA="42161c7a9dc60314d6815f8c0f0a971e24b2739180b2f5f3099c21cb7472eecf"
EXPECTED_SOURCE_SAFE_ORDER_SHA="d54825668f46095049dbd7b21b3ce67253e7b618e6bfe1f8582ef142897cb73e"
EXPECTED_SOURCE_BACKUP_PLAN_SHA="20cf568f765d5a465737aacb0825e116774cfe1b66e728e23e355d56fcbcfe9e"
EXPECTED_SOURCE_TEST_ASSESSMENT_SHA="94d3c8ba56fc49e1a7b2d8683d86bc58617232bd740d99716033843563ad5eac"
EXPECTED_SOURCE_TEST_CANDIDATE_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"
EXPECTED_SOURCE_TEST_DIFF_SHA="b5730bc406ef041e58a208cb7052034002e787f99fdc0ff3c5dc33c67ab688a4"
EXPECTED_SOURCE_GATE_CHECKLIST_SHA="0721efd119e1a34f4b156eb916e10c33c09533ce2784065057c41351712dbf5b"
EXPECTED_SOURCE_EVIDENCE_MANIFEST_SHA="03cfe12818108bfd42c7e6cab8285f9ad5670991e81b2286e09319f146aad97c"

EXPECTED_CANDIDATE_MANIFEST_SHA="c882f2cb1afbfbe5215db61667a6c72feccc71bc84a558cdda792806d440f843"
EXPECTED_DEPENDENCY_CLOSURE_SHA="9eb8854b7b877cc927ca0350281f84d8dc3a8160f564982825f9f87f36ec79e9"
EXPECTED_DOWNSTREAM_PLAN_SHA="5fa8255966773bda7d35ba0d89b1f40c0f8b9a7df89b33578e3997f6cc22bed8"

PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
PRODUCTION_DB="${REPO_ROOT}/data/database/ebook_affiliate.db"
WORKFLOW_MIGRATION="${REPO_ROOT}/migrations/versions/00241611109d_add_unique_wordpress_post_id.py"
ACCESS_GUARD_SOURCE="${REPO_ROOT}/app/db/access_guard.py"
DB_CONFIG_SOURCE="${REPO_ROOT}/app/db/config.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
DB_SESSION_SOURCE="${REPO_ROOT}/app/db/session.py"
SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"

EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_PRODUCTION_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
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

require_file_sha "$SOURCE_RESULT" "$EXPECTED_SOURCE_RESULT_SHA"
require_file_sha "$SOURCE_PACKET_MANIFEST" "$EXPECTED_SOURCE_PACKET_MANIFEST_SHA"
require_file_sha "$SOURCE_REBIND_SPEC" "$EXPECTED_SOURCE_REBIND_SPEC_SHA"
require_file_sha "$SOURCE_SHADOW_DRAFT" "$EXPECTED_SOURCE_SHADOW_DRAFT_SHA"
require_file_sha "$SOURCE_MANIFEST_VALIDATION" "$EXPECTED_SOURCE_MANIFEST_VALIDATION_SHA"
require_file_sha "$SOURCE_MIGRATION_SEMANTICS" "$EXPECTED_SOURCE_MIGRATION_SEMANTICS_SHA"
require_file_sha "$SOURCE_SAFE_ORDER" "$EXPECTED_SOURCE_SAFE_ORDER_SHA"
require_file_sha "$SOURCE_BACKUP_PLAN" "$EXPECTED_SOURCE_BACKUP_PLAN_SHA"
require_file_sha "$SOURCE_TEST_ASSESSMENT" "$EXPECTED_SOURCE_TEST_ASSESSMENT_SHA"
require_file_sha "$SOURCE_TEST_CANDIDATE" "$EXPECTED_SOURCE_TEST_CANDIDATE_SHA"
require_file_sha "$SOURCE_TEST_DIFF" "$EXPECTED_SOURCE_TEST_DIFF_SHA"
require_file_sha "$SOURCE_GATE_CHECKLIST" "$EXPECTED_SOURCE_GATE_CHECKLIST_SHA"
require_file_sha "$SOURCE_EVIDENCE_MANIFEST" "$EXPECTED_SOURCE_EVIDENCE_MANIFEST_SHA"

require_file_sha "$SOURCE_CANDIDATE_MANIFEST" "$EXPECTED_CANDIDATE_MANIFEST_SHA"
require_file_sha "$SOURCE_DEPENDENCY_CLOSURE" "$EXPECTED_DEPENDENCY_CLOSURE_SHA"
require_file_sha "$SOURCE_DOWNSTREAM_PLAN" "$EXPECTED_DOWNSTREAM_PLAN_SHA"

require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$PRODUCTION_DB" "$EXPECTED_PRODUCTION_DB_SHA"
require_file_sha "$WORKFLOW_MIGRATION" "$EXPECTED_WORKFLOW_MIGRATION_SHA"
require_file_sha "$ACCESS_GUARD_SOURCE" "$EXPECTED_ACCESS_GUARD_SHA"
require_file_sha "$DB_CONFIG_SOURCE" "$EXPECTED_DB_CONFIG_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$DB_SESSION_SOURCE" "$EXPECTED_DB_SESSION_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3e-c1-semantic-correction-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3e-c1-manifest-migration-semantic-correction-${RUN_ID}"
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
    "$SHADOW_ROOT/selftest" \
    "$SHADOW_ROOT/pycache" \
    "$EVIDENCE_ROOT/candidate-input-snapshot" \
    "$EVIDENCE_ROOT/packet-snapshot"

CANDIDATE_SNAPSHOT="${EVIDENCE_ROOT}/candidate-input-snapshot/candidate-manifest.json"
CLOSURE_SNAPSHOT="${EVIDENCE_ROOT}/candidate-input-snapshot/dependency-closure.json"
DOWNSTREAM_SNAPSHOT="${EVIDENCE_ROOT}/candidate-input-snapshot/downstream-rebinding-plan.json"

cp --preserve=mode,timestamps "$SOURCE_CANDIDATE_MANIFEST" "$CANDIDATE_SNAPSHOT"
cp --preserve=mode,timestamps "$SOURCE_DEPENDENCY_CLOSURE" "$CLOSURE_SNAPSHOT"
cp --preserve=mode,timestamps "$SOURCE_DOWNSTREAM_PLAN" "$DOWNSTREAM_SNAPSHOT"
chmod 0444 "$CANDIDATE_SNAPSHOT" "$CLOSURE_SNAPSHOT" "$DOWNSTREAM_SNAPSHOT"

require_file_sha "$CANDIDATE_SNAPSHOT" "$EXPECTED_CANDIDATE_MANIFEST_SHA"
require_file_sha "$CLOSURE_SNAPSHOT" "$EXPECTED_DEPENDENCY_CLOSURE_SHA"
require_file_sha "$DOWNSTREAM_SNAPSHOT" "$EXPECTED_DOWNSTREAM_PLAN_SHA"

cp --preserve=mode,timestamps "$SOURCE_SAFE_ORDER" \
    "$SHADOW_ROOT/packet/corrected-production-release-order.json"
cp --preserve=mode,timestamps "$SOURCE_BACKUP_PLAN" \
    "$SHADOW_ROOT/packet/sqlite-backup-and-restore-rehearsal-plan.json"
cp --preserve=mode,timestamps "$SOURCE_TEST_ASSESSMENT" \
    "$SHADOW_ROOT/packet/corrected-shadow-test-promotion-assessment.json"
cp --preserve=mode,timestamps "$SOURCE_TEST_CANDIDATE" \
    "$SHADOW_ROOT/packet/test_slack_approval_socket_hold_remediation_offline.candidate.py"
cp --preserve=mode,timestamps "$SOURCE_TEST_DIFF" \
    "$SHADOW_ROOT/packet/shadow-test-promotion-minimal.diff"
cp --preserve=mode,timestamps "$SOURCE_GATE_CHECKLIST" \
    "$SHADOW_ROOT/packet/corrected-production-approval-gate-checklist.json"

cat > "$SHADOW_ROOT/packet/human-approval-verbatim.txt" <<'TXT'
承認：
PACKET_REVIEW=HOLD_FOR_CORRECTION
APPROVE_3E_C1_MANIFEST_AND_MIGRATION_SEMANTIC_CORRECTION_SHADOW_ONLY

修正条件：
1. shadow production manifestのsource_file_countを17へ更新し、
   source_file_count == len(source_files)をvalidatorで必須検証する。
2. source path重複、SHA形式、size、mode、変更対象外entry、
   無関係なmanifest metadataの不変性をsemantic検証する。
3. migration内のmodule-level INDEX_NAME定数を安全に解決し、
   実際のindex名をupgrade・downgrade双方で検証する。
4. 実index名、table、column、unique、sqlite_where、
   upgrade create数、downgrade drop数を実値で固定する。
5. ADD_SOURCE_BINDINGには
   rollback_action=REMOVE_ADDED_SOURCE_BINDINGを明記する。
6. REBIND_EXISTING_SOURCEには
   rollback_action=RESTORE_PRIOR_SHAを明記する。
7. 既存3E-C証跡を変更せず、新しい一意なshadow／evidence領域へ
   修正版Packetを生成する。

禁止事項：
production manifest変更、production DB接続、SQL実行、
production migration適用、source/test変更、test昇格、deployment、
production approval作成、外部通信、Slack Worker起動、
production release承認は引き続き禁止する。
TXT

cat > "$SHADOW_ROOT/packet/validate_shadow_production_manifest_v2.py" <<'PYVALIDATOR'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MODE_RE = re.compile(r"^0[0-7]{3}$")
HASH_KEYS = ("sha256", "source_sha256", "current_sha256", "file_sha256")
MUTABLE_TOP_LEVEL_KEYS = {"source_file_count", "source_files"}


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entry_path(entry: dict[str, Any]) -> str:
    value = entry.get("path")
    if not isinstance(value, str) or not value:
        raise ValidationError("SOURCE_PATH_EMPTY_OR_INVALID")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValidationError(f"SOURCE_PATH_NOT_REPOSITORY_RELATIVE:{value}")
    return value


def entry_sha(entry: dict[str, Any], source_path: str) -> str:
    present = [key for key in HASH_KEYS if key in entry]
    if not present:
        raise ValidationError(f"SOURCE_SHA_FIELD_MISSING:{source_path}")
    values = {entry[key] for key in present}
    if len(values) != 1:
        raise ValidationError(f"SOURCE_SHA_FIELDS_CONFLICT:{source_path}")
    value = next(iter(values))
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValidationError(f"SOURCE_SHA_INVALID:{source_path}")
    return value


def entry_mode(entry: dict[str, Any], source_path: str) -> str:
    value = entry.get("mode")
    if not isinstance(value, str) or not MODE_RE.fullmatch(value):
        raise ValidationError(f"SOURCE_MODE_INVALID:{source_path}:{value!r}")
    return value


def entry_size(entry: dict[str, Any], source_path: str) -> int:
    value = entry.get("size")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"SOURCE_SIZE_INVALID:{source_path}:{value!r}")
    return value


def source_map(
    entries: list[Any],
    label: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    result: dict[str, dict[str, Any]] = {}
    ordered: list[str] = []
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            raise ValidationError(f"SOURCE_ENTRY_NOT_OBJECT:{label}:{index}")
        source_path = entry_path(raw_entry)
        if source_path in result:
            raise ValidationError(f"SOURCE_PATH_DUPLICATE:{label}:{source_path}")
        entry_sha(raw_entry, source_path)
        entry_size(raw_entry, source_path)
        entry_mode(raw_entry, source_path)
        result[source_path] = raw_entry
        ordered.append(source_path)
    return result, ordered


def check_actual_file(
    repo: Path,
    source_path: str,
    entry: dict[str, Any],
) -> None:
    actual_path = (repo / source_path).resolve()
    try:
        actual_path.relative_to(repo)
    except ValueError as exc:
        raise ValidationError(
            f"SOURCE_PATH_ESCAPES_REPOSITORY:{source_path}"
        ) from exc
    if not actual_path.is_file():
        raise ValidationError(f"SOURCE_FILE_MISSING:{source_path}")

    actual_sha = sha(actual_path)
    expected_sha = entry_sha(entry, source_path)
    if actual_sha != expected_sha:
        raise ValidationError(
            f"SOURCE_REPOSITORY_SHA_MISMATCH:{source_path}"
        )

    actual_size = actual_path.stat().st_size
    if entry_size(entry, source_path) != actual_size:
        raise ValidationError(
            f"SOURCE_SIZE_MISMATCH:{source_path}:"
            f"manifest={entry.get('size')}:actual={actual_size}"
        )

    actual_mode = f"0{stat.S_IMODE(actual_path.stat().st_mode):03o}"
    if entry_mode(entry, source_path) != actual_mode:
        raise ValidationError(
            f"SOURCE_MODE_MISMATCH:{source_path}:"
            f"manifest={entry.get('mode')}:actual={actual_mode}"
        )


def validate(args: argparse.Namespace) -> dict[str, Any]:
    production_path = Path(args.production).resolve()
    draft_path = Path(args.draft).resolve()
    spec_path = Path(args.spec).resolve()
    candidate_path = Path(args.candidate).resolve()
    repo = Path(args.repo).resolve()

    production = load_json(production_path)
    draft = load_json(draft_path)
    spec = load_json(spec_path)
    candidate = load_json(candidate_path)

    if set(production) != set(draft):
        raise ValidationError("TOP_LEVEL_SCHEMA_CHANGED")

    for key in sorted(set(production) - MUTABLE_TOP_LEVEL_KEYS):
        if production[key] != draft[key]:
            raise ValidationError(f"UNRELATED_TOP_LEVEL_METADATA_CHANGED:{key}")

    production_entries = production.get("source_files")
    draft_entries = draft.get("source_files")
    candidate_entries = candidate.get("source_files")
    if not isinstance(production_entries, list):
        raise ValidationError("PRODUCTION_SOURCE_FILES_NOT_LIST")
    if not isinstance(draft_entries, list):
        raise ValidationError("DRAFT_SOURCE_FILES_NOT_LIST")
    if not isinstance(candidate_entries, list):
        raise ValidationError("CANDIDATE_SOURCE_FILES_NOT_LIST")

    production_count = production.get("source_file_count")
    draft_count = draft.get("source_file_count")
    if isinstance(production_count, bool) or not isinstance(production_count, int):
        raise ValidationError("PRODUCTION_SOURCE_FILE_COUNT_INVALID")
    if isinstance(draft_count, bool) or not isinstance(draft_count, int):
        raise ValidationError("DRAFT_SOURCE_FILE_COUNT_INVALID")
    if production_count != len(production_entries):
        raise ValidationError(
            "PRODUCTION_SOURCE_FILE_COUNT_MISMATCH:"
            f"{production_count}!={len(production_entries)}"
        )
    if draft_count != len(draft_entries):
        raise ValidationError(
            "DRAFT_SOURCE_FILE_COUNT_MISMATCH:"
            f"{draft_count}!={len(draft_entries)}"
        )

    production_map, production_order = source_map(
        production_entries,
        "production",
    )
    draft_map, draft_order = source_map(draft_entries, "draft")
    candidate_map, _ = source_map(candidate_entries, "candidate")

    operations = spec.get("operations")
    if not isinstance(operations, list):
        raise ValidationError("OPERATIONS_NOT_LIST")

    operation_paths: set[str] = set()
    added_paths: set[str] = set()
    rebound_paths: set[str] = set()

    for index, raw_operation in enumerate(operations):
        if not isinstance(raw_operation, dict):
            raise ValidationError(f"OPERATION_NOT_OBJECT:{index}")
        source_path = raw_operation.get("source_path")
        operation = raw_operation.get("operation")
        old_sha = raw_operation.get("old_sha256")
        new_sha = raw_operation.get("new_sha256")
        rollback_action = raw_operation.get("rollback_action")
        rollback_sha = raw_operation.get("rollback_sha256")

        if not isinstance(source_path, str) or not source_path:
            raise ValidationError(f"OPERATION_SOURCE_PATH_INVALID:{index}")
        if source_path in operation_paths:
            raise ValidationError(f"OPERATION_SOURCE_PATH_DUPLICATE:{source_path}")
        operation_paths.add(source_path)

        if not isinstance(new_sha, str) or not SHA_RE.fullmatch(new_sha):
            raise ValidationError(f"OPERATION_NEW_SHA_INVALID:{source_path}")
        if source_path not in draft_map:
            raise ValidationError(f"OPERATION_SOURCE_MISSING_IN_DRAFT:{source_path}")
        if source_path not in candidate_map:
            raise ValidationError(
                f"OPERATION_SOURCE_MISSING_IN_CANDIDATE:{source_path}"
            )
        if entry_sha(draft_map[source_path], source_path) != new_sha:
            raise ValidationError(f"OPERATION_DRAFT_SHA_MISMATCH:{source_path}")
        if entry_sha(candidate_map[source_path], source_path) != new_sha:
            raise ValidationError(f"OPERATION_CANDIDATE_SHA_MISMATCH:{source_path}")

        if operation == "ADD_SOURCE_BINDING":
            if source_path in production_map:
                raise ValidationError(f"ADD_SOURCE_ALREADY_IN_PRODUCTION:{source_path}")
            if old_sha is not None or rollback_sha is not None:
                raise ValidationError(f"ADD_SOURCE_OLD_OR_ROLLBACK_SHA_NOT_NULL:{source_path}")
            if rollback_action != "REMOVE_ADDED_SOURCE_BINDING":
                raise ValidationError(f"ADD_SOURCE_ROLLBACK_ACTION_INVALID:{source_path}")
            added_paths.add(source_path)
        elif operation == "REBIND_EXISTING_SOURCE":
            if source_path not in production_map:
                raise ValidationError(f"REBIND_SOURCE_NOT_IN_PRODUCTION:{source_path}")
            production_sha = entry_sha(production_map[source_path], source_path)
            if old_sha != production_sha:
                raise ValidationError(f"REBIND_OLD_SHA_MISMATCH:{source_path}")
            if rollback_sha != production_sha:
                raise ValidationError(f"REBIND_ROLLBACK_SHA_MISMATCH:{source_path}")
            if rollback_action != "RESTORE_PRIOR_SHA":
                raise ValidationError(f"REBIND_ROLLBACK_ACTION_INVALID:{source_path}")
            if set(draft_map[source_path]) != set(production_map[source_path]):
                raise ValidationError(f"REBIND_ENTRY_SCHEMA_CHANGED:{source_path}")
            rebound_paths.add(source_path)
        else:
            raise ValidationError(f"OPERATION_TYPE_INVALID:{source_path}:{operation}")

    deleted_paths = set(production_map) - set(draft_map)
    if deleted_paths:
        raise ValidationError(f"PRODUCTION_SOURCE_DELETED:{sorted(deleted_paths)}")

    unexpected_added = set(draft_map) - set(production_map) - added_paths
    if unexpected_added:
        raise ValidationError(f"UNEXPECTED_SOURCE_ADDED:{sorted(unexpected_added)}")

    unchanged_paths = set(production_map) - rebound_paths
    for source_path in sorted(unchanged_paths):
        if draft_map[source_path] != production_map[source_path]:
            raise ValidationError(f"UNCHANGED_SOURCE_ENTRY_MUTATED:{source_path}")

    for source_path in sorted(added_paths):
        candidate_entry = candidate_map[source_path]
        draft_entry = draft_map[source_path]
        if set(draft_entry) != set(production_entries[0]):
            raise ValidationError(f"ADDED_SOURCE_ENTRY_SCHEMA_INVALID:{source_path}")
        for key in draft_entry:
            if key in {"path", "sha256", "source_sha256", "current_sha256", "file_sha256", "size", "mode"}:
                continue
            if key in candidate_entry and draft_entry[key] != candidate_entry[key]:
                raise ValidationError(
                    f"ADDED_SOURCE_METADATA_MISMATCH:{source_path}:{key}"
                )

    expected_order = [
        path for path in draft_order if path in production_map or path in added_paths
    ]
    if expected_order != draft_order:
        raise ValidationError("DRAFT_SOURCE_ORDER_INVALID")

    for source_path in sorted(operation_paths):
        check_actual_file(repo, source_path, draft_map[source_path])

    for source_path in sorted(set(draft_map) - operation_paths):
        actual_path = repo / source_path
        if actual_path.is_file():
            actual_size = actual_path.stat().st_size
            if entry_size(draft_map[source_path], source_path) != actual_size:
                raise ValidationError(
                    f"UNCHANGED_SOURCE_SIZE_MISMATCH:{source_path}"
                )
            actual_mode = f"0{stat.S_IMODE(actual_path.stat().st_mode):03o}"
            if entry_mode(draft_map[source_path], source_path) != actual_mode:
                raise ValidationError(
                    f"UNCHANGED_SOURCE_MODE_MISMATCH:{source_path}"
                )

    if draft_count != production_count + len(added_paths):
        raise ValidationError(
            "DRAFT_SOURCE_COUNT_DELTA_INVALID:"
            f"{draft_count}!={production_count}+{len(added_paths)}"
        )

    return {
        "schema_version": "2.0",
        "result": "PASS_SHADOW_PRODUCTION_MANIFEST_SEMANTIC_VALIDATION_V2",
        "production_manifest_sha256": sha(production_path),
        "shadow_draft_sha256": sha(draft_path),
        "operation_spec_sha256": sha(spec_path),
        "candidate_snapshot_sha256": sha(candidate_path),
        "top_level_schema_preserved": True,
        "unrelated_top_level_metadata_preserved": True,
        "production_source_file_count": production_count,
        "draft_source_file_count": draft_count,
        "draft_source_file_count_matches_length": True,
        "source_paths_unique": True,
        "source_paths_repository_relative": True,
        "source_sha_format_valid": True,
        "source_size_validated": True,
        "source_mode_validated": True,
        "unchanged_source_entries_preserved": True,
        "added_source_count": len(added_paths),
        "rebound_source_count": len(rebound_paths),
        "deleted_source_count": 0,
        "unexpected_added_source_count": 0,
        "rollback_actions_validated": True,
        "production_manifest_modified": False,
        "application_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        report = validate(args)
    except Exception as exc:
        print(f"VALIDATION_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output).resolve()
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYVALIDATOR

cat > "$SHADOW_ROOT/packet/validate_migration_semantics_v2.py" <<'PYMIGRATION'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

INDEX_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ValidationError(ValueError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def safe_eval(node: ast.AST, constants: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, bool, type(None))):
            return node.value
        raise ValidationError("UNSUPPORTED_CONSTANT_TYPE")

    if isinstance(node, ast.Name):
        if node.id not in constants:
            raise ValidationError(f"UNRESOLVED_CONSTANT:{node.id}")
        return constants[node.id]

    if isinstance(node, ast.List):
        return [safe_eval(item, constants) for item in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(safe_eval(item, constants) for item in node.elts)

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = safe_eval(node.left, constants)
        right = safe_eval(node.right, constants)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        raise ValidationError("UNSAFE_OR_UNSUPPORTED_BINOP")

    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                parts.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                value = safe_eval(part.value, constants)
                if not isinstance(value, (str, int)):
                    raise ValidationError("UNSUPPORTED_FSTRING_VALUE")
                parts.append(str(value))
            else:
                raise ValidationError("UNSUPPORTED_FSTRING_PART")
        return "".join(parts)

    if isinstance(node, ast.Call):
        call_name = qualified_name(node.func)
        if call_name in {"sa.text", "sqlalchemy.text"}:
            if len(node.args) != 1 or node.keywords:
                raise ValidationError("TEXT_CALL_SIGNATURE_INVALID")
            value = safe_eval(node.args[0], constants)
            if not isinstance(value, str):
                raise ValidationError("TEXT_CALL_ARGUMENT_NOT_STRING")
            return value

    raise ValidationError(
        f"UNSUPPORTED_STATIC_EXPRESSION:{type(node).__name__}"
    )


def resolve_module_constants(tree: ast.Module) -> dict[str, Any]:
    pending: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    pending.append((target.id, node.value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                pending.append((node.target.id, node.value))

    constants: dict[str, Any] = {}
    progress = True
    while progress and pending:
        progress = False
        next_pending: list[tuple[str, ast.AST]] = []
        for name, expression in pending:
            try:
                constants[name] = safe_eval(expression, constants)
            except ValidationError as exc:
                if str(exc).startswith("UNRESOLVED_CONSTANT:"):
                    next_pending.append((name, expression))
                    continue
                next_pending.append((name, expression))
                continue
            progress = True
        pending = next_pending

    return constants


def function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise ValidationError(
            f"MIGRATION_FUNCTION_COUNT_INVALID:{name}:{len(matches)}"
        )
    return matches[0]


def calls_in(function: ast.FunctionDef, call_name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and qualified_name(node.func) == call_name
    ]


def keyword_map(
    call: ast.Call,
    constants: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg is None:
            raise ValidationError("STAR_KEYWORD_NOT_ALLOWED")
        result[keyword.arg] = safe_eval(keyword.value, constants)
    return result


def assignment_string(
    tree: ast.Module,
    name: str,
    constants: dict[str, Any],
) -> str:
    if name not in constants or not isinstance(constants[name], str):
        raise ValidationError(f"MODULE_STRING_CONSTANT_UNRESOLVED:{name}")
    return constants[name]


def validate_migration(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    constants = resolve_module_constants(tree)

    revision = assignment_string(tree, "revision", constants)
    down_revision = assignment_string(tree, "down_revision", constants)
    resolved_index_name = assignment_string(tree, "INDEX_NAME", constants)

    if resolved_index_name == "INDEX_NAME":
        raise ValidationError("INDEX_NAME_PLACEHOLDER_NOT_RESOLVED")
    if not INDEX_NAME_RE.fullmatch(resolved_index_name):
        raise ValidationError(
            f"INDEX_NAME_FORMAT_INVALID:{resolved_index_name}"
        )
    lowered = resolved_index_name.lower()
    if "ebook_items" not in lowered or "wordpress_post_id" not in lowered:
        raise ValidationError(
            f"INDEX_NAME_SEMANTIC_COMPONENTS_MISSING:{resolved_index_name}"
        )

    upgrade = function_node(tree, "upgrade")
    downgrade = function_node(tree, "downgrade")
    create_calls = calls_in(upgrade, "op.create_index")
    drop_calls = calls_in(downgrade, "op.drop_index")

    if len(create_calls) != 1:
        raise ValidationError(
            f"CREATE_INDEX_CALL_COUNT_INVALID:{len(create_calls)}"
        )
    if len(drop_calls) != 1:
        raise ValidationError(
            f"DROP_INDEX_CALL_COUNT_INVALID:{len(drop_calls)}"
        )

    create_call = create_calls[0]
    drop_call = drop_calls[0]
    if len(create_call.args) < 3:
        raise ValidationError("CREATE_INDEX_POSITIONAL_ARGS_INCOMPLETE")

    create_index_symbol = (
        create_call.args[0].id
        if isinstance(create_call.args[0], ast.Name)
        else None
    )
    create_index_name = safe_eval(create_call.args[0], constants)
    table_name = safe_eval(create_call.args[1], constants)
    columns = safe_eval(create_call.args[2], constants)
    create_keywords = keyword_map(create_call, constants)

    drop_index_symbol = (
        drop_call.args[0].id
        if drop_call.args and isinstance(drop_call.args[0], ast.Name)
        else None
    )
    drop_keywords = keyword_map(drop_call, constants)
    drop_index_name = (
        safe_eval(drop_call.args[0], constants)
        if drop_call.args
        else drop_keywords.get("index_name")
    )
    drop_table_name = (
        safe_eval(drop_call.args[1], constants)
        if len(drop_call.args) > 1
        else drop_keywords.get("table_name")
    )

    unique = create_keywords.get("unique")
    sqlite_where = create_keywords.get("sqlite_where")
    if not isinstance(sqlite_where, str):
        raise ValidationError("SQLITE_WHERE_NOT_RESOLVED_STRING")
    normalized_where = " ".join(sqlite_where.split()).upper()

    if create_index_symbol != "INDEX_NAME":
        raise ValidationError(
            f"CREATE_INDEX_CONSTANT_SYMBOL_INVALID:{create_index_symbol}"
        )
    if drop_index_symbol != "INDEX_NAME":
        raise ValidationError(
            f"DROP_INDEX_CONSTANT_SYMBOL_INVALID:{drop_index_symbol}"
        )
    if create_index_name != resolved_index_name:
        raise ValidationError("CREATE_INDEX_RESOLUTION_MISMATCH")
    if drop_index_name != resolved_index_name:
        raise ValidationError("DROP_INDEX_RESOLUTION_MISMATCH")
    if table_name != "ebook_items":
        raise ValidationError(f"TABLE_NAME_INVALID:{table_name!r}")
    if drop_table_name not in (None, "ebook_items"):
        raise ValidationError(
            f"DROP_TABLE_NAME_INVALID:{drop_table_name!r}"
        )
    if columns != ["wordpress_post_id"]:
        raise ValidationError(f"INDEX_COLUMNS_INVALID:{columns!r}")
    if unique is not True:
        raise ValidationError(f"UNIQUE_FLAG_INVALID:{unique!r}")
    if normalized_where != "WORDPRESS_POST_ID IS NOT NULL":
        raise ValidationError(
            f"SQLITE_WHERE_SEMANTICS_INVALID:{sqlite_where!r}"
        )

    return {
        "schema_version": "2.0",
        "result": "PASS_MIGRATION_STATIC_SEMANTIC_VALIDATION_V2",
        "migration_path": str(path),
        "migration_sha256": sha(path),
        "revision": revision,
        "down_revision": down_revision,
        "module_constants": {
            "INDEX_NAME": resolved_index_name,
        },
        "upgrade": {
            "create_index_call_count": 1,
            "index_constant_name": create_index_symbol,
            "resolved_index_name": create_index_name,
            "table_name": table_name,
            "columns": columns,
            "unique": unique,
            "sqlite_where": sqlite_where,
            "normalized_where": normalized_where,
        },
        "downgrade": {
            "drop_index_call_count": 1,
            "index_constant_name": drop_index_symbol,
            "resolved_index_name": drop_index_name,
            "table_name": drop_table_name,
            "matches_upgrade_index": True,
        },
        "actual_index_name_resolved": True,
        "sql_executed": False,
        "migration_applied": False,
        "static_validation_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migration", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        report = validate_migration(Path(args.migration).resolve())
    except Exception as exc:
        print(f"VALIDATION_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        return 1

    Path(args.output).resolve().write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYMIGRATION

python3 - \
    "$REPO_ROOT" \
    "$PRODUCTION_MANIFEST" \
    "$CANDIDATE_SNAPSHOT" \
    "$CLOSURE_SNAPSHOT" \
    "$DOWNSTREAM_SNAPSHOT" \
    "$SHADOW_ROOT/packet" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PYGENERATE'
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve()
production_manifest_path = Path(sys.argv[2]).resolve()
candidate_snapshot_path = Path(sys.argv[3]).resolve()
closure_snapshot_path = Path(sys.argv[4]).resolve()
downstream_snapshot_path = Path(sys.argv[5]).resolve()
packet_root = Path(sys.argv[6]).resolve()
candidate_id = sys.argv[7]
review_bundle_id = sys.argv[8]

HASH_KEYS = ("sha256", "source_sha256", "current_sha256", "file_sha256")


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


def entry_path(entry: dict[str, Any]) -> str | None:
    value = entry.get("path")
    return value if isinstance(value, str) else None


def hash_keys(entry: dict[str, Any]) -> list[str]:
    return [key for key in HASH_KEYS if key in entry]


def primary_sha(entry: dict[str, Any], label: str) -> str:
    keys = hash_keys(entry)
    if not keys:
        raise SystemExit(f"HASH_FIELD_MISSING:{label}")
    values = {entry[key] for key in keys}
    if len(values) != 1:
        raise SystemExit(f"HASH_FIELD_CONFLICT:{label}")
    value = next(iter(values))
    if not isinstance(value, str):
        raise SystemExit(f"HASH_VALUE_INVALID:{label}")
    return value


production = load_json(production_manifest_path)
candidate = load_json(candidate_snapshot_path)

if candidate.get("candidate_id") != candidate_id:
    raise SystemExit("CANDIDATE_ID_MISMATCH")

production_entries = production.get("source_files")
candidate_entries = candidate.get("source_files")
if not isinstance(production_entries, list):
    raise SystemExit("PRODUCTION_SOURCE_FILES_INVALID")
if not isinstance(candidate_entries, list):
    raise SystemExit("CANDIDATE_SOURCE_FILES_INVALID")
if production.get("source_file_count") != len(production_entries):
    raise SystemExit("PRODUCTION_SOURCE_FILE_COUNT_MISMATCH")

known_sources = {
    "app/db/access_guard.py": "1584ac2975a39433fbf4670bbd2ea9974870866f6193cf8036f9528e72669583",
    "app/db/config.py": "5eeef8af4343d1e16412df40945f19667ee0f41dcbdea4a9f74386f12f7ddd59",
    "app/db/repositories/workflow_state_repository.py": "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "app/db/session.py": "0d6a0c2de0f5ab4691eae5d1dc311bf7d800461b7949d5ef1895fbc4b5b1d818",
    "scripts/run_slack_approval_socket.py": "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6",
}

production_by_path = {
    entry_path(entry): (index, entry)
    for index, entry in enumerate(production_entries)
    if isinstance(entry, dict) and entry_path(entry)
}
candidate_by_path = {
    entry_path(entry): (index, entry)
    for index, entry in enumerate(candidate_entries)
    if isinstance(entry, dict) and entry_path(entry)
}

for source_path, expected_sha in known_sources.items():
    if source_path not in candidate_by_path:
        raise SystemExit(f"CANDIDATE_SOURCE_MISSING:{source_path}")
    candidate_entry = candidate_by_path[source_path][1]
    if primary_sha(candidate_entry, f"candidate:{source_path}") != expected_sha:
        raise SystemExit(f"CANDIDATE_SHA_MISMATCH:{source_path}")
    actual_path = repo / source_path
    if sha(actual_path) != expected_sha:
        raise SystemExit(f"REPOSITORY_SHA_MISMATCH:{source_path}")

draft = copy.deepcopy(production)
draft_entries = draft["source_files"]

for source_path, new_sha in known_sources.items():
    if source_path not in production_by_path:
        continue
    production_index, production_entry = production_by_path[source_path]
    candidate_entry = candidate_by_path[source_path][1]
    updated = copy.deepcopy(production_entry)

    for key in hash_keys(updated):
        updated[key] = new_sha

    actual_path = repo / source_path
    if "size" in updated:
        updated["size"] = actual_path.stat().st_size
    if "mode" in updated:
        updated["mode"] = f"0{stat.S_IMODE(actual_path.stat().st_mode):03o}"

    for key in ("size", "mode"):
        if key in candidate_entry and key in updated:
            if candidate_entry[key] != updated[key]:
                raise SystemExit(
                    f"CANDIDATE_REPOSITORY_{key.upper()}_MISMATCH:{source_path}"
                )

    draft_entries[production_index] = updated

schema_counter = Counter(
    tuple(sorted(entry.keys()))
    for entry in production_entries
    if isinstance(entry, dict)
)
dominant_schema = set(schema_counter.most_common(1)[0][0])

for source_path, new_sha in known_sources.items():
    if source_path in production_by_path:
        continue

    candidate_index, candidate_entry = candidate_by_path[source_path]
    actual_path = repo / source_path
    new_entry: dict[str, Any] = {}

    for key in sorted(dominant_schema):
        if key == "path":
            new_entry[key] = source_path
        elif key in HASH_KEYS:
            new_entry[key] = new_sha
        elif key == "size":
            new_entry[key] = actual_path.stat().st_size
        elif key == "mode":
            new_entry[key] = f"0{stat.S_IMODE(actual_path.stat().st_mode):03o}"
        elif key in candidate_entry:
            new_entry[key] = copy.deepcopy(candidate_entry[key])
        else:
            raise SystemExit(
                f"ADDED_SOURCE_SCHEMA_VALUE_UNRESOLVED:{source_path}:{key}"
            )

    current_by_path = {
        entry_path(entry): index
        for index, entry in enumerate(draft_entries)
        if isinstance(entry, dict) and entry_path(entry)
    }
    insertion_index: int | None = None
    for later_entry in candidate_entries[candidate_index + 1 :]:
        later_path = entry_path(later_entry)
        if later_path in current_by_path:
            insertion_index = current_by_path[later_path]
            break
    if insertion_index is None:
        for earlier_entry in reversed(candidate_entries[:candidate_index]):
            earlier_path = entry_path(earlier_entry)
            if earlier_path in current_by_path:
                insertion_index = current_by_path[earlier_path] + 1
                break
    if insertion_index is None:
        insertion_index = 0

    draft_entries.insert(insertion_index, new_entry)

draft["source_file_count"] = len(draft_entries)
if draft["source_file_count"] != 17:
    raise SystemExit(
        f"DRAFT_SOURCE_FILE_COUNT_NOT_17:{draft['source_file_count']}"
    )

draft_by_path = {
    entry_path(entry): (index, entry)
    for index, entry in enumerate(draft_entries)
    if isinstance(entry, dict) and entry_path(entry)
}

operations: list[dict[str, Any]] = []
for source_path, new_sha in known_sources.items():
    candidate_index = candidate_by_path[source_path][0]
    draft_index = draft_by_path[source_path][0]

    if source_path in production_by_path:
        production_index, production_entry = production_by_path[source_path]
        old_sha = primary_sha(production_entry, f"production:{source_path}")
        operation = "REBIND_EXISTING_SOURCE"
        rollback_action = "RESTORE_PRIOR_SHA"
        rollback_sha = old_sha
        production_pointer: str | None = f"$.source_files[{production_index}]"
    else:
        old_sha = None
        operation = "ADD_SOURCE_BINDING"
        rollback_action = "REMOVE_ADDED_SOURCE_BINDING"
        rollback_sha = None
        production_pointer = None

    operations.append(
        {
            "source_path": source_path,
            "operation": operation,
            "old_sha256": old_sha,
            "new_sha256": new_sha,
            "production_json_pointer": production_pointer,
            "shadow_draft_json_pointer": f"$.source_files[{draft_index}]",
            "candidate_json_pointer": f"$.source_files[{candidate_index}]",
            "rollback_action": rollback_action,
            "rollback_sha256": rollback_sha,
            "human_review_required": True,
            "application_allowed": False,
        }
    )

draft_path = packet_root / "shadow-production-manifest-draft-v2.json"
write_json(draft_path, draft)

production_pretty = (
    json.dumps(production, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
)
draft_pretty = draft_path.read_text(encoding="utf-8")
diff_text = "".join(
    difflib.unified_diff(
        production_pretty.splitlines(keepends=True),
        draft_pretty.splitlines(keepends=True),
        fromfile="a/config/slack_worker_release_source_manifest.json",
        tofile="b/shadow/config/slack_worker_release_source_manifest.json",
        n=5,
    )
)
(packet_root / "shadow-production-manifest-draft-v2.diff").write_text(
    diff_text,
    encoding="utf-8",
)

write_json(
    packet_root / "production-manifest-corrective-rebind-spec-v2.json",
    {
        "schema_version": "2.0",
        "phase": "TST-5D-W2B-I2F-3E-C1",
        "status": "SHADOW_DRAFT_ONLY_NOT_APPROVED_FOR_APPLICATION",
        "candidate_id": candidate_id,
        "review_bundle_id": review_bundle_id,
        "production_manifest": {
            "path": str(production_manifest_path.relative_to(repo)),
            "sha256": sha(production_manifest_path),
            "source_file_count": production["source_file_count"],
            "modified": False,
        },
        "candidate_input_snapshot": {
            "candidate_manifest_path": str(candidate_snapshot_path),
            "candidate_manifest_sha256": sha(candidate_snapshot_path),
            "dependency_closure_path": str(closure_snapshot_path),
            "dependency_closure_sha256": sha(closure_snapshot_path),
            "downstream_plan_path": str(downstream_snapshot_path),
            "downstream_plan_sha256": sha(downstream_snapshot_path),
            "uses_tmp_input": False,
        },
        "shadow_draft": {
            "path": draft_path.name,
            "sha256": sha(draft_path),
            "source_file_count": draft["source_file_count"],
            "source_files_length": len(draft_entries),
            "source_file_count_matches_length": True,
            "production_schema_preserved": set(draft) == set(production),
        },
        "operations": operations,
        "operation_counts": {
            "add": sum(
                item["operation"] == "ADD_SOURCE_BINDING"
                for item in operations
            ),
            "rebind": sum(
                item["operation"] == "REBIND_EXISTING_SOURCE"
                for item in operations
            ),
        },
        "production_manifest_write_performed": False,
        "application_allowed": False,
    },
)

readme = (
    "# 3E-C1 Manifest and Migration Semantic Correction Packet\n\n"
    "Status: SHADOW / EVIDENCE ONLY — NOT APPROVED FOR APPLICATION\n\n"
    "Corrections:\n"
    "- source_file_count is updated to 17 and validated against source_files length.\n"
    "- path uniqueness, SHA format, size, mode, unchanged entries, and unrelated metadata are validated.\n"
    "- migration INDEX_NAME is resolved from the module-level constant to its actual string value.\n"
    "- ADD and REBIND operations carry explicit rollback actions.\n"
    "- Existing 3E-C evidence remains immutable.\n\n"
    "No production manifest, DB, migration, source, test, deployment,\n"
    "approval, network, or worker action is performed.\n"
)
(packet_root / "README.md").write_text(readme, encoding="utf-8")
PYGENERATE

MANIFEST_VALIDATOR="${SHADOW_ROOT}/packet/validate_shadow_production_manifest_v2.py"
MANIFEST_DRAFT="${SHADOW_ROOT}/packet/shadow-production-manifest-draft-v2.json"
MANIFEST_SPEC="${SHADOW_ROOT}/packet/production-manifest-corrective-rebind-spec-v2.json"
MANIFEST_VALIDATION="${SHADOW_ROOT}/packet/shadow-production-manifest-semantic-validation-v2.json"

python3 "$MANIFEST_VALIDATOR" \
    --production "$PRODUCTION_MANIFEST" \
    --draft "$MANIFEST_DRAFT" \
    --spec "$MANIFEST_SPEC" \
    --candidate "$CANDIDATE_SNAPSHOT" \
    --repo "$REPO_ROOT" \
    --output "$MANIFEST_VALIDATION"

python3 -m json.tool "$MANIFEST_VALIDATION" >/dev/null

if [[ "$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["result"])' \
        "$MANIFEST_VALIDATION"
)" != "PASS_SHADOW_PRODUCTION_MANIFEST_SEMANTIC_VALIDATION_V2" ]]; then
    printf 'ERROR=MANIFEST_SEMANTIC_VALIDATION_V2_FAILED\n' >&2
    exit 1
fi

MIGRATION_VALIDATOR="${SHADOW_ROOT}/packet/validate_migration_semantics_v2.py"
MIGRATION_VALIDATION="${SHADOW_ROOT}/packet/migration-static-semantic-validation-v2.json"

python3 "$MIGRATION_VALIDATOR" \
    --migration "$WORKFLOW_MIGRATION" \
    --output "$MIGRATION_VALIDATION"

python3 -m json.tool "$MIGRATION_VALIDATION" >/dev/null

if [[ "$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["result"])' \
        "$MIGRATION_VALIDATION"
)" != "PASS_MIGRATION_STATIC_SEMANTIC_VALIDATION_V2" ]]; then
    printf 'ERROR=MIGRATION_SEMANTIC_VALIDATION_V2_FAILED\n' >&2
    exit 1
fi

RESOLVED_INDEX_NAME="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["module_constants"]["INDEX_NAME"])' \
        "$MIGRATION_VALIDATION"
)"

python3 - \
    "$MIGRATION_VALIDATION" \
    "$SHADOW_ROOT/packet/migration-shadow-rehearsal-plan-v2.json" <<'PYPLAN'
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

validation_path = Path(sys.argv[1]).resolve()
output_path = Path(sys.argv[2]).resolve()

validation = json.loads(validation_path.read_text(encoding="utf-8"))
if validation.get("result") != "PASS_MIGRATION_STATIC_SEMANTIC_VALIDATION_V2":
    raise SystemExit("MIGRATION_VALIDATION_V2_REQUIRED")

index_name = validation["module_constants"]["INDEX_NAME"]
table_name = validation["upgrade"]["table_name"]
columns = validation["upgrade"]["columns"]
sqlite_where = validation["upgrade"]["sqlite_where"]

plan: dict[str, Any] = {
    "schema_version": "2.0",
    "status": "SHADOW_REHEARSAL_PLAN_ONLY_NOT_EXECUTED",
    "validated_migration_semantics_sha256": __import__("hashlib").sha256(
        validation_path.read_bytes()
    ).hexdigest(),
    "resolved_index_contract": {
        "index_constant_name": "INDEX_NAME",
        "resolved_index_name": index_name,
        "table_name": table_name,
        "columns": columns,
        "unique": True,
        "sqlite_where": sqlite_where,
        "upgrade_create_count": 1,
        "downgrade_drop_count": 1,
    },
    "shadow_rehearsal_sequence": [
        "Create a unique temporary SQLite rehearsal database from an approved schema baseline or verified backup clone.",
        "Confirm its Alembic revision equals down_revision 29962ac6d9a5.",
        "Seed multiple NULL wordpress_post_id values and distinct non-NULL values.",
        "Apply only revision 00241611109d to the temporary database.",
        f"Verify sqlite_master contains unique index {index_name!r} on {table_name!r}.",
        f"Verify columns equal {columns!r}.",
        f"Verify the predicate is semantically {sqlite_where!r}.",
        "Verify multiple NULL values remain allowed.",
        "Verify duplicate non-NULL wordpress_post_id insertion is rejected.",
        "Run integrity_check and foreign_key_check.",
        "Downgrade exactly one revision.",
        f"Verify index {index_name!r} is removed.",
        "Restore a fresh clone and repeat upgrade to confirm repeatability.",
        "Preserve all logs, schema dumps, SHA values, and exit codes.",
    ],
    "production_database_opened": False,
    "sql_executed": False,
    "migration_applied": False,
}

output_path.write_text(
    json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PYPLAN

cat > "$SHADOW_ROOT/packet/run_manifest_validator_negative_selftests.py" <<'PYSELFTEST'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validator", required=True)
    parser.add_argument("--production", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    validator = Path(args.validator).resolve()
    production = Path(args.production).resolve()
    valid_draft_path = Path(args.draft).resolve()
    spec = Path(args.spec).resolve()
    candidate = Path(args.candidate).resolve()
    repo = Path(args.repo).resolve()
    workdir = Path(args.workdir).resolve()
    output = Path(args.output).resolve()
    workdir.mkdir(parents=True, exist_ok=False)

    valid_draft = json.loads(valid_draft_path.read_text(encoding="utf-8"))
    operations = json.loads(spec.read_text(encoding="utf-8"))["operations"]
    changed_paths = {item["source_path"] for item in operations}

    cases: list[tuple[str, dict[str, Any], str]] = []

    count_bad = copy.deepcopy(valid_draft)
    count_bad["source_file_count"] -= 1
    cases.append(
        (
            "source_file_count_mismatch",
            count_bad,
            "DRAFT_SOURCE_FILE_COUNT_MISMATCH",
        )
    )

    duplicate_bad = copy.deepcopy(valid_draft)
    duplicate_bad["source_files"][1]["path"] = duplicate_bad["source_files"][0]["path"]
    cases.append(
        ("duplicate_path", duplicate_bad, "SOURCE_PATH_DUPLICATE")
    )

    sha_bad = copy.deepcopy(valid_draft)
    sha_bad["source_files"][0]["sha256"] = "not-a-sha"
    cases.append(("invalid_sha", sha_bad, "SOURCE_SHA_INVALID"))

    size_bad = copy.deepcopy(valid_draft)
    size_bad["source_files"][0]["size"] += 1
    cases.append(("size_mismatch", size_bad, "SOURCE_SIZE_MISMATCH"))

    mode_bad = copy.deepcopy(valid_draft)
    mode_bad["source_files"][0]["mode"] = "0999"
    cases.append(("invalid_mode", mode_bad, "SOURCE_MODE_INVALID"))

    metadata_bad = copy.deepcopy(valid_draft)
    metadata_key = next(
        key
        for key in metadata_bad
        if key not in {"source_file_count", "source_files"}
    )
    original = metadata_bad[metadata_key]
    if isinstance(original, bool):
        metadata_bad[metadata_key] = not original
    elif isinstance(original, int):
        metadata_bad[metadata_key] = original + 1
    elif isinstance(original, str):
        metadata_bad[metadata_key] = original + "-mutated"
    elif isinstance(original, list):
        metadata_bad[metadata_key] = original + ["mutated"]
    elif isinstance(original, dict):
        metadata_bad[metadata_key] = {**original, "_mutated": True}
    else:
        raise SystemExit(f"UNSUPPORTED_METADATA_TYPE:{metadata_key}")
    cases.append(
        (
            "unrelated_metadata_mutation",
            metadata_bad,
            "UNRELATED_TOP_LEVEL_METADATA_CHANGED",
        )
    )

    unchanged_bad = copy.deepcopy(valid_draft)
    unchanged_index = next(
        index
        for index, entry in enumerate(unchanged_bad["source_files"])
        if entry["path"] not in changed_paths
    )
    unchanged_bad["source_files"][unchanged_index]["size"] += 1
    cases.append(
        (
            "unchanged_entry_mutation",
            unchanged_bad,
            "UNCHANGED_SOURCE_ENTRY_MUTATED",
        )
    )

    results: list[dict[str, Any]] = []
    for case_name, payload, expected_error in cases:
        case_path = workdir / f"{case_name}.json"
        case_output = workdir / f"{case_name}.output.json"
        write_json(case_path, payload)

        completed = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--production",
                str(production),
                "--draft",
                str(case_path),
                "--spec",
                str(spec),
                "--candidate",
                str(candidate),
                "--repo",
                str(repo),
                "--output",
                str(case_output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        combined = completed.stdout + completed.stderr
        passed = completed.returncode != 0 and expected_error in combined
        results.append(
            {
                "case": case_name,
                "expected_error": expected_error,
                "exit_code": completed.returncode,
                "expected_rejection_observed": passed,
                "draft_sha256": sha(case_path),
            }
        )
        if not passed:
            print(
                f"SELFTEST_FAILED:{case_name}:"
                f"exit={completed.returncode}:output={combined}",
                file=sys.stderr,
            )
            return 1

    report = {
        "schema_version": "1.0",
        "result": "PASS_MANIFEST_VALIDATOR_NEGATIVE_SELFTESTS",
        "case_count": len(results),
        "passed_count": sum(
            item["expected_rejection_observed"] for item in results
        ),
        "cases": results,
        "production_manifest_modified": False,
        "repository_source_modified": False,
    }
    write_json(output, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYSELFTEST

SELFTEST_RUNNER="${SHADOW_ROOT}/packet/run_manifest_validator_negative_selftests.py"
SELFTEST_WORKDIR="${SHADOW_ROOT}/selftest/cases"
SELFTEST_RESULT="${SHADOW_ROOT}/packet/manifest-validator-negative-selftests.json"

python3 "$SELFTEST_RUNNER" \
    --validator "$MANIFEST_VALIDATOR" \
    --production "$PRODUCTION_MANIFEST" \
    --draft "$MANIFEST_DRAFT" \
    --spec "$MANIFEST_SPEC" \
    --candidate "$CANDIDATE_SNAPSHOT" \
    --repo "$REPO_ROOT" \
    --workdir "$SELFTEST_WORKDIR" \
    --output "$SELFTEST_RESULT"

python3 -m json.tool "$SELFTEST_RESULT" >/dev/null

if [[ "$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["result"])' \
        "$SELFTEST_RESULT"
)" != "PASS_MANIFEST_VALIDATOR_NEGATIVE_SELFTESTS" ]]; then
    printf 'ERROR=MANIFEST_VALIDATOR_NEGATIVE_SELFTESTS_FAILED\n' >&2
    exit 1
fi

PYTHONPYCACHEPREFIX="$SHADOW_ROOT/pycache" \
    python3 -m py_compile "$MANIFEST_VALIDATOR"
PYTHONPYCACHEPREFIX="$SHADOW_ROOT/pycache" \
    python3 -m py_compile "$MIGRATION_VALIDATOR"
PYTHONPYCACHEPREFIX="$SHADOW_ROOT/pycache" \
    python3 -m py_compile "$SELFTEST_RUNNER"
PYTHONPYCACHEPREFIX="$SHADOW_ROOT/pycache" \
    python3 -m py_compile \
    "$SHADOW_ROOT/packet/test_slack_approval_socket_hold_remediation_offline.candidate.py"

python3 - \
    "$SHADOW_ROOT/packet" \
    "$CANDIDATE_SNAPSHOT" \
    "$CLOSURE_SNAPSHOT" \
    "$DOWNSTREAM_SNAPSHOT" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PYPACKET'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

packet_root = Path(sys.argv[1]).resolve()
candidate_path = Path(sys.argv[2]).resolve()
closure_path = Path(sys.argv[3]).resolve()
downstream_path = Path(sys.argv[4]).resolve()
candidate_id = sys.argv[5]
review_bundle_id = sys.argv[6]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


files = sorted(
    path
    for path in packet_root.iterdir()
    if path.is_file()
    and path.name != "semantic-correction-packet-manifest.json"
)

write_json(
    packet_root / "semantic-correction-packet-manifest.json",
    {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-C1",
        "result": "PASS_3E_C1_SEMANTIC_CORRECTION_PACKET_GENERATED",
        "status": "SHADOW_ONLY_NOT_APPROVED_FOR_APPLICATION",
        "candidate_id": candidate_id,
        "review_bundle_id": review_bundle_id,
        "corrections": {
            "source_file_count_updated_to_17": True,
            "source_file_count_length_validation_passed": True,
            "source_path_uniqueness_validation_passed": True,
            "sha_format_validation_passed": True,
            "size_validation_passed": True,
            "mode_validation_passed": True,
            "unchanged_entry_validation_passed": True,
            "unrelated_metadata_validation_passed": True,
            "manifest_validator_negative_selftests_passed": True,
            "migration_index_constant_resolved": True,
            "migration_actual_index_name_validated": True,
            "add_rollback_action_added": True,
            "rebind_rollback_action_added": True,
            "existing_3e_c_evidence_modified": False,
        },
        "input_snapshots": {
            "candidate_manifest_sha256": sha(candidate_path),
            "dependency_closure_sha256": sha(closure_path),
            "downstream_plan_sha256": sha(downstream_path),
            "uses_tmp_input": False,
        },
        "packet_files": [
            {
                "name": path.name,
                "sha256": sha(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
        "packet_file_count_excluding_manifest": len(files),
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
            "production_approval_created": False,
            "external_network_used": False,
            "slack_worker_started": False,
            "production_release_approved": False,
        },
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "next_gate": "HUMAN_REVIEW_3E_C1_SEMANTIC_CORRECTION_PACKET",
    },
)
PYPACKET

find "$SHADOW_ROOT/packet" -type f -exec chmod 0444 {} +
cp -a "$SHADOW_ROOT/packet/." "$EVIDENCE_ROOT/packet-snapshot/"
find "$EVIDENCE_ROOT/packet-snapshot" -type f -exec chmod 0444 {} +

SHADOW_PACKET_MANIFEST="${SHADOW_ROOT}/packet/semantic-correction-packet-manifest.json"
EVIDENCE_PACKET_MANIFEST="${EVIDENCE_ROOT}/packet-snapshot/semantic-correction-packet-manifest.json"
SHADOW_PACKET_MANIFEST_SHA="$(sha256_file "$SHADOW_PACKET_MANIFEST")"
EVIDENCE_PACKET_MANIFEST_SHA="$(sha256_file "$EVIDENCE_PACKET_MANIFEST")"

if [[ "$SHADOW_PACKET_MANIFEST_SHA" != "$EVIDENCE_PACKET_MANIFEST_SHA" ]]; then
    printf 'ERROR=PACKET_MANIFEST_SNAPSHOT_SHA_MISMATCH\n' >&2
    exit 1
fi

PACKET_FILE_COUNT="$(find "$SHADOW_ROOT/packet" -maxdepth 1 -type f | wc -l)"
MANIFEST_DRAFT_SHA="$(sha256_file "$MANIFEST_DRAFT")"
MANIFEST_SPEC_SHA="$(sha256_file "$MANIFEST_SPEC")"
MANIFEST_VALIDATOR_SHA="$(sha256_file "$MANIFEST_VALIDATOR")"
MANIFEST_VALIDATION_SHA="$(sha256_file "$MANIFEST_VALIDATION")"
SELFTEST_RUNNER_SHA="$(sha256_file "$SELFTEST_RUNNER")"
SELFTEST_RESULT_SHA="$(sha256_file "$SELFTEST_RESULT")"
MIGRATION_VALIDATOR_SHA="$(sha256_file "$MIGRATION_VALIDATOR")"
MIGRATION_VALIDATION_SHA="$(sha256_file "$MIGRATION_VALIDATION")"
MIGRATION_REHEARSAL_PLAN_SHA="$(
    sha256_file "$SHADOW_ROOT/packet/migration-shadow-rehearsal-plan-v2.json"
)"

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/semantic-correction-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'semantic-correction-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"
chmod 0444 "$EVIDENCE_MANIFEST"
EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"

require_file_sha "$SOURCE_RESULT" "$EXPECTED_SOURCE_RESULT_SHA"
require_file_sha "$SOURCE_PACKET_MANIFEST" "$EXPECTED_SOURCE_PACKET_MANIFEST_SHA"
require_file_sha "$SOURCE_EVIDENCE_MANIFEST" "$EXPECTED_SOURCE_EVIDENCE_MANIFEST_SHA"
require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$PRODUCTION_DB" "$EXPECTED_PRODUCTION_DB_SHA"
require_file_sha "$WORKFLOW_MIGRATION" "$EXPECTED_WORKFLOW_MIGRATION_SHA"
require_file_sha "$ACCESS_GUARD_SOURCE" "$EXPECTED_ACCESS_GUARD_SHA"
require_file_sha "$DB_CONFIG_SOURCE" "$EXPECTED_DB_CONFIG_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$DB_SESSION_SOURCE" "$EXPECTED_DB_SESSION_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"

RESULT_JSON="${EVIDENCE_ROOT}/result.json"

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3E-C1",
  "result": "PASS_W2B_I2F3E_C1_MANIFEST_MIGRATION_SEMANTIC_CORRECTION_READY",
  "candidate_id": "${EXPECTED_CANDIDATE_ID}",
  "review_bundle_id": "${EXPECTED_REVIEW_BUNDLE_ID}",
  "shadow_root": "${SHADOW_ROOT}",
  "evidence_root": "${EVIDENCE_REL}",
  "packet": {
    "status": "SHADOW_ONLY_NOT_APPROVED_FOR_APPLICATION",
    "packet_file_count": ${PACKET_FILE_COUNT},
    "shadow_packet_manifest_sha256": "${SHADOW_PACKET_MANIFEST_SHA}",
    "evidence_packet_manifest_sha256": "${EVIDENCE_PACKET_MANIFEST_SHA}",
    "evidence_manifest_sha256": "${EVIDENCE_MANIFEST_SHA}"
  },
  "manifest": {
    "source_file_count": 17,
    "source_file_count_matches_length": true,
    "draft_sha256": "${MANIFEST_DRAFT_SHA}",
    "spec_sha256": "${MANIFEST_SPEC_SHA}",
    "validator_sha256": "${MANIFEST_VALIDATOR_SHA}",
    "validation_sha256": "${MANIFEST_VALIDATION_SHA}",
    "semantic_validation": "PASS",
    "negative_selftest_runner_sha256": "${SELFTEST_RUNNER_SHA}",
    "negative_selftest_result_sha256": "${SELFTEST_RESULT_SHA}",
    "negative_selftests": "PASS"
  },
  "migration": {
    "index_constant_name": "INDEX_NAME",
    "resolved_index_name": "${RESOLVED_INDEX_NAME}",
    "validator_sha256": "${MIGRATION_VALIDATOR_SHA}",
    "validation_sha256": "${MIGRATION_VALIDATION_SHA}",
    "rehearsal_plan_sha256": "${MIGRATION_REHEARSAL_PLAN_SHA}",
    "semantic_validation": "PASS"
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
    "production_approval_created": false,
    "external_network_used": false,
    "slack_worker_started": false,
    "production_release_approved": false
  },
  "safety": {
    "existing_3e_c_result_changed": false,
    "existing_3e_c_packet_manifest_changed": false,
    "existing_3e_c_evidence_manifest_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "workflow_migration_changed": false,
    "repository_source_changed": false
  },
  "production_release_decision": "HOLD",
  "release_status": "CANDIDATE_NOT_APPROVED",
  "next_gate": "HUMAN_REVIEW_3E_C1_SEMANTIC_CORRECTION_PACKET",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3E_C1_MANIFEST_MIGRATION_SEMANTIC_CORRECTION_READY\n'
printf 'CANDIDATE_ID=%s\n' "$EXPECTED_CANDIDATE_ID"
printf 'REVIEW_BUNDLE_ID=%s\n' "$EXPECTED_REVIEW_BUNDLE_ID"
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'PACKET_FILE_COUNT=%s\n' "$PACKET_FILE_COUNT"
printf 'PACKET_STATUS=SHADOW_ONLY_NOT_APPROVED_FOR_APPLICATION\n'
printf 'SOURCE_FILE_COUNT=17\n'
printf 'SOURCE_FILE_COUNT_MATCHES_LENGTH=true\n'
printf 'MANIFEST_SEMANTIC_VALIDATION=PASS\n'
printf 'MANIFEST_NEGATIVE_SELFTESTS=PASS\n'
printf 'MANIFEST_DRAFT_SHA=%s\n' "$MANIFEST_DRAFT_SHA"
printf 'MANIFEST_SPEC_SHA=%s\n' "$MANIFEST_SPEC_SHA"
printf 'MANIFEST_VALIDATOR_SHA=%s\n' "$MANIFEST_VALIDATOR_SHA"
printf 'MANIFEST_VALIDATION_SHA=%s\n' "$MANIFEST_VALIDATION_SHA"
printf 'MANIFEST_SELFTEST_RESULT_SHA=%s\n' "$SELFTEST_RESULT_SHA"
printf 'MIGRATION_INDEX_CONSTANT_NAME=INDEX_NAME\n'
printf 'MIGRATION_RESOLVED_INDEX_NAME=%s\n' "$RESOLVED_INDEX_NAME"
printf 'MIGRATION_SEMANTIC_VALIDATION=PASS\n'
printf 'MIGRATION_VALIDATOR_SHA=%s\n' "$MIGRATION_VALIDATOR_SHA"
printf 'MIGRATION_VALIDATION_SHA=%s\n' "$MIGRATION_VALIDATION_SHA"
printf 'MIGRATION_REHEARSAL_PLAN_SHA=%s\n' "$MIGRATION_REHEARSAL_PLAN_SHA"
printf 'SHADOW_PACKET_MANIFEST_SHA=%s\n' "$SHADOW_PACKET_MANIFEST_SHA"
printf 'EVIDENCE_PACKET_MANIFEST_SHA=%s\n' "$EVIDENCE_PACKET_MANIFEST_SHA"
printf 'SEMANTIC_CORRECTION_EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'EXISTING_3E_C_EVIDENCE_CHANGED=false\n'
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
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'SLACK_WORKER_STARTED=false\n'
printf 'PRODUCTION_RELEASE_APPROVED=false\n'
printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'NEXT_GATE=HUMAN_REVIEW_3E_C1_SEMANTIC_CORRECTION_PACKET\n'
printf 'SCRIPT_EXIT_CODE=0\n'
