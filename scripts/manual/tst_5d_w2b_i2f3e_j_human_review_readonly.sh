#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

EVIDENCE_REL="${BASE_REL}/i2f3e-j-runner-preparation-blocked-no-execution-20260725T155845Z-514350"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
LOG_ROOT="${EVIDENCE_ROOT}/validation-logs"

REVIEW_OUT="/tmp/tst_5d_w2b_i2f3e_j_human_review.txt"

EXPECTED_RESULT_SHA="18f40a9a4b81b5613c4ad8fb39cf6c9e13fff74a289d392d1f542e89c1f40c9d"
EXPECTED_PACKET_MANIFEST_SHA="9d1b47df30b8bf1cba1793192e3c9603aa8e3643bc728cf0756d0f724aa2a794"
EXPECTED_SEMANTIC_SHA="dc158bb774f653698565e314d4ca30ebacede2cc26a28ddb108710d0368b778e"
EXPECTED_EVIDENCE_MANIFEST_SHA="7ae5783d4ba62360fb25c8052b1669a47283de98416786d6d2b4658a75703fb4"

EXPECTED_CANDIDATE_MANIFEST_SHA="90389e95ed6c33b3bb6de100261620fe4ce7b9fd5f9dbd650296a89f42d6e066"
EXPECTED_RUNNER_SHA="58afe2824f10b6255e3f5be1e2138475fe3ba4b351a76120d2abbe8c63e7f920"
EXPECTED_ROOT_HELPER_SHA="a4e3cd04a17fce10d46d5869a66b916b5a2ab81df92c7da15f4e9155f8f272d6"
EXPECTED_VALIDATOR_SHA="0a4b610a8f16483bb91318b028aa27d9cf0e6600e9b8a64f7b50f5b3941ff019"
EXPECTED_NEGATIVE_TEST_SHA="26666d68bdb2b2a6f5600223a7a13d367c2daa6344a2b86b5d655761ba6d9d8a"
EXPECTED_POLICY_SHA="b36421be9271296e1e9712b93a76bffee526526dfb482fa348da12cd9d63ecee"
EXPECTED_MANUAL_SHA="ed1c1596826f6117871eb51ac71a896a09ea57ddaf7ce1e07acbaf257d1366bb"

cd "$REPO_ROOT"

