#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SOURCE_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-r1-nested-manifest-basename-exclusion-correction-packet-preparation-20260726T032952Z-526992"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"

FINAL_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-r1-final-evidence-registration-and-seal-20260726T035208Z-527505"
FINAL_ROOT="${REPO_ROOT}/${FINAL_REL}"
PACKET_ROOT="${FINAL_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
SNAPSHOT_ROOT="${PACKET_ROOT}/registration-input-snapshot"
LOG_ROOT="${PACKET_ROOT}/validation-logs"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_REVIEW_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$SOURCE_ROOT"
test -d "$FINAL_ROOT"
test -d "$PACKET_ROOT"
test -d "$CANDIDATE_ROOT"
test -d "$SNAPSHOT_ROOT"
test -d "$LOG_ROOT"

cd "$REPO_ROOT"

printf '\n===== FINAL SEALED EVIDENCE FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
c9d71a2969a2ddf2a710f9e45c60327e42b5257994d613477c0ee724694d3bba  ${FINAL_ROOT}/result.json
700a572496fb3d3c61235da276fbe668afb1a8bdf576040885f6fb07eac502c2  ${PACKET_ROOT}/packet-manifest.json
eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f  ${CANDIDATE_ROOT}/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${CANDIDATE_ROOT}/r2-r8-r3-snapshot-manifest.json
0c674bd9a7ea654bec9acea38a41b03a990d8dbf52b63dea23bb2562662f6d20  ${FINAL_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== APPROVED SOURCE R3-R1 FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
8129fdce8ce1c1767a261523f16a63ca56c867ef635829c8c1e6ef5bd8953d56  ${SOURCE_ROOT}/result.json
0220b3bea10a53cff6a1c7a1cc19527bf7a827921ba856662aff80336c8b47b6  ${SOURCE_ROOT}/packet-snapshot/packet-manifest.json
eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json
2c572560f375b369eae22f71460c531cc298190a69309e93cb7b86ab7e7eab89  ${SOURCE_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== FINAL REGISTRATION AND SEAL RESULT HUMAN REVIEW =====\n'

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$SOURCE_ROOT" \
  "$FINAL_ROOT" \
  "$PACKET_ROOT" \
  "$CANDIDATE_ROOT" \
  "$SNAPSHOT_ROOT" \
  "$LOG_ROOT" \
  "$SOURCE_REL" \
  "$FINAL_REL" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import pwd
import grp
import re
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
source_root = Path(sys.argv[2]).resolve(strict=True)
final_root = Path(sys.argv[3]).resolve(strict=True)
packet_root = Path(sys.argv[4]).resolve(strict=True)
candidate_root = Path(sys.argv[5]).resolve(strict=True)
snapshot_root = Path(sys.argv[6]).resolve(strict=True)
log_root = Path(sys.argv[7]).resolve(strict=True)
source_relative = sys.argv[8]
final_relative = sys.argv[9]

PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3-R1-FINAL-SEAL"
SOURCE_PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3-R1"
TARGET = "/etc/sudoers.d/ai-media-os-3e-j-root-helper"
SEAL_TIMESTAMP = "2026-07-26T03:52:08Z"

FINAL_FIXED_SHA = {
    "result.json": (
        "c9d71a2969a2ddf2a710f9e45c60327e"
        "42b5257994d613477c0ee724694d3bba"
    ),
    "packet-snapshot/packet-manifest.json": (
        "700a572496fb3d3c61235da276fbe668a"
        "fb1a8bdf576040885f6fb07eac502c2"
    ),
    "packet-snapshot/candidate-artifacts/candidate-manifest.json": (
        "eef41d075309aba52f07f6d8d4d62a2f"
        "12f0d74bda01e353be969af9be5a8e0f"
    ),
    "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json": (
        "afaa189fb6d9565ade2a5826449cc859"
        "f65f0358946deae21aae4703f414631c"
    ),
    "evidence-manifest.txt": (
        "0c674bd9a7ea654bec9acea38a41b03a"
        "990d8dbf52b63dea23bb2562662f6d20"
    ),
}

SOURCE_FIXED_SHA = {
    "result.json": (
        "8129fdce8ce1c1767a261523f16a63ca"
        "56c867ef635829c8c1e6ef5bd8953d56"
    ),
    "packet-snapshot/packet-manifest.json": (
        "0220b3bea10a53cff6a1c7a1cc19527b"
        "f7a827921ba856662aff80336c8b47b6"
    ),
    "packet-snapshot/candidate-artifacts/candidate-manifest.json": (
        "eef41d075309aba52f07f6d8d4d62a2f"
        "12f0d74bda01e353be969af9be5a8e0f"
    ),
    "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json": (
        "afaa189fb6d9565ade2a5826449cc859"
        "f65f0358946deae21aae4703f414631c"
    ),
    "evidence-manifest.txt": (
        "2c572560f375b369eae22f71460c531c"
        "c298190a69309e93cb7b86ab7e7eab89"
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

EXPECTED_PACKET_FILES = {
    "packet-manifest.json",
    "human-approval-verbatim.txt",
    *(f"candidate-artifacts/{name}" for name in EXPECTED_CANDIDATE_FILES),
    *(f"registration-input-snapshot/{name}" for name in EXPECTED_SNAPSHOT_FILES),
    *(f"validation-logs/{name}" for name in EXPECTED_LOG_FILES),
}

EXPECTED_PACKET_DIRECTORIES = {
    "candidate-artifacts",
    "registration-input-snapshot",
    *(f"registration-input-snapshot/{name}" for name in EXPECTED_SNAPSHOT_DIRECTORIES),
    "validation-logs",
}

EXPECTED_EVIDENCE_FILES = {
    "result.json",
    "evidence-manifest.txt",
    *(f"packet-snapshot/{name}" for name in EXPECTED_PACKET_FILES),
}

EXPECTED_EVIDENCE_DIRECTORIES = {
    "packet-snapshot",
    *(f"packet-snapshot/{name}" for name in EXPECTED_PACKET_DIRECTORIES),
}

NESTED_PACKET_MANIFEST = (
    "registration-input-snapshot/r2-r8-r2-evidence/"
    "packet-snapshot/packet-manifest.json"
)
NESTED_EVIDENCE_MANIFEST = (
    "packet-snapshot/registration-input-snapshot/"
    "r2-r8-r2-evidence/evidence-manifest.txt"
)

COPY_FROM_SOURCE = {
    *(f"packet-snapshot/candidate-artifacts/{name}" for name in EXPECTED_CANDIDATE_FILES),
    *(f"packet-snapshot/registration-input-snapshot/{name}" for name in EXPECTED_SNAPSHOT_FILES),
    *(f"packet-snapshot/validation-logs/{name}" for name in EXPECTED_LOG_FILES),
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

def require_regular_nonsymlink(path: Path, label: str) -> os.stat_result:
    item = path.lstat()
    require(stat.S_ISREG(item.st_mode), f"{label}_NOT_REGULAR")
    require(not stat.S_ISLNK(item.st_mode), f"{label}_SYMLINK")
    return item

def scan(root: Path) -> tuple[set[str], set[str], int, int]:
    root_item = root.lstat()
    require(stat.S_ISDIR(root_item.st_mode), f"ROOT_NOT_DIRECTORY:{root}")
    require(not stat.S_ISLNK(root_item.st_mode), f"ROOT_SYMLINK:{root}")

    files: set[str] = set()
    directories: set[str] = set()
    symlinks = 0
    nonregular = 0

    def walk(directory: Path) -> None:
        nonlocal symlinks, nonregular
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: item.name)
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

def tree_identity(root: Path) -> dict[str, tuple[str, int, int, int, int]]:
    files, directories, links, other = scan(root)
    require(links == 0, f"IDENTITY_SYMLINK:{root}")
    require(other == 0, f"IDENTITY_NONREGULAR:{root}")

    identity: dict[str, tuple[str, int, int, int, int]] = {}
    root_item = root.lstat()
    identity["./"] = (
        "DIRECTORY",
        0,
        stat.S_IMODE(root_item.st_mode),
        root_item.st_uid,
        root_item.st_gid,
    )
    for relative in sorted(directories):
        item = (root / relative).lstat()
        identity[relative + "/"] = (
            "DIRECTORY",
            0,
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        identity[relative] = (
            sha256(path),
            item.st_size,
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    return identity

def parse_evidence_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        require("  " in line, "EVIDENCE_MANIFEST_LINE_FORMAT")
        digest, relative = line.split("  ", 1)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "MANIFEST_DIGEST")
        require(relative not in entries, f"MANIFEST_DUPLICATE:{relative}")
        entries[relative] = digest
    return entries

# Path bindings.
require(
    source_root.relative_to(repo_root).as_posix() == source_relative,
    "SOURCE_ROOT_BINDING",
)
require(
    final_root.relative_to(repo_root).as_posix() == final_relative,
    "FINAL_ROOT_BINDING",
)
require(packet_root == final_root / "packet-snapshot", "PACKET_ROOT_BINDING")
require(
    candidate_root == packet_root / "candidate-artifacts",
    "CANDIDATE_ROOT_BINDING",
)
require(
    snapshot_root == packet_root / "registration-input-snapshot",
    "SNAPSHOT_ROOT_BINDING",
)
require(log_root == packet_root / "validation-logs", "LOG_ROOT_BINDING")

# Fixed SHA review and pre-review tree identities.
for relative, expected in FINAL_FIXED_SHA.items():
    path = final_root / relative
    require_regular_nonsymlink(path, f"FINAL_FIXED:{relative}")
    require(sha256(path) == expected, f"FINAL_FIXED_SHA:{relative}")

for relative, expected in SOURCE_FIXED_SHA.items():
    path = source_root / relative
    require_regular_nonsymlink(path, f"SOURCE_FIXED:{relative}")
    require(sha256(path) == expected, f"SOURCE_FIXED_SHA:{relative}")

source_identity_before = tree_identity(source_root)
final_identity_before = tree_identity(final_root)

# Exact file and directory sets.
source_files, source_dirs, source_links, source_other = scan(source_root)
require(source_files == EXPECTED_EVIDENCE_FILES, "SOURCE_EXACT_FILE_SET")
require(source_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "SOURCE_EXACT_DIR_SET")
require(len(source_files) == 36, "SOURCE_FILE_COUNT")
require(len(source_dirs) == 11, "SOURCE_DIR_COUNT")
require(source_links == 0, "SOURCE_SYMLINK_COUNT")
require(source_other == 0, "SOURCE_NONREGULAR_COUNT")

final_files, final_dirs, final_links, final_other = scan(final_root)
require(final_files == EXPECTED_EVIDENCE_FILES, "FINAL_EXACT_FILE_SET")
require(final_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "FINAL_EXACT_DIR_SET")
require(len(final_files) == 36, "FINAL_FILE_COUNT")
require(len(final_dirs) == 11, "FINAL_DIR_COUNT")
require(final_links == 0, "FINAL_SYMLINK_COUNT")
require(final_other == 0, "FINAL_NONREGULAR_COUNT")

packet_files, packet_dirs, packet_links, packet_other = scan(packet_root)
require(packet_files == EXPECTED_PACKET_FILES, "PACKET_EXACT_FILE_SET")
require(packet_dirs == EXPECTED_PACKET_DIRECTORIES, "PACKET_EXACT_DIR_SET")
require(len(packet_files) == 34, "PACKET_FILE_COUNT")
require(len(packet_dirs) == 10, "PACKET_DIR_COUNT")
require(packet_links == 0, "PACKET_SYMLINK_COUNT")
require(packet_other == 0, "PACKET_NONREGULAR_COUNT")

candidate_files, candidate_dirs, candidate_links, candidate_other = scan(
    candidate_root
)
require(
    candidate_files == EXPECTED_CANDIDATE_FILES,
    "CANDIDATE_EXACT_FILE_SET",
)
require(len(candidate_files) == 10, "CANDIDATE_FILE_COUNT")
require(not candidate_dirs, "CANDIDATE_DIR_COUNT")
require(candidate_links == 0, "CANDIDATE_SYMLINK_COUNT")
require(candidate_other == 0, "CANDIDATE_NONREGULAR_COUNT")

snapshot_files, snapshot_dirs, snapshot_links, snapshot_other = scan(
    snapshot_root
)
require(
    snapshot_files == EXPECTED_SNAPSHOT_FILES,
    "SNAPSHOT_EXACT_FILE_SET",
)
require(
    snapshot_dirs == EXPECTED_SNAPSHOT_DIRECTORIES,
    "SNAPSHOT_EXACT_DIR_SET",
)
require(len(snapshot_files) == 19, "SNAPSHOT_FILE_COUNT")
require(len(snapshot_dirs) == 7, "SNAPSHOT_DIR_COUNT")
require(snapshot_links == 0, "SNAPSHOT_SYMLINK_COUNT")
require(snapshot_other == 0, "SNAPSHOT_NONREGULAR_COUNT")

log_files, log_dirs, log_links, log_other = scan(log_root)
require(log_files == EXPECTED_LOG_FILES, "LOG_EXACT_FILE_SET")
require(not log_dirs, "LOG_DIR_COUNT")
require(log_links == 0, "LOG_SYMLINK_COUNT")
require(log_other == 0, "LOG_NONREGULAR_COUNT")

# Source unsealed and Final sealed metadata.
source_file_modes = Counter()
source_dir_modes = Counter()
source_uid = source_root.lstat().st_uid
source_gid = source_root.lstat().st_gid

for relative in sorted(source_files):
    item = require_regular_nonsymlink(
        source_root / relative,
        f"SOURCE_FILE:{relative}",
    )
    require(item.st_uid == source_uid, f"SOURCE_FILE_OWNER:{relative}")
    require(item.st_gid == source_gid, f"SOURCE_FILE_GROUP:{relative}")
    source_file_modes[f"{stat.S_IMODE(item.st_mode):04o}"] += 1

for path in [
    source_root,
    *(source_root / relative for relative in sorted(source_dirs)),
]:
    item = path.lstat()
    require(stat.S_ISDIR(item.st_mode), f"SOURCE_DIRECTORY:{path}")
    require(not stat.S_ISLNK(item.st_mode), f"SOURCE_DIRECTORY_SYMLINK:{path}")
    require(item.st_uid == source_uid, f"SOURCE_DIRECTORY_OWNER:{path}")
    require(item.st_gid == source_gid, f"SOURCE_DIRECTORY_GROUP:{path}")
    source_dir_modes[f"{stat.S_IMODE(item.st_mode):04o}"] += 1

require(
    source_file_modes == Counter({"0640": 36}),
    "SOURCE_FILE_MODE_DISTRIBUTION",
)
require(
    source_dir_modes == Counter({"0750": 12}),
    "SOURCE_DIR_MODE_DISTRIBUTION",
)

final_file_modes = Counter()
final_dir_modes = Counter()

for relative in sorted(final_files):
    item = require_regular_nonsymlink(
        final_root / relative,
        f"FINAL_FILE:{relative}",
    )
    require(item.st_uid == source_uid, f"FINAL_FILE_OWNER:{relative}")
    require(item.st_gid == source_gid, f"FINAL_FILE_GROUP:{relative}")
    final_file_modes[f"{stat.S_IMODE(item.st_mode):04o}"] += 1

for path in [
    final_root,
    *(final_root / relative for relative in sorted(final_dirs)),
]:
    item = path.lstat()
    require(stat.S_ISDIR(item.st_mode), f"FINAL_DIRECTORY:{path}")
    require(not stat.S_ISLNK(item.st_mode), f"FINAL_DIRECTORY_SYMLINK:{path}")
    require(item.st_uid == source_uid, f"FINAL_DIRECTORY_OWNER:{path}")
    require(item.st_gid == source_gid, f"FINAL_DIRECTORY_GROUP:{path}")
    final_dir_modes[f"{stat.S_IMODE(item.st_mode):04o}"] += 1

require(
    final_file_modes == Counter({"0444": 36}),
    "FINAL_FILE_MODE_DISTRIBUTION",
)
require(
    final_dir_modes == Counter({"0555": 12}),
    "FINAL_DIR_MODE_DISTRIBUTION",
)

source_owner = pwd.getpwuid(source_uid).pw_name
source_group = grp.getgrgid(source_gid).gr_name

# Final Packet manifest.
packet_manifest = load_json(packet_root / "packet-manifest.json")
require(packet_manifest["phase"] == PHASE, "PACKET_PHASE")
require(packet_manifest["source_phase"] == SOURCE_PHASE, "PACKET_SOURCE_PHASE")
require(
    packet_manifest["status"]
    == "FINAL_EVIDENCE_REGISTRATION_AND_SEAL_EXECUTED",
    "PACKET_STATUS",
)
require(
    packet_manifest["packet_file_count_excluding_manifest"] == 33,
    "PACKET_MANIFEST_ENTRY_COUNT",
)
require(len(packet_manifest["packet_files"]) == 33, "PACKET_MANIFEST_LIST_LENGTH")
require(
    packet_manifest["candidate_artifact_count"] == 10,
    "PACKET_CANDIDATE_COUNT",
)
require(packet_manifest["snapshot_file_count"] == 19, "PACKET_SNAPSHOT_COUNT")
require(packet_manifest["validation_log_count"] == 3, "PACKET_LOG_COUNT")
require(
    packet_manifest["source_packet_human_review"] == "PASS",
    "PACKET_SOURCE_HUMAN_REVIEW",
)
require(
    packet_manifest["source_packet_human_review_decision"]
    == "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD",
    "PACKET_SOURCE_HUMAN_DECISION",
)
require(
    packet_manifest["nested_packet_manifest_included"] is True,
    "PACKET_NESTED_PACKET",
)
require(
    packet_manifest["nested_evidence_manifest_expected"] is True,
    "PACKET_NESTED_EVIDENCE_EXPECTED",
)
require(
    packet_manifest["root_packet_manifest_only_excluded"] is True,
    "PACKET_ROOT_ONLY_EXCLUSION",
)
require(
    packet_manifest["final_evidence_registration_executed"] is True,
    "PACKET_REGISTRATION_EXECUTED",
)
require(
    packet_manifest["final_evidence_seal_execution_authorized"] is True,
    "PACKET_SEAL_AUTHORIZED",
)
require(
    packet_manifest["root_readonly_verification_reexecution_allowed"] is False,
    "PACKET_REEXECUTION",
)
require(
    packet_manifest["one_shot_guard_change_allowed"] is False,
    "PACKET_GUARD_CHANGE",
)
require(
    packet_manifest["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "PACKET_RUNNER_HOLD",
)
require(
    packet_manifest["production_release_decision"] == "HOLD",
    "PACKET_RELEASE_HOLD",
)

packet_declared = {item["name"] for item in packet_manifest["packet_files"]}
packet_actual_excluding_root = EXPECTED_PACKET_FILES - {"packet-manifest.json"}
require(packet_declared == packet_actual_excluding_root, "PACKET_EXACT_DECLARATION")
require(NESTED_PACKET_MANIFEST in packet_declared, "NESTED_PACKET_NOT_INCLUDED")
require("packet-manifest.json" not in packet_declared, "ROOT_PACKET_NOT_EXCLUDED")
for item in packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(sha256(path) == item["sha256"], f"PACKET_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"PACKET_SIZE:{item['name']}",
    )

# Final Evidence manifest.
evidence_manifest = parse_evidence_manifest(
    final_root / "evidence-manifest.txt"
)
evidence_actual_excluding_root = (
    EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"}
)
require(len(evidence_manifest) == 35, "EVIDENCE_MANIFEST_ENTRY_COUNT")
require(
    set(evidence_manifest) == evidence_actual_excluding_root,
    "EVIDENCE_EXACT_DECLARATION",
)
require(
    NESTED_EVIDENCE_MANIFEST in evidence_manifest,
    "NESTED_EVIDENCE_NOT_INCLUDED",
)
require(
    "evidence-manifest.txt" not in evidence_manifest,
    "ROOT_EVIDENCE_NOT_EXCLUDED",
)
for relative, digest in evidence_manifest.items():
    require(
        sha256(final_root / relative) == digest,
        f"EVIDENCE_SHA:{relative}",
    )

# Candidate manifest and copied candidate set.
candidate_manifest = load_json(candidate_root / "candidate-manifest.json")
require(candidate_manifest["phase"] == SOURCE_PHASE, "CANDIDATE_PHASE")
require(
    candidate_manifest["source_phase"]
    == "TST-5D-W2B-I2F-3E-J-R2-R8-R3",
    "CANDIDATE_SOURCE_PHASE",
)
require(candidate_manifest["total_file_count"] == 10, "CANDIDATE_TOTAL")
require(
    candidate_manifest["file_count_excluding_manifest"] == 9,
    "CANDIDATE_EXCLUDING",
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

# Snapshot manifest and Snapshot content.
snapshot_manifest = load_json(
    candidate_root / "r2-r8-r3-snapshot-manifest.json"
)
require(
    snapshot_manifest["phase"]
    == "TST-5D-W2B-I2F-3E-J-R2-R8-R3",
    "SNAPSHOT_PHASE",
)
require(
    snapshot_manifest["status"] == "SNAPSHOT_CANDIDATE_PREPARED_UNSEALED",
    "SNAPSHOT_STATUS",
)
require(snapshot_manifest["snapshot_file_count"] == 19, "SNAPSHOT_MANIFEST_COUNT")
require(
    snapshot_manifest["snapshot_directory_count_excluding_root"] == 7,
    "SNAPSHOT_MANIFEST_DIR_COUNT",
)
require(
    snapshot_manifest["snapshot_byte_equivalence"] == "PASS",
    "SNAPSHOT_BYTE_EQUIVALENCE",
)
require(
    snapshot_manifest["snapshot_size_equivalence"] == "PASS",
    "SNAPSHOT_SIZE_EQUIVALENCE",
)
require(
    snapshot_manifest["snapshot_sha256_equivalence"] == "PASS",
    "SNAPSHOT_SHA_EQUIVALENCE",
)
require(
    snapshot_manifest["source_mutation_performed"] is False,
    "SNAPSHOT_SOURCE_MUTATION",
)
require(len(snapshot_manifest["files"]) == 19, "SNAPSHOT_MANIFEST_ENTRY_COUNT")
require(
    {item["snapshot_relative_path"] for item in snapshot_manifest["files"]}
    == EXPECTED_SNAPSHOT_FILES,
    "SNAPSHOT_MANIFEST_EXACT_SET",
)
for item in snapshot_manifest["files"]:
    relative = item["snapshot_relative_path"]
    path = snapshot_root / relative
    require(sha256(path) == item["sha256"], f"SNAPSHOT_SHA:{relative}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"SNAPSHOT_SIZE:{relative}",
    )
    require(
        item["source_mode"].isdigit() and len(item["source_mode"]) == 4,
        f"SNAPSHOT_SOURCE_MODE:{relative}",
    )
    require(isinstance(item["source_uid"], int), f"SNAPSHOT_SOURCE_UID:{relative}")
    require(isinstance(item["source_gid"], int), f"SNAPSHOT_SOURCE_GID:{relative}")
    require(bool(item["source_owner"]), f"SNAPSHOT_SOURCE_OWNER:{relative}")
    require(bool(item["source_group"]), f"SNAPSHOT_SOURCE_GROUP:{relative}")

# Specific root verification evidence remains fixed.
output_path = (
    snapshot_root
    / "root-verification/root-readonly-verification-output.txt"
)
require(
    output_path.read_text(encoding="utf-8").splitlines()
    == EXPECTED_OUTPUT_LINES,
    "ROOT_OUTPUT_EXACT_CONTENT",
)
require(
    sha256(output_path)
    == "582ce48b8847b578035e82131ca374101a7ad189ad9e988ee73b775e687ed88a",
    "ROOT_OUTPUT_SHA",
)

guard_path = snapshot_root / "one-shot-guard/execution-attempt.txt"
guard_values: dict[str, str] = {}
for line in guard_path.read_text(encoding="utf-8").splitlines():
    key, value = line.split("=", 1)
    require(key not in guard_values, f"GUARD_DUPLICATE:{key}")
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
require(guard_values["verifier_exit_code"] == "0", "GUARD_VERIFIER_EXIT")
require(
    guard_values["output_log_sha256"] == sha256(output_path),
    "GUARD_OUTPUT_SHA",
)

wrapper_path = next(
    snapshot_root / relative
    for relative in EXPECTED_SNAPSHOT_FILES
    if relative.startswith("executed-wrapper/")
)
require(
    sha256(wrapper_path)
    == "714e98a5ed0cf2e3e8db320b7d4fdda234e015cb898e7f2d1d2a16dabc255b04",
    "WRAPPER_FIXED_SHA",
)

# Registered source 32-file equivalence.
require(len(COPY_FROM_SOURCE) == 32, "REGISTERED_SOURCE_COUNT")
for relative in sorted(COPY_FROM_SOURCE):
    source = source_root / relative
    destination = final_root / relative
    require(
        source.read_bytes() == destination.read_bytes(),
        f"REGISTERED_BYTE_EQUIVALENCE:{relative}",
    )
    require(
        sha256(source) == sha256(destination),
        f"REGISTERED_SHA_EQUIVALENCE:{relative}",
    )
    require(
        source.stat().st_size == destination.stat().st_size,
        f"REGISTERED_SIZE_EQUIVALENCE:{relative}",
    )

# Final approval text.
approval_text = (
    packet_root / "human-approval-verbatim.txt"
).read_text(encoding="utf-8")
approval_markers = (
    "APPROVE_3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_REGISTRATION_AND_SEAL_EXECUTION",
    "R2_R8_R3_R1_PACKET_HUMAN_REVIEW=PASS",
    (
        "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD"
    ),
    "8129fdce8ce1c1767a261523f16a63ca56c867ef635829c8c1e6ef5bd8953d56",
    "0220b3bea10a53cff6a1c7a1cc19527bf7a827921ba856662aff80336c8b47b6",
    "eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f",
    "afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c",
    "2c572560f375b369eae22f71460c531cc298190a69309e93cb7b86ab7e7eab89",
    "FINAL_EVIDENCE_REGISTRATION_EXECUTION_ALLOWED=true",
    "FINAL_EVIDENCE_SEAL_EXECUTION_ALLOWED=true",
    "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false",
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

# Final result record.
result = load_json(final_root / "result.json")
require(result["phase"] == PHASE, "RESULT_PHASE")
require(result["source_phase"] == SOURCE_PHASE, "RESULT_SOURCE_PHASE")
require(
    result["result"]
    == (
        "PASS_W2B_I2F3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
        "REGISTRATION_AND_SEAL_EXECUTED_HUMAN_REVIEW_REQUIRED"
    ),
    "RESULT_VALUE",
)
require(result["evidence_root"] == final_relative, "RESULT_EVIDENCE_ROOT")
require(result["source_evidence_root"] == source_relative, "RESULT_SOURCE_ROOT")
require(
    result["source_packet_human_review"] == "PASS",
    "RESULT_SOURCE_HUMAN_REVIEW",
)
require(
    result["source_packet_human_review_decision"]
    == "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD",
    "RESULT_SOURCE_HUMAN_DECISION",
)
for key in (
    "source_result_sha_review",
    "source_packet_manifest_sha_review",
    "source_candidate_manifest_sha_review",
    "source_snapshot_manifest_sha_review",
    "source_evidence_manifest_sha_review",
):
    require(result[key] == "PASS", f"RESULT_SOURCE_PASS:{key}")
require(result["source_evidence_unchanged"] is True, "RESULT_SOURCE_UNCHANGED")
require(
    result["final_evidence_registration_execution_allowed"] is True,
    "RESULT_REGISTRATION_ALLOWED",
)
require(
    result["final_evidence_seal_execution_allowed"] is True,
    "RESULT_SEAL_ALLOWED",
)
require(
    result["final_evidence_registration_executed"] is True,
    "RESULT_REGISTRATION_EXECUTED",
)
require(
    result["final_evidence_seal_executed"] is True,
    "RESULT_SEAL_EXECUTED",
)
require(
    result["seal_commit_timestamp_utc"] == SEAL_TIMESTAMP,
    "RESULT_SEAL_TIMESTAMP",
)
require(result["final_evidence_file_count"] == 36, "RESULT_FILE_COUNT")
require(
    result["final_evidence_directory_count_excluding_root"] == 11,
    "RESULT_DIRECTORY_COUNT",
)
require(result["packet_file_count"] == 34, "RESULT_PACKET_FILE_COUNT")
require(result["packet_directory_count"] == 10, "RESULT_PACKET_DIR_COUNT")
require(
    result["packet_manifest_entry_count"] == 33,
    "RESULT_PACKET_MANIFEST_COUNT",
)
require(
    result["evidence_manifest_entry_count"] == 35,
    "RESULT_EVIDENCE_MANIFEST_COUNT",
)
require(result["candidate_artifact_count"] == 10, "RESULT_CANDIDATE_COUNT")
require(result["snapshot_file_count"] == 19, "RESULT_SNAPSHOT_COUNT")
require(result["snapshot_directory_count"] == 7, "RESULT_SNAPSHOT_DIR_COUNT")
require(result["validation_log_count"] == 3, "RESULT_LOG_COUNT")
require(result["registered_source_file_count"] == 32, "RESULT_SOURCE_FILE_COUNT")
require(
    result["registered_source_byte_equivalence"] == "PASS",
    "RESULT_BYTE_EQUIVALENCE",
)
require(
    result["registered_source_size_equivalence"] == "PASS",
    "RESULT_SIZE_EQUIVALENCE",
)
require(
    result["registered_source_sha256_equivalence"] == "PASS",
    "RESULT_SHA_EQUIVALENCE",
)
for key in (
    "nested_packet_manifest_included",
    "nested_evidence_manifest_included",
    "root_packet_manifest_only_excluded",
    "root_evidence_manifest_only_excluded",
):
    require(result[key] is True, f"RESULT_MANIFEST_TRUE:{key}")
require(result["final_file_mode"] == "0444", "RESULT_FILE_MODE")
require(result["final_directory_mode"] == "0555", "RESULT_DIRECTORY_MODE")
require(result["final_symlink_count"] == 0, "RESULT_SYMLINK_COUNT")
require(result["final_nonregular_count"] == 0, "RESULT_NONREGULAR_COUNT")
require(
    result["owner_group_change_performed"] is False,
    "RESULT_OWNER_GROUP_CHANGE",
)
require(
    result["root_readonly_verification_result"] == "ABSENT_CONFIRMED",
    "RESULT_ROOT_VERIFICATION",
)
require(
    result["root_readonly_verification_execution_attempt_count"] == 1,
    "RESULT_ATTEMPT_COUNT",
)
require(
    result["root_readonly_verification_max_executions"] == 1,
    "RESULT_MAX_EXECUTIONS",
)
for key in (
    "root_readonly_verification_reexecution_allowed",
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
    "final_production_token_created",
    "approval_binding_created",
):
    require(result[key] is False, f"RESULT_FALSE:{key}")
require(result["protected_sha_unchanged"] is True, "RESULT_PROTECTED_SHA")
require(
    result["packet_manifest_sha256"] == FINAL_FIXED_SHA[
        "packet-snapshot/packet-manifest.json"
    ],
    "RESULT_PACKET_MANIFEST_SHA",
)
require(
    result["candidate_manifest_sha256"] == FINAL_FIXED_SHA[
        "packet-snapshot/candidate-artifacts/candidate-manifest.json"
    ],
    "RESULT_CANDIDATE_MANIFEST_SHA",
)
require(
    result["snapshot_manifest_sha256"] == FINAL_FIXED_SHA[
        "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json"
    ],
    "RESULT_SNAPSHOT_MANIFEST_SHA",
)
require(
    result["post_seal_validation_required_before_script_success"] is True,
    "RESULT_POST_SEAL_REQUIRED",
)
require(
    result["post_seal_human_review_required"] is True,
    "RESULT_HUMAN_REVIEW_REQUIRED",
)
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
    result["next_gate"]
    == (
        "HUMAN_REVIEW_3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
        "REGISTRATION_AND_SEAL_RESULT_READONLY"
    ),
    "RESULT_NEXT_GATE",
)

# Candidate safety files remain static and unexecuted.
registration_policy = load_json(
    candidate_root / "r2-r8-r3-registration-policy.json"
)
source_contract = load_json(candidate_root / "r2-r8-r3-source-contract.json")
seal_contract = load_json(candidate_root / "r2-r8-r3-seal-contract.json")
require(
    registration_policy["evidence_registration_executed"] is False,
    "CANDIDATE_POLICY_REGISTRATION_STATE",
)
require(
    registration_policy["evidence_seal_executed"] is False,
    "CANDIDATE_POLICY_SEAL_STATE",
)
require(
    registration_policy["root_readonly_verification_reexecution_allowed"]
    is False,
    "CANDIDATE_POLICY_REEXECUTION",
)
require(
    registration_policy["one_shot_guard_change_allowed"] is False,
    "CANDIDATE_POLICY_GUARD_CHANGE",
)
require(
    source_contract["root_verification_reexecution_allowed"] is False,
    "CANDIDATE_SOURCE_REEXECUTION",
)
require(
    source_contract["one_shot_guard_change_allowed"] is False,
    "CANDIDATE_SOURCE_GUARD_CHANGE",
)
require(
    source_contract["sudoers_content_read_allowed"] is False,
    "CANDIDATE_SOURCE_CONTENT_READ",
)
require(
    source_contract["sudoers_change_allowed"] is False,
    "CANDIDATE_SOURCE_SUDOERS_CHANGE",
)
require(
    seal_contract["seal_execution_status"] == "NOT_EXECUTED",
    "CANDIDATE_SEAL_STATUS",
)
require(
    seal_contract["seal_execution_allowed_in_current_phase"] is False,
    "CANDIDATE_SEAL_CURRENT_PHASE",
)
require(
    seal_contract["future_execution_requires_new_explicit_human_approval"]
    is True,
    "CANDIDATE_SEAL_APPROVAL_GATE",
)
require(
    seal_contract["production_release_decision"] == "HOLD",
    "CANDIDATE_SEAL_RELEASE_HOLD",
)

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

# Validation logs are the approved static logs; no candidate executables run.
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
require(
    validator_log.splitlines()
    == [
        "VALIDATOR_SOURCE_COMPILE=PASS",
        "FINAL_RUNTIME_VALIDATOR_REQUIRED_BEFORE_SCRIPT_SUCCESS=true",
        "FINAL_RUNTIME_VALIDATOR_OUTPUT_PERSISTED=false",
        "REASON=AVOID_SELF_REFERENTIAL_MANIFEST_MUTATION",
    ],
    "VALIDATOR_LOG_CONTENT",
)

negative_log = (log_root / "negative-tests.log").read_text(encoding="utf-8")
require(
    negative_log.splitlines()
    == [
        "NEGATIVE_TEST_SOURCE_COMPILE=PASS",
        "FINAL_RUNTIME_NEGATIVE_TEST_COUNT_REQUIRED=18",
        "FINAL_RUNTIME_NEGATIVE_TESTS_REQUIRED_BEFORE_SCRIPT_SUCCESS=true",
        "FINAL_RUNTIME_NEGATIVE_TEST_OUTPUT_PERSISTED=false",
        "REASON=AVOID_SELF_REFERENTIAL_MANIFEST_MUTATION",
    ],
    "NEGATIVE_LOG_CONTENT",
)

validator_source = (
    candidate_root / "validate_r2_r8_r3_packet.py"
).read_text(encoding="utf-8")
negative_source = (
    candidate_root / "test_r2_r8_r3_packet_negative.py"
).read_text(encoding="utf-8")
compile(
    validator_source,
    str(candidate_root / "validate_r2_r8_r3_packet.py"),
    "exec",
)
compile(
    negative_source,
    str(candidate_root / "test_r2_r8_r3_packet_negative.py"),
    "exec",
)
negative_test_names = re.findall(
    r"^    def (test_[A-Za-z0-9_]+)\(self\) -> None:$",
    negative_source,
    flags=re.MULTILINE,
)
require(len(negative_test_names) == 18, "NEGATIVE_TEST_METHOD_COUNT")
require(len(set(negative_test_names)) == 18, "NEGATIVE_TEST_METHOD_UNIQUENESS")

# Independent reconstruction of post-seal validation.
require(final_file_modes == Counter({"0444": 36}), "POSTSEAL_FILE_MODE")
require(final_dir_modes == Counter({"0555": 12}), "POSTSEAL_DIR_MODE")
require(final_links == 0, "POSTSEAL_SYMLINK_COUNT")
require(final_other == 0, "POSTSEAL_NONREGULAR_COUNT")
require(len(packet_manifest["packet_files"]) == 33, "POSTSEAL_PACKET_COUNT")
require(len(evidence_manifest) == 35, "POSTSEAL_EVIDENCE_COUNT")
require(len(COPY_FROM_SOURCE) == 32, "POSTSEAL_SOURCE_COUNT")
require(NESTED_PACKET_MANIFEST in packet_declared, "POSTSEAL_NESTED_PACKET")
require(
    NESTED_EVIDENCE_MANIFEST in evidence_manifest,
    "POSTSEAL_NESTED_EVIDENCE",
)
require(not list(final_root.rglob("*.pyc")), "FINAL_BYTECODE_SIDE_EFFECT")
require(not list(source_root.rglob("*.pyc")), "SOURCE_BYTECODE_SIDE_EFFECT")

# Protected SHA before final identity comparison.
for relative, expected in PROTECTED_SHA.items():
    path = repo_root / relative
    require_regular_nonsymlink(path, f"PROTECTED:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

# No mutation during the review.
source_identity_after = tree_identity(source_root)
final_identity_after = tree_identity(final_root)
require(
    source_identity_after == source_identity_before,
    "SOURCE_EVIDENCE_CHANGED_DURING_REVIEW",
)
require(
    final_identity_after == final_identity_before,
    "FINAL_EVIDENCE_CHANGED_DURING_REVIEW",
)

for relative, expected in PROTECTED_SHA.items():
    require(
        sha256(repo_root / relative) == expected,
        f"PROTECTED_CHANGED:{relative}",
    )

print("FINAL_RESULT_SHA_REVIEW=PASS")
print("FINAL_PACKET_MANIFEST_SHA_REVIEW=PASS")
print("FINAL_CANDIDATE_MANIFEST_SHA_REVIEW=PASS")
print("FINAL_SNAPSHOT_MANIFEST_SHA_REVIEW=PASS")
print("FINAL_EVIDENCE_MANIFEST_SHA_REVIEW=PASS")
print("FINAL_EVIDENCE_ROOT_PATH_REVIEW=PASS")
print(f"FINAL_SEAL_COMMIT_TIMESTAMP_UTC={SEAL_TIMESTAMP}")
print("SOURCE_R3_R1_FIXED_SHA_REVIEW=PASS")
print("SOURCE_R3_R1_PACKET_EVIDENCE_UNCHANGED=true")
print("FINAL_EVIDENCE_FILE_COUNT=36")
print("FINAL_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=11")
print("FINAL_PACKET_FILE_COUNT=34")
print("FINAL_PACKET_DIRECTORY_COUNT=10")
print("FINAL_PACKET_MANIFEST_ENTRY_COUNT=33")
print("FINAL_EVIDENCE_MANIFEST_ENTRY_COUNT=35")
print("FINAL_CANDIDATE_ARTIFACT_COUNT=10")
print("FINAL_SNAPSHOT_FILE_COUNT=19")
print("FINAL_SNAPSHOT_DIRECTORY_COUNT=7")
print("FINAL_VALIDATION_LOG_COUNT=3")
print("REGISTERED_SOURCE_FILE_COUNT=32")
print("REGISTERED_SOURCE_BYTE_EQUIVALENCE=PASS")
print("REGISTERED_SOURCE_SIZE_EQUIVALENCE=PASS")
print("REGISTERED_SOURCE_SHA256_EQUIVALENCE=PASS")
print("NESTED_PACKET_MANIFEST_INCLUDED=true")
print("NESTED_EVIDENCE_MANIFEST_INCLUDED=true")
print("ROOT_PACKET_MANIFEST_ONLY_EXCLUDED=true")
print("ROOT_EVIDENCE_MANIFEST_ONLY_EXCLUDED=true")
print(f"FINAL_FILE_MODE_DISTRIBUTION={dict(sorted(final_file_modes.items()))}")
print(f"FINAL_DIRECTORY_MODE_DISTRIBUTION={dict(sorted(final_dir_modes.items()))}")
print("FINAL_SYMLINK_COUNT=0")
print("FINAL_NONREGULAR_COUNT=0")
print("FINAL_OWNER_GROUP_CHANGE_PERFORMED=false")
print(f"FINAL_OWNER={source_owner}")
print(f"FINAL_GROUP={source_group}")
print("FINAL_EXACT_FILE_SET_REVIEW=PASS")
print("FINAL_PACKET_MANIFEST_CONTENT_REVIEW=PASS")
print("FINAL_EVIDENCE_MANIFEST_CONTENT_REVIEW=PASS")
print("FINAL_CANDIDATE_MANIFEST_CONTENT_REVIEW=PASS")
print("FINAL_SNAPSHOT_MANIFEST_CONTENT_REVIEW=PASS")
print("FINAL_APPROVAL_TEXT_REVIEW=PASS")
print("FINAL_RESULT_RECORD_REVIEW=PASS")
print("ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED")
print("ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1")
print("ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
print("FINAL_EVIDENCE_REGISTRATION_EXECUTED=true")
print("FINAL_EVIDENCE_SEAL_EXECUTED=true")
print("POST_SEAL_READONLY_VALIDATION_RECONSTRUCTED=PASS")
print(
    "POST_SEAL_READONLY_VALIDATION_ORIGINAL_CONSOLE_MARKER="
    "USER_PROVIDED_TRANSCRIPT_PASS"
)
print("POST_SEAL_HUMAN_REVIEW_REQUIRED=true")
print("CANDIDATE_BLOCKED_ENTRYPOINT_EXECUTED=false")
print("CANDIDATE_VALIDATOR_EXECUTED=false")
print("CANDIDATE_NEGATIVE_TESTS_EXECUTED=false")
print("FINAL_EVIDENCE_MUTATION=false")
print("SOURCE_R3_R1_EVIDENCE_MUTATION=false")
print("FINAL_BYTECODE_SIDE_EFFECT=false")
print("PROTECTED_SHA_REVIEW=PASS")
print("SUDOERS_CHANGED=false")
print("AUTOMATIC_DEPLOYMENT_PERFORMED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("PRODUCTION_DIRECTORY_CREATED=false")
print("PRODUCTION_FILE_CREATED=false")
print("PRODUCTION_PROCESS_SIGNAL_SENT=false")
print("PRODUCTION_DATABASE_SQL_CONNECTION_USED=false")
print("PRODUCTION_BACKUP_CREATED=false")
print("MIGRATION_EXECUTED=false")
print("EXTERNAL_NETWORK_USED=false")
print("FINAL_PRODUCTION_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "FINAL_EVIDENCE_RESULT_HUMAN_REVIEW_DECISION="
    "APPROVE_FINAL_REGISTRATION_AND_SEAL_RESULT_WITH_PRODUCTION_HOLD"
)
print(
    "NEXT_GATE="
    "HUMAN_DECISION_FOR_3E_J_R2_R8_R3_R1_FINAL_SEAL_"
    "ACCEPTANCE_AND_DEPLOYMENT_GATE_SELECTION"
)
PY

printf '\n===== FINAL SEALED EVIDENCE HUMAN REVIEW MARKERS =====\n'

echo "FINAL_EVIDENCE_REGISTRATION_AND_SEAL_RESULT_HUMAN_REVIEW=PASS"
echo "FINAL_EVIDENCE_RESULT_HUMAN_REVIEW_DECISION=APPROVE_FINAL_REGISTRATION_AND_SEAL_RESULT_WITH_PRODUCTION_HOLD"
echo "FINAL_EVIDENCE_REGISTRATION_EXECUTED=true"
echo "FINAL_EVIDENCE_SEAL_EXECUTED=true"
echo "POST_SEAL_READONLY_VALIDATION_RECONSTRUCTED=PASS"
echo "SOURCE_R3_R1_PACKET_EVIDENCE_UNCHANGED=true"
echo "FINAL_EVIDENCE_MUTATION=false"
echo "SOURCE_R3_R1_EVIDENCE_MUTATION=false"
echo "FINAL_FILE_MODE=0444"
echo "FINAL_DIRECTORY_MODE=0555"
echo "FINAL_SYMLINK_COUNT=0"
echo "FINAL_NONREGULAR_COUNT=0"
echo "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false"
echo "ONE_SHOT_GUARD_CHANGE_ALLOWED=false"
echo "SUDOERS_CHANGED=false"
echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
echo "FINAL_PRODUCTION_TOKEN_CREATED=false"
echo "APPROVAL_BINDING_CREATED=false"
echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
echo "WRITER_FREEZE_EXECUTION=HOLD"
echo "PRODUCTION_RELEASE_DECISION=HOLD"
echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
echo "NEXT_GATE=HUMAN_DECISION_FOR_3E_J_R2_R8_R3_R1_FINAL_SEAL_ACCEPTANCE_AND_DEPLOYMENT_GATE_SELECTION"
echo "REVIEW_COMMAND_EXIT_CODE=0"
