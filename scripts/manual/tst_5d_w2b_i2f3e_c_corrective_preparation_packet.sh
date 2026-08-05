#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
PACKET_V1_ROOT_REL="${I2E_ROOT_REL}/i2f3e-b-production-release-preparation-packet-20260725T171412-499331"
PACKET_V1_SNAPSHOT_REL="${PACKET_V1_ROOT_REL}/packet-snapshot"
PREFLIGHT_ROOT_REL="${I2E_ROOT_REL}/i2f3e-a-production-release-preflight-inventory-20260725T170659-498762"
FINAL_REVIEW_ROOT_REL="${I2E_ROOT_REL}/i2f3d-c-slack-runtime-human-rereview-20260725T170114-498322"
SLACK_TEST_ROOT_REL="${I2E_ROOT_REL}/i2f3d-b-slack-hold-offline-tests-20260725T164615-497367"

PACKET_V1_RESULT="${REPO_ROOT}/${PACKET_V1_ROOT_REL}/result.json"
PACKET_V1_MANIFEST="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/preparation-packet-manifest.json"
PACKET_V1_EVIDENCE_MANIFEST="${REPO_ROOT}/${PACKET_V1_ROOT_REL}/preparation-packet-evidence-manifest.txt"
PACKET_V1_REBIND_PROPOSAL="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/production-manifest-rebind-proposal.json"
PACKET_V1_MIGRATION_PLAN="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/workflow-migration-preflight-plan.json"
PACKET_V1_DB_PLAN="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/production-db-readonly-preflight-plan.json"
PACKET_V1_DEPLOYMENT_PLAN="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/deployment-and-rollback-plan.json"
PACKET_V1_SLACK_PLAN="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/slack-worker-operation-plan.json"
PACKET_V1_TEST_ASSESSMENT="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/shadow-test-promotion-assessment.json"
PACKET_V1_GATE_CHECKLIST="${REPO_ROOT}/${PACKET_V1_SNAPSHOT_REL}/production-approval-gate-checklist.json"

PREFLIGHT_RESULT="${REPO_ROOT}/${PREFLIGHT_ROOT_REL}/result.json"
FINAL_DECISION_SET="${REPO_ROOT}/${FINAL_REVIEW_ROOT_REL}/final-human-review-decision-set.json"
SLACK_TEST_RESULT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/result.json"
SLACK_TEST_SNAPSHOT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/shadow-test-snapshot/test_slack_approval_socket_hold_remediation_offline.py"

EXPECTED_PACKET_V1_RESULT_SHA="eed9218323fa03fe1bb948ca42294e9fa313c47599e89d3714a5cc4700fd6de5"
EXPECTED_PACKET_V1_MANIFEST_SHA="b0f42af11fb53c664f601f3a0d292224fad6d29ea214a1d2818d267b062ae7fb"
EXPECTED_PACKET_V1_EVIDENCE_MANIFEST_SHA="af67c35919d7b52c96a1544602f300c56503c376941d252462a95c0eb37059c1"
EXPECTED_PACKET_V1_REBIND_PROPOSAL_SHA="c935a9b9b05ccb597dc1f9c67409940ef26b6fd31884965a84fdb96a46e97702"
EXPECTED_PACKET_V1_MIGRATION_PLAN_SHA="182c7f36006bf67b1937b2d9486e54e69a492d5c6d4fd2b04a50196eb419ab68"
EXPECTED_PACKET_V1_DB_PLAN_SHA="11d3d85906fceb8c616630bebbe394136264e5025990d4af849efd18c876387c"
EXPECTED_PACKET_V1_DEPLOYMENT_PLAN_SHA="853d99e9ea85058f8e09e24113e4111571665fe7ed67c01f3ec3d3c3162b1b27"
EXPECTED_PACKET_V1_SLACK_PLAN_SHA="23b8f36be2d8e0906cf43f7e4accc6e12d87fcd14d3f321a0c37f71ac4f064f2"
EXPECTED_PACKET_V1_TEST_ASSESSMENT_SHA="ed2f8e12655498d01298d5646d90cc6031125e3a223fc40cd988cdf5db45896c"
EXPECTED_PACKET_V1_GATE_CHECKLIST_SHA="8c878dcf6d9c8198c06de1e6e094212841670680dd90113dcc98582336f62811"

EXPECTED_PREFLIGHT_RESULT_SHA="31264f0f9e7a29143571c3b063264d61693d547505cea458ec8b1ca4ca0cbb7c"
EXPECTED_FINAL_DECISION_SET_SHA="9b28a2581535f6e2d12b811a61b7ff67777d4199f8db3edd3fda1f729e29ed30"
EXPECTED_SLACK_TEST_RESULT_SHA="732840292f5c551d589ea8e9459fc677c9df0380fb4ef1f18d5eafa2f1c33ce0"
EXPECTED_SLACK_TEST_SNAPSHOT_SHA="5f4bc6709120998383543f346e504c4ab2c408c0dfd7219d1ff3f8a236a83184"

R4_CANDIDATE_ROOT="/tmp/tst-5d-w2b-i2f3b-r4-candidate-20260725T153121-489639"
CANDIDATE_MANIFEST_SOURCE="${R4_CANDIDATE_ROOT}/candidate-manifest.json"
DEPENDENCY_CLOSURE_SOURCE="${R4_CANDIDATE_ROOT}/dependency-closure.json"
DOWNSTREAM_PLAN_SOURCE="${R4_CANDIDATE_ROOT}/downstream-rebinding-plan.json"

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

require_file_sha "$PACKET_V1_RESULT" "$EXPECTED_PACKET_V1_RESULT_SHA"
require_file_sha "$PACKET_V1_MANIFEST" "$EXPECTED_PACKET_V1_MANIFEST_SHA"
require_file_sha "$PACKET_V1_EVIDENCE_MANIFEST" "$EXPECTED_PACKET_V1_EVIDENCE_MANIFEST_SHA"
require_file_sha "$PACKET_V1_REBIND_PROPOSAL" "$EXPECTED_PACKET_V1_REBIND_PROPOSAL_SHA"
require_file_sha "$PACKET_V1_MIGRATION_PLAN" "$EXPECTED_PACKET_V1_MIGRATION_PLAN_SHA"
require_file_sha "$PACKET_V1_DB_PLAN" "$EXPECTED_PACKET_V1_DB_PLAN_SHA"
require_file_sha "$PACKET_V1_DEPLOYMENT_PLAN" "$EXPECTED_PACKET_V1_DEPLOYMENT_PLAN_SHA"
require_file_sha "$PACKET_V1_SLACK_PLAN" "$EXPECTED_PACKET_V1_SLACK_PLAN_SHA"
require_file_sha "$PACKET_V1_TEST_ASSESSMENT" "$EXPECTED_PACKET_V1_TEST_ASSESSMENT_SHA"
require_file_sha "$PACKET_V1_GATE_CHECKLIST" "$EXPECTED_PACKET_V1_GATE_CHECKLIST_SHA"

