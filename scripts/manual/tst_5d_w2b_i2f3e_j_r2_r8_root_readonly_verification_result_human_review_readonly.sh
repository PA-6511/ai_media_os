#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
R2_REL="${BASE_REL}/i2f3e-j-r2-r8-r2-candidate-exact-file-set-correction-20260726T021229Z-524713"
R2_ROOT="${REPO_ROOT}/${R2_REL}"
PACKET_ROOT="${R2_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"

VERIFIER="${CANDIDATE_ROOT}/root_readonly_sudoers_destination_verifier.sh"
CONTRACT="${CANDIDATE_ROOT}/root-readonly-command-contract.json"
CANDIDATE_MANIFEST="${CANDIDATE_ROOT}/candidate-manifest.json"

WRAPPER="${REPO_ROOT}/scripts/manual/tst_5d_w2b_i2f3e_j_r2_r8_r1_nonexecutable_verifier_bash_invocation_correction_execution_once.sh"
OUTPUT_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r8_root_readonly_verification_execution.txt"
GUARD_DIR="/tmp/ai-media-os-3e-j-r2-r8-root-readonly-verification-once-c1d53b3a.guard"
ATTEMPT_RECORD="${GUARD_DIR}/execution-attempt.txt"

TARGET="/etc/sudoers.d/ai-media-os-3e-j-root-helper"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_REVIEW_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$R2_ROOT"
test -d "$CANDIDATE_ROOT"
test -f "$VERIFIER"
test -f "$CONTRACT"
test -f "$CANDIDATE_MANIFEST"
test -f "$WRAPPER"
test -f "$OUTPUT_LOG"
test -d "$GUARD_DIR"
test -f "$ATTEMPT_RECORD"

cd "$REPO_ROOT"

printf '\n===== FIXED SHA READ-ONLY REVIEW =====\n'

sha256sum -c <<SHAS
b9706aaa71dee9ee3de527bcaa7ca114fec03f5f63220a4a220cd3f417e979ac  ${R2_ROOT}/result.json
41d3e08bcd454307d1f51dcfd185f68f0ac56f96cb85a3bb5f029c5ddd902450  ${PACKET_ROOT}/packet-manifest.json
b9516b7e4041abfd969866748a8c6a7cf98d623bed501fd1d50c59d647250971  ${R2_ROOT}/evidence-manifest.txt
c1d53b3ac8dac86435dde89d4cfe021e1573a000747ce303ebcf62a5fb1c39ec  ${CANDIDATE_MANIFEST}
bd555f07ba09c72e211ab1ae5d1af3b8c544a87ff5204ab8d476cb8923fddd93  ${VERIFIER}
d7f6caa8a5c7b4eee4e343a8b6350ab8e0ad378a6c704d175834c9ed0561b2f8  ${CONTRACT}
714e98a5ed0cf2e3e8db320b7d4fdda234e015cb898e7f2d1d2a16dabc255b04  ${WRAPPER}
582ce48b8847b578035e82131ca374101a7ad189ad9e988ee73b775e687ed88a  ${OUTPUT_LOG}
SHAS

printf '\n===== ROOT READ-ONLY VERIFICATION RESULT HUMAN REVIEW =====\n'

"$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$R2_ROOT" \
  "$PACKET_ROOT" \
  "$CANDIDATE_ROOT" \
  "$VERIFIER" \
  "$CONTRACT" \
  "$CANDIDATE_MANIFEST" \
  "$WRAPPER" \
  "$OUTPUT_LOG" \
  "$GUARD_DIR" \
  "$ATTEMPT_RECORD" \
  "$TARGET" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
r2_root = Path(sys.argv[2]).resolve(strict=True)
packet_root = Path(sys.argv[3]).resolve(strict=True)
candidate_root = Path(sys.argv[4]).resolve(strict=True)
verifier_path = Path(sys.argv[5]).resolve(strict=True)
contract_path = Path(sys.argv[6]).resolve(strict=True)
candidate_manifest_path = Path(sys.argv[7]).resolve(strict=True)
wrapper_path = Path(sys.argv[8]).resolve(strict=True)
output_log_path = Path(sys.argv[9]).resolve(strict=True)
guard_dir = Path(sys.argv[10]).resolve(strict=True)
attempt_record_path = Path(sys.argv[11]).resolve(strict=True)
target = sys.argv[12]

