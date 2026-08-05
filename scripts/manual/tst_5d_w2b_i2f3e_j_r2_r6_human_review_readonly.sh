#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

R1_REL="${BASE_REL}/i2f3e-j-r1-root-scan-late-exit-correction-blocked-no-execution-20260725T161929Z-515154"
R1_ROOT="${REPO_ROOT}/${R1_REL}"

R6_REL="${BASE_REL}/i2f3e-j-r2-r6-negative-test-log-marker-correction-20260725T170657Z-517926"
R6_ROOT="${REPO_ROOT}/${R6_REL}"
PACKET_ROOT="${R6_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
INVENTORY_ROOT="${R6_ROOT}/readonly-inventory"
LOG_ROOT="${R6_ROOT}/validation-logs"

REVIEW_OUT="/tmp/tst_5d_w2b_i2f3e_j_r2_r6_human_review.txt"

EXPECTED_RESULT_SHA="a6af278eb38b31590b8dfb3ffc03a8ab0227419a2ceea467561660b3b0e8add0"
EXPECTED_PACKET_MANIFEST_SHA="06c10cfdb7c83c0699c73caeb7248d8429027e27c6d696c437bac38aad3eaa66"
EXPECTED_SEMANTIC_SHA="df0463ac59afc44d06f00b1908376dd4c706db47493602989e4831faddc7fb2f"
EXPECTED_EVIDENCE_MANIFEST_SHA="347a0032bd4b68db531661249e10886c6ce79f2b3db70fc15413f88a0bbe4d16"

EXPECTED_CANDIDATE_MANIFEST_SHA="24ca0a5c3850f781b4a9e89cfbb09f916209c57304069923040fe7e69698e8de"
EXPECTED_DEPLOYMENT_CONTRACT_SHA="de88aeca1165215805479a5ac10d8b5fa1d42436f439277cd367950af377d2ac"
EXPECTED_DEPLOYED_POLICY_SHA="ad1f468a95637ebb0fffee672120befd465e6ca7b49251a23117d20d32cfb3cc"
EXPECTED_SUDOERS_CANDIDATE_SHA="6065c383265267f99a44326cf523594d3aeae0eccf1970c8ec940733cc479986"
EXPECTED_SUDO_COMMAND_CONTRACT_SHA="e34323dda92f9cd773108d6e27d9ab1e903ff7c195a77ef39577bca2bc7604cd"

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
    "packet-snapshot/candidate-artifacts/r2-candidate-manifest.json"
    "packet-snapshot/candidate-artifacts/deployment-contract.json"
    "packet-snapshot/candidate-artifacts/blocked-deployment-planner.py"
    "packet-snapshot/candidate-artifacts/runtime/runner-policy.json"
    "packet-snapshot/candidate-artifacts/runtime/one_shot_writer_freeze_backup_restart_runner.py"
    "packet-snapshot/candidate-artifacts/runtime/root_fd_metadata_helper.py"
    "packet-snapshot/candidate-artifacts/authorization/ai-media-os-3e-j-root-helper.sudoers"
    "packet-snapshot/candidate-artifacts/authorization/sudo-command-contract.json"
    "packet-snapshot/candidate-artifacts/validate_3e_j_r2_deployment_authorization_packet.py"
    "packet-snapshot/candidate-artifacts/test_3e_j_r2_deployment_authorization_negative.py"
    "readonly-inventory/repository-layout-inventory.json"
    "readonly-inventory/sudoers-metadata-inventory.json"
    "readonly-inventory/sudo-readonly-inventory.json"
    "readonly-inventory/planned-destination-readiness.json"
    "validation-logs/python-compile.log"
    "validation-logs/r2-validator.log"
    "validation-logs/r2-negative-tests.log"
    "validation-logs/deployment-plan-validation.log"
    "validation-logs/deployment-apply-block.log"
    "validation-logs/visudo-isolated-check.log"
    "validation-logs/protected-sha-after.log"
  )

  for name in "${required_files[@]}"; do
    test -f "$R6_ROOT/$name"
    printf 'FILE_PRESENT=%s\n' "$name"
  done

  printf '\n===== R2-R6 FIXED SHA CHECK =====\n'

  echo "$EXPECTED_RESULT_SHA  $R6_ROOT/result.json" | sha256sum -c -
  echo "$EXPECTED_PACKET_MANIFEST_SHA  $PACKET_ROOT/packet-manifest.json" | sha256sum -c -
  echo "$EXPECTED_SEMANTIC_SHA  $PACKET_ROOT/packet-semantic-validation.json" | sha256sum -c -
  echo "$EXPECTED_EVIDENCE_MANIFEST_SHA  $R6_ROOT/evidence-manifest.txt" | sha256sum -c -

  echo "$EXPECTED_CANDIDATE_MANIFEST_SHA  $CANDIDATE_ROOT/r2-candidate-manifest.json" | sha256sum -c -
  echo "$EXPECTED_DEPLOYMENT_CONTRACT_SHA  $CANDIDATE_ROOT/deployment-contract.json" | sha256sum -c -
  echo "$EXPECTED_DEPLOYED_POLICY_SHA  $CANDIDATE_ROOT/runtime/runner-policy.json" | sha256sum -c -
  echo "$EXPECTED_SUDOERS_CANDIDATE_SHA  $CANDIDATE_ROOT/authorization/ai-media-os-3e-j-root-helper.sudoers" | sha256sum -c -
  echo "$EXPECTED_SUDO_COMMAND_CONTRACT_SHA  $CANDIDATE_ROOT/authorization/sudo-command-contract.json" | sha256sum -c -

  printf '\n===== SOURCE 3E-J-R1 IMMUTABILITY CHECK =====\n'

  sha256sum -c <<SHAS