require_file_sha "$PREFLIGHT_RESULT" "$EXPECTED_PREFLIGHT_RESULT_SHA"
require_file_sha "$FINAL_DECISION_SET" "$EXPECTED_FINAL_DECISION_SET_SHA"
require_file_sha "$SLACK_TEST_RESULT" "$EXPECTED_SLACK_TEST_RESULT_SHA"
require_file_sha "$SLACK_TEST_SNAPSHOT" "$EXPECTED_SLACK_TEST_SNAPSHOT_SHA"

require_file_sha "$CANDIDATE_MANIFEST_SOURCE" "$EXPECTED_CANDIDATE_MANIFEST_SHA"
require_file_sha "$DEPENDENCY_CLOSURE_SOURCE" "$EXPECTED_DEPENDENCY_CLOSURE_SHA"
require_file_sha "$DOWNSTREAM_PLAN_SOURCE" "$EXPECTED_DOWNSTREAM_PLAN_SHA"

require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"
require_file_sha "$WORKFLOW_MIGRATION" "$EXPECTED_WORKFLOW_MIGRATION_SHA"
require_file_sha "$ACCESS_GUARD_SOURCE" "$EXPECTED_ACCESS_GUARD_SHA"
require_file_sha "$DB_CONFIG_SOURCE" "$EXPECTED_DB_CONFIG_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$DB_SESSION_SOURCE" "$EXPECTED_DB_SESSION_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3e-c-corrective-preparation-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3e-c-corrective-preparation-packet-${RUN_ID}"
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
    "$SHADOW_ROOT/pycache" \
    "$EVIDENCE_ROOT/candidate-input-snapshot" \
    "$EVIDENCE_ROOT/packet-snapshot"

CANDIDATE_SNAPSHOT="${EVIDENCE_ROOT}/candidate-input-snapshot/candidate-manifest.json"
CLOSURE_SNAPSHOT="${EVIDENCE_ROOT}/candidate-input-snapshot/dependency-closure.json"
DOWNSTREAM_SNAPSHOT="${EVIDENCE_ROOT}/candidate-input-snapshot/downstream-rebinding-plan.json"

cp --preserve=mode,timestamps "$CANDIDATE_MANIFEST_SOURCE" "$CANDIDATE_SNAPSHOT"
cp --preserve=mode,timestamps "$DEPENDENCY_CLOSURE_SOURCE" "$CLOSURE_SNAPSHOT"
cp --preserve=mode,timestamps "$DOWNSTREAM_PLAN_SOURCE" "$DOWNSTREAM_SNAPSHOT"
chmod 0444 "$CANDIDATE_SNAPSHOT" "$CLOSURE_SNAPSHOT" "$DOWNSTREAM_SNAPSHOT"

require_file_sha "$CANDIDATE_SNAPSHOT" "$EXPECTED_CANDIDATE_MANIFEST_SHA"
require_file_sha "$CLOSURE_SNAPSHOT" "$EXPECTED_DEPENDENCY_CLOSURE_SHA"
require_file_sha "$DOWNSTREAM_SNAPSHOT" "$EXPECTED_DOWNSTREAM_PLAN_SHA"

cat > "$SHADOW_ROOT/packet/human-approval-verbatim.txt" <<'TXT'
承認：
PACKET_REVIEW=APPROVE_WITH_CONDITIONS
APPROVE_3E_C_CORRECTIVE_PREPARATION_PACKET_SHADOW_ONLY

修正条件：
1. production manifestの旧SHA→新SHAを含む正確なshadow draftと
   semantic validatorを作成する。
2. /tmp依存のcandidate入力を不変evidence snapshotへ固定する。
3. DB preflight・backup・migration・manifest・production approval・
   network・worker起動の順序を安全順へ修正する。
4. SQLite backup方式とrestore rehearsalを具体化する。
5. migrationのtable・column・index・WHERE・upgrade・downgradeを
   semanticに検証するshadow rehearsal計画を作成する。
6. Slack offline testをrepository相対pathへ修正した最小差分案を作り、
   TEST_PROMOTIONをproduction release前の必須ゲートへ変更する。

禁止事項：
production manifest変更、production DB接続、SQL実行、
production migration適用、source/test変更、test昇格、deployment、
production approval作成、外部通信、Slack Worker起動、
production release承認は引き続き禁止する。
TXT

cat > "$SHADOW_ROOT/packet/validate_shadow_production_manifest.py" <<'PYVALIDATOR'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
HASH_KEYS = ("sha256", "source_sha256", "current_sha256", "file_sha256")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entry_path(entry: dict[str, Any]) -> str | None:
    value = entry.get("path")
    return value if isinstance(value, str) else None


def entry_sha(entry: dict[str, Any]) -> str:
    values = {entry[key] for key in HASH_KEYS if key in entry}
    if len(values) != 1:
        raise ValueError("SOURCE_ENTRY_SHA_AMBIGUOUS")
    value = next(iter(values))
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValueError("SOURCE_ENTRY_SHA_INVALID")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    production_path = Path(args.production).resolve()
    draft_path = Path(args.draft).resolve()
    spec_path = Path(args.spec).resolve()
    candidate_path = Path(args.candidate).resolve()
    repo = Path(args.repo).resolve()
    output_path = Path(args.output).resolve()

    production = load_json(production_path)
    draft = load_json(draft_path)
    spec = load_json(spec_path)
    candidate = load_json(candidate_path)

    if set(production) != set(draft):
        raise ValueError("TOP_LEVEL_SCHEMA_CHANGED")

    production_sources = production.get("source_files")
    draft_sources = draft.get("source_files")
    candidate_sources = candidate.get("source_files")
    if not all(
        isinstance(value, list)
        for value in (production_sources, draft_sources, candidate_sources)
    ):
        raise ValueError("SOURCE_FILES_LIST_REQUIRED")

    production_map = {
        entry_path(entry): entry
        for entry in production_sources
        if isinstance(entry, dict) and entry_path(entry)
    }
    draft_map = {
        entry_path(entry): entry
        for entry in draft_sources
        if isinstance(entry, dict) and entry_path(entry)
    }
    candidate_map = {
        entry_path(entry): entry
        for entry in candidate_sources
        if isinstance(entry, dict) and entry_path(entry)
    }

    operations = spec.get("operations")
    if not isinstance(operations, list):
        raise ValueError("OPERATIONS_LIST_REQUIRED")

    changed: list[str] = []
    added: list[str] = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("OPERATION_OBJECT_REQUIRED")
        source_path = operation["source_path"]
        old_sha = operation["old_sha256"]
        new_sha = operation["new_sha256"]

        if source_path not in draft_map:
            raise ValueError(f"DRAFT_SOURCE_MISSING:{source_path}")
        if source_path not in candidate_map:
            raise ValueError(f"CANDIDATE_SOURCE_MISSING:{source_path}")
        if entry_sha(draft_map[source_path]) != new_sha:
            raise ValueError(f"DRAFT_SHA_MISMATCH:{source_path}")
        if entry_sha(candidate_map[source_path]) != new_sha:
            raise ValueError(f"CANDIDATE_SHA_MISMATCH:{source_path}")
        if sha(repo / source_path) != new_sha:
            raise ValueError(f"REPOSITORY_SHA_MISMATCH:{source_path}")

        if operation["operation"] == "ADD_SOURCE_BINDING":
            if old_sha is not None:
                raise ValueError(f"ADD_OLD_SHA_MUST_BE_NULL:{source_path}")
            if source_path in production_map:
                raise ValueError(f"ADD_SOURCE_ALREADY_PRESENT:{source_path}")
            added.append(source_path)
        elif operation["operation"] == "REBIND_EXISTING_SOURCE":
            if source_path not in production_map:
                raise ValueError(f"REBIND_SOURCE_NOT_PRESENT:{source_path}")
            if entry_sha(production_map[source_path]) != old_sha:
                raise ValueError(f"OLD_SHA_MISMATCH:{source_path}")
            changed.append(source_path)
        else:
            raise ValueError(f"UNKNOWN_OPERATION:{source_path}")

    operation_paths = {item["source_path"] for item in operations}
    unchanged_paths: list[str] = []
    for source_path, production_entry in production_map.items():
        if source_path in operation_paths:
            continue
        if source_path not in draft_map:
            raise ValueError(f"UNRELATED_SOURCE_DELETED:{source_path}")
        if draft_map[source_path] != production_entry:
            raise ValueError(f"UNRELATED_SOURCE_CHANGED:{source_path}")
        unchanged_paths.append(source_path)

    deleted_paths = sorted(set(production_map) - set(draft_map))
    unexpected_added = sorted(
        set(draft_map) - set(production_map) - set(added)
    )
    if deleted_paths:
        raise ValueError(f"SOURCE_DELETION_DETECTED:{deleted_paths}")
    if unexpected_added:
        raise ValueError(f"UNEXPECTED_SOURCE_ADDITION:{unexpected_added}")

    report = {
        "schema_version": "1.0",
        "result": "PASS_SHADOW_PRODUCTION_MANIFEST_SEMANTIC_VALIDATION",
        "production_manifest_sha256": sha(production_path),
        "shadow_draft_sha256": sha(draft_path),
        "operation_spec_sha256": sha(spec_path),
        "candidate_snapshot_sha256": sha(candidate_path),
        "top_level_schema_preserved": True,
        "production_source_count": len(production_sources),
        "draft_source_count": len(draft_sources),
        "rebound_source_count": len(changed),
        "added_source_count": len(added),
        "unchanged_source_count": len(unchanged_paths),
        "deleted_source_count": 0,
        "unexpected_added_source_count": 0,
        "candidate_sha_match": True,
        "repository_sha_match": True,
        "production_manifest_modified": False,
        "application_allowed": False,
    }
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYVALIDATOR

