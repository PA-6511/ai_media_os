#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
PRIOR_DECISION_ROOT_REL="${I2E_ROOT_REL}/i2f3c-c-human-review-decision-record-20260725T161539-495634"
SLACK_TEST_ROOT_REL="${I2E_ROOT_REL}/i2f3d-b-slack-hold-offline-tests-20260725T164615-497367"
BUNDLE_ROOT_REL="${I2E_ROOT_REL}/i2f3c-b-review-bundle-validation-20260725T160528-494244"

PRIOR_DECISION_RESULT="${REPO_ROOT}/${PRIOR_DECISION_ROOT_REL}/result.json"
PRIOR_DECISION_SET="${REPO_ROOT}/${PRIOR_DECISION_ROOT_REL}/human-review-decision-set.json"
PRIOR_DECISION_VALIDATION="${REPO_ROOT}/${PRIOR_DECISION_ROOT_REL}/human-review-decision-validation.json"
PRIOR_APPROVAL_VERBATIM="${REPO_ROOT}/${PRIOR_DECISION_ROOT_REL}/human-approval-verbatim.txt"
PRIOR_DECISION_MANIFEST="${REPO_ROOT}/${PRIOR_DECISION_ROOT_REL}/decision-evidence-manifest.txt"

SLACK_TEST_RESULT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/result.json"
SLACK_TEST_SUMMARY="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/offline-test-summary.json"
SLACK_TEST_MANIFEST="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/offline-test-evidence-manifest.txt"
SLACK_TEST_SNAPSHOT="${REPO_ROOT}/${SLACK_TEST_ROOT_REL}/shadow-test-snapshot/test_slack_approval_socket_hold_remediation_offline.py"

BUNDLE_RESULT="${REPO_ROOT}/${BUNDLE_ROOT_REL}/result.json"

EXPECTED_PRIOR_DECISION_RESULT_SHA="1790eedbf06d94c29c7dbe03e7aa3dd9bea4b4343f5cd3a1c4ea42d6ed732cba"
EXPECTED_PRIOR_DECISION_SET_SHA="4c72b8b39f30961741c47702e00d9dd4062168bf943fe96ffcbea63d29e65cf6"
EXPECTED_PRIOR_DECISION_VALIDATION_SHA="d4fa57d22ec2d5f3d149755f37035f06fb54f2392404cfaabc59021d8ae7da86"
EXPECTED_PRIOR_APPROVAL_VERBATIM_SHA="77f43f601c043e41a07b8bcf0c8f4fe3a0074eda19a8ef9a8ac9b010f7116116"
EXPECTED_PRIOR_DECISION_MANIFEST_SHA="ee41601f75c8e5afd9ea7d1255957395f4e62a0323484690805812b7ab78d79d"

EXPECTED_SLACK_TEST_RESULT_SHA="732840292f5c551d589ea8e9459fc677c9df0380fb4ef1f18d5eafa2f1c33ce0"
EXPECTED_SLACK_TEST_SUMMARY_SHA="366d96fd38f85d8dda234ace2c49015386909d9baf5c23f91195b3e278fc3a31"
EXPECTED_SLACK_TEST_MANIFEST_SHA="a7f65b6b16eb7f760b9503e630ca7b8559b2e4c38484eb6a045170ef369459c6"
EXPECTED_SLACK_TEST_SNAPSHOT_SHA="5f4bc6709120998383543f346e504c4ab2c408c0dfd7219d1ff3f8a236a83184"

EXPECTED_BUNDLE_RESULT_SHA="5a56b1df319d1a056a0ba3c4a86c3edcf3ceca2b0c74b97cde4a6133041275e8"

SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

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

require_file_sha \
    "$PRIOR_DECISION_RESULT" \
    "$EXPECTED_PRIOR_DECISION_RESULT_SHA"
require_file_sha \
    "$PRIOR_DECISION_SET" \
    "$EXPECTED_PRIOR_DECISION_SET_SHA"
require_file_sha \
    "$PRIOR_DECISION_VALIDATION" \
    "$EXPECTED_PRIOR_DECISION_VALIDATION_SHA"
require_file_sha \
    "$PRIOR_APPROVAL_VERBATIM" \
    "$EXPECTED_PRIOR_APPROVAL_VERBATIM_SHA"