APPROVAL_TOKEN = (
    "APPROVE_3E_J_R2_R8_ROOT_READONLY_"
    "SUDOERS_DESTINATION_VERIFICATION_EXECUTION"
)
APPROVAL_TOKEN_SHA = (
    "a08c5de90a96b4180b5c47a6033003b"
    "33006700a4642a93d4f88a2fb6ba4ff27"
)

EXPECTED_SHA = {
    "result": (
        r2_root / "result.json",
        "b9706aaa71dee9ee3de527bcaa7ca114f"
        "ec03f5f63220a4a220cd3f417e979ac",
    ),
    "packet_manifest": (
        packet_root / "packet-manifest.json",
        "41d3e08bcd454307d1f51dcfd185f68f"
        "0ac56f96cb85a3bb5f029c5ddd902450",
    ),
    "evidence_manifest": (
        r2_root / "evidence-manifest.txt",
        "b9516b7e4041abfd969866748a8c6a7c"
        "f98d623bed501fd1d50c59d647250971",
    ),
    "candidate_manifest": (
        candidate_manifest_path,
        "c1d53b3ac8dac86435dde89d4cfe021e"
        "1573a000747ce303ebcf62a5fb1c39ec",
    ),
    "verifier": (
        verifier_path,
        "bd555f07ba09c72e211ab1ae5d1af3b"
        "8c544a87ff5204ab8d476cb8923fddd93",
    ),
    "contract": (
        contract_path,
        "d7f6caa8a5c7b4eee4e343a8b6350ab"
        "8e0ad378a6c704d175834c9ed0561b2f8",
    ),
    "wrapper": (
        wrapper_path,
        "714e98a5ed0cf2e3e8db320b7d4fdda"
        "234e015cb898e7f2d1d2a16dabc255b04",
    ),
    "output_log": (
        output_log_path,
        "582ce48b8847b578035e82131ca374101"
        "a7ad189ad9e988ee73b775e687ed88a",
    ),
}

PROTECTED_SHA = {
    "data/database/ebook_affiliate.db": (
        "1a421bd32edf1e9eedebc90cfd1b588b"
        "1ca0745670c6372c146a99b154e374e9"
    ),
    "config/slack_worker_release_source_manifest.json": (
        "ea201edeba978e1d0b3cf6219cc16efa"
        "c8641567216885c5a245c66e99fc9c2d"
    ),
    "app/db/repositories/workflow_state_repository.py": (
        "00241611109dc51d44c8e23f2b0940c1"
        "0f5488bf7cd4061597284679bdcfd90e"
    ),
    "migrations/versions/00241611109d_add_unique_wordpress_post_id.py": (
        "e1d29ed34fdbcaedb4a811681d8c2853"
        "4682f8ce2d1144d044c0cb6dd0f3054a"
    ),
    "scripts/run_slack_approval_socket.py": (
        "c2ab37a7e86fbdca79a456ed17a8c55"
        "b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
    ),
    "tests/test_slack_approval_socket_hold_remediation_offline.py": (
        "86dfc01686ffd53a2c6c7e73192d469d"
        "b5040bc38f6541031cb6f36e7846ed72"
    ),
}

EXPECTED_COMMANDS = [
    ["/usr/bin/sudo", "--", "/usr/bin/id", "-u"],
    ["/usr/bin/sudo", "--", "/usr/bin/test", "-e", target],
    ["/usr/bin/sudo", "--", "/usr/bin/test", "-L", target],
    [
        "/usr/bin/sudo",
        "--",
        "/usr/bin/stat",
        (
            "--printf=file_type=%F\\nowner_name=%U\\nowner_uid=%u\\n"
            "group_name=%G\\ngroup_gid=%g\\nmode=%a\\n"
        ),
        "--",
        target,
    ],
]

