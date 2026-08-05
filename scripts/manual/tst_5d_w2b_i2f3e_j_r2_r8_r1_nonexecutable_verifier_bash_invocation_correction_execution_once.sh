#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
R2_REL="${BASE_REL}/i2f3e-j-r2-r8-r2-candidate-exact-file-set-correction-20260726T021229Z-524713"
R2_ROOT="${REPO_ROOT}/${R2_REL}"
PACKET_ROOT="${R2_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"

VERIFIER="${CANDIDATE_ROOT}/root_readonly_sudoers_destination_verifier.sh"
CONTRACT="${CANDIDATE_ROOT}/root-readonly-command-contract.json"

TARGET="/etc/sudoers.d/ai-media-os-3e-j-root-helper"
APPROVAL_TOKEN="APPROVE_3E_J_R2_R8_ROOT_READONLY_SUDOERS_DESTINATION_VERIFICATION_EXECUTION"

EXPECTED_RESULT_SHA="b9706aaa71dee9ee3de527bcaa7ca114fec03f5f63220a4a220cd3f417e979ac"
EXPECTED_PACKET_MANIFEST_SHA="41d3e08bcd454307d1f51dcfd185f68f0ac56f96cb85a3bb5f029c5ddd902450"
EXPECTED_EVIDENCE_MANIFEST_SHA="b9516b7e4041abfd969866748a8c6a7cf98d623bed501fd1d50c59d647250971"
EXPECTED_CANDIDATE_MANIFEST_SHA="c1d53b3ac8dac86435dde89d4cfe021e1573a000747ce303ebcf62a5fb1c39ec"
EXPECTED_VERIFIER_SHA="bd555f07ba09c72e211ab1ae5d1af3b8c544a87ff5204ab8d476cb8923fddd93"
EXPECTED_CONTRACT_SHA="d7f6caa8a5c7b4eee4e343a8b6350ab8e0ad378a6c704d175834c9ed0561b2f8"

GUARD_DIR="/tmp/ai-media-os-3e-j-r2-r8-root-readonly-verification-once-c1d53b3a.guard"
OUTPUT_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r8_root_readonly_verification_execution.txt"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "DIRECT_ROOT_EXECUTION_FORBIDDEN=true" >&2
  exit 2
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 2
fi

test -d "$R2_ROOT"
test -d "$CANDIDATE_ROOT"
test -f "$VERIFIER"
test -f "$CONTRACT"
if [[ ! -r "$VERIFIER" ]]; then
  echo "FIXED_VERIFIER_READABLE=false" >&2
  exit 2
fi
test -x /usr/bin/bash
test -x "${REPO_ROOT}/.venv/bin/python"

cd "$REPO_ROOT"

echo "CORRECTION_LABEL=NONEXECUTABLE_0640_VERIFIER_BASH_INVOCATION"
echo "SOURCE_EXECUTION_WRAPPER_RESULT=FAILED_PRE_GUARD_TEST_X_NO_ROOT_EXECUTION"
echo "FIXED_VERIFIER_INVOKED_VIA=/usr/bin/bash"
echo "FIXED_VERIFIER_CONTENT_CHANGED=false"
echo "ROOT_READONLY_VERIFICATION_PREVIOUS_ATTEMPT_CONSUMED=false"

printf '\n===== PRE-EXECUTION FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
${EXPECTED_RESULT_SHA}  ${R2_ROOT}/result.json
${EXPECTED_PACKET_MANIFEST_SHA}  ${PACKET_ROOT}/packet-manifest.json
${EXPECTED_EVIDENCE_MANIFEST_SHA}  ${R2_ROOT}/evidence-manifest.txt
${EXPECTED_CANDIDATE_MANIFEST_SHA}  ${CANDIDATE_ROOT}/candidate-manifest.json
${EXPECTED_VERIFIER_SHA}  ${VERIFIER}
${EXPECTED_CONTRACT_SHA}  ${CONTRACT}
SHAS

printf '\n===== PRE-EXECUTION CONTRACT REVIEW =====\n'