require_file_sha \
    "$PRIOR_DECISION_MANIFEST" \
    "$EXPECTED_PRIOR_DECISION_MANIFEST_SHA"

require_file_sha \
    "$SLACK_TEST_RESULT" \
    "$EXPECTED_SLACK_TEST_RESULT_SHA"
require_file_sha \
    "$SLACK_TEST_SUMMARY" \
    "$EXPECTED_SLACK_TEST_SUMMARY_SHA"
require_file_sha \
    "$SLACK_TEST_MANIFEST" \
    "$EXPECTED_SLACK_TEST_MANIFEST_SHA"
require_file_sha \
    "$SLACK_TEST_SNAPSHOT" \
    "$EXPECTED_SLACK_TEST_SNAPSHOT_SHA"

require_file_sha "$BUNDLE_RESULT" "$EXPECTED_BUNDLE_RESULT_SHA"

require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3d-c-slack-runtime-human-rereview-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p \
    "$EVIDENCE_ROOT/source-evidence-snapshot" \
    "$EVIDENCE_ROOT/human-decisions"

python3 - \
    "$PRIOR_DECISION_SET" \
    "$PRIOR_DECISION_RESULT" \
    "$SLACK_TEST_RESULT" \
    "$SLACK_TEST_SUMMARY" \
    "$BUNDLE_RESULT" \
    "$EVIDENCE_ROOT" \
    "$EXPECTED_CANDIDATE_ID" \
    "$EXPECTED_REVIEW_BUNDLE_ID" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

prior_set_path = Path(sys.argv[1]).resolve()
prior_result_path = Path(sys.argv[2]).resolve()
slack_test_result_path = Path(sys.argv[3]).resolve()
slack_test_summary_path = Path(sys.argv[4]).resolve()
bundle_result_path = Path(sys.argv[5]).resolve()
evidence_root = Path(sys.argv[6]).resolve()
expected_candidate_id = sys.argv[7]
expected_review_bundle_id = sys.argv[8]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


prior_set = load_json(prior_set_path)
prior_result = load_json(prior_result_path)
slack_test_result = load_json(slack_test_result_path)
slack_test_summary = load_json(slack_test_summary_path)
bundle_result = load_json(bundle_result_path)

if prior_set.get("candidate_id") != expected_candidate_id:
    raise SystemExit("PRIOR_DECISION_CANDIDATE_ID_MISMATCH")
if prior_set.get("review_bundle_id") != expected_review_bundle_id:
    raise SystemExit("PRIOR_DECISION_REVIEW_BUNDLE_ID_MISMATCH")
if prior_set.get("overall_candidate_decision") != "HOLD":
    raise SystemExit("PRIOR_OVERALL_DECISION_NOT_HOLD")
if prior_set.get("release_status") != "CANDIDATE_NOT_APPROVED":
    raise SystemExit("PRIOR_RELEASE_STATUS_INVALID")

prior_decisions = prior_set.get("decisions")
if not isinstance(prior_decisions, dict):
    raise SystemExit("PRIOR_DECISIONS_INVALID")

expected_prior_labels = {
    "UNIT_DB_SAFETY": "APPROVE",
    "UNIT_WORKFLOW_STATE": "APPROVE_WITH_CONDITIONS",
    "UNIT_SLACK_RUNTIME": "HOLD",
}

for unit_id, expected_label in expected_prior_labels.items():
    item = prior_decisions.get(unit_id)
    if not isinstance(item, dict):
        raise SystemExit(f"PRIOR_DECISION_MISSING:{unit_id}")
    if item.get("requested_decision_label") != expected_label:
        raise SystemExit(f"PRIOR_DECISION_LABEL_INVALID:{unit_id}")

if prior_result.get("result") != (
    "PASS_W2B_I2F3C_C_HUMAN_REVIEW_DECISIONS_RECORDED"
):
    raise SystemExit("PRIOR_DECISION_RESULT_INVALID")

if slack_test_result.get("result") != (
    "PASS_W2B_I2F3D_B_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS"
):
    raise SystemExit("SLACK_TEST_RESULT_INVALID")

pytest_result = slack_test_result.get("pytest")
if not isinstance(pytest_result, dict):
    raise SystemExit("SLACK_TEST_PYTEST_INVALID")
if pytest_result.get("focused_passed_count") != 4:
    raise SystemExit("SLACK_FOCUSED_TEST_COUNT_INVALID")
