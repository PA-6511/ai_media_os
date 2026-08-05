#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

EXECUTED_SCRIPT="${REPO_ROOT}/scripts/manual/tst_5d_w2b_i2f3e_j_r2_r7_evidence_seal_correction_no_execution.sh"
EXPECTED_SCRIPT_LINES="550"
EXPECTED_SCRIPT_BYTES="29504"
EXPECTED_SCRIPT_SHA="c351fa93c2a5f2047341936c94ff4f519370b97632164afc90678fb3648b291a"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SOURCE_REL="${BASE_REL}/i2f3e-j-r2-r6-negative-test-log-marker-correction-20260725T170657Z-517926"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"

R7_REL="${BASE_REL}/i2f3e-j-r2-r7-evidence-seal-correction-20260726T012717Z-523349"
R7_ROOT="${REPO_ROOT}/${R7_REL}"
SNAPSHOT_ROOT="${R7_ROOT}/source-r2-r6-snapshot"

CONSOLE_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r7_console.txt"
REVIEW_LOG="/tmp/tst_5d_w2b_i2f3e_j_r2_r7_human_review_readonly.txt"

EXPECTED_RESULT_SHA="ff696c3857c9b9624ec8bb76b7eb668f2a90285825711f4cb3fdcbcc48f048c1"
EXPECTED_SEAL_VALIDATION_SHA="a8927081753839939f752256fa7edbe0dbad1816341cb34a32484a325ab96e1d"
EXPECTED_SNAPSHOT_MANIFEST_SHA="d6b71537bae70fa0f4e9ae2a6b9b214881ec11e0190e440782c9da0a71d9afc3"
EXPECTED_EVIDENCE_MANIFEST_SHA="a31bd7fc37753688feaa19e0bf518fb1fdcf5d5743a2fb87ac3d4625ec2ea380"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -f "$EXECUTED_SCRIPT"
test -d "$SOURCE_ROOT"
test -d "$R7_ROOT"
test -f "$CONSOLE_LOG"

cd "$REPO_ROOT"

