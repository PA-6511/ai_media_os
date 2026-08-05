#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
VISUDO_BIN="/usr/sbin/visudo"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

EXECUTION_PACKET_REL="${BASE_REL}/i2f3e-j-root-deployment-execution-packet-preparation-20260726T052028Z-529268"
EXECUTION_PACKET_ROOT="${REPO_ROOT}/${EXECUTION_PACKET_REL}"
PACKET_ROOT="${EXECUTION_PACKET_ROOT}/packet-snapshot"
CANDIDATE_ROOT="${PACKET_ROOT}/candidate-artifacts"
INPUT_ROOT="${PACKET_ROOT}/deployment-input-snapshot"
SOURCE_PACKET_INPUT="${INPUT_ROOT}/source-root-deployment-packet"
FINAL_INPUT="${INPUT_ROOT}/final-seal-evidence"
RUNNER_INPUT="${INPUT_ROOT}/runner-candidate"
LOG_ROOT="${PACKET_ROOT}/validation-logs"

SOURCE_PACKET_REL="${BASE_REL}/i2f3e-j-final-seal-acceptance-root-deployment-packet-preparation-20260726T045508Z-528388"
SOURCE_PACKET_ROOT="${REPO_ROOT}/${SOURCE_PACKET_REL}"

FINAL_SEAL_REL="${BASE_REL}/i2f3e-j-r2-r8-r3-r1-final-evidence-registration-and-seal-20260726T035208Z-527505"
FINAL_SEAL_ROOT="${REPO_ROOT}/${FINAL_SEAL_REL}"

RUNNER_SOURCE_REL="${BASE_REL}/i2f3e-j-r1-root-scan-late-exit-correction-blocked-no-execution-20260725T161929Z-515154/packet-snapshot/candidate-artifacts"
RUNNER_SOURCE_ROOT="${REPO_ROOT}/${RUNNER_SOURCE_REL}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_REVIEW_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -x "$VISUDO_BIN"
test -d "$EXECUTION_PACKET_ROOT"
test -d "$PACKET_ROOT"
test -d "$CANDIDATE_ROOT"
test -d "$INPUT_ROOT"
test -d "$SOURCE_PACKET_INPUT"
test -d "$FINAL_INPUT"
test -d "$RUNNER_INPUT"
test -d "$LOG_ROOT"
test -d "$SOURCE_PACKET_ROOT"
test -d "$FINAL_SEAL_ROOT"
test -d "$RUNNER_SOURCE_ROOT"

cd "$REPO_ROOT"