python3 - \
    "$REPO_ROOT" \
    "$PACKET_V1_RESULT" \
    "$PACKET_V1_MANIFEST" \
    "$PREFLIGHT_RESULT" \
    "$FINAL_DECISION_SET" \
    "$SLACK_TEST_RESULT" \
    "$SLACK_TEST_SNAPSHOT" \
    "$CANDIDATE_SNAPSHOT" \
    "$CLOSURE_SNAPSHOT" \
    "$DOWNSTREAM_SNAPSHOT" \
    "$PRODUCTION_MANIFEST" \
    "$WORKFLOW_MIGRATION" \
    "$SHADOW_ROOT/packet" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PYGEN'
from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
import re
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo = Path(sys.argv[1]).resolve()
packet_v1_result_path = Path(sys.argv[2]).resolve()
packet_v1_manifest_path = Path(sys.argv[3]).resolve()
preflight_result_path = Path(sys.argv[4]).resolve()
final_decision_set_path = Path(sys.argv[5]).resolve()
slack_test_result_path = Path(sys.argv[6]).resolve()
slack_test_snapshot_path = Path(sys.argv[7]).resolve()
candidate_snapshot_path = Path(sys.argv[8]).resolve()
closure_snapshot_path = Path(sys.argv[9]).resolve()
downstream_snapshot_path = Path(sys.argv[10]).resolve()
production_manifest_path = Path(sys.argv[11]).resolve()
workflow_migration_path = Path(sys.argv[12]).resolve()
packet_root = Path(sys.argv[13]).resolve()
expected_candidate_id = sys.argv[14]
expected_review_bundle_id = sys.argv[15]

HASH_KEYS = ("sha256", "source_sha256", "current_sha256", "file_sha256")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


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


def ensure_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise SystemExit(f"INVALID_SHA256:{label}:{value!r}")
    return value


packet_v1_result = load_json(packet_v1_result_path)
packet_v1_manifest = load_json(packet_v1_manifest_path)
preflight_result = load_json(preflight_result_path)
final_decision_set = load_json(final_decision_set_path)
slack_test_result = load_json(slack_test_result_path)
candidate_manifest = load_json(candidate_snapshot_path)
dependency_closure = load_json(closure_snapshot_path)
downstream_plan = load_json(downstream_snapshot_path)
production_manifest = load_json(production_manifest_path)

if packet_v1_result.get("result") != (
    "PASS_W2B_I2F3E_B_PRODUCTION_RELEASE_PREPARATION_PACKET_READY"
):
    raise SystemExit("PACKET_V1_RESULT_INVALID")
if packet_v1_manifest.get("result") != (
    "PASS_PRODUCTION_RELEASE_PREPARATION_PACKET_READY"
):
    raise SystemExit("PACKET_V1_MANIFEST_INVALID")
if preflight_result.get("result") != (
    "PASS_W2B_I2F3E_A_PRODUCTION_RELEASE_PREFLIGHT_INVENTORY_READY"
):
    raise SystemExit("PREFLIGHT_RESULT_INVALID")
if final_decision_set.get("record_status") != (
    "ALL_REVIEW_UNITS_APPROVED_REVIEW_ONLY"
):
    raise SystemExit("FINAL_DECISION_SET_INVALID")
if slack_test_result.get("result") != (
    "PASS_W2B_I2F3D_B_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS"
):
    raise SystemExit("SLACK_TEST_RESULT_INVALID")
if candidate_manifest.get("candidate_id") != expected_candidate_id:
    raise SystemExit("CANDIDATE_MANIFEST_ID_MISMATCH")

known_sources = {
    "app/db/access_guard.py": "1584ac2975a39433fbf4670bbd2ea9974870866f6193cf8036f9528e72669583",
    "app/db/config.py": "5eeef8af4343d1e16412df40945f19667ee0f41dcbdea4a9f74386f12f7ddd59",
    "app/db/repositories/workflow_state_repository.py": "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "app/db/session.py": "0d6a0c2de0f5ab4691eae5d1dc311bf7d800461b7949d5ef1895fbc4b5b1d818",
    "scripts/run_slack_approval_socket.py": "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6",
}

production_sources = production_manifest.get("source_files")
candidate_sources = candidate_manifest.get("source_files")
if not isinstance(production_sources, list):
    raise SystemExit("PRODUCTION_SOURCE_FILES_INVALID")
if not isinstance(candidate_sources, list):
    raise SystemExit("CANDIDATE_SOURCE_FILES_INVALID")
if not all(isinstance(item, dict) for item in production_sources):
    raise SystemExit("PRODUCTION_SOURCE_ENTRY_INVALID")
if not all(isinstance(item, dict) for item in candidate_sources):
    raise SystemExit("CANDIDATE_SOURCE_ENTRY_INVALID")


