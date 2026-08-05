#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

REPO_ROOT="/home/deploy/ai_media_os"
PHASE="TST-5D-W2B-I2F-3E-E"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
C1_ROOT_REL="${I2E_ROOT_REL}/i2f3e-c1-manifest-migration-semantic-correction-20260725T184357-503375"
D_ROOT_REL="${I2E_ROOT_REL}/i2f3e-d-slack-test-only-promotion-20260725T122751-507283"

C1_RESULT="${REPO_ROOT}/${C1_ROOT_REL}/result.json"
C1_PACKET_MANIFEST="${REPO_ROOT}/${C1_ROOT_REL}/packet-snapshot/semantic-correction-packet-manifest.json"
D_RESULT="${REPO_ROOT}/${D_ROOT_REL}/result.json"
D_EVIDENCE_MANIFEST="${REPO_ROOT}/${D_ROOT_REL}/test-promotion-evidence-manifest.txt"

DB_REL="data/database/ebook_affiliate.db"
DB_PATH="${REPO_ROOT}/${DB_REL}"
DB_WAL_PATH="${DB_PATH}-wal"
DB_SHM_PATH="${DB_PATH}-shm"
PRODUCTION_MANIFEST_REL="config/slack_worker_release_source_manifest.json"
PRODUCTION_MANIFEST="${REPO_ROOT}/${PRODUCTION_MANIFEST_REL}"
WORKFLOW_SOURCE_REL="app/db/repositories/workflow_state_repository.py"
WORKFLOW_SOURCE="${REPO_ROOT}/${WORKFLOW_SOURCE_REL}"
MIGRATION_SOURCE_REL="migrations/versions/00241611109d_add_unique_wordpress_post_id.py"
MIGRATION_SOURCE="${REPO_ROOT}/${MIGRATION_SOURCE_REL}"
SLACK_SOURCE_REL="scripts/run_slack_approval_socket.py"
SLACK_SOURCE="${REPO_ROOT}/${SLACK_SOURCE_REL}"
PROMOTED_TEST_REL="tests/test_slack_approval_socket_hold_remediation_offline.py"
PROMOTED_TEST="${REPO_ROOT}/${PROMOTED_TEST_REL}"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

EXPECTED_C1_RESULT_SHA="ff1449147a56adede9685fc0c42e10ebd91b796da4e6202f2eb6862714ec9f7b"
EXPECTED_C1_PACKET_MANIFEST_SHA="5158aee338a9b410639eda23f652434767e9dee607f0405d3c4af4a5b62c49cc"
EXPECTED_D_RESULT_SHA="28fcf6d3703d737d02e8412f84407030baf12132007e3e57374004330c737955"
EXPECTED_D_EVIDENCE_MANIFEST_SHA="630295522b6356f0f7e05c8a1130624c604481c0c1e0648d9203ca9e0be5eecb"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SOURCE_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"
EXPECTED_PRE_MIGRATION_REVISION="29962ac6d9a5"
TARGET_MIGRATION_REVISION="00241611109d"
TARGET_INDEX_NAME="uq_ebook_items_wordpress_post_id_not_null"

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

fail() {
    local message="$1"
    local rc="${2:-1}"
    printf 'RESULT=BLOCKED_W2B_I2F3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION\n' >&2
    printf 'ERROR=%s\n' "$message" >&2
    if [[ -n "${EVIDENCE_REL:-}" ]]; then
        printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL" >&2
        printf 'FAILED_EVIDENCE_PRESERVED=true\n' >&2
    fi
    printf 'PRODUCTION_DB_OPENED=false\n' >&2
    printf 'SQL_EXECUTED=false\n' >&2
    printf 'WRITER_STOP_PERFORMED=false\n' >&2
    printf 'BACKUP_CREATED=false\n' >&2
    printf 'RESTORE_EXECUTED=false\n' >&2
    printf 'PRODUCTION_RELEASE_DECISION=HOLD\n' >&2
    printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n' >&2
    exit "$rc"
}

require_file_sha() {
    local path="$1"
    local expected="$2"
    local actual

    [[ -f "$path" ]] || fail "MISSING_FILE:${path}"
    actual="$(sha256_file "$path")"
    [[ "$actual" == "$expected" ]] || fail "SHA_MISMATCH:${path}:expected=${expected}:actual=${actual}"
    printf 'SHA_PASS=%s:%s\n' "$path" "$actual"
}

cd "$REPO_ROOT"

[[ -x "$PYTHON_BIN" ]] || fail "PYTHON_NOT_EXECUTABLE:${PYTHON_BIN}"
[[ -d "${REPO_ROOT}/.git" ]] || fail "GIT_REPOSITORY_REQUIRED"

require_file_sha "$C1_RESULT" "$EXPECTED_C1_RESULT_SHA"
require_file_sha "$C1_PACKET_MANIFEST" "$EXPECTED_C1_PACKET_MANIFEST_SHA"
require_file_sha "$D_RESULT" "$EXPECTED_D_RESULT_SHA"
require_file_sha "$D_EVIDENCE_MANIFEST" "$EXPECTED_D_EVIDENCE_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"
require_file_sha "$PRODUCTION_MANIFEST" "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha "$MIGRATION_SOURCE" "$EXPECTED_MIGRATION_SOURCE_SHA"
require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"
require_file_sha "$PROMOTED_TEST" "$EXPECTED_PROMOTED_TEST_SHA"

PROMOTED_TEST_STATUS="$(git status --porcelain=v1 --untracked-files=all -- "$PROMOTED_TEST_REL")"
[[ "$PROMOTED_TEST_STATUS" == "?? ${PROMOTED_TEST_REL}" ]] || \
    fail "PROMOTED_TEST_EXPECTED_UNTRACKED:${PROMOTED_TEST_STATUS:-EMPTY}"
if git ls-files --error-unmatch "$PROMOTED_TEST_REL" >/dev/null 2>&1; then
    fail "PROMOTED_TEST_UNEXPECTEDLY_TRACKED:${PROMOTED_TEST_REL}"
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3e-e-production-db-preflight-backup-preparation-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3e-e-production-db-preflight-backup-preparation-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
INPUT_ROOT="${EVIDENCE_ROOT}/input-snapshots"

[[ ! -e "$SHADOW_ROOT" ]] || fail "SHADOW_ROOT_EXISTS:${SHADOW_ROOT}"
[[ ! -e "$EVIDENCE_ROOT" ]] || fail "EVIDENCE_ROOT_EXISTS:${EVIDENCE_REL}"
mkdir -p "$SHADOW_ROOT" "$PACKET_ROOT" "$INPUT_ROOT"

APPROVAL_FILE="${PACKET_ROOT}/human-approval-verbatim.txt"
cat > "$APPROVAL_FILE" <<'APPROVAL'
承認：
TEST_PROMOTION_REVIEW=APPROVE
3E_D_TEST_PROMOTION_EVIDENCE_REVIEW=PASS
APPROVE_3E_E_PRODUCTION_DB_PREFLIGHT_AND_BACKUP_PREPARATION_ONLY

許可範囲：
1. Production DBのread-only preflight、writer freeze、
   SQLite backup、restore rehearsalに必要な準備Packetを作成する。
2. 現在のDB、manifest、workflow source、migration source、
   Slack runtime source、昇格済みtestのSHAを読み取り確認する。
3. DB本体、WAL、SHMの存在・パス・ファイル属性を、
   SQLite接続を行わずに確認する。
