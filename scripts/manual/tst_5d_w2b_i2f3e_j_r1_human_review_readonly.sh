#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SOURCE_J_REL="${BASE_REL}/i2f3e-j-runner-preparation-blocked-no-execution-20260725T155845Z-514350"
SOURCE_J_ROOT="${REPO_ROOT}/${SOURCE_J_REL}"
SOURCE_J_CANDIDATE_ROOT="${SOURCE_J_ROOT}/packet-snapshot/candidate-artifacts"

EVIDENCE_REL="${BASE_REL}/i2f3e-j-r1-root-scan-late-exit-correction-blocked-no-execution-20260725T161929Z-515154"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
LOG_ROOT="${EVIDENCE_ROOT}/validation-logs"
INPUT_ROOT="${EVIDENCE_ROOT}/input-provenance"

REVIEW_OUT="/tmp/tst_5d_w2b_i2f3e_j_r1_human_review.txt"

EXPECTED_RESULT_SHA="0e655aaf36f47b8e516665f586e9d1b1427804ee0fb99d959323b30bf8388476"
EXPECTED_PACKET_MANIFEST_SHA="29cdf5074b7c8c1bb2bdf3801048d682a98f116f6c014e5463ad5a452c5ee447"
EXPECTED_SEMANTIC_SHA="b668a621b58459f0ef8dc62cdf25b3665ab8e8db51127bb15d381bb1e1b065fe"
EXPECTED_EVIDENCE_MANIFEST_SHA="c22f6084056a0175c04c0437d981e975e820364335af3acfdfb4ef4f77341430"

EXPECTED_CANDIDATE_MANIFEST_SHA="0677a9a9479e209a6e1ee30fdcd07996b671737850b17e79b97987578a73ec7f"
EXPECTED_RUNNER_SHA="1ccdabcbf59d130c1010643f6444f71f3dd8ea9a1ccaa4b8bad111e098b3b052"
EXPECTED_ROOT_HELPER_SHA="e989fb528110a4b7c482404fc5b024e2d4a8371a6d6cf901c2a940b8f4f83888"
EXPECTED_VALIDATOR_SHA="eaf5f28f3a924da93a4dc0dc6a15669c5546c784b4207074629282954c48e65f"
EXPECTED_NEGATIVE_TEST_SHA="3e46a59517699e7e4845f9e716bd7ca021ddf9a23714453afb784960d223238e"
EXPECTED_POLICY_SHA="261941dab03f577b0882836f000f9a0f06b255a6dbf85b78ad8b5e4a3b7682dd"
EXPECTED_MANUAL_SHA="2ff4a42b574c4fb89699cf92beb555b7c83772a381847facca1ae289a765c773"

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
    "input-provenance/source-3e-j-fixed-sha.txt"
  )

  for name in "${required_files[@]}"; do
    test -f "$EVIDENCE_ROOT/$name"
    printf 'FILE_PRESENT=%s\n' "$name"
  done

  printf '\n===== R1 FIXED SHA CHECK =====\n'

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

  printf '\n===== SOURCE 3E-J IMMUTABILITY CHECK =====\n'

  sha256sum -c <<SHAS