if pytest_result.get("related_passed_count") != 17:
    raise SystemExit("SLACK_RELATED_TEST_COUNT_INVALID")
if pytest_result.get("collect_exit_code") != 0:
    raise SystemExit("SLACK_COLLECT_EXIT_INVALID")
if pytest_result.get("focused_exit_code") != 0:
    raise SystemExit("SLACK_FOCUSED_EXIT_INVALID")
if pytest_result.get("related_exit_code") != 0:
    raise SystemExit("SLACK_RELATED_EXIT_INVALID")

hold_conditions = slack_test_result.get("hold_conditions")
if not isinstance(hold_conditions, dict):
    raise SystemExit("SLACK_HOLD_CONDITIONS_INVALID")

expected_hold_pass = {
    "slack_bolt_import_error_fixed_error": "PASS",
    "production_default_factory_equivalence": "PASS",
    "handler_lifecycle_offline": "PASS",
}
for key, expected in expected_hold_pass.items():
    if hold_conditions.get(key) != expected:
        raise SystemExit(f"SLACK_HOLD_CONDITION_NOT_PASS:{key}")

execution = slack_test_result.get("execution")
if not isinstance(execution, dict):
    raise SystemExit("SLACK_TEST_EXECUTION_INVALID")

required_false_execution = {
    "production_test_file_created",
    "production_runtime_source_modified",
    "production_database_opened",
    "credential_content_read",
    "external_network_used",
}
for key in sorted(required_false_execution):
    if execution.get(key) is not False:
        raise SystemExit(f"SLACK_TEST_BOUNDARY_INVALID:{key}")

if slack_test_result.get("governance", {}).get(
    "unit_slack_runtime"
) != "READY_FOR_HUMAN_REREVIEW_NOT_APPROVED":
    raise SystemExit("SLACK_REREVIEW_STATE_INVALID")
if slack_test_result.get("governance", {}).get(
    "overall_candidate_decision"
) != "HOLD":
    raise SystemExit("SLACK_TEST_OVERALL_DECISION_INVALID")
if slack_test_result.get("governance", {}).get(
    "release_status"
) != "CANDIDATE_NOT_APPROVED":
    raise SystemExit("SLACK_TEST_RELEASE_STATUS_INVALID")

if slack_test_summary.get("result") != (
    "PASS_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS"
):
    raise SystemExit("SLACK_TEST_SUMMARY_INVALID")
if slack_test_summary.get("unit_slack_runtime") != (
    "READY_FOR_HUMAN_REREVIEW_NOT_APPROVED"
):
    raise SystemExit("SLACK_TEST_SUMMARY_STATE_INVALID")

if bundle_result.get("candidate_id") != expected_candidate_id:
    raise SystemExit("BUNDLE_RESULT_CANDIDATE_ID_MISMATCH")
if bundle_result.get("review_bundle_id") != expected_review_bundle_id:
    raise SystemExit("BUNDLE_RESULT_REVIEW_BUNDLE_ID_MISMATCH")
if bundle_result.get("result") != (
    "PASS_W2B_I2F3C_B_SHADOW_REVIEW_BUNDLE_VALIDATED"
):
    raise SystemExit("BUNDLE_RESULT_INVALID")

snapshot_root = evidence_root / "source-evidence-snapshot"
copy_read_only(prior_set_path, snapshot_root / "prior-human-review-decision-set.json")
copy_read_only(prior_result_path, snapshot_root / "prior-human-review-result.json")
copy_read_only(
    slack_test_result_path,
    snapshot_root / "slack-hold-offline-test-result.json",
)
copy_read_only(
    slack_test_summary_path,
    snapshot_root / "slack-hold-offline-test-summary.json",
)
copy_read_only(
    bundle_result_path,
    snapshot_root / "review-bundle-result.json",
)

reviewed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    "+00:00", "Z"
)

slack_conditions = [
    "Slack Bolt ImportError固定エラー試験のPASSを承認",
    "production default factory equivalence試験のPASSを承認",
    "handler lifecycle offline試験のPASSを承認",
    "承認対象はSlack runtime source/rebinding reviewに限定",
    "production manifest更新は未承認",
    "production DB接続は未承認",
    "production migrationは未承認",
    "deploymentは未承認",
    "Slack Worker起動は未承認",
    "外部通信は未承認",
    "production approval作成は未承認",
]