4. GUI、scheduler、systemd timer、Slack Worker、
   その他DB writer候補の停止・確認手順を設計する。
5. writer freeze後に使用するread-only preflight、
   sqlite3.Connection.backup、restore rehearsalの
   実行コマンドと判定条件を準備する。
6. backup保存先、重複防止、SHA記録、fsync、
   integrity_check、foreign_key_check、
   upgrade／downgrade rehearsalの証跡仕様を準備する。
7. 昇格済みtestが未追跡である状態を記録し、
   後続Release候補へ固定するための処理を別ゲートとして残す。
8. 新しい一意なshadow／evidence領域へ準備資料を保存する。

この段階で禁止する操作：
Production DBをSQLiteで開くこと、SQL実行、writer停止、
GUI停止・再起動、systemd変更、timer変更、backup実作成、
restore実行、migration実行、manifest変更、source変更、
追加のtest変更、git add、git commit、deployment、
production approval、外部通信、Slack Worker起動、
production release承認は禁止する。

PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

cp -- "$C1_RESULT" "${INPUT_ROOT}/3e-c1-result.json"
cp -- "$C1_PACKET_MANIFEST" "${INPUT_ROOT}/3e-c1-packet-manifest.json"
cp -- "$D_RESULT" "${INPUT_ROOT}/3e-d-result.json"
cp -- "$D_EVIDENCE_MANIFEST" "${INPUT_ROOT}/3e-d-evidence-manifest.txt"
cp -- "$PROMOTED_TEST" "${INPUT_ROOT}/promoted-test.py"

PROTECTED_SHA_BEFORE="${SHADOW_ROOT}/protected-sha-before.txt"
sha256sum \
    "$DB_PATH" \
    "$PRODUCTION_MANIFEST" \
    "$WORKFLOW_SOURCE" \
    "$MIGRATION_SOURCE" \
    "$SLACK_SOURCE" \
    "$PROMOTED_TEST" \
    > "$PROTECTED_SHA_BEFORE"

DB_FS_JSON="${PACKET_ROOT}/production-db-filesystem-inventory.json"
DB_HANDLES_JSON="${PACKET_ROOT}/production-db-open-handle-inventory.json"
WRITER_PROCESS_JSON="${PACKET_ROOT}/writer-candidate-process-inventory.json"
SYSTEMD_INVENTORY="${PACKET_ROOT}/systemd-readonly-inventory.txt"
SCHEDULER_INVENTORY="${PACKET_ROOT}/scheduler-readonly-inventory.txt"
PROMOTED_TEST_STATE="${PACKET_ROOT}/promoted-test-release-binding-state.json"
PROTECTED_SHA_JSON="${PACKET_ROOT}/protected-sha-inventory.json"

"$PYTHON_BIN" - \
    "$DB_FS_JSON" \
    "$DB_PATH" \
    "$DB_WAL_PATH" \
    "$DB_SHM_PATH" \
    "$EXPECTED_DB_SHA" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

output = Path(sys.argv[1])
paths = [Path(value) for value in sys.argv[2:5]]
expected_main_sha = sys.argv[5]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path: Path, include_sha: bool) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sqlite_connection_opened": False,
    }
    if not path.exists():
        return record
    metadata = path.stat()
    record.update(
        {
            "is_regular_file": stat.S_ISREG(metadata.st_mode),
            "size_bytes": metadata.st_size,
            "mode": f"0{stat.S_IMODE(metadata.st_mode):03o}",
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
            "inode": metadata.st_ino,
            "device": metadata.st_dev,
            "mtime_ns": metadata.st_mtime_ns,
        }
    )
    if include_sha:
        record["sha256"] = sha256(path)
    return record

main = inventory(paths[0], True)
if main.get("sha256") != expected_main_sha:
    raise SystemExit(
        f"PRODUCTION_DB_SHA_MISMATCH:{main.get('sha256')}:{expected_main_sha}"
    )

result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "FILESYSTEM_INVENTORY_ONLY_NO_SQLITE_CONNECTION",
    "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    "database_files": {
        "main": main,
        "wal": inventory(paths[1], False),
        "shm": inventory(paths[2], False),
    },
    "production_database_opened": False,
    "production_database_sql_connection_used": False,
    "sql_executed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$DB_HANDLES_JSON" \
    "$DB_PATH" \
    "$DB_WAL_PATH" \
    "$DB_SHM_PATH" <<'PY'
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

output = Path(sys.argv[1])
targets = {str(Path(value).resolve()) for value in sys.argv[2:]}
handles: list[dict[str, Any]] = []
permission_denied_count = 0
scanned_pid_count = 0

for proc_dir in sorted(Path("/proc").glob("[0-9]*"), key=lambda p: int(p.name)):
    pid = int(proc_dir.name)
    scanned_pid_count += 1
    fd_dir = proc_dir / "fd"
    try:
        fds = list(fd_dir.iterdir())
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        permission_denied_count += 1
        continue

    try:
        cmdline_raw = (proc_dir / "cmdline").read_bytes()
        cmdline = cmdline_raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        cmdline = ""

    for fd in fds:
        try:
            target = os.readlink(fd)
        except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
            continue
        normalized = target.removesuffix(" (deleted)")
        try:
            resolved = str(Path(normalized).resolve(strict=False))
        except OSError:
            resolved = normalized
        if resolved in targets:
            handles.append(
                {
                    "pid": pid,
                    "fd": fd.name,
                    "target": target,
                    "resolved_target": resolved,
                    "cmdline": cmdline,
                }
            )

result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PROC_FD_READONLY_INVENTORY_ONLY",
    "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    "target_paths": sorted(targets),
    "open_handle_count": len(handles),
    "open_handles": handles,
    "scanned_pid_count": scanned_pid_count,
    "inaccessible_or_vanished_proc_count": permission_denied_count,
    "writer_stop_performed": False,
    "production_database_opened": False,
    "sql_executed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - "$WRITER_PROCESS_JSON" "$REPO_ROOT" <<'PY'
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

output = Path(sys.argv[1])
repo_root = str(Path(sys.argv[2]).resolve())
keywords = (
    "ai_media_os",
    "ebook_affiliate",
    "run_slack_approval_socket",
    "uvicorn",
    "gunicorn",
    "flask",
    "celery",
    "apscheduler",
    "cron",
    "wordpress",
)
records: list[dict[str, Any]] = []

for proc_dir in sorted(Path("/proc").glob("[0-9]*"), key=lambda p: int(p.name)):
    pid = int(proc_dir.name)
    try:
        raw = (proc_dir / "cmdline").read_bytes()
        cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        continue
    if not cmdline:
        continue
    lowered = cmdline.lower()
    if repo_root.lower() not in lowered and not any(word in lowered for word in keywords):
        continue
    try:
        cwd = os.readlink(proc_dir / "cwd")
    except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
        cwd = None
    try:
        exe = os.readlink(proc_dir / "exe")
    except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
        exe = None
    try:
        status_lines = (proc_dir / "status").read_text(encoding="utf-8").splitlines()
        status = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in status_lines
            if ":" in line
        }
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        status = {}
    records.append(
        {
            "pid": pid,
            "ppid": status.get("PPid"),
            "uid": status.get("Uid"),
            "state": status.get("State"),
            "cmdline": cmdline,
            "cwd": cwd,
            "exe": exe,
        }
    )