0e655aaf36f47b8e516665f586e9d1b1427804ee0fb99d959323b30bf8388476  $R1_ROOT/result.json
29cdf5074b7c8c1bb2bdf3801048d682a98f116f6c014e5463ad5a452c5ee447  $R1_ROOT/packet-snapshot/packet-manifest.json
b668a621b58459f0ef8dc62cdf25b3665ab8e8db51127bb15d381bb1e1b065fe  $R1_ROOT/packet-snapshot/packet-semantic-validation.json
c22f6084056a0175c04c0437d981e975e820364335af3acfdfb4ef4f77341430  $R1_ROOT/evidence-manifest.txt
SHAS

  printf '\n===== PACKET CONTENT REVIEW =====\n'

  python3 - "$R6_ROOT" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
packet = root / "packet-snapshot"
candidate = packet / "candidate-artifacts"
inventory = root / "readonly-inventory"
logs = root / "validation-logs"

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

result = load(root / "result.json")
packet_manifest = load(packet / "packet-manifest.json")
semantic = load(packet / "packet-semantic-validation.json")
summary = load(packet / "preparation-summary.json")
candidate_manifest = load(candidate / "r2-candidate-manifest.json")
contract = load(candidate / "deployment-contract.json")
policy = load(candidate / "runtime/runner-policy.json")
command_contract = load(
    candidate / "authorization/sudo-command-contract.json"
)
readiness = load(inventory / "planned-destination-readiness.json")
sudo_inventory = load(inventory / "sudo-readonly-inventory.json")

