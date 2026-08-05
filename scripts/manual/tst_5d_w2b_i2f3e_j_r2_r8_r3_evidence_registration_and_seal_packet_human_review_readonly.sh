#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
R3_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-result-evidence-registration-and-seal-packet-preparation-20260726T030618Z-526407"
R3_ROOT="${REPO_ROOT}/${R3_REL}"
PACKET_ROOT="${R3_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
SNAPSHOT_ROOT="${PACKET_ROOT}/registration-input-snapshot"
LOG_ROOT="${PACKET_ROOT}/validation-logs"

EXPECTED_RESULT_SHA="158059471540ecf81cfc9e2d03b7bab69218a6c71e00f16fb34879c2e287a6d7"
EXPECTED_PACKET_MANIFEST_SHA="43221ebdaf1e092521072f10a1864e269a21f5ab064716638484068c50293665"
EXPECTED_CANDIDATE_MANIFEST_SHA="7c7fb60906b7215f5293608ded5f335644b8a5836b89a02cbbdb478e3d3973ed"
EXPECTED_SNAPSHOT_MANIFEST_SHA="afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c"
EXPECTED_EVIDENCE_MANIFEST_SHA="75aa57aa74c8300202d7b7c823118bc70d532aee622dfef67778c80abc49282a"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_REVIEW_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$R3_ROOT"
test -d "$PACKET_ROOT"
test -d "$CANDIDATE_ROOT"
test -d "$SNAPSHOT_ROOT"
test -d "$LOG_ROOT"

cd "$REPO_ROOT"

printf '\n===== R2-R8-R3 FIXED SHA READ-ONLY REVIEW =====\n'