result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PROCESS_INVENTORY_ONLY_NO_STOP_ACTION",
    "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    "candidate_process_count": len(records),
    "candidate_processes": records,
    "process_signal_sent": False,
    "writer_stop_performed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

{
    printf 'SYSTEMD_READONLY_INVENTORY\n'
    printf 'CAPTURED_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'SYSTEMD_CHANGE_PERFORMED=false\n'
    printf 'SYSTEMCTL_STOP_EXECUTED=false\n'
    printf 'SYSTEMCTL_START_EXECUTED=false\n'
    printf 'SYSTEMCTL_RESTART_EXECUTED=false\n'
    printf 'SYSTEMCTL_ENABLE_DISABLE_EXECUTED=false\n'
    printf '\n===== RELEVANT SERVICES =====\n'
    if command -v systemctl >/dev/null 2>&1; then
        set +e
        timeout 15s systemctl --no-pager --plain --all list-units --type=service 2>&1 \
            | grep -Ei 'ai-media|ai_media|ebook|slack|uvicorn|gunicorn|wordpress|python' || true
        printf 'RELEVANT_SERVICE_QUERY_RC=%s\n' "${PIPESTATUS[0]}"
        printf '\n===== RELEVANT TIMERS =====\n'
        timeout 15s systemctl --no-pager --plain --all list-timers 2>&1 \
            | grep -Ei 'ai-media|ai_media|ebook|slack|wordpress|python|NEXT|LEFT|LAST|PASSED|UNIT|ACTIVATES' || true
        printf 'RELEVANT_TIMER_QUERY_RC=%s\n' "${PIPESTATUS[0]}"
        set -e
    else
        printf 'SYSTEMCTL_AVAILABLE=false\n'
    fi
} > "$SYSTEMD_INVENTORY"

{
    printf 'SCHEDULER_READONLY_INVENTORY\n'
    printf 'CAPTURED_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'CRONTAB_MODIFIED=false\n'
    printf 'TIMER_MODIFIED=false\n'
    printf '\n===== USER CRONTAB =====\n'
    if command -v crontab >/dev/null 2>&1; then
        set +e
        crontab -l 2>&1
        printf 'CRONTAB_LIST_RC=%s\n' "$?"
        set -e
    else
        printf 'CRONTAB_AVAILABLE=false\n'
    fi
    printf '\n===== CRON DIRECTORY FILE NAMES =====\n'
    for directory in /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly; do
        if [[ -d "$directory" ]]; then
            find "$directory" -maxdepth 1 -type f -printf '%p|%m|%u|%g|%s|%TY-%Tm-%TdT%TH:%TM:%TS%Tz\n' 2>/dev/null | LC_ALL=C sort
        fi
    done
    printf '\n===== RELEVANT PROCESS SNAPSHOT =====\n'
    ps -eo pid,ppid,user,lstart,stat,comm,args --no-headers 2>/dev/null \
        | grep -Ei 'ai_media_os|ebook_affiliate|run_slack_approval_socket|uvicorn|gunicorn|celery|apscheduler|cron' \
        | grep -vE 'grep -Ei|tst_5d_w2b_i2f3e_e_' || true
} > "$SCHEDULER_INVENTORY"

"$PYTHON_BIN" - \
    "$PROMOTED_TEST_STATE" \
    "$PROMOTED_TEST_REL" \
    "$EXPECTED_PROMOTED_TEST_SHA" \
    "$PROMOTED_TEST_STATUS" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
target = sys.argv[2]
sha256 = sys.argv[3]
status_line = sys.argv[4]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "target_path": target,
    "sha256": sha256,
    "git_porcelain_status": status_line,
    "is_untracked": status_line == f"?? {target}",
    "is_git_tracked": False,
    "release_candidate_binding_performed": False,
    "git_add_performed": False,
    "git_commit_performed": False,
    "next_required_gate": "SEPARATE_TEST_RELEASE_BINDING_APPROVAL",
    "status": "PROMOTED_TEST_PRESENT_UNTRACKED_BINDING_DEFERRED",
}
if not result["is_untracked"]:
    raise SystemExit(f"PROMOTED_TEST_NOT_UNTRACKED:{status_line}")
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$PROTECTED_SHA_JSON" \
    "$DB_REL" "$EXPECTED_DB_SHA" \
    "$PRODUCTION_MANIFEST_REL" "$EXPECTED_PRODUCTION_MANIFEST_SHA" \
    "$WORKFLOW_SOURCE_REL" "$EXPECTED_WORKFLOW_SOURCE_SHA" \
    "$MIGRATION_SOURCE_REL" "$EXPECTED_MIGRATION_SOURCE_SHA" \
    "$SLACK_SOURCE_REL" "$EXPECTED_SLACK_SOURCE_SHA" \
    "$PROMOTED_TEST_REL" "$EXPECTED_PROMOTED_TEST_SHA" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
items = []
args = sys.argv[2:]
if len(args) % 2:
    raise SystemExit("PATH_SHA_ARGUMENT_COUNT_INVALID")
for index in range(0, len(args), 2):
    items.append({"path": args[index], "sha256": args[index + 1]})
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "READ_ONLY_SHA_INVENTORY_VERIFIED",
    "protected_files": items,
    "production_database_opened": False,
    "sql_executed": False,
    "files_modified": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

README="${PACKET_ROOT}/README.md"
cat > "$README" <<'README'
# 3E-E Production DB Preflight and Backup Preparation Packet

Status: PREPARATION / EVIDENCE ONLY — NOT APPROVED FOR EXECUTION

This packet records the current protected SHA values and filesystem-only
inventory for the production SQLite main, WAL, and SHM paths. It also records
candidate writer processes, read-only systemd/timer/scheduler inventory, and
the untracked state of the promoted Slack offline test.

It prepares, but does not execute:

1. writer freeze and zero-open-handle verification;
2. final SHA and read-only SQLite preflight;
3. `sqlite3.Connection.backup` to a unique destination;
4. backup restore, integrity, foreign-key, upgrade, and downgrade rehearsal;
5. immutable evidence and acceptance criteria.

No production SQLite connection, SQL, writer stop, GUI restart, systemd or
timer change, backup, restore, migration, manifest/source/test change, Git
index operation, deployment, network operation, Slack Worker start, or
production approval is performed.
README

WRITER_FREEZE_PLAN="${PACKET_ROOT}/writer-freeze-plan.json"
READONLY_PREFLIGHT_PLAN="${PACKET_ROOT}/readonly-production-db-preflight-plan.json"
BACKUP_PLAN="${PACKET_ROOT}/sqlite-consistent-backup-plan.json"
RESTORE_PLAN="${PACKET_ROOT}/restore-and-migration-rehearsal-plan.json"
EVIDENCE_SPEC="${PACKET_ROOT}/evidence-and-acceptance-specification.json"
GATE_CHECKLIST="${PACKET_ROOT}/production-db-preflight-backup-gate-checklist.json"

"$PYTHON_BIN" - \
    "$WRITER_FREEZE_PLAN" \
    "$DB_PATH" "$DB_WAL_PATH" "$DB_SHM_PATH" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