slack_rereview_record = {
    "schema_version": "slack_worker_review_human_rereview_decision_record_v1",
    "record_status": "HUMAN_REREVIEW_DECISION_RECORDED_REVIEW_ONLY",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "review_unit_id": "UNIT_SLACK_RUNTIME",
    "prior_requested_decision_label": "HOLD",
    "requested_decision_label": "APPROVE",
    "canonical_decision": "APPROVE",
    "reviewer": "HUMAN_OPERATOR",
    "decision_source": "EXPLICIT_CHAT_APPROVAL",
    "reviewed_at": reviewed_at,
    "reason": (
        "The approved Slack Bolt ImportError fixed-error test, production "
        "default factory equivalence test, and handler lifecycle offline test "
        "all passed together with 17 directly related tests."
    ),
    "conditions": slack_conditions,
    "evidence": {
        "prior_decision_set_sha256": sha(prior_set_path),
        "prior_decision_result_sha256": sha(prior_result_path),
        "slack_hold_offline_test_result_sha256": sha(slack_test_result_path),
        "slack_hold_offline_test_summary_sha256": sha(slack_test_summary_path),
        "review_bundle_result_sha256": sha(bundle_result_path),
        "focused_test_passed_count": 4,
        "related_test_passed_count": 17,
    },
    "review_decision_recorded": True,
    "approval_issued": False,
    "production_approval_created": False,
    "production_manifest_update_allowed": False,
    "production_database_access_allowed": False,
    "production_migration_allowed": False,
    "deployment_allowed": False,
    "slack_worker_start_allowed": False,
    "runtime_execution_allowed": False,
    "external_network_allowed": False,
    "single_use": True,
}

slack_record_path = (
    evidence_root
    / "human-decisions"
    / "UNIT_SLACK_RUNTIME.human-rereview-decision.json"
)
write_json(slack_record_path, slack_rereview_record)
slack_record_path.chmod(0o444)
slack_record_sha = sha(slack_record_path)

workflow_conditions = [
    "FIX1 source/rebinding reviewのみ承認",
    "production migrationは未承認",
    "production manifest更新は未承認",
    "production DB接続は未承認",
    "deploymentおよび外部通信は未承認",
]

final_decision_set = {
    "schema_version": "slack_worker_release_rebinding_final_human_review_set_v1",
    "record_status": "ALL_REVIEW_UNITS_APPROVED_REVIEW_ONLY",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "reviewed_at": reviewed_at,
    "reviewer": "HUMAN_OPERATOR",
    "decision_source": "EXPLICIT_CHAT_APPROVAL",
    "supersedes_review_state_only": {
        "prior_decision_set_path": str(prior_set_path),
        "prior_decision_set_sha256": sha(prior_set_path),
        "prior_overall_candidate_decision": "HOLD",
        "prior_unit_slack_runtime": "HOLD",
    },
    "decisions": {
        "UNIT_DB_SAFETY": {
            "requested_decision_label": "APPROVE",
            "canonical_decision": "APPROVE",
            "conditions": [
                "source/rebinding reviewに限定",
                "production操作は未承認",
            ],
            "decision_source": "PRIOR_DECISION_MAINTAINED",
        },
        "UNIT_WORKFLOW_STATE": {
            "requested_decision_label": "APPROVE_WITH_CONDITIONS",
            "canonical_decision": "APPROVE",
            "conditions": workflow_conditions,
            "decision_source": "PRIOR_DECISION_MAINTAINED",
        },
        "UNIT_SLACK_RUNTIME": {
            "requested_decision_label": "APPROVE",
            "canonical_decision": "APPROVE",
            "conditions": slack_conditions,
            "decision_source": "NEW_HUMAN_REREVIEW_DECISION",
            "decision_record_path": (
                "human-decisions/"
                "UNIT_SLACK_RUNTIME.human-rereview-decision.json"
            ),
            "decision_record_sha256": slack_record_sha,
        },
    },
    "unit_summary": {
        "approved_unit_count": 3,
        "conditionally_approved_unit_count": 1,
        "held_unit_count": 0,
        "rejected_unit_count": 0,
        "all_review_units_approved": True,
    },
    "overall_review_decision": "APPROVE_WITH_CONDITIONS",
    "overall_review_canonical_decision": "APPROVE",
    "overall_review_scope": "SOURCE_AND_REBINDING_REVIEW_ONLY",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "human_review_performed": True,
    "human_rereview_performed": True,
    "human_decision_recorded": True,
    "production_approval_created": False,
    "production_manifest_update_allowed": False,
    "production_database_access_allowed": False,
    "production_migration_allowed": False,
    "deployment_allowed": False,
    "slack_worker_start_allowed": False,
    "runtime_execution_allowed": False,
    "external_network_allowed": False,
    "unit_db_safety_status": "APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
    "unit_workflow_state_status": (
        "APPROVED_WITH_CONDITIONS_REVIEW_ONLY_HOLD_FOR_PRODUCTION"
    ),
    "unit_slack_runtime_status": "APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
    "next_gate": "PRODUCTION_RELEASE_REMAINS_EXPLICITLY_UNAPPROVED",
}

