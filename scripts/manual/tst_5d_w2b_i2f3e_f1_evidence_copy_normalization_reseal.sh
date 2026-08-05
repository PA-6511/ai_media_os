#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PHASE="TST-5D-W2B-I2F-3E-F1"
REPO_ROOT="/home/deploy/ai_media_os"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SOURCE_EVIDENCE_REL="${BASE_REL}/i2f3e-f-writer-attribution-freeze-scope-readonly-20260725T135318Z-509358"
SOURCE_EVIDENCE_ROOT="${REPO_ROOT}/${SOURCE_EVIDENCE_REL}"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_ROOT_REL="${BASE_REL}/i2f3e-f1-evidence-copy-normalization-reseal-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_ROOT_REL}"

SOURCE_SNAPSHOT_ROOT="${EVIDENCE_ROOT}/source-evidence-snapshot"
CORRECTED_PACKET_ROOT="${EVIDENCE_ROOT}/corrected-packet-snapshot"

EXPECTED_SOURCE_RESULT_SHA="6e65e6400c047f9e9bb2081e5e302e1f442049080336ccc22abc4a7a148ea0d3"
EXPECTED_SOURCE_PACKET_MANIFEST_SHA="169dad6ff4609b59405d553e4607b29f5cadeb0dab9ba940c4ce11599147e8be"
EXPECTED_SOURCE_SEMANTIC_VALIDATION_SHA="7a4d85c55916ca2c44e36f2023a3e6c0c065b851074415a13dd45d4a1e98cd2b"
EXPECTED_SOURCE_EVIDENCE_MANIFEST_SHA="1e944406c9659db787016bf41f1b22099b6e82e64536097fbe3ea817605541c9"
EXPECTED_SOURCE_ROOT_PROC_SHA="ebeec25e35d3d8cf517a6de1ff032d04349b80c7abd93c2810dcd3a313e05345"

EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_RUNTIME_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "RUN_AS_ROOT_FORBIDDEN=true" >&2
  exit 1
fi

mkdir "$EVIDENCE_ROOT"

on_error() {
  local rc=$?
  set +e

  if [[ -d "$EVIDENCE_ROOT" && -w "$EVIDENCE_ROOT" ]]; then
    {
      printf 'FAILURE_PHASE=%s\n' "$PHASE"
      printf 'FAILURE_EXIT_CODE=%s\n' "$rc"
      printf 'FAILURE_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_ROOT_REL"
      printf 'SOURCE_EVIDENCE_MUTATION_ALLOWED=false\n'
      printf 'WRITER_FREEZE_EXECUTION=HOLD\n'
      printf 'PRODUCTION_DB_OPENED=false\n'
      printf 'SQL_EXECUTED=false\n'
      printf 'PROCESS_SIGNAL_SENT=false\n'
      printf 'WRITER_STOP_PERFORMED=false\n'
      printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
      printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
    } > "$EVIDENCE_ROOT/failure.txt" 2>/dev/null || true
  fi

  printf 'SCRIPT_EXIT_CODE=%s\n' "$rc"
  exit "$rc"
}
trap on_error ERR

cd "$REPO_ROOT"

test -d "$SOURCE_EVIDENCE_ROOT"
test -f "$SOURCE_EVIDENCE_ROOT/result.json"
test -f "$SOURCE_EVIDENCE_ROOT/packet-snapshot/packet-manifest.json"
test -f "$SOURCE_EVIDENCE_ROOT/packet-snapshot/packet-semantic-validation.json"
test -f "$SOURCE_EVIDENCE_ROOT/packet-snapshot/root-proc-readonly-inspection.json"
test -f "$SOURCE_EVIDENCE_ROOT/packet-snapshot/safety-boundary.json"
test -f "$SOURCE_EVIDENCE_ROOT/packet-snapshot/stop-restart-scope-plan.json"
test -f "$SOURCE_EVIDENCE_ROOT/evidence-manifest.txt"
test -f "$SOURCE_EVIDENCE_ROOT/failure.txt"

cat > "$EVIDENCE_ROOT/human-approval-verbatim.txt" <<'APPROVAL'
承認：
3E_F_ATTRIBUTION_CONTENT=PASS
3E_F_PACKET_CONTENT=PASS
3E_F_EVIDENCE_FINALIZATION=FAIL
APPROVE_3E_F1_EVIDENCE_COPY_NORMALIZATION_AND_RESEAL_NEW_ROOT_ONLY

許可範囲：
1. 失敗済み3E-F Evidence rootを読み取り専用入力として使用する。
2. 元Evidenceは変更、削除、chmod、chown、上書きしない。
3. 新しい一意な3E-F1 Evidence rootを作成する。
4. 元Evidenceの全ファイルについて、相対path、SHA-256、size、owner、group、modeをsource inventoryとして記録する。
5. 元Evidenceの内容を新しいsource-evidence-snapshot領域へbyte-for-byteでコピーする。
6. packet-snapshot内の14ファイルを新しいcorrected packet領域へbyte-for-byteでコピーする。
7. root所有のroot-proc-readonly-inspection.jsonは、元ファイルを変更せず、読取りコピーによってdeploy所有の新規ファイルとして作成する。
8. コピー前後で全ファイルのSHA-256とsize一致を検証する。
9. 実際のPacket manifest名packet-manifest.jsonを使用して内容、file count、各SHA、sizeを検証する。
10. packet-semantic-validation.json、result.json、safety-boundary.jsonのPASS／HOLD境界を再検証する。
11. 新しいEvidence内の全ファイルを最終的に0444、ディレクトリを0555として封印する。
12. 新しいcorrective result、provenance record、Evidence manifestを生成する。
13. 元の失敗Evidence rootと、新しいF1 Evidence rootの双方を永続保持する。

