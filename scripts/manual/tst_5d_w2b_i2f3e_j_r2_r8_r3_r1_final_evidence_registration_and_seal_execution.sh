#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
SOURCE_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-r1-nested-manifest-basename-exclusion-correction-packet-preparation-20260726T032952Z-526992"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"

FINAL_PREFIX="i2f3e-j-r2-r8-r3-r1-final-evidence-registration-and-seal"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
FINAL_REL="${BASE_REL}/${FINAL_PREFIX}-${RUN_ID}"
FINAL_ROOT="${REPO_ROOT}/${FINAL_REL}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$SOURCE_ROOT"

cd "$REPO_ROOT"

printf '\n===== APPROVED R3-R1 SOURCE FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
8129fdce8ce1c1767a261523f16a63ca56c867ef635829c8c1e6ef5bd8953d56  ${SOURCE_ROOT}/result.json
0220b3bea10a53cff6a1c7a1cc19527bf7a827921ba856662aff80336c8b47b6  ${SOURCE_ROOT}/packet-snapshot/packet-manifest.json
eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json
2c572560f375b369eae22f71460c531cc298190a69309e93cb7b86ab7e7eab89  ${SOURCE_ROOT}/evidence-manifest.txt
SHAS

mkdir "$FINAL_ROOT"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$SOURCE_ROOT" \
  "$FINAL_ROOT" \
  "$SOURCE_REL" \
  "$FINAL_REL" \
  "$FINAL_PREFIX" <<'PY'
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
source_root = Path(sys.argv[2]).resolve(strict=True)
final_root = Path(sys.argv[3]).resolve(strict=True)
source_relative = sys.argv[4]
final_relative = sys.argv[5]
final_prefix = sys.argv[6]

packet_root = final_root / "packet-snapshot"
candidate_root = packet_root / "candidate-artifacts"
snapshot_root = packet_root / "registration-input-snapshot"
log_root = packet_root / "validation-logs"

PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3-R1-FINAL-SEAL"
SOURCE_PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R3-R1"
TARGET = "/etc/sudoers.d/ai-media-os-3e-j-root-helper"

