#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

R7_REL="${BASE_REL}/i2f3e-j-r2-r7-evidence-seal-correction-20260726T012717Z-523349"
R7_ROOT="${REPO_ROOT}/${R7_REL}"

FAILED_R1_REL="${BASE_REL}/i2f3e-j-r2-r8-root-readonly-verification-packet-preparation-20260726T015730Z-524269"
FAILED_R1_ROOT="${REPO_ROOT}/${FAILED_R1_REL}"

R2_REL="${BASE_REL}/i2f3e-j-r2-r8-r2-candidate-exact-file-set-correction-20260726T021229Z-524713"
R2_ROOT="${REPO_ROOT}/${R2_REL}"
PACKET_ROOT="${R2_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
LOG_ROOT="${R2_ROOT}/validation-logs"

CONSOLE_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r8_r2_console.txt"
REVIEW_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r8_r2_human_review_readonly.txt"

EXPECTED_RESULT_SHA="b9706aaa71dee9ee3de527bcaa7ca114fec03f5f63220a4a220cd3f417e979ac"
EXPECTED_PACKET_MANIFEST_SHA="41d3e08bcd454307d1f51dcfd185f68f0ac56f96cb85a3bb5f029c5ddd902450"
EXPECTED_EVIDENCE_MANIFEST_SHA="b9516b7e4041abfd969866748a8c6a7cf98d623bed501fd1d50c59d647250971"
EXPECTED_CANDIDATE_MANIFEST_SHA="c1d53b3ac8dac86435dde89d4cfe021e1573a000747ce303ebcf62a5fb1c39ec"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$R7_ROOT"
test -d "$FAILED_R1_ROOT"
test -d "$R2_ROOT"
test -d "$CANDIDATE_ROOT"
test -d "$LOG_ROOT"
test -f "$CONSOLE_LOG"

cd "$REPO_ROOT"