禁止事項：
元Evidenceのchmod、chown、修正、削除、上書き、process signal送信、writer停止、GUI停止・再起動、
systemctl stop/start/restart、cron変更、timer変更、Production DB接続、SQL実行、backup、restore、migration、
manifest変更、source/test変更、git add、git commit、deployment、外部通信、Slack Worker起動、
production approval、production release承認は禁止する。

追加条件：
1. 元EvidenceはFAILED_PARTIAL_PERMISSION_FINALIZATIONとして固定する。
2. 新しいF1 EvidenceはCORRECTED_COPY_RESEALED_NO_SOURCE_MUTATIONとして区別する。
3. ATTRIBUTION判定値は変更しない。
4. exact_restart_command_statusは未解決のまま保持する。
5. 3E-F1成功後の次ゲートは人間レビューとし、Writer freeze実行へ自動遷移しない。

WRITER_FREEZE_EXECUTION=HOLD
PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

python3 - \
  "$REPO_ROOT" \
  "$SOURCE_EVIDENCE_ROOT" \
  "$SOURCE_EVIDENCE_REL" \
  "$EVIDENCE_ROOT" \
  "$EVIDENCE_ROOT_REL" \
  "$SOURCE_SNAPSHOT_ROOT" \
  "$CORRECTED_PACKET_ROOT" \
  "$EXPECTED_SOURCE_RESULT_SHA" \
  "$EXPECTED_SOURCE_PACKET_MANIFEST_SHA" \
  "$EXPECTED_SOURCE_SEMANTIC_VALIDATION_SHA" \
  "$EXPECTED_SOURCE_EVIDENCE_MANIFEST_SHA" \
  "$EXPECTED_SOURCE_ROOT_PROC_SHA" \
  "$EXPECTED_DB_SHA" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_WORKFLOW_SHA" \
  "$EXPECTED_MIGRATION_SHA" \
  "$EXPECTED_SLACK_RUNTIME_SHA" \
  "$EXPECTED_PROMOTED_TEST_SHA" <<'PY'
from __future__ import annotations

import datetime as dt
import grp
import hashlib
import json
import os
import pwd
import stat
import sys
from pathlib import Path
from typing import Any

(
    repo_root_s,
    source_root_s,
    source_rel,
    evidence_root_s,
    evidence_rel,
    source_snapshot_s,
    corrected_packet_s,
    expected_source_result_sha,
    expected_source_packet_manifest_sha,
    expected_source_semantic_sha,
    expected_source_evidence_manifest_sha,
    expected_source_root_proc_sha,
    expected_db_sha,
    expected_manifest_sha,
    expected_workflow_sha,
    expected_migration_sha,
    expected_slack_runtime_sha,
    expected_promoted_test_sha,
) = sys.argv[1:]

repo_root = Path(repo_root_s).resolve()
source_root = Path(source_root_s).resolve()
evidence_root = Path(evidence_root_s).resolve()
source_snapshot_root = Path(source_snapshot_s).resolve()
corrected_packet_root = Path(corrected_packet_s).resolve()

now_utc = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

def fail(message: str) -> None:
    raise RuntimeError(message)

def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def owner_name(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)

def group_name(gid: int) -> str:
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)

def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path}")
    return value

def inventory_tree(root: Path) -> dict[str, Any]:
    require(root.is_dir(), f"INVENTORY_ROOT_MISSING:{root}")

    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []

    root_stat = root.lstat()
    require(not stat.S_ISLNK(root_stat.st_mode), f"ROOT_SYMLINK_FORBIDDEN:{root}")

    for current, dir_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)

        for name in sorted(dir_names):
            path = current_path / name
            metadata = path.lstat()
            require(not stat.S_ISLNK(metadata.st_mode), f"DIRECTORY_SYMLINK_FORBIDDEN:{path}")
            require(stat.S_ISDIR(metadata.st_mode), f"NON_DIRECTORY_ENTRY:{path}")
            directories.append(
                {
                    "relative_path": relative(path, root),
                    "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                    "uid": metadata.st_uid,
                    "gid": metadata.st_gid,
                    "owner": owner_name(metadata.st_uid),
                    "group": group_name(metadata.st_gid),
                }
            )

        for name in sorted(file_names):
            path = current_path / name
            metadata = path.lstat()
            require(not stat.S_ISLNK(metadata.st_mode), f"FILE_SYMLINK_FORBIDDEN:{path}")
            require(stat.S_ISREG(metadata.st_mode), f"NON_REGULAR_FILE_FORBIDDEN:{path}")
            files.append(
                {
                    "relative_path": relative(path, root),
                    "sha256": sha256(path),
                    "size_bytes": metadata.st_size,
                    "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                    "uid": metadata.st_uid,
                    "gid": metadata.st_gid,
                    "owner": owner_name(metadata.st_uid),
                    "group": group_name(metadata.st_gid),
                }
            )

    files.sort(key=lambda item: item["relative_path"])
    directories.sort(key=lambda item: item["relative_path"])

    return {
        "captured_at_utc": now_utc(),
        "root": str(root),
        "file_count": len(files),
        "directory_count_excluding_root": len(directories),
        "files": files,
        "directories": directories,
    }

