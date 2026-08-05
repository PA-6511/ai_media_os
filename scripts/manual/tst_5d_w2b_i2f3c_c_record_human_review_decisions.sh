#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
C_B_ROOT_REL="${I2E_ROOT_REL}/i2f3c-b-review-bundle-validation-20260725T160528-494244"

C_B_RESULT="${REPO_ROOT}/${C_B_ROOT_REL}/result.json"
C_B_SEMANTIC="${REPO_ROOT}/${C_B_ROOT_REL}/review-bundle-semantic-validation.json"
C_B_BUNDLE_SNAPSHOT_MANIFEST="${REPO_ROOT}/${C_B_ROOT_REL}/bundle-snapshot-manifest.txt"
C_B_EXECUTION_CONTROL_MANIFEST="${REPO_ROOT}/${C_B_ROOT_REL}/execution-review-shadow-control-manifest.txt"

EXPECTED_C_B_RESULT_SHA="5a56b1df319d1a056a0ba3c4a86c3edcf3ceca2b0c74b97cde4a6133041275e8"
EXPECTED_C_B_SEMANTIC_SHA="541815733492a5aeff441456a66a5d91e9d78dc34690181f4e52a6e1f544c72c"
EXPECTED_C_B_BUNDLE_SNAPSHOT_MANIFEST_SHA="d81b75da44ac7049778c1514f0862b6ca6b4de0f145f342f8fcf895e16d9f7c8"
EXPECTED_C_B_EXECUTION_CONTROL_MANIFEST_SHA="0de56730add38390e8fb6fd2dfd2379df30aa93ae0f3177b50c33fe707fa4b71"

REVIEW_BUNDLE_ROOT="/tmp/tst-5d-w2b-i2f3c-b-review-exec-shadow-20260725T160528-494244/review_requests/slack-worker-CANDIDATE-NOT-APPROVED-668ab8855ad6"
REVIEW_BUNDLE_MANIFEST="${REVIEW_BUNDLE_ROOT}/review-bundle-manifest.json"

EXPECTED_REVIEW_BUNDLE_MANIFEST_SHA="0187336a04e15cadcdfa400e2c534efff75d28666f9497c381634552cc051f13"
EXPECTED_CANDIDATE_ID="slack-worker-CANDIDATE-NOT-APPROVED-668ab8855ad6"
EXPECTED_REVIEW_BUNDLE_ID="slack-worker-release-rebinding-review-SCHEMA-CANDIDATE-c882f2cb1afb"
EXPECTED_CANDIDATE_MANIFEST_SHA="c882f2cb1afbfbe5215db61667a6c72feccc71bc84a558cdda792806d440f843"

SOURCE_PATH="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
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

require_file_sha "$C_B_RESULT" "$EXPECTED_C_B_RESULT_SHA"
require_file_sha "$C_B_SEMANTIC" "$EXPECTED_C_B_SEMANTIC_SHA"
require_file_sha \
    "$C_B_BUNDLE_SNAPSHOT_MANIFEST" \
    "$EXPECTED_C_B_BUNDLE_SNAPSHOT_MANIFEST_SHA"
require_file_sha \
    "$C_B_EXECUTION_CONTROL_MANIFEST" \
    "$EXPECTED_C_B_EXECUTION_CONTROL_MANIFEST_SHA"
require_file_sha \
    "$REVIEW_BUNDLE_MANIFEST" \
    "$EXPECTED_REVIEW_BUNDLE_MANIFEST_SHA"
require_file_sha "$SOURCE_PATH" "$EXPECTED_SOURCE_SHA"
require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

if [[ ! -d "$REVIEW_BUNDLE_ROOT" ]]; then
    printf 'ERROR=REVIEW_BUNDLE_ROOT_MISSING:%s\n' "$REVIEW_BUNDLE_ROOT" >&2
    exit 1
fi

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3c-c-human-review-decision-record-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p \
    "$EVIDENCE_ROOT/source-bundle-snapshot" \
    "$EVIDENCE_ROOT/unit-decisions"