def entry_path(entry: dict[str, Any]) -> str | None:
    value = entry.get("path")
    return value if isinstance(value, str) else None


def hash_keys(entry: dict[str, Any]) -> list[str]:
    return [key for key in HASH_KEYS if key in entry]


def primary_sha(entry: dict[str, Any], label: str) -> str:
    keys = hash_keys(entry)
    if not keys:
        raise SystemExit(f"SOURCE_ENTRY_HASH_KEY_MISSING:{label}")
    values = {ensure_sha(entry[key], f"{label}.{key}") for key in keys}
    if len(values) != 1:
        raise SystemExit(f"SOURCE_ENTRY_HASH_VALUES_CONFLICT:{label}")
    return next(iter(values))


original_production_by_path = {
    entry_path(entry): (index, entry)
    for index, entry in enumerate(production_sources)
    if entry_path(entry) is not None
}
candidate_by_path = {
    entry_path(entry): (index, entry)
    for index, entry in enumerate(candidate_sources)
    if entry_path(entry) is not None
}

for source_path, current_sha in known_sources.items():
    ensure_sha(current_sha, source_path)
    if source_path not in candidate_by_path:
        raise SystemExit(f"CANDIDATE_SOURCE_MISSING:{source_path}")
    if primary_sha(
        candidate_by_path[source_path][1],
        f"candidate:{source_path}",
    ) != current_sha:
        raise SystemExit(f"CANDIDATE_SOURCE_SHA_MISMATCH:{source_path}")
    if sha(repo / source_path) != current_sha:
        raise SystemExit(f"REPOSITORY_SOURCE_SHA_MISMATCH:{source_path}")

draft_manifest = copy.deepcopy(production_manifest)
draft_sources = draft_manifest["source_files"]

for source_path, new_sha in known_sources.items():
    if source_path not in original_production_by_path:
        continue
    original_index, original_entry = original_production_by_path[source_path]
    source_hash_keys = hash_keys(original_entry)
    if not source_hash_keys:
        raise SystemExit(f"PRODUCTION_HASH_KEY_MISSING:{source_path}")
    for key in source_hash_keys:
        draft_sources[original_index][key] = new_sha

schema_counter = Counter(
    tuple(sorted(str(key) for key in entry.keys()))
    for entry in production_sources
)
if not schema_counter:
    raise SystemExit("PRODUCTION_SOURCE_SCHEMA_EMPTY")
dominant_schema = set(schema_counter.most_common(1)[0][0])

for source_path, new_sha in known_sources.items():
    if source_path in original_production_by_path:
        continue

    candidate_index, candidate_entry = candidate_by_path[source_path]
    source_hash_keys = [key for key in HASH_KEYS if key in dominant_schema]
    if not source_hash_keys:
        source_hash_keys = hash_keys(candidate_entry)
    if not source_hash_keys:
        raise SystemExit("ADD_SOURCE_HASH_SCHEMA_UNRESOLVED")

    new_entry: dict[str, Any] = {}
    for key in sorted(dominant_schema):
        if key == "path":
            new_entry[key] = source_path
        elif key in HASH_KEYS:
            new_entry[key] = new_sha
        elif key == "size":
            new_entry[key] = (repo / source_path).stat().st_size
        elif key == "mode":
            candidate_value = candidate_entry.get("mode")
            if candidate_value is None:
                candidate_value = stat.S_IMODE(
                    (repo / source_path).stat().st_mode
                )
            new_entry[key] = candidate_value
        elif key in candidate_entry:
            new_entry[key] = copy.deepcopy(candidate_entry[key])
        else:
            raise SystemExit(
                f"ADD_SOURCE_SCHEMA_VALUE_UNRESOLVED:{source_path}:{key}"
            )

    if "path" not in new_entry:
        new_entry["path"] = source_path
    for key in source_hash_keys:
        new_entry[key] = new_sha

    current_draft_by_path = {
        entry_path(entry): index
        for index, entry in enumerate(draft_sources)
        if entry_path(entry) is not None
    }
    insertion_index: int | None = None
    for later_entry in candidate_sources[candidate_index + 1 :]:
        later_path = entry_path(later_entry)
        if later_path in current_draft_by_path:
            insertion_index = current_draft_by_path[later_path]
            break
    if insertion_index is None:
        for earlier_entry in reversed(candidate_sources[:candidate_index]):
            earlier_path = entry_path(earlier_entry)
            if earlier_path in current_draft_by_path:
                insertion_index = current_draft_by_path[earlier_path] + 1
                break
    if insertion_index is None:
        insertion_index = 0
    draft_sources.insert(insertion_index, new_entry)

draft_by_path = {
    entry_path(entry): (index, entry)
    for index, entry in enumerate(draft_sources)
    if entry_path(entry) is not None
}

operations: list[dict[str, Any]] = []
for source_path, new_sha in known_sources.items():
    candidate_index = candidate_by_path[source_path][0]
    draft_index = draft_by_path[source_path][0]
    if source_path in original_production_by_path:
        original_index, original_entry = original_production_by_path[source_path]
        old_sha = primary_sha(original_entry, f"production:{source_path}")
        operation = "REBIND_EXISTING_SOURCE"
        production_pointer: str | None = f"$.source_files[{original_index}]"
    else:
        old_sha = None
        operation = "ADD_SOURCE_BINDING"
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
            "rollback_sha256": old_sha,
            "human_review_required": True,
            "application_allowed": False,
        }
    )

draft_path = packet_root / "shadow-production-manifest-draft.json"
write_json(draft_path, draft_manifest)