db, wal, shm = sys.argv[2:5]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PLAN_ONLY_NOT_EXECUTED",
    "execution_allowed": False,
    "required_prior_approval": "WRITER_FREEZE_EXECUTION_APPROVAL",
    "protected_paths": [db, wal, shm],
    "writer_classes": [
        "GUI or web application process capable of DB writes",
        "scheduled import or workflow runner",
        "systemd service or timer capable of DB writes",
        "cron job capable of DB writes",
        "Slack approval worker",
        "manual Python or shell process using the production DB",
    ],
    "ordered_steps": [
        {
            "order": 1,
            "action": "Resolve exact writer processes, services, timers, and cron entries from the inventories.",
            "stop_action_performed": False,
        },
        {
            "order": 2,
            "action": "Obtain a separate explicit approval naming every process, service, timer, and GUI action to stop.",
            "stop_action_performed": False,
        },
        {
            "order": 3,
            "action": "Record service/timer/process state and DB/WAL/SHM stat inventory immediately before freeze.",
            "stop_action_performed": False,
        },
        {
            "order": 4,
            "action": "Stop only explicitly approved writers using graceful application or service controls; do not use kill -9 without a separate exception approval.",
            "stop_action_performed": False,
        },
        {
            "order": 5,
            "action": "Verify no process has an open fd to the DB, WAL, or SHM path and no approved writer remains active.",
            "stop_action_performed": False,
        },
        {
            "order": 6,
            "action": "Record a freeze token, timestamp, operator, exact stopped units/processes, and rollback/start sequence.",
            "stop_action_performed": False,
        },
        {
            "order": 7,
            "action": "Proceed to final SHA and read-only DB preflight only under its separate approval.",
            "stop_action_performed": False,
        },
    ],
    "acceptance_criteria": {
        "db_wal_shm_open_handle_count": 0,
        "unresolved_writer_candidate_count": 0,
        "writer_state_snapshot_preserved": True,
        "restart_or_rollback_sequence_prepared": True,
        "production_database_opened_during_freeze_verification": False,
    },
    "prohibited": [
        "unapproved process signals",
        "unapproved systemctl stop/start/restart",
        "systemd unit edits",
        "timer edits",
        "GUI restart",
        "production SQLite connection",
        "SQL execution",
    ],
    "writer_stop_performed": False,
    "gui_stopped_or_restarted": False,
    "systemd_changed": False,
    "timer_changed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$READONLY_PREFLIGHT_PLAN" \
    "$DB_PATH" \
    "$EXPECTED_DB_SHA" \
    "$EXPECTED_PRE_MIGRATION_REVISION" \
    "$TARGET_INDEX_NAME" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
db_path, expected_sha, expected_revision, target_index = sys.argv[2:6]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PLAN_ONLY_NOT_EXECUTED",
    "execution_allowed": False,
    "required_prior_gates": [
        "WRITER_FREEZE_EXECUTION_APPROVED_AND_VERIFIED",
        "READONLY_PRODUCTION_DB_PREFLIGHT_EXECUTION_APPROVAL",
    ],
    "source": {
        "path": db_path,
        "expected_sha256_before_open": expected_sha,
        "sqlite_uri": f"file:{db_path}?mode=ro",
        "immutable_parameter_allowed": False,
        "reason_immutable_disabled": "immutable=1 can ignore live WAL state and is not permitted for this preflight",
    },
    "connection_controls": [
        "Use Python sqlite3 URI mode=ro only after writer freeze is verified.",
        "Immediately execute PRAGMA query_only=ON.",
        "Install a SQLite authorizer that denies INSERT, UPDATE, DELETE, DDL, ATTACH, DETACH, transaction writes, and writable PRAGMA operations.",
        "Set a finite busy timeout and abort on any lock or authorizer denial.",
        "Do not change journal_mode, synchronous, locking_mode, user_version, or application_id.",
    ],
    "read_only_checks": [
        {"order": 1, "query": "PRAGMA query_only", "expected": 1},
        {"order": 2, "query": "PRAGMA integrity_check", "expected": ["ok"]},
        {"order": 3, "query": "PRAGMA foreign_key_check", "expected_row_count": 0},
        {"order": 4, "query": "SELECT version_num FROM alembic_version", "expected_single_value": expected_revision},
        {"order": 5, "query": "PRAGMA table_info('ebook_items')", "required_column": "wordpress_post_id"},
        {"order": 6, "query": "PRAGMA index_list('ebook_items')", "forbidden_existing_index": target_index},
        {"order": 7, "query": "SELECT wordpress_post_id, COUNT(*) FROM ebook_items WHERE wordpress_post_id IS NOT NULL GROUP BY wordpress_post_id HAVING COUNT(*) > 1", "expected_row_count": 0},
        {"order": 8, "query": "SELECT COUNT(*) FROM ebook_items WHERE wordpress_post_id IS NULL", "record_only": True},
    ],
    "required_evidence": [
        "source-stat-before.json",
        "source-sha-before.txt",
        "readonly-authorizer-policy.json",
        "readonly-query-log.jsonl",
        "integrity-check.txt",
        "foreign-key-check.txt",
        "alembic-revision.txt",
        "ebook-items-table-info.json",
        "ebook-items-index-list.json",
        "duplicate-non-null-wordpress-post-id-check.json",
        "source-stat-after.json",
        "source-sha-after.txt",
        "readonly-preflight-result.json",
    ],
    "acceptance_criteria": {
        "source_sha_before_equals_expected": True,
        "source_sha_after_equals_before": True,
        "source_inode_size_mtime_unchanged": True,
        "integrity_check": "ok",
        "foreign_key_violation_count": 0,
        "alembic_revision": expected_revision,
        "duplicate_non_null_wordpress_post_id_count": 0,
        "target_index_absent_before_migration": True,
        "authorizer_denial_count": 0,
    },
    "production_database_opened": False,
    "sql_executed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$BACKUP_PLAN" \
    "$DB_PATH" \
    "$EXPECTED_DB_SHA" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
db_path, expected_sha = sys.argv[2:4]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PLAN_ONLY_NOT_EXECUTED",
    "execution_allowed": False,
    "required_prior_gates": [
        "WRITER_FREEZE_EXECUTION_APPROVED_AND_VERIFIED",
        "READONLY_PRODUCTION_DB_PREFLIGHT_PASS",
        "CONSISTENT_SQLITE_BACKUP_EXECUTION_APPROVAL",
    ],
    "source": {
        "path": db_path,
        "expected_sha256_before_open": expected_sha,
        "sqlite_uri": f"file:{db_path}?mode=ro",
    },
    "destination_contract": {
        "root_template": "/home/deploy/ai_media_os/backups/ebook_affiliate/production-release-rehearsal/<UTC_RUN_ID>",
        "database_filename": "ebook_affiliate.pre-migration.sqlite3",
        "must_not_exist_before_execution": True,
        "parent_created_with_mode": "0750",
        "database_file_final_mode": "0440",
        "overwrite_allowed": False,
        "symlink_destination_allowed": False,
    },
    "backup_method": "PYTHON_SQLITE3_CONNECTION_BACKUP_API",
    "ordered_steps": [
        "Reverify writer freeze and zero DB/WAL/SHM open handles.",
        "Record main/WAL/SHM stat inventory and source main SHA before opening.",
        "Create a unique destination directory with O_EXCL-style existence checks.",
        "Open source through SQLite URI mode=ro; do not use immutable=1.",
        "Open only the unique new destination.",
        "Run sqlite3.Connection.backup with progress callbacks and a finite page batch.",
        "Close source and destination connections.",
        "Open destination read-only and run integrity_check and foreign_key_check.",
        "fsync the destination database file.",
        "fsync the destination directory and backup root directory.",
        "Record destination SHA-256, size, inode, mode, and timestamps.",
        "Re-record source main/WAL/SHM stat inventory and source main SHA.",
        "Require source SHA, inode, size, and mtime to equal the before values.",
        "Mark backup eligible for restore rehearsal only after every criterion passes.",
    ],
    "wal_controls": [
        "Record WAL and SHM presence before and after backup.",
        "Do not copy only the live main DB file.",
        "Do not execute wal_checkpoint or change journal_mode.",
        "Abort if writer freeze cannot be proven or source attributes change.",
    ],
    "required_evidence": [
        "backup-approval-verbatim.txt",
        "freeze-verification.json",
        "source-stat-before.json",
        "source-sha-before.txt",
        "backup-progress.jsonl",
        "backup-destination-stat.json",
        "backup-destination-sha.txt",
        "backup-integrity-check.txt",
        "backup-foreign-key-check.txt",
        "fsync-result.json",
        "source-stat-after.json",
        "source-sha-after.txt",
        "consistent-backup-result.json",
        "consistent-backup-evidence-manifest.txt",
    ],
    "backup_created": False,
    "production_database_opened": False,
    "sql_executed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$RESTORE_PLAN" \
    "$EXPECTED_PRE_MIGRATION_REVISION" \
    "$TARGET_MIGRATION_REVISION" \
    "$TARGET_INDEX_NAME" \
    "$EXPECTED_MIGRATION_SOURCE_SHA" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