(
  set -Eeuo pipefail

  printf '\n===== EXECUTED SCRIPT IDENTITY =====\n'

  ACTUAL_LINES="$(wc -l < "$EXECUTED_SCRIPT")"
  ACTUAL_BYTES="$(wc -c < "$EXECUTED_SCRIPT")"
  ACTUAL_SHA="$(sha256sum "$EXECUTED_SCRIPT" | awk '{print $1}')"

  printf 'EXECUTED_SCRIPT_LINES=%s\n' "$ACTUAL_LINES"
  printf 'EXECUTED_SCRIPT_BYTES=%s\n' "$ACTUAL_BYTES"
  printf 'EXECUTED_SCRIPT_SHA=%s\n' "$ACTUAL_SHA"

  [[ "$ACTUAL_LINES" == "$EXPECTED_SCRIPT_LINES" ]]
  [[ "$ACTUAL_BYTES" == "$EXPECTED_SCRIPT_BYTES" ]]
  [[ "$ACTUAL_SHA" == "$EXPECTED_SCRIPT_SHA" ]]

  bash -n "$EXECUTED_SCRIPT"
  echo "EXECUTED_SCRIPT_BASH_N=PASS"

  printf '\n===== EXECUTED SCRIPT STATIC SAFETY REVIEW =====\n'

  "$PYTHON_BIN" - "$EXECUTED_SCRIPT" <<'PY'
from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path

path = Path(sys.argv[1]).resolve(strict=True)
text = path.read_text(encoding="utf-8")

assert len(text.splitlines()) == 550
assert len(path.read_bytes()) == 29504
assert hashlib.sha256(path.read_bytes()).hexdigest() == (
    "c351fa93c2a5f2047341936c94ff4f519370b97632164afc90678fb3648b291a"
)

match = re.search(r"<<'PY'\n(.*)\nPY\s*$", text, flags=re.DOTALL)
assert match is not None
embedded = match.group(1)
compile(embedded, f"{path}:embedded-python", "exec")
tree = ast.parse(embedded)

allowed_imports = {
    "__future__",
    "base64",
    "hashlib",
    "json",
    "os",
    "stat",
    "sys",
    "pathlib",
    "typing",
}
actual_imports: set[str] = set()

for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        actual_imports.update(alias.name.split(".", 1)[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        assert node.module is not None
        actual_imports.add(node.module.split(".", 1)[0])

assert actual_imports <= allowed_imports
assert not (
    actual_imports
    & {
        "subprocess",
        "socket",
        "sqlite3",
        "urllib",
        "http",
        "requests",
        "signal",
        "shutil",
    }
)

forbidden_calls = {
    "os.system",
    "os.popen",
    "os.spawnl",
    "os.spawnv",
    "os.execv",
    "os.execve",
    "os.remove",
    "os.unlink",
    "os.rename",
    "os.replace",
    "os.chown",
    "os.fchown",
    "os.kill",
    "os.killpg",
    "eval",
    "exec",
    "compile",
    "__import__",
}

call_names: list[str] = []
chmod_calls: list[ast.Call] = []

def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""

for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        name = call_name(node.func)
        call_names.append(name)
        assert name not in forbidden_calls, name
        if name == "os.chmod":
            chmod_calls.append(node)

assert len(chmod_calls) == 2
chmod_modes = []
for call in chmod_calls:
    assert len(call.args) >= 2
    mode_node = call.args[1]
    assert isinstance(mode_node, ast.Constant)
    chmod_modes.append(mode_node.value)

    keyword_values = {
        keyword.arg: keyword.value
        for keyword in call.keywords
        if keyword.arg is not None
    }
    assert "follow_symlinks" in keyword_values
    follow_value = keyword_values["follow_symlinks"]
    assert isinstance(follow_value, ast.Constant)
    assert follow_value.value is False

assert sorted(chmod_modes) == [0o444, 0o555]

required_markers = (
    'RUN_AS_ROOT_FORBIDDEN=true',
    'os.O_EXCL | os.O_NOFOLLOW',
    'ensure_inside(path, evidence_root)',
    'CHMOD_SCOPE=NEW_R2_R7_EVIDENCE_ROOT_ONLY',
    'SOURCE_R2_R6_UNCHANGED=true',
    'PROTECTED_SHA_UNCHANGED=true',
    'CANDIDATE_DEPLOYED_TO_PRODUCTION=false',
    'SUDOERS_CHANGED=false',
    'PRODUCTION_DB_SQL_CONNECTION_USED=false',
    'PRODUCTION_DEPLOYMENT_PERFORMED=false',
    'EXTERNAL_NETWORK_USED=false',
)
for marker in required_markers:
    assert marker in text, marker

forbidden_shell_patterns = (
    r'(^|\n)\s*sudo(?:\s|$)',
    r'(^|\n)\s*systemctl(?:\s|$)',
    r'(^|\n)\s*git\s+(?:add|commit|push|reset|checkout|clean)(?:\s|$)',
    r'(^|\n)\s*(?:rm|mv|chown|kill|pkill|killall)(?:\s|$)',
    r'/opt/ai-media-os/3e-j',
    r'/etc/sudoers(?:\.d)?/',
)
for pattern in forbidden_shell_patterns:
    assert re.search(pattern, text, flags=re.MULTILINE) is None, pattern

assert "subprocess" not in call_names
assert "socket" not in call_names

print("EXECUTED_SCRIPT_EMBEDDED_PYTHON_COMPILE=PASS")
print("EXECUTED_SCRIPT_IMPORT_ALLOWLIST=PASS")
print("EXECUTED_SCRIPT_FORBIDDEN_CALL_REVIEW=PASS")
print("EXECUTED_SCRIPT_CHMOD_CALL_COUNT=2")
print("EXECUTED_SCRIPT_CHMOD_MODES=0444,0555")
print("EXECUTED_SCRIPT_CHMOD_NOFOLLOW=true")
print("EXECUTED_SCRIPT_EXCLUSIVE_CREATE_REVIEW=PASS")
print("EXECUTED_SCRIPT_ROOT_CONFINEMENT_MARKER_REVIEW=PASS")
print("EXECUTED_SCRIPT_PRODUCTION_ACTION_STATIC_REVIEW=PASS")
PY

  printf '\n===== FIXED ARTIFACT SHA =====\n'

  sha256sum -c <<SHAS
${EXPECTED_RESULT_SHA}  ${R7_ROOT}/result.json
${EXPECTED_SEAL_VALIDATION_SHA}  ${R7_ROOT}/seal-validation.json
${EXPECTED_SNAPSHOT_MANIFEST_SHA}  ${R7_ROOT}/snapshot-copy-manifest.json
${EXPECTED_EVIDENCE_MANIFEST_SHA}  ${R7_ROOT}/evidence-manifest.txt
SHAS

  printf '\n===== R2-R7 SEALED EVIDENCE REVIEW =====\n'

  "$PYTHON_BIN" - \
    "$REPO_ROOT" \
    "$SOURCE_ROOT" \
    "$R7_ROOT" \
    "$SNAPSHOT_ROOT" \
    "$CONSOLE_LOG" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
source_root = Path(sys.argv[2]).resolve(strict=True)
r7_root = Path(sys.argv[3]).resolve(strict=True)
snapshot_root = Path(sys.argv[4]).resolve(strict=True)
console_log = Path(sys.argv[5]).resolve(strict=True)

expected_r7_relative = (
    "exchange/review_evidence/slack_worker_release_rebinding/"
    "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/"
    "tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/"
    "i2f3e-j-r2-r7-evidence-seal-correction-20260726T012717Z-523349"
)
expected_source_relative = (
    "exchange/review_evidence/slack_worker_release_rebinding/"
    "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/"
    "tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/"
    "i2f3e-j-r2-r6-negative-test-log-marker-correction-"
    "20260725T170657Z-517926"
)

expected_fixed_sha = {
    "result.json": (
        "a6af278eb38b31590b8dfb3ffc03a8ab"
        "0227419a2ceea467561660b3b0e8add0"
    ),
    "packet-snapshot/packet-manifest.json": (
        "06c10cfdb7c83c0699c73caeb7248d84"
        "29027e27c6d696c437bac38aad3eaa66"
    ),
    "packet-snapshot/packet-semantic-validation.json": (
        "df0463ac59afc44d06f00b1908376dd4"
        "c706db47493602989e4831faddc7fb2f"
    ),
    "evidence-manifest.txt": (
        "347a0032bd4b68db531661249e10886c6"
        "ce79f2b3db70fc15413f88a0bbe4d16"
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

def scan(root: Path) -> tuple[list[Path], list[Path], int, int]:
    root_state = root.lstat()
    require(stat.S_ISDIR(root_state.st_mode), f"ROOT_NOT_DIRECTORY:{root}")
    require(not stat.S_ISLNK(root_state.st_mode), f"ROOT_SYMLINK:{root}")

    files: list[Path] = []
    directories: list[Path] = [root]
    symlinks = 0
    nonregular = 0

    def walk(directory: Path) -> None:
        nonlocal symlinks, nonregular
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: item.name)
        for entry in entries:
            path = Path(entry.path)
            state = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(state.st_mode):
                symlinks += 1
            elif stat.S_ISDIR(state.st_mode):
                directories.append(path)
                walk(path)
            elif stat.S_ISREG(state.st_mode):
                files.append(path)
            else:
                nonregular += 1

    walk(root)
    return sorted(files), sorted(directories), symlinks, nonregular

def current_source_state() -> dict[str, Any]:
    files, directories, symlinks, nonregular = scan(source_root)

    def record(path: Path) -> dict[str, Any]:
        state = path.lstat()
        relative = (
            "."
            if path == source_root
            else path.relative_to(source_root).as_posix()
        )
        value: dict[str, Any] = {
            "relative_path": relative,
            "uid": state.st_uid,
            "gid": state.st_gid,
            "mode": f"{stat.S_IMODE(state.st_mode):04o}",
            "mtime_ns": state.st_mtime_ns,
            "size_bytes": state.st_size,
            "is_regular_file": stat.S_ISREG(state.st_mode),
            "is_directory": stat.S_ISDIR(state.st_mode),
            "is_symlink": stat.S_ISLNK(state.st_mode),
        }
        if value["is_regular_file"]:
            value["sha256"] = sha256(path)
        return value

    return {
        "file_count": len(files),
        "directory_count": len(directories),
        "symlink_count": symlinks,
        "files": [record(path) for path in files],
        "directories": [record(path) for path in directories],
    }

require(
    r7_root.relative_to(repo_root).as_posix() == expected_r7_relative,
    "R7_ROOT_BINDING_INVALID",
)
require(
    source_root.relative_to(repo_root).as_posix()
    == expected_source_relative,
    "SOURCE_ROOT_BINDING_INVALID",
)
require(
    snapshot_root == r7_root / "source-r2-r6-snapshot",
    "SNAPSHOT_ROOT_BINDING_INVALID",
)

repo_state = repo_root.stat()
expected_uid = repo_state.st_uid
expected_gid = repo_state.st_gid

r7_files, r7_directories, r7_symlinks, r7_nonregular = scan(r7_root)
require(len(r7_files) == 39, "R7_FILE_COUNT_NOT_39")
require(len(r7_directories) == 10, "R7_DIRECTORY_COUNT_NOT_10")
require(r7_symlinks == 0, "R7_SYMLINK_COUNT_NOT_ZERO")
require(r7_nonregular == 0, "R7_NONREGULAR_COUNT_NOT_ZERO")

file_modes = Counter(
    f"{stat.S_IMODE(path.lstat().st_mode):04o}"
    for path in r7_files
)
directory_modes = Counter(
    f"{stat.S_IMODE(path.lstat().st_mode):04o}"
    for path in r7_directories
)
require(file_modes == {"0444": 39}, "R7_FILE_MODE_DISTRIBUTION_INVALID")
require(
    directory_modes == {"0555": 10},
    "R7_DIRECTORY_MODE_DISTRIBUTION_INVALID",
)
require(
    all(
        path.lstat().st_uid == expected_uid
        and path.lstat().st_gid == expected_gid
        for path in r7_files + r7_directories
    ),
    "R7_OWNER_GROUP_INVALID",
)

required_top_files = {
    "source-r2-r6-fixed-sha.json",
    "source-r2-r6-mode-inventory.json",
    "snapshot-copy-manifest.json",
    "seal-policy.json",
    "seal-validation.json",
    "result.json",
    "evidence-manifest.txt",
    "human-approval-verbatim.txt",
}
actual_top_files = {
    path.name for path in r7_root.iterdir() if path.is_file()
}
require(actual_top_files == required_top_files, "R7_TOP_FILE_SET_INVALID")

result = load_json(r7_root / "result.json")
seal_validation = load_json(r7_root / "seal-validation.json")
copy_manifest = load_json(r7_root / "snapshot-copy-manifest.json")
seal_policy = load_json(r7_root / "seal-policy.json")
fixed_sha_record = load_json(r7_root / "source-r2-r6-fixed-sha.json")
mode_inventory = load_json(
    r7_root / "source-r2-r6-mode-inventory.json"
)

require(result["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R7", "RESULT_PHASE")
require(
    result["result"]
    == "PASS_W2B_I2F3E_J_R2_R7_EVIDENCE_SEAL_CORRECTION_NO_EXECUTION",
    "RESULT_VALUE",
)
require(result["recording_semantics"] == "PRECOMMITTED_BEFORE_SEAL", "RESULT_RECORDING")
require(result["valid_only_if_script_exit_code_zero"] is True, "RESULT_EXIT_BINDING")
require(result["evidence_root"] == expected_r7_relative, "RESULT_EVIDENCE_ROOT")
require(result["source_evidence_root"] == expected_source_relative, "RESULT_SOURCE_ROOT")
require(result["source_file_count"] == 31, "RESULT_SOURCE_FILE_COUNT")
require(result["source_directory_count"] == 9, "RESULT_SOURCE_DIR_COUNT")
require(result["snapshot_file_count"] == 31, "RESULT_SNAPSHOT_COUNT")
require(result["evidence_file_mode_required"] == "0444", "RESULT_FILE_MODE")
require(result["evidence_directory_mode_required"] == "0555", "RESULT_DIR_MODE")
require(
    result["chmod_scope"] == "NEW_R2_R7_EVIDENCE_ROOT_ONLY",
    "RESULT_CHMOD_SCOPE",
)
require(
    result["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "RESULT_RUNNER_STATUS",
)
require(
    result["sudoers_destination_existence_state"]
    == "UNKNOWN_PERMISSION_DENIED",
    "RESULT_SUDOERS_STATE",
)
require(
    result["deployment_authorization_packet_status"]
    == "HOLD_PENDING_CONDITION_RESOLUTION",
    "RESULT_PACKET_STATUS",
)
for key in (
    "candidate_deployed_to_production",
    "sudoers_changed",
    "final_approval_token_created",
    "approval_binding_created",
):
    require(result[key] is False, f"RESULT_FALSE_MARKER:{key}")
require(result["writer_freeze_execution"] == "HOLD", "RESULT_WRITER_HOLD")
require(result["production_release_decision"] == "HOLD", "RESULT_RELEASE_HOLD")
require(result["release_status"] == "CANDIDATE_NOT_APPROVED", "RESULT_RELEASE_STATUS")
require(
    result["next_gate"] == "HUMAN_REVIEW_3E_J_R2_R7_EVIDENCE_SEAL",
    "RESULT_NEXT_GATE",
)

require(
    seal_validation["recording_semantics"]
    == "PRECOMMITTED_BEFORE_SEAL",
    "SEAL_RECORDING",
)
require(
    seal_validation["valid_only_if_script_exit_code_zero"] is True,
    "SEAL_EXIT_BINDING",
)
require(
    seal_validation["required_final_file_mode"] == "0444",
    "SEAL_FILE_MODE",
)
require(
    seal_validation["required_final_directory_mode"] == "0555",
    "SEAL_DIR_MODE",
)
require(
    seal_validation["required_final_symlink_count"] == 0,
    "SEAL_SYMLINK_COUNT",
)
require(
    seal_validation["source_snapshot_sha_and_size_equivalence"] is True,
    "SEAL_SNAPSHOT_EQUIVALENCE",
)
require(
    seal_validation["source_r2_r6_must_remain_unchanged"] is True,
    "SEAL_SOURCE_IMMUTABILITY",
)

require(copy_manifest["phase"] == "TST-5D-W2B-I2F-3E-J-R2-R7", "COPY_PHASE")
require(copy_manifest["copy_method"] == "O_EXCL_O_NOFOLLOW", "COPY_METHOD")
require(copy_manifest["source_file_count"] == 31, "COPY_SOURCE_COUNT")
require(copy_manifest["snapshot_file_count"] == 31, "COPY_SNAPSHOT_COUNT")
require(
    copy_manifest["sha256_and_size_equivalence_required"] is True,
    "COPY_EQUIVALENCE_REQUIRED",
)
records = copy_manifest["records"]
require(isinstance(records, list), "COPY_RECORDS_NOT_LIST")
require(len(records) == 31, "COPY_RECORD_COUNT_NOT_31")

seen_source: set[str] = set()
seen_snapshot: set[str] = set()

for record in records:
    source_relative = record["source_relative_path"]
    snapshot_relative = record["snapshot_relative_path"]

    require(source_relative not in seen_source, f"COPY_SOURCE_DUPLICATE:{source_relative}")
    require(snapshot_relative not in seen_snapshot, f"COPY_SNAPSHOT_DUPLICATE:{snapshot_relative}")
    seen_source.add(source_relative)
    seen_snapshot.add(snapshot_relative)

    source_path = (source_root / source_relative).resolve(strict=True)
    snapshot_path = (r7_root / snapshot_relative).resolve(strict=True)

    require(
        source_path == source_root / source_relative,
        f"COPY_SOURCE_PATH_NORMALIZATION:{source_relative}",
    )
    require(
        snapshot_path == r7_root / snapshot_relative,
        f"COPY_SNAPSHOT_PATH_NORMALIZATION:{snapshot_relative}",
    )
    require(
        snapshot_path == snapshot_root / source_relative,
        f"COPY_RELATIVE_PATH_MISMATCH:{source_relative}",
    )
    require(source_path.is_file(), f"COPY_SOURCE_MISSING:{source_relative}")
    require(snapshot_path.is_file(), f"COPY_SNAPSHOT_MISSING:{snapshot_relative}")

    expected_hash = record["sha256"]
    expected_size = record["size_bytes"]
    require(sha256(source_path) == expected_hash, f"COPY_SOURCE_SHA:{source_relative}")
    require(sha256(snapshot_path) == expected_hash, f"COPY_SNAPSHOT_SHA:{snapshot_relative}")
    require(source_path.stat().st_size == expected_size, f"COPY_SOURCE_SIZE:{source_relative}")
    require(snapshot_path.stat().st_size == expected_size, f"COPY_SNAPSHOT_SIZE:{snapshot_relative}")

snapshot_files, snapshot_directories, snapshot_symlinks, snapshot_nonregular = scan(snapshot_root)
require(len(snapshot_files) == 31, "SNAPSHOT_FILE_COUNT_NOT_31")
require(len(snapshot_directories) == 9, "SNAPSHOT_DIRECTORY_COUNT_NOT_9")
require(snapshot_symlinks == 0, "SNAPSHOT_SYMLINK_COUNT_NOT_ZERO")
require(snapshot_nonregular == 0, "SNAPSHOT_NONREGULAR_COUNT_NOT_ZERO")

manifest_path = r7_root / "evidence-manifest.txt"
manifest_entries: dict[str, str] = {}
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    require(relative not in manifest_entries, f"R7_MANIFEST_DUPLICATE:{relative}")
    manifest_entries[relative] = expected

actual_manifest_set = {
    path.relative_to(r7_root).as_posix()
    for path in r7_files
    if path != manifest_path
}
require(len(manifest_entries) == 38, "R7_MANIFEST_ENTRY_COUNT_NOT_38")
require(set(manifest_entries) == actual_manifest_set, "R7_MANIFEST_SET_MISMATCH")
for relative, expected in manifest_entries.items():
    require(
        sha256(r7_root / relative) == expected,
        f"R7_MANIFEST_SHA_MISMATCH:{relative}",
    )

require(
    fixed_sha_record["source_evidence_root"] == expected_source_relative,
    "FIXED_SHA_SOURCE_ROOT",
)
require(
    fixed_sha_record["source_fixed_sha256"] == expected_fixed_sha,
    "FIXED_SHA_RECORD_MISMATCH",
)
require(
    fixed_sha_record["source_manifest_entry_count"] == 30,
    "FIXED_SHA_SOURCE_MANIFEST_COUNT",
)
require(
    fixed_sha_record["source_total_file_count"] == 31,
    "FIXED_SHA_SOURCE_FILE_COUNT",
)
require(
    fixed_sha_record["source_r2_r6_mutation_allowed"] is False,
    "FIXED_SHA_SOURCE_MUTATION_FLAG",
)
require(
    fixed_sha_record["source_r2_r6_chmod_allowed"] is False,
    "FIXED_SHA_SOURCE_CHMOD_FLAG",
)

source_files, source_directories, source_symlinks, source_nonregular = scan(source_root)
require(len(source_files) == 31, "SOURCE_FILE_COUNT_NOT_31")
require(len(source_directories) == 9, "SOURCE_DIRECTORY_COUNT_NOT_9")
require(source_symlinks == 0, "SOURCE_SYMLINK_COUNT_NOT_ZERO")
require(source_nonregular == 0, "SOURCE_NONREGULAR_COUNT_NOT_ZERO")
require(
    all(stat.S_IMODE(path.lstat().st_mode) == 0o640 for path in source_files),
    "SOURCE_FILE_MODE_CHANGED",
)
require(
    all(stat.S_IMODE(path.lstat().st_mode) == 0o750 for path in source_directories),
    "SOURCE_DIRECTORY_MODE_CHANGED",
)
require(
    all(
        path.lstat().st_uid == expected_uid
        and path.lstat().st_gid == expected_gid
        for path in source_files + source_directories
    ),
    "SOURCE_OWNER_GROUP_CHANGED",
)

recorded_source_state = mode_inventory["state"]
require(
    recorded_source_state == current_source_state(),
    "SOURCE_RECORDED_STATE_MISMATCH",
)
require(mode_inventory["source_state_sha256"], "SOURCE_STATE_SHA_MISSING")
require(mode_inventory["file_count"] == 31, "MODE_INVENTORY_FILE_COUNT")
require(mode_inventory["directory_count"] == 9, "MODE_INVENTORY_DIR_COUNT")
require(mode_inventory["file_mode"] == "0640", "MODE_INVENTORY_FILE_MODE")
require(mode_inventory["directory_mode"] == "0750", "MODE_INVENTORY_DIR_MODE")
require(mode_inventory["symlink_count"] == 0, "MODE_INVENTORY_SYMLINK_COUNT")

for relative, expected in expected_fixed_sha.items():
    require(
        sha256(source_root / relative) == expected,
        f"SOURCE_FIXED_SHA_CHANGED:{relative}",
    )

source_manifest_path = source_root / "evidence-manifest.txt"
source_manifest_entries: dict[str, str] = {}
for line in source_manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    require(relative not in source_manifest_entries, f"SOURCE_MANIFEST_DUPLICATE:{relative}")
    source_manifest_entries[relative] = expected

source_manifest_set = {
    path.relative_to(source_root).as_posix()
    for path in source_files
    if path != source_manifest_path
}
require(len(source_manifest_entries) == 30, "SOURCE_MANIFEST_ENTRY_COUNT_NOT_30")
require(set(source_manifest_entries) == source_manifest_set, "SOURCE_MANIFEST_SET_MISMATCH")
for relative, expected in source_manifest_entries.items():
    require(
        sha256(source_root / relative) == expected,
        f"SOURCE_MANIFEST_SHA_CHANGED:{relative}",
    )

for relative, expected in expected_protected_sha.items():
    require(
        sha256(repo_root / relative) == expected,
        f"PROTECTED_SHA_CHANGED:{relative}",
    )

require(
    fixed_sha_record["protected_production_sha256"]
    == expected_protected_sha,
    "RECORDED_PROTECTED_SHA_MISMATCH",
)

require(seal_policy["file_mode"] == "0444", "POLICY_FILE_MODE")
require(seal_policy["directory_mode"] == "0555", "POLICY_DIRECTORY_MODE")
require(seal_policy["owner_uid"] == expected_uid, "POLICY_OWNER_UID")
require(seal_policy["group_gid"] == expected_gid, "POLICY_GROUP_GID")
require(seal_policy["symlink_allowed"] is False, "POLICY_SYMLINK_ALLOWED")
require(
    seal_policy["chmod_scope"] == "NEW_R2_R7_EVIDENCE_ROOT_ONLY",
    "POLICY_CHMOD_SCOPE",
)
require(
    seal_policy["directory_chmod_order"] == "DEEPEST_FIRST",
    "POLICY_CHMOD_ORDER",
)
require(
    seal_policy["source_r2_r6_mutation_allowed"] is False,
    "POLICY_SOURCE_MUTATION",
)
require(
    seal_policy["source_r2_r6_chmod_allowed"] is False,
    "POLICY_SOURCE_CHMOD",
)
require(
    seal_policy["runner_status"]
    == "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "POLICY_RUNNER_STATUS",
)
require(
    seal_policy["sudoers_destination_existence_state"]
    == "UNKNOWN_PERMISSION_DENIED",
    "POLICY_SUDOERS_STATE",
)
require(
    seal_policy["deployment_authorization_packet_status"]
    == "HOLD_PENDING_CONDITION_RESOLUTION",
    "POLICY_PACKET_STATUS",
)

console = console_log.read_text(encoding="utf-8", errors="strict")
required_console_lines = (
    "RESULT=PASS_W2B_I2F3E_J_R2_R7_EVIDENCE_SEAL_CORRECTION_NO_EXECUTION",
    f"EVIDENCE_ROOT={expected_r7_relative}",
    "SOURCE_R2_R6_FIXED_SHA_REVIEW=PASS",
    "SOURCE_R2_R6_MANIFEST_ENTRY_COUNT=30",
    "SOURCE_R2_R6_FILE_COUNT=31",
    "SOURCE_R2_R6_DIRECTORY_COUNT=9",
    "SOURCE_R2_R6_FILE_MODE=0640",
    "SOURCE_R2_R6_DIRECTORY_MODE=0750",
    "SOURCE_R2_R6_SYMLINK_COUNT=0",
    "SNAPSHOT_FILE_COUNT=31",
    "SNAPSHOT_BYTE_EQUIVALENCE=PASS",
    "SNAPSHOT_SIZE_EQUIVALENCE=PASS",
    "EXCLUSIVE_CREATE=PASS",
    "R2_R7_EVIDENCE_FILE_COUNT=39",
    "R2_R7_EVIDENCE_DIRECTORY_COUNT=10",
    "R2_R7_EVIDENCE_MANIFEST_ENTRY_COUNT=38",
    "R2_R7_EVIDENCE_FILE_MODE=0444",
    "R2_R7_EVIDENCE_DIRECTORY_MODE=0555",
    "R2_R7_EVIDENCE_SYMLINK_COUNT=0",
    "EVIDENCE_MANIFEST_CONTENT_VALID=true",
    "POST_SEAL_VALIDATION=PASS",
    "SOURCE_R2_R6_UNCHANGED=true",
    "SOURCE_R2_R6_MODE_UNCHANGED=true",
    "SOURCE_R2_R6_MTIME_UNCHANGED=true",
    "PROTECTED_SHA_UNCHANGED=true",
    "CHMOD_SCOPE=NEW_R2_R7_EVIDENCE_ROOT_ONLY",
    "RESULT_SHA=ff696c3857c9b9624ec8bb76b7eb668f2a90285825711f4cb3fdcbcc48f048c1",
    "SEAL_VALIDATION_SHA=a8927081753839939f752256fa7edbe0dbad1816341cb34a32484a325ab96e1d",
    "SNAPSHOT_COPY_MANIFEST_SHA=d6b71537bae70fa0f4e9ae2a6b9b214881ec11e0190e440782c9da0a71d9afc3",
    "EVIDENCE_MANIFEST_SHA=a31bd7fc37753688feaa19e0bf518fb1fdcf5d5743a2fb87ac3d4625ec2ea380",
    "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "SUDOERS_DESTINATION_EXISTENCE_STATE=UNKNOWN_PERMISSION_DENIED",
    "DEPLOYMENT_AUTHORIZATION_PACKET_STATUS=HOLD_PENDING_CONDITION_RESOLUTION",
    "CANDIDATE_DEPLOYED_TO_PRODUCTION=false",
    "PRODUCTION_DIRECTORY_CREATED=false",
    "PRODUCTION_FILE_CREATED=false",
    "SUDOERS_CHANGED=false",
    "FINAL_APPROVAL_TOKEN_CREATED=false",
    "APPROVAL_BINDING_CREATED=false",
    "PRODUCTION_PROCESS_SIGNAL_SENT=false",
    "WRITER_STOP_PERFORMED=false",
    "GUI_STOPPED_OR_RESTARTED=false",
    "PRODUCTION_DB_SQL_CONNECTION_USED=false",
    "PRODUCTION_BACKUP_CREATED=false",
    "RESTORE_EXECUTED=false",
    "MIGRATION_EXECUTED=false",
    "PRODUCTION_MANIFEST_MODIFIED=false",
    "GIT_ADD_PERFORMED=false",
    "GIT_COMMIT_PERFORMED=false",
    "PRODUCTION_DEPLOYMENT_PERFORMED=false",
    "EXTERNAL_NETWORK_USED=false",
    "WRITER_FREEZE_EXECUTION=HOLD",
    "PRODUCTION_RELEASE_DECISION=HOLD",
    "RELEASE_STATUS=CANDIDATE_NOT_APPROVED",
    "NEXT_GATE=HUMAN_REVIEW_3E_J_R2_R7_EVIDENCE_SEAL",
)
console_lines = [line.strip() for line in console.splitlines()]
for marker in required_console_lines:
    require(marker in console_lines, f"CONSOLE_MARKER_MISSING:{marker}")

require(
    console_lines.count("SCRIPT_EXIT_CODE=0") == 1,
    "CONSOLE_EXIT_ZERO_COUNT_NOT_EXACTLY_ONE",
)
require("Traceback (most recent call last):" not in console, "CONSOLE_TRACEBACK_PRESENT")
require("SealError:" not in console, "CONSOLE_SEAL_ERROR_PRESENT")

production_root = Path("/opt/ai-media-os/3e-j")
try:
    production_root.lstat()
except FileNotFoundError:
    production_root_state = "ABSENT_CONFIRMED"
else:
    production_root_state = "PRESENT_CONFIRMED"
require(
    production_root_state == "ABSENT_CONFIRMED",
    "PRODUCTION_DEPLOYMENT_ROOT_PRESENT",
)

sudoers_destination = Path(
    "/etc/sudoers.d/ai-media-os-3e-j-root-helper"
)
try:
    sudoers_destination.lstat()
except FileNotFoundError:
    live_sudoers_state = "ABSENT_CONFIRMED"
except PermissionError:
    live_sudoers_state = "UNKNOWN_PERMISSION_DENIED"
except OSError:
    live_sudoers_state = "UNKNOWN_OS_ERROR"
else:
    live_sudoers_state = "PRESENT_CONFIRMED"

require(
    live_sudoers_state in {
        "UNKNOWN_PERMISSION_DENIED",
        "UNKNOWN_OS_ERROR",
    },
    "LIVE_SUDOERS_STATE_UNEXPECTED_FOR_HOLD_REVIEW",
)

print("R2_R7_EXECUTED_SCRIPT_IDENTITY_REVIEW=PASS")
print("R2_R7_EXECUTED_SCRIPT_STATIC_SAFETY_REVIEW=PASS")
print("R2_R7_FIXED_ARTIFACT_SHA_REVIEW=PASS")
print("R2_R7_RESULT_CONTRACT_REVIEW=PASS")
print("R2_R7_SEAL_POLICY_REVIEW=PASS")
print("R2_R7_CONSOLE_COMPLETION_BINDING_REVIEW=PASS")
print("R2_R7_CONSOLE_EXIT_ZERO_MARKER_COUNT=1")
print("R2_R7_OUTER_WRAPPER_EXIT_MARKER_NOT_IN_TEE_LOG=true")
print("R2_R7_EVIDENCE_FILE_COUNT=39")
print("R2_R7_EVIDENCE_DIRECTORY_COUNT=10")
print("R2_R7_EVIDENCE_MANIFEST_ENTRY_COUNT=38")
print("R2_R7_EVIDENCE_FILE_MODE_DISTRIBUTION={\"0444\":39}")
print("R2_R7_EVIDENCE_DIRECTORY_MODE_DISTRIBUTION={\"0555\":10}")
print("R2_R7_EVIDENCE_SYMLINK_COUNT=0")
print("R2_R7_EVIDENCE_NONREGULAR_COUNT=0")
print("R2_R7_EVIDENCE_OWNER_GROUP_REVIEW=PASS")
print("R2_R7_EVIDENCE_MANIFEST_CONTENT_REVIEW=PASS")
print("R2_R7_SNAPSHOT_FILE_COUNT=31")
print("R2_R7_SNAPSHOT_BYTE_AND_SIZE_EQUIVALENCE_REVIEW=PASS")
print("R2_R6_SOURCE_FILE_COUNT=31")
print("R2_R6_SOURCE_DIRECTORY_COUNT=9")
print("R2_R6_SOURCE_MODE_AND_METADATA_UNCHANGED_REVIEW=PASS")
print("R2_R6_SOURCE_MANIFEST_CONTENT_REVIEW=PASS")
print("PROTECTED_SHA_REVIEW=PASS")
print("PRODUCTION_DEPLOYMENT_ROOT_STATE=ABSENT_CONFIRMED")
print(f"LIVE_SUDOERS_DESTINATION_EXISTENCE_STATE={live_sudoers_state}")
print("EVIDENCE_SEAL_COMPLETE=true")
print("R2_R7_HUMAN_REVIEW_DECISION=APPROVE_SEALED_EVIDENCE_WITH_EXECUTION_HOLD")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("DEPLOYMENT_AUTHORIZATION_PACKET_STATUS=HOLD_PENDING_CONDITION_RESOLUTION")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("SUDOERS_CHANGED=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE="
    "HUMAN_APPROVAL_FOR_3E_J_R2_R8_ROOT_READONLY_"
    "SUDOERS_DESTINATION_VERIFICATION_PACKET_PREPARATION_NO_EXECUTION"
)
PY

  printf '\n===== FINAL REVIEW MARKERS =====\n'

  echo "R2_R7_EXECUTED_SCRIPT_IDENTITY_REVIEW=PASS"
  echo "R2_R7_EXECUTED_SCRIPT_STATIC_SAFETY_REVIEW=PASS"
  echo "R2_R7_FIXED_ARTIFACT_SHA_REVIEW=PASS"
  echo "R2_R7_SEALED_EVIDENCE_REVIEW=PASS"
  echo "R2_R7_CONSOLE_EXIT_ZERO_MARKER_COUNT=1"
  echo "R2_R7_OUTER_WRAPPER_EXIT_MARKER_NOT_IN_TEE_LOG=true"
  echo "R2_R7_HUMAN_REVIEW_DECISION=APPROVE_SEALED_EVIDENCE_WITH_EXECUTION_HOLD"
  echo "EVIDENCE_SEAL_COMPLETE=true"
  echo "RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL"
  echo "DEPLOYMENT_AUTHORIZATION_PACKET_STATUS=HOLD_PENDING_CONDITION_RESOLUTION"
  echo "CANDIDATE_DEPLOYED_TO_PRODUCTION=false"
  echo "SUDOERS_CHANGED=false"
  echo "FINAL_APPROVAL_TOKEN_CREATED=false"
  echo "APPROVAL_BINDING_CREATED=false"
  echo "WRITER_FREEZE_EXECUTION=HOLD"
  echo "PRODUCTION_RELEASE_DECISION=HOLD"
  echo "RELEASE_STATUS=CANDIDATE_NOT_APPROVED"
  echo "NEXT_GATE=HUMAN_APPROVAL_FOR_3E_J_R2_R8_ROOT_READONLY_SUDOERS_DESTINATION_VERIFICATION_PACKET_PREPARATION_NO_EXECUTION"

) 2>&1 | tee "$REVIEW_LOG"

REVIEW_RC=${PIPESTATUS[0]}
printf 'REVIEW_COMMAND_EXIT_CODE=%s\n' "$REVIEW_RC"
printf 'REVIEW_OUTPUT=%s\n' "$REVIEW_LOG"
