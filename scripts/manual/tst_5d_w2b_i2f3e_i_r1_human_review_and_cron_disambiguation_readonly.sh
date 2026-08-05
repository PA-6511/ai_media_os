#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

EVIDENCE_REL="${BASE_REL}/i2f3e-i-r1-writer-freeze-backup-execution-packet-prep-20260725T151813Z-512616"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"

F1_REL="${BASE_REL}/i2f3e-f1-evidence-copy-normalization-reseal-20260725T140856Z-509951"
F1_ROOT="${REPO_ROOT}/${F1_REL}"

REVIEW_OUT="/tmp/tst_5d_w2b_i2f3e_i_r1_human_review.txt"

EXPECTED_RESULT_SHA="4ab4198efa4ba51440a355a498c004159717018e02498fbe9c6ea2d861b59439"
EXPECTED_PACKET_MANIFEST_SHA="3d3cb6a4c781ba2562af48109198cfc7d63980e671435be75796175438ba67ea"
EXPECTED_SEMANTIC_SHA="e6e6e28483015ecd4b89b66acce3d4d1f99099504dd0c02d45d9a8b3731b3835"
EXPECTED_EVIDENCE_MANIFEST_SHA="ccd021015be098a087db624a863ccbeaf28d8d200e420f089f900b849937679e"

cd "$REPO_ROOT"