approval_text = base64.b64decode(
    "QVBQUk9WRV8zRV9KX1IyX1I4X1IzX1IxX0ZJTkFMX0VWSURFTkNFX1JFR0lTVFJBVElPTl9BTkRfU0VBTF9FWEVDVVRJT04KClIyX1I4X1IzX1IxX1BBQ0tFVF9IVU1BTl9SRVZJRVc9UEFTUwpSMl9SOF9SM19SMV9QQUNLRVRfSFVNQU5fUkVWSUVXX0RFQ0lTSU9OPQpBUFBST1ZFX05FU1RFRF9NQU5JRkVTVF9DT1JSRUNUSU9OX1BBQ0tFVF9XSVRIX0VYRUNVVElPTl9IT0xECgrlr77osaFQYWNrZXQgRXZpZGVuY2XvvJoKCmV4Y2hhbmdlL3Jldmlld19ldmlkZW5jZS9zbGFja193b3JrZXJfcmVsZWFzZV9yZWJpbmRpbmcvCnNsYWNrLXdvcmtlci1DQU5ESURBVEUtTk9ULUFQUFJPVkVELTAxYmE4ODA5ZjEzMy8KdHN0LTVkLXcyYi1pMmUtYmFzZWxpbmUtYWJzb3JwdGlvbi1yZXJldmlldy0yMDI2MDcyNVQxNDE2MzIvCmkyZjNlLWotcjItcjgtcjMtcjEtbmVzdGVkLW1hbmlmZXN0LWJhc2VuYW1lLWV4Y2x1c2lvbi0KY29ycmVjdGlvbi1wYWNrZXQtcHJlcGFyYXRpb24tMjAyNjA3MjZUMDMyOTUyWi01MjY5OTIKCuWbuuWumlNIQe+8mgoKUkVTVUxUX1NIQT0KODEyOWZkY2U4Y2UxYzE3NjdhMjYxNTIzZjE2YTYzY2E1NmM4NjdlZjYzNTgyOWM4YzFlNmVmNWJkODk1M2Q1NgoKUEFDS0VUX01BTklGRVNUX1NIQT0KMDIyMGIzYmVhMTBhNTNjZmY2YTFjN2ExY2MxOTUyN2JmN2E4Mjc5MjFiYTg1NjY2MmFmZjgwMzM2YzhiNDdiNgoKQ0FORElEQVRFX01BTklGRVNUX1NIQT0KZWVmNDFkMDc1MzA5YWJhNTJmMDdmNmQ4ZDRkNjJhMmYxMmYwZDc0YmRhMDFlMzUzYmU5NjlhZjliZTVhOGUwZgoKU05BUFNIT1RfTUFOSUZFU1RfU0hBPQphZmFhMTg5ZmI2ZDk1NjVhZGUyYTU4MjY0NDljYzg1OWY2NWYwMzU4OTQ2ZGVhZTIxYWFlNDcwM2Y0MTQ2MzFjCgpFVklERU5DRV9NQU5JRkVTVF9TSEE9CjJjNTcyNTYwZjM3NWIzNjllYWUyMmY3MTQ2MGM1MzFjYzI5ODE5MGE2OTMwOWU5M2NiN2I4NmFiN2U3ZWFiODkKCkZJTkFMX0VWSURFTkNFX1JFR0lTVFJBVElPTl9FWEVDVVRJT05fQUxMT1dFRD10cnVlCkZJTkFMX0VWSURFTkNFX1NFQUxfRVhFQ1VUSU9OX0FMTE9XRUQ9dHJ1ZQoKUk9PVF9SRUFET05MWV9WRVJJRklDQVRJT05fUkVFWEVDVVRJT05fQUxMT1dFRD1mYWxzZQpPTkVfU0hPVF9HVUFSRF9DSEFOR0VfQUxMT1dFRD1mYWxzZQpTVURPRVJTX0NIQU5HRUQ9ZmFsc2UKQVVUT01BVElDX0RFUExPWU1FTlRfUEVSRk9STUVEPWZhbHNlCkNBTkRJREFURV9ERVBMT1lFRF9UT19QUk9EVUNUSU9OPWZhbHNlCgpSVU5ORVJfU1RBVFVTPUJMT0NLRURfVU5USUxfRVhQTElDSVRfRklOQUxfRVhFQ1VUSU9OX0FQUFJPVkFMCldSSVRFUl9GUkVFWkVfRVhFQ1VUSU9OPUhPTEQKUFJPRFVDVElPTl9SRUxFQVNFX0RFQ0lTSU9OPUhPTEQKUkVMRUFTRV9TVEFUVVM9Q0FORElEQVRFX05PVF9BUFBST1ZFRAo=",
    validate=True,
).decode("utf-8")

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

def write_exclusive(path: Path, data: bytes, mode: int = 0o640) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
    )
    with os.fdopen(descriptor, "wb", closefd=True) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def mkdir_exclusive(path: Path, mode: int = 0o750) -> None:
    os.mkdir(path, mode)

def copy_exclusive(source: Path, destination: Path) -> None:
    require_regular_nonsymlink(source, f"COPY_SOURCE:{source}")
    write_exclusive(destination, source.read_bytes())

def parse_evidence_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        require(relative not in entries, f"MANIFEST_DUPLICATE:{relative}")
        require(len(digest) == 64, f"MANIFEST_DIGEST_LENGTH:{relative}")
        entries[relative] = digest
    return entries

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

