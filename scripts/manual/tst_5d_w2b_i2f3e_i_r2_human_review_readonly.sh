#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

EVIDENCE_REL="${BASE_REL}/i2f3e-i-r2-cron-canonical-disambiguation-packet-correction-20260725T153249Z-513165"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
REVIEW_OUT="/tmp/tst_5d_w2b_i2f3e_i_r2_human_review.txt"

EXPECTED_RESULT_SHA="9f4949bb37b2c00cdce49aa99c64acb9f503c63403ee74450da444369161b7b4"
EXPECTED_PACKET_MANIFEST_SHA="53f70a4d969607fd8d9c3e572ee5319dd8e7c18dbc10150011695a921c89404c"
EXPECTED_SEMANTIC_SHA="f7e3e5bfef6ce7a4fa29f6eb5661cbfd408d66c914d42418a4a5a2dbbc17f023"
EXPECTED_EVIDENCE_MANIFEST_SHA="01ca5ac90336d9bd88f922299bd87e4cc293ddde99debd48f21027d85f7e3339"

cd "$REPO_ROOT"

(
  set -Eeuo pipefail

  printf '\n===== REQUIRED FILES =====\n'

  required_files=(
    "result.json"
    "evidence-manifest.txt"
    "packet-snapshot/packet-manifest.json"
    "packet-snapshot/packet-semantic-validation.json"
    "packet-snapshot/current-crontab-redacted-inventory.json"
    "packet-snapshot/canonical-cron-disambiguation.json"
    "packet-snapshot/corrected-cron-window-control-plan.json"
    "packet-snapshot/corrected-execution-eligibility.json"
    "packet-snapshot/input-provenance-and-correction-record.json"
    "packet-snapshot/protected-sha-before.json"
    "packet-snapshot/protected-sha-after.json"
    "packet-snapshot/human-approval-verbatim.txt"
  )

  for name in "${required_files[@]}"; do
    test -f "$EVIDENCE_ROOT/$name"
    printf 'FILE_PRESENT=%s\n' "$name"
  done

  printf '\n===== FIXED SHA CHECK =====\n'

  echo "$EXPECTED_RESULT_SHA  $EVIDENCE_ROOT/result.json" \
    | sha256sum -c -

  echo "$EXPECTED_PACKET_MANIFEST_SHA  $PACKET_ROOT/packet-manifest.json" \
    | sha256sum -c -

  echo "$EXPECTED_SEMANTIC_SHA  $PACKET_ROOT/packet-semantic-validation.json" \
    | sha256sum -c -

  echo "$EXPECTED_EVIDENCE_MANIFEST_SHA  $EVIDENCE_ROOT/evidence-manifest.txt" \
    | sha256sum -c -

  printf '\n===== SEMANTIC REVIEW =====\n'

  python3 - "$EVIDENCE_ROOT" <<'PY'
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path(sys.argv[1]).resolve()
packet = root / "packet-snapshot"

EXPECTED_TARGETS = {
    "WP_DRAFT_PREPUBLISH_REPORT": {
        "sha256": "e9610d7384a37b85a2e04e3a36b776ca64e9fae9eff29d3bf38884feea1f2810",
        "schedule": "0 2 * * *",
        "classification": "WINDOW_CONTROL_ONLY",
        "tokens": [
            "/home/deploy/ai_media_os",
            "tools/check_wp_draft_prepublish.py",
        ],
    },
    "PHASE2_OBSERVATION_REPORT": {
        "sha256": "218fd6ba09b9bc0d425d5398d29cf940f89dfa46c983a3bc1c405bf71b4d5b18",
        "schedule": "0 9 * * *",
        "classification": "WINDOW_CONTROL_ONLY",
        "tokens": [
            "/home/deploy/ai_media_os",
            "tools/report_phase2_observation.py",
        ],
    },
    "AI_POST_QUEUE": {
        "sha256": "967688ce82407c8401af2f7eaa9e0b575cce55a8f21c07c97f2fee5e1a615fda",
        "schedule": "10 8 * * *",
        "classification": "WINDOW_CONTROL_ONLY",
        "tokens": [
            "/home/deploy/ai_media_os",
            "scripts/run_ai_post_queue.sh",
        ],
    },
}

EXPECTED_EXCLUDED = {
    "target_id": "AUTO_SYSTEM_EBOOK_AFFILIATE_BLOCK",
    "sha256": "5aae2b90052415f1408a16fb31e7bb763a337b3dad14856d1c436f8fdf3132a0",
    "schedule": "0 9 * * *",
    "classification": "NOT_RELEVANT",
    "tokens": [
        "/opt/auto-system",
        "runner/run_block.py",
        "ebook_affiliate",
    ],
}

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value

result = load(root / "result.json")
manifest = load(packet / "packet-manifest.json")
semantic = load(packet / "packet-semantic-validation.json")
inventory = load(packet / "current-crontab-redacted-inventory.json")
canonical = load(packet / "canonical-cron-disambiguation.json")
window = load(packet / "corrected-cron-window-control-plan.json")
eligibility = load(packet / "corrected-execution-eligibility.json")
provenance = load(packet / "input-provenance-and-correction-record.json")
before = load(packet / "protected-sha-before.json")
after = load(packet / "protected-sha-after.json")

assert result["phase"] == "TST-5D-W2B-I2F-3E-I-R2"
assert result["result"] == (
    "PASS_W2B_I2F3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET_CORRECTED_NO_EXECUTION"
)
assert result["source_i_r1_ambiguity"] == (
    "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
)
assert result["current_active_cron_line_count"] == 11
assert result["expected_relevant_cron_job_count"] == 3
assert result["resolved_relevant_cron_job_count"] == 3
assert result["all_expected_targets_resolved"] is True
assert result["excluded_candidate_proven_not_relevant"] is True
assert result["cron_relevant_job_selection"] == "RESOLVED"
assert result["cron_control_method"] == "SCHEDULE_AVOIDANCE_ONLY"
assert result["cron_execution_control_resolved"] is True
assert result["candidate_safe_window_available"] is True
assert result["execution_eligibility"] is True
assert result["execution_eligibility_status"] == (
    "READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
)
assert result["maximum_writer_freeze_seconds"] == 600
assert result["guard_before_seconds"] == 300
assert result["guard_after_seconds"] == 300
assert result["restart_profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert result["wordpress_external_actions_after_restart"] == "HOLD"
assert result["full_operational_parity_after_restart"] == "NOT_ESTABLISHED"
assert result["raw_crontab_saved"] is False
assert result["crontab_secret_values_saved"] is False
assert result["writer_freeze_execution"] == "HOLD"
assert result["production_release_decision"] == "HOLD"
assert result["release_status"] == "CANDIDATE_NOT_APPROVED"
assert result["next_gate"] == (
    "HUMAN_REVIEW_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET"
)

assert semantic["result"] == (
    "PASS_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_AND_PACKET_CORRECTION_READONLY_NO_EXECUTION"
)
assert semantic["source_i_r1_ambiguity"] == (
    "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
)
assert semantic["expected_relevant_cron_job_count"] == 3
assert semantic["resolved_relevant_cron_job_count"] == 3
assert semantic["all_expected_targets_resolved"] is True
assert semantic["excluded_candidate_proven_not_relevant"] is True
assert semantic["cron_relevant_job_selection"] == "RESOLVED"
assert semantic["schedule_only_match_used"] is False
assert semantic["cron_control_method"] == "SCHEDULE_AVOIDANCE_ONLY"
assert semantic["cron_execution_control_resolved"] is True
assert semantic["candidate_safe_window_available"] is True
assert semantic["execution_eligibility"] is True
assert semantic["execution_eligibility_status"] == (
    "READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
)
assert semantic["raw_crontab_saved"] is False
assert semantic["crontab_secret_values_saved"] is False
assert semantic["protected_sha_unchanged"] is True
assert semantic["writer_freeze_execution"] == "HOLD"

assert inventory["raw_crontab_saved"] is False
assert inventory["secret_values_saved"] is False
assert inventory["active_line_count"] == 11
assert inventory["crontab_changed"] is False
assert len(inventory["active_lines"]) == 11
for line in inventory["active_lines"]:
    assert line["raw_line_saved"] is False
    assert "line_sha256" in line
    assert "redacted_normalized_line" in line
    assert "redacted_normalized_command" in line

assert canonical["source_i_r1_ambiguity"] == (
    "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
)
assert canonical["source_i_r1_matched_candidate_count"] == 11
assert canonical["expected_relevant_cron_job_count"] == 3
assert canonical["historical_window_control_only_count"] == 3
assert canonical["all_expected_targets_resolved"] is True
assert canonical["excluded_candidate_proven_not_relevant"] is True
assert canonical["cron_relevant_job_selection"] == "RESOLVED"
assert canonical["schedule_only_match_used"] is False
assert canonical["raw_crontab_saved"] is False
assert canonical["secret_values_saved"] is False
assert len(canonical["target_resolutions"]) == 3

seen_target_ids = set()
selected_hashes = set()

for target in canonical["target_resolutions"]:
    target_id = target["target_id"]
    expected = EXPECTED_TARGETS[target_id]
    seen_target_ids.add(target_id)

    assert target["expected_sha256"] == expected["sha256"]
    assert target["expected_schedule"] == expected["schedule"]
    assert target["expected_classification"] == expected["classification"]
    assert target["current_match_count"] == 1
    assert target["historical_match_count"] == 1
    assert target["resolved"] is True
    assert target["schedule_only_match_forbidden"] is True
    assert target["raw_command_saved"] is False
    assert target["secret_values_saved"] is False

    current = target["current_match"]
    historical = target["historical_match"]

    assert current["line_sha256"] == expected["sha256"]
    assert current["schedule"] == expected["schedule"]
    assert current["raw_line_saved"] is False

    for token in expected["tokens"]:
        assert token in current["redacted_normalized_line"]
        assert token in historical["redacted_identity_text"]

    assert historical["classification"] == expected["classification"]
    assert historical["schedule"] == expected["schedule"]
    selected_hashes.add(current["line_sha256"])

assert seen_target_ids == set(EXPECTED_TARGETS)
assert len(selected_hashes) == 3

excluded = canonical["excluded_candidate_resolution"]
assert excluded["target_id"] == EXPECTED_EXCLUDED["target_id"]
assert excluded["expected_sha256"] == EXPECTED_EXCLUDED["sha256"]
assert excluded["expected_schedule"] == EXPECTED_EXCLUDED["schedule"]
assert excluded["expected_classification"] == EXPECTED_EXCLUDED["classification"]
assert excluded["current_match_count"] == 1
assert excluded["historical_match_count"] == 1
assert excluded["resolved"] is True
assert excluded["current_match"]["line_sha256"] == EXPECTED_EXCLUDED["sha256"]
assert excluded["historical_match"]["classification"] == "NOT_RELEVANT"
for token in EXPECTED_EXCLUDED["tokens"]:
    assert token in excluded["current_match"]["redacted_normalized_line"]
    assert token in excluded["historical_match"]["redacted_identity_text"]

assert window["timezone"] == "Asia/Tokyo"
assert window["selected_target_count"] == 3
assert set(window["selected_schedules"]) == {
    "0 2 * * *",
    "0 9 * * *",
    "10 8 * * *",
}
assert set(window["selected_line_sha256"]) == selected_hashes
assert window["cron_relevant_job_selection"] == "RESOLVED"
assert window["candidate_safe_window"] is not None
assert window["shared_lock_tokens"] == []
assert window["control_method"] == "SCHEDULE_AVOIDANCE_ONLY"
assert window["execution_control_resolved"] is True
assert window["maximum_writer_freeze_seconds"] == 600
assert window["guard_before_seconds"] == 300
assert window["guard_after_seconds"] == 300
assert window["raw_crontab_saved"] is False
assert window["secret_values_saved"] is False
assert window["crontab_changed"] is False
assert window["writer_freeze_execution"] == "HOLD"

safe = window["candidate_safe_window"]
assert safe == result["candidate_safe_window"]
assert safe["timezone"] == "Asia/Tokyo"
assert safe["max_freeze_seconds"] == 600
assert safe["guard_before_seconds"] == 300
assert safe["guard_after_seconds"] == 300
assert safe["conflicting_event_count"] == 0

tz = ZoneInfo("Asia/Tokyo")
freeze_start = dt.datetime.fromisoformat(safe["candidate_freeze_start"])
freeze_end = dt.datetime.fromisoformat(safe["candidate_freeze_end"])
guard_start = dt.datetime.fromisoformat(safe["guarded_interval_start"])
guard_end = dt.datetime.fromisoformat(safe["guarded_interval_end"])
now = dt.datetime.now(tz)

assert freeze_start.tzinfo is not None
assert freeze_end - freeze_start == dt.timedelta(seconds=600)
assert freeze_start - guard_start == dt.timedelta(seconds=300)
assert guard_end - freeze_end == dt.timedelta(seconds=300)

if now < guard_start:
    window_state = "FUTURE"
elif guard_start <= now <= guard_end:
    window_state = "ACTIVE_REFERENCE_WINDOW"
else:
    window_state = "EXPIRED"

assert eligibility["source_i_r1_execution_eligibility"] is False
assert eligibility["source_i_r1_execution_eligibility_status"] == (
    "BLOCKED_PENDING_CONDITION_RESOLUTION"
)
assert eligibility["source_i_r1_ambiguity"] == (
    "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
)
assert eligibility["cron_relevant_job_selection"] == "RESOLVED"
assert eligibility["cron_control_method"] == "SCHEDULE_AVOIDANCE_ONLY"
assert eligibility["cron_execution_control_resolved"] is True
assert eligibility["candidate_safe_window_available"] is True
assert eligibility["execution_eligibility"] is True
assert eligibility["execution_eligibility_status"] == (
    "READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
)
assert eligibility["execution_allowed"] is False
assert eligibility["restart_profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert eligibility["wordpress_external_actions_after_restart"] == "HOLD"
assert eligibility["full_operational_parity_after_restart"] == (
    "NOT_ESTABLISHED"
)
assert eligibility["writer_freeze_execution"] == "HOLD"

assert provenance["original_ambiguity"] == (
    "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
)
assert provenance["correction_method"] == (
    "CANONICAL_SCHEDULE_PLUS_COMMAND_PATH_PLUS_NORMALIZED_LINE_SHA256"
)
assert provenance["source_evidence_mutated"] is False
assert provenance["raw_crontab_saved"] is False
assert provenance["secret_values_saved"] is False

assert before["files"] == after["files"]

execution = result["execution"]
false_keys = [
    "process_signal_sent",
    "writer_stop_performed",
    "gui_stopped_or_restarted",
    "crontab_changed",
    "timer_changed",
    "systemd_changed",
    "production_database_opened",
    "production_database_sql_connection_used",
    "sql_executed",
    "backup_created",
    "restore_executed",
    "migration_executed",
    "production_manifest_modified",
    "source_modified",
    "test_modified",
    "git_add_performed",
    "git_commit_performed",
    "deployment_performed",
    "external_network_used",
    "slack_worker_started",
    "production_approval_created",
    "production_release_approved",
]
for key in false_keys:
    assert execution[key] is False, key

print(f"PHASE={result['phase']}")
print("SOURCE_I_R1_AMBIGUITY=AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS")
print("CRON_CANONICAL_DISAMBIGUATION_REVIEW=PASS")
print("RESOLVED_RELEVANT_CRON_JOB_COUNT=3")
print("ALL_EXPECTED_TARGETS_RESOLVED=true")
print("EXCLUDED_CANDIDATE_PROVEN_NOT_RELEVANT=true")
print("SCHEDULE_ONLY_MATCH_USED=false")
print("CRON_RELEVANT_JOB_SELECTION=RESOLVED")
print("CRON_CONTROL_METHOD=SCHEDULE_AVOIDANCE_ONLY")
print("CRON_EXECUTION_CONTROL_RESOLVED=true")
print("CANDIDATE_SAFE_WINDOW_AVAILABLE=true")
print(f"CANDIDATE_FREEZE_START={safe['candidate_freeze_start']}")
print(f"CANDIDATE_FREEZE_END={safe['candidate_freeze_end']}")
print(f"CANDIDATE_GUARDED_INTERVAL_START={safe['guarded_interval_start']}")
print(f"CANDIDATE_GUARDED_INTERVAL_END={safe['guarded_interval_end']}")
print(f"CANDIDATE_WINDOW_STATE_AT_REVIEW={window_state}")
print("CANDIDATE_WINDOW_EXECUTION_AUTHORITY=false")
print("FRESH_WINDOW_RECOMPUTE_REQUIRED_BEFORE_EXECUTION=true")
print("EXECUTION_ELIGIBILITY=true")
print("EXECUTION_ELIGIBILITY_STATUS=READY_FOR_HUMAN_REVIEW_NOT_EXECUTION")
print("EXECUTION_ALLOWED=false")
print("MAXIMUM_WRITER_FREEZE_SECONDS=600")
print("CRON_GUARD_BEFORE_SECONDS=300")
print("CRON_GUARD_AFTER_SECONDS=300")
print("RESTART_PROFILE=SAFE_MINIMAL_MAINTENANCE_MODE")
print("WORDPRESS_EXTERNAL_ACTIONS_AFTER_RESTART=HOLD")
print("FULL_OPERATIONAL_PARITY_AFTER_RESTART=NOT_ESTABLISHED")
print("RAW_CRONTAB_SAVED=false")
print("CRONTAB_SECRET_VALUES_SAVED=false")
print("PROTECTED_SHA_BEFORE_AFTER_EQUAL=true")
print("SAFETY_BOUNDARY_VALID=true")
PY

  printf '\n===== RESOLVED CRON TARGETS =====\n'

  python3 - "$PACKET_ROOT/canonical-cron-disambiguation.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

for target in sorted(
    payload["target_resolutions"],
    key=lambda item: item["target_id"],
):
    current = target["current_match"]
    historical = target["historical_match"]

    print(f"TARGET_ID={target['target_id']}")
    print(f"TARGET_LINE_SHA256={current['line_sha256']}")
    print(f"TARGET_SCHEDULE={current['schedule']}")
    print(
        "TARGET_REDACTED_LINE="
        + current["redacted_normalized_line"]
    )
    print(
        "HISTORICAL_CLASSIFICATION="
        + historical["classification"]
    )
    print(
        "HISTORICAL_INDEX="
        + str(historical["historical_index"])
    )
    print("CURRENT_MATCH_COUNT=1")
    print("HISTORICAL_MATCH_COUNT=1")
    print("TARGET_RESOLVED=true")
    print("---")

excluded = payload["excluded_candidate_resolution"]
print(f"EXCLUDED_TARGET_ID={excluded['target_id']}")
print(
    "EXCLUDED_LINE_SHA256="
    + excluded["current_match"]["line_sha256"]
)
print(
    "EXCLUDED_SCHEDULE="
    + excluded["current_match"]["schedule"]
)
print(
    "EXCLUDED_REDACTED_LINE="
    + excluded["current_match"]["redacted_normalized_line"]
)
print(
    "EXCLUDED_HISTORICAL_CLASSIFICATION="
    + excluded["historical_match"]["classification"]
)
print("EXCLUDED_CANDIDATE_RESOLVED=true")
print("RAW_COMMAND_SAVED=false")
print("SECRET_VALUES_SAVED=false")
PY

  printf '\n===== PACKET MANIFEST CHECK =====\n'

  python3 - "$PACKET_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
manifest = json.loads(
    (root / "packet-manifest.json").read_text(encoding="utf-8")
)

assert manifest["packet_file_count_excluding_manifest"] == 9
assert len(manifest["packet_files"]) == 9
assert manifest["source_i_r1_ambiguity"] == (
    "AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS"
)
assert manifest["cron_relevant_job_selection"] == "RESOLVED"
assert manifest["cron_control_method"] == "SCHEDULE_AVOIDANCE_ONLY"
assert manifest["cron_execution_control_resolved"] is True
assert manifest["execution_eligibility"] is True
assert manifest["execution_eligibility_status"] == (
    "READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
)
assert manifest["writer_freeze_execution"] == "HOLD"
assert manifest["production_release_decision"] == "HOLD"
assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"
assert manifest["next_gate"] == (
    "HUMAN_REVIEW_3E_I_R2_CRON_CANONICAL_DISAMBIGUATION_PACKET"
)

expected_names = {
    item["name"] for item in manifest["packet_files"]
}
actual_names = {
    path.name
    for path in root.iterdir()
    if path.is_file() and path.name != "packet-manifest.json"
}
assert expected_names == actual_names

for item in manifest["packet_files"]:
    artifact = root / item["name"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

print("PACKET_MANIFEST_FILE_SET_VALID=true")
print("PACKET_MANIFEST_SHA_AND_SIZE_VALID=true")
print("PACKET_FILE_COUNT_EXCLUDING_MANIFEST=9")
print("PACKET_FILE_COUNT=10")
PY

  printf '\n===== EVIDENCE MANIFEST CHECK =====\n'

  python3 - "$EVIDENCE_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
manifest = root / "evidence-manifest.txt"
entries = {}

for line in manifest.read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    assert relative not in entries
    entries[relative] = expected

actual = {
    path.relative_to(root).as_posix()
    for path in root.rglob("*")
    if path.is_file() and path != manifest
}
assert set(entries) == actual

for relative, expected in entries.items():
    artifact = root / relative
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == expected

print(f"EVIDENCE_MANIFEST_ENTRY_COUNT={len(entries)}")
print("EVIDENCE_MANIFEST_CONTENT_VALID=true")
PY

  printf '\n===== OWNER / MODE CHECK =====\n'

  python3 - "$EVIDENCE_ROOT" <<'PY'
from __future__ import annotations

import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
repo = Path("/home/deploy/ai_media_os")
expected_uid = repo.stat().st_uid
expected_gid = repo.stat().st_gid

assert stat.S_IMODE(root.stat().st_mode) == 0o555
assert root.stat().st_uid == expected_uid
assert root.stat().st_gid == expected_gid

files = 0
directories = 1

for path in root.rglob("*"):
    metadata = path.lstat()

    assert not stat.S_ISLNK(metadata.st_mode), path
    assert metadata.st_uid == expected_uid, path
    assert metadata.st_gid == expected_gid, path

    if path.is_file():
        assert stat.S_IMODE(metadata.st_mode) == 0o444, path
        files += 1
    elif path.is_dir():
        assert stat.S_IMODE(metadata.st_mode) == 0o555, path
        directories += 1
    else:
        raise AssertionError(path)

print(f"SEALED_FILE_COUNT={files}")
print(f"SEALED_DIRECTORY_COUNT={directories}")
print("ALL_EVIDENCE_FILES_MODE_0444=true")
print("ALL_EVIDENCE_DIRECTORIES_MODE_0555=true")
print("ALL_EVIDENCE_OWNED_BY_DEPLOY=true")
PY

  printf '\n===== CURRENT PROTECTED SHA =====\n'

  sha256sum \
    data/database/ebook_affiliate.db \
    config/slack_worker_release_source_manifest.json \
    app/db/repositories/workflow_state_repository.py \
    migrations/versions/00241611109d_add_unique_wordpress_post_id.py \
    scripts/run_slack_approval_socket.py \
    tests/test_slack_approval_socket_hold_remediation_offline.py

  printf '\n===== FINAL REVIEW MARKERS =====\n'

  echo "I_R2_EXECUTION_EVIDENCE_REVIEW=PASS"
  echo "I_R2_PACKET_INTEGRITY_REVIEW=PASS"
  echo "CRON_CANONICAL_DISAMBIGUATION_REVIEW=PASS"
  echo "CRON_RELEVANT_JOB_SELECTION=RESOLVED"
  echo "CRON_CONTROL_METHOD=SCHEDULE_AVOIDANCE_ONLY"
  echo "CRON_EXECUTION_CONTROL_RESOLVED=true"
  echo "EXECUTION_ELIGIBILITY=true"
  echo "EXECUTION_ELIGIBILITY_STATUS=READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
  echo "EXECUTION_ALLOWED=false"
  echo "CANDIDATE_WINDOW_EXECUTION_AUTHORITY=false"
  echo "FRESH_WINDOW_RECOMPUTE_REQUIRED_BEFORE_EXECUTION=true"
  echo "RAW_CRONTAB_SAVED=false"
  echo "CRONTAB_SECRET_VALUES_SAVED=false"
  echo "PROCESS_SIGNAL_SENT=false"
  echo "WRITER_STOP_PERFORMED=false"
  echo "GUI_STOPPED_OR_RESTARTED=false"
  echo "PRODUCTION_DB_OPENED=false"
  echo "SQL_EXECUTED=false"
  echo "BACKUP_CREATED=false"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"

) 2>&1 | tee "$REVIEW_OUT"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_OUT"