python3 - \
    "$REVIEW_BUNDLE_ROOT" \
    "$EVIDENCE_ROOT" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" \
    "$EXPECTED_CANDIDATE_MANIFEST_SHA" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

bundle_root = Path(sys.argv[1]).resolve()
evidence_root = Path(sys.argv[2]).resolve()
expected_candidate_id = sys.argv[3]
expected_bundle_id = sys.argv[4]
expected_candidate_sha = sys.argv[5]

manifest_path = bundle_root / "review-bundle-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

if manifest.get("candidate_id") != expected_candidate_id:
    raise SystemExit("CANDIDATE_ID_MISMATCH")
if manifest.get("review_bundle_id") != expected_bundle_id:
    raise SystemExit("REVIEW_BUNDLE_ID_MISMATCH")
if manifest.get("candidate_manifest_sha256") != expected_candidate_sha:
    raise SystemExit("CANDIDATE_MANIFEST_SHA_MISMATCH")
if manifest.get("review_bundle_status") != "READY_FOR_HUMAN_REVIEW_NOT_APPROVED":
    raise SystemExit("REVIEW_BUNDLE_STATUS_INVALID")
if manifest.get("release_status") != "CANDIDATE_NOT_APPROVED":
    raise SystemExit("RELEASE_STATUS_INVALID")
if manifest.get("human_decision_recorded") is not False:
    raise SystemExit("SOURCE_BUNDLE_ALREADY_HAS_HUMAN_DECISION")
if manifest.get("production_approval_created") is not False:
    raise SystemExit("SOURCE_BUNDLE_PRODUCTION_APPROVAL_INVALID")
if manifest.get("deployment_allowed") is not False:
    raise SystemExit("SOURCE_BUNDLE_DEPLOYMENT_INVALID")
if manifest.get("runtime_execution_allowed") is not False:
    raise SystemExit("SOURCE_BUNDLE_RUNTIME_INVALID")
if manifest.get("production_manifest_replacement_allowed") is not False:
    raise SystemExit("SOURCE_BUNDLE_MANIFEST_REPLACEMENT_INVALID")

unit_paths = manifest.get("review_unit_paths")
unit_hashes = manifest.get("review_unit_sha256")
template_paths = manifest.get("decision_template_paths")
template_hashes = manifest.get("decision_template_sha256")

expected_units = {
    "UNIT_DB_SAFETY",
    "UNIT_WORKFLOW_STATE",
    "UNIT_SLACK_RUNTIME",
}

if not isinstance(unit_paths, dict) or set(unit_paths) != expected_units:
    raise SystemExit("REVIEW_UNIT_PATH_SET_INVALID")
if not isinstance(unit_hashes, dict) or set(unit_hashes) != expected_units:
    raise SystemExit("REVIEW_UNIT_HASH_SET_INVALID")
if not isinstance(template_paths, dict) or set(template_paths) != expected_units:
    raise SystemExit("DECISION_TEMPLATE_PATH_SET_INVALID")