def comparable_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_count": inventory["file_count"],
        "directory_count_excluding_root": inventory["directory_count_excluding_root"],
        "files": inventory["files"],
        "directories": inventory["directories"],
    }

def safe_copy_file(source: Path, destination: Path) -> dict[str, Any]:
    source_metadata = source.lstat()
    require(stat.S_ISREG(source_metadata.st_mode), f"COPY_SOURCE_NOT_REGULAR:{source}")
    require(not stat.S_ISLNK(source_metadata.st_mode), f"COPY_SOURCE_SYMLINK:{source}")

    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    require(not destination.exists(), f"COPY_DESTINATION_EXISTS:{destination}")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(destination, flags, 0o640)
    try:
        with source.open("rb") as source_stream, os.fdopen(descriptor, "wb", closefd=False) as destination_stream:
            while True:
                chunk = source_stream.read(1024 * 1024)
                if not chunk:
                    break
                destination_stream.write(chunk)
            destination_stream.flush()
            os.fsync(destination_stream.fileno())
    finally:
        os.close(descriptor)

    destination_metadata = destination.lstat()
    require(stat.S_ISREG(destination_metadata.st_mode), f"COPY_DESTINATION_NOT_REGULAR:{destination}")

    source_sha = sha256(source)
    destination_sha = sha256(destination)

    require(source_sha == destination_sha, f"COPY_SHA_MISMATCH:{source}")
    require(source_metadata.st_size == destination_metadata.st_size, f"COPY_SIZE_MISMATCH:{source}")

    return {
        "source": str(source),
        "destination": str(destination),
        "sha256": source_sha,
        "size_bytes": source_metadata.st_size,
        "source_uid": source_metadata.st_uid,
        "source_gid": source_metadata.st_gid,
        "source_owner": owner_name(source_metadata.st_uid),
        "source_group": group_name(source_metadata.st_gid),
        "source_mode": f"{stat.S_IMODE(source_metadata.st_mode):04o}",
        "destination_uid": destination_metadata.st_uid,
        "destination_gid": destination_metadata.st_gid,
        "destination_owner": owner_name(destination_metadata.st_uid),
        "destination_group": group_name(destination_metadata.st_gid),
        "destination_mode_before_seal": f"{stat.S_IMODE(destination_metadata.st_mode):04o}",
        "byte_match": True,
    }

def verify_expected_sha(path: Path, expected: str, label: str) -> None:
    require(path.is_file(), f"{label}_MISSING:{path}")
    actual = sha256(path)
    require(actual == expected, f"{label}_SHA_MISMATCH:expected={expected}:actual={actual}")

# The normalization must be owned by the repository operator, not root.
repo_uid = repo_root.stat().st_uid
repo_gid = repo_root.stat().st_gid
require(os.geteuid() == repo_uid, f"RUNNER_UID_MUST_MATCH_REPOSITORY_OWNER:{os.geteuid()}!={repo_uid}")

require(source_root.is_dir(), f"SOURCE_EVIDENCE_ROOT_MISSING:{source_root}")
require(evidence_root.is_dir(), f"NEW_EVIDENCE_ROOT_MISSING:{evidence_root}")
require(source_root != evidence_root, "SOURCE_AND_DESTINATION_ROOT_MUST_DIFFER")
require(source_root not in evidence_root.parents, "NEW_EVIDENCE_ROOT_MUST_NOT_BE_INSIDE_SOURCE_ROOT")

source_result_path = source_root / "result.json"
source_packet_manifest_path = source_root / "packet-snapshot" / "packet-manifest.json"
source_semantic_path = source_root / "packet-snapshot" / "packet-semantic-validation.json"
source_root_proc_path = source_root / "packet-snapshot" / "root-proc-readonly-inspection.json"
source_safety_path = source_root / "packet-snapshot" / "safety-boundary.json"
source_scope_path = source_root / "packet-snapshot" / "stop-restart-scope-plan.json"
source_attribution_path = source_root / "packet-snapshot" / "process-and-cron-attribution.json"
source_failure_path = source_root / "failure.txt"
source_evidence_manifest_path = source_root / "evidence-manifest.txt"

verify_expected_sha(source_result_path, expected_source_result_sha, "SOURCE_RESULT")
verify_expected_sha(source_packet_manifest_path, expected_source_packet_manifest_sha, "SOURCE_PACKET_MANIFEST")
verify_expected_sha(source_semantic_path, expected_source_semantic_sha, "SOURCE_SEMANTIC_VALIDATION")
verify_expected_sha(source_evidence_manifest_path, expected_source_evidence_manifest_sha, "SOURCE_EVIDENCE_MANIFEST")
verify_expected_sha(source_root_proc_path, expected_source_root_proc_sha, "SOURCE_ROOT_PROC")

live_protected_paths = {
    "production_database": (repo_root / "data/database/ebook_affiliate.db", expected_db_sha),
    "production_manifest": (repo_root / "config/slack_worker_release_source_manifest.json", expected_manifest_sha),
    "workflow_source": (repo_root / "app/db/repositories/workflow_state_repository.py", expected_workflow_sha),
    "migration_source": (repo_root / "migrations/versions/00241611109d_add_unique_wordpress_post_id.py", expected_migration_sha),
    "slack_runtime_source": (repo_root / "scripts/run_slack_approval_socket.py", expected_slack_runtime_sha),
    "promoted_test": (repo_root / "tests/test_slack_approval_socket_hold_remediation_offline.py", expected_promoted_test_sha),
}