# Bind paths.
require(
    source_root.relative_to(repo_root).as_posix() == source_relative,
    "SOURCE_ROOT_BINDING",
)
require(
    final_root.relative_to(repo_root).as_posix() == final_relative,
    "FINAL_ROOT_BINDING",
)
require(
    final_root.name.startswith(final_prefix + "-"),
    "FINAL_ROOT_PREFIX_BINDING",
)
require(final_root.parent == source_root.parent, "FINAL_ROOT_PARENT_BINDING")

# One-shot final root prefix: current just-created root must be the only match.
matching_final_roots = sorted(
    path
    for path in final_root.parent.glob(final_prefix + "-*")
    if path.is_dir()
)
require(
    matching_final_roots == [final_root],
    "FINAL_EXECUTION_ALREADY_EXISTS_OR_DUPLICATE",
)

# Source fixed SHA and exact approved structure.
for relative, expected in SOURCE_FIXED_SHA.items():
    path = source_root / relative
    require_regular_nonsymlink(path, f"SOURCE_FIXED:{relative}")
    require(sha256(path) == expected, f"SOURCE_FIXED_SHA:{relative}")

source_files, source_dirs, source_links, source_other = scan(source_root)
require(source_files == EXPECTED_EVIDENCE_FILES, "SOURCE_EXACT_FILE_SET")
require(source_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "SOURCE_EXACT_DIRECTORY_SET")
require(len(source_files) == 36, "SOURCE_FILE_COUNT")
require(len(source_dirs) == 11, "SOURCE_DIRECTORY_COUNT")
require(source_links == 0, "SOURCE_SYMLINK_COUNT")
require(source_other == 0, "SOURCE_NONREGULAR_COUNT")

source_identity_before = tree_identity(source_root)

source_result = load_json(source_root / "result.json")
require(source_result["phase"] == SOURCE_PHASE, "SOURCE_RESULT_PHASE")
require(
    source_result["result"]
    == (
        "PASS_W2B_I2F3E_J_R2_R8_R3_R1_NESTED_MANIFEST_"
        "BASENAME_EXCLUSION_CORRECTION_PACKET_PREPARED_NO_EXECUTION"
    ),
    "SOURCE_RESULT_VALUE",
)
require(
    source_result["source_packet_human_review"] == "FAILED_MANIFEST_SCOPE",
    "SOURCE_FAILED_REVIEW_STATE",
)
require(
    source_result["packet_manifest_entry_count"] == 33,
    "SOURCE_PACKET_MANIFEST_COUNT",
)
require(
    source_result["evidence_manifest_entry_count"] == 35,
    "SOURCE_EVIDENCE_MANIFEST_COUNT",
)
require(source_result["candidate_artifact_count"] == 10, "SOURCE_CANDIDATE_COUNT")
require(source_result["snapshot_file_count"] == 19, "SOURCE_SNAPSHOT_COUNT")
require(source_result["validator"] == "PASS", "SOURCE_VALIDATOR")
require(source_result["negative_tests"] == "PASS", "SOURCE_NEGATIVE_TESTS")
require(
    source_result["nested_packet_manifest_included"] is True,
    "SOURCE_NESTED_PACKET",
)
require(
    source_result["nested_evidence_manifest_included"] is True,
    "SOURCE_NESTED_EVIDENCE",
)
require(
    source_result["packet_evidence_seal_performed"] is False,
    "SOURCE_UNSEALED_STATE",
)
require(
    source_result["production_release_decision"] == "HOLD",
    "SOURCE_RELEASE_HOLD",
)

source_packet_manifest = load_json(
    source_root / "packet-snapshot/packet-manifest.json"
)
require(
    source_packet_manifest["packet_file_count_excluding_manifest"] == 33,
    "SOURCE_PACKET_ENTRY_COUNT",
)
require(
    len(source_packet_manifest["packet_files"]) == 33,
    "SOURCE_PACKET_LIST_LENGTH",
)
source_packet_declared = {
    item["name"] for item in source_packet_manifest["packet_files"]
}
require(
    source_packet_declared == EXPECTED_PACKET_FILES - {"packet-manifest.json"},
    "SOURCE_PACKET_EXACT_DECLARATION",
)
require(
    NESTED_PACKET_MANIFEST in source_packet_declared,
    "SOURCE_NESTED_PACKET_NOT_DECLARED",
)