(
  set -Eeuo pipefail

  printf '\n===== REQUIRED FILES =====\n'

  required_files=(
    "result.json"
    "evidence-manifest.txt"
    "packet-snapshot/packet-manifest.json"
    "packet-snapshot/packet-semantic-validation.json"
    "packet-snapshot/current-gui-identity-readonly.json"
    "packet-snapshot/cron-window-control-plan.json"
    "packet-snapshot/current-db-file-set-metadata-readonly.json"
    "packet-snapshot/future-root-post-stop-check-plan.json"
    "packet-snapshot/filesystem-backup-contract.json"
    "packet-snapshot/future-gui-stop-contract.json"
    "packet-snapshot/safe-minimal-restart-profile.json"
    "packet-snapshot/future-freeze-backup-restart-sequence.json"
    "packet-snapshot/protected-sha-before.json"
    "packet-snapshot/protected-sha-after.json"
    "packet-snapshot/human-approval-verbatim.txt"
  )

  for name in "${required_files[@]}"; do
    test -f "$EVIDENCE_ROOT/$name"
    printf 'FILE_PRESENT=%s\n' "$name"
  done

  test -f "$F1_ROOT/corrected-packet-snapshot/freeze-window-plan.json"
  test -f "$F1_ROOT/corrected-packet-snapshot/process-and-cron-attribution.json"

  printf '\n===== FIXED SHA CHECK =====\n'

  echo "$EXPECTED_RESULT_SHA  $EVIDENCE_ROOT/result.json" \
    | sha256sum -c -

  echo "$EXPECTED_PACKET_MANIFEST_SHA  $PACKET_ROOT/packet-manifest.json" \
    | sha256sum -c -

  echo "$EXPECTED_SEMANTIC_SHA  $PACKET_ROOT/packet-semantic-validation.json" \
    | sha256sum -c -

  echo "$EXPECTED_EVIDENCE_MANIFEST_SHA  $EVIDENCE_ROOT/evidence-manifest.txt" \
    | sha256sum -c -

  printf '\n===== PACKET SEMANTIC REVIEW =====\n'

  python3 - "$EVIDENCE_ROOT" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
packet = root / "packet-snapshot"

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value

result = load(root / "result.json")
manifest = load(packet / "packet-manifest.json")
semantic = load(packet / "packet-semantic-validation.json")
identity = load(packet / "current-gui-identity-readonly.json")
cron = load(packet / "cron-window-control-plan.json")
dbset = load(packet / "current-db-file-set-metadata-readonly.json")
root_plan = load(packet / "future-root-post-stop-check-plan.json")
backup = load(packet / "filesystem-backup-contract.json")
stop = load(packet / "future-gui-stop-contract.json")
restart = load(packet / "safe-minimal-restart-profile.json")
sequence = load(packet / "future-freeze-backup-restart-sequence.json")
before = load(packet / "protected-sha-before.json")
after = load(packet / "protected-sha-after.json")

assert result["phase"] == "TST-5D-W2B-I2F-3E-I-R1"
assert result["correction_label"] == "3E_E_MANIFEST_PATH_CORRECTION"
assert result["original_3e_i_result"] == "FAILED_MISSING_REQUIRED_INPUT_PATHS"
assert result["result"] == (
    "PASS_W2B_I2F3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_PREPARED_NO_EXECUTION"
)
assert result["process_state"] == "RUNNING_SINGLE_MATCH"
assert result["matching_process_count"] == 1
assert result["current_gui_pid"] == 302168
assert result["current_process_identity_sha256"] == (
    "3dcadb53adeadac94cb1062d2a4e24c2a00d63a51c87991046b96cd7f0f6ba2a"
)
assert result["current_identity_matches_g_r1"] is True
assert result["listener_owned_by_current_gui"] is True

assert result["cron_control_method"] == "UNRESOLVED"
assert result["cron_execution_control_resolved"] is False
assert result["matched_relevant_cron_job_count"] == 11
assert result["expected_relevant_cron_job_count"] == 3
assert result["execution_eligibility"] is False
assert result["execution_eligibility_status"] == (
    "BLOCKED_PENDING_CONDITION_RESOLUTION"
)

assert result["backup_copy_conditions_resolved"] is True
assert result["reserved_backup_directory_exists_now"] is False
assert result["exact_stop_route_status"] == (
    "RESOLVED_PENDING_SEPARATE_EXECUTION_APPROVAL"
)
assert result["exact_restart_route_status"] == (
    "RESOLVED_PENDING_HUMAN_REVIEW"
)
assert result["maximum_writer_freeze_seconds"] == 600
assert result["restart_profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert result["wordpress_external_actions_after_restart"] == "HOLD"
assert result["full_operational_parity_after_restart"] == "NOT_ESTABLISHED"
assert result["writer_freeze_execution"] == "HOLD"
assert result["production_release_decision"] == "HOLD"
assert result["release_status"] == "CANDIDATE_NOT_APPROVED"

assert semantic["result"] == (
    "PASS_3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_PREPARATION_NO_EXECUTION"
)
assert semantic["cron_control_method"] == "UNRESOLVED"
assert semantic["cron_execution_control_resolved"] is False
assert semantic["matched_relevant_cron_job_count"] == 11
assert semantic["expected_relevant_cron_job_count"] == 3
assert semantic["backup_copy_conditions_resolved"] is True
assert semantic["execution_eligibility"] is False
assert semantic["execution_eligibility_status"] == (
    "BLOCKED_PENDING_CONDITION_RESOLUTION"
)
assert semantic["writer_freeze_execution"] == "HOLD"

assert identity["process_state"] == "RUNNING_SINGLE_MATCH"
assert identity["matching_process_count"] == 1
assert identity["identity_matches_prior"] is True
assert identity["listener_inventory"]["target_pid_owned"] is True
assert identity["process_signal_sent"] is False
assert identity["gui_stopped_or_restarted"] is False

assert cron["raw_crontab_saved"] is False
assert cron["secret_values_saved"] is False
assert cron["expected_relevant_cron_job_count"] == 3
assert cron["matched_relevant_cron_job_count"] == 11
assert len(cron["relevant_jobs"]) == 11
assert cron["control_method"] == "UNRESOLVED"
assert cron["execution_control_resolved"] is False
assert cron["candidate_safe_window"] is None
assert cron["crontab_changed"] is False
assert cron["writer_freeze_execution"] == "HOLD"

assert dbset["status"] == "INFORMATIONAL_PRE_FREEZE_NOT_BACKUP_SOURCE"
assert dbset["db_sha_verified"] is True
assert dbset["production_database_sql_connection_used"] is False
assert dbset["sql_executed"] is False

assert root_plan["status"] == "PLAN_ONLY_NOT_EXECUTED"
assert root_plan["execution_allowed"] is False
assert root_plan["requires_root"] is True
assert root_plan["future_result_requirement"]["root_open_handle_count"] == 0
assert root_plan["future_result_requirement"]["sql_executed"] is False

assert backup["status"] == "PLAN_ONLY_NOT_EXECUTED"
assert backup["execution_allowed"] is False
assert backup["backup_method"] == "FROZEN_FILESYSTEM_COPY_NO_SQL_CONNECTION"
assert backup["reserved_directory_exists_now"] is False
assert backup["sql_connection_used"] is False
assert backup["backup_created_now"] is False

assert stop["status"] == "RESOLVED_PENDING_SEPARATE_EXECUTION_APPROVAL"
assert stop["execution_allowed"] is False
assert stop["method"] == "SIGTERM_TO_EXACT_PID_AFTER_IDENTITY_REVALIDATION"
assert stop["max_wait_seconds"] == 30
assert stop["sigkill_allowed"] is False
assert stop["writer_stop_performed_now"] is False
assert stop["process_signal_sent_now"] is False

assert restart["profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert restart["execution_allowed"] is False
assert restart["wordpress_external_actions_after_restart"] == "HOLD"
assert restart["full_operational_parity_after_restart"] == "NOT_ESTABLISHED"

assert sequence["status"] == "BLOCKED_PENDING_CONDITION_RESOLUTION"
assert sequence["execution_allowed"] is False
assert sequence["maximum_writer_freeze_seconds"] == 600
assert sequence["automatic_retry_allowed"] is False
assert sequence["automatic_restore_allowed"] is False
assert sequence["separate_execution_approval_required"] is True
assert sequence["separate_restore_approval_required"] is True
assert sequence["writer_freeze_execution"] == "HOLD"

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
print(f"CURRENT_GUI_PID={result['current_gui_pid']}")
print(f"PROCESS_IDENTITY_SHA={result['current_process_identity_sha256']}")
print("GUI_IDENTITY_AND_LISTENER_REVIEW=PASS")
print("CRON_CONTROL_METHOD=UNRESOLVED")
print("CRON_EXECUTION_CONTROL_RESOLVED=false")
print("MATCHED_RELEVANT_CRON_JOB_COUNT=11")
print("EXPECTED_RELEVANT_CRON_JOB_COUNT=3")
print("CRON_SELECTION_STATUS=AMBIGUOUS_11_CANDIDATES_FOR_3_TARGETS")
print("BACKUP_COPY_CONDITIONS_REVIEW=PASS_PLAN_ONLY")
print("EXACT_STOP_ROUTE_REVIEW=PASS_PLAN_ONLY")
print("EXACT_RESTART_ROUTE_REVIEW=PASS_PLAN_ONLY")
print("EXECUTION_ELIGIBILITY=false")
print("EXECUTION_ELIGIBILITY_STATUS=BLOCKED_PENDING_CONDITION_RESOLUTION")
print("MAXIMUM_WRITER_FREEZE_SECONDS=600")
print("RESTART_PROFILE=SAFE_MINIMAL_MAINTENANCE_MODE")
print("WORDPRESS_EXTERNAL_ACTIONS_AFTER_RESTART=HOLD")
print("FULL_OPERATIONAL_PARITY_AFTER_RESTART=NOT_ESTABLISHED")
print("PROTECTED_SHA_BEFORE_AFTER_EQUAL=true")
print("SAFETY_BOUNDARY_VALID=true")
PY

  printf '\n===== REDACTED CRON CANDIDATES: 11 =====\n'

  python3 - "$PACKET_ROOT/cron-window-control-plan.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
jobs = payload["relevant_jobs"]

assert len(jobs) == 11

for index, job in enumerate(jobs, start=1):
    print(f"CRON_CANDIDATE_INDEX={index}")
    print(f"CRON_CANDIDATE_SHA256={job['raw_line_sha256']}")
    print(f"CRON_CANDIDATE_SCHEDULE={job['schedule']}")
    print(f"CRON_CANDIDATE_REDACTED_COMMAND={job['redacted_command']}")
    print(f"CRON_CANDIDATE_REDACTED_LINE={job['redacted_normalized_line']}")
    print("---")

print("RAW_CRONTAB_SAVED=false")
print("CRONTAB_SECRET_VALUES_SAVED=false")
print("CRON_CANDIDATE_COUNT=11")
PY

  printf '\n===== HISTORICAL CRON ATTRIBUTION SUMMARY =====\n'

  python3 - \
    "$F1_ROOT/corrected-packet-snapshot/freeze-window-plan.json" \
    "$F1_ROOT/corrected-packet-snapshot/process-and-cron-attribution.json" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

freeze_path = Path(sys.argv[1])
attribution_path = Path(sys.argv[2])

secret_assignment_re = re.compile(
    r"(?i)(token|password|passwd|secret|credential|private[_-]?key|"
    r"api[_-]?key|access[_-]?key|cookie|authorization|bearer)"
    r"(\s*[:=]\s*)([^\s]+)"
)
url_credential_re = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@"
)

def redact(value: str) -> str:
    value = secret_assignment_re.sub(
        lambda m: f"{m.group(1)}{m.group(2)}<REDACTED>",
        value,
    )
    value = url_credential_re.sub(
        lambda m: f"{m.group(1)}<REDACTED>:<REDACTED>@",
        value,
    )
    return value[:1000]

def walk(value: Any, path: str = "$") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_lower = key.lower()
            if isinstance(child, (str, int, float, bool)) or child is None:
                if any(
                    token in key_lower
                    for token in (
                        "cron",
                        "job",
                        "schedule",
                        "writer",
                        "window",
                        "classification",
                        "count",
                        "freeze",
                    )
                ):
                    rows.append((child_path, redact(str(child))))
            rows.extend(walk(child, child_path))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(walk(child, f"{path}[{index}]"))

    return rows

freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
attribution = json.loads(attribution_path.read_text(encoding="utf-8"))

print("FREEZE_WINDOW_PLAN_RELEVANT_FIELDS_BEGIN")
for path, value in walk(freeze):
    print(f"{path}={value}")
print("FREEZE_WINDOW_PLAN_RELEVANT_FIELDS_END")

print("PROCESS_AND_CRON_ATTRIBUTION_RELEVANT_FIELDS_BEGIN")
for path, value in walk(attribution):
    print(f"{path}={value}")
print("PROCESS_AND_CRON_ATTRIBUTION_RELEVANT_FIELDS_END")

print("HISTORICAL_SECRET_VALUES_PRINTED=false")
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

assert manifest["packet_file_count_excluding_manifest"] == 12
assert len(manifest["packet_files"]) == 12
assert manifest["cron_control_method"] == "UNRESOLVED"
assert manifest["execution_eligibility"] is False
assert manifest["execution_eligibility_status"] == (
    "BLOCKED_PENDING_CONDITION_RESOLUTION"
)
assert manifest["writer_freeze_execution"] == "HOLD"
assert manifest["production_release_decision"] == "HOLD"
assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"

expected_names = {item["name"] for item in manifest["packet_files"]}
actual_names = {
    path.name
    for path in root.iterdir()
    if path.is_file() and path.name != "packet-manifest.json"
}
assert expected_names == actual_names

for item in manifest["packet_files"]:
    path = root / item["name"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert path.stat().st_size == item["size_bytes"]

print("PACKET_MANIFEST_FILE_SET_VALID=true")
print("PACKET_MANIFEST_SHA_AND_SIZE_VALID=true")
print("PACKET_FILE_COUNT_EXCLUDING_MANIFEST=12")
print("PACKET_FILE_COUNT=13")
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
    path = root / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected

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

  echo "I_R1_EXECUTION_EVIDENCE_REVIEW=PASS_WITH_CRON_HOLD"
  echo "I_R1_PACKET_INTEGRITY_REVIEW=PASS"
  echo "GUI_IDENTITY_AND_LISTENER_REVIEW=PASS"
  echo "BACKUP_CONTRACT_REVIEW=PASS_PLAN_ONLY"
  echo "EXACT_STOP_ROUTE_REVIEW=PASS_PLAN_ONLY"
  echo "EXACT_RESTART_ROUTE_REVIEW=PASS_PLAN_ONLY"
  echo "CRON_RELEVANT_JOB_SELECTION_REVIEW=HOLD_AMBIGUOUS_11_OF_3"
  echo "CRON_EXECUTION_CONTROL_RESOLVED=false"
  echo "EXECUTION_ELIGIBILITY=false"
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