if not isinstance(template_hashes, dict) or set(template_hashes) != expected_units:
    raise SystemExit("DECISION_TEMPLATE_HASH_SET_INVALID")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def copy_read_only(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"SNAPSHOT_SOURCE_MISSING:{src}")
    if dst.exists() or os.path.lexists(dst):
        raise SystemExit(f"SNAPSHOT_DESTINATION_EXISTS:{dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst, follow_symlinks=False)
    dst.chmod(0o444)


packets: dict[str, dict[str, Any]] = {}
templates: dict[str, dict[str, Any]] = {}
packet_sha: dict[str, str] = {}
template_sha: dict[str, str] = {}

for unit_id in sorted(expected_units):
    packet_path = bundle_root / unit_paths[unit_id]
    template_path = bundle_root / template_paths[unit_id]

    packet_bytes = packet_path.read_bytes()
    template_bytes = template_path.read_bytes()

    if sha256_bytes(packet_bytes) != unit_hashes[unit_id]:
        raise SystemExit(f"REVIEW_PACKET_SHA_MISMATCH:{unit_id}")
    if sha256_bytes(template_bytes) != template_hashes[unit_id]:
        raise SystemExit(f"DECISION_TEMPLATE_SHA_MISMATCH:{unit_id}")

    packet = load_json(packet_path)
    template = load_json(template_path)

    if packet.get("review_status") != "NOT_REVIEWED":
        raise SystemExit(f"REVIEW_PACKET_STATUS_INVALID:{unit_id}")
    if packet.get("approval_status") != "NOT_ISSUED":
        raise SystemExit(f"REVIEW_PACKET_APPROVAL_STATUS_INVALID:{unit_id}")

    if template.get("decision") is not None:
        raise SystemExit(f"DECISION_TEMPLATE_NOT_EMPTY:{unit_id}")
    if template.get("approval_issued") is not False:
        raise SystemExit(f"DECISION_TEMPLATE_APPROVAL_INVALID:{unit_id}")
    if template.get("deployment_allowed") is not False:
        raise SystemExit(f"DECISION_TEMPLATE_DEPLOYMENT_INVALID:{unit_id}")
    if template.get("production_manifest_update_allowed") is not False:
        raise SystemExit(f"DECISION_TEMPLATE_MANIFEST_UPDATE_INVALID:{unit_id}")

    packets[unit_id] = packet
    templates[unit_id] = template
    packet_sha[unit_id] = sha256_bytes(packet_bytes)
    template_sha[unit_id] = sha256_bytes(template_bytes)

snapshot_root = evidence_root / "source-bundle-snapshot"
copy_read_only(manifest_path, snapshot_root / "review-bundle-manifest.json")
for unit_id in sorted(expected_units):
    copy_read_only(
        bundle_root / unit_paths[unit_id],
        snapshot_root / unit_paths[unit_id],
    )
    copy_read_only(
        bundle_root / template_paths[unit_id],
        snapshot_root / template_paths[unit_id],
    )

reviewed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    "+00:00", "Z"
)

workflow_conditions = [
    "FIX1 source/rebinding reviewのみ承認",
    "production migrationは未承認",
    "production manifest更新は未承認",
    "production DB接続は未承認",
    "deploymentおよび外部通信は未承認",
]

slack_hold_conditions = [
    "Slack Bolt ImportErrorを強制し固定エラーSLACK_BOLT_DEPENDENCY_NOT_AVAILABLEを検証するoffline focused testを追加",
    "ImportError時にmain()が終了コード3を返すことを検証",
    "ImportError時にhandler.startへ到達しないことを検証",
    "ImportError時にDB sessionを生成しないことを検証",
    "production default factory equivalenceをoffline testで検証",
    "App(token=bot_token)およびSocketModeHandler(app, app_token)の引数同等性を検証",
    "正常終了および停止経路でhandler.startが1回、closeが最大1回であることを検証",
]

decision_specs: dict[str, dict[str, Any]] = {
    "UNIT_DB_SAFETY": {
        "requested_decision_label": "APPROVE",
        "canonical_decision": "APPROVE",
        "conditions": [
            "承認範囲はsource/rebinding reviewに限定",
            "production manifest更新、production DB接続、migration、deployment、外部通信は未承認",
        ],
        "reason": (
            "Fail-closed production SQLite access guard, lazy engine creation, "
            "path/inode boundary checks, and compatibility alias were reviewed."
        ),
    },
    "UNIT_WORKFLOW_STATE": {
        "requested_decision_label": "APPROVE_WITH_CONDITIONS",
        "canonical_decision": "APPROVE",
        "conditions": workflow_conditions,
        "reason": (
            "FIX1 input normalization, no-clear/no-rebind semantics, idempotent "
            "same binding, repository uniqueness precheck, partial unique index "
            "contract, and DRAFT-only reconciliation were reviewed."
        ),
    },
    "UNIT_SLACK_RUNTIME": {
        "requested_decision_label": "HOLD",
        "canonical_decision": "HOLD",
        "conditions": slack_hold_conditions,
        "reason": (
            "Offline focused coverage is still required for Slack Bolt ImportError "
            "and production default factory equivalence before approval."
        ),
    },
}