live_protected: list[dict[str, Any]] = []
for label, (path, expected) in live_protected_paths.items():
    verify_expected_sha(path, expected, f"LIVE_{label.upper()}")
    metadata = path.stat()
    live_protected.append(
        {
            "label": label,
            "path": str(path),
            "sha256": expected,
            "size_bytes": metadata.st_size,
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        }
    )

write_json(
    evidence_root / "protected-live-sha-verification.json",
    {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-F1",
        "status": "READ_ONLY_SHA_VERIFICATION_PASS",
        "production_database_opened": False,
        "sql_executed": False,
        "files": live_protected,
    },
)

source_inventory_before = inventory_tree(source_root)
write_json(evidence_root / "source-evidence-inventory-before.json", source_inventory_before)

source_files_by_relative = {
    item["relative_path"]: item
    for item in source_inventory_before["files"]
}

root_proc_entry = source_files_by_relative.get("packet-snapshot/root-proc-readonly-inspection.json")
require(root_proc_entry is not None, "ROOT_PROC_INVENTORY_ENTRY_MISSING")
require(root_proc_entry["owner"] == "root", f"ROOT_PROC_SOURCE_OWNER_UNEXPECTED:{root_proc_entry['owner']}")
require(root_proc_entry["group"] == "root", f"ROOT_PROC_SOURCE_GROUP_UNEXPECTED:{root_proc_entry['group']}")
require(root_proc_entry["mode"] == "0644", f"ROOT_PROC_SOURCE_MODE_UNEXPECTED:{root_proc_entry['mode']}")

failure_text = source_failure_path.read_text(encoding="utf-8", errors="replace")
require("FAILURE_EXIT_CODE=1" in failure_text, "SOURCE_FAILURE_EXIT_CODE_NOT_1")
require("FAILURE_PHASE=TST-5D-W2B-I2F-3E-F" in failure_text, "SOURCE_FAILURE_PHASE_INVALID")

source_snapshot_root.mkdir(mode=0o750)
source_copy_records: list[dict[str, Any]] = []

for directory in source_inventory_before["directories"]:
    target_directory = source_snapshot_root / directory["relative_path"]
    target_directory.mkdir(parents=True, exist_ok=False, mode=0o750)

for entry in source_inventory_before["files"]:
    source_path = source_root / entry["relative_path"]
    destination_path = source_snapshot_root / entry["relative_path"]
    source_copy_records.append(safe_copy_file(source_path, destination_path))

source_snapshot_inventory = inventory_tree(source_snapshot_root)
source_snapshot_files = {
    item["relative_path"]: item
    for item in source_snapshot_inventory["files"]
}

require(
    set(source_files_by_relative) == set(source_snapshot_files),
    "SOURCE_SNAPSHOT_FILE_SET_MISMATCH",
)

for relative_path, source_entry in source_files_by_relative.items():
    copied_entry = source_snapshot_files[relative_path]
    require(source_entry["sha256"] == copied_entry["sha256"], f"SOURCE_SNAPSHOT_SHA_MISMATCH:{relative_path}")
    require(source_entry["size_bytes"] == copied_entry["size_bytes"], f"SOURCE_SNAPSHOT_SIZE_MISMATCH:{relative_path}")
    require(copied_entry["uid"] == repo_uid, f"SOURCE_SNAPSHOT_OWNER_UID_INVALID:{relative_path}")
    require(copied_entry["gid"] == repo_gid, f"SOURCE_SNAPSHOT_GROUP_GID_INVALID:{relative_path}")

write_json(
    evidence_root / "source-evidence-snapshot-verification.json",
    {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-F1",
        "status": "SOURCE_EVIDENCE_SNAPSHOT_BYTE_FOR_BYTE_PASS",
        "source_evidence_status": "FAILED_PARTIAL_PERMISSION_FINALIZATION",
        "source_root": str(source_root),
        "snapshot_root": str(source_snapshot_root),
        "source_file_count": source_inventory_before["file_count"],
        "snapshot_file_count": source_snapshot_inventory["file_count"],
        "source_directory_count_excluding_root": source_inventory_before["directory_count_excluding_root"],
        "snapshot_directory_count_excluding_root": source_snapshot_inventory["directory_count_excluding_root"],
        "all_file_sha_and_size_match": True,
        "source_root_proc_owner": root_proc_entry["owner"],
        "source_root_proc_group": root_proc_entry["group"],
        "source_root_proc_mode": root_proc_entry["mode"],
        "snapshot_files_owned_by_repository_operator": True,
        "copy_records": source_copy_records,
    },
)

source_packet_root = source_root / "packet-snapshot"
source_packet_files = sorted(
    path
    for path in source_packet_root.iterdir()
    if path.is_file()
)
require(len(source_packet_files) == 14, f"SOURCE_PACKET_FILE_COUNT_INVALID:{len(source_packet_files)}")
require(not any(path.is_symlink() for path in source_packet_files), "SOURCE_PACKET_SYMLINK_FORBIDDEN")
require(not any(path.is_dir() for path in source_packet_root.iterdir()), "SOURCE_PACKET_NESTED_DIRECTORY_FORBIDDEN")

corrected_packet_root.mkdir(mode=0o750)
packet_copy_records: list[dict[str, Any]] = []

for source_path in source_packet_files:
    destination_path = corrected_packet_root / source_path.name
    packet_copy_records.append(safe_copy_file(source_path, destination_path))