pre_revision, target_revision, index_name, migration_sha = sys.argv[2:6]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PLAN_ONLY_NOT_EXECUTED",
    "execution_allowed": False,
    "required_prior_gates": [
        "CONSISTENT_SQLITE_BACKUP_PASS",
        "BACKUP_RESTORE_AND_MIGRATION_REHEARSAL_EXECUTION_APPROVAL",
        "PROMOTED_TEST_RELEASE_BINDING_RESOLVED_OR_EXPLICITLY_DEFERRED",
    ],
    "rehearsal_workspace_contract": {
        "root_template": "/tmp/tst-5d-w2b-i2f3e-restore-rehearsal-<UTC_RUN_ID>",
        "production_database_path_forbidden": True,
        "production_manifest_path_forbidden": True,
        "unique_nonexistent_root_required": True,
        "approved_backup_copy_is_only_input_database": True,
    },
    "migration_contract": {
        "migration_revision_before": pre_revision,
        "upgrade_target_revision": target_revision,
        "downgrade_target_revision": pre_revision,
        "migration_source_sha256": migration_sha,
        "expected_unique_partial_index": index_name,
        "expected_table": "ebook_items",
        "expected_columns": ["wordpress_post_id"],
        "expected_where": "wordpress_post_id IS NOT NULL",
    },
    "ordered_steps": [
        "Verify the approved backup SHA and evidence manifest.",
        "Copy the approved backup to a unique temporary rehearsal path; never point Alembic at production.",
        "Record restored-copy SHA, size, inode, mode, and initial Alembic revision.",
        "Run integrity_check and foreign_key_check on the restored copy.",
        "Verify the initial revision exactly matches the migration down_revision.",
        "Seed or verify a fixture state that includes at least two NULL wordpress_post_id values and distinct non-NULL values without modifying production.",
        "Apply only migration revision 00241611109d to the restored copy.",
        "Verify sqlite_master reports the expected unique partial index, table, column, and WHERE predicate.",
        "Verify multiple NULL values remain accepted.",
        "Verify a duplicate non-NULL wordpress_post_id insertion is rejected and rolled back.",
        "Run integrity_check and foreign_key_check after upgrade.",
        "Downgrade exactly to revision 29962ac6d9a5.",
        "Verify the target index is absent and schema revision is restored.",
        "Run integrity_check and foreign_key_check after downgrade.",
        "Create a fresh second restored copy and repeat the upgrade to demonstrate repeatability.",
        "Preserve all commands, environment variables, exit codes, schema dumps, query outputs, and SHA values.",
    ],
    "required_evidence": [
        "restore-input-backup-sha.txt",
        "restore-copy-stat-before.json",
        "restore-copy-sha-before.txt",
        "alembic-revision-before.txt",
        "schema-before.sql",
        "upgrade-command.txt",
        "upgrade-exit-code.txt",
        "alembic-revision-after-upgrade.txt",
        "sqlite-master-index-after-upgrade.json",
        "null-uniqueness-test.txt",
        "duplicate-non-null-rejection-test.txt",
        "integrity-check-after-upgrade.txt",
        "foreign-key-check-after-upgrade.txt",
        "downgrade-command.txt",
        "downgrade-exit-code.txt",
        "alembic-revision-after-downgrade.txt",
        "sqlite-master-index-after-downgrade.json",
        "integrity-check-after-downgrade.txt",
        "foreign-key-check-after-downgrade.txt",
        "repeatability-upgrade-result.json",
        "rehearsal-result.json",
        "rehearsal-evidence-manifest.txt",
    ],
    "acceptance_criteria": {
        "production_path_used": False,
        "upgrade_exit_code": 0,
        "revision_after_upgrade": target_revision,
        "expected_index_present_after_upgrade": True,
        "multiple_null_values_allowed": True,
        "duplicate_non_null_rejected": True,
        "downgrade_exit_code": 0,
        "revision_after_downgrade": pre_revision,
        "expected_index_absent_after_downgrade": True,
        "integrity_check_all_stages": "ok",
        "foreign_key_violation_count_all_stages": 0,
        "repeatability_upgrade_pass": True,
    },
    "restore_executed": False,
    "migration_executed": False,
    "production_database_opened": False,
    "sql_executed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$EVIDENCE_SPEC" \
    "$EXPECTED_DB_SHA" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA" \
    "$EXPECTED_WORKFLOW_SOURCE_SHA" \
    "$EXPECTED_MIGRATION_SOURCE_SHA" \
    "$EXPECTED_SLACK_SOURCE_SHA" \
    "$EXPECTED_PROMOTED_TEST_SHA" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
(db_sha, manifest_sha, workflow_sha, migration_sha, slack_sha, test_sha) = sys.argv[2:8]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PREPARATION_EVIDENCE_SPECIFICATION_ONLY",
    "execution_allowed": False,
    "fixed_inputs": {
        "production_db_sha256": db_sha,
        "production_manifest_sha256": manifest_sha,
        "workflow_source_sha256": workflow_sha,
        "migration_source_sha256": migration_sha,
        "slack_runtime_source_sha256": slack_sha,
        "promoted_test_sha256": test_sha,
    },
    "common_evidence_requirements": [
        "unique run id and non-existing output paths",
        "verbatim human approval",
        "command transcript and exit code for every operation",
        "SHA-256 manifest covering every evidence file",
        "before and after protected SHA inventory",
        "before and after filesystem stat inventory",
        "explicit guard state and blocked-operation count",
        "no overwrite and no destructive cleanup of prior evidence",
        "0444 evidence file permissions after successful finalization",
    ],
    "failure_policy": [
        "stop immediately on the first failed gate",
        "preserve the unique failed evidence root",
        "do not rerun blindly",
        "do not continue to migration, manifest rebind, network, or worker start",
        "require a new explicit approval after root-cause review",
    ],
    "prohibited_current_phase": {
        "production_database_open": True,
        "sql_execution": True,
        "writer_stop": True,
        "gui_stop_or_restart": True,
        "systemd_or_timer_change": True,
        "backup_creation": True,
        "restore_execution": True,
        "migration_execution": True,
        "manifest_change": True,
        "source_change": True,
        "test_change": True,
        "git_add_or_commit": True,
        "deployment": True,
        "external_network": True,
        "slack_worker_start": True,
        "production_approval": True,
    },
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