decision_sha: dict[str, str] = {}

for unit_id, spec in decision_specs.items():
    decision = {
        "schema_version": "slack_worker_review_human_decision_record_v1",
        "record_status": "HUMAN_DECISION_RECORDED_REVIEW_ONLY",
        "candidate_id": expected_candidate_id,
        "review_bundle_id": expected_bundle_id,
        "review_bundle_manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "review_unit_id": unit_id,
        "review_packet_path": unit_paths[unit_id],
        "review_packet_sha256": packet_sha[unit_id],
        "source_decision_template_path": template_paths[unit_id],
        "source_decision_template_sha256": template_sha[unit_id],
        "requested_decision_label": spec["requested_decision_label"],
        "canonical_decision": spec["canonical_decision"],
        "allowed_template_decision": spec["canonical_decision"],
        "reviewer": "HUMAN_OPERATOR",
        "decision_source": "EXPLICIT_CHAT_APPROVAL",
        "reviewed_at": reviewed_at,
        "reason": spec["reason"],
        "conditions": spec["conditions"],
        "single_use": True,
        "review_decision_recorded": True,
        "approval_issued": False,
        "production_approval_created": False,
        "production_manifest_update_allowed": False,
        "production_database_access_allowed": False,
        "production_migration_allowed": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "external_network_allowed": False,
    }

    path = evidence_root / "unit-decisions" / f"{unit_id}.human-decision.json"
    write_json(path, decision)
    path.chmod(0o444)
    decision_sha[unit_id] = sha256_bytes(path.read_bytes())

aggregate = {
    "schema_version": "slack_worker_release_rebinding_human_review_decision_set_v1",
    "record_status": "HUMAN_REVIEW_DECISIONS_RECORDED_REVIEW_ONLY",
    "candidate_id": expected_candidate_id,
    "candidate_manifest_sha256": expected_candidate_sha,
    "review_bundle_id": expected_bundle_id,
    "review_bundle_manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
    "reviewed_at": reviewed_at,
    "reviewer": "HUMAN_OPERATOR",
    "decision_source": "EXPLICIT_CHAT_APPROVAL",
    "decisions": {
        unit_id: {
            "requested_decision_label": decision_specs[unit_id][
                "requested_decision_label"
            ],
            "canonical_decision": decision_specs[unit_id]["canonical_decision"],
            "decision_record_path": (
                f"unit-decisions/{unit_id}.human-decision.json"
            ),
            "decision_record_sha256": decision_sha[unit_id],
        }
        for unit_id in sorted(expected_units)
    },
    "unit_summary": {
        "approved_unit_count": 2,
        "held_unit_count": 1,
        "rejected_unit_count": 0,
        "conditionally_approved_unit_count": 1,
    },
    "overall_candidate_decision": "HOLD",
    "overall_candidate_reason": (
        "UNIT_SLACK_RUNTIME remains HOLD pending two offline focused test groups."
    ),
    "release_status": "CANDIDATE_NOT_APPROVED",
    "human_review_performed": True,
    "human_decision_recorded": True,
    "production_approval_created": False,
    "production_manifest_update_allowed": False,
    "production_database_access_allowed": False,
    "production_migration_allowed": False,
    "deployment_allowed": False,
    "runtime_execution_allowed": False,
    "external_network_allowed": False,
    "unit_workflow_state": "APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
    "unit_slack_runtime": "HOLD_PENDING_OFFLINE_FOCUSED_TESTS",
    "next_phase": "TST-5D-W2B-I2F-3D-A_SLACK_HOLD_REMEDIATION_TEST_INVENTORY",
}