corrected_packet_files = sorted(
    path
    for path in corrected_packet_root.iterdir()
    if path.is_file()
)
require(len(corrected_packet_files) == 14, f"CORRECTED_PACKET_FILE_COUNT_INVALID:{len(corrected_packet_files)}")

corrected_manifest_path = corrected_packet_root / "packet-manifest.json"
require(sha256(corrected_manifest_path) == expected_source_packet_manifest_sha, "CORRECTED_PACKET_MANIFEST_SHA_MISMATCH")
packet_manifest = load_json(corrected_manifest_path)

require(packet_manifest.get("schema_version") == "1.0", "PACKET_MANIFEST_SCHEMA_INVALID")
require(packet_manifest.get("phase") == "TST-5D-W2B-I2F-3E-F", "PACKET_MANIFEST_PHASE_INVALID")
require(
    packet_manifest.get("result") == "PASS_3E_F_WRITER_ATTRIBUTION_FREEZE_SCOPE_PACKET_GENERATED",
    "PACKET_MANIFEST_RESULT_INVALID",
)
require(
    packet_manifest.get("status") == "READONLY_PREPARATION_ONLY_WRITER_FREEZE_NOT_APPROVED",
    "PACKET_MANIFEST_STATUS_INVALID",
)
require(packet_manifest.get("writer_freeze_execution") == "HOLD", "PACKET_MANIFEST_WRITER_FREEZE_INVALID")
require(packet_manifest.get("production_release_decision") == "HOLD", "PACKET_MANIFEST_RELEASE_DECISION_INVALID")
require(packet_manifest.get("release_status") == "CANDIDATE_NOT_APPROVED", "PACKET_MANIFEST_RELEASE_STATUS_INVALID")

manifest_entries = packet_manifest.get("packet_files")
require(isinstance(manifest_entries, list), "PACKET_MANIFEST_FILES_NOT_LIST")
require(packet_manifest.get("packet_file_count_excluding_manifest") == 13, "PACKET_MANIFEST_COUNT_NOT_13")
require(len(manifest_entries) == 13, f"PACKET_MANIFEST_ENTRY_COUNT_INVALID:{len(manifest_entries)}")

manifest_names: set[str] = set()
for raw_entry in manifest_entries:
    require(isinstance(raw_entry, dict), "PACKET_MANIFEST_ENTRY_NOT_OBJECT")
    name = raw_entry.get("name")
    expected_sha = raw_entry.get("sha256")
    expected_size = raw_entry.get("size_bytes")

    require(isinstance(name, str) and name, "PACKET_MANIFEST_NAME_INVALID")
    require(name != "packet-manifest.json", "PACKET_MANIFEST_SELF_ENTRY_FORBIDDEN")
    require(name not in manifest_names, f"PACKET_MANIFEST_DUPLICATE_NAME:{name}")
    manifest_names.add(name)

    path = corrected_packet_root / name
    require(path.is_file(), f"CORRECTED_PACKET_FILE_MISSING:{name}")
    require(sha256(path) == expected_sha, f"CORRECTED_PACKET_SHA_MISMATCH:{name}")
    require(path.stat().st_size == expected_size, f"CORRECTED_PACKET_SIZE_MISMATCH:{name}")

actual_non_manifest_names = {
    path.name
    for path in corrected_packet_files
    if path.name != "packet-manifest.json"
}
require(manifest_names == actual_non_manifest_names, "PACKET_MANIFEST_FILE_SET_MISMATCH")

source_result = load_json(source_result_path)
corrected_result_copy = load_json(source_snapshot_root / "result.json")
corrected_semantic = load_json(corrected_packet_root / "packet-semantic-validation.json")
corrected_safety = load_json(corrected_packet_root / "safety-boundary.json")
corrected_scope = load_json(corrected_packet_root / "stop-restart-scope-plan.json")
corrected_attribution = load_json(corrected_packet_root / "process-and-cron-attribution.json")
corrected_root_proc = load_json(corrected_packet_root / "root-proc-readonly-inspection.json")

require(source_result == corrected_result_copy, "SOURCE_RESULT_COPY_CONTENT_MISMATCH")
require(source_result.get("result") == "PASS_W2B_I2F3E_F_WRITER_ATTRIBUTION_FREEZE_SCOPE_PREPARATION_READY", "SOURCE_RESULT_VALUE_INVALID")
require(source_result.get("writer_freeze_execution") == "HOLD", "SOURCE_RESULT_WRITER_FREEZE_INVALID")
require(source_result.get("production_release_decision") == "HOLD", "SOURCE_RESULT_RELEASE_DECISION_INVALID")
require(source_result.get("release_status") == "CANDIDATE_NOT_APPROVED", "SOURCE_RESULT_RELEASE_STATUS_INVALID")

expected_attribution = {
    "cron": "WINDOW_CONTROL_ONLY",
    "uvicorn": "NOT_RELEVANT",
    "ebook_gui": "STOP_REQUIRED",
    "unresolved_count": 0,
    "root_open_handle_count": 0,
}
require(source_result.get("attribution") == expected_attribution, "SOURCE_RESULT_ATTRIBUTION_CHANGED")