"$PYTHON_BIN" - \
    "$GATE_CHECKLIST" \
    "$PROMOTED_TEST_REL" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
test_path = sys.argv[2]
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "status": "PREPARATION_PACKET_READY_EXECUTION_NOT_APPROVED",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "completed_prior_gates": [
        "PACKET_CORRECTIVE_REVIEW",
        "TEST_PROMOTION_APPROVAL",
        "TEST_PROMOTION_AND_PROMOTED_TEST_PASS",
    ],
    "current_gate": "PRODUCTION_DB_PREFLIGHT_AND_BACKUP_PREPARATION",
    "current_gate_execution_performed": False,
    "prepared_future_gates": [
        "WRITER_FREEZE",
        "FINAL_SHA_AND_READONLY_DB_PREFLIGHT",
        "CONSISTENT_SQLITE_BACKUP",
        "BACKUP_RESTORE_AND_MIGRATION_REHEARSAL",
    ],
    "unresolved_separate_gate": {
        "gate": "PROMOTED_TEST_RELEASE_BINDING",
        "target_path": test_path,
        "current_state": "UNTRACKED",
        "git_add_performed": False,
        "git_commit_performed": False,
    },
    "next_gate": "HUMAN_REVIEW_3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_PACKET",
    "production_database_opened": False,
    "sql_executed": False,
    "writer_stop_performed": False,
    "backup_created": False,
    "restore_executed": False,
    "migration_executed": False,
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