(
  set -Eeuo pipefail

  printf '\n===== REQUIRED FILES =====\n'

  required_files=(
    "result.json"
    "evidence-manifest.txt"
    "packet-snapshot/packet-manifest.json"
    "packet-snapshot/packet-semantic-validation.json"
    "packet-snapshot/preparation-summary.json"
    "packet-snapshot/human-approval-verbatim.txt"
    "packet-snapshot/candidate-artifacts/candidate-manifest.json"
    "packet-snapshot/candidate-artifacts/one_shot_writer_freeze_backup_restart_runner.py"
    "packet-snapshot/candidate-artifacts/root_fd_metadata_helper.py"
    "packet-snapshot/candidate-artifacts/validate_3e_j_runner_packet.py"
    "packet-snapshot/candidate-artifacts/test_3e_j_runner_negative.py"
    "packet-snapshot/candidate-artifacts/runner-policy.json"
    "packet-snapshot/candidate-artifacts/3e_j_operation_manual.md"
    "validation-logs/python-compile.log"
    "validation-logs/validator.log"
    "validation-logs/negative-tests.log"
    "validation-logs/runner-self-check.log"
    "validation-logs/protected-sha-after.log"
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

  echo "$EXPECTED_CANDIDATE_MANIFEST_SHA  $CANDIDATE_ROOT/candidate-manifest.json" \
    | sha256sum -c -

  echo "$EXPECTED_RUNNER_SHA  $CANDIDATE_ROOT/one_shot_writer_freeze_backup_restart_runner.py" \
    | sha256sum -c -

  echo "$EXPECTED_ROOT_HELPER_SHA  $CANDIDATE_ROOT/root_fd_metadata_helper.py" \
    | sha256sum -c -

  echo "$EXPECTED_VALIDATOR_SHA  $CANDIDATE_ROOT/validate_3e_j_runner_packet.py" \
    | sha256sum -c -

  echo "$EXPECTED_NEGATIVE_TEST_SHA  $CANDIDATE_ROOT/test_3e_j_runner_negative.py" \
    | sha256sum -c -

  echo "$EXPECTED_POLICY_SHA  $CANDIDATE_ROOT/runner-policy.json" \
    | sha256sum -c -

  echo "$EXPECTED_MANUAL_SHA  $CANDIDATE_ROOT/3e_j_operation_manual.md" \
    | sha256sum -c -

  printf '\n===== PREPARATION / PACKET REVIEW =====\n'

  python3 - "$EVIDENCE_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
packet = root / "packet-snapshot"
candidate = packet / "candidate-artifacts"
logs = root / "validation-logs"

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

result = load(root / "result.json")
manifest = load(packet / "packet-manifest.json")
semantic = load(packet / "packet-semantic-validation.json")
summary = load(packet / "preparation-summary.json")
candidate_manifest = load(candidate / "candidate-manifest.json")
policy = load(candidate / "runner-policy.json")

assert result["phase"] == "TST-5D-W2B-I2F-3E-J"
assert result["result"] == (
    "PASS_W2B_I2F3E_J_ONE_SHOT_RUNNER_PREPARED_BLOCKED_NO_EXECUTION"
)
assert result["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert result["candidate_artifact_count"] == 7
assert result["validator"] == "PASS"
assert result["negative_test_count"] == 6
assert result["negative_tests"] == "PASS"
assert result["self_check"] == "PASS"
assert result["python_compile"] == "PASS"
assert result["candidate_deployed_to_production"] is False
assert result["final_approval_token_created"] is False
assert result["approval_binding_created"] is False
assert result["root_sudo_rule_created"] is False
assert result["process_signal_sent"] is False
assert result["writer_stop_performed"] is False
assert result["gui_stopped_or_restarted"] is False
assert result["crontab_changed"] is False
assert result["production_database_sql_connection_used"] is False
assert result["production_backup_created"] is False
assert result["restore_executed"] is False
assert result["migration_executed"] is False
assert result["production_manifest_modified"] is False
assert result["production_deployment_performed"] is False
assert result["external_network_used"] is False
assert result["writer_freeze_execution"] == "HOLD"
assert result["production_release_decision"] == "HOLD"
assert result["release_status"] == "CANDIDATE_NOT_APPROVED"
assert result["next_gate"] == "HUMAN_REVIEW_3E_J_BLOCKED_RUNNER_PACKET"

assert manifest["result"] == "PASS_3E_J_BLOCKED_RUNNER_PACKET_GENERATED"
assert manifest["packet_file_count_excluding_manifest"] == 10
assert len(manifest["packet_files"]) == 10
assert manifest["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert manifest["candidate_deployed_to_production"] is False
assert manifest["writer_freeze_execution"] == "HOLD"
assert manifest["production_release_decision"] == "HOLD"
assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"

expected_packet_names = {item["name"] for item in manifest["packet_files"]}
actual_packet_names = {
    path.relative_to(packet).as_posix()
    for path in packet.rglob("*")
    if path.is_file() and path.name != "packet-manifest.json"
}
assert expected_packet_names == actual_packet_names
for item in manifest["packet_files"]:
    artifact = packet / item["name"]
    assert sha256(artifact) == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

assert semantic["result"] == (
    "PASS_3E_J_ONE_SHOT_WRITER_FREEZE_BACKUP_RESTART_RUNNER_"
    "PREPARATION_BLOCKED_NO_EXECUTION"
)
assert semantic["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert semantic["exact_approval_token_required"] is True
assert semantic["evidence_sha_binding_required"] is True
assert semantic["single_use_consumption_marker_required"] is True
assert semantic["token_reuse_rejected_before_signal"] is True
assert semantic["fresh_safe_window_required_before_signal"] is True
assert semantic["cron_selected_three_sha_required"] is True
assert semantic["cron_excluded_sha_required"] is True
assert semantic["gui_identity_required_before_signal"] is True
assert semantic["root_helper_required_before_signal"] is True
assert semantic["sigkill_allowed"] is False
assert semantic["max_freeze_seconds"] == 600
assert semantic["stop_wait_seconds"] == 30
assert semantic["restart_profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert semantic["wordpress_external_actions_after_restart"] == "HOLD"
assert semantic["full_operational_parity_after_restart"] == "NOT_ESTABLISHED"
assert semantic["candidate_deployed_to_production"] is False
assert semantic["process_signal_sent"] is False
assert semantic["writer_stop_performed"] is False
assert semantic["gui_stopped_or_restarted"] is False
assert semantic["production_database_sql_connection_used"] is False
assert semantic["production_backup_created"] is False
assert semantic["restore_executed"] is False
assert semantic["migration_executed"] is False
assert semantic["writer_freeze_execution"] == "HOLD"

assert summary["result"] == (
    "PASS_3E_J_RUNNER_CANDIDATE_PREPARED_BLOCKED_NO_EXECUTION"
)
assert summary["candidate_artifact_count_excluding_manifest"] == 6
assert summary["validator"] == "PASS"
assert summary["negative_test_count"] == 6
assert summary["negative_tests"] == "PASS"
assert summary["self_check"] == "PASS"
assert summary["python_compile_file_count"] == 4
assert summary["python_compile"] == "PASS"
assert summary["candidate_deployed_to_production"] is False

assert candidate_manifest["phase"] == "TST-5D-W2B-I2F-3E-J"
assert candidate_manifest["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert len(candidate_manifest["files"]) == 6
expected_candidate_files = {
    "3e_j_operation_manual.md",
    "one_shot_writer_freeze_backup_restart_runner.py",
    "root_fd_metadata_helper.py",
    "runner-policy.json",
    "test_3e_j_runner_negative.py",
    "validate_3e_j_runner_packet.py",
}
assert {item["name"] for item in candidate_manifest["files"]} == expected_candidate_files
for item in candidate_manifest["files"]:
    artifact = candidate / item["name"]
    assert sha256(artifact) == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

assert policy["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert policy["limits"]["max_freeze_seconds"] == 600
assert policy["limits"]["stop_wait_seconds"] == 30
assert policy["limits"]["sigkill_allowed"] is False
assert policy["restart"]["profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert policy["restart"]["wordpress_external_actions_after_restart"] == "HOLD"
assert policy["restart"]["full_operational_parity_after_restart"] == (
    "NOT_ESTABLISHED"
)
assert len(policy["cron"]["selected_line_sha256"]) == 3
assert policy["database"]["sqlite_connection_allowed"] is False

compile_log = (logs / "python-compile.log").read_text(encoding="utf-8")
validator_log = (logs / "validator.log").read_text(encoding="utf-8")
negative_log = (logs / "negative-tests.log").read_text(encoding="utf-8")
self_check_log = (logs / "runner-self-check.log").read_text(encoding="utf-8")
protected_log = (logs / "protected-sha-after.log").read_text(encoding="utf-8")

assert compile_log.count("PYTHON_COMPILE_PASS=") == 4
assert "VALIDATION=PASS" in validator_log
assert "PRODUCTION_SIGNAL_CALL_COUNT=1" in validator_log
assert "TOKEN_CONSUMED_BEFORE_SIGNAL=true" in validator_log
assert "SIGKILL_ALLOWED=false" in validator_log
assert "SQLITE_CONNECTION_USED=false" in validator_log
assert "PRODUCTION_EXECUTION_ALLOWED=false" in validator_log
assert "Ran 6 tests" in negative_log
assert negative_log.rstrip().endswith("OK")
assert "SELF_CHECK=PASS" in self_check_log
assert "EXECUTION_ALLOWED=false" in self_check_log
assert protected_log.count(": OK") == 6

print("J_PREPARATION_EVIDENCE_REVIEW=PASS")
print("J_PACKET_INTEGRITY_REVIEW=PASS")
print("J_CANDIDATE_MANIFEST_REVIEW=PASS")
print("J_PREPARATION_VALIDATION_LOG_REVIEW=PASS")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ROOT_SUDO_RULE_CREATED=false")
print("PRODUCTION_PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("PRODUCTION_DB_SQL_CONNECTION_USED=false")
print("PRODUCTION_BACKUP_CREATED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
PY

  printf '\n===== FUTURE RUNNER STATIC ORDER / SAFETY REVIEW =====\n'

  python3 - "$CANDIDATE_ROOT" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
runner_path = root / "one_shot_writer_freeze_backup_restart_runner.py"
helper_path = root / "root_fd_metadata_helper.py"

runner_source = runner_path.read_text(encoding="utf-8")
helper_source = helper_path.read_text(encoding="utf-8")
runner_tree = ast.parse(runner_source)
helper_tree = ast.parse(helper_source)

def calls(tree: ast.AST) -> list[tuple[str, int]]:
    records = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            name = ".".join(reversed(parts))
        else:
            name = ""
        records.append((name, getattr(node, "lineno", -1)))
    return records

runner_calls = calls(runner_tree)
helper_calls = calls(helper_tree)

def only_line(name: str) -> int:
    found = [line for call_name, line in runner_calls if call_name == name]
    assert len(found) == 1, (name, found)
    return found[0]

consume_line = only_line("consume_token_once")
signal_line = only_line("os.kill")
assert consume_line < signal_line

assert runner_source.count("signal.SIGTERM") == 1
assert "signal.SIGKILL" not in runner_source
assert "kill -9" not in runner_source
assert "sqlite3" not in runner_source
assert "sqlite3" not in helper_source
assert "systemctl" not in runner_source
assert "crontab -r" not in runner_source
assert "APPROVAL_TOKEN_ALREADY_CONSUMED" in runner_source
assert "FRESH_SAFE_WINDOW_UNAVAILABLE" in runner_source
assert "GUI_PROCESS_IDENTITY_CHANGED" in runner_source
assert "ROOT_HELPER_UNAVAILABLE" in runner_source
assert "FROZEN_FILESYSTEM_COPY_NO_SQL_CONNECTION" in runner_source
assert "SAFE_MINIMAL_MAINTENANCE_MODE" in runner_source
assert "automatic_retry_allowed" in runner_source
assert "automatic_restore_allowed" in runner_source
assert "source_sha256_after_copy" in runner_source
assert "BACKUP_SOURCE_SHA_CHANGED_BEFORE_MANIFEST" in runner_source

for name, line in helper_calls:
    assert name not in {
        "open",
        "Path.open",
        "sqlite3.connect",
        "subprocess.run",
        "os.kill",
    }, (name, line)

print("TOKEN_CONSUMED_BEFORE_FIRST_SIGNAL=true")
print("PRODUCTION_SIGNAL_CALL_COUNT=1")
print("PRODUCTION_SIGNAL_TYPE=SIGTERM")
print("SIGKILL_ALLOWED=false")
print("SQLITE_CONNECTION_USED=false")
print("FILESYSTEM_BACKUP_CONTRACT_PRESENT=true")
print("SOURCE_SHA_REVALIDATION_PRESENT=true")
print("SAFE_MINIMAL_RESTART_PRESENT=true")
PY

  printf '\n===== BLOCKER REVIEW: ROOT /PROC SCAN COMPLETENESS =====\n'

  python3 - "$CANDIDATE_ROOT/root_fd_metadata_helper.py" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

silent_permission_skip = False
uninspectable_counter_present = any(
    token in source
    for token in (
        "uninspectable_process_count",
        "inaccessible_process_count",
        "scan_incomplete",
        "coverage_complete",
    )
)

for node in ast.walk(tree):
    if not isinstance(node, ast.Try):
        continue
    for handler in node.handlers:
        type_text = ast.unparse(handler.type) if handler.type is not None else ""
        if "PermissionError" not in type_text:
            continue
        if any(isinstance(statement, ast.Continue) for statement in handler.body):
            silent_permission_skip = True

assert silent_permission_skip is True
assert uninspectable_counter_present is False

print("ROOT_HELPER_PERMISSION_ERROR_CONTINUES_SILENTLY=true")
print("ROOT_HELPER_UNINSPECTABLE_PROCESS_COUNTER_PRESENT=false")
print("ROOT_HELPER_SCAN_COMPLETENESS_PROVEN=false")
print("ROOT_OPEN_HANDLE_ZERO_CAN_BE_APPROVED=false")
print("ROOT_HELPER_SCAN_COVERAGE_REVIEW=FAIL_REQUIRES_R1_CORRECTION")
PY

  printf '\n===== BLOCKER REVIEW: STOP TIMEOUT / LATE EXIT RECOVERY =====\n'

  python3 - "$CANDIDATE_ROOT/one_shot_writer_freeze_backup_restart_runner.py" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

execute_node = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "execute_once":
        execute_node = node
        break
assert execute_node is not None

execute_text = ast.get_source_segment(source, execute_node)
assert execute_text is not None

assert "wait_for_gui_exit(identity[\"pid\"], policy)" in execute_text
assert "old_process_stopped = True" in execute_text
assert (
    "if signal_sent and old_process_stopped and not restart_attempted:"
    in execute_text
)

wait_index = execute_text.index('wait_for_gui_exit(identity["pid"], policy)')
stopped_index = execute_text.index("old_process_stopped = True")
recovery_index = execute_text.index(
    "if signal_sent and old_process_stopped and not restart_attempted:"
)

assert wait_index < stopped_index < recovery_index

# A timeout raises before old_process_stopped becomes true. The exception branch
# therefore skips recovery restart even if the process exits immediately after
# the timeout boundary.
assert "GUI_STOP_TIMEOUT_SIGKILL_FORBIDDEN" in source
assert "recheck" not in execute_text.lower()
assert "late_exit" not in execute_text.lower()

print("STOP_TIMEOUT_RAISES_BEFORE_OLD_PROCESS_STOPPED_TRUE=true")
print("RECOVERY_RESTART_REQUIRES_OLD_PROCESS_STOPPED_TRUE=true")
print("POST_TIMEOUT_PROCESS_AND_PORT_RECHECK_PRESENT=false")
print("LATE_EXIT_CAN_LEAVE_GUI_DOWN_WITHOUT_RECOVERY=true")
print("STOP_TIMEOUT_RECOVERY_REVIEW=FAIL_REQUIRES_R1_CORRECTION")
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

expected = {item["name"] for item in manifest["packet_files"]}
actual = {
    path.relative_to(root).as_posix()
    for path in root.rglob("*")
    if path.is_file() and path.name != "packet-manifest.json"
}
assert expected == actual

for item in manifest["packet_files"]:
    artifact = root / item["name"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

print("PACKET_MANIFEST_FILE_SET_VALID=true")
print("PACKET_MANIFEST_SHA_AND_SIZE_VALID=true")
print(f"PACKET_FILE_COUNT_EXCLUDING_MANIFEST={len(expected)}")
print(f"PACKET_FILE_COUNT={len(expected) + 1}")
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
uid = repo.stat().st_uid
gid = repo.stat().st_gid

assert stat.S_IMODE(root.stat().st_mode) == 0o555
assert root.stat().st_uid == uid
assert root.stat().st_gid == gid

files = 0
directories = 1
for path in root.rglob("*"):
    metadata = path.lstat()
    assert not stat.S_ISLNK(metadata.st_mode), path
    assert metadata.st_uid == uid, path
    assert metadata.st_gid == gid, path
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

  echo "J_PREPARATION_EVIDENCE_REVIEW=PASS"
  echo "J_PACKET_INTEGRITY_REVIEW=PASS"
  echo "J_CANDIDATE_MANIFEST_REVIEW=PASS"
  echo "J_PREPARATION_VALIDATION_LOG_REVIEW=PASS"
  echo "J_BASE_RUNNER_STATIC_SAFETY_REVIEW=PASS_WITH_TWO_BLOCKERS"
  echo "ROOT_HELPER_SCAN_COVERAGE_REVIEW=FAIL_REQUIRES_R1_CORRECTION"
  echo "STOP_TIMEOUT_RECOVERY_REVIEW=FAIL_REQUIRES_R1_CORRECTION"
  echo "J_RUNNER_APPROVAL_DECISION=HOLD_PENDING_R1_CORRECTION"
  echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
  echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
  echo "FINAL_APPROVAL_TOKEN_CREATED=false"
  echo "APPROVAL_BINDING_CREATED=false"
  echo "ROOT_SUDO_RULE_CREATED=false"
  echo "PRODUCTION_PROCESS_SIGNAL_SENT=false"
  echo "WRITER_STOP_PERFORMED=false"
  echo "GUI_STOPPED_OR_RESTARTED=false"
  echo "PRODUCTION_DB_SQL_CONNECTION_USED=false"
  echo "PRODUCTION_BACKUP_CREATED=false"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
  echo "NEXT_GATE=3E_J_R1_ROOT_SCAN_AND_LATE_EXIT_RECOVERY_CORRECTION"

) 2>&1 | tee "$REVIEW_OUT"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_OUT"