EXPECTED_OUTPUT_LINES = [
    "ROOT_CONTEXT_VERIFICATION=PASS",
    f"TARGET_PATH={target}",
    "TEST_EXISTS_EXIT_CODE=1",
    "TEST_SYMLINK_EXIT_CODE=1",
    "SUDOERS_DESTINATION_EXISTENCE_STATE=ABSENT_CONFIRMED",
    "SUDOERS_DESTINATION_SYMLINK_STATE=false",
    "ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED",
    "ROOT_READONLY_VERIFICATION_EXECUTED=true",
    "SUDOERS_CHANGED=false",
    (
        "NEXT_GATE="
        "HUMAN_REVIEW_3E_J_R2_R8_ROOT_READONLY_VERIFICATION_RESULT"
    ),
]

EXPECTED_GUARD_KEYS = {
    "approval_token_sha256",
    "verifier_sha256",
    "target_path",
    "started_at_utc",
    "verifier_exit_code",
    "completed_at_utc",
    "output_log_sha256",
}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_NOT_OBJECT:{path}")
    return value

def require_regular_nonsymlink(path: Path, label: str) -> os.stat_result:
    item = path.lstat()
    require(stat.S_ISREG(item.st_mode), f"{label}_NOT_REGULAR")
    require(not stat.S_ISLNK(item.st_mode), f"{label}_SYMLINK")
    return item

def parse_kv_lines(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        require("=" in line, "GUARD_LINE_WITHOUT_EQUALS")
        key, value = line.split("=", 1)
        require(key not in values, f"GUARD_DUPLICATE_KEY:{key}")
        values[key] = value
    require(set(values) == EXPECTED_GUARD_KEYS, "GUARD_EXACT_KEY_SET")
    require(len(lines) == 7, "GUARD_LINE_COUNT_NOT_7")
    return values

def parse_utc(value: str) -> datetime:
    require(
        re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value)
        is not None,
        "GUARD_TIMESTAMP_FORMAT",
    )
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return parsed.replace(tzinfo=timezone.utc)

# Root/path binding and fixed identities.
require(
    r2_root.relative_to(repo_root).as_posix().endswith(
        "i2f3e-j-r2-r8-r2-candidate-exact-file-set-correction-"
        "20260726T021229Z-524713"
    ),
    "R2_ROOT_BINDING",
)
require(packet_root == r2_root / "packet-snapshot", "PACKET_ROOT_BINDING")
require(
    candidate_root == packet_root / "candidate-artifacts",
    "CANDIDATE_ROOT_BINDING",
)
require(
    verifier_path
    == candidate_root / "root_readonly_sudoers_destination_verifier.sh",
    "VERIFIER_PATH_BINDING",
)
require(
    contract_path
    == candidate_root / "root-readonly-command-contract.json",
    "CONTRACT_PATH_BINDING",
)
require(
    candidate_manifest_path
    == candidate_root / "candidate-manifest.json",
    "CANDIDATE_MANIFEST_PATH_BINDING",
)
require(
    output_log_path.as_posix()
    == (
        "/tmp/tst_5d_w2b_i2f3e_j_r2_r8_"
        "root_readonly_verification_execution.txt"
    ),
    "OUTPUT_LOG_PATH_BINDING",
)
require(
    guard_dir.as_posix()
    == (
        "/tmp/ai-media-os-3e-j-r2-r8-root-readonly-"
        "verification-once-c1d53b3a.guard"
    ),
    "GUARD_PATH_BINDING",
)
require(
    attempt_record_path == guard_dir / "execution-attempt.txt",
    "ATTEMPT_RECORD_PATH_BINDING",
)

for label, (path, expected) in EXPECTED_SHA.items():
    require_regular_nonsymlink(path, label.upper())
    require(sha256(path) == expected, f"{label.upper()}_SHA")