source_evidence_manifest = parse_evidence_manifest(
    source_root / "evidence-manifest.txt"
)
require(
    len(source_evidence_manifest) == 35,
    "SOURCE_EVIDENCE_ENTRY_COUNT",
)
require(
    set(source_evidence_manifest)
    == EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"},
    "SOURCE_EVIDENCE_EXACT_DECLARATION",
)
require(
    NESTED_EVIDENCE_MANIFEST in source_evidence_manifest,
    "SOURCE_NESTED_EVIDENCE_NOT_DECLARED",
)

source_candidate_manifest = load_json(
    source_root
    / "packet-snapshot/candidate-artifacts/candidate-manifest.json"
)
require(
    source_candidate_manifest["total_file_count"] == 10,
    "SOURCE_CANDIDATE_TOTAL",
)
require(
    source_candidate_manifest["file_count_excluding_manifest"] == 9,
    "SOURCE_CANDIDATE_EXCLUDING",
)

source_snapshot_manifest = load_json(
    source_root
    / "packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json"
)
require(
    source_snapshot_manifest["snapshot_file_count"] == 19,
    "SOURCE_SNAPSHOT_MANIFEST_COUNT",
)
require(
    source_snapshot_manifest["snapshot_directory_count_excluding_root"] == 7,
    "SOURCE_SNAPSHOT_MANIFEST_DIRECTORY_COUNT",
)