18f40a9a4b81b5613c4ad8fb39cf6c9e13fff74a289d392d1f542e89c1f40c9d  $SOURCE_J_ROOT/result.json
9d1b47df30b8bf1cba1793192e3c9603aa8e3643bc728cf0756d0f724aa2a794  $SOURCE_J_ROOT/packet-snapshot/packet-manifest.json
dc158bb774f653698565e314d4ca30ebacede2cc26a28ddb108710d0368b778e  $SOURCE_J_ROOT/packet-snapshot/packet-semantic-validation.json
7ae5783d4ba62360fb25c8052b1669a47283de98416786d6d2b4658a75703fb4  $SOURCE_J_ROOT/evidence-manifest.txt
90389e95ed6c33b3bb6de100261620fe4ce7b9fd5f9dbd650296a89f42d6e066  $SOURCE_J_CANDIDATE_ROOT/candidate-manifest.json
58afe2824f10b6255e3f5be1e2138475fe3ba4b351a76120d2abbe8c63e7f920  $SOURCE_J_CANDIDATE_ROOT/one_shot_writer_freeze_backup_restart_runner.py
a4e3cd04a17fce10d46d5869a66b916b5a2ab81df92c7da15f4e9155f8f272d6  $SOURCE_J_CANDIDATE_ROOT/root_fd_metadata_helper.py
0a4b610a8f16483bb91318b028aa27d9cf0e6600e9b8a64f7b50f5b3941ff019  $SOURCE_J_CANDIDATE_ROOT/validate_3e_j_runner_packet.py
26666d68bdb2b2a6f5600223a7a13d367c2daa6344a2b86b5d655761ba6d9d8a  $SOURCE_J_CANDIDATE_ROOT/test_3e_j_runner_negative.py
b36421be9271296e1e9712b93a76bffee526526dfb482fa348da12cd9d63ecee  $SOURCE_J_CANDIDATE_ROOT/runner-policy.json
ed1c1596826f6117871eb51ac71a896a09ea57ddaf7ce1e07acbaf257d1366bb  $SOURCE_J_CANDIDATE_ROOT/3e_j_operation_manual.md
SHAS

  printf '\n===== PACKET / LOG SEMANTIC REVIEW =====\n'

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