final_set_path = evidence_root / "final-human-review-decision-set.json"
write_json(final_set_path, final_decision_set)
final_set_path.chmod(0o444)

approval_text = """承認：
UNIT_SLACK_RUNTIME=APPROVE

SLACK条件：
Slack Bolt ImportError固定エラー試験、
production default factory equivalence試験、
handler lifecycle offline試験のPASSを承認する。

承認対象はSlack runtime source/rebinding reviewに限定する。
production manifest更新、production DB接続、production migration、
deployment、Slack Worker起動、外部通信、production approval作成は未承認。

既存判断：
UNIT_DB_SAFETY=APPROVE
UNIT_WORKFLOW_STATE=APPROVE_WITH_CONDITIONS
を維持する。
"""

approval_path = evidence_root / "human-slack-rereview-approval-verbatim.txt"
approval_path.write_text(approval_text, encoding="utf-8")
approval_path.chmod(0o444)

validation = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3D-C",
    "result": "PASS_SLACK_RUNTIME_HUMAN_REREVIEW_DECISION_VALIDATED",
    "candidate_id": expected_candidate_id,
    "review_bundle_id": expected_review_bundle_id,
    "prior_decision_set_unchanged": True,
    "slack_test_evidence_verified": True,
    "slack_hold_conditions_satisfied": True,
    "unit_db_safety": "APPROVE",
    "unit_workflow_state": "APPROVE_WITH_CONDITIONS",
    "unit_slack_runtime": "APPROVE",
    "all_review_units_approved": True,
    "overall_review_decision": "APPROVE_WITH_CONDITIONS",
    "overall_review_canonical_decision": "APPROVE",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_approval_created": False,
    "production_manifest_update_allowed": False,
    "production_database_access_allowed": False,
    "production_migration_allowed": False,
    "deployment_allowed": False,
    "slack_worker_start_allowed": False,
    "runtime_execution_allowed": False,
    "external_network_allowed": False,
    "next_gate": "PRODUCTION_RELEASE_REMAINS_EXPLICITLY_UNAPPROVED",
}

validation_path = evidence_root / "slack-human-rereview-validation.json"
write_json(validation_path, validation)
validation_path.chmod(0o444)
PY

FINAL_DECISION_SET="${EVIDENCE_ROOT}/final-human-review-decision-set.json"
SLACK_DECISION_RECORD="${EVIDENCE_ROOT}/human-decisions/UNIT_SLACK_RUNTIME.human-rereview-decision.json"
REREVIEW_VALIDATION="${EVIDENCE_ROOT}/slack-human-rereview-validation.json"
APPROVAL_VERBATIM="${EVIDENCE_ROOT}/human-slack-rereview-approval-verbatim.txt"

python3 -m json.tool "$FINAL_DECISION_SET" >/dev/null
python3 -m json.tool "$SLACK_DECISION_RECORD" >/dev/null
python3 -m json.tool "$REREVIEW_VALIDATION" >/dev/null

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/rereview-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'rereview-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"
chmod 0444 "$EVIDENCE_MANIFEST"

FINAL_DECISION_SET_SHA="$(sha256_file "$FINAL_DECISION_SET")"
SLACK_DECISION_RECORD_SHA="$(sha256_file "$SLACK_DECISION_RECORD")"
REREVIEW_VALIDATION_SHA="$(sha256_file "$REREVIEW_VALIDATION")"
APPROVAL_VERBATIM_SHA="$(sha256_file "$APPROVAL_VERBATIM")"
EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"