require(
    corrected_semantic.get("result")
    == "PASS_3E_F_WRITER_ATTRIBUTION_FREEZE_SCOPE_PREPARATION_SEMANTIC_VALIDATION",
    "CORRECTED_SEMANTIC_RESULT_INVALID",
)
require(corrected_semantic.get("cron_classification") == "WINDOW_CONTROL_ONLY", "SEMANTIC_CRON_CLASSIFICATION_INVALID")
require(corrected_semantic.get("uvicorn_classification") == "NOT_RELEVANT", "SEMANTIC_UVICORN_CLASSIFICATION_INVALID")
require(corrected_semantic.get("gui_classification") == "STOP_REQUIRED", "SEMANTIC_GUI_CLASSIFICATION_INVALID")
require(corrected_semantic.get("unresolved_count") == 0, "SEMANTIC_UNRESOLVED_COUNT_INVALID")
require(corrected_semantic.get("root_open_handle_count") == 0, "SEMANTIC_ROOT_OPEN_HANDLE_INVALID")
require(corrected_semantic.get("writer_freeze_execution") == "HOLD", "SEMANTIC_WRITER_FREEZE_INVALID")
require(corrected_semantic.get("production_release_decision") == "HOLD", "SEMANTIC_RELEASE_DECISION_INVALID")
require(corrected_semantic.get("release_status") == "CANDIDATE_NOT_APPROVED", "SEMANTIC_RELEASE_STATUS_INVALID")

classification_map = {
    item["logical_writer"]: item["classification"]
    for item in corrected_attribution.get("classifications", [])
}
require(
    classification_map
    == {
        "cron_daemon": "WINDOW_CONTROL_ONLY",
        "uvicorn_8000": "NOT_RELEVANT",
        "ebook_gui_8765": "STOP_REQUIRED",
    },
    "CORRECTED_PACKET_ATTRIBUTION_CLASSIFICATIONS_CHANGED",
)
require(corrected_attribution.get("root_open_handle_count") == 0, "ATTRIBUTION_ROOT_OPEN_HANDLE_COUNT_INVALID")
require(corrected_attribution.get("writer_freeze_execution") == "HOLD", "ATTRIBUTION_WRITER_FREEZE_INVALID")
require(corrected_attribution.get("production_database_opened") is False, "ATTRIBUTION_DB_OPENED")
require(corrected_attribution.get("sql_executed") is False, "ATTRIBUTION_SQL_EXECUTED")

require(
    corrected_scope.get("exact_restart_command_status")
    == "REQUIRES_HUMAN_REVIEW_OF_SYSTEMD_MEMBERSHIP_AND_STDIO",
    "EXACT_RESTART_COMMAND_STATUS_CHANGED",
)
require(corrected_scope.get("writer_freeze_execution") == "HOLD", "SCOPE_WRITER_FREEZE_INVALID")
require(corrected_scope.get("unresolved_count") == 0, "SCOPE_UNRESOLVED_COUNT_INVALID")
require(corrected_scope.get("stop_targets") == ["ebook_gui_8765"], "SCOPE_STOP_TARGETS_INVALID")
require(corrected_scope.get("window_control_targets") == ["cron_daemon"], "SCOPE_WINDOW_TARGETS_INVALID")
require(corrected_scope.get("not_relevant_targets") == ["uvicorn_8000"], "SCOPE_NOT_RELEVANT_TARGETS_INVALID")

require(corrected_root_proc.get("root_privileged_readonly_inspection") is True, "ROOT_PROC_PRIVILEGED_FLAG_INVALID")
require(corrected_root_proc.get("production_database_opened") is False, "ROOT_PROC_DB_OPENED")
require(corrected_root_proc.get("sql_executed") is False, "ROOT_PROC_SQL_EXECUTED")
require(corrected_root_proc.get("root_proc_scan", {}).get("open_handle_count") == 0, "ROOT_PROC_OPEN_HANDLE_COUNT_INVALID")