aggregate_path = evidence_root / "human-review-decision-set.json"
write_json(aggregate_path, aggregate)
aggregate_path.chmod(0o444)

approval_text = """承認：
UNIT_DB_SAFETY=APPROVE
UNIT_WORKFLOW_STATE=APPROVE_WITH_CONDITIONS
UNIT_SLACK_RUNTIME=HOLD

WORKFLOW条件：
FIX1 source/rebinding reviewのみ承認。
production migration、production manifest更新、production DB接続、
deployment、外部通信は未承認。

SLACK HOLD解除条件：
Slack Bolt ImportError固定エラー試験と
production default factory equivalenceのoffline試験を追加する。
"""

approval_text_path = evidence_root / "human-approval-verbatim.txt"
approval_text_path.write_text(approval_text, encoding="utf-8")
approval_text_path.chmod(0o444)

validation = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3C-C",
    "result": "PASS_HUMAN_REVIEW_DECISION_RECORD_VALIDATED",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_bundle_id,
    "review_bundle_manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
    "source_bundle_immutable": True,
    "decision_records": {
        unit_id: {
            "sha256": decision_sha[unit_id],
            "requested_decision_label": decision_specs[unit_id][
                "requested_decision_label"
            ],
            "canonical_decision": decision_specs[unit_id]["canonical_decision"],
        }
        for unit_id in sorted(expected_units)
    },
    "overall_candidate_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_approval_created": False,
    "production_manifest_update_allowed": False,
    "production_database_access_allowed": False,
    "production_migration_allowed": False,
    "deployment_allowed": False,
    "runtime_execution_allowed": False,
    "external_network_allowed": False,
    "next_phase": "TST-5D-W2B-I2F-3D-A_SLACK_HOLD_REMEDIATION_TEST_INVENTORY",
}

validation_path = evidence_root / "human-review-decision-validation.json"
write_json(validation_path, validation)
validation_path.chmod(0o444)
PY

SNAPSHOT_MANIFEST="${EVIDENCE_ROOT}/decision-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'decision-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$SNAPSHOT_MANIFEST"
chmod 0444 "$SNAPSHOT_MANIFEST"

DECISION_SET="${EVIDENCE_ROOT}/human-review-decision-set.json"
DECISION_VALIDATION="${EVIDENCE_ROOT}/human-review-decision-validation.json"
APPROVAL_VERBATIM="${EVIDENCE_ROOT}/human-approval-verbatim.txt"

DECISION_SET_SHA="$(sha256_file "$DECISION_SET")"
DECISION_VALIDATION_SHA="$(sha256_file "$DECISION_VALIDATION")"
APPROVAL_VERBATIM_SHA="$(sha256_file "$APPROVAL_VERBATIM")"
SNAPSHOT_MANIFEST_SHA="$(sha256_file "$SNAPSHOT_MANIFEST")"

SOURCE_AFTER="$(sha256_file "$SOURCE_PATH")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"
REVIEW_BUNDLE_MANIFEST_AFTER="$(sha256_file "$REVIEW_BUNDLE_MANIFEST")"