for relative, expected in PROTECTED_SHA.items():
    path = repo_root / relative
    require_regular_nonsymlink(path, f"PROTECTED:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

# Guard structure and immutable execution-attempt record.
guard_item = guard_dir.lstat()
require(stat.S_ISDIR(guard_item.st_mode), "GUARD_NOT_DIRECTORY")
require(not stat.S_ISLNK(guard_item.st_mode), "GUARD_SYMLINK")
guard_entries = sorted(os.scandir(guard_dir), key=lambda item: item.name)
require(len(guard_entries) == 1, "GUARD_ENTRY_COUNT_NOT_1")
require(guard_entries[0].name == "execution-attempt.txt", "GUARD_ENTRY_NAME")
require(not guard_entries[0].is_symlink(), "ATTEMPT_RECORD_SYMLINK")
require(guard_entries[0].is_file(follow_symlinks=False), "ATTEMPT_NOT_FILE")

current_uid = os.getuid()
current_gid = os.getgid()
attempt_item = require_regular_nonsymlink(attempt_record_path, "ATTEMPT_RECORD")
output_item = require_regular_nonsymlink(output_log_path, "OUTPUT_LOG")
require(guard_item.st_uid == current_uid, "GUARD_OWNER")
require(attempt_item.st_uid == current_uid, "ATTEMPT_OWNER")
require(output_item.st_uid == current_uid, "OUTPUT_OWNER")
require(guard_item.st_gid == current_gid, "GUARD_GROUP")
require(attempt_item.st_gid == current_gid, "ATTEMPT_GROUP")
require(output_item.st_gid == current_gid, "OUTPUT_GROUP")
require(stat.S_IMODE(guard_item.st_mode) == 0o700, "GUARD_MODE_NOT_0700")
require(stat.S_IMODE(attempt_item.st_mode) == 0o600, "ATTEMPT_MODE_NOT_0600")
require(stat.S_IMODE(output_item.st_mode) == 0o600, "OUTPUT_MODE_NOT_0600")

attempt = parse_kv_lines(attempt_record_path)
require(attempt["approval_token_sha256"] == APPROVAL_TOKEN_SHA, "GUARD_TOKEN_SHA")
require(
    attempt["verifier_sha256"] == EXPECTED_SHA["verifier"][1],
    "GUARD_VERIFIER_SHA",
)
require(attempt["target_path"] == target, "GUARD_TARGET")
require(attempt["verifier_exit_code"] == "0", "GUARD_VERIFIER_EXIT_CODE")
require(
    attempt["output_log_sha256"] == EXPECTED_SHA["output_log"][1],
    "GUARD_OUTPUT_SHA",
)
started = parse_utc(attempt["started_at_utc"])
completed = parse_utc(attempt["completed_at_utc"])
require(started <= completed, "GUARD_TIMESTAMP_ORDER")

# Output log exact result evidence.
output_lines = output_log_path.read_text(encoding="utf-8").splitlines()
require(output_lines == EXPECTED_OUTPUT_LINES, "OUTPUT_LOG_EXACT_CONTENT")
require(output_lines.count("ROOT_CONTEXT_VERIFICATION=PASS") == 1, "ROOT_PASS_COUNT")
require(output_lines.count(f"TARGET_PATH={target}") == 1, "TARGET_COUNT")
require(output_lines.count("TEST_EXISTS_EXIT_CODE=1") == 1, "EXISTS_RC_COUNT")
require(output_lines.count("TEST_SYMLINK_EXIT_CODE=1") == 1, "SYMLINK_RC_COUNT")
require(
    output_lines.count(
        "SUDOERS_DESTINATION_EXISTENCE_STATE=ABSENT_CONFIRMED"
    )
    == 1,
    "ABSENT_STATE_COUNT",
)
require(
    output_lines.count("SUDOERS_DESTINATION_SYMLINK_STATE=false") == 1,
    "SYMLINK_FALSE_COUNT",
)
require(
    output_lines.count("ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED")
    == 1,
    "RESULT_ABSENT_COUNT",
)
require(
    output_lines.count("ROOT_READONLY_VERIFICATION_EXECUTED=true") == 1,
    "EXECUTED_TRUE_COUNT",
)
require(output_lines.count("SUDOERS_CHANGED=false") == 1, "UNCHANGED_COUNT")
require(
    not any(line.startswith("file_type=") for line in output_lines),
    "UNEXPECTED_FILE_TYPE_METADATA",
)
require(
    not any(line.startswith("owner_") for line in output_lines),
    "UNEXPECTED_OWNER_METADATA",
)
require(
    not any(line.startswith("group_") for line in output_lines),
    "UNEXPECTED_GROUP_METADATA",
)
require(
    not any(line.startswith("mode=") for line in output_lines),
    "UNEXPECTED_MODE_METADATA",
)

# Packet/contract/verifier remain fixed and enforce absent-before-stat behavior.
candidate_manifest = load_json(candidate_manifest_path)
require(candidate_manifest["target_path"] == target, "MANIFEST_TARGET")
require(
    candidate_manifest["root_readonly_verification_executed"] is False,
    "MANIFEST_PREP_EXECUTION_STATE",
)
require(
    candidate_manifest["sudo_execution_performed"] is False,
    "MANIFEST_PREP_SUDO_STATE",
)
require(candidate_manifest["sudoers_changed"] is False, "MANIFEST_SUDOERS_STATE")
require(
    candidate_manifest["candidate_deployed_to_production"] is False,
    "MANIFEST_DEPLOYMENT_STATE",
)

contract = load_json(contract_path)
require(contract["target_path"] == target, "CONTRACT_TARGET")
require(contract["command_count"] == 4, "CONTRACT_COMMAND_COUNT")
require(
    [item["argv"] for item in contract["commands"]] == EXPECTED_COMMANDS,
    "CONTRACT_EXACT_ARGV",
)
require(all(item["read_only"] is True for item in contract["commands"]), "READ_ONLY")
require(
    contract["required_execution_approval_value"] == APPROVAL_TOKEN,
    "CONTRACT_APPROVAL_TOKEN",
)
for key in (
    "additional_command_allowed",
    "additional_argument_allowed",
    "target_override_allowed",
    "stdin_input_allowed",
    "root_shell_allowed",
    "file_content_read_allowed",
    "file_write_allowed",
    "sudoers_change_allowed",
):
    require(contract[key] is False, f"CONTRACT_FALSE:{key}")

verifier = verifier_path.read_text(encoding="utf-8")
require(f'TARGET="{target}"' in verifier, "VERIFIER_TARGET")
require(f'REQUIRED_APPROVAL="{APPROVAL_TOKEN}"' in verifier, "VERIFIER_TOKEN")
require(verifier.count('"$SUDO_BIN" --') == 4, "VERIFIER_SUDO_CALL_SITES")
absent_marker = (
    'if [[ "$EXISTS_RC" -eq 1 && "$SYMLINK_RC" -eq 1 ]]; then'
)
stat_marker = 'STAT_OUTPUT="$('
require(absent_marker in verifier, "VERIFIER_ABSENT_BRANCH")
require(stat_marker in verifier, "VERIFIER_STAT_BRANCH")
require(
    verifier.index(absent_marker) < verifier.index(stat_marker),
    "VERIFIER_ABSENT_BRANCH_NOT_BEFORE_STAT",
)
absent_section = verifier[
    verifier.index(absent_marker):verifier.index(stat_marker)
]
require("exit 0" in absent_section, "VERIFIER_ABSENT_BRANCH_NO_EXIT")
require("%N" not in verifier, "VERIFIER_LINK_TARGET_DISCLOSURE")
for forbidden in ("cat ", "chmod ", "chown ", "rm ", "mv "):
    require(forbidden not in verifier, f"VERIFIER_FORBIDDEN:{forbidden}")

# Wrapper identity and one-shot sequencing.
wrapper = wrapper_path.read_text(encoding="utf-8")
require(
    'GUARD_DIR="/tmp/ai-media-os-3e-j-r2-r8-root-readonly-'
    'verification-once-c1d53b3a.guard"' in wrapper,
    "WRAPPER_GUARD_PATH",
)
require(
    'OUTPUT_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r8_'
    'root_readonly_verification_execution.txt"' in wrapper,
    "WRAPPER_OUTPUT_PATH",
)
require(wrapper.count('mkdir "$GUARD_DIR"') == 1, "WRAPPER_GUARD_CREATE_COUNT")
require(
    wrapper.count('/usr/bin/bash "$VERIFIER" 2>&1 | tee "$OUTPUT_LOG"') == 1,
    "WRAPPER_VERIFIER_INVOCATION_COUNT",
)
require(
    wrapper.index('mkdir "$GUARD_DIR"')
    < wrapper.index('/usr/bin/bash "$VERIFIER" 2>&1 | tee "$OUTPUT_LOG"'),
    "WRAPPER_GUARD_ORDER",
)
require('rm "$GUARD_DIR"' not in wrapper, "WRAPPER_GUARD_DELETE")
require('rm -r "$GUARD_DIR"' not in wrapper, "WRAPPER_GUARD_DELETE_RECURSIVE")
require("DO_NOT_DELETE_GUARD_OR_RETRY=true" in wrapper, "WRAPPER_NO_RETRY")
require(
    'echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"' in wrapper,
    "WRAPPER_NO_AUTO_DEPLOY",
)
require(
    'echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"'
    in wrapper,
    "WRAPPER_RUNNER_HOLD",
)
require(
    'echo "PRODUCTION_RELEASE_DECISION=HOLD"' in wrapper,
    "WRAPPER_RELEASE_HOLD",
)
require(
    'echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"' in wrapper,
    "WRAPPER_CANDIDATE_HOLD",
)

# Packet result keeps production boundary at HOLD.
packet_result = load_json(r2_root / "result.json")
for key in (
    "candidate_deployed_to_production",
    "production_directory_created",
    "production_file_created",
    "production_process_signal_sent",
    "production_database_sql_connection_used",
    "production_backup_created",
    "migration_executed",
    "external_network_used",
    "final_approval_token_created",
    "approval_binding_created",
):
    require(packet_result[key] is False, f"PACKET_RESULT_FALSE:{key}")
require(
    packet_result["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "PACKET_RUNNER_HOLD",
)
require(packet_result["writer_freeze_execution"] == "HOLD", "PACKET_WRITER_HOLD")
require(
    packet_result["production_release_decision"] == "HOLD",
    "PACKET_RELEASE_HOLD",
)
require(
    packet_result["release_status"] == "CANDIDATE_NOT_APPROVED",
    "PACKET_CANDIDATE_HOLD",
)

print("R2_R8_RESULT_FIXED_PACKET_SHA_REVIEW=PASS")
print("R2_R8_RESULT_FIXED_VERIFIER_SHA_REVIEW=PASS")
print("R2_R8_RESULT_FIXED_COMMAND_CONTRACT_SHA_REVIEW=PASS")
print("R2_R8_RESULT_EXECUTED_WRAPPER_SHA_REVIEW=PASS")
print("R2_R8_RESULT_OUTPUT_LOG_SHA_REVIEW=PASS")
print("R2_R8_ONE_SHOT_GUARD_EXISTS=true")
print("R2_R8_ONE_SHOT_GUARD_EXACT_ENTRY_COUNT=1")
print("R2_R8_ONE_SHOT_GUARD_MODE=0700")
print("R2_R8_EXECUTION_ATTEMPT_RECORD_MODE=0600")
print("R2_R8_OUTPUT_LOG_MODE=0600")
print("R2_R8_EXECUTION_ATTEMPT_RECORD_EXACT_KEY_SET_REVIEW=PASS")
print("R2_R8_EXECUTION_APPROVAL_TOKEN_SHA_REVIEW=PASS")
print("R2_R8_EXECUTION_ATTEMPT_TARGET_REVIEW=PASS")
print("R2_R8_EXECUTION_ATTEMPT_VERIFIER_SHA_REVIEW=PASS")
print("R2_R8_EXECUTION_ATTEMPT_VERIFIER_EXIT_CODE=0")
print("R2_R8_EXECUTION_ATTEMPT_OUTPUT_LOG_SHA_REVIEW=PASS")
print("R2_R8_EXECUTION_ATTEMPT_TIMESTAMP_REVIEW=PASS")
print(f"R2_R8_EXECUTION_STARTED_AT_UTC={attempt['started_at_utc']}")
print(f"R2_R8_EXECUTION_COMPLETED_AT_UTC={attempt['completed_at_utc']}")
print("R2_R8_OUTPUT_LOG_EXACT_CONTENT_REVIEW=PASS")
print("ROOT_CONTEXT_VERIFICATION=PASS")
print(f"TARGET_PATH={target}")
print("TEST_EXISTS_EXIT_CODE=1")
print("TEST_SYMLINK_EXIT_CODE=1")
print("SUDOERS_DESTINATION_EXISTENCE_STATE=ABSENT_CONFIRMED")
print("SUDOERS_DESTINATION_SYMLINK_STATE=false")
print("ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED")
print("ROOT_READONLY_VERIFICATION_EXECUTED=true")
print("SUDOERS_CHANGED=false")
print("R2_R8_ABSENT_BRANCH_BEFORE_STAT_STATIC_REVIEW=PASS")
print("R2_R8_STAT_METADATA_OUTPUT_PRESENT=false")
print("R2_R8_FIXED_COMMAND_ARGV_REVIEW=PASS")
print("R2_R8_SUDOERS_CONTENT_READ_ALLOWED=false")
print("R2_R8_SUDOERS_CHANGE_ALLOWED=false")
print("R2_R8_WRAPPER_ONE_SHOT_GUARD_ORDER_REVIEW=PASS")
print("R2_R8_WRAPPER_VERIFIER_INVOCATION_COUNT=1")
print("R2_R8_ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1")
print("R2_R8_ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
print("PROTECTED_SHA_REVIEW=PASS")
print("AUTOMATIC_DEPLOYMENT_PERFORMED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "WRAPPER_EXIT_CODE_LOCAL_PERSISTED_EVIDENCE="
    "NOT_AVAILABLE_OUTPUT_LOG_CONTAINS_VERIFIER_ONLY"
)
print(
    "WRAPPER_EXIT_CODE_USER_PROVIDED_CONSOLE_TRANSCRIPT=0"
)
print(
    "R2_R8_ROOT_READONLY_VERIFICATION_RESULT_HUMAN_REVIEW="
    "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER"
)
print(
    "R2_R8_RESULT_HUMAN_REVIEW_DECISION="
    "APPROVE_ABSENT_CONFIRMED_WITH_DEPLOYMENT_HOLD"
)
print(
    "NEXT_GATE="
    "HUMAN_APPROVAL_FOR_3E_J_R2_R8_R3_ROOT_READONLY_RESULT_"
    "EVIDENCE_REGISTRATION_AND_SEAL_PACKET_PREPARATION_NO_EXECUTION"
)
PY

printf '\n===== FINAL READ-ONLY HUMAN REVIEW MARKERS =====\n'

echo "R2_R8_ROOT_READONLY_VERIFICATION_RESULT_HUMAN_REVIEW=PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER"
echo "R2_R8_RESULT_HUMAN_REVIEW_DECISION=APPROVE_ABSENT_CONFIRMED_WITH_DEPLOYMENT_HOLD"
echo "ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED"
echo "ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1"
echo "ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1"
echo "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false"
echo "ONE_SHOT_GUARD_CHANGE_ALLOWED=false"
echo "SUDOERS_CHANGED=false"
echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
echo "WRITER_FREEZE_EXECUTION=HOLD"
echo "PRODUCTION_RELEASE_DECISION=HOLD"
echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
echo "NEXT_GATE=HUMAN_APPROVAL_FOR_3E_J_R2_R8_R3_ROOT_READONLY_RESULT_EVIDENCE_REGISTRATION_AND_SEAL_PACKET_PREPARATION_NO_EXECUTION"
echo "REVIEW_COMMAND_EXIT_CODE=0"