"${REPO_ROOT}/.venv/bin/python" -B - \
  "$CONTRACT" \
  "$VERIFIER" \
  "$TARGET" \
  "$APPROVAL_TOKEN" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

contract_path = Path(sys.argv[1]).resolve(strict=True)
verifier_path = Path(sys.argv[2]).resolve(strict=True)
target = sys.argv[3]
approval_token = sys.argv[4]

expected_commands = [
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

contract = json.loads(contract_path.read_text(encoding="utf-8"))
verifier = verifier_path.read_text(encoding="utf-8")

assert contract["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R8"
assert contract["target_path"] == target
assert contract["command_count"] == 4
assert [item["argv"] for item in contract["commands"]] == expected_commands
assert all(item["read_only"] is True for item in contract["commands"])

assert (
    contract["required_execution_approval_environment_variable"]
    == "R2_R8_ROOT_READONLY_VERIFICATION_APPROVED"
)
assert contract["required_execution_approval_value"] == approval_token

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
    assert contract[key] is False, key

assert verifier_path.stat().st_mode & 0o777 == 0o640
assert f'TARGET="{target}"' in verifier
assert f'REQUIRED_APPROVAL="{approval_token}"' in verifier
assert 'if [[ "$#" -ne 0 ]]' in verifier
assert verifier.count('"$SUDO_BIN" --') == 4
assert "cat " not in verifier
assert "chmod " not in verifier
assert "chown " not in verifier
assert "rm " not in verifier
assert "mv " not in verifier
assert "/bin/sh" not in verifier
assert "/bin/bash" not in verifier
assert "python" not in verifier.lower()
assert "%N" not in verifier

print("PRE_EXECUTION_CONTRACT_REVIEW=PASS")
print("TARGET_PATH_FIXED=true")
print("COMMAND_COUNT=4")
print("COMMAND_ARGV_EXACT=true")
print("APPROVAL_GATE_EXACT=true")
print("ADDITIONAL_ARGUMENT_ALLOWED=false")
print("ROOT_SHELL_ALLOWED=false")
print("FILE_CONTENT_READ_ALLOWED=false")
print("FILE_WRITE_ALLOWED=false")
print("SUDOERS_CHANGE_ALLOWED=false")
PY

printf '\n===== ONE-SHOT GUARD =====\n'

if ! mkdir "$GUARD_DIR" 2>/dev/null; then
  echo "ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1" >&2
  echo "ONE_SHOT_GUARD_STATE=ALREADY_CONSUMED_OR_PRESENT" >&2
  echo "ROOT_READONLY_VERIFICATION_EXECUTED=false" >&2
  echo "DO_NOT_DELETE_GUARD_OR_RETRY=true" >&2
  exit 2
fi

printf 'approval_token_sha256=%s\n' \
  "$(printf '%s' "$APPROVAL_TOKEN" | sha256sum | awk '{print $1}')" \
  > "${GUARD_DIR}/execution-attempt.txt"
printf 'verifier_sha256=%s\n' "$EXPECTED_VERIFIER_SHA" \
  >> "${GUARD_DIR}/execution-attempt.txt"
printf 'target_path=%s\n' "$TARGET" \
  >> "${GUARD_DIR}/execution-attempt.txt"
printf 'started_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "${GUARD_DIR}/execution-attempt.txt"

echo "ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1"
echo "ONE_SHOT_GUARD_CREATED=true"
echo "ONE_SHOT_GUARD=$GUARD_DIR"
echo "DO_NOT_DELETE_GUARD_OR_RETRY=true"

printf '\n===== ROOT READ-ONLY VERIFICATION EXECUTION =====\n'

set +e
R2_R8_ROOT_READONLY_VERIFICATION_APPROVED="$APPROVAL_TOKEN" \
  /usr/bin/bash "$VERIFIER" 2>&1 | tee "$OUTPUT_LOG"
VERIFIER_RC=${PIPESTATUS[0]}
set -e

printf 'verifier_exit_code=%s\n' "$VERIFIER_RC" \
  >> "${GUARD_DIR}/execution-attempt.txt"
printf 'completed_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "${GUARD_DIR}/execution-attempt.txt"
printf 'output_log_sha256=%s\n' \
  "$(sha256sum "$OUTPUT_LOG" | awk '{print $1}')" \
  >> "${GUARD_DIR}/execution-attempt.txt"

printf '\n===== EXECUTION RESULT BINDING =====\n'

echo "VERIFIER_EXIT_CODE=$VERIFIER_RC"
echo "ROOT_READONLY_VERIFICATION_OUTPUT_LOG=$OUTPUT_LOG"
echo "ROOT_READONLY_VERIFICATION_OUTPUT_LOG_SHA=$(sha256sum "$OUTPUT_LOG" | awk '{print $1}')"
echo "FIXED_VERIFIER_FILE_MODE=0640"
echo "FIXED_VERIFIER_INVOKED_VIA=/usr/bin/bash"
echo "FIXED_VERIFIER_CONTENT_CHANGED=false"
echo "ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1"
echo "ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1"
echo "SUDOERS_CONTENT_READ_ALLOWED=false"
echo "SUDOERS_CHANGE_ALLOWED=false"
echo "AUTOMATIC_DEPLOYMENT_ALLOWED=false"
echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
echo "WRITER_FREEZE_EXECUTION=HOLD"
echo "PRODUCTION_RELEASE_DECISION=HOLD"
echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
echo "NEXT_GATE=HUMAN_REVIEW_3E_J_R2_R8_ROOT_READONLY_VERIFICATION_RESULT"

if [[ "$VERIFIER_RC" -ne 0 ]]; then
  echo "ROOT_READONLY_VERIFICATION_WRAPPER_RESULT=VERIFIER_NONZERO_HOLD"
  echo "DO_NOT_RETRY=true"
  exit "$VERIFIER_RC"
fi

mapfile -t RESULT_LINES < <(
  grep '^ROOT_READONLY_VERIFICATION_RESULT=' "$OUTPUT_LOG" || true
)

if [[ "${#RESULT_LINES[@]}" -ne 1 ]]; then
  echo "ROOT_READONLY_VERIFICATION_WRAPPER_RESULT=RESULT_MARKER_INVALID_HOLD" >&2
  echo "DO_NOT_RETRY=true" >&2
  exit 2
fi

grep -Fx "ROOT_CONTEXT_VERIFICATION=PASS" "$OUTPUT_LOG" >/dev/null
grep -Fx "TARGET_PATH=$TARGET" "$OUTPUT_LOG" >/dev/null
grep -Fx "ROOT_READONLY_VERIFICATION_EXECUTED=true" "$OUTPUT_LOG" >/dev/null
grep -Fx "SUDOERS_CHANGED=false" "$OUTPUT_LOG" >/dev/null

case "${RESULT_LINES[0]}" in
  ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED|\
  ROOT_READONLY_VERIFICATION_RESULT=PRESENT_NON_SYMLINK_HOLD|\
  ROOT_READONLY_VERIFICATION_RESULT=PRESENT_SYMLINK_HOLD|\
  ROOT_READONLY_VERIFICATION_RESULT=DANGLING_SYMLINK_PRESENT_HOLD|\
  ROOT_READONLY_VERIFICATION_RESULT=STATE_UNRESOLVED_HOLD)
    ;;
  *)
    echo "ROOT_READONLY_VERIFICATION_WRAPPER_RESULT=UNRECOGNIZED_RESULT_HOLD" >&2
    echo "DO_NOT_RETRY=true" >&2
    exit 2
    ;;
esac

echo "ROOT_READONLY_VERIFICATION_WRAPPER_RESULT=PASS_RESULT_CAPTURED_HUMAN_REVIEW_REQUIRED"
echo "${RESULT_LINES[0]}"
echo "ROOT_READONLY_VERIFICATION_EXECUTED=true"
echo "SUDOERS_CHANGED=false"
echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
echo "DO_NOT_RETRY=true"
echo "WRAPPER_EXIT_CODE=0"