[[ "$SOURCE_AFTER" == "$EXPECTED_SOURCE_SHA" ]] || {
    printf 'ERROR=PRODUCTION_SOURCE_CHANGED\n' >&2
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
[[ "$REVIEW_BUNDLE_MANIFEST_AFTER" == "$EXPECTED_REVIEW_BUNDLE_MANIFEST_SHA" ]] || {
    printf 'ERROR=SOURCE_REVIEW_BUNDLE_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3C-C",
  "result": "PASS_W2B_I2F3C_C_HUMAN_REVIEW_DECISIONS_RECORDED",
  "candidate_id": "${EXPECTED_CANDIDATE_ID}",
  "review_bundle_id": "${EXPECTED_REVIEW_BUNDLE_ID}",
  "review_bundle_manifest_sha256": "${EXPECTED_REVIEW_BUNDLE_MANIFEST_SHA}",
  "evidence_root": "${EVIDENCE_REL}",
  "decisions": {
    "UNIT_DB_SAFETY": "APPROVE",
    "UNIT_WORKFLOW_STATE": "APPROVE_WITH_CONDITIONS",
    "UNIT_SLACK_RUNTIME": "HOLD"
  },
  "normalization": {
    "UNIT_WORKFLOW_STATE_requested_label": "APPROVE_WITH_CONDITIONS",
    "UNIT_WORKFLOW_STATE_canonical_decision": "APPROVE"
  },
  "overall_candidate_decision": "HOLD",
  "release_status": "CANDIDATE_NOT_APPROVED",
  "artifacts": {
    "human_review_decision_set_sha256": "${DECISION_SET_SHA}",
    "human_review_decision_validation_sha256": "${DECISION_VALIDATION_SHA}",
    "human_approval_verbatim_sha256": "${APPROVAL_VERBATIM_SHA}",
    "decision_evidence_manifest_sha256": "${SNAPSHOT_MANIFEST_SHA}"
  },
  "governance": {
    "human_review_performed": true,
    "human_decision_recorded": true,
    "production_approval_created": false,
    "production_manifest_update_allowed": false,
    "production_database_access_allowed": false,
    "production_migration_allowed": false,
    "deployment_allowed": false,
    "runtime_execution_allowed": false,
    "external_network_allowed": false
  },
  "safety": {
    "source_review_bundle_changed": false,
    "production_source_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "unit_workflow_state": "APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
  "unit_slack_runtime": "HOLD_PENDING_OFFLINE_FOCUSED_TESTS",
  "next_phase": "TST-5D-W2B-I2F-3D-A_SLACK_HOLD_REMEDIATION_TEST_INVENTORY",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3C_C_HUMAN_REVIEW_DECISIONS_RECORDED\n'
printf 'CANDIDATE_ID=%s\n' "$EXPECTED_CANDIDATE_ID"
printf 'REVIEW_BUNDLE_ID=%s\n' "$EXPECTED_REVIEW_BUNDLE_ID"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'UNIT_DB_SAFETY=APPROVE\n'
printf 'UNIT_WORKFLOW_STATE=APPROVE_WITH_CONDITIONS\n'
printf 'UNIT_WORKFLOW_STATE_CANONICAL_DECISION=APPROVE\n'
printf 'UNIT_SLACK_RUNTIME=HOLD\n'
printf 'OVERALL_CANDIDATE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'DECISION_SET_SHA=%s\n' "$DECISION_SET_SHA"
printf 'DECISION_VALIDATION_SHA=%s\n' "$DECISION_VALIDATION_SHA"
printf 'APPROVAL_VERBATIM_SHA=%s\n' "$APPROVAL_VERBATIM_SHA"
printf 'DECISION_EVIDENCE_MANIFEST_SHA=%s\n' "$SNAPSHOT_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'HUMAN_REVIEW_PERFORMED=true\n'
printf 'HUMAN_DECISION_RECORDED=true\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'PRODUCTION_MANIFEST_UPDATE_ALLOWED=false\n'
printf 'PRODUCTION_DB_ACCESS_ALLOWED=false\n'
printf 'PRODUCTION_MIGRATION_ALLOWED=false\n'
printf 'DEPLOYMENT_ALLOWED=false\n'
printf 'RUNTIME_EXECUTION_ALLOWED=false\n'
printf 'EXTERNAL_NETWORK_ALLOWED=false\n'
printf 'SOURCE_REVIEW_BUNDLE_CHANGED=false\n'
printf 'PRODUCTION_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_WORKFLOW_STATE_STATUS=APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION\n'
printf 'UNIT_SLACK_RUNTIME_STATUS=HOLD_PENDING_OFFLINE_FOCUSED_TESTS\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3D-A_SLACK_HOLD_REMEDIATION_TEST_INVENTORY\n'
printf 'SCRIPT_EXIT_CODE=0\n'