printf '\n===== EXECUTION PACKET FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
93152736eda119f41fd1d5aa5dcab670b618a5e6bdf14c0848345551b9b5f741  ${EXECUTION_PACKET_ROOT}/result.json
134a4a7d25e23661944047654b25e0041461f7fe796556e00db3953ad1b487ad  ${PACKET_ROOT}/packet-manifest.json
7bb5f4009de9e8bb50b44db3d7524897780fe19ad86f2bae3cb6e50187f805bd  ${CANDIDATE_ROOT}/candidate-manifest.json
61955ce7f7327d98fa3b0ab076291353619a0512d2c4d2a9753bd06209f37997  ${EXECUTION_PACKET_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== SOURCE ROOT DEPLOYMENT PACKET FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
07951222582d6dda8ae07bcef6cd920db0d7cbdf22b20b39e48593cf716f9e6f  ${SOURCE_PACKET_ROOT}/result.json
fae7a17137d4283d144bd3ac5352de80653adac6480c6db0e0eb776e6df3b267  ${SOURCE_PACKET_ROOT}/packet-snapshot/packet-manifest.json
10c5aa0b9e53bd6ed03c8a89ac99c6b87d7fc4ed00fe45dca7ccbe7939336748  ${SOURCE_PACKET_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
29dca2ef58e72b40cbec06581d86d28d49b5ccc0a1a239316eebc3c380159d9c  ${SOURCE_PACKET_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== FINAL SEAL SOURCE FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
c9d71a2969a2ddf2a710f9e45c60327e42b5257994d613477c0ee724694d3bba  ${FINAL_SEAL_ROOT}/result.json
700a572496fb3d3c61235da276fbe668afb1a8bdf576040885f6fb07eac502c2  ${FINAL_SEAL_ROOT}/packet-snapshot/packet-manifest.json
eef41d075309aba52f07f6d8d4d62a2f12f0d74bda01e353be969af9be5a8e0f  ${FINAL_SEAL_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
afaa189fb6d9565ade2a5826449cc859f65f0358946deae21aae4703f414631c  ${FINAL_SEAL_ROOT}/packet-snapshot/candidate-artifacts/r2-r8-r3-snapshot-manifest.json
0c674bd9a7ea654bec9acea38a41b03a990d8dbf52b63dea23bb2562662f6d20  ${FINAL_SEAL_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== RUNNER SOURCE FIXED SHA REVIEW =====\n'

sha256sum -c <<SHAS
0677a9a9479e209a6e1ee30fdcd07996b671737850b17e79b97987578a73ec7f  ${RUNNER_SOURCE_ROOT}/candidate-manifest.json
1ccdabcbf59d130c1010643f6444f71f3dd8ea9a1ccaa4b8bad111e098b3b052  ${RUNNER_SOURCE_ROOT}/one_shot_writer_freeze_backup_restart_runner.py
e989fb528110a4b7c482404fc5b024e2d4a8371a6d6cf901c2a940b8f4f83888  ${RUNNER_SOURCE_ROOT}/root_fd_metadata_helper.py
eaf5f28f3a924da93a4dc0dc6a15669c5546c784b4207074629282954c48e65f  ${RUNNER_SOURCE_ROOT}/validate_3e_j_runner_packet.py
3e46a59517699e7e4845f9e716bd7ca021ddf9a23714453afb784960d223238e  ${RUNNER_SOURCE_ROOT}/test_3e_j_runner_negative.py
261941dab03f577b0882836f000f9a0f06b255a6dbf85b78ad8b5e4a3b7682dd  ${RUNNER_SOURCE_ROOT}/runner-policy.json
2ff4a42b574c4fb89699cf92beb555b7c83772a381847facca1ae289a765c773  ${RUNNER_SOURCE_ROOT}/3e_j_operation_manual.md
SHAS

printf '\n===== EXECUTION PACKET HUMAN REVIEW =====\n'

set +e
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$EXECUTION_PACKET_ROOT" \
  "$PACKET_ROOT" \
  "$CANDIDATE_ROOT" \
  "$INPUT_ROOT" \
  "$SOURCE_PACKET_INPUT" \
  "$FINAL_INPUT" \
  "$RUNNER_INPUT" \
  "$LOG_ROOT" \
  "$SOURCE_PACKET_ROOT" \
  "$FINAL_SEAL_ROOT" \
  "$RUNNER_SOURCE_ROOT" \
  "$EXECUTION_PACKET_REL" \
  "$SOURCE_PACKET_REL" \
  "$FINAL_SEAL_REL" \
  "$RUNNER_SOURCE_REL" \
  "$VISUDO_BIN" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
evidence_root = Path(sys.argv[2]).resolve(strict=True)
packet_root = Path(sys.argv[3]).resolve(strict=True)
candidate_root = Path(sys.argv[4]).resolve(strict=True)
input_root = Path(sys.argv[5]).resolve(strict=True)
source_packet_input = Path(sys.argv[6]).resolve(strict=True)
final_input = Path(sys.argv[7]).resolve(strict=True)
runner_input = Path(sys.argv[8]).resolve(strict=True)
log_root = Path(sys.argv[9]).resolve(strict=True)
source_packet_root = Path(sys.argv[10]).resolve(strict=True)
final_seal_root = Path(sys.argv[11]).resolve(strict=True)
runner_source_root = Path(sys.argv[12]).resolve(strict=True)
evidence_relative = sys.argv[13]
source_packet_relative = sys.argv[14]
final_seal_relative = sys.argv[15]
runner_source_relative = sys.argv[16]
visudo_bin = Path(sys.argv[17]).resolve(strict=True)

PHASE = "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-EXECUTION-PACKET"
APPROVAL_TOKEN = "APPROVE_3E_J_ROOT_DEPLOYMENT_EXECUTION_ONCE"
APPROVAL_TOKEN_SHA = (
    "0ebc6d8dd465ed30d07d95dd48abf1ee"
    "194863efb9927ca174fa9d33e2a0eb4a"
)

PACKET_FIXED_SHA = {
    "result.json": (
        "93152736eda119f41fd1d5aa5dcab670"
        "b618a5e6bdf14c0848345551b9b5f741"
    ),
    "packet-snapshot/packet-manifest.json": (
        "134a4a7d25e23661944047654b25e004"
        "1461f7fe796556e00db3953ad1b487ad"
    ),
    "packet-snapshot/candidate-artifacts/candidate-manifest.json": (
        "7bb5f4009de9e8bb50b44db3d752489"
        "7780fe19ad86f2bae3cb6e50187f805bd"
    ),
    "evidence-manifest.txt": (
        "61955ce7f7327d98fa3b0ab076291353"
        "619a0512d2c4d2a9753bd06209f37997"
    ),
}

SOURCE_PACKET_MAP = {
    "result.json": "result.json",
    "packet-manifest.json": "packet-snapshot/packet-manifest.json",
    "candidate-manifest.json": (
        "packet-snapshot/candidate-artifacts/candidate-manifest.json"
    ),
    "evidence-manifest.txt": "evidence-manifest.txt",
}
SOURCE_PACKET_SHA = {
    "result.json": (
        "07951222582d6dda8ae07bcef6cd920d"
        "b0d7cbdf22b20b39e48593cf716f9e6f"
    ),
    "packet-manifest.json": (
        "fae7a17137d4283d144bd3ac5352de80"
        "653adac6480c6db0e0eb776e6df3b267"
    ),
    "candidate-manifest.json": (
        "10c5aa0b9e53bd6ed03c8a89ac99c6b8"
        "7d7fc4ed00fe45dca7ccbe7939336748"
    ),
    "evidence-manifest.txt": (
        "29dca2ef58e72b40cbec06581d86d28d"
        "49b5ccc0a1a239316eebc3c380159d9c"
    ),
}

FINAL_SEAL_MAP = {
    "result.json": "result.json",
    "packet-manifest.json": "packet-snapshot/packet-manifest.json",
    "candidate-manifest.json": (
        "packet-snapshot/candidate-artifacts/candidate-manifest.json"
    ),
    "snapshot-manifest.json": (
        "packet-snapshot/candidate-artifacts/"
        "r2-r8-r3-snapshot-manifest.json"
    ),
    "evidence-manifest.txt": "evidence-manifest.txt",
}
FINAL_SEAL_SHA = {
    "result.json": (
        "c9d71a2969a2ddf2a710f9e45c60327"
        "e42b5257994d613477c0ee724694d3bba"
    ),
    "packet-manifest.json": (
        "700a572496fb3d3c61235da276fbe668a"
        "fb1a8bdf576040885f6fb07eac502c2"
    ),
    "candidate-manifest.json": (
        "eef41d075309aba52f07f6d8d4d62a2f"
        "12f0d74bda01e353be969af9be5a8e0f"
    ),
    "snapshot-manifest.json": (
        "afaa189fb6d9565ade2a5826449cc859"
        "f65f0358946deae21aae4703f414631c"
    ),
    "evidence-manifest.txt": (
        "0c674bd9a7ea654bec9acea38a41b03a"
        "990d8dbf52b63dea23bb2562662f6d20"
    ),
}

RUNNER_SHA = {
    "candidate-manifest.json": (
        "0677a9a9479e209a6e1ee30fdcd07996"
        "b671737850b17e79b97987578a73ec7f"
    ),
    "one_shot_writer_freeze_backup_restart_runner.py": (
        "1ccdabcbf59d130c1010643f6444f71f"
        "3dd8ea9a1ccaa4b8bad111e098b3b052"
    ),
    "root_fd_metadata_helper.py": (
        "e989fb528110a4b7c482404fc5b024e2"
        "d4a8371a6d6cf901c2a940b8f4f83888"
    ),
    "validate_3e_j_runner_packet.py": (
        "eaf5f28f3a924da93a4dc0dc6a15669"
        "c5546c784b4207074629282954c48e65f"
    ),
    "test_3e_j_runner_negative.py": (
        "3e46a59517699e7e4845f9e716bd7ca0"
        "21ddf9a23714453afb784960d223238e"
    ),
    "runner-policy.json": (
        "261941dab03f577b0882836f000f9a0f0"
        "6b255a6dbf85b78ad8b5e4a3b7682dd"
    ),
    "3e_j_operation_manual.md": (
        "2ff4a42b574c4fb89699cf92beb555b7"
        "c83772a381847facca1ae289a765c773"
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
    "execution-packet-policy.json",
    "source-binding-contract.json",
    "approval-binding-contract.json",
    "root-deployment-transaction-contract.json",
    "execution-result-schema.json",
    "ai-media-os-3e-j-root-helper.sudoers",
    "root_deployment_execution_once.py",
    "blocked_root_deployment_execution_entrypoint.py",
    "validate_root_deployment_execution_packet.py",
    "test_root_deployment_execution_packet_negative.py",
    "root_deployment_execution_operation_manual.md",
}

EXPECTED_SOURCE_PACKET_INPUT = set(SOURCE_PACKET_SHA)
EXPECTED_FINAL_INPUT = set(FINAL_SEAL_SHA)
EXPECTED_RUNNER_INPUT = set(RUNNER_SHA)

EXPECTED_INPUT_FILES = {
    *(f"source-root-deployment-packet/{name}" for name in EXPECTED_SOURCE_PACKET_INPUT),
    *(f"final-seal-evidence/{name}" for name in EXPECTED_FINAL_INPUT),
    *(f"runner-candidate/{name}" for name in EXPECTED_RUNNER_INPUT),
}
EXPECTED_INPUT_DIRS = {
    "source-root-deployment-packet",
    "final-seal-evidence",
    "runner-candidate",
}

EXPECTED_LOG_FILES = {
    "python-compile.log",
    "validator.log",
    "negative-tests.log",
    "visudo.log",
}

EXPECTED_PACKET_FILES = {
    "packet-manifest.json",
    "human-approval-verbatim.txt",
    *(f"candidate-artifacts/{name}" for name in EXPECTED_CANDIDATE_FILES),
    *(f"deployment-input-snapshot/{name}" for name in EXPECTED_INPUT_FILES),
    *(f"validation-logs/{name}" for name in EXPECTED_LOG_FILES),
}

EXPECTED_PACKET_DIRS = {
    "candidate-artifacts",
    "deployment-input-snapshot",
    *(f"deployment-input-snapshot/{name}" for name in EXPECTED_INPUT_DIRS),
    "validation-logs",
}

EXPECTED_EVIDENCE_FILES = {
    "result.json",
    "evidence-manifest.txt",
    *(f"packet-snapshot/{name}" for name in EXPECTED_PACKET_FILES),
}

EXPECTED_EVIDENCE_DIRS = {
    "packet-snapshot",
    *(f"packet-snapshot/{name}" for name in EXPECTED_PACKET_DIRS),
}

EXPECTED_REQUIRED_BINDING_FIELDS = [
    "schema_version",
    "approved",
    "approval_token_sha256",
    "execution_packet_evidence_manifest_sha256",
    "execution_wrapper_sha256",
    "source_root_deployment_packet_result_sha256",
    "approved_at_utc",
    "expires_at_utc",
    "max_execution_attempts",
]

EXPECTED_PARTIAL_FAILURE_STATES = [
    "NO_MUTATION_PREFLIGHT_FAILURE",
    "GUARD_CREATED_NO_PRODUCTION_MUTATION",
    "PARENT_CREATED_STAGE_NOT_CREATED",
    "STAGING_CREATED_NOT_PROMOTED",
    "DEPLOYMENT_ROOT_PROMOTED_SUDOERS_NOT_INSTALLED",
    "SUDOERS_INSTALLED_POSTCHECK_FAILED",
    "ROLLBACK_COMPLETE_HUMAN_REVIEW_REQUIRED",
    "ROLLBACK_INCOMPLETE_EMERGENCY_HOLD",
    "SUCCESS_HUMAN_REVIEW_REQUIRED",
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

def require_regular(path: Path, label: str) -> os.stat_result:
    item = path.lstat()
    require(stat.S_ISREG(item.st_mode), f"{label}_NOT_REGULAR")
    require(not stat.S_ISLNK(item.st_mode), f"{label}_SYMLINK")
    return item

def scan(root: Path) -> tuple[set[str], set[str], int, int]:
    item = root.lstat()
    require(stat.S_ISDIR(item.st_mode), f"ROOT_NOT_DIRECTORY:{root}")
    require(not stat.S_ISLNK(item.st_mode), f"ROOT_SYMLINK:{root}")
    files: set[str] = set()
    dirs: set[str] = set()
    links = 0
    other = 0
    for path in sorted(root.rglob("*")):
        entry = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(entry.st_mode):
            links += 1
        elif stat.S_ISREG(entry.st_mode):
            files.add(relative)
        elif stat.S_ISDIR(entry.st_mode):
            dirs.add(relative)
        else:
            other += 1
    return files, dirs, links, other

def tree_identity(root: Path) -> dict[str, tuple[Any, ...]]:
    files, dirs, links, other = scan(root)
    require(links == 0, f"IDENTITY_SYMLINK:{root}")
    require(other == 0, f"IDENTITY_NONREGULAR:{root}")
    identity: dict[str, tuple[Any, ...]] = {}
    root_item = root.lstat()
    identity["./"] = (
        "DIRECTORY",
        stat.S_IMODE(root_item.st_mode),
        root_item.st_uid,
        root_item.st_gid,
    )
    for relative in sorted(dirs):
        entry = (root / relative).lstat()
        identity[relative + "/"] = (
            "DIRECTORY",
            stat.S_IMODE(entry.st_mode),
            entry.st_uid,
            entry.st_gid,
        )
    for relative in sorted(files):
        path = root / relative
        entry = path.lstat()
        identity[relative] = (
            sha256(path),
            entry.st_size,
            stat.S_IMODE(entry.st_mode),
            entry.st_uid,
            entry.st_gid,
        )
    return identity

def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        require("  " in line, "MANIFEST_LINE_FORMAT")
        digest, relative = line.split("  ", 1)
        require(
            re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            f"MANIFEST_DIGEST:{relative}",
        )
        require(relative not in entries, f"MANIFEST_DUPLICATE:{relative}")
        entries[relative] = digest
    return entries

# Fixed path binding.
require(
    evidence_root.relative_to(repo_root).as_posix() == evidence_relative,
    "EVIDENCE_ROOT_BINDING",
)
require(
    source_packet_root.relative_to(repo_root).as_posix()
    == source_packet_relative,
    "SOURCE_PACKET_ROOT_BINDING",
)
require(
    final_seal_root.relative_to(repo_root).as_posix()
    == final_seal_relative,
    "FINAL_SEAL_ROOT_BINDING",
)
require(
    runner_source_root.relative_to(repo_root).as_posix()
    == runner_source_relative,
    "RUNNER_SOURCE_ROOT_BINDING",
)

# Fixed SHA review.
for relative, expected in PACKET_FIXED_SHA.items():
    path = evidence_root / relative
    require_regular(path, f"PACKET_FIXED:{relative}")
    require(sha256(path) == expected, f"PACKET_FIXED_SHA:{relative}")

for name, relative in SOURCE_PACKET_MAP.items():
    path = source_packet_root / relative
    require_regular(path, f"SOURCE_PACKET:{name}")
    require(sha256(path) == SOURCE_PACKET_SHA[name], f"SOURCE_PACKET_SHA:{name}")

for name, relative in FINAL_SEAL_MAP.items():
    path = final_seal_root / relative
    require_regular(path, f"FINAL_SEAL:{name}")
    require(sha256(path) == FINAL_SEAL_SHA[name], f"FINAL_SEAL_SHA:{name}")

for name, expected in RUNNER_SHA.items():
    path = runner_source_root / name
    require_regular(path, f"RUNNER_SOURCE:{name}")
    require(sha256(path) == expected, f"RUNNER_SOURCE_SHA:{name}")

# Identities before review runtime checks.
evidence_identity_before = tree_identity(evidence_root)
source_packet_identity_before = tree_identity(source_packet_root)
final_seal_identity_before = tree_identity(final_seal_root)
runner_source_identity_before = tree_identity(runner_source_root)

# Exact sets and counts.
evidence_files, evidence_dirs, evidence_links, evidence_other = scan(evidence_root)
require(evidence_files == EXPECTED_EVIDENCE_FILES, "EVIDENCE_EXACT_FILE_SET")
require(evidence_dirs == EXPECTED_EVIDENCE_DIRS, "EVIDENCE_EXACT_DIR_SET")
require(len(evidence_files) == 36, "EVIDENCE_FILE_COUNT")
require(len(evidence_dirs) == 7, "EVIDENCE_DIR_COUNT")
require(evidence_links == 0, "EVIDENCE_SYMLINK_COUNT")
require(evidence_other == 0, "EVIDENCE_NONREGULAR_COUNT")

packet_files, packet_dirs, packet_links, packet_other = scan(packet_root)
require(packet_files == EXPECTED_PACKET_FILES, "PACKET_EXACT_FILE_SET")
require(packet_dirs == EXPECTED_PACKET_DIRS, "PACKET_EXACT_DIR_SET")
require(len(packet_files) == 34, "PACKET_FILE_COUNT")
require(len(packet_dirs) == 6, "PACKET_DIR_COUNT")
require(packet_links == 0, "PACKET_SYMLINK_COUNT")
require(packet_other == 0, "PACKET_NONREGULAR_COUNT")

candidate_files, candidate_dirs, candidate_links, candidate_other = scan(
    candidate_root
)
require(
    candidate_files == EXPECTED_CANDIDATE_FILES,
    "CANDIDATE_EXACT_FILE_SET",
)
require(len(candidate_files) == 12, "CANDIDATE_FILE_COUNT")
require(not candidate_dirs, "CANDIDATE_DIR_COUNT")
require(candidate_links == 0, "CANDIDATE_SYMLINK_COUNT")
require(candidate_other == 0, "CANDIDATE_NONREGULAR_COUNT")

input_files, input_dirs, input_links, input_other = scan(input_root)
require(input_files == EXPECTED_INPUT_FILES, "INPUT_EXACT_FILE_SET")
require(input_dirs == EXPECTED_INPUT_DIRS, "INPUT_EXACT_DIR_SET")
require(len(input_files) == 16, "INPUT_FILE_COUNT")
require(len(input_dirs) == 3, "INPUT_DIR_COUNT")
require(input_links == 0, "INPUT_SYMLINK_COUNT")
require(input_other == 0, "INPUT_NONREGULAR_COUNT")

log_files, log_dirs, log_links, log_other = scan(log_root)
require(log_files == EXPECTED_LOG_FILES, "LOG_EXACT_FILE_SET")
require(not log_dirs, "LOG_DIR_COUNT")
require(log_links == 0, "LOG_SYMLINK_COUNT")
require(log_other == 0, "LOG_NONREGULAR_COUNT")

# 16 input snapshots: source, byte, size, and SHA equivalence.
for name, relative in SOURCE_PACKET_MAP.items():
    source = source_packet_root / relative
    snapshot = source_packet_input / name
    require(source.read_bytes() == snapshot.read_bytes(), f"SOURCE_INPUT_BYTES:{name}")
    require(source.stat().st_size == snapshot.stat().st_size, f"SOURCE_INPUT_SIZE:{name}")
    require(sha256(snapshot) == SOURCE_PACKET_SHA[name], f"SOURCE_INPUT_SHA:{name}")

for name, relative in FINAL_SEAL_MAP.items():
    source = final_seal_root / relative
    snapshot = final_input / name
    require(source.read_bytes() == snapshot.read_bytes(), f"FINAL_INPUT_BYTES:{name}")
    require(source.stat().st_size == snapshot.stat().st_size, f"FINAL_INPUT_SIZE:{name}")
    require(sha256(snapshot) == FINAL_SEAL_SHA[name], f"FINAL_INPUT_SHA:{name}")

for name, expected in RUNNER_SHA.items():
    source = runner_source_root / name
    snapshot = runner_input / name
    require(source.read_bytes() == snapshot.read_bytes(), f"RUNNER_INPUT_BYTES:{name}")
    require(source.stat().st_size == snapshot.stat().st_size, f"RUNNER_INPUT_SIZE:{name}")
    require(sha256(snapshot) == expected, f"RUNNER_INPUT_SHA:{name}")

# Candidate manifest.
candidate_manifest = load_json(candidate_root / "candidate-manifest.json")
require(candidate_manifest["phase"] == PHASE, "CANDIDATE_PHASE")
require(
    candidate_manifest["status"]
    == "ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARED_NO_EXECUTION",
    "CANDIDATE_STATUS",
)
require(candidate_manifest["total_file_count"] == 12, "CANDIDATE_TOTAL")
require(
    candidate_manifest["file_count_excluding_manifest"] == 11,
    "CANDIDATE_EXCLUDING",
)
require(
    candidate_manifest["deployment_input_snapshot_file_count"] == 16,
    "CANDIDATE_INPUT_COUNT",
)
require(candidate_manifest["negative_test_count"] == 30, "CANDIDATE_NEGATIVE_COUNT")
require(
    candidate_manifest["root_deployment_execution_allowed"] is False,
    "CANDIDATE_EXECUTION_ALLOWED",
)
require(
    candidate_manifest["sudoers_installation_allowed"] is False,
    "CANDIDATE_SUDOERS_ALLOWED",
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
for item in candidate_manifest["files"]:
    path = candidate_root / item["name"]
    require(sha256(path) == item["sha256"], f"CANDIDATE_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"CANDIDATE_SIZE:{item['name']}",
    )

# Policy and source binding.
policy = load_json(candidate_root / "execution-packet-policy.json")
require(policy["phase"] == PHASE, "POLICY_PHASE")
require(
    policy["status"]
    == "ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARED_NO_EXECUTION",
    "POLICY_STATUS",
)
require(policy["packet_preparation_only"] is True, "POLICY_PACKET_ONLY")
for key in (
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "production_file_creation_allowed",
    "production_directory_creation_allowed",
    "root_helper_execution_allowed",
    "runner_execution_allowed",
    "blocked_entrypoint_execution_allowed",
    "one_shot_deployment_guard_creation_allowed",
    "root_readonly_verification_reexecution_allowed",
    "one_shot_guard_change_allowed",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_production_token_created",
    "approval_binding_created",
):
    require(policy[key] is False, f"POLICY_FALSE:{key}")
require(
    policy["future_execution_requires_explicit_approval_binding"] is True,
    "POLICY_FUTURE_BINDING",
)
require(policy["future_execution_max_attempts"] == 1, "POLICY_MAX_ATTEMPTS")
require(policy["future_automatic_retry_allowed"] is False, "POLICY_RETRY")
require(policy["candidate_artifact_count"] == 12, "POLICY_CANDIDATE_COUNT")
require(
    policy["deployment_input_snapshot_file_count"] == 16,
    "POLICY_INPUT_COUNT",
)
require(policy["negative_test_count"] == 30, "POLICY_NEGATIVE_COUNT")
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

source_contract = load_json(candidate_root / "source-binding-contract.json")
require(source_contract["phase"] == PHASE, "SOURCE_CONTRACT_PHASE")
require(
    source_contract["source_root_deployment_packet"]["fixed_file_count"] == 4,
    "SOURCE_CONTRACT_PACKET_COUNT",
)
require(
    source_contract["final_seal_identity"]["fixed_file_count"] == 5,
    "SOURCE_CONTRACT_FINAL_COUNT",
)
require(
    source_contract["runner_candidate"]["fixed_file_count"] == 7,
    "SOURCE_CONTRACT_RUNNER_COUNT",
)
require(
    source_contract["source_root_deployment_packet"]["fixed_sha256"]
    == SOURCE_PACKET_SHA,
    "SOURCE_CONTRACT_PACKET_SHA",
)
require(
    source_contract["final_seal_identity"]["fixed_sha256"]
    == FINAL_SEAL_SHA,
    "SOURCE_CONTRACT_FINAL_SHA",
)
require(
    source_contract["runner_candidate"]["fixed_sha256"] == RUNNER_SHA,
    "SOURCE_CONTRACT_RUNNER_SHA",
)
require(len(source_contract["deployment_payload"]) == 6, "SOURCE_PAYLOAD_COUNT")
require(source_contract["owner"] == "root", "SOURCE_OWNER")
require(source_contract["group"] == "root", "SOURCE_GROUP")
require(source_contract["directory_mode"] == "0755", "SOURCE_DIR_MODE")
require(
    source_contract["source_mutation_allowed"] is False,
    "SOURCE_MUTATION_ALLOWED",
)

# Approval binding contract.
binding = load_json(candidate_root / "approval-binding-contract.json")
require(binding["phase"] == PHASE, "BINDING_PHASE")
require(
    binding["binding_path"]
    == "/var/lib/ai-media-os/approvals/3e-j-root-deployment-v1.json",
    "BINDING_PATH",
)
require(binding["binding_parent_required_preexisting"] is True, "BINDING_PARENT")
require(binding["binding_owner"] == "root", "BINDING_OWNER")
require(binding["binding_group"] == "root", "BINDING_GROUP")
require(binding["binding_mode"] == "0400", "BINDING_MODE")
require(
    binding["binding_regular_file_required"] is True,
    "BINDING_REGULAR",
)
require(binding["binding_symlink_forbidden"] is True, "BINDING_SYMLINK")
require(
    binding["binding_creation_allowed_current_phase"] is False,
    "BINDING_CURRENT_CREATION",
)
require(
    binding["required_fields"] == EXPECTED_REQUIRED_BINDING_FIELDS,
    "BINDING_REQUIRED_FIELDS",
)
required_values = binding["required_values"]
require(required_values["schema_version"] == "1.0", "BINDING_SCHEMA")
require(required_values["approved"] is True, "BINDING_APPROVED")
require(
    required_values["approval_token_sha256"] == APPROVAL_TOKEN_SHA,
    "BINDING_TOKEN_SHA",
)
require(
    required_values["source_root_deployment_packet_result_sha256"]
    == SOURCE_PACKET_SHA["result.json"],
    "BINDING_SOURCE_PACKET_RESULT",
)
require(
    required_values["max_execution_attempts"] == 1,
    "BINDING_MAX_ATTEMPTS",
)
require(binding["expiration_required"] is True, "BINDING_EXPIRATION")
require(
    binding["future_binding_requires_separate_human_approval"] is True,
    "BINDING_SEPARATE_APPROVAL",
)

# Transaction contract.
transaction = load_json(
    candidate_root / "root-deployment-transaction-contract.json"
)
require(transaction["phase"] == PHASE, "TRANSACTION_PHASE")
future = transaction["future_execution"]
require(future["root_uid_required"] == 0, "FUTURE_ROOT_UID")
require(future["arbitrary_arguments_allowed"] is False, "FUTURE_ARGS")
require(future["approval_binding_required"] is True, "FUTURE_BINDING")
require(
    future["guard_path"]
    == "/var/lib/ai-media-os/guards/3e-j-root-deployment-v1.guard",
    "FUTURE_GUARD_PATH",
)
require(
    future["guard_parent_required_preexisting"] is True,
    "FUTURE_GUARD_PARENT",
)
require(future["guard_exclusive_create"] is True, "FUTURE_GUARD_EXCLUSIVE")
require(future["guard_mode"] == "0600", "FUTURE_GUARD_MODE")
require(future["guard_never_removed"] is True, "FUTURE_GUARD_NEVER_REMOVED")
require(future["max_execution_attempts"] == 1, "FUTURE_MAX_ATTEMPTS")
require(future["automatic_retry_allowed"] is False, "FUTURE_RETRY")

preflight = transaction["preflight"]
require(
    preflight["deployment_root"] == "/opt/ai-media-os/3e-j",
    "PREFLIGHT_DEPLOYMENT_ROOT",
)
require(
    preflight["deployment_root_must_be_absent"] is True,
    "PREFLIGHT_ROOT_ABSENT",
)
require(
    preflight["sudoers_target"]
    == "/etc/sudoers.d/ai-media-os-3e-j-root-helper",
    "PREFLIGHT_SUDOERS_TARGET",
)
require(
    preflight["sudoers_target_must_be_absent"] is True,
    "PREFLIGHT_SUDOERS_ABSENT",
)
require(
    preflight["parent_symlink_rejection"] is True,
    "PREFLIGHT_PARENT_SYMLINK",
)
require(
    preflight["target_symlink_rejection"] is True,
    "PREFLIGHT_TARGET_SYMLINK",
)
require(
    preflight["source_fixed_sha_revalidation"] is True,
    "PREFLIGHT_SOURCE_SHA",
)
require(
    preflight["protected_sha_revalidation"] is True,
    "PREFLIGHT_PROTECTED_SHA",
)
require(
    preflight["production_release_must_remain_hold"] is True,
    "PREFLIGHT_RELEASE_HOLD",
)
require(preflight["visudo_path"] == "/usr/sbin/visudo", "PREFLIGHT_VISUDO")
require(preflight["visudo_required"] is True, "PREFLIGHT_VISUDO_REQUIRED")

staging = transaction["staging"]
require(staging["parent"] == "/opt/ai-media-os", "STAGING_PARENT")
require(
    staging["parent_may_be_exclusive_created"] is True,
    "STAGING_PARENT_CREATE",
)
require(staging["parent_mode"] == "0755", "STAGING_PARENT_MODE")
require(staging["stage_prefix"] == ".3e-j-stage-", "STAGING_PREFIX")
require(staging["exclusive_create"] is True, "STAGING_EXCLUSIVE")
require(staging["mode"] == "0700", "STAGING_MODE")
require(
    staging["same_filesystem_atomic_rename"] is True,
    "STAGING_ATOMIC_RENAME",
)
require(staging["overwrite_allowed"] is False, "STAGING_OVERWRITE")

promotion = transaction["promotion"]
require(promotion["target"] == "/opt/ai-media-os/3e-j", "PROMOTION_TARGET")
require(
    promotion["atomic_rename_required"] is True,
    "PROMOTION_ATOMIC_RENAME",
)
require(promotion["overwrite_allowed"] is False, "PROMOTION_OVERWRITE")
require(promotion["owner"] == "root", "PROMOTION_OWNER")
require(promotion["group"] == "root", "PROMOTION_GROUP")
require(promotion["directory_mode"] == "0755", "PROMOTION_MODE")

sudoers_install = transaction["sudoers_installation"]
require(
    sudoers_install["target"]
    == "/etc/sudoers.d/ai-media-os-3e-j-root-helper",
    "SUDOERS_TARGET",
)
require(sudoers_install["exclusive_create"] is True, "SUDOERS_EXCLUSIVE")
require(sudoers_install["overwrite_allowed"] is False, "SUDOERS_OVERWRITE")
require(sudoers_install["owner"] == "root", "SUDOERS_OWNER")
require(sudoers_install["group"] == "root", "SUDOERS_GROUP")
require(sudoers_install["mode"] == "0440", "SUDOERS_MODE")
require(
    sudoers_install["staged_visudo_validation_required"] is True,
    "SUDOERS_VISUDO_REQUIRED",
)

rollback = transaction["rollback"]
require(
    rollback["scope"] == "CURRENT_TRANSACTION_CREATED_PATHS_ONLY",
    "ROLLBACK_SCOPE",
)
require(
    rollback["existing_path_removal_allowed"] is False,
    "ROLLBACK_EXISTING_PATH",
)
require(
    rollback["source_evidence_mutation_allowed"] is False,
    "ROLLBACK_SOURCE_MUTATION",
)
require(
    rollback["automatic_retry_allowed"] is False,
    "ROLLBACK_AUTOMATIC_RETRY",
)
require(rollback["max_execution_attempts"] == 1, "ROLLBACK_MAX_ATTEMPTS")
require(rollback["guard_removal_allowed"] is False, "ROLLBACK_GUARD")
require(
    rollback["sudoers_removal_requires_created_by_transaction"] is True,
    "ROLLBACK_SUDOERS_TRANSACTION",
)
require(
    rollback["sudoers_removal_requires_inode_device_match"] is True,
    "ROLLBACK_SUDOERS_INODE",
)
require(
    rollback["sudoers_removal_requires_content_sha_match"] is True,
    "ROLLBACK_SUDOERS_SHA",
)
require(
    rollback["deployment_root_removal_requires_created_by_transaction"]
    is True,
    "ROLLBACK_ROOT_TRANSACTION",
)
require(
    rollback["deployment_root_removal_requires_inode_device_match"] is True,
    "ROLLBACK_ROOT_INODE",
)
require(
    rollback["deployment_root_removal_requires_tree_identity_match"] is True,
    "ROLLBACK_ROOT_TREE",
)
require(
    rollback["stage_removal_requires_created_by_transaction"] is True,
    "ROLLBACK_STAGE_TRANSACTION",
)
require(
    rollback["stage_removal_requires_inode_device_match"] is True,
    "ROLLBACK_STAGE_INODE",
)
require(
    rollback["created_parent_removal_requires_empty_and_inode_device_match"]
    is True,
    "ROLLBACK_PARENT_IDENTITY",
)
require(
    rollback["rollback_incomplete_action"]
    == "EMERGENCY_HOLD_AND_HUMAN_REVIEW",
    "ROLLBACK_INCOMPLETE_ACTION",
)
require(rollback["sigkill_allowed"] is False, "ROLLBACK_SIGKILL")
require(
    rollback["process_group_signal_allowed"] is False,
    "ROLLBACK_PROCESS_GROUP",
)
require(
    transaction["partial_failure_states"] == EXPECTED_PARTIAL_FAILURE_STATES,
    "PARTIAL_FAILURE_STATES",
)
require(transaction["current_phase_execution"] is False, "TRANSACTION_CURRENT")

# Result schema.
result_schema = load_json(candidate_root / "execution-result-schema.json")
require(result_schema["phase"] == PHASE, "RESULT_SCHEMA_PHASE")
require(
    result_schema["fixed_values"]["attempt_count"] == 1,
    "RESULT_SCHEMA_ATTEMPT",
)
require(
    result_schema["fixed_values"]["root_helper_executed"] is False,
    "RESULT_SCHEMA_HELPER",
)
require(
    result_schema["fixed_values"]["runner_executed"] is False,
    "RESULT_SCHEMA_RUNNER",
)
require(
    result_schema["fixed_values"]["production_release_decision"] == "HOLD",
    "RESULT_SCHEMA_RELEASE",
)
require(
    result_schema["console_only_current_design"] is True,
    "RESULT_SCHEMA_CONSOLE",
)
require(
    result_schema["automatic_production_release"] is False,
    "RESULT_SCHEMA_AUTO_RELEASE",
)

# Candidate sudoers.
sudoers_path = candidate_root / "ai-media-os-3e-j-root-helper.sudoers"
sudoers_text = sudoers_path.read_text(encoding="utf-8")
require("NOPASSWD:NOSETENV" in sudoers_text, "SUDOERS_TAGS")
require("*" not in sudoers_text, "SUDOERS_WILDCARD")
require("/bin/sh" not in sudoers_text, "SUDOERS_SHELL")
require(
    sha256(sudoers_path) == sudoers_install["content_sha256"],
    "SUDOERS_CONTENT_SHA",
)

# Blocked entrypoint static review only.
blocked_path = candidate_root / "blocked_root_deployment_execution_entrypoint.py"
blocked_source = blocked_path.read_text(encoding="utf-8")
compile(blocked_source, str(blocked_path), "exec")
for marker in (
    "ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARATION_ONLY=true",
    "ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false",
    "SUDOERS_INSTALLATION_ALLOWED=false",
    "PRODUCTION_FILE_CREATION_ALLOWED=false",
    "PRODUCTION_DIRECTORY_CREATION_ALLOWED=false",
    "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "return 2",
):
    require(marker in blocked_source, f"BLOCKED_MARKER:{marker}")
for forbidden in (
    "subprocess",
    "shutil",
    "socket",
    "sqlite3",
    "os.",
):
    require(forbidden not in blocked_source, f"BLOCKED_FORBIDDEN:{forbidden}")

# Future execution wrapper: compile and expected controls.
wrapper_path = candidate_root / "root_deployment_execution_once.py"
wrapper_source = wrapper_path.read_text(encoding="utf-8")
compile(wrapper_source, str(wrapper_path), "exec")
for marker in (
    "ROOT_UID_REQUIRED",
    "ARBITRARY_ARGUMENTS_FORBIDDEN",
    "BINDING_EXACT_KEYS",
    "BINDING_APPROVAL_TOKEN",
    "BINDING_EVIDENCE_MANIFEST",
    "BINDING_WRAPPER_SHA",
    "BINDING_SOURCE_PACKET",
    "BINDING_EXPIRED_OR_NOT_YET_VALID",
    "ONE_SHOT_GUARD_EXISTS",
    "DEPLOYMENT_ROOT_EXISTS",
    "SUDOERS_TARGET_EXISTS",
    "VISUDO_VALIDATION_FAILED",
    "CURRENT_TRANSACTION_CREATED_PATHS_ONLY",
    "ROLLBACK_COMPLETE_HUMAN_REVIEW_REQUIRED",
    "ROLLBACK_INCOMPLETE_EMERGENCY_HOLD",
    "SUCCESS_HUMAN_REVIEW_REQUIRED",
):
    require(marker in wrapper_source, f"WRAPPER_MARKER:{marker}")
require("shell=True" not in wrapper_source, "WRAPPER_SHELL_TRUE")
require("SIGKILL" not in wrapper_source, "WRAPPER_SIGKILL")
require("killpg" not in wrapper_source, "WRAPPER_KILLPG")
require("sqlite3" not in wrapper_source, "WRAPPER_SQLITE")
require("socket" not in wrapper_source, "WRAPPER_SOCKET")
require(
    "root_fd_metadata_helper.py self-check" not in wrapper_source,
    "WRAPPER_HELPER_EXECUTION",
)
require(
    "[str(VISUDO), \"-cf\", str(staged_sudoers)]" in wrapper_source,
    "WRAPPER_VISUDO_ARGV",
)
require(
    "while written < len(view):" in wrapper_source,
    "WRAPPER_PARTIAL_WRITE_LOOP",
)

# Packet and Evidence manifests.
packet_manifest = load_json(packet_root / "packet-manifest.json")
require(packet_manifest["phase"] == PHASE, "PACKET_PHASE")
require(
    packet_manifest["status"]
    == "ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARED_NO_EXECUTION",
    "PACKET_STATUS",
)
require(
    packet_manifest["packet_file_count_excluding_manifest"] == 33,
    "PACKET_MANIFEST_COUNT",
)
require(len(packet_manifest["packet_files"]) == 33, "PACKET_MANIFEST_LIST")
require(
    {item["name"] for item in packet_manifest["packet_files"]}
    == EXPECTED_PACKET_FILES - {"packet-manifest.json"},
    "PACKET_MANIFEST_EXACT_SET",
)
for item in packet_manifest["packet_files"]:
    path = packet_root / item["name"]
    require(sha256(path) == item["sha256"], f"PACKET_SHA:{item['name']}")
    require(
        path.stat().st_size == item["size_bytes"],
        f"PACKET_SIZE:{item['name']}",
    )

evidence_manifest = parse_manifest(evidence_root / "evidence-manifest.txt")
require(len(evidence_manifest) == 35, "EVIDENCE_MANIFEST_COUNT")
require(
    set(evidence_manifest)
    == EXPECTED_EVIDENCE_FILES - {"evidence-manifest.txt"},
    "EVIDENCE_MANIFEST_EXACT_SET",
)
for relative, digest in evidence_manifest.items():
    require(
        sha256(evidence_root / relative) == digest,
        f"EVIDENCE_SHA:{relative}",
    )

# Result record.
result = load_json(evidence_root / "result.json")
require(result["phase"] == PHASE, "RESULT_PHASE")
require(
    result["result"]
    == (
        "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_EXECUTION_"
        "PACKET_PREPARED_NO_EXECUTION"
    ),
    "RESULT_VALUE",
)
require(result["evidence_root"] == evidence_relative, "RESULT_EVIDENCE_ROOT")
require(
    result["source_packet_human_review"] == "PASS",
    "RESULT_SOURCE_HUMAN_REVIEW",
)
require(
    result["source_packet_human_review_decision"]
    == "APPROVE_ROOT_DEPLOYMENT_PACKET_WITH_EXECUTION_HOLD",
    "RESULT_SOURCE_DECISION",
)
require(
    result["source_packet_fixed_sha_review"] == "PASS",
    "RESULT_SOURCE_SHA",
)
require(result["source_packet_unchanged"] is True, "RESULT_SOURCE_UNCHANGED")
require(result["evidence_file_count"] == 36, "RESULT_EVIDENCE_COUNT")
require(
    result["evidence_directory_count_excluding_root"] == 7,
    "RESULT_EVIDENCE_DIR_COUNT",
)
require(result["packet_file_count"] == 34, "RESULT_PACKET_COUNT")
require(result["packet_directory_count"] == 6, "RESULT_PACKET_DIR_COUNT")
require(
    result["packet_manifest_entry_count"] == 33,
    "RESULT_PACKET_MANIFEST_COUNT",
)
require(
    result["evidence_manifest_entry_count"] == 35,
    "RESULT_EVIDENCE_MANIFEST_COUNT",
)
require(result["candidate_artifact_count"] == 12, "RESULT_CANDIDATE_COUNT")
require(
    result["deployment_input_snapshot_file_count"] == 16,
    "RESULT_INPUT_COUNT",
)
require(
    result["source_root_deployment_packet_identity_count"] == 4,
    "RESULT_SOURCE_IDENTITY_COUNT",
)
require(
    result["final_seal_identity_file_count"] == 5,
    "RESULT_FINAL_IDENTITY_COUNT",
)
require(
    result["runner_candidate_file_count"] == 7,
    "RESULT_RUNNER_COUNT",
)
require(result["validation_log_count"] == 4, "RESULT_LOG_COUNT")
require(result["negative_test_count"] == 30, "RESULT_NEGATIVE_COUNT")
require(result["validator"] == "PASS", "RESULT_VALIDATOR")
require(result["negative_tests"] == "PASS", "RESULT_NEGATIVE")
require(
    result["visudo_static_validation"] == "PASS",
    "RESULT_VISUDO",
)
require(result["packet_preparation_only"] is True, "RESULT_PACKET_ONLY")
for key in (
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "production_file_creation_allowed",
    "production_directory_creation_allowed",
    "root_helper_execution_allowed",
    "runner_execution_allowed",
    "one_shot_deployment_guard_created",
    "approval_binding_created",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "final_production_token_created",
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

# Static logs.
compile_log = (log_root / "python-compile.log").read_text(encoding="utf-8")
require(
    compile_log.splitlines()
    == [
        "PYTHON_COMPILE_PASS=root_deployment_execution_once.py",
        "PYTHON_COMPILE_PASS=blocked_root_deployment_execution_entrypoint.py",
        "PYTHON_COMPILE_PASS=validate_root_deployment_execution_packet.py",
        "PYTHON_COMPILE_PASS=test_root_deployment_execution_packet_negative.py",
    ],
    "COMPILE_LOG",
)
validator_log = (log_root / "validator.log").read_text(encoding="utf-8")
require(
    validator_log.splitlines()
    == [
        "VALIDATOR_SOURCE_COMPILE=PASS",
        "FINAL_RUNTIME_VALIDATOR_REQUIRED=true",
        "PACKET_PREPARATION_ONLY=true",
    ],
    "VALIDATOR_LOG",
)
negative_log = (log_root / "negative-tests.log").read_text(encoding="utf-8")
require(
    negative_log.splitlines()
    == [
        "NEGATIVE_TEST_SOURCE_COMPILE=PASS",
        "FINAL_RUNTIME_NEGATIVE_TEST_COUNT_REQUIRED=30",
        "PACKET_PREPARATION_ONLY=true",
    ],
    "NEGATIVE_LOG",
)
visudo_log = (log_root / "visudo.log").read_text(encoding="utf-8")
require(
    visudo_log.startswith("VISUDO_VALIDATION=PASS\n"),
    "VISUDO_LOG",
)

# Runtime validator against actual Evidence.
validator_path = candidate_root / "validate_root_deployment_execution_packet.py"
validator_run = subprocess.run(
    [
        str(repo_root / ".venv/bin/python"),
        "-B",
        str(validator_path),
        str(evidence_root),
    ],
    cwd=candidate_root,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
    text=True,
)
require(
    validator_run.returncode == 0,
    "RUNTIME_VALIDATOR_NONZERO\n" + validator_run.stdout,
)
require("VALIDATION=PASS" in validator_run.stdout, "RUNTIME_VALIDATOR_MARKER")

# Runtime negative tests on their internal temporary copies.
negative_path = candidate_root / "test_root_deployment_execution_packet_negative.py"
negative_source = negative_path.read_text(encoding="utf-8")
compile(negative_source, str(negative_path), "exec")
negative_test_names = re.findall(
    r"^    def (test_[A-Za-z0-9_]+)\(self\) -> None:$",
    negative_source,
    flags=re.MULTILINE,
)
require(len(negative_test_names) == 30, "NEGATIVE_TEST_METHOD_COUNT")
require(len(set(negative_test_names)) == 30, "NEGATIVE_TEST_METHOD_UNIQUENESS")
require("tempfile.TemporaryDirectory" in negative_source, "NEGATIVE_TEMP_DIR")
require(
    "shutil.copytree(EVIDENCE_ROOT, self.root)" in negative_source,
    "NEGATIVE_COPYTREE",
)
negative_run = subprocess.run(
    [
        str(repo_root / ".venv/bin/python"),
        "-B",
        str(negative_path),
    ],
    cwd=candidate_root,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
    text=True,
)
require(
    negative_run.returncode == 0,
    "RUNTIME_NEGATIVE_NONZERO\n" + negative_run.stdout,
)
require("Ran 30 tests" in negative_run.stdout, "RUNTIME_NEGATIVE_COUNT")
require(
    [line.strip() for line in negative_run.stdout.splitlines()].count("OK")
    == 1,
    "RUNTIME_NEGATIVE_OK",
)

# Re-run visudo only against Candidate sudoers file.
visudo_run = subprocess.run(
    [str(visudo_bin), "-cf", str(sudoers_path)],
    cwd=candidate_root,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
    text=True,
)
require(
    visudo_run.returncode == 0,
    "RUNTIME_VISUDO_NONZERO\n" + visudo_run.stdout,
)

# Enhanced static implementation review.
blockers: list[tuple[str, str]] = []

if (
    "parse_manifest(" not in wrapper_source
    and "parse_evidence_manifest(" not in wrapper_source
):
    blockers.append(
        (
            "BLOCKER_1_EVIDENCE_MANIFEST_CONTENT_NOT_REVALIDATED",
            (
                "The wrapper binds only the Evidence-manifest file SHA. "
                "It does not parse the manifest and verify every payload "
                "file before creating the one-shot guard."
            ),
        )
    )

if "PROTECTED_SHA" not in wrapper_source:
    blockers.append(
        (
            "BLOCKER_2_PROTECTED_SHA_REVALIDATION_NOT_IMPLEMENTED",
            (
                "The transaction contract requires protected SHA "
                "revalidation, but the wrapper contains no protected SHA "
                "table or corresponding preflight verification."
            ),
        )
    )

if not (
    "parent_dev" in wrapper_source
    and "parent_ino" in wrapper_source
    and "ROLLBACK_PARENT_DEVICE" in wrapper_source
    and "ROLLBACK_PARENT_INODE" in wrapper_source
):
    blockers.append(
        (
            "BLOCKER_3_CREATED_PARENT_INODE_DEVICE_ROLLBACK_CHECK_MISSING",
            (
                "The contract requires inode/device verification before "
                "removing a transaction-created parent. The wrapper checks "
                "only directory type and emptiness."
            ),
        )
    )

if (
    "os.rename(stage_path, DEPLOYMENT_ROOT)" in wrapper_source
    and "RENAME_NOREPLACE" not in wrapper_source
    and "renameat2" not in wrapper_source
):
    blockers.append(
        (
            "BLOCKER_4_PROMOTION_IS_NOT_ATOMIC_NO_REPLACE",
            (
                "The wrapper uses os.rename after an existence check. "
                "This does not enforce no-replace atomically and leaves a "
                "TOCTOU window contrary to overwrite_allowed=false."
            ),
        )
    )

uses_exists_for_targets = all(
    marker in wrapper_source
    for marker in (
        "not GUARD_PATH.exists()",
        "not DEPLOYMENT_ROOT.exists()",
        "not SUDOERS_TARGET.exists()",
    )
)
has_lexists_or_target_lstat = (
    "os.path.lexists" in wrapper_source
    or "lexists(" in wrapper_source
    or "require_path_entry_absent" in wrapper_source
)
if uses_exists_for_targets and not has_lexists_or_target_lstat:
    blockers.append(
        (
            "BLOCKER_5_DANGLING_SYMLINK_ABSENCE_CHECK_INCOMPLETE",
            (
                "Path.exists() treats a dangling symlink as absent. "
                "The contract requires target symlink rejection before "
                "mutation, but the wrapper has no lexists/lstat absence "
                "check for the guard, deployment root, and sudoers target."
            ),
        )
    )

expected_blocker_names = [
    "BLOCKER_1_EVIDENCE_MANIFEST_CONTENT_NOT_REVALIDATED",
    "BLOCKER_2_PROTECTED_SHA_REVALIDATION_NOT_IMPLEMENTED",
    "BLOCKER_3_CREATED_PARENT_INODE_DEVICE_ROLLBACK_CHECK_MISSING",
    "BLOCKER_4_PROMOTION_IS_NOT_ATOMIC_NO_REPLACE",
    "BLOCKER_5_DANGLING_SYMLINK_ABSENCE_CHECK_INCOMPLETE",
]
require(
    [name for name, _ in blockers] == expected_blocker_names,
    "STATIC_BLOCKER_SET_CHANGED",
)

# No bytecode or source mutation.
require(not list(evidence_root.rglob("*.pyc")), "EVIDENCE_BYTECODE")
require(not list(source_packet_root.rglob("*.pyc")), "SOURCE_PACKET_BYTECODE")
require(not list(final_seal_root.rglob("*.pyc")), "FINAL_SEAL_BYTECODE")
require(not list(runner_source_root.rglob("*.pyc")), "RUNNER_SOURCE_BYTECODE")

for relative, expected in PROTECTED_SHA.items():
    path = repo_root / relative
    require_regular(path, f"PROTECTED:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

require(
    tree_identity(evidence_root) == evidence_identity_before,
    "EVIDENCE_CHANGED_DURING_REVIEW",
)
require(
    tree_identity(source_packet_root) == source_packet_identity_before,
    "SOURCE_PACKET_CHANGED_DURING_REVIEW",
)
require(
    tree_identity(final_seal_root) == final_seal_identity_before,
    "FINAL_SEAL_CHANGED_DURING_REVIEW",
)
require(
    tree_identity(runner_source_root) == runner_source_identity_before,
    "RUNNER_SOURCE_CHANGED_DURING_REVIEW",
)

for relative, expected in PROTECTED_SHA.items():
    require(
        sha256(repo_root / relative) == expected,
        f"PROTECTED_CHANGED:{relative}",
    )

print("EXECUTION_PACKET_RESULT_SHA_REVIEW=PASS")
print("EXECUTION_PACKET_MANIFEST_SHA_REVIEW=PASS")
print("EXECUTION_CANDIDATE_MANIFEST_SHA_REVIEW=PASS")
print("EXECUTION_EVIDENCE_MANIFEST_SHA_REVIEW=PASS")
print("EXECUTION_PACKET_EVIDENCE_ROOT_PATH_REVIEW=PASS")
print("EXECUTION_PACKET_EVIDENCE_FILE_COUNT=36")
print("EXECUTION_PACKET_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=7")
print("EXECUTION_PACKET_FILE_COUNT=34")
print("EXECUTION_PACKET_DIRECTORY_COUNT=6")
print("EXECUTION_PACKET_MANIFEST_ENTRY_COUNT=33")
print("EXECUTION_EVIDENCE_MANIFEST_ENTRY_COUNT=35")
print("EXECUTION_CANDIDATE_ARTIFACT_COUNT=12")
print("EXECUTION_INPUT_SNAPSHOT_FILE_COUNT=16")
print("SOURCE_ROOT_DEPLOYMENT_PACKET_IDENTITY_COUNT=4")
print("FINAL_SEAL_IDENTITY_FILE_COUNT=5")
print("RUNNER_CANDIDATE_FILE_COUNT=7")
print("EXECUTION_VALIDATION_LOG_COUNT=4")
print("INPUT_SNAPSHOT_BYTE_SIZE_SHA_EQUIVALENCE=PASS")
print("SOURCE_ROOT_DEPLOYMENT_PACKET_UNCHANGED=true")
print("FINAL_SEAL_SOURCE_UNCHANGED=true")
print("RUNNER_CANDIDATE_SOURCE_UNCHANGED=true")
print("EXECUTION_PACKET_POLICY_REVIEW=PASS")
print("SOURCE_BINDING_CONTRACT_REVIEW=PASS")
print("APPROVAL_BINDING_CONTRACT_REVIEW=PASS")
print(f"APPROVAL_TOKEN={APPROVAL_TOKEN}")
print(f"APPROVAL_TOKEN_SHA256={APPROVAL_TOKEN_SHA}")
print("ROOT_DEPLOYMENT_TRANSACTION_CONTRACT_REVIEW=PASS")
print("EXECUTION_RESULT_SCHEMA_REVIEW=PASS")
print("CANDIDATE_SUDOERS_CONTENT_REVIEW=PASS")
print("BLOCKED_ENTRYPOINT_STATIC_REVIEW=PASS")
print("BLOCKED_ENTRYPOINT_EXECUTED=false")
print("FUTURE_EXECUTION_WRAPPER_COMPILE_REVIEW=PASS")
print("FUTURE_EXECUTION_WRAPPER_EXECUTED=false")
print("EXECUTION_PACKET_RUNTIME_VALIDATOR_EXECUTED_READONLY=true")
print("EXECUTION_PACKET_RUNTIME_VALIDATOR=PASS")
print("EXECUTION_PACKET_RUNTIME_NEGATIVE_TESTS_TEMP_COPY_ONLY=true")
print("EXECUTION_PACKET_RUNTIME_NEGATIVE_TEST_COUNT=30")
print("EXECUTION_PACKET_RUNTIME_NEGATIVE_TESTS=PASS")
print("EXECUTION_PACKET_RUNTIME_VISUDO_CANDIDATE_ONLY=PASS")
print("EXECUTION_PACKET_EVIDENCE_MUTATION=false")
print("SOURCE_ROOT_DEPLOYMENT_PACKET_MUTATION=false")
print("FINAL_SEAL_SOURCE_MUTATION=false")
print("RUNNER_CANDIDATE_SOURCE_MUTATION=false")
print("EXECUTION_PACKET_BYTECODE_SIDE_EFFECT=false")
print("PROTECTED_SHA_REVIEW=PASS")
print(f"EXECUTION_WRAPPER_STATIC_SAFETY_BLOCKER_COUNT={len(blockers)}")
for name, detail in blockers:
    print(f"{name}=CONFIRMED")
    print(f"{name}_DETAIL={detail}")
print("ROOT_DEPLOYMENT_EXECUTION_PACKET_PREPARATION_ONLY=true")
print("ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false")
print("SUDOERS_INSTALLATION_ALLOWED=false")
print("PRODUCTION_FILE_CREATION_ALLOWED=false")
print("PRODUCTION_DIRECTORY_CREATION_ALLOWED=false")
print("ROOT_HELPER_EXECUTION_ALLOWED=false")
print("RUNNER_EXECUTION_ALLOWED=false")
print("ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
print("SUDOERS_CHANGED=false")
print("AUTOMATIC_DEPLOYMENT_PERFORMED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("FINAL_PRODUCTION_TOKEN_CREATED=false")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print("ROOT_DEPLOYMENT_EXECUTION_PACKET_HUMAN_REVIEW=FAIL_STATIC_SAFETY_BLOCKERS")
print(
    "ROOT_DEPLOYMENT_EXECUTION_PACKET_HUMAN_REVIEW_DECISION="
    "REJECT_EXECUTION_PACKET_REQUIRE_R1_STATIC_SAFETY_CORRECTION_"
    "WITH_PRODUCTION_HOLD"
)
print(
    "NEXT_GATE="
    "HUMAN_APPROVAL_FOR_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_R1_"
    "STATIC_SAFETY_CORRECTION_PREPARATION_NO_EXECUTION"
)
raise SystemExit(2)
PY
REVIEW_RC=$?
set -e

printf '\n===== FINAL EXECUTION PACKET HUMAN REVIEW MARKERS =====\n'

if [[ "$REVIEW_RC" -eq 2 ]]; then
  echo "ROOT_DEPLOYMENT_EXECUTION_PACKET_HUMAN_REVIEW=FAIL_STATIC_SAFETY_BLOCKERS"
  echo "ROOT_DEPLOYMENT_EXECUTION_PACKET_HUMAN_REVIEW_DECISION=REJECT_EXECUTION_PACKET_REQUIRE_R1_STATIC_SAFETY_CORRECTION_WITH_PRODUCTION_HOLD"
  echo "EXECUTION_WRAPPER_STATIC_SAFETY_BLOCKER_COUNT=5"
  echo "ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false"
  echo "SUDOERS_INSTALLATION_ALLOWED=false"
  echo "PRODUCTION_FILE_CREATION_ALLOWED=false"
  echo "PRODUCTION_DIRECTORY_CREATION_ALLOWED=false"
  echo "ROOT_HELPER_EXECUTION_ALLOWED=false"
  echo "RUNNER_EXECUTION_ALLOWED=false"
  echo "ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false"
  echo "APPROVAL_BINDING_CREATED=false"
  echo "SUDOERS_CHANGED=false"
  echo "AUTOMATIC_DEPLOYMENT_PERFORMED=false"
  echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
  echo "FINAL_PRODUCTION_TOKEN_CREATED=false"
  echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
  echo "NEXT_GATE=HUMAN_APPROVAL_FOR_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_R1_STATIC_SAFETY_CORRECTION_PREPARATION_NO_EXECUTION"
  echo "REVIEW_COMMAND_EXIT_CODE=2"
  exit 2
fi

echo "UNEXPECTED_REVIEW_EXIT_CODE=${REVIEW_RC}" >&2
exit "$REVIEW_RC"