false_safety_keys = [
    "production_database_opened",
    "production_database_sql_connection_used",
    "sql_executed",
    "process_signal_sent",
    "writer_stop_performed",
    "gui_stopped_or_restarted",
    "systemctl_stop_start_restart_executed",
    "systemd_changed",
    "cron_changed",
    "timer_changed",
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
for key in false_safety_keys:
    require(corrected_safety.get(key) is False, f"SAFETY_FLAG_NOT_FALSE:{key}")

require(corrected_safety.get("writer_freeze_execution") == "HOLD", "SAFETY_WRITER_FREEZE_INVALID")
require(corrected_safety.get("production_release_decision") == "HOLD", "SAFETY_RELEASE_DECISION_INVALID")
require(corrected_safety.get("release_status") == "CANDIDATE_NOT_APPROVED", "SAFETY_RELEASE_STATUS_INVALID")

source_inventory_after = inventory_tree(source_root)
write_json(evidence_root / "source-evidence-inventory-after.json", source_inventory_after)

require(
    comparable_inventory(source_inventory_before)
    == comparable_inventory(source_inventory_after),
    "SOURCE_EVIDENCE_MUTATED_DURING_F1",
)

write_json(
    evidence_root / "corrected-packet-verification.json",
    {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-F1",
        "status": "CORRECTED_PACKET_COPY_AND_SEMANTIC_VALIDATION_PASS",
        "corrected_evidence_status": "CORRECTED_COPY_RESEALED_NO_SOURCE_MUTATION",
        "packet_file_count": len(corrected_packet_files),
        "packet_file_count_excluding_manifest": len(manifest_entries),
        "packet_manifest_filename": "packet-manifest.json",
        "packet_manifest_sha256": sha256(corrected_manifest_path),
        "packet_manifest_file_set_valid": True,
        "all_packet_file_sha_and_size_match": True,
        "attribution_unchanged": True,
        "attribution": expected_attribution,
        "exact_restart_command_status": corrected_scope["exact_restart_command_status"],
        "root_proc_copy_owner": owner_name((corrected_packet_root / "root-proc-readonly-inspection.json").stat().st_uid),
        "root_proc_copy_group": group_name((corrected_packet_root / "root-proc-readonly-inspection.json").stat().st_gid),
        "root_proc_copy_sha256": sha256(corrected_packet_root / "root-proc-readonly-inspection.json"),
        "packet_copy_records": packet_copy_records,
        "writer_freeze_execution": "HOLD",
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
    },
)

provenance = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-F1",
    "created_at_utc": now_utc(),
    "source_evidence": {
        "relative_root": source_rel,
        "absolute_root": str(source_root),
        "status": "FAILED_PARTIAL_PERMISSION_FINALIZATION",
        "result_sha256": expected_source_result_sha,
        "packet_manifest_sha256": expected_source_packet_manifest_sha,
        "packet_semantic_validation_sha256": expected_source_semantic_sha,
        "evidence_manifest_sha256": expected_source_evidence_manifest_sha,
        "root_proc_readonly_inspection_sha256": expected_source_root_proc_sha,
        "failure_exit_code": 1,
        "mutated_by_f1": False,
    },
    "corrective_evidence": {
        "relative_root": evidence_rel,
        "absolute_root": str(evidence_root),
        "status": "CORRECTED_COPY_RESEALED_NO_SOURCE_MUTATION",
        "source_snapshot_root": str(source_snapshot_root),
        "corrected_packet_root": str(corrected_packet_root),
    },
    "normalization": {
        "content_changed": False,
        "byte_for_byte_copy": True,
        "source_root_proc_file_left_root_owned_and_unchanged": True,
        "new_copies_owned_by_repository_operator": True,
        "new_file_final_mode": "0444",
        "new_directory_final_mode": "0555",
    },
    "attribution_preserved": expected_attribution,
    "exact_restart_command_status": corrected_scope["exact_restart_command_status"],
    "next_gate": "HUMAN_REVIEW_3E_F1_CORRECTED_EVIDENCE",
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(evidence_root / "provenance-record.json", provenance)

execution_flags = {
    "source_evidence_chmod_performed": False,
    "source_evidence_chown_performed": False,
    "source_evidence_modified": False,
    "source_evidence_deleted": False,
    "process_signal_sent": False,
    "writer_stop_performed": False,
    "gui_stopped_or_restarted": False,
    "systemd_changed": False,
    "cron_changed": False,
    "timer_changed": False,
    "production_database_opened": False,
    "production_database_sql_connection_used": False,
    "sql_executed": False,
    "backup_created": False,
    "restore_executed": False,
    "migration_executed": False,
    "production_manifest_modified": False,
    "source_modified": False,
    "test_modified": False,
    "git_add_performed": False,
    "git_commit_performed": False,
    "deployment_performed": False,
    "external_network_used": False,
    "slack_worker_started": False,
    "production_approval_created": False,
    "production_release_approved": False,
}

corrective_result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-F1",
    "completed_at_utc": now_utc(),
    "result": "PASS_W2B_I2F3E_F1_EVIDENCE_COPY_NORMALIZED_AND_RESEALED",
    "evidence_root": evidence_rel,
    "source_evidence_root": source_rel,
    "source_evidence_status": "FAILED_PARTIAL_PERMISSION_FINALIZATION",
    "corrected_evidence_status": "CORRECTED_COPY_RESEALED_NO_SOURCE_MUTATION",
    "source_file_count": source_inventory_before["file_count"],
    "source_snapshot_file_count": source_snapshot_inventory["file_count"],
    "source_snapshot_byte_match": True,
    "corrected_packet_file_count": len(corrected_packet_files),
    "packet_manifest_validation": "PASS",
    "packet_semantic_validation": corrected_semantic["result"],
    "attribution_unchanged": True,
    "attribution": expected_attribution,
    "exact_restart_command_status": corrected_scope["exact_restart_command_status"],
    "source_evidence_mutated": False,
    "execution": execution_flags,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_F1_CORRECTED_EVIDENCE",
}
write_json(evidence_root / "corrective-result.json", corrective_result)

preseal_validation = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-F1",
    "result": "PASS_3E_F1_PRESEAL_VALIDATION",
    "source_inventory_before_equals_after": True,
    "source_snapshot_file_set_equal": True,
    "source_snapshot_all_sha_and_size_match": True,
    "corrected_packet_file_count": 14,
    "packet_manifest_file_count_excluding_manifest": 13,
    "packet_manifest_all_sha_and_size_match": True,
    "packet_semantic_validation_pass": True,
    "safety_boundary_preserved": True,
    "attribution_preserved": True,
    "exact_restart_command_status_preserved": True,
    "source_evidence_mutated": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(evidence_root / "preseal-validation.json", preseal_validation)

# Build the evidence manifest only after every other final evidence file exists.
manifest_path = evidence_root / "evidence-manifest.txt"
manifest_lines: list[str] = []
for path in sorted(evidence_root.rglob("*"), key=lambda item: item.relative_to(evidence_root).as_posix()):
    if not path.is_file() or path == manifest_path:
        continue
    manifest_lines.append(
        f"{sha256(path)}  {path.relative_to(evidence_root).as_posix()}"
    )
manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