sha256sum -c <<SHAS
${EXPECTED_RESULT_SHA}  ${R3_ROOT}/result.json
${EXPECTED_PACKET_MANIFEST_SHA}  ${PACKET_ROOT}/packet-manifest.json
${EXPECTED_CANDIDATE_MANIFEST_SHA}  ${CANDIDATE_ROOT}/candidate-manifest.json
${EXPECTED_SNAPSHOT_MANIFEST_SHA}  ${CANDIDATE_ROOT}/r2-r8-r3-snapshot-manifest.json
${EXPECTED_EVIDENCE_MANIFEST_SHA}  ${R3_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== R2-R8-R3 PACKET HUMAN REVIEW =====\n'

"$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$R3_ROOT" \
  "$PACKET_ROOT" \
  "$CANDIDATE_ROOT" \
  "$SNAPSHOT_ROOT" \
  "$LOG_ROOT" \
  "$R3_REL" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import pwd
import grp
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
r3_root = Path(sys.argv[2]).resolve(strict=True)
packet_root = Path(sys.argv[3]).resolve(strict=True)
candidate_root = Path(sys.argv[4]).resolve(strict=True)
snapshot_root = Path(sys.argv[5]).resolve(strict=True)
log_root = Path(sys.argv[6]).resolve(strict=True)
expected_r3_relative = sys.argv[7]

PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3"
TARGET = "/etc/sudoers.d/ai-media-os-3e-j-root-helper"

EXPECTED_FIXED_SHA = {
    "result.json": (
        "158059471540ecf81cfc9e2d03b7bab6"
        "9218a6c71e00f16fb34879c2e287a6d7"
    ),
    "packet-snapshot/packet-manifest.json": (
        "43221ebdaf1e092521072f10a1864e269"
        "a21f5ab064716638484068c50293665"
    ),
    "packet-snapshot/candidate-artifacts/candidate-manifest.json": (
        "7c7fb60906b7215f5293608ded5f3356"
        "44b8a5836b89a02cbbdb478e3d3973ed"
    ),
    "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json": (
        "afaa189fb6d9565ade2a5826449cc859"
        "f65f0358946deae21aae4703f414631c"
    ),
    "evidence-manifest.txt": (
        "75aa57aa74c8300202d7b7c823118bc7"
        "0d532aee622dfef67778c80abc49282a"
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

EXPECTED_CANDIDATE_FILES = {
    "candidate-manifest.json",
    "r2-r8-r3-registration-policy.json",
    "r2-r8-r3-source-contract.json",
    "r2-r8-r3-seal-contract.json",
    "r2-r8-r3-result-record.json",
    "r2-r8-r3-snapshot-manifest.json",
    "blocked_registration_and_seal_entrypoint.py",
    "validate_r2_r8_r3_packet.py",
    "test_r2_r8_r3_packet_negative.py",
    "r2-r8-r3-operation-manual.md",
}

EXPECTED_SNAPSHOT_FILES = {
    "r2-r8-r2-evidence/result.json",
    "r2-r8-r2-evidence/evidence-manifest.txt",
    "r2-r8-r2-evidence/packet-snapshot/packet-manifest.json",
    "r2-r8-r2-evidence/packet-snapshot/human-approval-verbatim.txt",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/candidate-manifest.json",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/3e-j-r2-r8-operation-manual.md",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/r2-r8-result-schema.json",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/root-readonly-command-contract.json",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/root-readonly-verification-policy.json",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/root_readonly_sudoers_destination_verifier.sh",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/test_r2_r8_packet_negative.py",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts/validate_r2_r8_packet.py",
    "r2-r8-r2-evidence/validation-logs/negative-tests.log",
    "r2-r8-r2-evidence/validation-logs/python-compile.log",
    "r2-r8-r2-evidence/validation-logs/validator.log",
    "r2-r8-r2-evidence/validation-logs/verifier-bash-n.log",
    "root-verification/root-readonly-verification-output.txt",
    "one-shot-guard/execution-attempt.txt",
    "executed-wrapper/tst_5d_w2b_i2f3e_j_r2_r8_r1_nonexecutable_verifier_bash_invocation_correction_execution_once.sh",
}

EXPECTED_SNAPSHOT_DIRECTORIES = {
    "r2-r8-r2-evidence",
    "r2-r8-r2-evidence/packet-snapshot",
    "r2-r8-r2-evidence/packet-snapshot/candidate-artifacts",
    "r2-r8-r2-evidence/validation-logs",
    "root-verification",
    "one-shot-guard",
    "executed-wrapper",
}

EXPECTED_LOG_FILES = {
    "python-compile.log",
    "validator.log",
    "negative-tests.log",
}

EXPECTED_PACKET_FILE_SET = {
    "human-approval-verbatim.txt",
    "packet-manifest.json",
    *(f"candidate-artifacts/{name}" for name in EXPECTED_CANDIDATE_FILES),
    *(f"registration-input-snapshot/{name}" for name in EXPECTED_SNAPSHOT_FILES),
    *(f"validation-logs/{name}" for name in EXPECTED_LOG_FILES),
}

EXPECTED_PACKET_DIRECTORY_SET = {
    "candidate-artifacts",
    "registration-input-snapshot",
    *(f"registration-input-snapshot/{name}" for name in EXPECTED_SNAPSHOT_DIRECTORIES),
    "validation-logs",
}

EXPECTED_EVIDENCE_FILE_SET = {
    "result.json",
    "evidence-manifest.txt",
    *(f"packet-snapshot/{name}" for name in EXPECTED_PACKET_FILE_SET),
}

EXPECTED_EVIDENCE_DIRECTORY_SET = {
    "packet-snapshot",
    *(f"packet-snapshot/{name}" for name in EXPECTED_PACKET_DIRECTORY_SET),
}

EXPECTED_OUTPUT_LINES = [
    "ROOT_CONTEXT_VERIFICATION=PASS",
    f"TARGET_PATH={TARGET}",
    "TEST_EXISTS_EXIT_CODE=1",
    "TEST_SYMLINK_EXIT_CODE=1",
    "SUDOERS_DESTINATION_EXISTENCE_STATE=ABSENT_CONFIRMED",
    "SUDOERS_DESTINATION_SYMLINK_STATE=false",
    "ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED",
    "ROOT_READONLY_VERIFICATION_EXECUTED=true",
    "SUDOERS_CHANGED=false",
    "NEXT_GATE=HUMAN_REVIEW_3E_J_R2_R8_ROOT_READONLY_VERIFICATION_RESULT",
]

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
    require(isinstance(value, dict), f"JSON_ROOT_NOT_OBJECT:{path}")
    return value

def scan_tree(root: Path) -> tuple[set[str], set[str], int, int]:
    root_state = root.lstat()
    require(stat.S_ISDIR(root_state.st_mode), f"ROOT_NOT_DIRECTORY:{root}")
    require(not stat.S_ISLNK(root_state.st_mode), f"ROOT_SYMLINK:{root}")

    files: set[str] = set()
    directories: set[str] = set()
    symlinks = 0
    nonregular = 0

    def walk(directory: Path) -> None:
        nonlocal symlinks, nonregular
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            item = entry.stat(follow_symlinks=False)
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(item.st_mode):
                symlinks += 1
            elif stat.S_ISDIR(item.st_mode):
                directories.add(relative)
                walk(path)
            elif stat.S_ISREG(item.st_mode):
                files.add(relative)
            else:
                nonregular += 1

    walk(root)
    return files, directories, symlinks, nonregular

def require_regular_nonsymlink(path: Path, label: str) -> os.stat_result:
    item = path.lstat()
    require(stat.S_ISREG(item.st_mode), f"{label}_NOT_REGULAR")
    require(not stat.S_ISLNK(item.st_mode), f"{label}_SYMLINK")
    return item

def resolve_source(source_path: str) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve(strict=True)

# Root bindings.
require(
    r3_root.relative_to(repo_root).as_posix() == expected_r3_relative,
    "R3_ROOT_BINDING",
)
require(packet_root == r3_root / "packet-snapshot", "PACKET_ROOT_BINDING")
require(
    candidate_root == packet_root / "candidate-artifacts",
    "CANDIDATE_ROOT_BINDING",
)
require(
    snapshot_root == packet_root / "registration-input-snapshot",
    "SNAPSHOT_ROOT_BINDING",
)
require(log_root == packet_root / "validation-logs", "LOG_ROOT_BINDING")

# Fixed SHA review.
for relative, expected in EXPECTED_FIXED_SHA.items():
    path = r3_root / relative
    require_regular_nonsymlink(path, f"FIXED:{relative}")
    require(sha256(path) == expected, f"FIXED_SHA:{relative}")

# Exact Evidence and Packet trees.
evidence_files, evidence_dirs, evidence_links, evidence_other = scan_tree(r3_root)
require(
    evidence_files == EXPECTED_EVIDENCE_FILE_SET,
    "EVIDENCE_EXACT_FILE_SET",
)
require(
    evidence_dirs == EXPECTED_EVIDENCE_DIRECTORY_SET,
    "EVIDENCE_EXACT_DIRECTORY_SET",
)
require(len(evidence_files) == 36, "EVIDENCE_FILE_COUNT_NOT_36")
require(len(evidence_dirs) == 11, "EVIDENCE_DIRECTORY_COUNT_NOT_11")
require(evidence_links == 0, "EVIDENCE_SYMLINK_COUNT")
require(evidence_other == 0, "EVIDENCE_NONREGULAR_COUNT")

packet_files, packet_dirs, packet_links, packet_other = scan_tree(packet_root)
require(packet_files == EXPECTED_PACKET_FILE_SET, "PACKET_EXACT_FILE_SET")
require(
    packet_dirs == EXPECTED_PACKET_DIRECTORY_SET,
    "PACKET_EXACT_DIRECTORY_SET",
)
require(len(packet_files) == 34, "PACKET_FILE_COUNT_NOT_34")
require(len(packet_dirs) == 10, "PACKET_DIRECTORY_COUNT_NOT_10")
require(packet_links == 0, "PACKET_SYMLINK_COUNT")
require(packet_other == 0, "PACKET_NONREGULAR_COUNT")

candidate_files, candidate_dirs, candidate_links, candidate_other = scan_tree(
    candidate_root
)
require(
    candidate_files == EXPECTED_CANDIDATE_FILES,
    "CANDIDATE_EXACT_FILE_SET",
)
require(len(candidate_files) == 10, "CANDIDATE_FILE_COUNT_NOT_10")
require(not candidate_dirs, "CANDIDATE_DIRECTORY_COUNT_NOT_0")
require(candidate_links == 0, "CANDIDATE_SYMLINK_COUNT")
require(candidate_other == 0, "CANDIDATE_NONREGULAR_COUNT")
require(
    not any(name.endswith(".pyc") for name in candidate_files),
    "CANDIDATE_PYC_PRESENT",
)

snapshot_files, snapshot_dirs, snapshot_links, snapshot_other = scan_tree(
    snapshot_root
)
require(
    snapshot_files == EXPECTED_SNAPSHOT_FILES,
    "SNAPSHOT_EXACT_FILE_SET",
)
require(
    snapshot_dirs == EXPECTED_SNAPSHOT_DIRECTORIES,
    "SNAPSHOT_EXACT_DIRECTORY_SET",
)
require(len(snapshot_files) == 19, "SNAPSHOT_FILE_COUNT_NOT_19")
require(len(snapshot_dirs) == 7, "SNAPSHOT_DIRECTORY_COUNT_NOT_7")
require(snapshot_links == 0, "SNAPSHOT_SYMLINK_COUNT")
require(snapshot_other == 0, "SNAPSHOT_NONREGULAR_COUNT")

log_files, log_dirs, log_links, log_other = scan_tree(log_root)
require(log_files == EXPECTED_LOG_FILES, "LOG_EXACT_FILE_SET")
require(not log_dirs, "LOG_DIRECTORY_COUNT_NOT_0")
require(log_links == 0, "LOG_SYMLINK_COUNT")
require(log_other == 0, "LOG_NONREGULAR_COUNT")

# Owner/group/modes for unsealed R3 Packet Evidence.
repo_state = repo_root.stat()
expected_uid = repo_state.st_uid
expected_gid = repo_state.st_gid
all_evidence_paths = [
    r3_root,
    *(r3_root / relative for relative in sorted(evidence_files)),
    *(r3_root / relative for relative in sorted(evidence_dirs)),
]
require(
    all(path.lstat().st_uid == expected_uid for path in all_evidence_paths),
    "EVIDENCE_OWNER",
)
require(
    all(path.lstat().st_gid == expected_gid for path in all_evidence_paths),
    "EVIDENCE_GROUP",
)
file_modes = Counter(
    f"{stat.S_IMODE((r3_root / relative).lstat().st_mode):04o}"
    for relative in evidence_files
)
directory_modes = Counter(
    f"{stat.S_IMODE(path.lstat().st_mode):04o}"
    for path in [
        r3_root,
        *(r3_root / relative for relative in sorted(evidence_dirs)),
    ]
)
require(file_modes == Counter({"0640": 36}), "EVIDENCE_FILE_MODE")
require(directory_modes == Counter({"0750": 12}), "EVIDENCE_DIRECTORY_MODE")

# Candidate manifest exact set, SHA, and size.
candidate_manifest = load_json(candidate_root / "candidate-manifest.json")
require(candidate_manifest["phase"] == PHASE, "CANDIDATE_MANIFEST_PHASE")
require(
    candidate_manifest["status"] == "CANDIDATE_PACKET_PREPARED_NO_EXECUTION",
    "CANDIDATE_MANIFEST_STATUS",
)
require(candidate_manifest["total_file_count"] == 10, "CANDIDATE_TOTAL_COUNT")
require(
    candidate_manifest["file_count_excluding_manifest"] == 9,
    "CANDIDATE_EXCLUDING_COUNT",
)
require(
    candidate_manifest["evidence_registration_executed"] is False,
    "CANDIDATE_REGISTRATION_STATE",
)
require(
    candidate_manifest["evidence_seal_executed"] is False,
    "CANDIDATE_SEAL_STATE",
)
require(
    candidate_manifest["root_readonly_verification_reexecution_allowed"]
    is False,
    "CANDIDATE_REEXECUTION",
)
require(
    candidate_manifest["one_shot_guard_change_allowed"] is False,
    "CANDIDATE_GUARD_CHANGE",
)
require(
    candidate_manifest["production_release_decision"] == "HOLD",
    "CANDIDATE_RELEASE_HOLD",
)
candidate_declared = {
    "candidate-manifest.json",
    *(item["name"] for item in candidate_manifest["files"]),
}
require(
    candidate_declared == EXPECTED_CANDIDATE_FILES,
    "CANDIDATE_MANIFEST_EXACT_SET",
)
require(len(candidate_manifest["files"]) == 9, "CANDIDATE_MANIFEST_ENTRY_COUNT")
for item in candidate_manifest["files"]:
    path = candidate_root / item["name"]
    require(sha256(path) == item["sha256"], f"CANDIDATE_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"CANDIDATE_SIZE:{item['name']}",
    )

# Snapshot manifest, source metadata, and byte-for-byte equivalence.
snapshot_manifest = load_json(
    candidate_root / "r2-r8-r3-snapshot-manifest.json"
)
require(snapshot_manifest["phase"] == PHASE, "SNAPSHOT_MANIFEST_PHASE")
require(
    snapshot_manifest["status"] == "SNAPSHOT_CANDIDATE_PREPARED_UNSEALED",
    "SNAPSHOT_MANIFEST_STATUS",
)
require(
    snapshot_manifest["snapshot_file_count"] == 19,
    "SNAPSHOT_MANIFEST_FILE_COUNT",
)
require(
    snapshot_manifest["snapshot_directory_count_excluding_root"] == 7,
    "SNAPSHOT_MANIFEST_DIRECTORY_COUNT",
)
require(
    snapshot_manifest["snapshot_byte_equivalence"] == "PASS",
    "SNAPSHOT_MANIFEST_BYTE",
)
require(
    snapshot_manifest["snapshot_size_equivalence"] == "PASS",
    "SNAPSHOT_MANIFEST_SIZE",
)
require(
    snapshot_manifest["snapshot_sha256_equivalence"] == "PASS",
    "SNAPSHOT_MANIFEST_SHA",
)
require(
    snapshot_manifest["source_mutation_performed"] is False,
    "SNAPSHOT_SOURCE_MUTATION",
)
snapshot_declared = {
    item["snapshot_relative_path"] for item in snapshot_manifest["files"]
}
require(
    snapshot_declared == EXPECTED_SNAPSHOT_FILES,
    "SNAPSHOT_MANIFEST_EXACT_SET",
)
require(len(snapshot_manifest["files"]) == 19, "SNAPSHOT_MANIFEST_ENTRY_COUNT")

source_paths_seen: set[str] = set()
for item in snapshot_manifest["files"]:
    source_display = item["source_path"]
    snapshot_relative = item["snapshot_relative_path"]
    require(source_display not in source_paths_seen, "SNAPSHOT_DUPLICATE_SOURCE")
    source_paths_seen.add(source_display)

    source = resolve_source(source_display)
    copy = snapshot_root / snapshot_relative
    source_state = require_regular_nonsymlink(source, f"SOURCE:{source_display}")
    copy_state = require_regular_nonsymlink(copy, f"SNAPSHOT:{snapshot_relative}")

    source_sha = sha256(source)
    copy_sha = sha256(copy)
    require(source_sha == item["sha256"], f"SOURCE_SHA:{source_display}")
    require(copy_sha == item["sha256"], f"SNAPSHOT_SHA:{snapshot_relative}")
    require(source_sha == copy_sha, f"BYTE_EQUIVALENCE:{snapshot_relative}")
    require(
        source_state.st_size == item["size_bytes"],
        f"SOURCE_SIZE:{source_display}",
    )
    require(
        copy_state.st_size == item["size_bytes"],
        f"SNAPSHOT_SIZE:{snapshot_relative}",
    )
    require(
        source.read_bytes() == copy.read_bytes(),
        f"BYTE_CONTENT:{snapshot_relative}",
    )
    require(
        item["source_mode"] == f"{stat.S_IMODE(source_state.st_mode):04o}",
        f"SOURCE_MODE:{source_display}",
    )
    require(item["source_uid"] == source_state.st_uid, f"SOURCE_UID:{source_display}")
    require(item["source_gid"] == source_state.st_gid, f"SOURCE_GID:{source_display}")
    require(
        item["source_owner"] == pwd.getpwuid(source_state.st_uid).pw_name,
        f"SOURCE_OWNER:{source_display}",
    )
    require(
        item["source_group"] == grp.getgrgid(source_state.st_gid).gr_name,
        f"SOURCE_GROUP:{source_display}",
    )

# Specific source bindings and content.
r2_source_prefix = (
    "exchange/review_evidence/slack_worker_release_rebinding/"
    "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/"
    "tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/"
    "i2f3e-j-r2-r8-r2-candidate-exact-file-set-correction-"
    "20260726T021229Z-524713/"
)
r2_items = [
    item for item in snapshot_manifest["files"]
    if item["source_path"].startswith(r2_source_prefix)
]
require(len(r2_items) == 16, "R2_SOURCE_SNAPSHOT_COUNT_NOT_16")

output_item = next(
    item for item in snapshot_manifest["files"]
    if item["snapshot_relative_path"]
    == "root-verification/root-readonly-verification-output.txt"
)
require(
    output_item["source_path"]
    == "/tmp/tst_5d_w2b_i2f3e_j_r2_r8_root_readonly_verification_execution.txt",
    "OUTPUT_SOURCE_PATH",
)
require(
    output_item["sha256"]
    == "582ce48b8847b578035e82131ca374101a7ad189ad9e988ee73b775e687ed88a",
    "OUTPUT_SOURCE_SHA",
)
output_lines = (
    snapshot_root / output_item["snapshot_relative_path"]
).read_text(encoding="utf-8").splitlines()
require(output_lines == EXPECTED_OUTPUT_LINES, "OUTPUT_EXACT_CONTENT")

guard_item = next(
    item for item in snapshot_manifest["files"]
    if item["snapshot_relative_path"] == "one-shot-guard/execution-attempt.txt"
)
require(
    guard_item["source_path"]
    == (
        "/tmp/ai-media-os-3e-j-r2-r8-root-readonly-"
        "verification-once-c1d53b3a.guard/execution-attempt.txt"
    ),
    "GUARD_SOURCE_PATH",
)
guard_values: dict[str, str] = {}
for line in (
    snapshot_root / guard_item["snapshot_relative_path"]
).read_text(encoding="utf-8").splitlines():
    key, value = line.split("=", 1)
    require(key not in guard_values, f"GUARD_DUPLICATE_KEY:{key}")
    guard_values[key] = value
require(
    set(guard_values)
    == {
        "approval_token_sha256",
        "verifier_sha256",
        "target_path",
        "started_at_utc",
        "verifier_exit_code",
        "completed_at_utc",
        "output_log_sha256",
    },
    "GUARD_EXACT_KEY_SET",
)
require(guard_values["target_path"] == TARGET, "GUARD_TARGET")
require(guard_values["verifier_exit_code"] == "0", "GUARD_EXIT_CODE")
require(
    guard_values["verifier_sha256"]
    == "bd555f07ba09c72e211ab1ae5d1af3b8c544a87ff5204ab8d476cb8923fddd93",
    "GUARD_VERIFIER_SHA",
)
require(
    guard_values["output_log_sha256"] == output_item["sha256"],
    "GUARD_OUTPUT_SHA",
)

wrapper_item = next(
    item for item in snapshot_manifest["files"]
    if item["snapshot_relative_path"].startswith("executed-wrapper/")
)
require(
    wrapper_item["source_path"]
    == (
        "scripts/manual/"
        "tst_5d_w2b_i2f3e_j_r2_r8_r1_nonexecutable_verifier_"
        "bash_invocation_correction_execution_once.sh"
    ),
    "WRAPPER_SOURCE_PATH",
)
require(
    wrapper_item["sha256"]
    == "714e98a5ed0cf2e3e8db320b7d4fdda234e015cb898e7f2d1d2a16dabc255b04",
    "WRAPPER_SOURCE_SHA",
)

# Registration result record.
record = load_json(candidate_root / "r2-r8-r3-result-record.json")
require(record["phase"] == PHASE, "RESULT_RECORD_PHASE")
require(record["target_path"] == TARGET, "RESULT_RECORD_TARGET")
require(record["root_context_verification"] == "PASS", "RESULT_ROOT_CONTEXT")
require(record["test_exists_exit_code"] == 1, "RESULT_EXISTS_RC")
require(record["test_symlink_exit_code"] == 1, "RESULT_SYMLINK_RC")
require(
    record["sudoers_destination_existence_state"] == "ABSENT_CONFIRMED",
    "RESULT_EXISTENCE_STATE",
)
require(
    record["sudoers_destination_symlink_state"] is False,
    "RESULT_SYMLINK_STATE",
)
require(
    record["root_readonly_verification_result"] == "ABSENT_CONFIRMED",
    "RESULT_ROOT_VALUE",
)
require(record["root_readonly_verification_executed"] is True, "RESULT_EXECUTED")
require(
    record["root_readonly_verification_execution_attempt_count"] == 1,
    "RESULT_ATTEMPT_COUNT",
)
require(
    record["root_readonly_verification_max_executions"] == 1,
    "RESULT_MAX_EXECUTIONS",
)
require(
    record["root_readonly_verification_reexecution_allowed"] is False,
    "RESULT_REEXECUTION",
)
require(record["verifier_exit_code"] == 0, "RESULT_VERIFIER_EXIT")
require(
    record["wrapper_exit_code_persisted_evidence_available"] is False,
    "RESULT_WRAPPER_PERSISTED",
)
require(
    record["wrapper_exit_code_user_provided_console_transcript"] == 0,
    "RESULT_WRAPPER_TRANSCRIPT",
)
require(
    record["wrapper_exit_code_qualifier"]
    == "USER_PROVIDED_CONSOLE_TRANSCRIPT_ONLY_NOT_LOCALLY_PERSISTED",
    "RESULT_WRAPPER_QUALIFIER",
)
require(
    record["result_human_review"]
    == "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER",
    "RESULT_HUMAN_REVIEW",
)
require(
    record["result_human_review_decision"]
    == "APPROVE_ABSENT_CONFIRMED_WITH_DEPLOYMENT_HOLD",
    "RESULT_HUMAN_DECISION",
)
for key in (
    "sudoers_content_read_allowed",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_approval_token_created",
    "approval_binding_created",
):
    require(record[key] is False, f"RESULT_RECORD_FALSE:{key}")
require(
    record["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "RESULT_RUNNER_HOLD",
)
require(record["writer_freeze_execution"] == "HOLD", "RESULT_WRITER_HOLD")
require(
    record["production_release_decision"] == "HOLD",
    "RESULT_RELEASE_HOLD",
)
require(
    record["release_status"] == "CANDIDATE_NOT_APPROVED",
    "RESULT_RELEASE_STATUS",
)

# Registration policy.
policy = load_json(candidate_root / "r2-r8-r3-registration-policy.json")
require(policy["phase"] == PHASE, "POLICY_PHASE")
require(policy["packet_preparation_only"] is True, "POLICY_PACKET_ONLY")
require(
    policy["evidence_registration_executed"] is False,
    "POLICY_REGISTRATION_STATE",
)
require(policy["evidence_seal_executed"] is False, "POLICY_SEAL_STATE")
require(
    policy["root_readonly_verification_reexecution_allowed"] is False,
    "POLICY_REEXECUTION",
)
require(
    policy["one_shot_guard_change_allowed"] is False,
    "POLICY_GUARD_CHANGE",
)
require(policy["source_mutation_allowed"] is False, "POLICY_SOURCE_MUTATION")
require(
    policy["snapshot_candidate_preparation_allowed"] is True,
    "POLICY_SNAPSHOT_ALLOWED",
)
require(
    policy["snapshot_candidate_file_content_copy"] == "BYTE_FOR_BYTE",
    "POLICY_COPY_METHOD",
)
require(
    policy["root_readonly_verification_result"] == "ABSENT_CONFIRMED",
    "POLICY_RESULT",
)
require(policy["verifier_exit_code"] == 0, "POLICY_VERIFIER_EXIT")
require(
    policy["wrapper_exit_code_persisted_evidence_available"] is False,
    "POLICY_WRAPPER_PERSISTED",
)
require(
    policy["human_review_qualifier"]
    == "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER",
    "POLICY_QUALIFIER",
)
require(policy["sudoers_changed"] is False, "POLICY_SUDOERS_CHANGED")
require(
    policy["automatic_deployment_performed"] is False,
    "POLICY_AUTO_DEPLOY",
)
require(
    policy["candidate_deployed_to_production"] is False,
    "POLICY_DEPLOYMENT",
)
require(
    policy["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "POLICY_RUNNER_HOLD",
)
require(policy["writer_freeze_execution"] == "HOLD", "POLICY_WRITER_HOLD")
require(
    policy["production_release_decision"] == "HOLD",
    "POLICY_RELEASE_HOLD",
)
require(
    policy["release_status"] == "CANDIDATE_NOT_APPROVED",
    "POLICY_RELEASE_STATUS",
)

# Source contract.
source_contract = load_json(candidate_root / "r2-r8-r3-source-contract.json")
require(source_contract["phase"] == PHASE, "SOURCE_CONTRACT_PHASE")
require(source_contract["source_count"] == 3, "SOURCE_CONTRACT_COUNT")
require(
    all(item["read_only"] is True for item in source_contract["sources"]),
    "SOURCE_CONTRACT_READ_ONLY",
)
require(
    source_contract["guard"]["expected_entry_count"] == 1,
    "SOURCE_CONTRACT_GUARD_ENTRY_COUNT",
)
require(
    source_contract["guard"]["expected_attempt_count"] == 1,
    "SOURCE_CONTRACT_ATTEMPT_COUNT",
)
require(
    source_contract["guard"]["change_allowed"] is False,
    "SOURCE_CONTRACT_GUARD_CHANGE",
)
require(
    source_contract["sudoers_content_read_allowed"] is False,
    "SOURCE_CONTRACT_CONTENT_READ",
)
require(
    source_contract["sudoers_change_allowed"] is False,
    "SOURCE_CONTRACT_SUDOERS_CHANGE",
)
require(
    source_contract["root_verification_reexecution_allowed"] is False,
    "SOURCE_CONTRACT_REEXECUTION",
)
require(
    source_contract["one_shot_guard_change_allowed"] is False,
    "SOURCE_CONTRACT_TOP_GUARD_CHANGE",
)

# Seal contract: preparation only, no seal executed.
seal = load_json(candidate_root / "r2-r8-r3-seal-contract.json")
require(seal["phase"] == PHASE, "SEAL_PHASE")
require(seal["seal_execution_status"] == "NOT_EXECUTED", "SEAL_STATUS")
require(
    seal["seal_execution_allowed_in_current_phase"] is False,
    "SEAL_CURRENT_PHASE",
)
require(
    seal["future_execution_requires_new_explicit_human_approval"] is True,
    "SEAL_APPROVAL_GATE",
)
require(
    seal["future_seal_scope"]
    == "NEW_FINAL_REGISTRATION_EVIDENCE_ROOT_ONLY",
    "SEAL_SCOPE",
)
require(
    seal["source_evidence_mutation_allowed"] is False,
    "SEAL_SOURCE_MUTATION",
)
require(
    seal["packet_preparation_evidence_mutation_allowed"] is False,
    "SEAL_PACKET_MUTATION",
)
require(seal["future_file_mode_after_seal"] == "0444", "SEAL_FILE_MODE")
require(
    seal["future_directory_mode_after_seal"] == "0555",
    "SEAL_DIRECTORY_MODE",
)
require(seal["future_symlink_allowed"] is False, "SEAL_SYMLINK")
require(
    seal["future_owner_group_change_allowed"] is False,
    "SEAL_OWNER_GROUP",
)
require(
    seal["future_copy_method"] == "EXCLUSIVE_CREATE_NO_OVERWRITE",
    "SEAL_COPY_METHOD",
)
require(
    seal["automatic_production_deployment_after_seal"] is False,
    "SEAL_AUTO_DEPLOY",
)
require(
    seal["production_release_decision"] == "HOLD",
    "SEAL_RELEASE_HOLD",
)

# Blocked entrypoint static review only.
blocked = (
    candidate_root / "blocked_registration_and_seal_entrypoint.py"
).read_text(encoding="utf-8")
for marker in (
    "R2_R8_R3_PACKET_PREPARATION_ONLY=true",
    "R2_R8_R3_EVIDENCE_REGISTRATION_EXECUTED=false",
    "R2_R8_R3_EVIDENCE_SEAL_EXECUTED=false",
    (
        "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_R2_R8_R3_"
        "REGISTRATION_AND_SEAL_EXECUTION_APPROVAL"
    ),
    "PRODUCTION_RELEASE_DECISION=HOLD",
):
    require(marker in blocked, f"BLOCKED_MARKER:{marker}")
for forbidden in ("subprocess", "shutil", "os.", "socket", "sqlite3"):
    require(forbidden not in blocked, f"BLOCKED_FORBIDDEN:{forbidden}")

# Existing validation logs only.
compile_log = (log_root / "python-compile.log").read_text(encoding="utf-8")
require(
    compile_log.splitlines()
    == [
        "PYTHON_COMPILE_PASS=blocked_registration_and_seal_entrypoint.py",
        "PYTHON_COMPILE_PASS=validate_r2_r8_r3_packet.py",
        "PYTHON_COMPILE_PASS=test_r2_r8_r3_packet_negative.py",
    ],
    "COMPILE_LOG_CONTENT",
)

validator_log = (log_root / "validator.log").read_text(encoding="utf-8")
validator_markers = {
    "VALIDATION=PASS",
    "CANDIDATE_FILE_COUNT=10",
    "CANDIDATE_DIRECTORY_COUNT=0",
    "CANDIDATE_PYC_FILE_COUNT=0",
    "SNAPSHOT_FILE_COUNT=19",
    "SNAPSHOT_DIRECTORY_COUNT_EXCLUDING_ROOT=7",
    "SNAPSHOT_EXACT_FILE_SET_REVIEW=PASS",
    "SNAPSHOT_SHA_SIZE_REVIEW=PASS",
    "SOURCE_METADATA_REVIEW=PASS",
    "ABSENT_CONFIRMED_RESULT_RECORD_REVIEW=PASS",
    "WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER_REVIEW=PASS",
    "EVIDENCE_REGISTRATION_EXECUTED=false",
    "EVIDENCE_SEAL_EXECUTED=false",
    "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false",
    "ONE_SHOT_GUARD_CHANGE_ALLOWED=false",
    "PRODUCTION_RELEASE_DECISION=HOLD",
}
validator_lines = {
    line.strip() for line in validator_log.splitlines() if line.strip()
}
require(validator_markers <= validator_lines, "VALIDATOR_LOG_MARKERS")

negative_log = (log_root / "negative-tests.log").read_text(encoding="utf-8")
negative_lines = [line.strip() for line in negative_log.splitlines()]
require("Ran 14 tests" in negative_log, "NEGATIVE_TEST_COUNT")
require(negative_lines.count("OK") == 1, "NEGATIVE_TEST_OK_COUNT")
require("FAILED" not in negative_lines, "NEGATIVE_TEST_FAILED")
require("ERROR" not in negative_lines, "NEGATIVE_TEST_ERROR")

# Packet manifest exact file set and SHA/size.
packet_manifest = load_json(packet_root / "packet-manifest.json")
require(packet_manifest["phase"] == PHASE, "PACKET_MANIFEST_PHASE")
require(
    packet_manifest["status"]
    == (
        "ROOT_READONLY_RESULT_EVIDENCE_REGISTRATION_AND_SEAL_"
        "PACKET_PREPARED_NO_EXECUTION"
    ),
    "PACKET_MANIFEST_STATUS",
)
require(
    packet_manifest["packet_file_count_excluding_manifest"] == 33,
    "PACKET_MANIFEST_ENTRY_COUNT",
)
require(
    packet_manifest["candidate_artifact_count"] == 10,
    "PACKET_MANIFEST_CANDIDATE_COUNT",
)
require(
    packet_manifest["snapshot_file_count"] == 19,
    "PACKET_MANIFEST_SNAPSHOT_COUNT",
)
require(
    packet_manifest["validation_log_count"] == 3,
    "PACKET_MANIFEST_LOG_COUNT",
)
for key in (
    "evidence_registration_executed",
    "evidence_seal_executed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
):
    require(packet_manifest[key] is False, f"PACKET_MANIFEST_FALSE:{key}")
require(
    packet_manifest["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "PACKET_MANIFEST_RUNNER_HOLD",
)
require(
    packet_manifest["production_release_decision"] == "HOLD",
    "PACKET_MANIFEST_RELEASE_HOLD",
)
packet_declared = {
    item["name"] for item in packet_manifest["packet_files"]
}
packet_actual_excluding_manifest = (
    EXPECTED_PACKET_FILE_SET - {"packet-manifest.json"}
)
require(len(packet_declared) == 33, "PACKET_DECLARED_COUNT_NOT_33")
require(
    packet_declared == packet_actual_excluding_manifest,
    "PACKET_MANIFEST_EXACT_SET",
)
for item in packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(sha256(path) == item["sha256"], f"PACKET_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"PACKET_SIZE:{item['name']}",
    )

# Evidence manifest exact file set and SHA.
evidence_manifest_entries: dict[str, str] = {}
for line in (r3_root / "evidence-manifest.txt").read_text(
    encoding="utf-8"
).splitlines():
    digest, relative = line.split("  ", 1)
    require(
        relative not in evidence_manifest_entries,
        f"EVIDENCE_DUPLICATE:{relative}",
    )
    evidence_manifest_entries[relative] = digest
evidence_actual_excluding_manifest = (
    EXPECTED_EVIDENCE_FILE_SET - {"evidence-manifest.txt"}
)
require(
    len(evidence_manifest_entries) == 35,
    "EVIDENCE_MANIFEST_ENTRY_COUNT_NOT_35",
)
require(
    set(evidence_manifest_entries) == evidence_actual_excluding_manifest,
    "EVIDENCE_MANIFEST_EXACT_SET",
)
for relative, digest in evidence_manifest_entries.items():
    require(
        sha256(r3_root / relative) == digest,
        f"EVIDENCE_MANIFEST_SHA:{relative}",
    )

# Result contract and safety boundary.
result = load_json(r3_root / "result.json")
require(result["phase"] == PHASE, "RESULT_PHASE")
require(
    result["result"]
    == (
        "PASS_W2B_I2F3E_J_R2_R8_R3_ROOT_READONLY_RESULT_"
        "EVIDENCE_REGISTRATION_AND_SEAL_PACKET_PREPARED_NO_EXECUTION"
    ),
    "RESULT_VALUE",
)
require(result["evidence_root"] == expected_r3_relative, "RESULT_EVIDENCE_ROOT")
for key in (
    "source_r2_r8_r2_fixed_sha_review",
    "source_output_log_sha_review",
    "source_guard_record_review",
    "source_wrapper_sha_review",
    "source_protected_sha_review",
):
    require(result[key] == "PASS", f"RESULT_PASS:{key}")
require(
    result["root_readonly_verification_result"] == "ABSENT_CONFIRMED",
    "RESULT_ROOT_VALUE",
)
require(
    result["root_readonly_verification_execution_attempt_count"] == 1,
    "RESULT_ATTEMPT_COUNT",
)
require(
    result["root_readonly_verification_max_executions"] == 1,
    "RESULT_MAX_EXECUTIONS",
)
require(
    result["root_readonly_verification_reexecution_allowed"] is False,
    "RESULT_REEXECUTION",
)
require(result["snapshot_source_file_count"] == 19, "RESULT_SOURCE_COUNT")
require(result["snapshot_copy_file_count"] == 19, "RESULT_COPY_COUNT")
require(result["snapshot_byte_equivalence"] == "PASS", "RESULT_BYTE")
require(result["snapshot_size_equivalence"] == "PASS", "RESULT_SIZE")
require(result["snapshot_sha256_equivalence"] == "PASS", "RESULT_SHA")
require(
    result["source_metadata_registration_candidate"] == "PASS",
    "RESULT_METADATA",
)
require(result["candidate_artifact_count"] == 10, "RESULT_CANDIDATE_COUNT")
require(result["negative_test_count"] == 14, "RESULT_NEGATIVE_COUNT")
require(result["negative_tests"] == "PASS", "RESULT_NEGATIVE")
require(result["validator"] == "PASS", "RESULT_VALIDATOR")
require(
    result["wrapper_exit_code_persisted_evidence_available"] is False,
    "RESULT_WRAPPER_PERSISTED",
)
require(
    result["wrapper_exit_code_user_provided_console_transcript"] == 0,
    "RESULT_WRAPPER_TRANSCRIPT",
)
require(
    result["human_review_qualifier"]
    == "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER",
    "RESULT_QUALIFIER",
)
require(result["packet_preparation_only"] is True, "RESULT_PACKET_ONLY")
for key in (
    "evidence_registration_executed",
    "evidence_seal_executed",
    "one_shot_guard_change_allowed",
    "sudoers_changed",
    "automatic_deployment_performed",
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
    require(result[key] is False, f"RESULT_FALSE:{key}")
require(result["protected_sha_unchanged"] is True, "RESULT_PROTECTED_SHA")
require(
    result["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "RESULT_RUNNER_HOLD",
)
require(result["writer_freeze_execution"] == "HOLD", "RESULT_WRITER_HOLD")
require(
    result["production_release_decision"] == "HOLD",
    "RESULT_RELEASE_HOLD",
)
require(
    result["release_status"] == "CANDIDATE_NOT_APPROVED",
    "RESULT_RELEASE_STATUS",
)
require(
    result["packet_evidence_seal_performed"] is False,
    "RESULT_PACKET_SEAL",
)
require(
    result["packet_evidence_seal_status"]
    == "NOT_PERFORMED_CHMOD_NOT_AUTHORIZED",
    "RESULT_PACKET_SEAL_STATUS",
)
require(
    result["next_gate"]
    == "HUMAN_REVIEW_3E_J_R2_R8_R3_EVIDENCE_REGISTRATION_AND_SEAL_PACKET",
    "RESULT_NEXT_GATE",
)

# Approval text binding.
approval_text = (
    packet_root / "human-approval-verbatim.txt"
).read_text(encoding="utf-8")
approval_markers = (
    "APPROVE_3E_J_R2_R8_R3_ROOT_READONLY_RESULT_EVIDENCE_REGISTRATION_AND_SEAL_PACKET_PREPARATION_NO_EXECUTION",
    (
        "R2_R8_ROOT_READONLY_VERIFICATION_RESULT_HUMAN_REVIEW="
        "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER"
    ),
    (
        "R2_R8_RESULT_HUMAN_REVIEW_DECISION="
        "APPROVE_ABSENT_CONFIRMED_WITH_DEPLOYMENT_HOLD"
    ),
    "ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED",
    "ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1",
    "ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1",
    "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false",
    "R2_R8_R3_PACKET_PREPARATION_ONLY=true",
    "R2_R8_R3_EVIDENCE_REGISTRATION_EXECUTED=false",
    "R2_R8_R3_EVIDENCE_SEAL_EXECUTED=false",
    "ONE_SHOT_GUARD_CHANGE_ALLOWED=false",
    "SUDOERS_CHANGED=false",
    "AUTOMATIC_DEPLOYMENT_PERFORMED=false",
    "CANDIDATE_DEPLOYED_TO_PRODUCTION=false",
    "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "WRITER_FREEZE_EXECUTION=HOLD",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "RELEASE_STATUS=CANDIDATE_NOT_APPROVED",
)
for marker in approval_markers:
    require(marker in approval_text, f"APPROVAL_MARKER:{marker}")

# Production protected SHA.
for relative, expected in PROTECTED_SHA.items():
    path = repo_root / relative
    require_regular_nonsymlink(path, f"PROTECTED:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

print("R2_R8_R3_RESULT_SHA_REVIEW=PASS")
print("R2_R8_R3_PACKET_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_CANDIDATE_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_SNAPSHOT_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_EVIDENCE_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_EVIDENCE_FILE_COUNT=36")
print("R2_R8_R3_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=11")
print(f"R2_R8_R3_EVIDENCE_FILE_MODE_DISTRIBUTION={dict(sorted(file_modes.items()))}")
print(
    "R2_R8_R3_EVIDENCE_DIRECTORY_MODE_DISTRIBUTION="
    f"{dict(sorted(directory_modes.items()))}"
)
print("R2_R8_R3_EVIDENCE_SYMLINK_COUNT=0")
print("R2_R8_R3_EVIDENCE_NONREGULAR_COUNT=0")
print("R2_R8_R3_EVIDENCE_OWNER_GROUP_REVIEW=PASS")
print("R2_R8_R3_EVIDENCE_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_PACKET_FILE_COUNT=34")
print("R2_R8_R3_PACKET_DIRECTORY_COUNT=10")
print("R2_R8_R3_PACKET_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_PACKET_MANIFEST_ENTRY_COUNT=33")
print("R2_R8_R3_PACKET_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R8_R3_EVIDENCE_MANIFEST_ENTRY_COUNT=35")
print("R2_R8_R3_EVIDENCE_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R8_R3_CANDIDATE_ARTIFACT_COUNT=10")
print("R2_R8_R3_CANDIDATE_DIRECTORY_COUNT=0")
print("R2_R8_R3_CANDIDATE_PYC_FILE_COUNT=0")
print("R2_R8_R3_CANDIDATE_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_CANDIDATE_ARTIFACT_SHA_SIZE_REVIEW=PASS")
print("R2_R8_R3_SNAPSHOT_FILE_COUNT=19")
print("R2_R8_R3_SNAPSHOT_DIRECTORY_COUNT=7")
print("R2_R8_R3_SNAPSHOT_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_SNAPSHOT_SOURCE_PATH_REVIEW=PASS")
print("R2_R8_R3_SNAPSHOT_SOURCE_METADATA_REVIEW=PASS")
print("R2_R8_R3_SNAPSHOT_BYTE_EQUIVALENCE=PASS")
print("R2_R8_R3_SNAPSHOT_SIZE_EQUIVALENCE=PASS")
print("R2_R8_R3_SNAPSHOT_SHA256_EQUIVALENCE=PASS")
print("R2_R8_R3_R2_FIXED_EVIDENCE_SNAPSHOT_COUNT=16")
print("R2_R8_R3_ROOT_OUTPUT_LOG_SNAPSHOT_REVIEW=PASS")
print("R2_R8_R3_ONE_SHOT_EXECUTION_RECORD_SNAPSHOT_REVIEW=PASS")
print("R2_R8_R3_EXECUTED_WRAPPER_SNAPSHOT_REVIEW=PASS")
print("ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED")
print("ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1")
print("ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("R2_R8_R3_VERIFIER_EXIT_CODE=0")
print(
    "R2_R8_R3_WRAPPER_EXIT_CODE_QUALIFIER="
    "USER_PROVIDED_CONSOLE_TRANSCRIPT_ONLY_NOT_LOCALLY_PERSISTED"
)
print("R2_R8_R3_REGISTRATION_POLICY_REVIEW=PASS")
print("R2_R8_R3_SOURCE_CONTRACT_REVIEW=PASS")
print("R2_R8_R3_SEAL_CONTRACT_REVIEW=PASS")
print("R2_R8_R3_RESULT_RECORD_REVIEW=PASS")
print("R2_R8_R3_BLOCKED_ENTRYPOINT_STATIC_REVIEW=PASS")
print("R2_R8_R3_VALIDATOR_LOG_REVIEW=PASS")
print("R2_R8_R3_NEGATIVE_TEST_COUNT=14")
print("R2_R8_R3_NEGATIVE_TEST_LOG_REVIEW=PASS")
print("PROTECTED_SHA_REVIEW=PASS")
print("R2_R8_R3_PACKET_PREPARATION_ONLY=true")
print("R2_R8_R3_EVIDENCE_REGISTRATION_EXECUTED=false")
print("R2_R8_R3_EVIDENCE_SEAL_EXECUTED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
print("SUDOERS_CHANGED=false")
print("AUTOMATIC_DEPLOYMENT_PERFORMED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "R2_R8_R3_PACKET_HUMAN_REVIEW_DECISION="
    "APPROVE_REGISTRATION_AND_SEAL_PACKET_WITH_EXECUTION_HOLD"
)
print(
    "NEXT_GATE="
    "HUMAN_APPROVAL_FOR_3E_J_R2_R8_R3_FINAL_EVIDENCE_"
    "REGISTRATION_AND_SEAL_EXECUTION"
)
PY

printf '\n===== FINAL R2-R8-R3 HUMAN REVIEW MARKERS =====\n'

echo "R2_R8_R3_PACKET_HUMAN_REVIEW=PASS"
echo "R2_R8_R3_PACKET_HUMAN_REVIEW_DECISION=APPROVE_REGISTRATION_AND_SEAL_PACKET_WITH_EXECUTION_HOLD"
echo "ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED"
echo "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false"
echo "R2_R8_R3_EVIDENCE_REGISTRATION_EXECUTED=false"
echo "R2_R8_R3_EVIDENCE_SEAL_EXECUTED=false"
echo "ONE_SHOT_GUARD_CHANGE_ALLOWED=false"
echo "SUDOERS_CHANGED=false"
echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
echo "WRITER_FREEZE_EXECUTION=HOLD"
echo "PRODUCTION_RELEASE_DECISION=HOLD"
echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
echo "NEXT_GATE=HUMAN_APPROVAL_FOR_3E_J_R2_R8_R3_FINAL_EVIDENCE_REGISTRATION_AND_SEAL_EXECUTION"
echo "REVIEW_COMMAND_EXIT_CODE=0"