assert result["phase"] == "TST-5D-W2B-I2F-3E-J-R1"
assert result["result"] == (
    "PASS_W2B_I2F3E_J_R1_ROOT_SCAN_AND_LATE_EXIT_"
    "CORRECTION_PREPARED_BLOCKED_NO_EXECUTION"
)
assert result["source_3e_j_candidate_status"] == (
    "HOLD_PENDING_R1_CORRECTION"
)
assert result["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert result["candidate_artifact_count"] == 7
assert result["python_compile"] == "PASS"
assert result["validator"] == "PASS"
assert result["negative_test_count"] == 15
assert result["negative_tests"] == "PASS"
assert result["self_check"] == "PASS"
assert result["root_scan_coverage_fail_closed"] is True
assert result["uninspectable_process_count_required"] == 0
assert result["post_timeout_recheck_present"] is True
assert result["late_exit_only_recovery_restart"] is True
assert result["late_exit_recovery_restart_max_count"] == 1
assert result["automatic_retry_loop_allowed"] is False
assert result["candidate_deployed_to_production"] is False
assert result["final_approval_token_created"] is False
assert result["approval_binding_created"] is False
assert result["root_sudo_rule_created"] is False
assert result["sudoers_changed"] is False
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
assert result["next_gate"] == (
    "HUMAN_REVIEW_3E_J_R1_CORRECTED_BLOCKED_RUNNER_PACKET"
)

assert manifest["phase"] == "TST-5D-W2B-I2F-3E-J-R1"
assert manifest["result"] == (
    "PASS_3E_J_R1_CORRECTED_BLOCKED_RUNNER_PACKET_GENERATED"
)
assert manifest["packet_file_count_excluding_manifest"] == 10
assert len(manifest["packet_files"]) == 10
assert manifest["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert manifest["candidate_deployed_to_production"] is False
assert manifest["writer_freeze_execution"] == "HOLD"
assert manifest["production_release_decision"] == "HOLD"
assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"

expected_packet = {item["name"] for item in manifest["packet_files"]}
actual_packet = {
    path.relative_to(packet).as_posix()
    for path in packet.rglob("*")
    if path.is_file() and path.name != "packet-manifest.json"
}
assert expected_packet == actual_packet
for item in manifest["packet_files"]:
    artifact = packet / item["name"]
    assert sha256(artifact) == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

assert semantic["phase"] == "TST-5D-W2B-I2F-3E-J-R1"
assert semantic["result"] == (
    "PASS_3E_J_R1_ROOT_SCAN_COVERAGE_AND_LATE_EXIT_RECOVERY_"
    "CORRECTION_BLOCKED_NO_EXECUTION"
)
assert semantic["source_3e_j_candidate_status"] == (
    "HOLD_PENDING_R1_CORRECTION"
)
assert semantic["root_scan_coverage_required"] is True
assert semantic["uninspectable_process_count_required"] == 0
assert semantic["transient_vanish_distinguished"] is True
assert semantic["open_handle_zero_requires_complete_scan"] is True
assert semantic["post_timeout_recheck_present"] is True
assert semantic["late_exit_only_recovery_restart"] is True
assert semantic["old_process_present_restart_forbidden"] is True
assert semantic["foreign_listener_restart_forbidden"] is True
assert semantic["pid_reuse_restart_forbidden"] is True
assert semantic["unresolved_state_restart_forbidden"] is True
assert semantic["late_exit_recovery_restart_max_count"] == 1
assert semantic["automatic_retry_loop_allowed"] is False
assert semantic["additional_signal_allowed"] is False
assert semantic["process_group_signal_allowed"] is False
assert semantic["sigkill_allowed"] is False
assert semantic["candidate_deployed_to_production"] is False
assert semantic["process_signal_sent"] is False
assert semantic["production_database_sql_connection_used"] is False
assert semantic["production_backup_created"] is False

assert summary["result"] == (
    "PASS_3E_J_R1_ROOT_SCAN_AND_LATE_EXIT_CORRECTION_"
    "PREPARED_BLOCKED_NO_EXECUTION"
)
assert summary["candidate_artifact_count_excluding_manifest"] == 6
assert summary["python_compile_file_count"] == 4
assert summary["validator"] == "PASS"
assert summary["negative_test_count"] == 15
assert summary["negative_tests"] == "PASS"
assert summary["self_check"] == "PASS"
assert summary["root_scan_coverage_fail_closed"] is True
assert summary["post_timeout_recheck_present"] is True
assert summary["late_exit_only_recovery_restart"] is True
assert summary["candidate_deployed_to_production"] is False

assert candidate_manifest["phase"] == "TST-5D-W2B-I2F-3E-J-R1"
assert candidate_manifest["correction_label"] == (
    "ROOT_SCAN_COVERAGE_AND_LATE_EXIT_RECOVERY_CORRECTION"
)
assert candidate_manifest["source_3e_j_candidate_status"] == (
    "HOLD_PENDING_R1_CORRECTION"
)
assert candidate_manifest["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert len(candidate_manifest["files"]) == 6
expected_candidate_names = {
    "3e_j_operation_manual.md",
    "one_shot_writer_freeze_backup_restart_runner.py",
    "root_fd_metadata_helper.py",
    "runner-policy.json",
    "test_3e_j_runner_negative.py",
    "validate_3e_j_runner_packet.py",
}
assert {item["name"] for item in candidate_manifest["files"]} == (
    expected_candidate_names
)
for item in candidate_manifest["files"]:
    artifact = candidate / item["name"]
    assert sha256(artifact) == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

assert policy["phase"] == "TST-5D-W2B-I2F-3E-J-R1"
assert policy["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert policy["root_scan"]["coverage_required"] is True
assert policy["root_scan"]["uninspectable_process_count_required"] == 0
assert policy["root_scan"]["transient_vanish_is_distinct"] is True
assert policy["database"]["sqlite_connection_allowed"] is False
assert policy["limits"]["stop_wait_seconds"] == 30
assert policy["limits"]["late_exit_recovery_restart_max_count"] == 1
assert policy["limits"]["automatic_retry_loop_allowed"] is False
assert policy["limits"]["sigkill_allowed"] is False
assert policy["limits"]["max_freeze_seconds"] == 600
assert policy["restart"]["profile"] == "SAFE_MINIMAL_MAINTENANCE_MODE"
assert policy["restart"]["wordpress_external_actions_after_restart"] == "HOLD"
assert policy["restart"]["full_operational_parity_after_restart"] == (
    "NOT_ESTABLISHED"
)

compile_log = (logs / "python-compile.log").read_text(encoding="utf-8")
validator_log = (logs / "validator.log").read_text(encoding="utf-8")
negative_log = (logs / "negative-tests.log").read_text(encoding="utf-8")
self_check_log = (logs / "runner-self-check.log").read_text(encoding="utf-8")
protected_log = (logs / "protected-sha-after.log").read_text(encoding="utf-8")

assert compile_log.count("PYTHON_COMPILE_PASS=") == 4
for marker in (
    "VALIDATION=PASS",
    "ROOT_SCAN_COVERAGE_FAIL_CLOSED=true",
    "UNINSPECTABLE_PROCESS_COUNT_REQUIRED=0",
    "POST_TIMEOUT_RECHECK_PRESENT=true",
    "LATE_EXIT_ONLY_RECOVERY_RESTART=true",
    "OLD_PROCESS_PRESENT_RESTART_FORBIDDEN=true",
    "FOREIGN_LISTENER_RESTART_FORBIDDEN=true",
    "PID_REUSE_RESTART_FORBIDDEN=true",
    "LATE_EXIT_RECOVERY_RESTART_MAX_COUNT=1",
    "AUTOMATIC_RETRY_LOOP_ALLOWED=false",
    "SIGKILL_ALLOWED=false",
    "SQLITE_CONNECTION_USED=false",
    "PRODUCTION_EXECUTION_ALLOWED=false",
):
    assert marker in validator_log, marker

assert "Ran 15 tests" in negative_log
assert negative_log.rstrip().endswith("OK")
assert "SELF_CHECK=PASS" in self_check_log
assert "EXECUTION_ALLOWED=false" in self_check_log
assert protected_log.count(": OK") == 6

print("J_R1_PREPARATION_EVIDENCE_REVIEW=PASS")
print("J_R1_PACKET_INTEGRITY_REVIEW=PASS")
print("J_R1_CANDIDATE_MANIFEST_REVIEW=PASS")
print("J_R1_VALIDATION_LOG_REVIEW=PASS")
print("SOURCE_3E_J_CANDIDATE_PRESERVED=true")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ROOT_SUDO_RULE_CREATED=false")
print("SUDOERS_CHANGED=false")
print("PRODUCTION_PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("PRODUCTION_DB_SQL_CONNECTION_USED=false")
print("PRODUCTION_BACKUP_CREATED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
PY

  printf '\n===== ROOT SCAN COVERAGE CORRECTION REVIEW =====\n'

  python3 - "$CANDIDATE_ROOT/root_fd_metadata_helper.py" \
    "$CANDIDATE_ROOT/one_shot_writer_freeze_backup_restart_runner.py" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

helper_path = Path(sys.argv[1])
runner_path = Path(sys.argv[2])
helper_source = helper_path.read_text(encoding="utf-8")
runner_source = runner_path.read_text(encoding="utf-8")
helper_tree = ast.parse(helper_source)
runner_tree = ast.parse(runner_source)

def function_source(source: str, tree: ast.Module, name: str) -> str:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            value = ast.get_source_segment(source, node)
            assert value is not None
            return value
    raise AssertionError(name)

for token in (
    "proc_pid_candidate_count",
    "proc_pid_inspected_count",
    "proc_pid_vanished_count",
    "proc_pid_uninspectable_count",
    "proc_fd_examined_count",
    "scan_coverage_complete",
    "vanished_pids",
    "uninspectable_pids",
):
    assert token in helper_source, token

scan_source = function_source(
    helper_source,
    helper_tree,
    "scan_open_handles",
)
status_source = function_source(
    helper_source,
    helper_tree,
    "inspection_result_status",
)
runner_inspect_source = function_source(
    runner_source,
    runner_tree,
    "helper_inspect",
)

assert "_is_transient_vanish" in scan_source
assert "PermissionError" in scan_source
assert "uninspectable[pid]" in scan_source
assert "vanished_pids.add(pid)" in scan_source
assert "scan_coverage_complete = len(uninspectable) == 0" in scan_source

coverage_check = 'if not scan["scan_coverage_complete"]'
handle_check = (
    'if require_zero and scan["total_open_handle_count"] != 0'
)
assert coverage_check in status_source
assert handle_check in status_source
assert status_source.index(coverage_check) < status_source.index(handle_check)
assert "BLOCKED_ROOT_DB_FILESET_SCAN_COVERAGE_INCOMPLETE" in status_source
assert "PASS_ROOT_DB_FILESET_OPEN_HANDLE_ZERO_COMPLETE_SCAN" in status_source

assert 'payload["scan_coverage_complete"] is True' in runner_inspect_source
assert 'payload["proc_pid_uninspectable_count"]' in runner_inspect_source
assert 'payload["total_open_handle_count"] == 0' in runner_inspect_source
assert 'payload["open_handle_zero_approved"] is True' in runner_inspect_source

assert "sqlite3" not in helper_source
assert "subprocess.run" not in helper_source
assert "os.kill" not in helper_source
assert "signal." not in helper_source
assert "systemctl" not in helper_source

print("ROOT_SCAN_COVERAGE_CORRECTION_REVIEW=PASS")
print("ROOT_SCAN_COVERAGE_FAIL_CLOSED=true")
print("TRANSIENT_VANISH_DISTINGUISHED=true")
print("PERMISSION_ERROR_RECORDED_AS_UNINSPECTABLE=true")
print("OPEN_HANDLE_ZERO_REQUIRES_COMPLETE_SCAN=true")
print("RUNNER_REVALIDATES_SCAN_COVERAGE=true")
print("UNINSPECTABLE_PROCESS_COUNT_REQUIRED=0")
print("ROOT_HELPER_SQLITE_CONNECTION_USED=false")
print("ROOT_HELPER_PROCESS_SIGNAL_USED=false")
PY

  printf '\n===== LATE EXIT RECOVERY CORRECTION REVIEW =====\n'

  python3 - "$CANDIDATE_ROOT/one_shot_writer_freeze_backup_restart_runner.py" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

def function_source(name: str) -> str:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            value = ast.get_source_segment(source, node)
            assert value is not None
            return value
    raise AssertionError(name)

classifier = function_source("classify_post_timeout_snapshot")
recheck = function_source("recheck_after_stop_timeout")
wait = function_source("wait_for_gui_exit")
recovery_gate = function_source(
    "recovery_restart_allowed_after_failure"
)
execute = function_source("execute_once")

classifications = (
    "LATE_EXIT_CONFIRMED",
    "OLD_PROCESS_STILL_RUNNING",
    "PID_REUSED_IDENTITY_MISMATCH",
    "DIFFERENT_GUI_PROCESS_PRESENT",
    "FOREIGN_LISTENER_PRESENT",
    "STATE_UNRESOLVED",
)
for value in classifications:
    assert value in classifier, value

assert classifier.count("recovery_restart_allowed = True") == 1
assert (
    classifier.index('classification = "LATE_EXIT_CONFIRMED"')
    < classifier.index("recovery_restart_allowed = True")
)

for token in (
    "old_proc_path.exists()",
    "build_process_identity(old_pid)",
    "matching_gui_pids(policy)",
    "port_listener_lines(policy)",
    "listener_owner_pids_from_lines",
):
    assert token in recheck, token

assert "recheck_after_stop_timeout" in wait
assert "LATE_EXIT_CONFIRMED_AFTER_TIMEOUT" in wait
assert "continue_backup_allowed" in wait
assert "additional_signal_sent" in wait
assert "sigkill_sent" in wait

assert '== "LATE_EXIT_CONFIRMED"' in recovery_gate
assert "LATE_EXIT_RECOVERY_RESTART_MAX_COUNT" in recovery_gate
assert "restart_attempted" in recovery_gate
assert "old_process_stopped" in recovery_gate

assert "GUI_STOP_TIMEOUT_LATE_EXIT_CONFIRMED_" in execute
assert "recovery_restart_allowed_after_failure" in execute
assert "recovery_restart_count += 1" in execute
assert "automatic_retry_allowed" in execute
assert "automatic_restore_allowed" in execute

assert source.count("os.kill(") == 1
assert source.count("signal.SIGTERM") == 1
assert "signal.SIGKILL" not in source
assert "os.killpg" not in source
assert "signal.pthread_kill" not in source
assert "kill -9" not in source

print("LATE_EXIT_RECOVERY_CORRECTION_REVIEW=PASS")
print("POST_TIMEOUT_PROCESS_RECHECK_PRESENT=true")
print("POST_TIMEOUT_IDENTITY_RECHECK_PRESENT=true")
print("POST_TIMEOUT_MATCHING_GUI_RECHECK_PRESENT=true")
print("POST_TIMEOUT_LISTENER_OWNER_RECHECK_PRESENT=true")
print("LATE_EXIT_ONLY_RECOVERY_RESTART=true")
print("OLD_PROCESS_PRESENT_RESTART_FORBIDDEN=true")
print("FOREIGN_LISTENER_RESTART_FORBIDDEN=true")
print("PID_REUSE_RESTART_FORBIDDEN=true")
print("UNRESOLVED_STATE_RESTART_FORBIDDEN=true")
print("LATE_EXIT_RECOVERY_RESTART_MAX_COUNT=1")
print("AUTOMATIC_RETRY_LOOP_ALLOWED=false")
print("ADDITIONAL_SIGNAL_ALLOWED=false")
print("PROCESS_GROUP_SIGNAL_ALLOWED=false")
print("SIGKILL_ALLOWED=false")
PY

  printf '\n===== NEGATIVE TEST COVERAGE REVIEW =====\n'

  python3 - "$CANDIDATE_ROOT/test_3e_j_runner_negative.py" \
    "$LOG_ROOT/negative-tests.log" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

test_path = Path(sys.argv[1])
log_path = Path(sys.argv[2])
source = test_path.read_text(encoding="utf-8")
tree = ast.parse(source)
log = log_path.read_text(encoding="utf-8")

test_names = {
    node.name
    for node in ast.walk(tree)
    if isinstance(node, ast.FunctionDef)
    and node.name.startswith("test_")
}

required = {
    "test_permission_error_marks_scan_incomplete",
    "test_transient_vanished_is_recorded_separately",
    "test_zero_handles_with_incomplete_coverage_is_rejected",
    "test_late_exit_allows_one_recovery_restart_path",
    "test_old_process_still_running_forbids_restart",
    "test_foreign_listener_forbids_restart",
    "test_pid_reuse_identity_mismatch_forbids_restart",
    "test_different_gui_process_forbids_restart",
    "test_unresolved_probe_forbids_restart",
    "test_wrong_token_is_blocked",
    "test_evidence_sha_mismatch_is_blocked",
    "test_reused_token_marker_is_blocked",
    "test_missing_final_authorization_is_blocked",
    "test_root_helper_rejects_non_root",
    "test_valid_approval_preflight_is_no_execution",
}

assert required <= test_names
assert len(test_names) == 15
for name in required:
    assert name in log, name
assert "Ran 15 tests" in log
assert log.rstrip().endswith("OK")

print("NEGATIVE_TEST_COVERAGE_REVIEW=PASS")
print("NEGATIVE_TEST_COUNT=15")
print("ROOT_SCAN_NEGATIVE_TESTS_PRESENT=true")
print("TIMEOUT_CLASSIFICATION_NEGATIVE_TESTS_PRESENT=true")
print("APPROVAL_GATE_NEGATIVE_TESTS_PRESENT=true")
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

  echo "J_R1_PREPARATION_EVIDENCE_REVIEW=PASS"
  echo "J_R1_PACKET_INTEGRITY_REVIEW=PASS"
  echo "J_R1_CANDIDATE_MANIFEST_REVIEW=PASS"
  echo "J_R1_VALIDATION_LOG_REVIEW=PASS"
  echo "ROOT_SCAN_COVERAGE_CORRECTION_REVIEW=PASS"
  echo "LATE_EXIT_RECOVERY_CORRECTION_REVIEW=PASS"
  echo "NEGATIVE_TEST_COVERAGE_REVIEW=PASS"
  echo "SOURCE_3E_J_CANDIDATE_PRESERVED=true"
  echo "J_R1_CORRECTED_RUNNER_REVIEW=PASS_PLAN_ONLY"
  echo "J_R1_RUNNER_APPROVAL_DECISION=APPROVE_WITH_EXECUTION_HOLD"
  echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
  echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
  echo "FINAL_APPROVAL_TOKEN_CREATED=false"
  echo "APPROVAL_BINDING_CREATED=false"
  echo "ROOT_SUDO_RULE_CREATED=false"
  echo "SUDOERS_CHANGED=false"
  echo "PRODUCTION_PROCESS_SIGNAL_SENT=false"
  echo "WRITER_STOP_PERFORMED=false"
  echo "GUI_STOPPED_OR_RESTARTED=false"
  echo "PRODUCTION_DB_SQL_CONNECTION_USED=false"
  echo "PRODUCTION_BACKUP_CREATED=false"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
  echo "NEXT_GATE=3E_J_R2_DEPLOYMENT_AND_ROOT_HELPER_AUTHORIZATION_PACKET_PREPARATION_NO_EXECUTION"

) 2>&1 | tee "$REVIEW_OUT"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_OUT"