# Protected identities, without DB connection or SQL.
for relative, expected in PROTECTED_SHA.items():
    path = repo_root / relative
    require_regular_nonsymlink(path, f"PROTECTED:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

# Create the exact directory structure.
for relative in sorted(EXPECTED_EVIDENCE_DIRECTORIES):
    mkdir_exclusive(final_root / relative)

# Copy approved Candidate, Snapshot, and validation logs byte-for-byte.
require(len(COPY_FROM_SOURCE) == 32, "COPY_SET_COUNT")
for relative in sorted(COPY_FROM_SOURCE):
    source = source_root / relative
    destination = final_root / relative
    copy_exclusive(source, destination)
    require(source.read_bytes() == destination.read_bytes(), f"COPY_BYTES:{relative}")
    require(sha256(source) == sha256(destination), f"COPY_SHA:{relative}")
    require(
        source.stat().st_size == destination.stat().st_size,
        f"COPY_SIZE:{relative}",
    )

# Final approval text replaces the packet-preparation approval text.
write_exclusive(
    packet_root / "human-approval-verbatim.txt",
    approval_text.encode("utf-8"),
)

# Build Final Packet manifest: exactly 33 entries, root-relative exclusion only.
packet_entries = []
for path in sorted(packet_root.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(packet_root).as_posix()
    if relative == "packet-manifest.json":
        continue
    packet_entries.append(
        {
            "name": relative,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
    )

require(len(packet_entries) == 33, "FINAL_PACKET_ENTRY_COUNT")
packet_names = {item["name"] for item in packet_entries}
require(
    packet_names == EXPECTED_PACKET_FILES - {"packet-manifest.json"},
    "FINAL_PACKET_EXACT_SET",
)
require(
    NESTED_PACKET_MANIFEST in packet_names,
    "FINAL_NESTED_PACKET_NOT_INCLUDED",
)
require(
    "packet-manifest.json" not in packet_names,
    "FINAL_ROOT_PACKET_NOT_EXCLUDED",
)

packet_manifest = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_phase": SOURCE_PHASE,
    "status": "FINAL_EVIDENCE_REGISTRATION_AND_SEAL_EXECUTED",
    "packet_file_count_excluding_manifest": 33,
    "packet_files": packet_entries,
    "candidate_artifact_count": 10,
    "snapshot_file_count": 19,
    "validation_log_count": 3,
    "source_packet_human_review": "PASS",
    "source_packet_human_review_decision": (
        "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD"
    ),
    "nested_packet_manifest_included": True,
    "nested_evidence_manifest_expected": True,
    "root_packet_manifest_only_excluded": True,
    "final_evidence_registration_executed": True,
    "final_evidence_seal_execution_authorized": True,
    "root_readonly_verification_reexecution_allowed": False,
    "one_shot_guard_change_allowed": False,
    "runner_status": "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "production_release_decision": "HOLD",
}
write_exclusive(
    packet_root / "packet-manifest.json",
    (
        json.dumps(
            packet_manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8"),
)

packet_manifest_sha = sha256(packet_root / "packet-manifest.json")
candidate_manifest_sha = sha256(candidate_root / "candidate-manifest.json")
snapshot_manifest_sha = sha256(
    candidate_root / "r2-r8-r3-snapshot-manifest.json"
)

seal_commit_timestamp = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)

# Final execution result. Script success is emitted only after post-seal validation.
result = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_phase": SOURCE_PHASE,
    "result": (
        "PASS_W2B_I2F3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
        "REGISTRATION_AND_SEAL_EXECUTED_HUMAN_REVIEW_REQUIRED"
    ),
    "evidence_root": final_relative,
    "source_evidence_root": source_relative,
    "source_packet_human_review": "PASS",
    "source_packet_human_review_decision": (
        "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD"
    ),
    "source_result_sha_review": "PASS",
    "source_packet_manifest_sha_review": "PASS",
    "source_candidate_manifest_sha_review": "PASS",
    "source_snapshot_manifest_sha_review": "PASS",
    "source_evidence_manifest_sha_review": "PASS",
    "source_evidence_unchanged": True,
    "final_evidence_registration_execution_allowed": True,
    "final_evidence_seal_execution_allowed": True,
    "final_evidence_registration_executed": True,
    "final_evidence_seal_executed": True,
    "seal_commit_timestamp_utc": seal_commit_timestamp,
    "final_evidence_file_count": 36,
    "final_evidence_directory_count_excluding_root": 11,
    "packet_file_count": 34,
    "packet_directory_count": 10,
    "packet_manifest_entry_count": 33,
    "evidence_manifest_entry_count": 35,
    "candidate_artifact_count": 10,
    "snapshot_file_count": 19,
    "snapshot_directory_count": 7,
    "validation_log_count": 3,
    "registered_source_file_count": 32,
    "registered_source_byte_equivalence": "PASS",
    "registered_source_size_equivalence": "PASS",
    "registered_source_sha256_equivalence": "PASS",
    "nested_packet_manifest_included": True,
    "nested_evidence_manifest_included": True,
    "root_packet_manifest_only_excluded": True,
    "root_evidence_manifest_only_excluded": True,
    "final_file_mode": "0444",
    "final_directory_mode": "0555",
    "final_symlink_count": 0,
    "final_nonregular_count": 0,
    "owner_group_change_performed": False,
    "root_readonly_verification_result": "ABSENT_CONFIRMED",
    "root_readonly_verification_execution_attempt_count": 1,
    "root_readonly_verification_max_executions": 1,
    "root_readonly_verification_reexecution_allowed": False,
    "one_shot_guard_change_allowed": False,
    "sudoers_changed": False,
    "automatic_deployment_performed": False,
    "candidate_deployed_to_production": False,
    "production_directory_created": False,
    "production_file_created": False,
    "production_process_signal_sent": False,
    "production_database_sql_connection_used": False,
    "production_backup_created": False,
    "migration_executed": False,
    "external_network_used": False,
    "final_production_token_created": False,
    "approval_binding_created": False,
    "protected_sha_unchanged": True,
    "packet_manifest_sha256": packet_manifest_sha,
    "candidate_manifest_sha256": candidate_manifest_sha,
    "snapshot_manifest_sha256": snapshot_manifest_sha,
    "post_seal_validation_required_before_script_success": True,
    "post_seal_human_review_required": True,
    "runner_status": "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": (
        "HUMAN_REVIEW_3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
        "REGISTRATION_AND_SEAL_RESULT_READONLY"
    ),
}
write_exclusive(
    final_root / "result.json",
    (
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8"),
)

# Final Evidence manifest: exactly 35 entries, root-relative exclusion only.
evidence_lines = []
for path in sorted(final_root.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(final_root).as_posix()
    if relative == "evidence-manifest.txt":
        continue
    evidence_lines.append(f"{sha256(path)}  {relative}")

require(len(evidence_lines) == 35, "FINAL_EVIDENCE_ENTRY_COUNT")
require(
    any(line.endswith("  " + NESTED_EVIDENCE_MANIFEST) for line in evidence_lines),
    "FINAL_NESTED_EVIDENCE_NOT_INCLUDED",
)
require(
    not any(line.endswith("  evidence-manifest.txt") for line in evidence_lines),
    "FINAL_ROOT_EVIDENCE_NOT_EXCLUDED",
)
write_exclusive(
    final_root / "evidence-manifest.txt",
    ("\n".join(evidence_lines) + "\n").encode("utf-8"),
)

# Pre-seal exact tree validation.
final_files, final_dirs, final_links, final_other = scan(final_root)
require(final_files == EXPECTED_EVIDENCE_FILES, "PRESEAL_EXACT_FILE_SET")
require(final_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "PRESEAL_EXACT_DIRECTORY_SET")
require(len(final_files) == 36, "PRESEAL_FILE_COUNT")
require(len(final_dirs) == 11, "PRESEAL_DIRECTORY_COUNT")
require(final_links == 0, "PRESEAL_SYMLINK_COUNT")
require(final_other == 0, "PRESEAL_NONREGULAR_COUNT")

# Validate final Packet manifest before sealing.
final_packet_manifest = load_json(packet_root / "packet-manifest.json")
require(
    final_packet_manifest["packet_file_count_excluding_manifest"] == 33,
    "PRESEAL_PACKET_ENTRY_COUNT",
)
require(
    len(final_packet_manifest["packet_files"]) == 33,
    "PRESEAL_PACKET_LIST_LENGTH",
)
for item in final_packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(sha256(path) == item["sha256"], f"PRESEAL_PACKET_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"PRESEAL_PACKET_SIZE:{item['name']}",
    )

# Validate final Evidence manifest before sealing.
final_evidence_manifest = parse_evidence_manifest(
    final_root / "evidence-manifest.txt"
)
require(
    len(final_evidence_manifest) == 35,
    "PRESEAL_EVIDENCE_ENTRY_COUNT",
)
require(
    set(final_evidence_manifest)
    == EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"},
    "PRESEAL_EVIDENCE_EXACT_SET",
)
require(
    NESTED_EVIDENCE_MANIFEST in final_evidence_manifest,
    "PRESEAL_NESTED_EVIDENCE",
)
for relative, digest in final_evidence_manifest.items():
    require(
        sha256(final_root / relative) == digest,
        f"PRESEAL_EVIDENCE_SHA:{relative}",
    )

# Seal only the newly-created Final Evidence root.
for relative in sorted(final_files):
    os.chmod(final_root / relative, 0o444)

for relative in sorted(
    final_dirs,
    key=lambda value: (value.count("/"), value),
    reverse=True,
):
    os.chmod(final_root / relative, 0o555)

os.chmod(final_root, 0o555)

# Post-seal read-only validation.
sealed_files, sealed_dirs, sealed_links, sealed_other = scan(final_root)
require(sealed_files == EXPECTED_EVIDENCE_FILES, "SEALED_EXACT_FILE_SET")
require(sealed_dirs == EXPECTED_EVIDENCE_DIRECTORIES, "SEALED_EXACT_DIRECTORY_SET")
require(len(sealed_files) == 36, "SEALED_FILE_COUNT")
require(len(sealed_dirs) == 11, "SEALED_DIRECTORY_COUNT")
require(sealed_links == 0, "SEALED_SYMLINK_COUNT")
require(sealed_other == 0, "SEALED_NONREGULAR_COUNT")

source_uid = source_root.lstat().st_uid
source_gid = source_root.lstat().st_gid

for relative in sorted(sealed_files):
    path = final_root / relative
    item = require_regular_nonsymlink(path, f"SEALED_FILE:{relative}")
    require(stat.S_IMODE(item.st_mode) == 0o444, f"SEALED_FILE_MODE:{relative}")
    require(item.st_uid == source_uid, f"SEALED_FILE_OWNER:{relative}")
    require(item.st_gid == source_gid, f"SEALED_FILE_GROUP:{relative}")

for path in [
    final_root,
    *(final_root / relative for relative in sorted(sealed_dirs)),
]:
    item = path.lstat()
    require(stat.S_ISDIR(item.st_mode), f"SEALED_DIRECTORY:{path}")
    require(not stat.S_ISLNK(item.st_mode), f"SEALED_DIRECTORY_SYMLINK:{path}")
    require(stat.S_IMODE(item.st_mode) == 0o555, f"SEALED_DIRECTORY_MODE:{path}")
    require(item.st_uid == source_uid, f"SEALED_DIRECTORY_OWNER:{path}")
    require(item.st_gid == source_gid, f"SEALED_DIRECTORY_GROUP:{path}")

# Revalidate every copied source after sealing.
for relative in sorted(COPY_FROM_SOURCE):
    source = source_root / relative
    destination = final_root / relative
    require(
        source.read_bytes() == destination.read_bytes(),
        f"SEALED_COPY_BYTES:{relative}",
    )
    require(
        sha256(source) == sha256(destination),
        f"SEALED_COPY_SHA:{relative}",
    )
    require(
        source.stat().st_size == destination.stat().st_size,
        f"SEALED_COPY_SIZE:{relative}",
    )

# Revalidate manifests after sealing.
post_packet_manifest = load_json(packet_root / "packet-manifest.json")
require(
    post_packet_manifest["packet_file_count_excluding_manifest"] == 33,
    "POSTSEAL_PACKET_ENTRY_COUNT",
)
require(
    {item["name"] for item in post_packet_manifest["packet_files"]}
    == EXPECTED_PACKET_FILES - {"packet-manifest.json"},
    "POSTSEAL_PACKET_EXACT_SET",
)
require(
    NESTED_PACKET_MANIFEST
    in {item["name"] for item in post_packet_manifest["packet_files"]},
    "POSTSEAL_NESTED_PACKET",
)
for item in post_packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(
        sha256(path) == item["sha256"],
        f"POSTSEAL_PACKET_SHA:{item['name']}",
    )
    require(
        path.stat().st_size == item["size_bytes"],
        f"POSTSEAL_PACKET_SIZE:{item['name']}",
    )

post_evidence_manifest = parse_evidence_manifest(
    final_root / "evidence-manifest.txt"
)
require(len(post_evidence_manifest) == 35, "POSTSEAL_EVIDENCE_ENTRY_COUNT")
require(
    set(post_evidence_manifest)
    == EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"},
    "POSTSEAL_EVIDENCE_EXACT_SET",
)
require(
    NESTED_EVIDENCE_MANIFEST in post_evidence_manifest,
    "POSTSEAL_NESTED_EVIDENCE",
)
for relative, digest in post_evidence_manifest.items():
    require(
        sha256(final_root / relative) == digest,
        f"POSTSEAL_EVIDENCE_SHA:{relative}",
    )

# Source Packet Evidence and protected identities remain unchanged.
source_identity_after = tree_identity(source_root)
require(
    source_identity_after == source_identity_before,
    "SOURCE_EVIDENCE_CHANGED",
)

for relative, expected in SOURCE_FIXED_SHA.items():
    require(
        sha256(source_root / relative) == expected,
        f"SOURCE_FIXED_CHANGED:{relative}",
    )

for relative, expected in PROTECTED_SHA.items():
    require(
        sha256(repo_root / relative) == expected,
        f"PROTECTED_CHANGED:{relative}",
    )

require(not list(final_root.rglob("*.pyc")), "FINAL_BYTECODE_SIDE_EFFECT")

final_result_sha = sha256(final_root / "result.json")
final_packet_manifest_sha = sha256(packet_root / "packet-manifest.json")
final_candidate_manifest_sha = sha256(candidate_root / "candidate-manifest.json")
final_snapshot_manifest_sha = sha256(
    candidate_root / "r2-r8-r3-snapshot-manifest.json"
)
final_evidence_manifest_sha = sha256(final_root / "evidence-manifest.txt")

print(
    "RESULT="
    "PASS_W2B_I2F3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
    "REGISTRATION_AND_SEAL_EXECUTED_HUMAN_REVIEW_REQUIRED"
)
print(f"FINAL_EVIDENCE_ROOT={final_relative}")
print("SOURCE_R3_R1_PACKET_EVIDENCE_UNCHANGED=true")
print("SOURCE_R3_R1_PACKET_HUMAN_REVIEW=PASS")
print(
    "SOURCE_R3_R1_PACKET_HUMAN_REVIEW_DECISION="
    "APPROVE_NESTED_MANIFEST_CORRECTION_PACKET_WITH_EXECUTION_HOLD"
)
print("FINAL_EVIDENCE_REGISTRATION_EXECUTION_ALLOWED=true")
print("FINAL_EVIDENCE_SEAL_EXECUTION_ALLOWED=true")
print("FINAL_EVIDENCE_REGISTRATION_EXECUTED=true")
print("FINAL_EVIDENCE_SEAL_EXECUTED=true")
print(f"SEAL_COMMIT_TIMESTAMP_UTC={seal_commit_timestamp}")
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
print("FINAL_FILE_MODE=0444")
print("FINAL_DIRECTORY_MODE=0555")
print("FINAL_SYMLINK_COUNT=0")
print("FINAL_NONREGULAR_COUNT=0")
print("FINAL_OWNER_GROUP_CHANGE_PERFORMED=false")
print("POST_SEAL_READONLY_VALIDATION=PASS")
print("FINAL_BYTECODE_SIDE_EFFECT=false")
print("ROOT_READONLY_VERIFICATION_RESULT=ABSENT_CONFIRMED")
print("ROOT_READONLY_VERIFICATION_EXECUTION_ATTEMPT_COUNT=1")
print("ROOT_READONLY_VERIFICATION_MAX_EXECUTIONS=1")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
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
print("PROTECTED_SHA_UNCHANGED=true")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE="
    "HUMAN_REVIEW_3E_J_R2_R8_R3_R1_FINAL_EVIDENCE_"
    "REGISTRATION_AND_SEAL_RESULT_READONLY"
)
print(f"FINAL_RESULT_SHA={final_result_sha}")
print(f"FINAL_PACKET_MANIFEST_SHA={final_packet_manifest_sha}")
print(f"FINAL_CANDIDATE_MANIFEST_SHA={final_candidate_manifest_sha}")
print(f"FINAL_SNAPSHOT_MANIFEST_SHA={final_snapshot_manifest_sha}")
print(f"FINAL_EVIDENCE_MANIFEST_SHA={final_evidence_manifest_sha}")
PY

echo "SCRIPT_EXIT_CODE=0"
