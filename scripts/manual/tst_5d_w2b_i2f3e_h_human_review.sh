#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"
EVIDENCE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-h-gui-restart-environment-contract-readonly-20260725T144423Z-511462"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
REVIEW_OUT="/tmp/tst_5d_w2b_i2f3e_h_human_review.txt"

EXPECTED_RESULT_SHA="998e6dbbb3bfc2e9357b490c15e731b0c17e6370a9ec95798ca4592612e020fa"
EXPECTED_PACKET_MANIFEST_SHA="9dd2e603f69b277db0a115e2970317dc454c5c1346ff8f03a3733fd850fb08b3"
EXPECTED_SEMANTIC_SHA="933aff0c381859f46c9317ac5f704d729db2fff214a3b13c67fafdb619a521b3"
EXPECTED_EVIDENCE_MANIFEST_SHA="4f330c224f2cac61e58f7f2b25b7091eb622f40240e6efca049d3a87b745670d"
EXPECTED_IDENTITY_SHA="3dcadb53adeadac94cb1062d2a4e24c2a00d63a51c87991046b96cd7f0f6ba2a"

cd "$REPO_ROOT"

(
  set -Eeuo pipefail

  printf '\n===== REQUIRED FILES =====\n'

  required_files=(
    "result.json"
    "evidence-manifest.txt"
    "packet-snapshot/packet-manifest.json"
    "packet-snapshot/packet-semantic-validation.json"
    "packet-snapshot/environment-contract-resolution.json"
    "packet-snapshot/exact-restart-environment-contract.json"
    "packet-snapshot/minimal-environment-contract.json"
    "packet-snapshot/environment-variable-classification.json"
    "packet-snapshot/environment-source-file-metadata.json"
    "packet-snapshot/import-closure-static-analysis.json"
    "packet-snapshot/repository-environment-launch-search.json"
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

  python3 - \
    "$EVIDENCE_ROOT" \
    "$EXPECTED_IDENTITY_SHA" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
expected_identity_sha = sys.argv[2]
packet = root / "packet-snapshot"

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value

result = load(root / "result.json")
manifest = load(packet / "packet-manifest.json")
semantic = load(packet / "packet-semantic-validation.json")
resolution = load(packet / "environment-contract-resolution.json")
restart = load(packet / "exact-restart-environment-contract.json")
minimal = load(packet / "minimal-environment-contract.json")
classification = load(packet / "environment-variable-classification.json")
metadata = load(packet / "environment-source-file-metadata.json")
static = load(packet / "import-closure-static-analysis.json")
launch = load(packet / "repository-environment-launch-search.json")
before = load(packet / "protected-sha-before.json")
after = load(packet / "protected-sha-after.json")

assert result["phase"] == "TST-5D-W2B-I2F-3E-H"
assert result["result"] == (
    "PASS_W2B_I2F3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_RESOLUTION_READY"
)
assert result["current_gui_pid"] == 302168
assert result["process_identity_sha256"] == expected_identity_sha
assert result["visited_python_file_count"] == 30

expected_counts = {
    "STARTUP_REQUIRED": 0,
    "RUNTIME_REQUIRED": 0,
    "EXTERNAL_ACTION_ONLY": 7,
    "OPTIONAL": 2,
    "INHERITED_NOT_USED": 7,
    "UNRESOLVED": 0,
}
assert result["environment_classification_counts"] == expected_counts
assert result["blocking_environment_classification_count"] == 0
assert result["loader_pattern_blocker_count"] == 0
assert result["parse_error_blocker_count"] == 0
assert result["environment_contract_resolved"] is True
assert result["exact_stop_status"] == "RESOLVED_PENDING_HUMAN_REVIEW"
assert result["exact_restart_status"] == "RESOLVED_PENDING_HUMAN_REVIEW"
assert result["both_exact_routes_resolved"] is True
assert result["credential_file_content_read"] is False
assert result["environment_file_content_read"] is False
assert result["raw_live_environment_saved"] is False
assert result["secret_environment_values_saved"] is False
assert result["shell_history_inspected"] is False
assert result["writer_freeze_execution"] == "HOLD"
assert result["production_release_decision"] == "HOLD"
assert result["release_status"] == "CANDIDATE_NOT_APPROVED"
assert result["next_gate"] == (
    "HUMAN_REVIEW_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_PACKET"
)

assert semantic["result"] == (
    "PASS_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_RESOLUTION_READONLY"
)
assert semantic["environment_contract_resolved"] is True
assert semantic["exact_restart_status"] == "RESOLVED_PENDING_HUMAN_REVIEW"
assert semantic["both_exact_routes_resolved"] is True
assert semantic["classification_counts"] == expected_counts
assert semantic["blocking_classification_count"] == 0
assert semantic["loader_pattern_blocker_count"] == 0
assert semantic["parse_error_blocker_count"] == 0
assert semantic["credential_file_content_read"] is False
assert semantic["environment_file_content_read"] is False
assert semantic["live_environment_values_saved"] is False
assert semantic["secret_environment_values_saved"] is False
assert semantic["shell_history_inspected"] is False
assert semantic["protected_sha_unchanged"] is True
assert semantic["process_signal_sent"] is False
assert semantic["writer_stop_performed"] is False
assert semantic["gui_stopped_or_restarted"] is False
assert semantic["production_database_opened"] is False
assert semantic["sql_executed"] is False
assert semantic["external_network_used"] is False
assert semantic["writer_freeze_execution"] == "HOLD"

assert resolution["current_gui_pid"] == 302168
assert resolution["process_identity_sha256"] == expected_identity_sha
assert resolution["environment_contract_resolved"] is True
assert resolution["both_exact_routes_resolved"] is True
assert resolution["minimal_environment_contract_created"] is True
assert resolution["restart_execution_allowed"] is False
assert resolution["credential_file_content_read"] is False
assert resolution["environment_file_content_read"] is False
assert resolution["live_environment_values_saved"] is False
assert resolution["secret_environment_values_saved"] is False
assert resolution["shell_history_inspected"] is False

assert restart["status"] == "RESOLVED_PENDING_HUMAN_REVIEW"
assert restart["execution_allowed"] is False
assert restart["working_directory"] == "/home/deploy/ai_media_os"
assert restart["python_executable"] == (
    "/home/deploy/ai_media_os/.venv/bin/python"
)
assert restart["script_path"] == (
    "/home/deploy/ai_media_os/scripts/new_release_multistore_app.py"
)
assert restart["arguments"] == [
    "--repo-root", "/home/deploy/ai_media_os",
    "--host", "127.0.0.1",
    "--port", "8765",
]
assert restart["stdin"] == "/dev/null"
assert restart["stdout"] == (
    "/home/deploy/ai_media_os/logs/new_release_gui.log"
)
assert restart["stderr"] == (
    "/home/deploy/ai_media_os/logs/new_release_gui.log"
)
assert restart["background_mode"] == "DETACHED_BACKGROUND"
assert restart["pid_capture"]["method"] == (
    "SHELL_BACKGROUND_PID_AND_PROCESS_IDENTITY_EVIDENCE"
)
assert restart["pid_capture"]["future_pid_file"] is None
assert restart["pid_capture"]["pid_file_created_now"] is False
assert restart["pid_capture"]["pid_only_trust_forbidden"] is True
assert restart["readiness_check"]["host"] == "127.0.0.1"
assert restart["readiness_check"]["port"] == 8765
assert restart["readiness_check"]["external_network_required"] is False
assert restart["double_start_prevention"] == {
    "after_start_require_listener_owned_by_new_process": True,
    "after_start_require_one_matching_process": True,
    "before_start_require_port_free": True,
    "before_start_require_zero_matching_processes": True,
}
assert restart["blocking_environment_classifications"] == []
assert restart["loader_pattern_blockers"] == []
assert restart["parse_error_blockers"] == []
assert restart["writer_freeze_execution"] == "HOLD"

planned = restart["planned_shell_command_not_executed"]
assert "nohup env -i " in planned
assert "/home/deploy/ai_media_os/.venv/bin/python" in planned
assert "/home/deploy/ai_media_os/scripts/new_release_multistore_app.py" in planned
assert "--host 127.0.0.1" in planned
assert "--port 8765" in planned
assert "</dev/null" in planned
assert "logs/new_release_gui.log" in planned
assert "new_pid=$!" in planned
assert "NEW_GUI_PID=" in planned
assert "credential.env" not in planned
assert "source " not in planned
assert ". " not in planned

assert minimal["type"] == (
    "STATIC_MINIMAL_ENVIRONMENT_CONTRACT_NO_CREDENTIAL_FILE"
)
assert minimal["credential_file_loaded"] is False
assert minimal["credential_file_content_read"] is False
assert minimal["inherits_parent_environment"] is False
assert minimal["secret_variables_inherited"] == []
assert set(minimal["contract"]) == {
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "VIRTUAL_ENV",
    "PWD",
    "PYTHONUNBUFFERED",
}

assert classification["classification_counts"] == expected_counts
assert classification["dynamic_environment_usage_count"] == 0
assert classification["environment_values_read_for_output"] is False
assert classification["environment_values_saved"] is False
assert classification["secret_values_saved"] is False

allowed_classifications = {
    "STARTUP_REQUIRED",
    "RUNTIME_REQUIRED",
    "EXTERNAL_ACTION_ONLY",
    "OPTIONAL",
    "INHERITED_NOT_USED",
    "UNRESOLVED",
}
for item in classification["classifications"]:
    assert item["classification"] in allowed_classifications
    assert item["value_read_for_output"] is False
    assert item["value_saved"] is False

assert metadata["credential_file_content_read"] is False
assert metadata["environment_file_content_read"] is False
assert metadata["metadata_only"] is True
for candidate in metadata["candidates"]:
    assert candidate["content_read"] is False

assert static["analysis_method"] == "PYTHON_AST_STATIC_ONLY"
assert static["imports_executed"] is False
assert static["source_modified"] is False
assert static["parse_errors"] == []
assert static["loader_patterns"] == []
assert static["environment_file_references"] == []

assert launch["shell_history_inspected"] is False
assert launch["history_secret_values_saved"] is False
assert launch["source_modified"] is False

assert before["files"] == after["files"]

execution = result["execution"]
false_keys = [
    "process_signal_sent",
    "writer_stop_performed",
    "gui_stopped_or_restarted",
    "systemctl_stop_start_restart_executed",
    "service_created_or_modified",
    "cron_changed",
    "timer_changed",
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
print(f"PROCESS_IDENTITY_SHA={result['process_identity_sha256']}")
print(f"VISITED_PYTHON_FILE_COUNT={result['visited_python_file_count']}")
print("ENVIRONMENT_CONTRACT_RESOLVED=true")
print("EXACT_STOP_STATUS=RESOLVED_PENDING_HUMAN_REVIEW")
print("EXACT_RESTART_STATUS=RESOLVED_PENDING_HUMAN_REVIEW")
print("BOTH_EXACT_ROUTES_RESOLVED=true")
print("ENVIRONMENT_SOURCE_TYPE="
      + minimal["type"])
print("MINIMAL_ENV_KEYS=" + ",".join(sorted(minimal["contract"].keys())))
print("STARTUP_REQUIRED_COUNT=0")
print("RUNTIME_REQUIRED_COUNT=0")
print("EXTERNAL_ACTION_ONLY_COUNT=7")
print("OPTIONAL_COUNT=2")
print("INHERITED_NOT_USED_COUNT=7")
print("UNRESOLVED_COUNT=0")
print("LOADER_PATTERN_BLOCKER_COUNT=0")
print("PARSE_ERROR_BLOCKER_COUNT=0")
print("CREDENTIAL_FILE_CONTENT_READ=false")
print("ENVIRONMENT_FILE_CONTENT_READ=false")
print("RAW_LIVE_ENVIRONMENT_SAVED=false")
print("SECRET_ENVIRONMENT_VALUES_SAVED=false")
print("SHELL_HISTORY_INSPECTED=false")
print("PROTECTED_SHA_BEFORE_AFTER_EQUAL=true")
print("SAFETY_BOUNDARY_VALID=true")
PY

  printf '\n===== ENVIRONMENT NAME CLASSIFICATION =====\n'

  python3 - "$PACKET_ROOT/environment-variable-classification.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))

for item in sorted(
    payload["classifications"],
    key=lambda value: (
        value["classification"],
        value["variable_name"],
    ),
):
    print(
        f"{item['classification']}|"
        f"{item['variable_name']}|"
        f"secret_name_pattern={str(item['secret_name_pattern']).lower()}|"
        f"present_in_current_process="
        f"{str(item['present_in_current_process']).lower()}"
    )

print(
    "CLASSIFICATION_RECORD_COUNT="
    + str(len(payload["classifications"]))
)
print("ENVIRONMENT_VALUES_PRINTED=false")
PY

  printf '\n===== ENVIRONMENT SOURCE FILE METADATA =====\n'

  python3 - "$PACKET_ROOT/environment-source-file-metadata.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

for item in payload["candidates"]:
    print(
        f"PATH={item['path']}|"
        f"EXISTS={item['exists']}|"
        f"OWNER={item.get('owner')}|"
        f"GROUP={item.get('group')}|"
        f"MODE={item.get('mode')}|"
        f"SIZE={item.get('size_bytes')}|"
        f"CONTENT_READ={str(item['content_read']).lower()}"
    )

print("CREDENTIAL_FILE_CONTENT_READ=false")
print("ENVIRONMENT_FILE_CONTENT_READ=false")
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

assert manifest["packet_file_count_excluding_manifest"] == 11
assert len(manifest["packet_files"]) == 11
assert manifest["environment_contract_resolved"] is True
assert manifest["exact_stop_status"] == "RESOLVED_PENDING_HUMAN_REVIEW"
assert manifest["exact_restart_status"] == "RESOLVED_PENDING_HUMAN_REVIEW"
assert manifest["both_exact_routes_resolved"] is True
assert manifest["writer_freeze_execution"] == "HOLD"
assert manifest["production_release_decision"] == "HOLD"
assert manifest["release_status"] == "CANDIDATE_NOT_APPROVED"

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
print("PACKET_FILE_COUNT_EXCLUDING_MANIFEST=11")
print("PACKET_FILE_COUNT=12")
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

  echo "H_EXECUTION_EVIDENCE_REVIEW=PASS"
  echo "ENVIRONMENT_CONTRACT_REVIEW=PASS"
  echo "EXACT_STOP_ROUTE_REVIEW=PASS_PENDING_EXECUTION_APPROVAL"
  echo "EXACT_RESTART_ROUTE_REVIEW=PASS_PENDING_EXECUTION_APPROVAL"
  echo "BOTH_EXACT_ROUTES_RESOLVED=true"
  echo "MINIMAL_ENVIRONMENT_CONTRACT_REVIEW=PASS"
  echo "CREDENTIAL_FILE_CONTENT_READ=false"
  echo "ENVIRONMENT_FILE_CONTENT_READ=false"
  echo "RAW_LIVE_ENVIRONMENT_SAVED=false"
  echo "SECRET_ENVIRONMENT_VALUES_SAVED=false"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"

) 2>&1 | tee "$REVIEW_OUT"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_OUT"