SLACK_SOURCE_AFTER="$(sha256_file "$SLACK_SOURCE")"
WORKFLOW_SOURCE_AFTER="$(sha256_file "$WORKFLOW_SOURCE")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"

PRIOR_DECISION_RESULT_AFTER="$(sha256_file "$PRIOR_DECISION_RESULT")"
PRIOR_DECISION_SET_AFTER="$(sha256_file "$PRIOR_DECISION_SET")"
SLACK_TEST_RESULT_AFTER="$(sha256_file "$SLACK_TEST_RESULT")"
SLACK_TEST_SUMMARY_AFTER="$(sha256_file "$SLACK_TEST_SUMMARY")"

[[ "$SLACK_SOURCE_AFTER" == "$EXPECTED_SLACK_SOURCE_SHA" ]] || {
    printf 'ERROR=SLACK_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$WORKFLOW_SOURCE_AFTER" == "$EXPECTED_WORKFLOW_SOURCE_SHA" ]] || {
    printf 'ERROR=WORKFLOW_SOURCE_CHANGED\n' >&2
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
[[ "$PRIOR_DECISION_RESULT_AFTER" == "$EXPECTED_PRIOR_DECISION_RESULT_SHA" ]] || {
    printf 'ERROR=PRIOR_DECISION_RESULT_CHANGED\n' >&2
    exit 1
}
[[ "$PRIOR_DECISION_SET_AFTER" == "$EXPECTED_PRIOR_DECISION_SET_SHA" ]] || {
    printf 'ERROR=PRIOR_DECISION_SET_CHANGED\n' >&2
    exit 1
}
[[ "$SLACK_TEST_RESULT_AFTER" == "$EXPECTED_SLACK_TEST_RESULT_SHA" ]] || {
    printf 'ERROR=SLACK_TEST_RESULT_CHANGED\n' >&2
    exit 1
}
[[ "$SLACK_TEST_SUMMARY_AFTER" == "$EXPECTED_SLACK_TEST_SUMMARY_SHA" ]] || {
    printf 'ERROR=SLACK_TEST_SUMMARY_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3D-C",
  "result": "PASS_W2B_I2F3D_C_SLACK_RUNTIME_APPROVAL_RECORDED",
  "candidate_id": "${EXPECTED_CANDIDATE_ID}",
  "review_bundle_id": "${EXPECTED_REVIEW_BUNDLE_ID}",
  "evidence_root": "${EVIDENCE_REL}",
  "decisions": {
    "UNIT_DB_SAFETY": "APPROVE",
    "UNIT_WORKFLOW_STATE": "APPROVE_WITH_CONDITIONS",
    "UNIT_SLACK_RUNTIME": "APPROVE"
  },
  "review_state": {
    "all_review_units_approved": true,
    "overall_review_decision": "APPROVE_WITH_CONDITIONS",
    "overall_review_canonical_decision": "APPROVE",
    "overall_review_scope": "SOURCE_AND_REBINDING_REVIEW_ONLY"
  },
  "production_state": {
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_approval_created": false,
    "production_manifest_update_allowed": false,
    "production_database_access_allowed": false,
    "production_migration_allowed": false,
    "deployment_allowed": false,
    "slack_worker_start_allowed": false,
    "runtime_execution_allowed": false,
    "external_network_allowed": false
  },
  "slack_hold_remediation_evidence": {
    "focused_test_passed_count": 4,
    "related_test_passed_count": 17,
    "slack_bolt_import_error_fixed_error": "PASS",
    "production_default_factory_equivalence": "PASS",
    "handler_lifecycle_offline": "PASS",
    "test_result_sha256": "${EXPECTED_SLACK_TEST_RESULT_SHA}",
    "test_summary_sha256": "${EXPECTED_SLACK_TEST_SUMMARY_SHA}"
  },
  "artifacts": {
    "final_human_review_decision_set_sha256": "${FINAL_DECISION_SET_SHA}",
    "slack_human_rereview_decision_sha256": "${SLACK_DECISION_RECORD_SHA}",
    "slack_human_rereview_validation_sha256": "${REREVIEW_VALIDATION_SHA}",
    "human_approval_verbatim_sha256": "${APPROVAL_VERBATIM_SHA}",
    "rereview_evidence_manifest_sha256": "${EVIDENCE_MANIFEST_SHA}"
  },
  "safety": {
    "prior_decision_result_changed": false,
    "prior_decision_set_changed": false,
    "slack_test_result_changed": false,
    "slack_test_summary_changed": false,
    "slack_source_changed": false,
    "workflow_source_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "slack_worker_started": false,
    "external_network_used": false
  },
  "unit_db_safety_status": "APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
  "unit_workflow_state_status": "APPROVED_WITH_CONDITIONS_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
  "unit_slack_runtime_status": "APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION",
  "next_gate": "PRODUCTION_RELEASE_REMAINS_EXPLICITLY_UNAPPROVED",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3D_C_SLACK_RUNTIME_APPROVAL_RECORDED\n'
printf 'CANDIDATE_ID=%s\n' "$EXPECTED_CANDIDATE_ID"
printf 'REVIEW_BUNDLE_ID=%s\n' "$EXPECTED_REVIEW_BUNDLE_ID"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'UNIT_DB_SAFETY=APPROVE\n'
printf 'UNIT_WORKFLOW_STATE=APPROVE_WITH_CONDITIONS\n'
printf 'UNIT_WORKFLOW_STATE_CANONICAL_DECISION=APPROVE\n'
printf 'UNIT_SLACK_RUNTIME=APPROVE\n'
printf 'ALL_REVIEW_UNITS_APPROVED=true\n'
printf 'OVERALL_REVIEW_DECISION=APPROVE_WITH_CONDITIONS\n'
printf 'OVERALL_REVIEW_CANONICAL_DECISION=APPROVE\n'
printf 'OVERALL_REVIEW_SCOPE=SOURCE_AND_REBINDING_REVIEW_ONLY\n'
printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'FOCUSED_TEST_PASSED_COUNT=4\n'
printf 'RELATED_TEST_PASSED_COUNT=17\n'
printf 'SLACK_BOLT_IMPORT_ERROR_FIXED_ERROR=PASS\n'
printf 'PRODUCTION_DEFAULT_FACTORY_EQUIVALENCE=PASS\n'
printf 'HANDLER_LIFECYCLE_OFFLINE=PASS\n'
printf 'FINAL_DECISION_SET_SHA=%s\n' "$FINAL_DECISION_SET_SHA"
printf 'SLACK_DECISION_RECORD_SHA=%s\n' "$SLACK_DECISION_RECORD_SHA"
printf 'REREVIEW_VALIDATION_SHA=%s\n' "$REREVIEW_VALIDATION_SHA"
printf 'APPROVAL_VERBATIM_SHA=%s\n' "$APPROVAL_VERBATIM_SHA"
printf 'REREVIEW_EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'PRODUCTION_MANIFEST_UPDATE_ALLOWED=false\n'
printf 'PRODUCTION_DB_ACCESS_ALLOWED=false\n'
printf 'PRODUCTION_MIGRATION_ALLOWED=false\n'
printf 'DEPLOYMENT_ALLOWED=false\n'
printf 'SLACK_WORKER_START_ALLOWED=false\n'
printf 'RUNTIME_EXECUTION_ALLOWED=false\n'
printf 'EXTERNAL_NETWORK_ALLOWED=false\n'
printf 'PRIOR_DECISION_RESULT_CHANGED=false\n'
printf 'PRIOR_DECISION_SET_CHANGED=false\n'
printf 'SLACK_TEST_RESULT_CHANGED=false\n'
printf 'SLACK_TEST_SUMMARY_CHANGED=false\n'
printf 'SLACK_SOURCE_CHANGED=false\n'
printf 'WORKFLOW_SOURCE_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'SLACK_WORKER_STARTED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'UNIT_DB_SAFETY_STATUS=APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION\n'
printf 'UNIT_WORKFLOW_STATE_STATUS=APPROVED_WITH_CONDITIONS_REVIEW_ONLY_HOLD_FOR_PRODUCTION\n'
printf 'UNIT_SLACK_RUNTIME_STATUS=APPROVED_REVIEW_ONLY_HOLD_FOR_PRODUCTION\n'
printf 'NEXT_GATE=PRODUCTION_RELEASE_REMAINS_EXPLICITLY_UNAPPROVED\n'
printf 'SCRIPT_EXIT_CODE=0\n'