VALIDATOR="${PACKET_ROOT}/validate_production_db_preflight_backup_preparation_packet.py"
cat > "$VALIDATOR" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(packet: Path) -> dict[str, Any]:
    required = {
        "README.md",
        "human-approval-verbatim.txt",
        "protected-sha-inventory.json",
        "production-db-filesystem-inventory.json",
        "production-db-open-handle-inventory.json",
        "writer-candidate-process-inventory.json",
        "systemd-readonly-inventory.txt",
        "scheduler-readonly-inventory.txt",
        "promoted-test-release-binding-state.json",
        "writer-freeze-plan.json",
        "readonly-production-db-preflight-plan.json",
        "sqlite-consistent-backup-plan.json",
        "restore-and-migration-rehearsal-plan.json",
        "evidence-and-acceptance-specification.json",
        "production-db-preflight-backup-gate-checklist.json",
        "validate_production_db_preflight_backup_preparation_packet.py",
    }
    actual = {path.name for path in packet.iterdir() if path.is_file()}
    require(actual == required, f"PACKET_FILE_SET_INVALID:{sorted(actual)}")

    protected = load(packet / "protected-sha-inventory.json")
    require(protected.get("status") == "READ_ONLY_SHA_INVENTORY_VERIFIED", "PROTECTED_SHA_STATUS_INVALID")
    entries = protected.get("protected_files")
    require(isinstance(entries, list) and len(entries) == 6, "PROTECTED_SHA_COUNT_INVALID")
    require(all(isinstance(item.get("sha256"), str) and SHA_RE.fullmatch(item["sha256"]) for item in entries), "PROTECTED_SHA_FORMAT_INVALID")
    require(protected.get("production_database_opened") is False, "PROTECTED_DB_OPEN_FLAG_INVALID")
    require(protected.get("sql_executed") is False, "PROTECTED_SQL_FLAG_INVALID")

    filesystem = load(packet / "production-db-filesystem-inventory.json")
    require(filesystem.get("status") == "FILESYSTEM_INVENTORY_ONLY_NO_SQLITE_CONNECTION", "FILESYSTEM_STATUS_INVALID")
    require(filesystem.get("production_database_opened") is False, "FILESYSTEM_DB_OPEN_FLAG_INVALID")
    require(filesystem.get("production_database_sql_connection_used") is False, "FILESYSTEM_DB_CONNECTION_FLAG_INVALID")
    require(filesystem.get("sql_executed") is False, "FILESYSTEM_SQL_FLAG_INVALID")
    main = filesystem.get("database_files", {}).get("main", {})
    require(main.get("exists") is True and main.get("is_regular_file") is True, "MAIN_DB_FILE_INVALID")
    require(isinstance(main.get("sha256"), str) and SHA_RE.fullmatch(main["sha256"]), "MAIN_DB_SHA_INVALID")

    handles = load(packet / "production-db-open-handle-inventory.json")
    require(handles.get("status") == "PROC_FD_READONLY_INVENTORY_ONLY", "HANDLE_STATUS_INVALID")
    require(isinstance(handles.get("open_handle_count"), int), "HANDLE_COUNT_INVALID")
    require(handles.get("writer_stop_performed") is False, "HANDLE_WRITER_STOP_FLAG_INVALID")
    require(handles.get("production_database_opened") is False, "HANDLE_DB_OPEN_FLAG_INVALID")

    process_inventory = load(packet / "writer-candidate-process-inventory.json")
    require(process_inventory.get("status") == "PROCESS_INVENTORY_ONLY_NO_STOP_ACTION", "PROCESS_STATUS_INVALID")
    require(process_inventory.get("process_signal_sent") is False, "PROCESS_SIGNAL_FLAG_INVALID")
    require(process_inventory.get("writer_stop_performed") is False, "PROCESS_STOP_FLAG_INVALID")

    promoted = load(packet / "promoted-test-release-binding-state.json")
    require(promoted.get("is_untracked") is True, "PROMOTED_TEST_NOT_UNTRACKED")
    require(promoted.get("is_git_tracked") is False, "PROMOTED_TEST_TRACKED_FLAG_INVALID")
    require(promoted.get("git_add_performed") is False, "PROMOTED_TEST_GIT_ADD_FLAG_INVALID")
    require(promoted.get("git_commit_performed") is False, "PROMOTED_TEST_GIT_COMMIT_FLAG_INVALID")
    require(promoted.get("release_candidate_binding_performed") is False, "PROMOTED_TEST_BINDING_FLAG_INVALID")

    writer = load(packet / "writer-freeze-plan.json")
    readonly = load(packet / "readonly-production-db-preflight-plan.json")
    backup = load(packet / "sqlite-consistent-backup-plan.json")
    restore = load(packet / "restore-and-migration-rehearsal-plan.json")
    evidence = load(packet / "evidence-and-acceptance-specification.json")
    gate = load(packet / "production-db-preflight-backup-gate-checklist.json")

    for name, plan in (("writer", writer), ("readonly", readonly), ("backup", backup), ("restore", restore), ("evidence", evidence)):
        require(plan.get("execution_allowed") is False, f"PLAN_EXECUTION_ALLOWED:{name}")
        require("PLAN_ONLY" in str(plan.get("status")) or "SPECIFICATION_ONLY" in str(plan.get("status")), f"PLAN_STATUS_INVALID:{name}")

    require(writer.get("writer_stop_performed") is False, "WRITER_STOP_PERFORMED")
    require(writer.get("gui_stopped_or_restarted") is False, "GUI_STOP_RESTART_PERFORMED")
    require(writer.get("systemd_changed") is False, "SYSTEMD_CHANGED")
    require(writer.get("timer_changed") is False, "TIMER_CHANGED")
    require(readonly.get("production_database_opened") is False, "READONLY_DB_OPENED")
    require(readonly.get("sql_executed") is False, "READONLY_SQL_EXECUTED")
    require(backup.get("backup_created") is False, "BACKUP_CREATED")
    require(backup.get("production_database_opened") is False, "BACKUP_DB_OPENED")
    require(restore.get("restore_executed") is False, "RESTORE_EXECUTED")
    require(restore.get("migration_executed") is False, "MIGRATION_EXECUTED")

    destination = backup.get("destination_contract", {})
    require(destination.get("must_not_exist_before_execution") is True, "BACKUP_NO_OVERWRITE_GATE_MISSING")
    require(destination.get("overwrite_allowed") is False, "BACKUP_OVERWRITE_ALLOWED")
    require(destination.get("symlink_destination_allowed") is False, "BACKUP_SYMLINK_ALLOWED")
    require(backup.get("backup_method") == "PYTHON_SQLITE3_CONNECTION_BACKUP_API", "BACKUP_METHOD_INVALID")

    migration = restore.get("migration_contract", {})
    require(migration.get("migration_revision_before") == "29962ac6d9a5", "PRE_REVISION_INVALID")
    require(migration.get("upgrade_target_revision") == "00241611109d", "TARGET_REVISION_INVALID")
    require(migration.get("expected_unique_partial_index") == "uq_ebook_items_wordpress_post_id_not_null", "TARGET_INDEX_INVALID")

    require(gate.get("production_release_decision") == "HOLD", "GATE_RELEASE_DECISION_INVALID")
    require(gate.get("release_status") == "CANDIDATE_NOT_APPROVED", "GATE_RELEASE_STATUS_INVALID")
    require(gate.get("current_gate_execution_performed") is False, "CURRENT_GATE_EXECUTED")
    require(gate.get("production_database_opened") is False, "GATE_DB_OPENED")
    require(gate.get("sql_executed") is False, "GATE_SQL_EXECUTED")
    require(gate.get("writer_stop_performed") is False, "GATE_WRITER_STOPPED")
    require(gate.get("backup_created") is False, "GATE_BACKUP_CREATED")
    require(gate.get("restore_executed") is False, "GATE_RESTORE_EXECUTED")
    require(gate.get("migration_executed") is False, "GATE_MIGRATION_EXECUTED")

    return {
        "schema_version": "1.0",
        "result": "PASS_3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_SEMANTIC_VALIDATION",
        "packet_file_count_before_manifest": len(required),
        "protected_sha_count": 6,
        "production_db_filesystem_inventory_valid": True,
        "db_open_handle_inventory_valid": True,
        "writer_process_inventory_valid": True,
        "promoted_test_untracked_state_recorded": True,
        "writer_freeze_plan_valid": True,
        "readonly_preflight_plan_valid": True,
        "consistent_backup_plan_valid": True,
        "restore_migration_rehearsal_plan_valid": True,
        "production_database_opened": False,
        "sql_executed": False,
        "writer_stop_performed": False,
        "backup_created": False,
        "restore_executed": False,
        "migration_executed": False,
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = validate(Path(args.packet).resolve())
    except Exception as exc:
        print(f"VALIDATION_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    Path(args.output).resolve().write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

VALIDATION_JSON="${PACKET_ROOT}/preparation-packet-semantic-validation.json"
PYTHONPYCACHEPREFIX="${SHADOW_ROOT}/pycache" "$PYTHON_BIN" -m py_compile "$VALIDATOR"
"$PYTHON_BIN" "$VALIDATOR" --packet "$PACKET_ROOT" --output "$VALIDATION_JSON"

PROTECTED_SHA_AFTER="${SHADOW_ROOT}/protected-sha-after.txt"
sha256sum \
    "$DB_PATH" \
    "$PRODUCTION_MANIFEST" \
    "$WORKFLOW_SOURCE" \
    "$MIGRATION_SOURCE" \
    "$SLACK_SOURCE" \
    "$PROMOTED_TEST" \
    > "$PROTECTED_SHA_AFTER"
cmp -s "$PROTECTED_SHA_BEFORE" "$PROTECTED_SHA_AFTER" || fail "PROTECTED_SHA_CHANGED_DURING_PREPARATION"

FINAL_PROMOTED_TEST_STATUS="$(git status --porcelain=v1 --untracked-files=all -- "$PROMOTED_TEST_REL")"
[[ "$FINAL_PROMOTED_TEST_STATUS" == "?? ${PROMOTED_TEST_REL}" ]] || \
    fail "PROMOTED_TEST_STATE_CHANGED:${FINAL_PROMOTED_TEST_STATUS:-EMPTY}"
[[ "$(sha256_file "$PROMOTED_TEST")" == "$EXPECTED_PROMOTED_TEST_SHA" ]] || \
    fail "PROMOTED_TEST_SHA_CHANGED"

cp -- "$PROTECTED_SHA_BEFORE" "${EVIDENCE_ROOT}/protected-sha-before.txt"
cp -- "$PROTECTED_SHA_AFTER" "${EVIDENCE_ROOT}/protected-sha-after.txt"
printf '%s\n' "$PROMOTED_TEST_STATUS" > "${EVIDENCE_ROOT}/promoted-test-git-status-before.txt"
printf '%s\n' "$FINAL_PROMOTED_TEST_STATUS" > "${EVIDENCE_ROOT}/promoted-test-git-status-after.txt"

PACKET_MANIFEST="${PACKET_ROOT}/production-db-preflight-backup-preparation-packet-manifest.json"
"$PYTHON_BIN" - \
    "$PACKET_MANIFEST" \
    "$PACKET_ROOT" \
    "$EVIDENCE_REL" \
    "$RUN_ID" \
    "$DB_HANDLES_JSON" \
    "$WRITER_PROCESS_JSON" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

output = Path(sys.argv[1])
packet = Path(sys.argv[2])
evidence_rel = sys.argv[3]
run_id = sys.argv[4]
handles_path = Path(sys.argv[5])
processes_path = Path(sys.argv[6])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

files = []
for path in sorted(packet.iterdir(), key=lambda item: item.name):
    if not path.is_file() or path == output:
        continue
    files.append(
        {
            "name": path.name,
            "sha256": sha(path),
            "size_bytes": path.stat().st_size,
        }
    )
handles = json.loads(handles_path.read_text(encoding="utf-8"))
processes = json.loads(processes_path.read_text(encoding="utf-8"))
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "result": "PASS_3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_PACKET_GENERATED",
    "status": "PREPARATION_ONLY_NOT_APPROVED_FOR_EXECUTION",
    "run_id": run_id,
    "evidence_root": evidence_rel,
    "packet_file_count_excluding_manifest": len(files),
    "packet_files": files,
    "observations": {
        "current_db_wal_shm_open_handle_count": handles.get("open_handle_count"),
        "current_writer_candidate_process_count": processes.get("candidate_process_count"),
        "promoted_test_state": "UNTRACKED",
    },
    "prepared_plans": {
        "writer_freeze": True,
        "readonly_production_db_preflight": True,
        "consistent_sqlite_backup": True,
        "restore_and_migration_rehearsal": True,
        "evidence_and_acceptance_specification": True,
    },
    "execution": {
        "production_database_opened": False,
        "production_database_sql_connection_used": False,
        "sql_executed": False,
        "writer_stop_performed": False,
        "gui_stopped_or_restarted": False,
        "systemd_changed": False,
        "timer_changed": False,
        "backup_created": False,
        "restore_executed": False,
        "migration_executed": False,
        "production_manifest_modified": False,
        "source_modified": False,
        "test_modified": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "deployment_performed": False,
        "production_approval_created": False,
        "external_network_used": False,
        "slack_worker_started": False,
        "production_release_approved": False,
    },
    "governance": {
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "next_gate": "HUMAN_REVIEW_3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_PACKET",
    },
    "completed_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
}
output.write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
"$PYTHON_BIN" - \
    "$RESULT_JSON" \
    "$EVIDENCE_REL" \
    "$PACKET_MANIFEST" \
    "$VALIDATION_JSON" \
    "$DB_HANDLES_JSON" \
    "$WRITER_PROCESS_JSON" \
    "$APPROVAL_FILE" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    result_path,
    evidence_rel,
    packet_manifest,
    validation,
    handles,
    processes,
    approval,
) = sys.argv[1:]


def sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

handle_data = json.loads(Path(handles).read_text(encoding="utf-8"))
process_data = json.loads(Path(processes).read_text(encoding="utf-8"))
result = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3E-E",
    "result": "PASS_W2B_I2F3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_READY",
    "evidence_root": evidence_rel,
    "approval": {
        "approval_label": "APPROVE_3E_E_PRODUCTION_DB_PREFLIGHT_AND_BACKUP_PREPARATION_ONLY",
        "approval_verbatim_sha256": sha(approval),
    },
    "packet": {
        "manifest_sha256": sha(packet_manifest),
        "semantic_validation_sha256": sha(validation),
        "semantic_validation": "PASS",
    },
    "inventory": {
        "db_wal_shm_filesystem_inventory_created": True,
        "db_open_handle_inventory_created": True,
        "current_open_handle_count": handle_data.get("open_handle_count"),
        "writer_candidate_process_inventory_created": True,
        "current_writer_candidate_process_count": process_data.get("candidate_process_count"),
        "systemd_readonly_inventory_created": True,
        "scheduler_readonly_inventory_created": True,
    },
    "prepared": {
        "writer_freeze_plan": True,
        "readonly_production_db_preflight_plan": True,
        "consistent_sqlite_backup_plan": True,
        "restore_and_migration_rehearsal_plan": True,
        "evidence_acceptance_specification": True,
        "promoted_test_untracked_state_recorded": True,
    },
    "execution": {
        "production_database_opened": False,
        "production_database_sql_connection_used": False,
        "sql_executed": False,
        "writer_stop_performed": False,
        "gui_stopped_or_restarted": False,
        "systemd_changed": False,
        "timer_changed": False,
        "backup_created": False,
        "restore_executed": False,
        "migration_executed": False,
        "production_manifest_modified": False,
        "source_modified": False,
        "test_modified": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "deployment_performed": False,
        "production_approval_created": False,
        "external_network_used": False,
        "slack_worker_started": False,
        "production_release_approved": False,
    },
    "governance": {
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "next_gate": "HUMAN_REVIEW_3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_PACKET",
    },
    "completed_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
}
Path(result_path).write_text(
    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/production-db-preflight-backup-preparation-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'production-db-preflight-backup-preparation-evidence-manifest.txt' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"

PACKET_FILE_COUNT="$(find "$PACKET_ROOT" -maxdepth 1 -type f | wc -l | tr -d ' ')"
PACKET_MANIFEST_SHA="$(sha256_file "$PACKET_MANIFEST")"
VALIDATION_SHA="$(sha256_file "$VALIDATION_JSON")"
RESULT_SHA="$(sha256_file "$RESULT_JSON")"
EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"
OPEN_HANDLE_COUNT="$($PYTHON_BIN -c 'import json,sys; print(json.load(open(sys.argv[1]))["open_handle_count"])' "$DB_HANDLES_JSON")"
WRITER_CANDIDATE_COUNT="$($PYTHON_BIN -c 'import json,sys; print(json.load(open(sys.argv[1]))["candidate_process_count"])' "$WRITER_PROCESS_JSON")"

find "$EVIDENCE_ROOT" -type f -exec chmod 0444 {} +

printf '\nRESULT=PASS_W2B_I2F3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_READY\n'
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'PACKET_FILE_COUNT=%s\n' "$PACKET_FILE_COUNT"
printf 'PACKET_STATUS=PREPARATION_ONLY_NOT_APPROVED_FOR_EXECUTION\n'
printf 'PACKET_MANIFEST_SHA=%s\n' "$PACKET_MANIFEST_SHA"
printf 'PACKET_SEMANTIC_VALIDATION=PASS\n'
printf 'PACKET_SEMANTIC_VALIDATION_SHA=%s\n' "$VALIDATION_SHA"
printf 'DB_WAL_SHM_FILESYSTEM_INVENTORY_CREATED=true\n'
printf 'DB_OPEN_HANDLE_INVENTORY_CREATED=true\n'
printf 'CURRENT_DB_WAL_SHM_OPEN_HANDLE_COUNT=%s\n' "$OPEN_HANDLE_COUNT"
printf 'WRITER_CANDIDATE_PROCESS_INVENTORY_CREATED=true\n'
printf 'CURRENT_WRITER_CANDIDATE_PROCESS_COUNT=%s\n' "$WRITER_CANDIDATE_COUNT"
printf 'SYSTEMD_READONLY_INVENTORY_CREATED=true\n'
printf 'SCHEDULER_READONLY_INVENTORY_CREATED=true\n'
printf 'WRITER_FREEZE_PLAN_CREATED=true\n'
printf 'READONLY_PRODUCTION_DB_PREFLIGHT_PLAN_CREATED=true\n'
printf 'CONSISTENT_SQLITE_BACKUP_PLAN_CREATED=true\n'
printf 'RESTORE_MIGRATION_REHEARSAL_PLAN_CREATED=true\n'
printf 'PROMOTED_TEST_STATE=UNTRACKED\n'
printf 'PROMOTED_TEST_RELEASE_BINDING_PERFORMED=false\n'
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'PRODUCTION_DB_OPENED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'SQL_EXECUTED=false\n'
printf 'WRITER_STOP_PERFORMED=false\n'
printf 'GUI_STOPPED_OR_RESTARTED=false\n'
printf 'SYSTEMD_CHANGED=false\n'
printf 'TIMER_CHANGED=false\n'
printf 'BACKUP_CREATED=false\n'
printf 'RESTORE_EXECUTED=false\n'
printf 'MIGRATION_EXECUTED=false\n'
printf 'PRODUCTION_MANIFEST_MODIFIED=false\n'
printf 'SOURCE_MODIFIED=false\n'
printf 'TEST_MODIFIED=false\n'
printf 'GIT_ADD_PERFORMED=false\n'
printf 'GIT_COMMIT_PERFORMED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'PRODUCTION_APPROVAL_CREATED=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'SLACK_WORKER_STARTED=false\n'
printf 'PRODUCTION_RELEASE_APPROVED=false\n'
printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'NEXT_GATE=HUMAN_REVIEW_3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION_PACKET\n'
printf 'SCRIPT_EXIT_CODE=0\n'