(
  set -Eeuo pipefail

  printf '\n===== FIXED SHA REVIEW =====\n'

  sha256sum -c <<SHAS
${EXPECTED_RESULT_SHA}  ${R2_ROOT}/result.json
${EXPECTED_PACKET_MANIFEST_SHA}  ${PACKET_ROOT}/packet-manifest.json
${EXPECTED_EVIDENCE_MANIFEST_SHA}  ${R2_ROOT}/evidence-manifest.txt
${EXPECTED_CANDIDATE_MANIFEST_SHA}  ${CANDIDATE_ROOT}/candidate-manifest.json
SHAS

  printf '\n===== READ-ONLY PACKET HUMAN REVIEW =====\n'

  "$PYTHON_BIN" -B - \
    "$REPO_ROOT" \
    "$R7_ROOT" \
    "$FAILED_R1_ROOT" \
    "$R2_ROOT" \
    "$PACKET_ROOT" \
    "$CANDIDATE_ROOT" \
    "$LOG_ROOT" \
    "$CONSOLE_LOG" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
r7_root = Path(sys.argv[2]).resolve(strict=True)
failed_r1_root = Path(sys.argv[3]).resolve(strict=True)
r2_root = Path(sys.argv[4]).resolve(strict=True)
packet_root = Path(sys.argv[5]).resolve(strict=True)
candidate_root = Path(sys.argv[6]).resolve(strict=True)
log_root = Path(sys.argv[7]).resolve(strict=True)
console_log = Path(sys.argv[8]).resolve(strict=True)

TARGET = "/etc/sudoers.d/ai-media-os-3e-j-root-helper"
CANDIDATE_PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8"
WRAPPER_PHASE = "TST-5D-W2B-I2F-3E-J-R2-R8-R2"
EXECUTION_APPROVAL_TOKEN = (
    "APPROVE_3E_J_R2_R8_ROOT_READONLY_"
    "SUDOERS_DESTINATION_VERIFICATION_EXECUTION"
)

expected_r7_relative = (
    "exchange/review_evidence/slack_worker_release_rebinding/"
    "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/"
    "tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/"
    "i2f3e-j-r2-r7-evidence-seal-correction-20260726T012717Z-523349"
)
expected_failed_r1_relative = (
    "exchange/review_evidence/slack_worker_release_rebinding/"
    "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/"
    "tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/"
    "i2f3e-j-r2-r8-root-readonly-verification-packet-preparation-"
    "20260726T015730Z-524269"
)
expected_r2_relative = (
    "exchange/review_evidence/slack_worker_release_rebinding/"
    "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/"
    "tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/"
    "i2f3e-j-r2-r8-r2-candidate-exact-file-set-correction-"
    "20260726T021229Z-524713"
)

expected_r2_sha = {
    "result.json": (
        "b9706aaa71dee9ee3de527bcaa7ca114f"
        "ec03f5f63220a4a220cd3f417e979ac"
    ),
    "packet-snapshot/packet-manifest.json": (
        "41d3e08bcd454307d1f51dcfd185f68f"
        "0ac56f96cb85a3bb5f029c5ddd902450"
    ),
    "evidence-manifest.txt": (
        "b9516b7e4041abfd969866748a8c6a7c"
        "f98d623bed501fd1d50c59d647250971"
    ),
    "packet-snapshot/candidate-artifacts/candidate-manifest.json": (
        "c1d53b3ac8dac86435dde89d4cfe021e"
        "1573a000747ce303ebcf62a5fb1c39ec"
    ),
}

expected_candidate_artifacts = {
    "candidate-manifest.json": {
        "sha256": (
            "c1d53b3ac8dac86435dde89d4cfe021e"
            "1573a000747ce303ebcf62a5fb1c39ec"
        ),
        "size_bytes": 1812,
    },
    "3e-j-r2-r8-operation-manual.md": {
        "sha256": (
            "e72d1c584d6e4b04e52b3d946f25a89"
            "e60472c50f0ae2196ab5a133f1afceeb7"
        ),
        "size_bytes": 2246,
    },
    "r2-r8-result-schema.json": {
        "sha256": (
            "48d2824bbfa27789dbe9eca3c3b96550"
            "789294761fba2f8fe2a886b329567d14"
        ),
        "size_bytes": 1118,
    },
    "root-readonly-command-contract.json": {
        "sha256": (
            "d7f6caa8a5c7b4eee4e343a8b6350ab"
            "8e0ad378a6c704d175834c9ed0561b2f8"
        ),
        "size_bytes": 1859,
    },
    "root-readonly-verification-policy.json": {
        "sha256": (
            "c909ea2f4d42d0b1e44dc35aa0a59cd"
            "6573609d5c988d5eeca837d3b2580d141"
        ),
        "size_bytes": 1384,
    },
    "root_readonly_sudoers_destination_verifier.sh": {
        "sha256": (
            "bd555f07ba09c72e211ab1ae5d1af3b"
            "8c544a87ff5204ab8d476cb8923fddd93"
        ),
        "size_bytes": 3711,
    },
    "test_r2_r8_packet_negative.py": {
        "sha256": (
            "ff001e7ec90c2b699edae347b8ee4e29"
            "56693805d226133f90bd159e7b66a4c2"
        ),
        "size_bytes": 5365,
    },
    "validate_r2_r8_packet.py": {
        "sha256": (
            "d459effbe8d4e659c0c1350c8acea0fb"
            "eb692470e1c8db39f0f13fa5e8956332"
        ),
        "size_bytes": 8396,
    },
}

expected_r7_sha = {
    "result.json": (
        "ff696c3857c9b9624ec8bb76b7eb668f"
        "2a90285825711f4cb3fdcbcc48f048c1"
    ),
    "seal-validation.json": (
        "a8927081753839939f752256fa7edbe0d"
        "bad1816341cb34a32484a325ab96e1d"
    ),
    "snapshot-copy-manifest.json": (
        "d6b71537bae70fa0f4e9ae2a6b9b2148"
        "81ec11e0190e440782c9da0a71d9afc3"
    ),
    "evidence-manifest.txt": (
        "a31bd7fc37753688feaa19e0bf518fb1"
        "fdcf5d5743a2fb87ac3d4625ec2ea380"
    ),
}

expected_failed_r1_sha = {
    "result.json": (
        "86ec0827d69dfdfda70f1eaa8c968fd6"
        "03bcbb3b0c5f3a552b8365becf494a84"
    ),
    "packet-snapshot/packet-manifest.json": (
        "4e2e735882ed2474caa03382b35fc1b6"
        "add45343267624a55d8a6f0794a0aa49"
    ),
    "evidence-manifest.txt": (
        "918e2fe2636e50626ecb24a2a5b6ea3c"
        "1edc0c0558eedb4f76b71ca2856847d4"
    ),
}

expected_protected_sha = {
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

expected_commands = [
    ["/usr/bin/sudo", "--", "/usr/bin/id", "-u"],
    ["/usr/bin/sudo", "--", "/usr/bin/test", "-e", TARGET],
    ["/usr/bin/sudo", "--", "/usr/bin/test", "-L", TARGET],
    [
        "/usr/bin/sudo",
        "--",
        "/usr/bin/stat",
        (
            "--printf=file_type=%F\\nowner_name=%U\\nowner_uid=%u\\n"
            "group_name=%G\\ngroup_gid=%g\\nmode=%a\\n"
        ),
        "--",
        TARGET,
    ],
]

expected_candidate_file_set = set(expected_candidate_artifacts)
expected_log_file_set = {
    "negative-tests.log",
    "python-compile.log",
    "validator.log",
    "verifier-bash-n.log",
}
expected_evidence_file_set = {
    "result.json",
    "evidence-manifest.txt",
    "packet-snapshot/packet-manifest.json",
    "packet-snapshot/human-approval-verbatim.txt",
    *(f"packet-snapshot/candidate-artifacts/{name}"
      for name in expected_candidate_file_set),
    *(f"validation-logs/{name}" for name in expected_log_file_set),
}
expected_evidence_directory_set = {
    "packet-snapshot",
    "packet-snapshot/candidate-artifacts",
    "validation-logs",
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

def scan_tree(root: Path) -> tuple[list[Path], list[Path], int, int]:
    state = root.lstat()
    require(stat.S_ISDIR(state.st_mode), f"ROOT_NOT_DIRECTORY:{root}")
    require(not stat.S_ISLNK(state.st_mode), f"ROOT_SYMLINK:{root}")

    files: list[Path] = []
    directories: list[Path] = []
    symlinks = 0
    nonregular = 0

    def walk(directory: Path) -> None:
        nonlocal symlinks, nonregular
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            item = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(item.st_mode):
                symlinks += 1
            elif stat.S_ISDIR(item.st_mode):
                directories.append(path)
                walk(path)
            elif stat.S_ISREG(item.st_mode):
                files.append(path)
            else:
                nonregular += 1

    walk(root)
    return sorted(files), sorted(directories), symlinks, nonregular

def validate_sha_map(root: Path, values: dict[str, str], label: str) -> None:
    for relative, expected in values.items():
        path = root / relative
        require(path.is_file(), f"{label}_MISSING:{relative}")
        require(sha256(path) == expected, f"{label}_SHA:{relative}")

require(
    r7_root.relative_to(repo_root).as_posix() == expected_r7_relative,
    "R7_ROOT_BINDING",
)
require(
    failed_r1_root.relative_to(repo_root).as_posix()
    == expected_failed_r1_relative,
    "FAILED_R1_ROOT_BINDING",
)
require(
    r2_root.relative_to(repo_root).as_posix() == expected_r2_relative,
    "R2_ROOT_BINDING",
)
require(packet_root == r2_root / "packet-snapshot", "PACKET_ROOT_BINDING")
require(
    candidate_root == packet_root / "candidate-artifacts",
    "CANDIDATE_ROOT_BINDING",
)
require(log_root == r2_root / "validation-logs", "LOG_ROOT_BINDING")

validate_sha_map(r2_root, expected_r2_sha, "R2")
validate_sha_map(r7_root, expected_r7_sha, "R7")
validate_sha_map(failed_r1_root, expected_failed_r1_sha, "FAILED_R1")
validate_sha_map(repo_root, expected_protected_sha, "PROTECTED")

# Exact R2-R8-R2 Evidence file and directory sets.
r2_files, r2_directories, r2_symlinks, r2_nonregular = scan_tree(r2_root)
actual_evidence_file_set = {
    path.relative_to(r2_root).as_posix() for path in r2_files
}
actual_evidence_directory_set = {
    path.relative_to(r2_root).as_posix() for path in r2_directories
}
require(
    actual_evidence_file_set == expected_evidence_file_set,
    "R2_EVIDENCE_EXACT_FILE_SET",
)
require(
    actual_evidence_directory_set == expected_evidence_directory_set,
    "R2_EVIDENCE_EXACT_DIRECTORY_SET",
)
require(len(r2_files) == 16, "R2_EVIDENCE_FILE_COUNT_NOT_16")
require(len(r2_directories) == 3, "R2_EVIDENCE_DIRECTORY_COUNT_NOT_3")
require(r2_symlinks == 0, "R2_EVIDENCE_SYMLINK_COUNT")
require(r2_nonregular == 0, "R2_EVIDENCE_NONREGULAR_COUNT")

repo_state = repo_root.stat()
expected_uid = repo_state.st_uid
expected_gid = repo_state.st_gid
require(
    all(
        path.lstat().st_uid == expected_uid
        and path.lstat().st_gid == expected_gid
        for path in [r2_root] + r2_files + r2_directories
    ),
    "R2_EVIDENCE_OWNER_GROUP",
)

file_modes = Counter(
    f"{stat.S_IMODE(path.lstat().st_mode):04o}" for path in r2_files
)
directory_modes = Counter(
    f"{stat.S_IMODE(path.lstat().st_mode):04o}"
    for path in [r2_root] + r2_directories
)

# Candidate exact set and independent SHA/size binding.
candidate_files, candidate_directories, candidate_symlinks, candidate_nonregular = (
    scan_tree(candidate_root)
)
actual_candidate_file_set = {
    path.relative_to(candidate_root).as_posix()
    for path in candidate_files
}
require(
    actual_candidate_file_set == expected_candidate_file_set,
    "CANDIDATE_EXACT_FILE_SET",
)
require(len(candidate_files) == 8, "CANDIDATE_FILE_COUNT_NOT_8")
require(len(candidate_directories) == 0, "CANDIDATE_DIRECTORY_COUNT_NOT_0")
require(candidate_symlinks == 0, "CANDIDATE_SYMLINK_COUNT")
require(candidate_nonregular == 0, "CANDIDATE_NONREGULAR_COUNT")
require(
    not any(path.suffix == ".pyc" for path in candidate_files),
    "CANDIDATE_PYC_PRESENT",
)
for name, expected in expected_candidate_artifacts.items():
    path = candidate_root / name
    require(path.is_file(), f"CANDIDATE_MISSING:{name}")
    require(sha256(path) == expected["sha256"], f"CANDIDATE_SHA:{name}")
    require(path.stat().st_size == expected["size_bytes"], f"CANDIDATE_SIZE:{name}")

candidate_manifest = load_json(candidate_root / "candidate-manifest.json")
require(candidate_manifest["phase"] == CANDIDATE_PHASE, "CANDIDATE_MANIFEST_PHASE")
require(
    candidate_manifest["status"] == "CANDIDATE_PACKET_PREPARED_NO_EXECUTION",
    "CANDIDATE_MANIFEST_STATUS",
)
require(
    candidate_manifest["target_path"] == TARGET,
    "CANDIDATE_MANIFEST_TARGET",
)
require(
    candidate_manifest["file_count_excluding_manifest"] == 7,
    "CANDIDATE_MANIFEST_EXCLUDING_COUNT",
)
require(
    candidate_manifest["exact_file_set_required"] is True,
    "CANDIDATE_MANIFEST_EXACT_REQUIRED",
)
require(
    candidate_manifest["expected_total_file_count"] == 8,
    "CANDIDATE_MANIFEST_TOTAL_COUNT",
)
require(
    candidate_manifest["expected_directory_count"] == 0,
    "CANDIDATE_MANIFEST_DIRECTORY_COUNT",
)
require(
    candidate_manifest["bytecode_file_allowed"] is False,
    "CANDIDATE_MANIFEST_BYTECODE_FLAG",
)
require(
    candidate_manifest["root_readonly_verification_executed"] is False,
    "CANDIDATE_MANIFEST_ROOT_EXECUTION",
)
require(
    candidate_manifest["sudo_execution_performed"] is False,
    "CANDIDATE_MANIFEST_SUDO_EXECUTION",
)
require(
    candidate_manifest["sudoers_changed"] is False,
    "CANDIDATE_MANIFEST_SUDOERS_CHANGED",
)
require(
    candidate_manifest["candidate_deployed_to_production"] is False,
    "CANDIDATE_MANIFEST_PRODUCTION",
)
declared_candidate = {
    "candidate-manifest.json",
    *(item["name"] for item in candidate_manifest["files"]),
}
require(
    declared_candidate == expected_candidate_file_set,
    "CANDIDATE_MANIFEST_DECLARED_SET",
)
for item in candidate_manifest["files"]:
    expected = expected_candidate_artifacts[item["name"]]
    require(item["sha256"] == expected["sha256"], f"MANIFEST_SHA:{item['name']}")
    require(
        item["size_bytes"] == expected["size_bytes"],
        f"MANIFEST_SIZE:{item['name']}",
    )

# Packet manifest must cover exactly 13 pre-manifest packet files.
packet_manifest = load_json(packet_root / "packet-manifest.json")
require(packet_manifest["phase"] == WRAPPER_PHASE, "PACKET_MANIFEST_PHASE")
require(
    packet_manifest["candidate_phase"] == CANDIDATE_PHASE,
    "PACKET_MANIFEST_CANDIDATE_PHASE",
)
require(
    packet_manifest["status"]
    == (
        "ROOT_READONLY_VERIFICATION_PACKET_EXACT_FILE_SET_"
        "CORRECTED_PREPARED_NO_EXECUTION"
    ),
    "PACKET_MANIFEST_STATUS",
)
require(packet_manifest["target_path"] == TARGET, "PACKET_MANIFEST_TARGET")
require(
    packet_manifest["packet_file_count_excluding_manifest"] == 13,
    "PACKET_MANIFEST_FILE_COUNT",
)
require(
    packet_manifest["candidate_declared_file_count"] == 8,
    "PACKET_MANIFEST_DECLARED_COUNT",
)
require(
    packet_manifest["candidate_actual_file_count"] == 8,
    "PACKET_MANIFEST_ACTUAL_COUNT",
)
require(
    packet_manifest["candidate_directory_count"] == 0,
    "PACKET_MANIFEST_DIRECTORY_COUNT",
)
require(
    packet_manifest["candidate_pyc_file_count"] == 0,
    "PACKET_MANIFEST_PYC_COUNT",
)
require(
    packet_manifest["candidate_exact_file_set_review"] == "PASS",
    "PACKET_MANIFEST_EXACT_REVIEW",
)
require(
    packet_manifest["python_compile_method"]
    == "BUILTIN_COMPILE_NO_BYTECODE",
    "PACKET_MANIFEST_COMPILE_METHOD",
)
require(
    packet_manifest["validation_subprocess_bytecode_disabled"] is True,
    "PACKET_MANIFEST_BYTECODE_DISABLED",
)
for key in (
    "root_readonly_verification_executed",
    "sudo_execution_performed",
    "sudoers_changed",
    "candidate_deployed_to_production",
):
    require(packet_manifest[key] is False, f"PACKET_MANIFEST_FALSE:{key}")

packet_declared = {
    item["name"] for item in packet_manifest["packet_files"]
}
packet_actual_excluding_manifest = {
    path.relative_to(packet_root).as_posix()
    for path in packet_root.rglob("*")
    if path.is_file() and path.name != "packet-manifest.json"
}
require(len(packet_declared) == 13, "PACKET_DECLARED_COUNT_NOT_13")
require(
    packet_declared == packet_actual_excluding_manifest,
    "PACKET_MANIFEST_EXACT_FILE_SET",
)
for item in packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(sha256(path) == item["sha256"], f"PACKET_FILE_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"PACKET_FILE_SIZE:{item['name']}",
    )

# Evidence manifest must cover exactly all other 15 files.
evidence_manifest_path = r2_root / "evidence-manifest.txt"
evidence_entries: dict[str, str] = {}
for line in evidence_manifest_path.read_text(encoding="utf-8").splitlines():
    digest, relative = line.split("  ", 1)
    require(relative not in evidence_entries, f"EVIDENCE_DUPLICATE:{relative}")
    evidence_entries[relative] = digest
actual_evidence_excluding_manifest = (
    actual_evidence_file_set - {"evidence-manifest.txt"}
)
require(len(evidence_entries) == 15, "EVIDENCE_MANIFEST_COUNT_NOT_15")
require(
    set(evidence_entries) == actual_evidence_excluding_manifest,
    "EVIDENCE_MANIFEST_EXACT_FILE_SET",
)
for relative, digest in evidence_entries.items():
    require(
        sha256(r2_root / relative) == digest,
        f"EVIDENCE_MANIFEST_SHA:{relative}",
    )

# Result contract and HOLD boundary.
result = load_json(r2_root / "result.json")
require(result["phase"] == WRAPPER_PHASE, "RESULT_PHASE")
require(result["candidate_phase"] == CANDIDATE_PHASE, "RESULT_CANDIDATE_PHASE")
require(
    result["result"]
    == (
        "PASS_W2B_I2F3E_J_R2_R8_R2_CANDIDATE_EXACT_FILE_SET_"
        "CORRECTION_PREPARED_NO_EXECUTION"
    ),
    "RESULT_VALUE",
)
require(result["evidence_root"] == expected_r2_relative, "RESULT_EVIDENCE_ROOT")
require(result["target_path"] == TARGET, "RESULT_TARGET")
require(
    result["source_r2_r7_fixed_sha_review"] == "PASS",
    "RESULT_R7_SHA",
)
require(result["source_r2_r7_seal_review"] == "PASS", "RESULT_R7_SEAL")
require(
    result["source_r2_r8_r1_result"]
    == "FAILED_CANDIDATE_EXTRA_PYC_FILES_NO_ROOT_EXECUTION",
    "RESULT_FAILED_R1_VALUE",
)
require(result["source_r2_r8_r1_declared_file_count"] == 8, "RESULT_R1_DECLARED")
require(result["source_r2_r8_r1_actual_file_count"] == 10, "RESULT_R1_ACTUAL")
require(result["source_r2_r8_r1_extra_file_count"] == 2, "RESULT_R1_EXTRA")
require(result["candidate_declared_file_count"] == 8, "RESULT_DECLARED")
require(result["candidate_actual_file_count"] == 8, "RESULT_ACTUAL")
require(result["candidate_directory_count"] == 0, "RESULT_DIRECTORY")
require(result["candidate_pyc_file_count"] == 0, "RESULT_PYC")
require(result["candidate_exact_file_set_review"] == "PASS", "RESULT_EXACT")
require(
    result["python_compile_method"] == "BUILTIN_COMPILE_NO_BYTECODE",
    "RESULT_COMPILE",
)
require(
    result["validation_subprocess_bytecode_disabled"] is True,
    "RESULT_BYTECODE_DISABLED",
)
require(result["negative_test_count"] == 13, "RESULT_NEGATIVE_COUNT")
require(result["negative_tests"] == "PASS", "RESULT_NEGATIVE")
require(result["validator"] == "PASS", "RESULT_VALIDATOR")
require(result["verifier_bash_n"] == "PASS", "RESULT_BASH_N")
for key in (
    "root_readonly_verification_executed",
    "sudo_execution_performed",
    "sudoers_changed",
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
    "RESULT_RUNNER_STATUS",
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
require(result["evidence_seal_performed"] is False, "RESULT_SEAL_PERFORMED")
require(
    result["evidence_seal_status"]
    == "NOT_PERFORMED_CHMOD_NOT_AUTHORIZED",
    "RESULT_SEAL_STATUS",
)
require(
    result["next_gate"]
    == "HUMAN_REVIEW_3E_J_R2_R8_R2_EXACT_FILE_SET_CORRECTED_PACKET",
    "RESULT_NEXT_GATE",
)

# Existing validation logs only; nothing is re-executed.
actual_log_file_set = {
    path.name for path in log_root.iterdir() if path.is_file()
}
actual_log_directories = {
    path.name for path in log_root.iterdir() if path.is_dir()
}
require(actual_log_file_set == expected_log_file_set, "LOG_EXACT_FILE_SET")
require(not actual_log_directories, "LOG_DIRECTORY_SET_NOT_EMPTY")

compile_log = (log_root / "python-compile.log").read_text(encoding="utf-8")
require(
    compile_log.splitlines()
    == [
        "PYTHON_COMPILE_PASS=validate_r2_r8_packet.py",
        "PYTHON_COMPILE_PASS=test_r2_r8_packet_negative.py",
    ],
    "COMPILE_LOG_CONTENT",
)

validator_log = (log_root / "validator.log").read_text(encoding="utf-8")
required_validator_markers = {
    "VALIDATION=PASS",
    "PACKET_EXACT_FILE_SET_VALID=true",
    "PACKET_FILE_COUNT=8",
    "PACKET_DIRECTORY_COUNT=0",
    "TARGET_PATH_FIXED=true",
    "COMMAND_COUNT=4",
    "COMMAND_ARGV_EXACT=true",
    "ROOT_SHELL_ALLOWED=false",
    "ARBITRARY_ARGUMENT_ALLOWED=false",
    "FILE_CONTENT_READ_ALLOWED=false",
    "WRITE_OPERATION_ALLOWED=false",
    "ROOT_READONLY_VERIFICATION_EXECUTED=false",
    "SUDOERS_CHANGED=false",
    "PRODUCTION_DEPLOYMENT_PERFORMED=false",
}
validator_lines = {
    line.strip() for line in validator_log.splitlines() if line.strip()
}
require(
    required_validator_markers <= validator_lines,
    "VALIDATOR_LOG_MARKER_MISSING",
)

negative_log = (log_root / "negative-tests.log").read_text(encoding="utf-8")
negative_lines = [line.strip() for line in negative_log.splitlines()]
require("Ran 13 tests" in negative_log, "NEGATIVE_LOG_TEST_COUNT")
require(negative_lines.count("OK") == 1, "NEGATIVE_LOG_OK_COUNT")
require("FAILED" not in negative_lines, "NEGATIVE_LOG_FAILED")
require("ERROR" not in negative_lines, "NEGATIVE_LOG_ERROR")

bash_log_path = log_root / "verifier-bash-n.log"
require(bash_log_path.stat().st_size == 0, "BASH_N_LOG_NOT_EMPTY")

# Fixed target, exact argv, and approval gate.
contract = load_json(
    candidate_root / "root-readonly-command-contract.json"
)
require(contract["phase"] == CANDIDATE_PHASE, "CONTRACT_PHASE")
require(contract["target_path"] == TARGET, "CONTRACT_TARGET")
require(contract["command_count"] == 4, "CONTRACT_COMMAND_COUNT")
require(
    [item["argv"] for item in contract["commands"]] == expected_commands,
    "CONTRACT_COMMAND_ARGV",
)
require(
    all(item["read_only"] is True for item in contract["commands"]),
    "CONTRACT_READ_ONLY",
)
require(
    contract["required_execution_approval_environment_variable"]
    == "R2_R8_ROOT_READONLY_VERIFICATION_APPROVED",
    "CONTRACT_APPROVAL_ENV",
)
require(
    contract["required_execution_approval_value"]
    == EXECUTION_APPROVAL_TOKEN,
    "CONTRACT_APPROVAL_VALUE",
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

policy = load_json(
    candidate_root / "root-readonly-verification-policy.json"
)
require(policy["phase"] == CANDIDATE_PHASE, "POLICY_PHASE")
require(policy["target_path"] == TARGET, "POLICY_TARGET")
require(
    policy["status"] == "ROOT_READONLY_VERIFICATION_PACKET_PREPARED_NO_EXECUTION",
    "POLICY_STATUS",
)
require(
    policy["verification_scope"]
    == [
        "existence_state",
        "file_type",
        "owner_name",
        "owner_uid",
        "group_name",
        "group_gid",
        "mode",
        "symlink_state",
    ],
    "POLICY_SCOPE",
)
for key in (
    "content_read_allowed",
    "root_readonly_verification_executed",
    "sudo_execution_performed",
    "sudoers_changed",
    "production_deployment_performed",
    "arbitrary_argument_allowed",
    "wildcard_allowed",
    "shell_as_root_allowed",
    "editor_as_root_allowed",
    "environment_inheritance_allowed",
    "command_substitution_as_root_allowed",
    "write_operation_allowed",
    "delete_operation_allowed",
    "rename_operation_allowed",
    "chmod_allowed",
    "chown_allowed",
    "automatic_deployment_after_absent_confirmation",
):
    require(policy[key] is False, f"POLICY_FALSE:{key}")
require(
    policy["deployment_authorization_packet_status"]
    == "HOLD_PENDING_ROOT_READONLY_VERIFICATION_AND_HUMAN_REVIEW",
    "POLICY_PACKET_STATUS",
)
require(
    policy["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "POLICY_RUNNER_STATUS",
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

schema = load_json(candidate_root / "r2-r8-result-schema.json")
require(
    schema["properties"]["target_path"]["const"] == TARGET,
    "SCHEMA_TARGET",
)
require(
    schema["properties"]["sudoers_changed"]["const"] is False,
    "SCHEMA_SUDOERS",
)

verifier = (
    candidate_root / "root_readonly_sudoers_destination_verifier.sh"
).read_text(encoding="utf-8")
require(f'TARGET="{TARGET}"' in verifier, "VERIFIER_FIXED_TARGET")
require('if [[ "$#" -ne 0 ]]' in verifier, "VERIFIER_ARG_GATE")
require(
    "R2_R8_ROOT_READONLY_VERIFICATION_APPROVED" in verifier,
    "VERIFIER_APPROVAL_ENV",
)
require(EXECUTION_APPROVAL_TOKEN in verifier, "VERIFIER_APPROVAL_VALUE")
require(verifier.count('"$SUDO_BIN" --') == 4, "VERIFIER_SUDO_CALL_COUNT")
require("cat " not in verifier, "VERIFIER_CONTENT_CAT")
require("chmod " not in verifier, "VERIFIER_CHMOD")
require("chown " not in verifier, "VERIFIER_CHOWN")
require("rm " not in verifier, "VERIFIER_RM")
require("mv " not in verifier, "VERIFIER_MV")
require("/bin/sh" not in verifier, "VERIFIER_ROOT_SHELL")
require("/bin/bash" not in verifier, "VERIFIER_ROOT_BASH")
require("python" not in verifier.lower(), "VERIFIER_ROOT_PYTHON")
require("%N" not in verifier, "VERIFIER_LINK_TARGET_DISCLOSURE")
require(
    "ROOT_READONLY_VERIFICATION_EXECUTED=false" in verifier,
    "VERIFIER_BLOCKED_MARKER",
)
require("SUDOERS_CHANGED=false" in verifier, "VERIFIER_SUDOERS_MARKER")

validator_source = (
    candidate_root / "validate_r2_r8_packet.py"
).read_text(encoding="utf-8")
require(
    "PACKET_EXACT_FILE_SET_MISMATCH" in validator_source,
    "VALIDATOR_EXACT_SET_ENFORCEMENT",
)
require(
    "PACKET_DIRECTORY_SET_NOT_EMPTY" in validator_source,
    "VALIDATOR_DIRECTORY_ENFORCEMENT",
)
require(
    "PACKET_EXACT_FILE_SET_VALID=true" in validator_source,
    "VALIDATOR_PASS_MARKER",
)

negative_source = (
    candidate_root / "test_r2_r8_packet_negative.py"
).read_text(encoding="utf-8")
require(
    "test_extra_packet_file_rejected" in negative_source,
    "NEGATIVE_EXTRA_FILE_TEST",
)
require(
    "unexpected.cpython-310.pyc" in negative_source,
    "NEGATIVE_PYC_FIXTURE",
)

approval_text = (
    packet_root / "human-approval-verbatim.txt"
).read_text(encoding="utf-8")
required_approval_markers = (
    "APPROVE_3E_J_R2_R8_ROOT_READONLY_SUDOERS_DESTINATION_VERIFICATION_PACKET_PREPARATION_NO_EXECUTION",
    "R2_R7_HUMAN_REVIEW_DECISION=APPROVE_SEALED_EVIDENCE_WITH_EXECUTION_HOLD",
    "EVIDENCE_SEAL_COMPLETE=true",
    "ROOT_READONLY_VERIFICATION_EXECUTED=false",
    "SUDOERS_CHANGED=false",
    "CANDIDATE_DEPLOYED_TO_PRODUCTION=false",
    "WRITER_FREEZE_EXECUTION=HOLD",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "RELEASE_STATUS=CANDIDATE_NOT_APPROVED",
)
for marker in required_approval_markers:
    require(marker in approval_text, f"APPROVAL_MARKER:{marker}")

# R2-R8-R1 immutable failed evidence must remain 8 declared / 10 actual.
failed_candidate = failed_r1_root / "packet-snapshot/candidate-artifacts"
failed_manifest = load_json(failed_candidate / "candidate-manifest.json")
failed_declared = {
    "candidate-manifest.json",
    *(item["name"] for item in failed_manifest["files"]),
}
failed_actual = {
    path.relative_to(failed_candidate).as_posix()
    for path in failed_candidate.rglob("*")
    if path.is_file()
}
failed_extra = failed_actual - failed_declared
require(len(failed_declared) == 8, "FAILED_R1_DECLARED_COUNT")
require(len(failed_actual) == 10, "FAILED_R1_ACTUAL_COUNT")
require(
    failed_extra
    == {
        "__pycache__/test_r2_r8_packet_negative.cpython-310.pyc",
        "__pycache__/validate_r2_r8_packet.cpython-310.pyc",
    },
    "FAILED_R1_EXTRA_SET",
)

# Console completion binding.
console = console_log.read_text(encoding="utf-8")
console_lines = [line.strip() for line in console.splitlines()]
required_console_lines = (
    "RESULT=PASS_W2B_I2F3E_J_R2_R8_R2_CANDIDATE_EXACT_FILE_SET_CORRECTION_PREPARED_NO_EXECUTION",
    f"EVIDENCE_ROOT={expected_r2_relative}",
    "SOURCE_R2_R7_FIXED_SHA_REVIEW=PASS",
    "SOURCE_R2_R7_SEAL_REVIEW=PASS",
    "SOURCE_R2_R8_R1_RESULT=FAILED_CANDIDATE_EXTRA_PYC_FILES_NO_ROOT_EXECUTION",
    "SOURCE_R2_R8_R1_DECLARED_FILE_COUNT=8",
    "SOURCE_R2_R8_R1_ACTUAL_FILE_COUNT=10",
    "SOURCE_R2_R8_R1_EXTRA_FILE_COUNT=2",
    f"TARGET_PATH={TARGET}",
    "CANDIDATE_DECLARED_FILE_COUNT=8",
    "CANDIDATE_ACTUAL_FILE_COUNT=8",
    "CANDIDATE_DIRECTORY_COUNT=0",
    "CANDIDATE_PYC_FILE_COUNT=0",
    "CANDIDATE_EXACT_FILE_SET_REVIEW=PASS",
    "PYTHON_COMPILE_METHOD=BUILTIN_COMPILE_NO_BYTECODE",
    "VALIDATION_SUBPROCESS_BYTECODE_DISABLED=true",
    "NEGATIVE_TEST_COUNT=13",
    "NEGATIVE_TESTS=PASS",
    "VALIDATOR=PASS",
    "VERIFIER_BASH_N=PASS",
    "ROOT_READONLY_VERIFICATION_EXECUTED=false",
    "SUDO_EXECUTION_PERFORMED=false",
    "SUDOERS_CHANGED=false",
    "CANDIDATE_DEPLOYED_TO_PRODUCTION=false",
    "PROTECTED_SHA_UNCHANGED=true",
    "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "WRITER_FREEZE_EXECUTION=HOLD",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "RELEASE_STATUS=CANDIDATE_NOT_APPROVED",
    "EVIDENCE_SEAL_PERFORMED=false",
    "EVIDENCE_SEAL_STATUS=NOT_PERFORMED_CHMOD_NOT_AUTHORIZED",
    "NEXT_GATE=HUMAN_REVIEW_3E_J_R2_R8_R2_EXACT_FILE_SET_CORRECTED_PACKET",
    "RESULT_SHA=b9706aaa71dee9ee3de527bcaa7ca114fec03f5f63220a4a220cd3f417e979ac",
    "PACKET_MANIFEST_SHA=41d3e08bcd454307d1f51dcfd185f68f0ac56f96cb85a3bb5f029c5ddd902450",
    "EVIDENCE_MANIFEST_SHA=b9516b7e4041abfd969866748a8c6a7cf98d623bed501fd1d50c59d647250971",
    "CORRECTION_LABEL=CANDIDATE_PYC_SIDE_EFFECT_AND_EXACT_FILE_SET_CORRECTION",
)
for marker in required_console_lines:
    require(marker in console_lines, f"CONSOLE_MARKER:{marker}")
require(
    console_lines.count("SCRIPT_EXIT_CODE=0") == 1,
    "CONSOLE_EXIT_ZERO_COUNT_NOT_EXACTLY_ONE",
)
require("Traceback (most recent call last):" not in console, "CONSOLE_TRACEBACK")
require("AssertionError:" not in console, "CONSOLE_ASSERTION_ERROR")

print("R2_R8_R2_RESULT_SHA_REVIEW=PASS")
print("R2_R8_R2_PACKET_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R2_EVIDENCE_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R2_CANDIDATE_MANIFEST_SHA_REVIEW=PASS")
print("R2_R8_R2_EVIDENCE_FILE_COUNT=16")
print("R2_R8_R2_EVIDENCE_DIRECTORY_COUNT=3")
print(f"R2_R8_R2_EVIDENCE_FILE_MODE_DISTRIBUTION={dict(sorted(file_modes.items()))}")
print(
    "R2_R8_R2_EVIDENCE_DIRECTORY_MODE_DISTRIBUTION="
    f"{dict(sorted(directory_modes.items()))}"
)
print("R2_R8_R2_EVIDENCE_SYMLINK_COUNT=0")
print("R2_R8_R2_EVIDENCE_NONREGULAR_COUNT=0")
print("R2_R8_R2_EVIDENCE_OWNER_GROUP_REVIEW=PASS")
print("R2_R8_R2_EVIDENCE_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R2_EVIDENCE_MANIFEST_ENTRY_COUNT=15")
print("R2_R8_R2_EVIDENCE_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R8_R2_PACKET_MANIFEST_ENTRY_COUNT=13")
print("R2_R8_R2_PACKET_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R8_R2_CANDIDATE_DECLARED_FILE_COUNT=8")
print("R2_R8_R2_CANDIDATE_ACTUAL_FILE_COUNT=8")
print("R2_R8_R2_CANDIDATE_DIRECTORY_COUNT=0")
print("R2_R8_R2_CANDIDATE_PYC_FILE_COUNT=0")
print("R2_R8_R2_CANDIDATE_EXACT_FILE_SET_REVIEW=PASS")
print("R2_R8_R2_CANDIDATE_ARTIFACT_SHA_SIZE_REVIEW=PASS")
print("R2_R8_R2_VALIDATOR_LOG_REVIEW=PASS")
print("R2_R8_R2_NEGATIVE_TEST_COUNT=13")
print("R2_R8_R2_NEGATIVE_TEST_LOG_REVIEW=PASS")
print("R2_R8_R2_VERIFIER_BASH_N_LOG_REVIEW=PASS")
print("R2_R8_R2_FIXED_TARGET_PATH_REVIEW=PASS")
print("R2_R8_R2_FIXED_COMMAND_ARGV_REVIEW=PASS")
print("R2_R8_R2_APPROVAL_GATE_REVIEW=PASS")
print("R2_R8_R2_VERIFIER_STATIC_SAFETY_REVIEW=PASS")
print("R2_R7_SOURCE_FIXED_SHA_REVIEW=PASS")
print("R2_R8_R1_FAILED_EVIDENCE_FIXED_SHA_REVIEW=PASS")
print("R2_R8_R1_FAILED_EXACT_FILE_SET_STATE_REVIEW=PASS")
print("PROTECTED_SHA_REVIEW=PASS")
print("R2_R8_R2_CONSOLE_COMPLETION_BINDING_REVIEW=PASS")
print("R2_R8_R2_CONSOLE_EXIT_ZERO_MARKER_COUNT=1")
print("ROOT_READONLY_VERIFICATION_EXECUTED=false")
print("SUDO_EXECUTION_PERFORMED=false")
print("SUDOERS_CHANGED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print("EVIDENCE_SEAL_PERFORMED=false")
print("EVIDENCE_SEAL_STATUS=NOT_PERFORMED_CHMOD_NOT_AUTHORIZED")
print(
    "R2_R8_R2_HUMAN_REVIEW_DECISION="
    "APPROVE_CORRECTED_PACKET_WITH_ROOT_VERIFICATION_EXECUTION_HOLD"
)
print(
    "NEXT_GATE="
    "HUMAN_APPROVAL_FOR_3E_J_R2_R8_ROOT_READONLY_"
    "SUDOERS_DESTINATION_VERIFICATION_EXECUTION"
)
PY

  printf '\n===== FINAL HUMAN REVIEW MARKERS =====\n'

  echo "R2_R8_R2_RESULT_SHA_REVIEW=PASS"
  echo "R2_R8_R2_PACKET_MANIFEST_SHA_REVIEW=PASS"
  echo "R2_R8_R2_EVIDENCE_MANIFEST_SHA_REVIEW=PASS"
  echo "R2_R8_R2_CANDIDATE_EXACT_FILE_SET_REVIEW=PASS"
  echo "R2_R8_R2_PACKET_HUMAN_REVIEW=PASS"
  echo "ROOT_READONLY_VERIFICATION_EXECUTED=false"
  echo "SUDO_EXECUTION_PERFORMED=false"
  echo "SUDOERS_CHANGED=false"
  echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
  echo "FINAL_APPROVAL_TOKEN_CREATED=false"
  echo "APPROVAL_BINDING_CREATED=false"
  echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
  echo "EVIDENCE_SEAL_PERFORMED=false"
  echo "EVIDENCE_SEAL_STATUS=NOT_PERFORMED_CHMOD_NOT_AUTHORIZED"
  echo "R2_R8_R2_HUMAN_REVIEW_DECISION=APPROVE_CORRECTED_PACKET_WITH_ROOT_VERIFICATION_EXECUTION_HOLD"
  echo "NEXT_GATE=HUMAN_APPROVAL_FOR_3E_J_R2_R8_ROOT_READONLY_SUDOERS_DESTINATION_VERIFICATION_EXECUTION"

) 2>&1 | tee "$REVIEW_LOG"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_LOG"