# Verify the generated evidence manifest before sealing.
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected_sha, relative_path = line.split("  ", 1)
    path = evidence_root / relative_path
    require(path.is_file(), f"EVIDENCE_MANIFEST_FILE_MISSING:{relative_path}")
    require(sha256(path) == expected_sha, f"EVIDENCE_MANIFEST_SHA_MISMATCH:{relative_path}")

# Final source check immediately before sealing.
final_source_inventory = inventory_tree(source_root)
require(
    comparable_inventory(source_inventory_before)
    == comparable_inventory(final_source_inventory),
    "SOURCE_EVIDENCE_MUTATED_BEFORE_SEAL",
)

# Every destination artifact must be owned by the repository operator.
for path in evidence_root.rglob("*"):
    metadata = path.lstat()
    require(not stat.S_ISLNK(metadata.st_mode), f"NEW_EVIDENCE_SYMLINK_FORBIDDEN:{path}")
    require(metadata.st_uid == repo_uid, f"NEW_EVIDENCE_UID_INVALID:{path}:{metadata.st_uid}")
    require(metadata.st_gid == repo_gid, f"NEW_EVIDENCE_GID_INVALID:{path}:{metadata.st_gid}")

# Seal files first, then directories deepest-first, with the evidence root last.
all_files = sorted(
    (path for path in evidence_root.rglob("*") if path.is_file()),
    key=lambda item: item.relative_to(evidence_root).as_posix(),
)
all_directories = sorted(
    (path for path in evidence_root.rglob("*") if path.is_dir()),
    key=lambda item: len(item.relative_to(evidence_root).parts),
    reverse=True,
)

for path in all_files:
    os.chmod(path, 0o444)

for path in all_directories:
    os.chmod(path, 0o555)

os.chmod(evidence_root, 0o555)

# Post-seal verification is read-only.
for path in all_files:
    mode = stat.S_IMODE(path.stat().st_mode)
    require(mode == 0o444, f"POST_SEAL_FILE_MODE_INVALID:{path}:{mode:04o}")

for path in [*all_directories, evidence_root]:
    mode = stat.S_IMODE(path.stat().st_mode)
    require(mode == 0o555, f"POST_SEAL_DIRECTORY_MODE_INVALID:{path}:{mode:04o}")

print(f"RESULT={corrective_result['result']}")
print(f"EVIDENCE_ROOT={evidence_rel}")
print(f"SOURCE_EVIDENCE_ROOT={source_rel}")
print("SOURCE_EVIDENCE_STATUS=FAILED_PARTIAL_PERMISSION_FINALIZATION")
print("CORRECTED_EVIDENCE_STATUS=CORRECTED_COPY_RESEALED_NO_SOURCE_MUTATION")
print(f"SOURCE_FILE_COUNT={source_inventory_before['file_count']}")
print(f"SOURCE_SNAPSHOT_FILE_COUNT={source_snapshot_inventory['file_count']}")
print("SOURCE_SNAPSHOT_BYTE_MATCH=true")
print("SOURCE_EVIDENCE_MUTATED=false")
print("CORRECTED_PACKET_FILE_COUNT=14")
print("PACKET_MANIFEST_FILENAME=packet-manifest.json")
print("PACKET_MANIFEST_VALIDATION=PASS")
print("PACKET_SEMANTIC_VALIDATION=PASS")
print("ATTRIBUTION_UNCHANGED=true")
print("CRON_CLASSIFICATION=WINDOW_CONTROL_ONLY")
print("UVICORN_CLASSIFICATION=NOT_RELEVANT")
print("EBOOK_GUI_CLASSIFICATION=STOP_REQUIRED")
print("UNRESOLVED_CLASSIFICATION_COUNT=0")
print("ROOT_DB_WAL_SHM_OPEN_HANDLE_COUNT=0")
print("EXACT_RESTART_COMMAND_STATUS=REQUIRES_HUMAN_REVIEW_OF_SYSTEMD_MEMBERSHIP_AND_STDIO")
print("ROOT_OWNED_SOURCE_FILE_MUTATED=false")
print("ROOT_PROC_COPY_OWNED_BY_REPOSITORY_OPERATOR=true")
print("ALL_NEW_EVIDENCE_FILES_MODE_0444=true")
print("ALL_NEW_EVIDENCE_DIRECTORIES_MODE_0555=true")
print(f"CORRECTIVE_RESULT_SHA={sha256(evidence_root / 'corrective-result.json')}")
print(f"PROVENANCE_RECORD_SHA={sha256(evidence_root / 'provenance-record.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(evidence_root / 'evidence-manifest.txt')}")
print("PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("PRODUCTION_DB_OPENED=false")
print("PRODUCTION_DB_SQL_CONNECTION_USED=false")
print("SQL_EXECUTED=false")
print("BACKUP_CREATED=false")
print("RESTORE_EXECUTED=false")
print("MIGRATION_EXECUTED=false")
print("PRODUCTION_MANIFEST_MODIFIED=false")
print("SOURCE_MODIFIED=false")
print("TEST_MODIFIED=false")
print("GIT_ADD_PERFORMED=false")
print("GIT_COMMIT_PERFORMED=false")
print("DEPLOYMENT_PERFORMED=false")
print("EXTERNAL_NETWORK_USED=false")
print("SLACK_WORKER_STARTED=false")
print("PRODUCTION_APPROVAL_CREATED=false")
print("PRODUCTION_RELEASE_APPROVED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print("NEXT_GATE=HUMAN_REVIEW_3E_F1_CORRECTED_EVIDENCE")
PY

trap - ERR
printf 'SCRIPT_EXIT_CODE=0\n'
