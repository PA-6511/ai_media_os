#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SOURCE_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-result-evidence-registration-and-seal-packet-preparation-20260726T030618Z-526407"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"

R1_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-r1-nested-manifest-basename-exclusion-correction-packet-preparation-20260726T032952Z-526992"
R1_ROOT="${REPO_ROOT}/${R1_REL}"
PACKET_ROOT="${R1_ROOT}/packet-snapshot"
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
test -d "$R1_ROOT"
test -d "$PACKET_ROOT"
test -d "$CANDIDATE_ROOT"
test -d "$SNAPSHOT_ROOT"
test -d "$LOG_ROOT"

cd "$REPO_ROOT"

printf '\n===== R3-R1 FIXED SHA READ-ONLY REVIEW =====\n'

sha256sum -c <<SHAS
8129fdce8ce1c1767a261523f16a63ca56c867ef635829c8c1e6ef5bd8953d56  ${R1_ROOT}/result.json
0220b3bea10a53cff6a1c7a1cc19527bf7a827921ba856662aff80336c8b47b6  ${PACKET_ROOT}/packet-manifest.json
eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f  ${CANDIDATE_ROOT}/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${CANDIDATE_ROOT}/r2-r8-r3-snapshot-manifest.json
2c572560f375b369eae22f71460c531cc298190a69309e93cb7b86ab7e7eab89  ${R1_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== SOURCE R3 IMMUTABLE FAILED EVIDENCE REVIEW =====\n'

sha256sum -c <<SHAS
158059471540ecf81cfc9e2d03b7bab69218a6c71e00f16fb34879c2e287a6d7  ${SOURCE_ROOT}/result.json
43221ebdaf1e092521072f10a1864e269a21f5ab064716638484068c50293665  ${SOURCE_ROOT}/packet-snapshot/packet-manifest.json
7c7fb60906b7215f5293608ded5f335644b8a5836b89a02cbbdb478e3d3973ed  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json
75aa57aa74c8300202d7b7c823118bc70d532aee622dfef67778c80abc49282a  ${SOURCE_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== R3-R1 CORRECTION PACKET HUMAN REVIEW =====\n'

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$SOURCE_ROOT" \
  "$R1_ROOT" \
  "$PACKET_ROOT" \
  "$CANDIDATE_ROOT" \
  "$SNAPSHOT_ROOT" \
  "$LOG_ROOT" \
  "$SOURCE_REL" \
  "$R1_REL" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import pwd
import grp
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
source_root = Path(sys.argv[2]).resolve(strict=True)
r1_root = Path(sys.argv[3]).resolve(strict=True)
packet_root = Path(sys.argv[4]).resolve(strict=True)
candidate_root = Path(sys.argv[5]).resolve(strict=True)
snapshot_root = Path(sys.argv[6]).resolve(strict=True)
log_root = Path(sys.argv[7]).resolve(strict=True)
source_relative = sys.argv[8]
r1_relative = sys.argv[9]

PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3-R1"
SOURCE_PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3"
TARGET = "/etc/sudoers.d/ai-media-os-3e-j-root-helper"

R1_FIXED_SHA = {
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

SOURCE_FIXED_SHA = {
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

SOURCE_REPLACED_OR_REGENERATED = {
    "result.json",
    "evidence-manifest.txt",
    "packet-snapshot/packet-manifest.json",
    "packet-snapshot/human-approval-verbatim.txt",
    "packet-snapshot/candidate-artifacts/candidate-manifest.json",
    "packet-snapshot/candidate-artifacts/r2-r8-r3-result-record.json",
    "packet-snapshot/candidate-artifacts/validate_r2_r8_r3_packet.py",
    "packet-snapshot/candidate-artifacts/test_r2_r8_r3_packet_negative.py",
    "packet-snapshot/candidate-artifacts/r2-r8-r3-operation-manual.md",
    "packet-snapshot/validation-logs/python-compile.log",
    "packet-snapshot/validation-logs/validator.log",
    "packet-snapshot/validation-logs/negative-tests.log",
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
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            item = entry.stat(follow_symlinks=False)
            path = Path(entry.path)
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
    require(links == 0, f"TREE_IDENTITY_SYMLINK:{root}")
    require(other == 0, f"TREE_IDENTITY_NONREGULAR:{root}")
    identity: dict[str, tuple[str, int, int, int, int]] = {}
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
    for relative in sorted(directories):
        path = root / relative
        item = path.lstat()
        identity[relative + "/"] = (
            "DIRECTORY",
            0,
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    root_item = root.lstat()
    identity["./"] = (
        "DIRECTORY",
        0,
        stat.S_IMODE(root_item.st_mode),
        root_item.st_uid,
        root_item.st_gid,
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
    r1_root.relative_to(repo_root).as_posix() == r1_relative,
    "R1_ROOT_BINDING",
)
require(packet_root == r1_root / "packet-snapshot", "PACKET_ROOT_BINDING")
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
for relative, expected in R1_FIXED_SHA.items():
    path = r1_root / relative
    require_regular_nonsymlink(path, f"R1_FIXED:{relative}")
    require(sha256(path) == expected, f"R1_FIXED_SHA:{relative}")

for relative, expected in SOURCE_FIXED_SHA.items():
    path = source_root / relative
    require_regular_nonsymlink(path, f"SOURCE_FIXED:{relative}")
    require(sha256(path) == expected, f"SOURCE_FIXED_SHA:{relative}")

# Full tree identities before executing any validator/test.
source_identity_before = tree_identity(source_root)
r1_identity_before = tree_identity(r1_root)

# Source R3 exact immutable failed state.
source_files, source_dirs, source_links, source_other = scan(source_root)
require(source_files == EXPECTED_EVIDENCE_FILES, "SOURCE_EXACT_FILE_SET")
require(source_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "SOURCE_EXACT_DIR_SET")
require(len(source_files) == 36, "SOURCE_FILE_COUNT")
require(len(source_dirs) == 11, "SOURCE_DIR_COUNT")
require(source_links == 0, "SOURCE_SYMLINK_COUNT")
require(source_other == 0, "SOURCE_NONREGULAR_COUNT")

source_packet = load_json(source_root / "packet-snapshot/packet-manifest.json")
require(source_packet["phase"] == SOURCE_PHASE, "SOURCE_PACKET_PHASE")
require(
    source_packet["packet_file_count_excluding_manifest"] == 32,
    "SOURCE_PACKET_COUNT_FIELD",
)
require(len(source_packet["packet_files"]) == 32, "SOURCE_PACKET_LIST_LENGTH")
source_declared = {item["name"] for item in source_packet["packet_files"]}
source_packet_actual = (
    EXPECTED_PACKET_FILES - {"packet-manifest.json"}
)
require(
    source_packet_actual - source_declared == {NESTED_PACKET_MANIFEST},
    "SOURCE_PACKET_MISSING_DIAGNOSIS",
)
require(
    not (source_declared - source_packet_actual),
    "SOURCE_PACKET_EXTRA_DIAGNOSIS",
)

source_evidence_manifest = parse_evidence_manifest(
    source_root / "evidence-manifest.txt"
)
source_evidence_actual = EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"}
require(
    len(source_evidence_manifest) == 34,
    "SOURCE_EVIDENCE_MANIFEST_ENTRY_COUNT",
)
require(
    source_evidence_actual - set(source_evidence_manifest)
    == {NESTED_EVIDENCE_MANIFEST},
    "SOURCE_EVIDENCE_MISSING_DIAGNOSIS",
)
require(
    not (set(source_evidence_manifest) - source_evidence_actual),
    "SOURCE_EVIDENCE_EXTRA_DIAGNOSIS",
)

source_result = load_json(source_root / "result.json")
require(source_result["phase"] == SOURCE_PHASE, "SOURCE_RESULT_PHASE")
require(
    source_result["packet_preparation_only"] is True,
    "SOURCE_PACKET_PREPARATION_ONLY",
)
require(
    source_result["packet_evidence_seal_performed"] is False,
    "SOURCE_PACKET_SEAL_STATE",
)
require(
    source_result["production_release_decision"] == "HOLD",
    "SOURCE_RELEASE_HOLD",
)

# New R3-R1 exact tree and metadata.
r1_files, r1_dirs, r1_links, r1_other = scan(r1_root)
require(r1_files == EXPECTED_EVIDENCE_FILES, "R1_EXACT_FILE_SET")
require(r1_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "R1_EXACT_DIR_SET")
require(len(r1_files) == 36, "R1_FILE_COUNT")
require(len(r1_dirs) == 11, "R1_DIR_COUNT")
require(r1_links == 0, "R1_SYMLINK_COUNT")
require(r1_other == 0, "R1_NONREGULAR_COUNT")

repo_item = repo_root.stat()
expected_uid = repo_item.st_uid
expected_gid = repo_item.st_gid

file_modes = Counter()
for relative in sorted(r1_files):
    path = r1_root / relative
    item = require_regular_nonsymlink(path, f"R1_FILE:{relative}")
    require(item.st_uid == expected_uid, f"R1_FILE_OWNER:{relative}")
    require(item.st_gid == expected_gid, f"R1_FILE_GROUP:{relative}")
    file_modes[f"{stat.S_IMODE(item.st_mode):04o}"] += 1

directory_modes = Counter()
for path in [
    r1_root,
    *(r1_root / relative for relative in sorted(r1_dirs)),
]:
    item = path.lstat()
    require(stat.S_ISDIR(item.st_mode), f"R1_DIRECTORY:{path}")
    require(not stat.S_ISLNK(item.st_mode), f"R1_DIRECTORY_SYMLINK:{path}")
    require(item.st_uid == expected_uid, f"R1_DIRECTORY_OWNER:{path}")
    require(item.st_gid == expected_gid, f"R1_DIRECTORY_GROUP:{path}")
    directory_modes[f"{stat.S_IMODE(item.st_mode):04o}"] += 1

require(file_modes == Counter({"0640": 36}), "R1_FILE_MODE_DISTRIBUTION")
require(directory_modes == Counter({"0750": 12}), "R1_DIR_MODE_DISTRIBUTION")

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
require(
    not any(relative.endswith(".pyc") for relative in candidate_files),
    "CANDIDATE_PYC_PRESENT",
)

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

# Source/new unchanged file equivalence.
unchanged_relatives = sorted(source_files - SOURCE_REPLACED_OR_REGENERATED)
require(len(SOURCE_REPLACED_OR_REGENERATED) == 12, "REPLACEMENT_SET_COUNT")
require(len(unchanged_relatives) == 24, "UNCHANGED_FILE_COUNT")
for relative in unchanged_relatives:
    source_path = source_root / relative
    new_path = r1_root / relative
    require(
        source_path.read_bytes() == new_path.read_bytes(),
        f"UNCHANGED_BYTE_MISMATCH:{relative}",
    )
    require(
        sha256(source_path) == sha256(new_path),
        f"UNCHANGED_SHA_MISMATCH:{relative}",
    )
    require(
        source_path.stat().st_size == new_path.stat().st_size,
        f"UNCHANGED_SIZE_MISMATCH:{relative}",
    )

# Candidate manifest.
candidate_manifest = load_json(candidate_root / "candidate-manifest.json")
require(candidate_manifest["phase"] == PHASE, "CANDIDATE_PHASE")
require(candidate_manifest["source_phase"] == SOURCE_PHASE, "CANDIDATE_SOURCE_PHASE")
require(
    candidate_manifest["status"]
    == (
        "NESTED_MANIFEST_BASENAME_EXCLUSION_CORRECTION_"
        "PACKET_PREPARED_NO_EXECUTION"
    ),
    "CANDIDATE_STATUS",
)
require(candidate_manifest["total_file_count"] == 10, "CANDIDATE_TOTAL_COUNT")
require(
    candidate_manifest["file_count_excluding_manifest"] == 9,
    "CANDIDATE_EXCLUDING_COUNT",
)
require(
    candidate_manifest["source_packet_human_review"]
    == "FAILED_MANIFEST_SCOPE",
    "CANDIDATE_SOURCE_REVIEW_STATE",
)
require(candidate_manifest["candidate_count_preserved"] is True, "CANDIDATE_PRESERVED")
require(candidate_manifest["snapshot_count_preserved"] is True, "SNAPSHOT_PRESERVED")
for key in (
    "evidence_registration_executed",
    "evidence_seal_executed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
):
    require(candidate_manifest[key] is False, f"CANDIDATE_FALSE:{key}")
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

# Snapshot manifest is unchanged from source R3.
source_snapshot_manifest_path = (
    source_root
    / "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json"
)
new_snapshot_manifest_path = (
    candidate_root / "r2-r8-r3-snapshot-manifest.json"
)
require(
    source_snapshot_manifest_path.read_bytes()
    == new_snapshot_manifest_path.read_bytes(),
    "SNAPSHOT_MANIFEST_BYTE_IDENTITY",
)
require(
    sha256(new_snapshot_manifest_path) == R1_FIXED_SHA[
        "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json"
    ],
    "SNAPSHOT_MANIFEST_FIXED_SHA",
)

snapshot_manifest = load_json(new_snapshot_manifest_path)
require(snapshot_manifest["phase"] == SOURCE_PHASE, "SNAPSHOT_MANIFEST_PHASE")
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
    "SNAPSHOT_MANIFEST_DIR_COUNT",
)
require(
    snapshot_manifest["snapshot_byte_equivalence"] == "PASS",
    "SNAPSHOT_MANIFEST_BYTE_EQUIVALENCE",
)
require(
    snapshot_manifest["snapshot_size_equivalence"] == "PASS",
    "SNAPSHOT_MANIFEST_SIZE_EQUIVALENCE",
)
require(
    snapshot_manifest["snapshot_sha256_equivalence"] == "PASS",
    "SNAPSHOT_MANIFEST_SHA_EQUIVALENCE",
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
    new_copy = snapshot_root / relative
    source_copy = (
        source_root
        / "packet-snapshot/registration-input-snapshot"
        / relative
    )
    new_state = require_regular_nonsymlink(new_copy, f"NEW_SNAPSHOT:{relative}")
    source_state = require_regular_nonsymlink(
        source_copy,
        f"SOURCE_SNAPSHOT:{relative}",
    )
    require(sha256(new_copy) == item["sha256"], f"NEW_SNAPSHOT_SHA:{relative}")
    require(
        sha256(source_copy) == item["sha256"],
        f"SOURCE_SNAPSHOT_SHA:{relative}",
    )
    require(
        new_copy.read_bytes() == source_copy.read_bytes(),
        f"SNAPSHOT_BYTE_PRESERVATION:{relative}",
    )
    require(
        new_state.st_size == item["size_bytes"],
        f"NEW_SNAPSHOT_SIZE:{relative}",
    )
    require(
        source_state.st_size == item["size_bytes"],
        f"SOURCE_SNAPSHOT_SIZE:{relative}",
    )
    require(
        item["source_mode"].isdigit() and len(item["source_mode"]) == 4,
        f"SNAPSHOT_SOURCE_MODE_FIELD:{relative}",
    )
    require(isinstance(item["source_uid"], int), f"SNAPSHOT_SOURCE_UID:{relative}")
    require(isinstance(item["source_gid"], int), f"SNAPSHOT_SOURCE_GID:{relative}")
    require(bool(item["source_owner"]), f"SNAPSHOT_SOURCE_OWNER:{relative}")
    require(bool(item["source_group"]), f"SNAPSHOT_SOURCE_GROUP:{relative}")

# Specific Snapshot content bindings.
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

# Corrected Packet manifest.
packet_manifest = load_json(packet_root / "packet-manifest.json")
require(packet_manifest["phase"] == PHASE, "PACKET_PHASE")
require(packet_manifest["source_phase"] == SOURCE_PHASE, "PACKET_SOURCE_PHASE")
require(
    packet_manifest["status"]
    == (
        "NESTED_MANIFEST_BASENAME_EXCLUSION_CORRECTION_"
        "PACKET_PREPARED_NO_EXECUTION"
    ),
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
    packet_manifest["source_packet_human_review"] == "FAILED_MANIFEST_SCOPE",
    "PACKET_SOURCE_REVIEW_STATE",
)
require(
    packet_manifest["nested_packet_manifest_included"] is True,
    "PACKET_NESTED_PACKET_MARKER",
)
require(
    packet_manifest["nested_evidence_manifest_expected"] is True,
    "PACKET_NESTED_EVIDENCE_EXPECTED",
)
require(
    packet_manifest["root_packet_manifest_only_excluded"] is True,
    "PACKET_ROOT_ONLY_EXCLUSION",
)
for key in (
    "evidence_registration_executed",
    "evidence_seal_executed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
):
    require(packet_manifest[key] is False, f"PACKET_FALSE:{key}")
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
require(packet_declared == packet_actual_excluding_root, "PACKET_MANIFEST_EXACT_SET")
require(NESTED_PACKET_MANIFEST in packet_declared, "NESTED_PACKET_NOT_INCLUDED")
require("packet-manifest.json" not in packet_declared, "ROOT_PACKET_NOT_EXCLUDED")
for item in packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(sha256(path) == item["sha256"], f"PACKET_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"PACKET_SIZE:{item['name']}",
    )

# Corrected Evidence manifest.
evidence_manifest = parse_evidence_manifest(r1_root / "evidence-manifest.txt")
evidence_actual_excluding_root = EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"}
require(len(evidence_manifest) == 35, "EVIDENCE_MANIFEST_ENTRY_COUNT")
require(
    set(evidence_manifest) == evidence_actual_excluding_root,
    "EVIDENCE_MANIFEST_EXACT_SET",
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
        sha256(r1_root / relative) == digest,
        f"EVIDENCE_MANIFEST_SHA:{relative}",
    )

# Correction record.
correction = load_json(candidate_root / "r2-r8-r3-result-record.json")
require(correction["phase"] == PHASE, "CORRECTION_PHASE")
require(correction["source_phase"] == SOURCE_PHASE, "CORRECTION_SOURCE_PHASE")
require(
    correction["record_type"]
    == "NESTED_MANIFEST_BASENAME_EXCLUSION_CORRECTION",
    "CORRECTION_RECORD_TYPE",
)
require(
    correction["source_packet_human_review"] == "FAILED_MANIFEST_SCOPE",
    "CORRECTION_SOURCE_REVIEW",
)
require(correction["source_packet_file_count_field"] == 32, "CORRECTION_SOURCE_COUNT")
require(
    correction["source_packet_manifest_list_length"] == 32,
    "CORRECTION_SOURCE_LIST_LENGTH",
)
require(
    correction["source_packet_actual_file_count_excluding_manifest"] == 33,
    "CORRECTION_SOURCE_ACTUAL_COUNT",
)
require(
    correction["source_packet_actual_unique_file_count"] == 33,
    "CORRECTION_SOURCE_UNIQUE_COUNT",
)
require(correction["source_packet_symlink_count"] == 0, "CORRECTION_SOURCE_LINKS")
require(
    correction["source_packet_nonregular_count"] == 0,
    "CORRECTION_SOURCE_NONREGULAR",
)
require(
    correction["source_packet_missing_declared_file"] == NESTED_PACKET_MANIFEST,
    "CORRECTION_MISSING_PACKET_PATH",
)
require(
    correction["source_evidence_missing_declared_file"]
    == NESTED_EVIDENCE_MANIFEST,
    "CORRECTION_MISSING_EVIDENCE_PATH",
)
require(
    correction["root_cause"] == "BASENAME_ONLY_MANIFEST_EXCLUSION",
    "CORRECTION_ROOT_CAUSE",
)
require(
    correction["correct_packet_exclusion"]
    == "PACKET_ROOT_RELATIVE_PATH_EQUALS_PACKET_MANIFEST_JSON",
    "CORRECTION_PACKET_CONTRACT",
)
require(
    correction["correct_evidence_exclusion"]
    == "EVIDENCE_ROOT_RELATIVE_PATH_EQUALS_EVIDENCE_MANIFEST_TXT",
    "CORRECTION_EVIDENCE_CONTRACT",
)
require(
    correction["nested_same_basename_files_included"] is True,
    "CORRECTION_NESTED_POLICY",
)
require(
    correction["corrected_packet_manifest_entry_count"] == 33,
    "CORRECTION_PACKET_COUNT",
)
require(
    correction["corrected_evidence_manifest_entry_count"] == 35,
    "CORRECTION_EVIDENCE_COUNT",
)
require(correction["candidate_artifact_count"] == 10, "CORRECTION_CANDIDATE_COUNT")
require(correction["snapshot_file_count"] == 19, "CORRECTION_SNAPSHOT_COUNT")
require(correction["snapshot_directory_count"] == 7, "CORRECTION_SNAPSHOT_DIR_COUNT")
require(
    correction["root_readonly_verification_result"] == "ABSENT_CONFIRMED",
    "CORRECTION_ROOT_RESULT",
)
require(
    correction["root_readonly_verification_execution_attempt_count"] == 1,
    "CORRECTION_ATTEMPT_COUNT",
)
require(
    correction["root_readonly_verification_max_executions"] == 1,
    "CORRECTION_MAX_EXECUTIONS",
)
require(
    correction["wrapper_exit_code_persisted_evidence_available"] is False,
    "CORRECTION_WRAPPER_PERSISTED",
)
require(
    correction["wrapper_exit_code_user_provided_console_transcript"] == 0,
    "CORRECTION_WRAPPER_TRANSCRIPT",
)
require(
    correction["human_review_qualifier"]
    == "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER",
    "CORRECTION_HUMAN_REVIEW_QUALIFIER",
)
require(correction["packet_preparation_only"] is True, "CORRECTION_PACKET_ONLY")
for key in (
    "evidence_registration_executed",
    "evidence_seal_executed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_approval_token_created",
    "approval_binding_created",
):
    require(correction[key] is False, f"CORRECTION_FALSE:{key}")
require(
    correction["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "CORRECTION_RUNNER_HOLD",
)
require(correction["writer_freeze_execution"] == "HOLD", "CORRECTION_WRITER_HOLD")
require(
    correction["production_release_decision"] == "HOLD",
    "CORRECTION_RELEASE_HOLD",
)
require(
    correction["release_status"] == "CANDIDATE_NOT_APPROVED",
    "CORRECTION_RELEASE_STATUS",
)

# Final result.
result = load_json(r1_root / "result.json")
require(result["phase"] == PHASE, "RESULT_PHASE")
require(result["source_phase"] == SOURCE_PHASE, "RESULT_SOURCE_PHASE")
require(
    result["result"]
    == (
        "PASS_W2B_I2F3E_J_R2_R8_R3_R1_NESTED_MANIFEST_"
        "BASENAME_EXCLUSION_CORRECTION_PACKET_PREPARED_NO_EXECUTION"
    ),
    "RESULT_VALUE",
)
require(result["evidence_root"] == r1_relative, "RESULT_EVIDENCE_ROOT")
require(
    result["source_packet_human_review"] == "FAILED_MANIFEST_SCOPE",
    "RESULT_SOURCE_REVIEW",
)
for key in (
    "source_result_sha_review",
    "source_packet_manifest_sha_review",
    "source_candidate_manifest_sha_review",
    "source_snapshot_manifest_sha_review",
    "source_evidence_manifest_sha_review",
):
    require(result[key] == "PASS", f"RESULT_SOURCE_SHA_PASS:{key}")
require(
    result["source_packet_manifest_entry_count"] == 32,
    "RESULT_SOURCE_PACKET_COUNT",
)
require(
    result["source_evidence_manifest_entry_count"] == 34,
    "RESULT_SOURCE_EVIDENCE_COUNT",
)
require(result["packet_manifest_entry_count"] == 33, "RESULT_PACKET_COUNT")
require(result["evidence_manifest_entry_count"] == 35, "RESULT_EVIDENCE_COUNT")
require(result["candidate_artifact_count"] == 10, "RESULT_CANDIDATE_COUNT")
require(result["snapshot_file_count"] == 19, "RESULT_SNAPSHOT_COUNT")
require(result["snapshot_directory_count"] == 7, "RESULT_SNAPSHOT_DIR_COUNT")
require(result["negative_test_count"] == 18, "RESULT_NEGATIVE_COUNT")
require(result["validator"] == "PASS", "RESULT_VALIDATOR")
require(result["negative_tests"] == "PASS", "RESULT_NEGATIVE_TESTS")
for key in (
    "packet_preparation_only",
    "source_evidence_unchanged",
    "candidate_count_preserved",
    "snapshot_count_preserved",
    "nested_packet_manifest_included",
    "nested_evidence_manifest_included",
    "root_packet_manifest_only_excluded",
    "root_evidence_manifest_only_excluded",
    "protected_sha_unchanged",
):
    require(result[key] is True, f"RESULT_TRUE:{key}")
require(
    result["root_readonly_verification_result"] == "ABSENT_CONFIRMED",
    "RESULT_ROOT_VALUE",
)
for key in (
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
    "evidence_registration_executed",
    "evidence_seal_executed",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_approval_token_created",
    "approval_binding_created",
):
    require(result[key] is False, f"RESULT_FALSE:{key}")
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
    == (
        "HUMAN_REVIEW_3E_J_R2_R8_R3_R1_NESTED_MANIFEST_"
        "BASENAME_EXCLUSION_CORRECTION_PACKET"
    ),
    "RESULT_NEXT_GATE",
)

# Preserved policies and blocked entrypoint.
registration_policy = load_json(
    candidate_root / "r2-r8-r3-registration-policy.json"
)
source_contract = load_json(candidate_root / "r2-r8-r3-source-contract.json")
seal_contract = load_json(candidate_root / "r2-r8-r3-seal-contract.json")
require(
    registration_policy["evidence_registration_executed"] is False,
    "POLICY_REGISTRATION_STATE",
)
require(
    registration_policy["evidence_seal_executed"] is False,
    "POLICY_SEAL_STATE",
)
require(
    registration_policy["root_readonly_verification_reexecution_allowed"]
    is False,
    "POLICY_REEXECUTION",
)
require(
    registration_policy["one_shot_guard_change_allowed"] is False,
    "POLICY_GUARD_CHANGE",
)
require(
    source_contract["root_verification_reexecution_allowed"] is False,
    "SOURCE_CONTRACT_REEXECUTION",
)
require(
    source_contract["one_shot_guard_change_allowed"] is False,
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
    seal_contract["seal_execution_status"] == "NOT_EXECUTED",
    "SEAL_STATUS",
)
require(
    seal_contract["seal_execution_allowed_in_current_phase"] is False,
    "SEAL_CURRENT_PHASE",
)
require(
    seal_contract["future_execution_requires_new_explicit_human_approval"]
    is True,
    "SEAL_APPROVAL_GATE",
)
require(
    seal_contract["automatic_production_deployment_after_seal"] is False,
    "SEAL_AUTO_DEPLOY",
)
require(
    seal_contract["production_release_decision"] == "HOLD",
    "SEAL_RELEASE_HOLD",
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

# Static validation logs and source code review.
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
    "VALIDATOR_STATIC_LOG_CONTENT",
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
    "NEGATIVE_STATIC_LOG_CONTENT",
)

validator_source = (
    candidate_root / "validate_r2_r8_r3_packet.py"
).read_text(encoding="utf-8")
negative_source = (
    candidate_root / "test_r2_r8_r3_packet_negative.py"
).read_text(encoding="utf-8")
manual = (
    candidate_root / "r2-r8-r3-operation-manual.md"
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

test_names = re.findall(
    r"^    def (test_[A-Za-z0-9_]+)\(self\) -> None:$",
    negative_source,
    flags=re.MULTILINE,
)
require(len(test_names) == 18, "NEGATIVE_TEST_METHOD_COUNT")
require(len(set(test_names)) == 18, "NEGATIVE_TEST_METHOD_UNIQUENESS")
for required_test in (
    "test_valid_packet_passes",
    "test_nested_packet_manifest_missing_from_packet_manifest_rejected",
    "test_nested_evidence_manifest_missing_rejected",
    "test_root_packet_manifest_declared_rejected",
    "test_root_evidence_manifest_declared_rejected",
    "test_packet_count_32_rejected",
    "test_packet_list_length_32_rejected",
    "test_evidence_manifest_length_34_rejected",
    "test_nested_packet_content_change_rejected",
    "test_nested_evidence_content_change_rejected",
):
    require(required_test in test_names, f"NEGATIVE_REQUIRED_TEST:{required_test}")

for marker in (
    "NESTED_PACKET_MANIFEST_INCLUDED=true",
    "NESTED_EVIDENCE_MANIFEST_INCLUDED=true",
    "ROOT_PACKET_MANIFEST_ONLY_EXCLUDED=true",
    "ROOT_EVIDENCE_MANIFEST_ONLY_EXCLUDED=true",
):
    require(marker in validator_source, f"VALIDATOR_OUTPUT_MARKER:{marker}")

for manual_marker in (
    "FAILED_MANIFEST_SCOPE",
    "Packet manifest entries: 33",
    "Evidence manifest entries: 35",
    "Candidate artifacts: 10",
    "Snapshot files: 19",
    "Packet preparation only: `true`",
    "Evidence registration executed: `false`",
    "Evidence seal executed: `false`",
    "Production release: `HOLD`",
):
    require(manual_marker in manual, f"MANUAL_MARKER:{manual_marker}")

approval_text = (
    packet_root / "human-approval-verbatim.txt"
).read_text(encoding="utf-8")
for marker in (
    "APPROVE_3E_J_R2_R8_R3_R1_NESTED_MANIFEST_BASENAME_EXCLUSION_CORRECTION_PACKET_PREPARATION_NO_EXECUTION",
    "R2_R8_R3_PACKET_HUMAN_REVIEW=FAILED_MANIFEST_SCOPE",
    "PACKET_FILE_COUNT_FIELD=32",
    "PACKET_MANIFEST_LIST_LENGTH=32",
    "PACKET_ACTUAL_FILE_COUNT_EXCLUDING_MANIFEST=33",
    "R2_R8_R3_R1_PACKET_PREPARATION_ONLY=true",
    "R2_R8_R3_R1_EVIDENCE_REGISTRATION_EXECUTED=false",
    "R2_R8_R3_R1_EVIDENCE_SEAL_EXECUTED=false",
    "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false",
    "ONE_SHOT_GUARD_CHANGE_ALLOWED=false",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "RELEASE_STATUS=CANDIDATE_NOT_APPROVED",
):
    require(marker in approval_text, f"APPROVAL_MARKER:{marker}")

# Protected identities before runtime read-only validation.
for relative, expected in PROTECTED_SHA.items():
    path = repo_root / relative
    require_regular_nonsymlink(path, f"PROTECTED:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

# Execute candidate validator read-only.
validator_path = candidate_root / "validate_r2_r8_r3_packet.py"
validator_run = subprocess.run(
    [
        str(repo_root / ".venv/bin/python"),
        "-B",
        str(validator_path),
        str(r1_root),
    ],
    cwd=candidate_root,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
    },
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
validator_output = validator_run.stdout.decode("utf-8")
require(
    validator_run.returncode == 0,
    "RUNTIME_VALIDATOR_NONZERO\n" + validator_output,
)
required_validator_lines = {
    "VALIDATION=PASS",
    "EVIDENCE_FILE_COUNT=36",
    "EVIDENCE_DIRECTORY_COUNT=11",
    "PACKET_FILE_COUNT=34",
    "PACKET_DIRECTORY_COUNT=10",
    "PACKET_MANIFEST_ENTRY_COUNT=33",
    "EVIDENCE_MANIFEST_ENTRY_COUNT=35",
    "CANDIDATE_ARTIFACT_COUNT=10",
    "SNAPSHOT_FILE_COUNT=19",
    "SNAPSHOT_DIRECTORY_COUNT=7",
    "NESTED_PACKET_MANIFEST_INCLUDED=true",
    "NESTED_EVIDENCE_MANIFEST_INCLUDED=true",
    "ROOT_PACKET_MANIFEST_ONLY_EXCLUDED=true",
    "ROOT_EVIDENCE_MANIFEST_ONLY_EXCLUDED=true",
    "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false",
    "EVIDENCE_REGISTRATION_EXECUTED=false",
    "EVIDENCE_SEAL_EXECUTED=false",
    "PRODUCTION_RELEASE_DECISION=HOLD",
}
validator_output_lines = {
    line.strip() for line in validator_output.splitlines() if line.strip()
}
require(
    required_validator_lines <= validator_output_lines,
    "RUNTIME_VALIDATOR_MARKERS",
)

# Execute 18 negative tests on isolated temporary copies only.
negative_path = candidate_root / "test_r2_r8_r3_packet_negative.py"
negative_run = subprocess.run(
    [
        str(repo_root / ".venv/bin/python"),
        "-B",
        str(negative_path),
    ],
    cwd=candidate_root,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
    },
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
negative_output = negative_run.stdout.decode("utf-8")
require(
    negative_run.returncode == 0,
    "RUNTIME_NEGATIVE_NONZERO\n" + negative_output,
)
require("Ran 18 tests" in negative_output, "RUNTIME_NEGATIVE_TEST_COUNT")
negative_output_lines = [
    line.strip() for line in negative_output.splitlines()
]
require(negative_output_lines.count("OK") == 1, "RUNTIME_NEGATIVE_OK_COUNT")
require("FAILED" not in negative_output, "RUNTIME_NEGATIVE_FAILED")
require("Traceback" not in negative_output, "RUNTIME_NEGATIVE_TRACEBACK")
require("ERROR:" not in negative_output, "RUNTIME_NEGATIVE_ERROR")

# Full source trees must remain byte-for-byte and metadata unchanged.
source_identity_after = tree_identity(source_root)
r1_identity_after = tree_identity(r1_root)
require(
    source_identity_after == source_identity_before,
    "SOURCE_R3_EVIDENCE_CHANGED_DURING_REVIEW",
)
require(
    r1_identity_after == r1_identity_before,
    "R3_R1_EVIDENCE_CHANGED_DURING_REVIEW",
)
require(not list(source_root.rglob("*.pyc")), "SOURCE_BYTECODE_SIDE_EFFECT")
require(not list(r1_root.rglob("*.pyc")), "R1_BYTECODE_SIDE_EFFECT")

# Protected identities after runtime read-only validation.
for relative, expected in PROTECTED_SHA.items():
    require(
        sha256(repo_root / relative) == expected,
        f"PROTECTED_CHANGED:{relative}",
    )

print("R2_R8_R3_R1_RESULT_SHA_REVIEW=PASS")
print("R2_R8_R3_R1_PACKET_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_R1_CANDIDATE_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_R1_SNAPSHOT_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R3_R1_EVIDENCE_MANIFEST_SHA_REVIEW=PASS")
print("SOURCE_R3_FIXED_SHA_REVIEW=PASS")
print("SOURCE_R3_EVIDENCE_UNCHANGED=true")
print("SOURCE_R3_PACKET_HUMAN_REVIEW=FAILED_MANIFEST_SCOPE")
print("SOURCE_R3_PACKET_MANIFEST_ENTRY_COUNT=32")
print("SOURCE_R3_EVIDENCE_MANIFEST_ENTRY_COUNT=34")
print("SOURCE_R3_NESTED_PACKET_MANIFEST_MISSING_CONFIRMED=true")
print("SOURCE_R3_NESTED_EVIDENCE_MANIFEST_MISSING_CONFIRMED=true")
print("R2_R8_R3_R1_EVIDENCE_FILE_COUNT=36")
print("R2_R8_R3_R1_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=11")
print(f"R2_R8_R3_R1_EVIDENCE_FILE_MODE_DISTRIBUTION={dict(sorted(file_modes.items()))}")
print(
    "R2_R8_R3_R1_EVIDENCE_DIRECTORY_MODE_DISTRIBUTION="
    f"{dict(sorted(directory_modes.items()))}"
)
print("R2_R8_R3_R1_EVIDENCE_SYMLINK_COUNT=0")
print("R2_R8_R3_R1_EVIDENCE_NONREGULAR_COUNT=0")
print("R2_R8_R3_R1_EVIDENCE_OWNER_GROUP_REVIEW=PASS")
print("R2_R8_R3_R1_EVIDENCE_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_R1_PACKET_FILE_COUNT=34")
print("R2_R8_R3_R1_PACKET_DIRECTORY_COUNT=10")
print("R2_R8_R3_R1_PACKET_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_R1_PACKET_MANIFEST_ENTRY_COUNT=33")
print("R2_R8_R3_R1_PACKET_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R8_R3_R1_EVIDENCE_MANIFEST_ENTRY_COUNT=35")
print("R2_R8_R3_R1_EVIDENCE_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R8_R3_R1_NESTED_PACKET_MANIFEST_INCLUDED=true")
print("R2_R8_R3_R1_NESTED_EVIDENCE_MANIFEST_INCLUDED=true")
print("R2_R8_R3_R1_ROOT_PACKET_MANIFEST_ONLY_EXCLUDED=true")
print("R2_R8_R3_R1_ROOT_EVIDENCE_MANIFEST_ONLY_EXCLUDED=true")
print("R2_R8_R3_R1_CANDIDATE_ARTIFACT_COUNT=10")
print("R2_R8_R3_R1_CANDIDATE_DIRECTORY_COUNT=0")
print("R2_R8_R3_R1_CANDIDATE_PYC_FILE_COUNT=0")
print("R2_R8_R3_R1_CANDIDATE_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_R1_CANDIDATE_ARTIFACT_SHA_SIZE_REVIEW=PASS")
print("R2_R8_R3_R1_SNAPSHOT_FILE_COUNT=19")
print("R2_R8_R3_R1_SNAPSHOT_DIRECTORY_COUNT=7")
print("R2_R8_R3_R1_SNAPSHOT_MANIFEST_UNCHANGED=true")
print("R2_R8_R3_R1_SNAPSHOT_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R3_R1_SNAPSHOT_SHA_SIZE_REVIEW=PASS")
print("R2_R8_R3_R1_SNAPSHOT_BYTE_PRESERVATION_REVIEW=PASS")
print("R2_R8_R3_R1_SOURCE_NEW_UNCHANGED_FILE_COUNT=24")
print("R2_R8_R3_R1_SOURCE_NEW_UNCHANGED_FILE_REVIEW=PASS")
print("ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED")
print("ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1")
print("ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("R2_R8_R3_R1_VERIFIER_EXIT_CODE=0")
print(
    "R2_R8_R3_R1_WRAPPER_EXIT_CODE_QUALIFIER="
    "PASS_WITH_WRAPPER_EXIT_CODE_TRANSCRIPT_QUALIFIER"
)
print("R2_R8_R3_R1_CORRECTION_RESULT_RECORD_REVIEW=PASS")
print("R2_R8_R3_R1_REGISTRATION_POLICY_REVIEW=PASS")
print("R2_R8_R3_R1_SOURCE_CONTRACT_REVIEW=PASS")
print("R2_R8_R3_R1_SEAL_CONTRACT_REVIEW=PASS")
print("R2_R8_R3_R1_BLOCKED_ENTRYPOINT_STATIC_REVIEW=PASS")
print("R2_R8_R3_R1_OPERATION_MANUAL_REVIEW=PASS")
print("R2_R8_R3_R1_VALIDATOR_SOURCE_COMPILE_REVIEW=PASS")
print("R2_R8_R3_R1_NEGATIVE_TEST_SOURCE_COMPILE_REVIEW=PASS")
print("R2_R8_R3_R1_NEGATIVE_TEST_METHOD_COUNT=18")
print("R2_R8_R3_R1_RUNTIME_VALIDATOR_EXECUTED_READONLY=true")
print("R2_R8_R3_R1_RUNTIME_VALIDATOR=PASS")
print("R2_R8_R3_R1_RUNTIME_NEGATIVE_TESTS_EXECUTED_ON_TEMP_COPY=true")
print("R2_R8_R3_R1_RUNTIME_NEGATIVE_TEST_COUNT=18")
print("R2_R8_R3_R1_RUNTIME_NEGATIVE_TESTS=PASS")
print("R2_R8_R3_R1_PERSISTED_VALIDATION_LOGS_STATIC_ONLY=true")
print("R2_R8_R3_R1_RUNTIME_VALIDATION_OUTPUT_PERSISTED=false")
print("R2_R8_R3_R1_SOURCE_EVIDENCE_MUTATION=false")
print("R2_R8_R3_R1_EVIDENCE_MUTATION=false")
print("R2_R8_R3_R1_BYTECODE_SIDE_EFFECT=false")
print("PROTECTED_SHA_REVIEW=PASS")
print("R2_R8_R3_R1_PACKET_PREPARATION_ONLY=true")
print("R2_R8_R3_R1_EVIDENCE_REGISTRATION_EXECUTED=false")
print("R2_R8_R3_R1_EVIDENCE_SEAL_EXECUTED=false")
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
    "R2_R8_R3_R1_PACKET_HUMAN_REVIEW_DECISION="
    "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD"
)
print(
    "NEXT_GATE="
    "HUMAN_APPROVAL_FOR_3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
    "REGISTRATION_AND_SEAL_EXECUTION"
)
PY

printf '\n===== FINAL R3-R1 HUMAN REVIEW MARKERS =====\n'

echo "R2_R8_R3_R1_PACKET_HUMAN_REVIEW=PASS"
echo "R2_R8_R3_R1_PACKET_HUMAN_REVIEW_DECISION=APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD"
echo "SOURCE_R3_EVIDENCE_UNCHANGED=true"
echo "SOURCE_R3_PACKET_HUMAN_REVIEW=FAILED_MANIFEST_SCOPE"
echo "R2_R8_R3_R1_PACKET_MANIFEST_ENTRY_COUNT=33"
echo "R2_R8_R3_R1_EVIDENCE_MANIFEST_ENTRY_COUNT=35"
echo "R2_R8_R3_R1_NESTED_PACKET_MANIFEST_INCLUDED=true"
echo "R2_R8_R3_R1_NESTED_EVIDENCE_MANIFEST_INCLUDED=true"
echo "R2_R8_R3_R1_ROOT_PACKET_MANIFEST_ONLY_EXCLUDED=true"
echo "R2_R8_R3_R1_ROOT_EVIDENCE_MANIFEST_ONLY_EXCLUDED=true"
echo "R2_R8_R3_R1_RUNTIME_VALIDATOR=PASS"
echo "R2_R8_R3_R1_RUNTIME_NEGATIVE_TEST_COUNT=18"
echo "R2_R8_R3_R1_RUNTIME_NEGATIVE_TESTS=PASS"
echo "R2_R8_R3_R1_SOURCE_EVIDENCE_MUTATION=false"
echo "R2_R8_R3_R1_EVIDENCE_MUTATION=false"
echo "R2_R8_R3_R1_BYTECODE_SIDE_EFFECT=false"
echo "R2_R8_R3_R1_EVIDENCE_REGISTRATION_EXECUTED=false"
echo "R2_R8_R3_R1_EVIDENCE_SEAL_EXECUTED=false"
echo "ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false"
echo "ONE_SHOT_GUARD_CHANGE_ALLOWED=false"
echo "SUDOERS_CHANGED=false"
echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
echo "WRITER_FREEZE_EXECUTION=HOLD"
echo "PRODUCTION_RELEASE_DECISION=HOLD"
echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
echo "NEXT_GATE=HUMAN_APPROVAL_FOR_3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_REGISTRATION_AND_SEAL_EXECUTION"
echo "REVIEW_COMMAND_EXIT_CODE=0"