assert result["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R6"
assert result["result"] == (
    "PASS_W2B_I2F3E_J_R2_R6_NEGATIVE_TEST_LOG_"
    "MARKER_CORRECTION_PREPARED_NO_EXECUTION"
)
assert result["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert result["wrapper_phase"] == "TST-5D-W2B-I2F-3E-J-R2-R6"
assert result["candidate_packet_phase"] == (
    "TST-5D-W2B-I2F-3E-J-R2-R3"
)
assert result["candidate_phase_binding_resolved"] is True
assert result["candidate_packet_status"] == (
    "DEPLOYMENT_AND_AUTHORIZATION_PACKET_"
    "PLANNER_PERMISSION_SAFE_PREPARED_NO_EXECUTION"
)
assert result["candidate_status_binding_resolved"] is True
assert result["negative_test_ok_match_method"] == (
    "EXACT_STANDALONE_LINE"
)
assert result["negative_test_ok_line_required"] is True
assert result["negative_test_ok_must_be_final_bytes"] is False
assert result["permission_safe_metadata_correction_preserved"] is True
assert result["planner_permission_safe_metadata"] is True
assert result["planner_metadata_unknown_is_hold"] is True
assert result["expected_planner_block_capture_method"] == (
    "IF_CONDITION_NO_ERR_TRAP"
)
assert result["expected_planner_block_exit_code"] == 2
assert result["python_compile"] == "PASS"
assert result["validator"] == "PASS"
assert result["negative_test_count"] == 13
assert result["negative_tests"] == "PASS"
assert result["planner_validation"] == "PASS"
assert result["planner_apply_block"] == "PASS_EXPECTED_BLOCK"
assert result["visudo_isolated_syntax_check"] == "PASS"
assert result["deployment_authorization_packet_status"] == (
    "HOLD_PENDING_CONDITION_RESOLUTION"
)
assert result["artifact_destinations_absent"] is True
assert result["artifact_destination_metadata_complete"] is True
assert result["sudoers_destination_absent"] is False
assert result["sudoers_destination_metadata_complete"] is False
assert result["sudoers_destination_existence_state"] == (
    "UNKNOWN_PERMISSION_DENIED"
)
assert result["existing_exact_root_helper_authorization"] is False
assert result["raw_sudo_list_saved"] is False
assert result["candidate_deployed_to_production"] is False
assert result["production_directory_created"] is False
assert result["production_file_created"] is False
assert result["chmod_performed"] is False
assert result["chown_performed"] is False
assert result["group_changed"] is False
assert result["sudoers_changed"] is False
assert result["final_approval_token_created"] is False
assert result["approval_binding_created"] is False
assert result["process_signal_sent"] is False
assert result["writer_stop_performed"] is False
assert result["gui_stopped_or_restarted"] is False
assert result["production_database_sql_connection_used"] is False
assert result["production_backup_created"] is False
assert result["restore_executed"] is False
assert result["migration_executed"] is False
assert result["production_manifest_modified"] is False
assert result["git_add_performed"] is False
assert result["git_commit_performed"] is False
assert result["production_deployment_performed"] is False
assert result["external_network_used"] is False
assert result["writer_freeze_execution"] == "HOLD"
assert result["production_release_decision"] == "HOLD"
assert result["release_status"] == "CANDIDATE_NOT_APPROVED"
assert result["next_gate"] == (
    "HUMAN_REVIEW_3E_J_R2_R6_LOG_VALIDATED_"
    "DEPLOYMENT_AUTHORIZATION_PACKET"
)

assert candidate_manifest["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R3"
assert candidate_manifest["status"] == (
    "DEPLOYMENT_AND_AUTHORIZATION_PACKET_"
    "PLANNER_PERMISSION_SAFE_PREPARED_NO_EXECUTION"
)
assert candidate_manifest["planner_permission_safe_metadata"] is True
assert candidate_manifest["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert len(candidate_manifest["files"]) == 13

for item in candidate_manifest["files"]:
    artifact = candidate / item["name"]
    assert artifact.is_file(), artifact
    assert sha256(artifact) == item["sha256"], artifact
    assert artifact.stat().st_size == item["size_bytes"], artifact

assert contract["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R3"
assert contract["status"] == "PACKET_PREPARATION_ONLY_NO_EXECUTION"
assert contract["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert contract["deployment_root"]["owner"] == "root"
assert contract["deployment_root"]["group"] == "root"
assert contract["deployment_root"]["mode"] == "0755"
assert contract["deployment_root"]["deploy_user_write_allowed"] is False
for artifact in contract["artifacts"]:
    assert artifact["exclusive_create_required"] is True
    assert artifact["overwrite_allowed"] is False
    assert artifact["symlink_allowed"] is False
    assert artifact["owner"] == "root"
    assert artifact["group"] == "root"
    assert artifact["source_sha256"] == (
        artifact["destination_sha256_required"]
    )

assert contract["sudoers"]["owner"] == "root"
assert contract["sudoers"]["group"] == "root"
assert contract["sudoers"]["mode"] == "0440"
assert contract["sudoers"]["exclusive_create_required"] is True
assert contract["sudoers"]["overwrite_allowed"] is False
assert contract["sudoers"]["wildcard_allowed"] is False
assert contract["sudoers"]["setenv_allowed"] is False
assert contract["sudoers"]["arbitrary_argument_allowed"] is False
assert contract["sudoers"]["allowed_command_count"] == 2

assert command_contract["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R3"
assert len(command_contract["allowed_commands"]) == 2
assert command_contract["wildcard_allowed"] is False
assert command_contract["setenv_allowed"] is False
assert command_contract["arbitrary_argument_allowed"] is False
assert command_contract["shell_allowed"] is False
assert command_contract["editor_allowed"] is False
assert command_contract["environment_inheritance_allowed"] is False
assert command_contract["command_substitution_allowed"] is False

assert policy["phase"] == (
    "TST-5D-W2B-I2F-3E-J-R2-R3-DEPLOYMENT-SHADOW"
)
assert policy["deployment_status"] == "NOT_DEPLOYED_PACKET_ONLY"
assert policy["planner_metadata_permission_safe"] is True
assert policy["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)

assert readiness["artifact_destinations_absent"] is True
assert readiness["artifact_destination_metadata_complete"] is True
assert readiness["sudoers_destination_absent"] is False
assert readiness["sudoers_destination_metadata_complete"] is False
assert readiness["sudoers_destination_state"]["existence_state"] == (
    "UNKNOWN_PERMISSION_DENIED"
)
assert readiness["deployment_authorization_packet_status"] == (
    "HOLD_PENDING_CONDITION_RESOLUTION"
)
assert readiness["production_directory_created"] is False
assert readiness["production_file_created"] is False
assert readiness["chmod_performed"] is False
assert readiness["chown_performed"] is False
assert readiness["sudoers_changed"] is False

assert sudo_inventory["raw_sudo_list_saved"] is False
assert sudo_inventory["exact_helper_path_match_count"] == 0
assert not any(
    sudo_inventory["exact_command_authorized"].values()
)

assert packet_manifest["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R6"
assert packet_manifest["packet_file_count_excluding_manifest"] == 17
assert len(packet_manifest["packet_files"]) == 17
assert packet_manifest["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert packet_manifest["deployment_authorization_packet_status"] == (
    "HOLD_PENDING_CONDITION_RESOLUTION"
)
assert packet_manifest["candidate_deployed_to_production"] is False
assert packet_manifest["sudoers_changed"] is False

expected_packet = {
    item["name"] for item in packet_manifest["packet_files"]
}
actual_packet = {
    path.relative_to(packet).as_posix()
    for path in packet.rglob("*")
    if path.is_file() and path.name != "packet-manifest.json"
}
assert expected_packet == actual_packet
for item in packet_manifest["packet_files"]:
    artifact = packet / item["name"]
    assert sha256(artifact) == item["sha256"]
    assert artifact.stat().st_size == item["size_bytes"]

assert semantic["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R6"
assert semantic["runner_status"] == (
    "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
)
assert semantic["candidate_phase_binding_resolved"] is True
assert semantic["candidate_status_binding_resolved"] is True
assert semantic["planner_permission_safe_metadata"] is True
assert semantic["planner_metadata_unknown_is_hold"] is True
assert semantic["deployment_authorization_packet_status"] == (
    "HOLD_PENDING_CONDITION_RESOLUTION"
)
assert semantic["candidate_deployed_to_production"] is False
assert semantic["sudoers_changed"] is False
assert semantic["final_approval_token_created"] is False
assert semantic["approval_binding_created"] is False
assert semantic["process_signal_sent"] is False
assert semantic["production_database_sql_connection_used"] is False
assert semantic["production_backup_created"] is False

assert summary["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R6"
assert summary["candidate_file_count"] == 14
assert summary["python_compile_file_count"] == 7
assert summary["negative_test_count"] == 13
assert summary["negative_tests"] == "PASS"
assert summary["planner_validation"] == "PASS"
assert summary["planner_apply_block"] == "PASS_EXPECTED_BLOCK"
assert summary["visudo_isolated_syntax_check"] == "PASS"

compile_log = (logs / "python-compile.log").read_text(encoding="utf-8")
validator_log = (logs / "r2-validator.log").read_text(encoding="utf-8")
negative_log = (logs / "r2-negative-tests.log").read_text(encoding="utf-8")
planner_log = (
    logs / "deployment-plan-validation.log"
).read_text(encoding="utf-8")
apply_log = (
    logs / "deployment-apply-block.log"
).read_text(encoding="utf-8")
visudo_log = (
    logs / "visudo-isolated-check.log"
).read_text(encoding="utf-8")
protected_log = (
    logs / "protected-sha-after.log"
).read_text(encoding="utf-8")

assert compile_log.count("PYTHON_COMPILE_PASS=") == 7
for marker in (
    "VALIDATION=PASS",
    "DEPLOYMENT_CONTRACT_VALID=true",
    "PLANNER_PERMISSION_SAFE_METADATA=true",
    "PLANNER_METADATA_UNKNOWN_IS_HOLD=true",
    "RUNNER_SUDO_ARGV_BYTE_EQUIVALENT=true",
    "PRODUCTION_DEPLOYMENT_ALLOWED=false",
    "SUDOERS_CHANGED=false",
):
    assert marker in validator_log, marker

negative_lines = [line.strip() for line in negative_log.splitlines()]
assert "Ran 13 tests" in negative_log
assert negative_lines.count("OK") == 1
assert not any(
    line.startswith("FAILED") or line.startswith("ERROR")
    for line in negative_lines
)

assert (
    "DEPLOYMENT_STATUS="
    "BLOCKED_UNTIL_EXPLICIT_DEPLOYMENT_APPROVAL"
) in planner_log
assert "PRODUCTION_WRITE_PERFORMED=false" in planner_log
assert (
    "DEPLOYMENT_BLOCKED="
    "EXPLICIT_DEPLOYMENT_APPROVAL_REQUIRED"
) in apply_log
assert "PRODUCTION_WRITE_PERFORMED=false" in apply_log
assert "SUDOERS_CHANGED=false" in apply_log
assert "parsed OK" in visudo_log
assert protected_log.count(": OK") == 6

print("J_R2_R6_PREPARATION_EVIDENCE_REVIEW=PASS")
print("J_R2_R6_PACKET_INTEGRITY_REVIEW=PASS")
print("J_R2_R6_CANDIDATE_MANIFEST_REVIEW=PASS")
print("J_R2_R6_DEPLOYMENT_CONTRACT_REVIEW=PASS")
print("J_R2_R6_SUDO_COMMAND_CONTRACT_REVIEW=PASS")
print("J_R2_R6_VALIDATION_LOG_REVIEW=PASS")
print("J_R2_R6_PERMISSION_SAFE_METADATA_REVIEW=PASS")
print("J_R2_R6_EXPECTED_PLANNER_BLOCK_REVIEW=PASS")
print("J_R2_R6_NEGATIVE_TEST_LOG_REVIEW=PASS")
print("DEPLOYMENT_AUTHORIZATION_PACKET_STATUS=HOLD_PENDING_CONDITION_RESOLUTION")
print("SUDOERS_DESTINATION_EXISTENCE_STATE=UNKNOWN_PERMISSION_DENIED")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("SUDOERS_CHANGED=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("PRODUCTION_PROCESS_SIGNAL_SENT=false")
print("PRODUCTION_BACKUP_CREATED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
PY

  printf '\n===== EVIDENCE MANIFEST CONTENT CHECK =====\n'

  python3 - "$R6_ROOT" <<'PY'
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

  printf '\n===== EVIDENCE SEAL REVIEW =====\n'

  python3 - "$R6_ROOT" <<'PY'
from __future__ import annotations

import json
import stat
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1]).resolve()
repo = Path("/home/deploy/ai_media_os")
expected_uid = repo.stat().st_uid
expected_gid = repo.stat().st_gid

files = [path for path in root.rglob("*") if path.is_file()]
directories = [root] + [
    path for path in root.rglob("*") if path.is_dir()
]

file_modes = Counter(
    f"{stat.S_IMODE(path.stat().st_mode):04o}"
    for path in files
)
directory_modes = Counter(
    f"{stat.S_IMODE(path.stat().st_mode):04o}"
    for path in directories
)

all_files_0444 = all(
    stat.S_IMODE(path.stat().st_mode) == 0o444
    for path in files
)
all_directories_0555 = all(
    stat.S_IMODE(path.stat().st_mode) == 0o555
    for path in directories
)
all_owned_by_deploy = all(
    path.stat().st_uid == expected_uid
    and path.stat().st_gid == expected_gid
    for path in files + directories
)
symlink_count = sum(
    1 for path in root.rglob("*") if path.is_symlink()
)

seal_complete = (
    all_files_0444
    and all_directories_0555
    and all_owned_by_deploy
    and symlink_count == 0
)

print(f"EVIDENCE_FILE_COUNT={len(files)}")
print(f"EVIDENCE_DIRECTORY_COUNT={len(directories)}")
print(
    "EVIDENCE_FILE_MODE_DISTRIBUTION="
    + json.dumps(dict(sorted(file_modes.items())), sort_keys=True)
)
print(
    "EVIDENCE_DIRECTORY_MODE_DISTRIBUTION="
    + json.dumps(
        dict(sorted(directory_modes.items())),
        sort_keys=True,
    )
)
print(f"EVIDENCE_SYMLINK_COUNT={symlink_count}")
print(
    "ALL_EVIDENCE_FILES_MODE_0444="
    + str(all_files_0444).lower()
)
print(
    "ALL_EVIDENCE_DIRECTORIES_MODE_0555="
    + str(all_directories_0555).lower()
)
print(
    "ALL_EVIDENCE_OWNED_BY_DEPLOY="
    + str(all_owned_by_deploy).lower()
)
print(
    "EVIDENCE_SEAL_COMPLETE="
    + str(seal_complete).lower()
)

if seal_complete:
    print("EVIDENCE_SEAL_REVIEW=PASS")
    print(
        "J_R2_R6_RUNNER_APPROVAL_DECISION="
        "APPROVE_PACKET_CONTENT_WITH_EXECUTION_HOLD"
    )
    print(
        "NEXT_GATE="
        "ROOT_READONLY_SUDOERS_DESTINATION_VERIFICATION_PACKET"
    )
else:
    print(
        "EVIDENCE_SEAL_REVIEW="
        "FAIL_REQUIRES_R2_R7_SEAL_CORRECTION"
    )
    print(
        "J_R2_R6_RUNNER_APPROVAL_DECISION="
        "HOLD_PENDING_EVIDENCE_SEAL_CORRECTION"
    )
    print(
        "NEXT_GATE="
        "3E_J_R2_R7_EVIDENCE_SEAL_CORRECTION_NO_EXECUTION"
    )
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

  echo "J_R2_R6_PREPARATION_EVIDENCE_REVIEW=PASS"
  echo "J_R2_R6_PACKET_INTEGRITY_REVIEW=PASS"
  echo "J_R2_R6_CANDIDATE_MANIFEST_REVIEW=PASS"
  echo "J_R2_R6_DEPLOYMENT_CONTRACT_REVIEW=PASS"
  echo "J_R2_R6_SUDO_COMMAND_CONTRACT_REVIEW=PASS"
  echo "J_R2_R6_VALIDATION_LOG_REVIEW=PASS"
  echo "J_R2_R6_PERMISSION_SAFE_METADATA_REVIEW=PASS"
  echo "J_R2_R6_EXPECTED_PLANNER_BLOCK_REVIEW=PASS"
  echo "J_R2_R6_NEGATIVE_TEST_LOG_REVIEW=PASS"
  echo "DEPLOYMENT_AUTHORIZATION_PACKET_STATUS=HOLD_PENDING_CONDITION_RESOLUTION"
  echo "SUDOERS_DESTINATION_EXISTENCE_STATE=UNKNOWN_PERMISSION_DENIED"
  echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
  echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
  echo "PRODUCTION_DIRECTORY_CREATED=false"
  echo "PRODUCTION_FILE_CREATED=false"
  echo "CHMOD_PERFORMED=false"
  echo "CHOWN_PERFORMED=false"
  echo "SUDOERS_CHANGED=false"
  echo "FINAL_APPROVAL_TOKEN_CREATED=false"
  echo "APPROVAL_BINDING_CREATED=false"
  echo "PRODUCTION_PROCESS_SIGNAL_SENT=false"
  echo "WRITER_STOP_PERFORMED=false"
  echo "GUI_STOPPED_OR_RESTARTED=false"
  echo "PRODUCTION_DB_SQL_CONNECTION_USED=false"
  echo "PRODUCTION_BACKUP_CREATED=false"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"

) 2>&1 | tee "$REVIEW_OUT"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_OUT"