production_pretty = (
    json.dumps(production_manifest, ensure_ascii=False, sort_keys=True, indent=2)
    + "\n"
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
(packet_root / "shadow-production-manifest-draft.diff").write_text(
    diff_text,
    encoding="utf-8",
)

write_json(
    packet_root / "production-manifest-corrective-rebind-spec.json",
    {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-C",
        "status": "SHADOW_DRAFT_ONLY_NOT_APPROVED_FOR_APPLICATION",
        "candidate_id": expected_candidate_id,
        "review_bundle_id": expected_review_bundle_id,
        "production_manifest": {
            "path": str(production_manifest_path.relative_to(repo)),
            "sha256": sha(production_manifest_path),
            "modified": False,
        },
        "candidate_input_snapshot": {
            "candidate_manifest_path": str(candidate_snapshot_path),
            "candidate_manifest_sha256": sha(candidate_snapshot_path),
            "dependency_closure_path": str(closure_snapshot_path),
            "dependency_closure_sha256": sha(closure_snapshot_path),
            "downstream_plan_path": str(downstream_snapshot_path),
            "downstream_plan_sha256": sha(downstream_snapshot_path),
            "uses_tmp_input_after_snapshot": False,
        },
        "shadow_draft": {
            "path": draft_path.name,
            "sha256": sha(draft_path),
            "production_schema_preserved": (
                set(draft_manifest) == set(production_manifest)
            ),
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

migration_text = workflow_migration_path.read_text(encoding="utf-8")
migration_tree = ast.parse(migration_text)


def get_function(name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in migration_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise SystemExit(f"MIGRATION_FUNCTION_COUNT_INVALID:{name}")
    return matches[0]


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{qualified_name(node.value)}.{node.attr}"
    return ""


def literal_or_text(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        pass
    if (
        isinstance(node, ast.Call)
        and qualified_name(node.func) in {"sa.text", "sqlalchemy.text"}
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return ast.unparse(node)


def calls_in(function: ast.FunctionDef, name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and qualified_name(node.func) == name
    ]


upgrade_node = get_function("upgrade")
downgrade_node = get_function("downgrade")
create_calls = calls_in(upgrade_node, "op.create_index")
drop_calls = calls_in(downgrade_node, "op.drop_index")
if len(create_calls) != 1:
    raise SystemExit(f"CREATE_INDEX_CALL_COUNT_INVALID:{len(create_calls)}")
if len(drop_calls) != 1:
    raise SystemExit(f"DROP_INDEX_CALL_COUNT_INVALID:{len(drop_calls)}")

create_call = create_calls[0]
drop_call = drop_calls[0]
if len(create_call.args) < 3:
    raise SystemExit("CREATE_INDEX_POSITIONAL_ARGS_INCOMPLETE")

index_name = literal_or_text(create_call.args[0])
table_name = literal_or_text(create_call.args[1])
columns = literal_or_text(create_call.args[2])
create_keywords = {
    keyword.arg: literal_or_text(keyword.value)
    for keyword in create_call.keywords
    if keyword.arg is not None
}
drop_keywords = {
    keyword.arg: literal_or_text(keyword.value)
    for keyword in drop_call.keywords
    if keyword.arg is not None
}
drop_index_name = (
    literal_or_text(drop_call.args[0])
    if drop_call.args
    else drop_keywords.get("index_name")
)
drop_table_name = (
    literal_or_text(drop_call.args[1])
    if len(drop_call.args) > 1
    else drop_keywords.get("table_name")
)
unique_value = create_keywords.get("unique")
sqlite_where = create_keywords.get("sqlite_where")
if sqlite_where is None:
    sqlite_where = create_keywords.get("postgresql_where")

if not isinstance(index_name, str) or not index_name:
    raise SystemExit("INDEX_NAME_INVALID")
if not isinstance(table_name, str) or not table_name:
    raise SystemExit("TABLE_NAME_INVALID")
if columns != ["wordpress_post_id"]:
    raise SystemExit(f"INDEX_COLUMNS_INVALID:{columns!r}")
if unique_value is not True:
    raise SystemExit(f"UNIQUE_FLAG_INVALID:{unique_value!r}")
if not isinstance(sqlite_where, str):
    raise SystemExit("SQLITE_WHERE_INVALID")
normalized_where = " ".join(sqlite_where.split()).upper()
if normalized_where != "WORDPRESS_POST_ID IS NOT NULL":
    raise SystemExit(f"SQLITE_WHERE_SEMANTICS_INVALID:{sqlite_where}")
if drop_index_name != index_name:
    raise SystemExit("DROP_INDEX_NAME_MISMATCH")
if drop_table_name not in (None, table_name):
    raise SystemExit("DROP_INDEX_TABLE_MISMATCH")

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

migration_semantics = {
    "schema_version": "1.0",
    "result": "PASS_MIGRATION_STATIC_SEMANTIC_VALIDATION",
    "migration_path": str(workflow_migration_path.relative_to(repo)),
    "migration_sha256": sha(workflow_migration_path),
    "revision": revision_match.group(1) if revision_match else None,
    "down_revision": (
        down_revision_match.group(1) if down_revision_match else None
    ),
    "upgrade": {
        "create_index_call_count": 1,
        "index_name": index_name,
        "table_name": table_name,
        "columns": columns,
        "unique": unique_value,
        "sqlite_where": sqlite_where,
        "normalized_where": normalized_where,
    },
    "downgrade": {
        "drop_index_call_count": 1,
        "index_name": drop_index_name,
        "table_name": drop_table_name,
        "matches_upgrade_index": True,
    },
    "static_validation_only": True,
    "sql_executed": False,
    "migration_applied": False,
}
write_json(
    packet_root / "migration-static-semantic-validation.json",
    migration_semantics,
)

write_json(
    packet_root / "migration-shadow-rehearsal-plan.json",
    {
        "schema_version": "1.0",
        "status": "SHADOW_REHEARSAL_PLAN_ONLY_NOT_EXECUTED",
        "validated_migration_semantics": migration_semantics,
        "shadow_rehearsal_sequence": [
            "Create a unique temporary SQLite rehearsal database from an approved schema baseline or verified backup clone.",
            "Confirm its Alembic revision exactly equals the migration down_revision.",
            "Seed at least two NULL wordpress_post_id rows and distinct non-NULL values.",
            "Apply only revision 00241611109d to the temporary rehearsal database.",
            f"Verify sqlite_master contains unique index {index_name!r} on table {table_name!r}.",
            "Verify the predicate is semantically wordpress_post_id IS NOT NULL.",
            "Verify multiple NULL values remain allowed.",
            "Verify duplicate non-NULL wordpress_post_id insertion is rejected.",
            "Run integrity_check and foreign_key_check on the rehearsal database.",
            "Downgrade exactly one revision.",
            f"Verify index {index_name!r} is removed by downgrade.",
            "Restore a fresh clone and re-apply the revision to confirm repeatability.",
            "Preserve every log, schema dump, SHA value, and exit code.",
        ],
        "required_outputs": [
            "rehearsal-db-sha-before.txt",
            "rehearsal-db-sha-after-upgrade.txt",
            "rehearsal-db-sha-after-downgrade.txt",
            "alembic-revision-before.txt",
            "alembic-revision-after-upgrade.txt",
            "alembic-revision-after-downgrade.txt",
            "sqlite-master-index-before.txt",
            "sqlite-master-index-after-upgrade.txt",
            "sqlite-master-index-after-downgrade.txt",
            "null-uniqueness-test.txt",
            "non-null-duplicate-rejection-test.txt",
            "integrity-check.txt",
            "foreign-key-check.txt",
            "rehearsal-result.json",
        ],
        "production_database_opened": False,
        "sql_executed": False,
        "migration_applied": False,
    },
)

write_json(
    packet_root / "sqlite-backup-and-restore-rehearsal-plan.json",
    {
        "schema_version": "1.0",
        "status": "PLAN_ONLY_NOT_EXECUTED",
        "primary_backup_method": "PYTHON_SQLITE3_CONNECTION_BACKUP_API",
        "source_access_mode": (
            "file:/home/deploy/ai_media_os/data/database/"
            "ebook_affiliate.db?mode=ro"
        ),
        "required_writer_state": "FROZEN_AND_VERIFIED",
        "wal_controls": [
            "Record whether ebook_affiliate.db-wal and ebook_affiliate.db-shm exist before backup.",
            "Do not copy only the main DB file while a live WAL may contain committed pages.",
            "Use sqlite3.Connection.backup from a read-only source connection to a unique destination after writer freeze.",
            "Do not enable or change journal_mode during backup preparation.",
        ],
        "planned_backup_sequence": [
            "Obtain separate production DB read-only preflight and backup approval.",
            "Stop and verify all application, GUI writer, scheduler, and Slack Worker processes.",
            "Record source DB, WAL, and SHM inventory without opening SQLite.",
            "Record source DB SHA-256 before opening.",
            "Open source with SQLite URI mode=ro and a unique new destination.",
            "Run sqlite3.Connection.backup with progress logging.",
            "Close connections and fsync destination file and directory.",
            "Record destination backup SHA-256 and size.",
            "Re-hash source DB and require equality with its pre-open SHA.",
        ],
        "planned_restore_rehearsal": [
            "Copy the verified backup to a unique temporary restore path.",
            "Open only the temporary restored copy.",
            "Run integrity_check and foreign_key_check.",
            "Record Alembic revision, tables, and indexes.",
            "Run approved upgrade and downgrade only on the restored copy.",
            "Retain restored-copy SHA values before and after every stage.",
            "Reject production migration eligibility on any restore or downgrade failure.",
        ],
        "prohibited_methods": [
            "Plain cp of a live main DB without WAL handling.",
            "In-place rehearsal on the production DB.",
            "Tests pointed at the production DB path.",
            "Overwrite of an existing backup.",
        ],
        "production_database_opened": False,
        "sql_executed": False,
        "backup_created": False,
        "restore_rehearsal_performed": False,
    },
)

safe_order = [
    {"order": 1, "gate": "PACKET_CORRECTIVE_REVIEW", "required": True, "currently_approved": False},
    {"order": 2, "gate": "TEST_PROMOTION_APPROVAL", "required": True, "currently_approved": False},
    {"order": 3, "gate": "TEST_PROMOTION_AND_PROMOTED_TEST_PASS", "required": True, "currently_approved": False},
    {"order": 4, "gate": "PRODUCTION_DB_PREFLIGHT_AND_BACKUP_PREPARATION_APPROVAL", "required": True, "currently_approved": False},
    {"order": 5, "gate": "WRITER_FREEZE", "required": True, "currently_approved": False},
    {"order": 6, "gate": "FINAL_SHA_AND_READONLY_DB_PREFLIGHT", "required": True, "currently_approved": False},
    {"order": 7, "gate": "CONSISTENT_SQLITE_BACKUP", "required": True, "currently_approved": False},
    {"order": 8, "gate": "BACKUP_RESTORE_AND_MIGRATION_REHEARSAL", "required": True, "currently_approved": False},
    {"order": 9, "gate": "PRODUCTION_MIGRATION_APPROVAL", "required": True, "currently_approved": False},
    {"order": 10, "gate": "PRODUCTION_MIGRATION_AND_POSTCHECK", "required": True, "currently_approved": False},
    {"order": 11, "gate": "PRODUCTION_MANIFEST_REBIND_APPROVAL", "required": True, "currently_approved": False},
    {"order": 12, "gate": "PRODUCTION_MANIFEST_REBIND_AND_OFFLINE_SMOKE", "required": True, "currently_approved": False},
    {"order": 13, "gate": "PRODUCTION_APPROVAL", "required": True, "currently_approved": False},
    {"order": 14, "gate": "EXTERNAL_NETWORK_APPROVAL", "required": True, "currently_approved": False},
    {"order": 15, "gate": "SLACK_WORKER_START_APPROVAL", "required": True, "currently_approved": False},
]

write_json(
    packet_root / "corrected-production-release-order.json",
    {
        "schema_version": "1.0",
        "status": "CORRECTED_SAFE_ORDER_PLAN_ONLY",
        "ordered_gates": safe_order,
        "invariants": [
            "Production approval precedes external network approval.",
            "Production approval precedes Slack Worker start approval.",
            "Production migration and postchecks precede production manifest rebinding.",
            "Consistent backup and restore rehearsal precede production migration approval.",
            "Repository test promotion and promoted-test PASS are mandatory before release.",
            "Every gate requires a distinct explicit approval and immutable evidence.",
        ],
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "execution_performed": False,
    },
)

shadow_test_text = slack_test_snapshot_path.read_text(encoding="utf-8")
absolute_line = 'REPO_ROOT = Path("/home/deploy/ai_media_os")'
relative_line = 'REPO_ROOT = Path(__file__).resolve().parents[1]'
if shadow_test_text.count(absolute_line) != 1:
    raise SystemExit("SHADOW_TEST_ABSOLUTE_PATH_COUNT_INVALID")

candidate_test_text = shadow_test_text.replace(
    absolute_line,
    relative_line,
    1,
)
if "/home/deploy/ai_media_os" in candidate_test_text:
    raise SystemExit("ABSOLUTE_REPOSITORY_PATH_REMAINS")

candidate_test_path = (
    packet_root
    / "test_slack_approval_socket_hold_remediation_offline.candidate.py"
)
candidate_test_path.write_text(candidate_test_text, encoding="utf-8")

test_diff = "".join(
    difflib.unified_diff(
        shadow_test_text.splitlines(keepends=True),
        candidate_test_text.splitlines(keepends=True),
        fromfile="a/evidence/test_slack_approval_socket_hold_remediation_offline.py",
        tofile="b/tests/test_slack_approval_socket_hold_remediation_offline.py",
        n=5,
    )
)
(packet_root / "shadow-test-promotion-minimal.diff").write_text(
    test_diff,
    encoding="utf-8",
)

test_tree = ast.parse(candidate_test_text)
test_names = [
    node.name
    for node in test_tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name.startswith("test_")
]
if len(test_names) != 4:
    raise SystemExit(f"PROMOTED_TEST_COUNT_INVALID:{len(test_names)}")

write_json(
    packet_root / "corrected-shadow-test-promotion-assessment.json",
    {
        "schema_version": "1.0",
        "status": "TEST_ONLY_CANDIDATE_NOT_PROMOTED",
        "source_shadow_test": {
            "path": str(slack_test_snapshot_path.relative_to(repo)),
            "sha256": sha(slack_test_snapshot_path),
        },
        "candidate_test": {
            "shadow_path": candidate_test_path.name,
            "sha256": sha(candidate_test_path),
            "repository_target": (
                "tests/"
                "test_slack_approval_socket_hold_remediation_offline.py"
            ),
            "repository_relative_root_resolution": relative_line,
            "absolute_repository_path_remaining": False,
            "test_count": len(test_names),
            "test_names": test_names,
        },
        "minimal_change": {
            "operation": "ADD_FILE_ONLY",
            "changed_existing_repository_file_count": 0,
            "runtime_source_change_required": False,
            "production_manifest_change_required": False,
        },
        "release_gate": {
            "gate": "TEST_PROMOTION",
            "required_before_release": True,
            "status": "NOT_APPROVED",
        },
        "promotion_performed": False,
        "repository_test_created": False,
        "pytest_executed": False,
    },
)

write_json(
    packet_root / "corrected-production-approval-gate-checklist.json",
    {
        "schema_version": "1.0",
        "status": "CORRECTIVE_PREPARATION_PACKET_READY_RELEASE_NOT_APPROVED",
        "candidate_id": expected_candidate_id,
        "review_bundle_id": expected_review_bundle_id,
        "production_release_gates": safe_order,
        "required_gate_count": len(safe_order),
        "test_promotion_required_before_release": True,
        "candidate_inputs_snapshot_in_evidence": True,
        "production_release_ready": False,
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "next_gate": "HUMAN_REVIEW_3E_C_CORRECTIVE_PREPARATION_PACKET",
    },
)

readme = (
    "# 3E-C Corrective Production Release Preparation Packet\n\n"
    "Status: SHADOW / EVIDENCE ONLY — NOT APPROVED FOR APPLICATION\n\n"
    "Corrections implemented:\n"
    "1. Exact old-SHA to new-SHA operations and schema-preserving shadow draft.\n"
    "2. Candidate inputs fixed to immutable evidence snapshots before use.\n"
    "3. Corrected release order through production approval, network, and worker start.\n"
    "4. Concrete SQLite backup API and restore rehearsal plan.\n"
    "5. Static migration semantics and shadow rehearsal plan.\n"
    "6. Repository-relative Slack test candidate and mandatory promotion gate.\n\n"
    "No production manifest, database, migration, source, test, deployment,\n"
    "approval, network, or worker-start action is performed.\n"
)
(packet_root / "README.md").write_text(readme, encoding="utf-8")
PYGEN

VALIDATOR="${SHADOW_ROOT}/packet/validate_shadow_production_manifest.py"
MANIFEST_VALIDATION="${SHADOW_ROOT}/packet/shadow-production-manifest-semantic-validation.json"

python3 "$VALIDATOR" \
    --production "$PRODUCTION_MANIFEST" \
    --draft "$SHADOW_ROOT/packet/shadow-production-manifest-draft.json" \
    --spec "$SHADOW_ROOT/packet/production-manifest-corrective-rebind-spec.json" \
    --candidate "$CANDIDATE_SNAPSHOT" \
    --repo "$REPO_ROOT" \
    --output "$MANIFEST_VALIDATION"

python3 -m json.tool "$MANIFEST_VALIDATION" >/dev/null

MANIFEST_VALIDATION_RESULT="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["result"])' \
        "$MANIFEST_VALIDATION"
)"
if [[ "$MANIFEST_VALIDATION_RESULT" != \
    "PASS_SHADOW_PRODUCTION_MANIFEST_SEMANTIC_VALIDATION" ]]; then
    printf 'ERROR=MANIFEST_SEMANTIC_VALIDATION_FAILED\n' >&2
    exit 1
fi

PYTHONPYCACHEPREFIX="$SHADOW_ROOT/pycache" \
    python3 -m py_compile "$VALIDATOR"
PYTHONPYCACHEPREFIX="$SHADOW_ROOT/pycache" \
    python3 -m py_compile \
    "$SHADOW_ROOT/packet/test_slack_approval_socket_hold_remediation_offline.candidate.py"

python3 - \
    "$SHADOW_ROOT/packet" \
    "$CANDIDATE_SNAPSHOT" \
    "$CLOSURE_SNAPSHOT" \
    "$DOWNSTREAM_SNAPSHOT" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PYMANIFEST'
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
    and path.name != "corrective-preparation-packet-manifest.json"
)

write_json(
    packet_root / "corrective-preparation-packet-manifest.json",
    {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-C",
        "result": "PASS_3E_C_CORRECTIVE_PREPARATION_PACKET_GENERATED",
        "status": "SHADOW_ONLY_NOT_APPROVED_FOR_APPLICATION",
        "candidate_id": candidate_id,
        "review_bundle_id": review_bundle_id,
        "corrections": {
            "exact_manifest_old_to_new_operations": True,
            "schema_preserving_shadow_manifest_draft": True,
            "manifest_semantic_validator_created": True,
            "manifest_semantic_validation_passed": True,
            "candidate_tmp_inputs_snapshotted_to_evidence": True,
            "safe_release_order_corrected": True,
            "sqlite_backup_and_restore_rehearsal_specified": True,
            "migration_static_semantics_validated": True,
            "migration_shadow_rehearsal_planned": True,
            "slack_test_repository_relative_candidate_created": True,
            "test_promotion_required_before_release": True,
        },
        "input_snapshots": {
            "candidate_manifest_sha256": sha(candidate_path),
            "dependency_closure_sha256": sha(closure_path),
            "downstream_plan_sha256": sha(downstream_path),
            "uses_tmp_input_after_snapshot": False,
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
        "next_gate": "HUMAN_REVIEW_3E_C_CORRECTIVE_PREPARATION_PACKET",
    },
)
PYMANIFEST

find "$SHADOW_ROOT/packet" -type f -exec chmod 0444 {} +
cp -a "$SHADOW_ROOT/packet/." "$EVIDENCE_ROOT/packet-snapshot/"
find "$EVIDENCE_ROOT/packet-snapshot" -type f -exec chmod 0444 {} +

SHADOW_PACKET_MANIFEST="${SHADOW_ROOT}/packet/corrective-preparation-packet-manifest.json"
EVIDENCE_PACKET_MANIFEST="${EVIDENCE_ROOT}/packet-snapshot/corrective-preparation-packet-manifest.json"
SHADOW_PACKET_MANIFEST_SHA="$(sha256_file "$SHADOW_PACKET_MANIFEST")"
EVIDENCE_PACKET_MANIFEST_SHA="$(sha256_file "$EVIDENCE_PACKET_MANIFEST")"

if [[ "$SHADOW_PACKET_MANIFEST_SHA" != "$EVIDENCE_PACKET_MANIFEST_SHA" ]]; then
    printf 'ERROR=PACKET_MANIFEST_SNAPSHOT_SHA_MISMATCH\n' >&2
    exit 1
fi

SHADOW_MANIFEST_DRAFT="${SHADOW_ROOT}/packet/shadow-production-manifest-draft.json"
SHADOW_MANIFEST_DRAFT_SHA="$(sha256_file "$SHADOW_MANIFEST_DRAFT")"
MANIFEST_VALIDATOR_SHA="$(sha256_file "$VALIDATOR")"
MANIFEST_VALIDATION_SHA="$(sha256_file "$MANIFEST_VALIDATION")"
MIGRATION_SEMANTIC_SHA="$(sha256_file "$SHADOW_ROOT/packet/migration-static-semantic-validation.json")"
MIGRATION_REHEARSAL_PLAN_SHA="$(sha256_file "$SHADOW_ROOT/packet/migration-shadow-rehearsal-plan.json")"
BACKUP_RESTORE_PLAN_SHA="$(sha256_file "$SHADOW_ROOT/packet/sqlite-backup-and-restore-rehearsal-plan.json")"
SAFE_ORDER_SHA="$(sha256_file "$SHADOW_ROOT/packet/corrected-production-release-order.json")"
TEST_CANDIDATE_SHA="$(sha256_file "$SHADOW_ROOT/packet/test_slack_approval_socket_hold_remediation_offline.candidate.py")"
TEST_PROMOTION_DIFF_SHA="$(sha256_file "$SHADOW_ROOT/packet/shadow-test-promotion-minimal.diff")"
GATE_CHECKLIST_SHA="$(sha256_file "$SHADOW_ROOT/packet/corrected-production-approval-gate-checklist.json")"
PACKET_FILE_COUNT="$(find "$SHADOW_ROOT/packet" -maxdepth 1 -type f | wc -l)"

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/corrective-preparation-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'corrective-preparation-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"
chmod 0444 "$EVIDENCE_MANIFEST"
EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"

[[ "$(sha256_file "$PACKET_V1_RESULT")" == "$EXPECTED_PACKET_V1_RESULT_SHA" ]] || exit 1
[[ "$(sha256_file "$PREFLIGHT_RESULT")" == "$EXPECTED_PREFLIGHT_RESULT_SHA" ]] || exit 1
[[ "$(sha256_file "$FINAL_DECISION_SET")" == "$EXPECTED_FINAL_DECISION_SET_SHA" ]] || exit 1
[[ "$(sha256_file "$PRODUCTION_MANIFEST")" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || exit 1
[[ "$(sha256_file "$DB_PATH")" == "$EXPECTED_DB_SHA" ]] || exit 1
[[ "$(sha256_file "$WORKFLOW_MIGRATION")" == "$EXPECTED_WORKFLOW_MIGRATION_SHA" ]] || exit 1
[[ "$(sha256_file "$ACCESS_GUARD_SOURCE")" == "$EXPECTED_ACCESS_GUARD_SHA" ]] || exit 1
[[ "$(sha256_file "$DB_CONFIG_SOURCE")" == "$EXPECTED_DB_CONFIG_SHA" ]] || exit 1
[[ "$(sha256_file "$WORKFLOW_SOURCE")" == "$EXPECTED_WORKFLOW_SOURCE_SHA" ]] || exit 1
[[ "$(sha256_file "$DB_SESSION_SOURCE")" == "$EXPECTED_DB_SESSION_SHA" ]] || exit 1
[[ "$(sha256_file "$SLACK_SOURCE")" == "$EXPECTED_SLACK_SOURCE_SHA" ]] || exit 1
[[ "$(sha256_file "$SLACK_TEST_SNAPSHOT")" == "$EXPECTED_SLACK_TEST_SNAPSHOT_SHA" ]] || exit 1

RESULT_JSON="${EVIDENCE_ROOT}/result.json"

cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3E-C",
  "result": "PASS_W2B_I2F3E_C_CORRECTIVE_PREPARATION_PACKET_READY",
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
  "corrections": {
    "exact_old_to_new_manifest_operations": true,
    "schema_preserving_shadow_manifest_draft": true,
    "manifest_semantic_validation_passed": true,
    "candidate_inputs_snapshotted_to_immutable_evidence": true,
    "tmp_input_used_after_snapshot": false,
    "safe_release_order_corrected": true,
    "sqlite_backup_and_restore_rehearsal_defined": true,
    "migration_static_semantics_validated": true,
    "migration_shadow_rehearsal_plan_created": true,
    "repository_relative_test_candidate_created": true,
    "test_promotion_required_before_release": true
  },
  "artifacts": {
    "shadow_manifest_draft_sha256": "${SHADOW_MANIFEST_DRAFT_SHA}",
    "manifest_validator_sha256": "${MANIFEST_VALIDATOR_SHA}",
    "manifest_semantic_validation_sha256": "${MANIFEST_VALIDATION_SHA}",
    "migration_static_semantic_validation_sha256": "${MIGRATION_SEMANTIC_SHA}",
    "migration_shadow_rehearsal_plan_sha256": "${MIGRATION_REHEARSAL_PLAN_SHA}",
    "sqlite_backup_restore_plan_sha256": "${BACKUP_RESTORE_PLAN_SHA}",
    "corrected_safe_order_sha256": "${SAFE_ORDER_SHA}",
    "repository_relative_test_candidate_sha256": "${TEST_CANDIDATE_SHA}",
    "test_promotion_minimal_diff_sha256": "${TEST_PROMOTION_DIFF_SHA}",
    "corrected_gate_checklist_sha256": "${GATE_CHECKLIST_SHA}"
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
  "production_release_decision": "HOLD",
  "release_status": "CANDIDATE_NOT_APPROVED",
  "next_gate": "HUMAN_REVIEW_3E_C_CORRECTIVE_PREPARATION_PACKET",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3E_C_CORRECTIVE_PREPARATION_PACKET_READY\n'
printf 'CANDIDATE_ID=%s\n' "$EXPECTED_CANDIDATE_ID"
printf 'REVIEW_BUNDLE_ID=%s\n' "$EXPECTED_REVIEW_BUNDLE_ID"
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'PACKET_FILE_COUNT=%s\n' "$PACKET_FILE_COUNT"
printf 'PACKET_STATUS=SHADOW_ONLY_NOT_APPROVED_FOR_APPLICATION\n'
printf 'CANDIDATE_INPUT_SNAPSHOT_CREATED=true\n'
printf 'TMP_INPUT_USED_AFTER_SNAPSHOT=false\n'
printf 'SHADOW_MANIFEST_DRAFT_CREATED=true\n'
printf 'SHADOW_MANIFEST_DRAFT_SHA=%s\n' "$SHADOW_MANIFEST_DRAFT_SHA"
printf 'MANIFEST_SEMANTIC_VALIDATOR_CREATED=true\n'
printf 'MANIFEST_SEMANTIC_VALIDATION=PASS\n'
printf 'MANIFEST_VALIDATOR_SHA=%s\n' "$MANIFEST_VALIDATOR_SHA"
printf 'MANIFEST_VALIDATION_SHA=%s\n' "$MANIFEST_VALIDATION_SHA"
printf 'MIGRATION_STATIC_SEMANTIC_VALIDATION=PASS\n'
printf 'MIGRATION_SEMANTIC_SHA=%s\n' "$MIGRATION_SEMANTIC_SHA"
printf 'MIGRATION_SHADOW_REHEARSAL_PLAN_CREATED=true\n'
printf 'MIGRATION_REHEARSAL_PLAN_SHA=%s\n' "$MIGRATION_REHEARSAL_PLAN_SHA"
printf 'SQLITE_BACKUP_RESTORE_PLAN_CREATED=true\n'
printf 'BACKUP_RESTORE_PLAN_SHA=%s\n' "$BACKUP_RESTORE_PLAN_SHA"
printf 'SAFE_RELEASE_ORDER_CORRECTED=true\n'
printf 'SAFE_ORDER_SHA=%s\n' "$SAFE_ORDER_SHA"
printf 'REPOSITORY_RELATIVE_TEST_CANDIDATE_CREATED=true\n'
printf 'TEST_CANDIDATE_SHA=%s\n' "$TEST_CANDIDATE_SHA"
printf 'TEST_PROMOTION_MINIMAL_DIFF_SHA=%s\n' "$TEST_PROMOTION_DIFF_SHA"
printf 'TEST_PROMOTION_REQUIRED_BEFORE_RELEASE=true\n'
printf 'CORRECTED_GATE_CHECKLIST_SHA=%s\n' "$GATE_CHECKLIST_SHA"
printf 'SHADOW_PACKET_MANIFEST_SHA=%s\n' "$SHADOW_PACKET_MANIFEST_SHA"
printf 'EVIDENCE_PACKET_MANIFEST_SHA=%s\n' "$EVIDENCE_PACKET_MANIFEST_SHA"
printf 'CORRECTIVE_EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
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
printf 'NEXT_GATE=HUMAN_REVIEW_3E_C_CORRECTIVE_PREPARATION_PACKET\n'
printf 'SCRIPT_EXIT_CODE=0\n'
