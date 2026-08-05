#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PHASE="TST-5D-W2B-I2F-3E-I-R1"
REPO_ROOT="/home/deploy/ai_media_os"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

E_REL="${BASE_REL}/i2f3e-e-production-db-preflight-backup-preparation-20260725T133523-508590"
F1_REL="${BASE_REL}/i2f3e-f1-evidence-copy-normalization-reseal-20260725T140856Z-509951"
G_R1_REL="${BASE_REL}/i2f3e-g-r1-gui-stop-restart-route-resolution-readonly-20260725T143015Z-510846"
H_REL="${BASE_REL}/i2f3e-h-gui-restart-environment-contract-readonly-20260725T144423Z-511462"

E_ROOT="${REPO_ROOT}/${E_REL}"
F1_ROOT="${REPO_ROOT}/${F1_REL}"
G_R1_ROOT="${REPO_ROOT}/${G_R1_REL}"
H_ROOT="${REPO_ROOT}/${H_REL}"

EXPECTED_E_RESULT_SHA="12437e404ee24af88a8bb80be055cd7dba87b55c178a131176673b137b2ffaa7"
EXPECTED_E_PACKET_MANIFEST_SHA="c0a352cdfcda2c54e7ac35a8b754a6a47c0b2f8ee3b26891586e844f44721d91"
EXPECTED_E_EVIDENCE_MANIFEST_SHA="c903d0855fb8e45fc04ade2d4f55c1acfde61c6089dcdeca5b44caa5b83b96e8"

EXPECTED_F1_RESULT_SHA="05eb0ac5f36e4e8b346be8a633cecb3d5798469f5901f1d799074bb7a43450ce"
EXPECTED_F1_PROVENANCE_SHA="4e05d14be765be28e6f6ae6be147e34b917164cd50ce053ae84e09757dc662ec"
EXPECTED_F1_EVIDENCE_MANIFEST_SHA="b71be1255a523257354cf089b50eaab4ea96151fca738f97a9398e15a84d08fb"

EXPECTED_G_R1_RESULT_SHA="31691e1bec7352e29f422ff3ea460b7e2451c977b730e28ec7dde611a1c47736"
EXPECTED_G_R1_PACKET_MANIFEST_SHA="4ca71f34df8ca6c8eced060eacaeb0d28d6b672a373550c886ac0439e0652b92"
EXPECTED_G_R1_EVIDENCE_MANIFEST_SHA="1a0c5216932643e08b80d6271be90275c77f2686e910fc2b829e623645ed7002"

EXPECTED_H_RESULT_SHA="998e6dbbb3bfc2e9357b490c15e731b0c17e6370a9ec95798ca4592612e020fa"
EXPECTED_H_PACKET_MANIFEST_SHA="9dd2e603f69b277db0a115e2970317dc454c5c1346ff8f03a3733fd850fb08b3"
EXPECTED_H_SEMANTIC_SHA="933aff0c381859f46c9317ac5f704d729db2fff214a3b13c67fafdb619a521b3"
EXPECTED_H_EVIDENCE_MANIFEST_SHA="4f330c224f2cac61e58f7f2b25b7091eb622f40240e6efca049d3a87b745670d"

EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_RUNTIME_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"

EXPECTED_PROCESS_IDENTITY_SHA="3dcadb53adeadac94cb1062d2a4e24c2a00d63a51c87991046b96cd7f0f6ba2a"

TARGET_SCRIPT="${REPO_ROOT}/scripts/new_release_multistore_app.py"
TARGET_HOST="127.0.0.1"
TARGET_PORT="8765"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_REL="${BASE_REL}/i2f3e-i-r1-writer-freeze-backup-execution-packet-prep-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
INPUT_ROOT="${EVIDENCE_ROOT}/input-snapshots"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "RUN_AS_ROOT_FORBIDDEN=true" >&2
  exit 1
fi

mkdir "$EVIDENCE_ROOT"
mkdir "$PACKET_ROOT"
mkdir "$INPUT_ROOT"

on_error() {
  local rc=$?
  set +e
  if [[ -d "$EVIDENCE_ROOT" && -w "$EVIDENCE_ROOT" ]]; then
    {
      printf 'FAILURE_PHASE=%s\n' "$PHASE"
      printf 'FAILURE_EXIT_CODE=%s\n' "$rc"
      printf 'FAILURE_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
      printf 'PROCESS_SIGNAL_SENT=false\n'
      printf 'WRITER_STOP_PERFORMED=false\n'
      printf 'GUI_STOPPED_OR_RESTARTED=false\n'
      printf 'CRONTAB_CHANGED=false\n'
      printf 'PRODUCTION_DB_OPENED=false\n'
      printf 'SQL_EXECUTED=false\n'
      printf 'BACKUP_CREATED=false\n'
      printf 'RESTORE_EXECUTED=false\n'
      printf 'WRITER_FREEZE_EXECUTION=HOLD\n'
      printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
      printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
    } > "$EVIDENCE_ROOT/failure.txt" 2>/dev/null || true
  fi
  printf 'SCRIPT_EXIT_CODE=%s\n' "$rc"
  exit "$rc"
}
trap on_error ERR

cd "$REPO_ROOT"

required_inputs=(
  "$E_ROOT/result.json"
  "$E_ROOT/packet-snapshot/production-db-preflight-backup-preparation-packet-manifest.json"
  "$E_ROOT/production-db-preflight-backup-preparation-evidence-manifest.txt"

  "$F1_ROOT/corrective-result.json"
  "$F1_ROOT/provenance-record.json"
  "$F1_ROOT/evidence-manifest.txt"
  "$F1_ROOT/corrected-packet-snapshot/cron-readonly-inventory.txt"
  "$F1_ROOT/corrected-packet-snapshot/freeze-window-plan.json"
  "$F1_ROOT/corrected-packet-snapshot/process-and-cron-attribution.json"
  "$F1_ROOT/corrected-packet-snapshot/root-proc-readonly-inspection.json"

  "$G_R1_ROOT/result.json"
  "$G_R1_ROOT/evidence-manifest.txt"
  "$G_R1_ROOT/packet-snapshot/packet-manifest.json"
  "$G_R1_ROOT/packet-snapshot/process-identity-contract.json"
  "$G_R1_ROOT/packet-snapshot/exact-stop-contract.json"
  "$G_R1_ROOT/packet-snapshot/gui-stop-restart-route-resolution.json"

  "$H_ROOT/result.json"
  "$H_ROOT/evidence-manifest.txt"
  "$H_ROOT/packet-snapshot/packet-manifest.json"
  "$H_ROOT/packet-snapshot/packet-semantic-validation.json"
  "$H_ROOT/packet-snapshot/exact-restart-environment-contract.json"
  "$H_ROOT/packet-snapshot/minimal-environment-contract.json"
  "$H_ROOT/packet-snapshot/environment-contract-resolution.json"

  "$TARGET_SCRIPT"
)

for required in "${required_inputs[@]}"; do
  test -f "$required"
done

echo "${EXPECTED_E_RESULT_SHA}  ${E_ROOT}/result.json" | sha256sum -c -
echo "${EXPECTED_E_PACKET_MANIFEST_SHA}  ${E_ROOT}/packet-snapshot/production-db-preflight-backup-preparation-packet-manifest.json" | sha256sum -c -
echo "${EXPECTED_E_EVIDENCE_MANIFEST_SHA}  ${E_ROOT}/production-db-preflight-backup-preparation-evidence-manifest.txt" | sha256sum -c -

echo "${EXPECTED_F1_RESULT_SHA}  ${F1_ROOT}/corrective-result.json" | sha256sum -c -
echo "${EXPECTED_F1_PROVENANCE_SHA}  ${F1_ROOT}/provenance-record.json" | sha256sum -c -
echo "${EXPECTED_F1_EVIDENCE_MANIFEST_SHA}  ${F1_ROOT}/evidence-manifest.txt" | sha256sum -c -

echo "${EXPECTED_G_R1_RESULT_SHA}  ${G_R1_ROOT}/result.json" | sha256sum -c -
echo "${EXPECTED_G_R1_PACKET_MANIFEST_SHA}  ${G_R1_ROOT}/packet-snapshot/packet-manifest.json" | sha256sum -c -
echo "${EXPECTED_G_R1_EVIDENCE_MANIFEST_SHA}  ${G_R1_ROOT}/evidence-manifest.txt" | sha256sum -c -

echo "${EXPECTED_H_RESULT_SHA}  ${H_ROOT}/result.json" | sha256sum -c -
echo "${EXPECTED_H_PACKET_MANIFEST_SHA}  ${H_ROOT}/packet-snapshot/packet-manifest.json" | sha256sum -c -
echo "${EXPECTED_H_SEMANTIC_SHA}  ${H_ROOT}/packet-snapshot/packet-semantic-validation.json" | sha256sum -c -
echo "${EXPECTED_H_EVIDENCE_MANIFEST_SHA}  ${H_ROOT}/evidence-manifest.txt" | sha256sum -c -

# Copy only compact decision/contract inputs. Raw cron evidence is read in place and
# is not replicated because current redacted derivatives are generated below.
cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$E_ROOT/result.json" \
  "$INPUT_ROOT/3e-e-result.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$F1_ROOT/corrective-result.json" \
  "$INPUT_ROOT/3e-f1-corrective-result.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/packet-snapshot/process-identity-contract.json" \
  "$INPUT_ROOT/3e-g-r1-process-identity-contract.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/packet-snapshot/exact-stop-contract.json" \
  "$INPUT_ROOT/3e-g-r1-exact-stop-contract.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$H_ROOT/packet-snapshot/exact-restart-environment-contract.json" \
  "$INPUT_ROOT/3e-h-exact-restart-environment-contract.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$H_ROOT/packet-snapshot/minimal-environment-contract.json" \
  "$INPUT_ROOT/3e-h-minimal-environment-contract.json"

cat > "$PACKET_ROOT/human-approval-verbatim.txt" <<'APPROVAL'
承認：
H_EXECUTION_EVIDENCE_REVIEW=APPROVE
ENVIRONMENT_CONTRACT_REVIEW=APPROVE_WITH_CONDITIONS
MINIMAL_ENVIRONMENT_CONTRACT_REVIEW=PASS
EXACT_STOP_ROUTE_REVIEW=PASS_PENDING_EXECUTION_APPROVAL
EXACT_RESTART_ROUTE_REVIEW=PASS_PENDING_EXECUTION_APPROVAL
BOTH_EXACT_ROUTES_RESOLVED=true
APPROVE_3E_I_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_PREPARATION_NO_EXECUTION

許可範囲：
1. 3E-E、3E-F1、3E-G-R1、3E-H Evidenceを読み取り専用入力として使用する。
2. 現行GUIプロセスのidentityと127.0.0.1:8765 listenerを読み取り専用で再確認する。
3. 関連cron 3件を読み取り、freeze中の窓制御方法を準備する。
4. cron窓制御をSCHEDULE_AVOIDANCE_ONLY、EXISTING_MAINTENANCE_LOCK、
   TEMPORARY_CRONTAB_CONTROL_REQUIRES_SEPARATE_APPROVAL、UNRESOLVEDから判定する。
5. 将来のGUI停止コマンド、最大待機時間、SIGKILL禁止、port消失確認を固定する。
6. Writer停止後に行う将来のroot読み取り確認を準備する。
7. Production DB backupのdirectory、DB/WAL/SHM取扱い、SHA/size/inode、
   copy後照合、fsync、manifest、rollback参照を実行せずに固定する。
8. writer停止とopen handleゼロ後のfilesystem copyを基本候補とし、SQL接続を使用しない。
9. 3E-H SAFE_MINIMAL_MAINTENANCE_MODEのrestart contractを使用する。
10. 再起動後の新PID、identity、単一process、listener、二重起動なし、
    protected SHA不変の確認計画を固定する。
11. WordPress等の外部操作はHOLDとし、FULL_OPERATIONAL_PARITYを主張しない。
12. stop condition、rollback condition、最大freeze時間を設定する。
13. 新しい一意なshadow/evidence領域へPacketを保存する。

禁止事項：
process signal送信、GUI停止・再起動、writer停止、cron変更、crontab書換え、
timer変更、systemctl stop/start/restart、service作成・変更、Production DB接続、
SQL実行、backup作成、restore、migration、manifest変更、source/test変更、
git add、git commit、deployment、外部通信、Slack Worker起動、
production approval、production release承認は禁止する。

追加条件：
1. cron窓制御がUNRESOLVEDの場合、Writer freeze executionを承認可能状態にしない。
2. DB/WAL/SHMの安全なcopy条件が未解決の場合、backup executionを承認可能状態にしない。
3. restart profileはSAFE_MINIMAL_MAINTENANCE_MODEとする。
4. 再起動後のWordPress外部操作はHOLDとする。
5. Packet完成後も停止・backupへ自動遷移せず、人間レビューを次ゲートとする。

RESTART_PROFILE=SAFE_MINIMAL_MAINTENANCE_MODE
WORDPRESS_EXTERNAL_ACTIONS_AFTER_RESTART=HOLD
FULL_OPERATIONAL_PARITY_AFTER_RESTART=NOT_ESTABLISHED
WRITER_FREEZE_EXECUTION=HOLD
PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

python3 - \
  "$REPO_ROOT" \
  "$E_ROOT" \
  "$E_REL" \
  "$F1_ROOT" \
  "$F1_REL" \
  "$G_R1_ROOT" \
  "$G_R1_REL" \
  "$H_ROOT" \
  "$H_REL" \
  "$EVIDENCE_ROOT" \
  "$EVIDENCE_REL" \
  "$PACKET_ROOT" \
  "$TARGET_SCRIPT" \
  "$TARGET_HOST" \
  "$TARGET_PORT" \
  "$RUN_ID" \
  "$EXPECTED_PROCESS_IDENTITY_SHA" \
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
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

(
    repo_root_s,
    e_root_s,
    e_rel,
    f1_root_s,
    f1_rel,
    g_r1_root_s,
    g_r1_rel,
    h_root_s,
    h_rel,
    evidence_root_s,
    evidence_rel,
    packet_root_s,
    target_script_s,
    target_host,
    target_port,
    run_id,
    expected_identity_sha,
    expected_db_sha,
    expected_manifest_sha,
    expected_workflow_sha,
    expected_migration_sha,
    expected_slack_runtime_sha,
    expected_promoted_test_sha,
) = sys.argv[1:]

repo_root = Path(repo_root_s).resolve()
e_root = Path(e_root_s).resolve()
f1_root = Path(f1_root_s).resolve()
g_r1_root = Path(g_r1_root_s).resolve()
h_root = Path(h_root_s).resolve()
evidence_root = Path(evidence_root_s).resolve()
packet_root = Path(packet_root_s).resolve()
target_script = Path(target_script_s).resolve()

phase = "TST-5D-W2B-I2F-3E-I-R1"
now_utc = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

MAX_FREEZE_SECONDS = 600
CRON_GUARD_BEFORE_SECONDS = 300
CRON_GUARD_AFTER_SECONDS = 300
CRON_SEARCH_DAYS = 7
STOP_WAIT_SECONDS = 30

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(token|password|passwd|secret|credential|private[_-]?key|"
    r"api[_-]?key|access[_-]?key|cookie|authorization|bearer)"
    r"(\s*[:=]\s*)([^\s]+)"
)
URL_CREDENTIAL_RE = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@"
)
SHELL_SECRET_ASSIGNMENT_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)"
)
SECRET_NAME_RE = re.compile(
    r"(TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE|API_KEY|ACCESS_KEY|"
    r"COOKIE|AUTHORIZATION|SESSION|BEARER|SIGNING|CLIENT_SECRET)",
    re.IGNORECASE,
)

CRON_FIELD_RE = re.compile(r"^[A-Za-z0-9*/,\-]+$")

MONTH_NAMES = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
DOW_NAMES = {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3,
    "THU": 4, "FRI": 5, "SAT": 6,
}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path}")
    return value

def safe_run(command: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
    except FileNotFoundError as exc:
        return {
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }

def redact_line(line: str) -> str:
    line = SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}<REDACTED>",
        line,
    )
    line = URL_CREDENTIAL_RE.sub(
        lambda match: f"{match.group(1)}<REDACTED>:<REDACTED>@",
        line,
    )

    def redact_shell_assignment(match: re.Match[str]) -> str:
        name = match.group(1)
        if SECRET_NAME_RE.search(name):
            return f"{name}=<REDACTED>"
        return match.group(0)

    return SHELL_SECRET_ASSIGNMENT_RE.sub(redact_shell_assignment, line)[:4000]

def normalize_ws(value: str) -> str:
    return " ".join(value.strip().split())

def proc_cmdline(pid: int) -> list[str]:
    raw = (Path("/proc") / str(pid) / "cmdline").read_bytes()
    return [
        part.decode("utf-8", errors="replace")
        for part in raw.split(b"\0")
        if part
    ]

def read_proc_text(pid: int, name: str) -> str:
    return (Path("/proc") / str(pid) / name).read_text(
        encoding="utf-8",
        errors="replace",
    )

def read_link(path: Path) -> str | None:
    try:
        return os.readlink(path)
    except (FileNotFoundError, PermissionError, OSError):
        return None

def proc_status(pid: int) -> dict[str, str]:
    values = {}
    for line in read_proc_text(pid, "status").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key] = value.strip()
    return values

def proc_stat_fields(pid: int) -> dict[str, Any]:
    text = read_proc_text(pid, "stat")
    left = text.find("(")
    right = text.rfind(")")
    require(left >= 0 and right > left, f"PROC_STAT_PARSE_FAILED:{pid}")
    prefix = text[:left].strip()
    comm = text[left + 1:right]
    rest = text[right + 1:].strip().split()
    require(len(rest) >= 20, f"PROC_STAT_TOO_SHORT:{pid}")
    return {
        "pid": int(prefix),
        "comm": comm,
        "state": rest[0],
        "ppid": int(rest[1]),
        "pgrp": int(rest[2]),
        "session": int(rest[3]),
        "tty_nr": int(rest[4]),
        "starttime_ticks": int(rest[19]),
    }

def boot_time_epoch() -> float:
    for line in Path("/proc/stat").read_text(encoding="utf-8").splitlines():
        if line.startswith("btime "):
            return float(line.split()[1])
    raise RuntimeError("BOOT_TIME_NOT_FOUND")

def process_start_iso(start_ticks: int) -> str:
    ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    epoch = boot_time_epoch() + (start_ticks / ticks)
    return dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc).isoformat()

def matching_gui_pids() -> list[int]:
    matches = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            argv = proc_cmdline(pid)
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if (
            str(target_script) in argv
            and "--host" in argv
            and target_host in argv
            and "--port" in argv
            and target_port in argv
        ):
            matches.append(pid)
    return sorted(matches)

def build_process_identity(pid: int) -> dict[str, Any]:
    stat_fields = proc_stat_fields(pid)
    status = proc_status(pid)
    argv = proc_cmdline(pid)
    uid_parts = status.get("Uid", "").split()
    uid = int(uid_parts[0]) if uid_parts else None
    username = pwd.getpwuid(uid).pw_name if uid is not None else None

    fields = {
        "pid": pid,
        "starttime_ticks": stat_fields["starttime_ticks"],
        "start_time_utc": process_start_iso(stat_fields["starttime_ticks"]),
        "cmdline_argv": argv,
        "cmdline_shell_quoted": shlex.join(argv),
        "cwd": read_link(Path("/proc") / str(pid) / "cwd"),
        "exe": read_link(Path("/proc") / str(pid) / "exe"),
        "uid": uid,
        "username": username,
        "session_id": stat_fields["session"],
        "process_group_id": stat_fields["pgrp"],
        "ppid": stat_fields["ppid"],
        "state": stat_fields["state"],
    }

    canonical_fields = {
        "pid": fields["pid"],
        "starttime_ticks": fields["starttime_ticks"],
        "start_time_utc": fields["start_time_utc"],
        "cmdline_argv": fields["cmdline_argv"],
        "cmdline_shell_quoted": fields["cmdline_shell_quoted"],
        "cwd": fields["cwd"],
        "exe": fields["exe"],
        "uid": fields["uid"],
        "username": fields["username"],
        "session_id": fields["session_id"],
        "process_group_id": fields["process_group_id"],
    }
    canonical = json.dumps(
        canonical_fields,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    fields["identity_sha256"] = hashlib.sha256(canonical).hexdigest()
    return fields

def listener_inventory(pid: int) -> dict[str, Any]:
    result = safe_run(["ss", "-ltnp"])
    lines = [
        redact_line(line)
        for line in str(result["stdout"]).splitlines()
        if f":{target_port}" in line
    ]
    pid_owned = any(f"pid={pid}" in line for line in lines)
    loopback_present = any(
        target_host in line or f"{target_host}:{target_port}" in line
        for line in lines
    )
    return {
        "command": ["ss", "-ltnp"],
        "exit_code": result["exit_code"],
        "timed_out": result["timed_out"],
        "relevant_lines": lines,
        "target_pid_owned": pid_owned,
        "target_loopback_listener_present": loopback_present,
        "network_connection_opened": False,
    }

def protected_sha_inventory() -> dict[str, Any]:
    items = [
        ("production_database", repo_root / "data/database/ebook_affiliate.db", expected_db_sha),
        ("production_manifest", repo_root / "config/slack_worker_release_source_manifest.json", expected_manifest_sha),
        ("workflow_source", repo_root / "app/db/repositories/workflow_state_repository.py", expected_workflow_sha),
        ("migration_source", repo_root / "migrations/versions/00241611109d_add_unique_wordpress_post_id.py", expected_migration_sha),
        ("slack_runtime_source", repo_root / "scripts/run_slack_approval_socket.py", expected_slack_runtime_sha),
        ("promoted_test", repo_root / "tests/test_slack_approval_socket_hold_remediation_offline.py", expected_promoted_test_sha),
    ]
    entries = []
    for label, path, expected in items:
        require(path.is_file(), f"PROTECTED_FILE_MISSING:{path}")
        actual = sha256(path)
        require(actual == expected, f"PROTECTED_SHA_MISMATCH:{label}:{actual}")
        metadata = path.stat()
        entries.append({
            "label": label,
            "path": str(path),
            "sha256": actual,
            "size_bytes": metadata.st_size,
            "inode": metadata.st_ino,
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        })
    return {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "files": entries,
        "production_database_opened": False,
        "sql_executed": False,
    }

def lstat_metadata(path: Path, *, hash_content: bool) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {
            "path": str(path),
            "exists": False,
            "hash_content": False,
            "content_sha256": None,
        }

    item = {
        "path": str(path),
        "exists": True,
        "is_regular_file": stat.S_ISREG(metadata.st_mode),
        "is_symlink": stat.S_ISLNK(metadata.st_mode),
        "owner": pwd.getpwuid(metadata.st_uid).pw_name,
        "group": grp.getgrgid(metadata.st_gid).gr_name,
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "size_bytes": metadata.st_size,
        "inode": metadata.st_ino,
        "mtime_ns": metadata.st_mtime_ns,
        "hash_content": bool(hash_content and stat.S_ISREG(metadata.st_mode)),
        "content_sha256": (
            sha256(path)
            if hash_content and stat.S_ISREG(metadata.st_mode)
            else None
        ),
    }
    return item

def is_cron_field_token(token: str) -> bool:
    return bool(CRON_FIELD_RE.fullmatch(token))

def extract_cron_lines(text: str) -> list[str]:
    results = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        tokens = stripped.split()

        if tokens and tokens[0].startswith("@") and len(tokens) >= 2:
            candidate = normalize_ws(" ".join(tokens))
            results.append(candidate)
            continue

        for start in range(0, max(0, len(tokens) - 5)):
            fields = tokens[start:start + 5]
            if len(fields) != 5 or not all(is_cron_field_token(item) for item in fields):
                continue
            if start + 5 >= len(tokens):
                continue
            candidate = normalize_ws(" ".join(tokens[start:]))
            results.append(candidate)
            break

    return sorted(set(results))

def active_crontab_lines(raw: str) -> list[str]:
    lines = []
    for raw_line in raw.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", stripped):
            continue
        lines.append(normalize_ws(stripped))
    return lines

def crontab_environment(raw: str) -> dict[str, str]:
    values = {}
    for raw_line in raw.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", stripped)
        if match:
            name = match.group(1)
            value = match.group(2).strip().strip("'\"")
            if not SECRET_NAME_RE.search(name):
                values[name] = value
    return values

def parse_value(value: str, names: dict[str, int]) -> int:
    upper = value.upper()
    if upper in names:
        return names[upper]
    return int(value)

def expand_cron_field(
    field: str,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None = None,
    *,
    dow: bool = False,
) -> set[int]:
    names = names or {}
    values: set[int] = set()

    for part in field.split(","):
        base, slash, step_text = part.partition("/")
        step = int(step_text) if slash else 1
        require(step > 0, f"CRON_STEP_INVALID:{field}")

        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            start = parse_value(start_text, names)
            end = parse_value(end_text, names)
        else:
            value = parse_value(base, names)
            if dow and value == 7:
                value = 0
            require(minimum <= value <= maximum, f"CRON_VALUE_OUT_OF_RANGE:{field}")
            values.add(value)
            continue

        require(minimum <= start <= maximum, f"CRON_RANGE_START_INVALID:{field}")
        require(minimum <= end <= maximum, f"CRON_RANGE_END_INVALID:{field}")
        require(start <= end, f"CRON_RANGE_REVERSED:{field}")

        for value in range(start, end + 1, step):
            if dow and value == 7:
                value = 0
            values.add(value)

    return values

def parse_standard_cron_line(line: str) -> dict[str, Any]:
    tokens = line.split()
    require(len(tokens) >= 6, f"CRON_LINE_TOO_SHORT:{line}")
    require(not tokens[0].startswith("@"), f"CRON_MACRO_UNSUPPORTED:{line}")

    minute_f, hour_f, dom_f, month_f, dow_f = tokens[:5]
    command = " ".join(tokens[5:])

    return {
        "line": line,
        "minute_field": minute_f,
        "hour_field": hour_f,
        "day_of_month_field": dom_f,
        "month_field": month_f,
        "day_of_week_field": dow_f,
        "command": command,
        "minute_values": expand_cron_field(minute_f, 0, 59),
        "hour_values": expand_cron_field(hour_f, 0, 23),
        "day_of_month_values": expand_cron_field(dom_f, 1, 31),
        "month_values": expand_cron_field(month_f, 1, 12, MONTH_NAMES),
        "day_of_week_values": expand_cron_field(
            dow_f, 0, 7, DOW_NAMES, dow=True
        ),
        "day_of_month_wildcard": dom_f == "*",
        "day_of_week_wildcard": dow_f == "*",
    }

def cron_matches(parsed: dict[str, Any], moment: dt.datetime) -> bool:
    if moment.minute not in parsed["minute_values"]:
        return False
    if moment.hour not in parsed["hour_values"]:
        return False
    if moment.month not in parsed["month_values"]:
        return False

    dom_match = moment.day in parsed["day_of_month_values"]
    cron_dow = (moment.weekday() + 1) % 7
    dow_match = cron_dow in parsed["day_of_week_values"]

    if (
        not parsed["day_of_month_wildcard"]
        and not parsed["day_of_week_wildcard"]
    ):
        day_match = dom_match or dow_match
    elif not parsed["day_of_month_wildcard"]:
        day_match = dom_match
    elif not parsed["day_of_week_wildcard"]:
        day_match = dow_match
    else:
        day_match = True

    return day_match

def resolve_timezone(cron_env: dict[str, str]) -> tuple[str, ZoneInfo]:
    cron_tz = cron_env.get("CRON_TZ")
    if cron_tz:
        try:
            return cron_tz, ZoneInfo(cron_tz)
        except ZoneInfoNotFoundError:
            pass

    timedatectl = safe_run(["timedatectl", "show", "-p", "Timezone", "--value"])
    timezone_name = str(timedatectl["stdout"]).strip()
    if timedatectl["exit_code"] == 0 and timezone_name:
        try:
            return timezone_name, ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            pass

    timezone_file = Path("/etc/timezone")
    if timezone_file.is_file():
        timezone_name = timezone_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
        try:
            return timezone_name, ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            pass

    return "UTC", ZoneInfo("UTC")

def scheduled_events(
    parsed_jobs: list[dict[str, Any]],
    timezone: ZoneInfo,
) -> list[dict[str, Any]]:
    current = dt.datetime.now(timezone).replace(second=0, microsecond=0)
    current += dt.timedelta(minutes=1)
    end = current + dt.timedelta(days=CRON_SEARCH_DAYS)

    events = []
    cursor = current
    while cursor <= end:
        for index, job in enumerate(parsed_jobs):
            if cron_matches(job, cursor):
                events.append({
                    "at": cursor,
                    "job_index": index,
                })
        cursor += dt.timedelta(minutes=1)

    events.sort(key=lambda item: item["at"])
    return events

def find_safe_window(
    events: list[dict[str, Any]],
    timezone: ZoneInfo,
) -> dict[str, Any] | None:
    start_search = dt.datetime.now(timezone).replace(second=0, microsecond=0)
    start_search += dt.timedelta(minutes=5)
    end_search = start_search + dt.timedelta(days=CRON_SEARCH_DAYS)

    freeze_delta = dt.timedelta(seconds=MAX_FREEZE_SECONDS)
    guard_before = dt.timedelta(seconds=CRON_GUARD_BEFORE_SECONDS)
    guard_after = dt.timedelta(seconds=CRON_GUARD_AFTER_SECONDS)

    cursor = start_search
    while cursor + freeze_delta <= end_search:
        freeze_end = cursor + freeze_delta
        blocked_start = cursor - guard_before
        blocked_end = freeze_end + guard_after

        conflict = any(
            blocked_start <= event["at"] <= blocked_end
            for event in events
        )
        if not conflict:
            return {
                "candidate_freeze_start": cursor.isoformat(),
                "candidate_freeze_end": freeze_end.isoformat(),
                "guarded_interval_start": blocked_start.isoformat(),
                "guarded_interval_end": blocked_end.isoformat(),
                "max_freeze_seconds": MAX_FREEZE_SECONDS,
                "guard_before_seconds": CRON_GUARD_BEFORE_SECONDS,
                "guard_after_seconds": CRON_GUARD_AFTER_SECONDS,
            }
        cursor += dt.timedelta(minutes=1)

    return None

def detect_existing_lock(
    relevant_lines: list[str],
) -> dict[str, Any]:
    if len(relevant_lines) != 3:
        return {
            "detected": False,
            "reason": "RELEVANT_CRON_COUNT_NOT_3",
            "shared_lock_tokens": [],
        }

    token_sets = []
    for line in relevant_lines:
        tokens = set(
            token
            for token in shlex.split(line, comments=False, posix=True)
            if (
                "flock" in token
                or token.endswith(".lock")
                or "maintenance" in token.lower()
                or "freeze" in token.lower()
            )
        )
        token_sets.append(tokens)

    shared = set.intersection(*token_sets) if token_sets else set()
    return {
        "detected": bool(shared),
        "reason": (
            "ALL_RELEVANT_CRON_LINES_SHARE_LOCK_TOKEN"
            if shared
            else "NO_SHARED_LOCK_TOKEN"
        ),
        "shared_lock_tokens": sorted(redact_line(token) for token in shared),
    }

def root_post_stop_check_plan(db_path: Path) -> dict[str, Any]:
    members = [
        str(db_path),
        str(Path(str(db_path) + "-wal")),
        str(Path(str(db_path) + "-shm")),
    ]
    return {
        "status": "PLAN_ONLY_NOT_EXECUTED",
        "execution_allowed": False,
        "requires_root": True,
        "members": members,
        "future_checks": [
            "Scan /proc/[0-9]*/fd symlinks for exact DB/WAL/SHM paths.",
            "Require total open handle count equals zero.",
            "lstat each member without opening SQLite.",
            "Record existence, owner, group, mode, size, inode and mtime_ns.",
            "Reject symlinks and non-regular files.",
            "Re-run immediately before filesystem copy.",
        ],
        "future_result_requirement": {
            "root_open_handle_count": 0,
            "production_database_sql_connection_used": False,
            "sql_executed": False,
        },
    }

def backup_contract(
    db_path: Path,
    reserved_backup_dir: Path,
) -> dict[str, Any]:
    db = str(db_path)
    wal = str(Path(db + "-wal"))
    shm = str(Path(db + "-shm"))

    return {
        "schema_version": "1.0",
        "phase": phase,
        "status": "PLAN_ONLY_NOT_EXECUTED",
        "execution_allowed": False,
        "backup_method": "FROZEN_FILESYSTEM_COPY_NO_SQL_CONNECTION",
        "reserved_backup_directory": str(reserved_backup_dir),
        "reserved_directory_exists_now": reserved_backup_dir.exists(),
        "future_directory_creation": {
            "must_use_exclusive_creation": True,
            "must_fail_if_path_exists": True,
            "mode": "0750",
        },
        "source_members": [
            {
                "role": "PRIMARY_DATABASE",
                "source_path": db,
                "copy_policy": "REQUIRED",
                "restore_authority": "AUTHORITATIVE",
            },
            {
                "role": "WRITE_AHEAD_LOG",
                "source_path": wal,
                "copy_policy": "COPY_IF_PRESENT_AFTER_FREEZE",
                "restore_authority": "AUTHORITATIVE_IF_PRESENT_IN_MANIFEST",
            },
            {
                "role": "SHARED_MEMORY",
                "source_path": shm,
                "copy_policy": "FORENSIC_COPY_IF_PRESENT_AFTER_FREEZE",
                "restore_authority": "NOT_AUTHORITATIVE_REBUILDABLE",
            },
        ],
        "preconditions": [
            "Approved cron window control is active.",
            "Reviewed GUI process identity matches exactly.",
            "GUI writer has exited after SIGTERM.",
            "127.0.0.1:8765 listener is absent.",
            "Root DB/WAL/SHM open handle count equals zero.",
            "DB exists, is a regular file and is not a symlink.",
            "Any present WAL/SHM member is a regular file and not a symlink.",
            "Reserved backup directory does not already exist.",
        ],
        "future_source_inventory": [
            "Record path, existence, SHA-256, size, inode, owner, group, mode and mtime_ns before copy.",
            "Hash DB and every present WAL/SHM member only after writer freeze.",
            "Record the frozen source file set in source-manifest.json.",
        ],
        "future_copy_algorithm": [
            "Create reserved backup directory exclusively.",
            "Open each source member read-only with symlink rejection.",
            "Create each destination with O_CREAT|O_EXCL and mode 0640.",
            "Copy byte-for-byte in bounded chunks.",
            "fsync each destination file.",
            "Re-stat and re-hash every source after copy.",
            "Require source metadata and SHA unchanged during copy.",
            "Require destination size and SHA equal source.",
            "Write backup-manifest.json with source and destination records.",
            "fsync backup-manifest.json and the backup directory.",
            "Seal files to 0440 and directory to 0550 after successful validation.",
        ],
        "rollback_reference": {
            "manifest": str(reserved_backup_dir / "backup-manifest.json"),
            "primary_database": str(
                reserved_backup_dir / db_path.name
            ),
            "write_ahead_log": str(
                reserved_backup_dir / (db_path.name + "-wal")
            ),
            "shared_memory_forensic": str(
                reserved_backup_dir / (db_path.name + "-shm")
            ),
            "restore_execution_allowed": False,
            "separate_restore_approval_required": True,
        },
        "sql_connection_used": False,
        "backup_created_now": False,
    }

e_result = read_json(e_root / "result.json")
f1_result = read_json(f1_root / "corrective-result.json")
g_result = read_json(g_r1_root / "result.json")
g_identity_input = read_json(
    g_r1_root / "packet-snapshot/process-identity-contract.json"
)
g_stop_input = read_json(
    g_r1_root / "packet-snapshot/exact-stop-contract.json"
)
h_result = read_json(h_root / "result.json")
h_restart_input = read_json(
    h_root / "packet-snapshot/exact-restart-environment-contract.json"
)
h_minimal_input = read_json(
    h_root / "packet-snapshot/minimal-environment-contract.json"
)

require(e_result.get("result") is not None, "3E_E_RESULT_MISSING")
require(
    f1_result.get("result")
    == "PASS_W2B_I2F3E_F1_EVIDENCE_COPY_NORMALIZED_AND_RESEALED",
    "3E_F1_RESULT_INVALID",
)
require(
    g_result.get("result")
    == "PASS_W2B_I2F3E_G_R1_GUI_STOP_RESTART_ROUTE_RESOLUTION_READY",
    "3E_G_R1_RESULT_INVALID",
)
require(
    h_result.get("result")
    == "PASS_W2B_I2F3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_RESOLUTION_READY",
    "3E_H_RESULT_INVALID",
)
require(h_result.get("environment_contract_resolved") is True, "3E_H_ENV_NOT_RESOLVED")
require(h_result.get("both_exact_routes_resolved") is True, "3E_H_ROUTES_NOT_RESOLVED")
require(
    h_restart_input.get("status") == "RESOLVED_PENDING_HUMAN_REVIEW",
    "3E_H_RESTART_STATUS_INVALID",
)
require(h_restart_input.get("execution_allowed") is False, "3E_H_RESTART_EXECUTION_INVALID")
require(
    h_minimal_input.get("type")
    == "STATIC_MINIMAL_ENVIRONMENT_CONTRACT_NO_CREDENTIAL_FILE",
    "3E_H_MINIMAL_ENV_TYPE_INVALID",
)
require(g_stop_input.get("method") == "SIGTERM_TO_EXACT_PID", "3E_G_STOP_METHOD_INVALID")
require(
    g_stop_input.get("status") == "RESOLVED_PENDING_HUMAN_REVIEW",
    "3E_G_STOP_STATUS_INVALID",
)
require(
    g_identity_input.get("contract", {}).get("identity_sha256")
    == expected_identity_sha,
    "3E_G_IDENTITY_SHA_INVALID",
)

protected_before = protected_sha_inventory()
write_json(packet_root / "protected-sha-before.json", protected_before)

pids = matching_gui_pids()
process_state = (
    "RUNNING_SINGLE_MATCH"
    if len(pids) == 1
    else "NOT_FOUND"
    if len(pids) == 0
    else "MULTIPLE_MATCHES"
)
current_identity = build_process_identity(pids[0]) if len(pids) == 1 else None
identity_matches_prior = bool(
    current_identity
    and current_identity["identity_sha256"] == expected_identity_sha
)
listener = listener_inventory(pids[0]) if len(pids) == 1 else {
    "command": ["ss", "-ltnp"],
    "exit_code": None,
    "timed_out": False,
    "relevant_lines": [],
    "target_pid_owned": False,
    "target_loopback_listener_present": False,
    "network_connection_opened": False,
}

write_json(
    packet_root / "current-gui-identity-readonly.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "process_state": process_state,
        "matching_process_count": len(pids),
        "current_identity": current_identity,
        "expected_prior_identity_sha256": expected_identity_sha,
        "identity_matches_prior": identity_matches_prior,
        "listener_inventory": listener,
        "process_signal_sent": False,
        "gui_stopped_or_restarted": False,
    },
)

crontab_result = safe_run(["crontab", "-l"])
raw_crontab = str(crontab_result["stdout"]) if crontab_result["exit_code"] == 0 else ""
current_active = active_crontab_lines(raw_crontab)
cron_env = crontab_environment(raw_crontab)

historical_cron_text = (
    f1_root / "corrected-packet-snapshot/cron-readonly-inventory.txt"
).read_text(encoding="utf-8", errors="replace")
historical_json_text = json.dumps(
    read_json(
        f1_root
        / "corrected-packet-snapshot/process-and-cron-attribution.json"
    ),
    ensure_ascii=False,
)

historical_candidates = sorted(set(
    extract_cron_lines(historical_cron_text)
    + extract_cron_lines(historical_json_text)
))
current_set = set(current_active)
relevant_lines = sorted(
    line for line in historical_candidates if line in current_set
)

freeze_plan_input = read_json(
    f1_root / "corrected-packet-snapshot/freeze-window-plan.json"
)
expected_relevant_count = int(
    freeze_plan_input.get("relevant_cron_job_count", 3)
)

cron_parse_errors = []
parsed_jobs = []
for line in relevant_lines:
    try:
        parsed_jobs.append(parse_standard_cron_line(line))
    except Exception as exc:
        cron_parse_errors.append({
            "line_sha256": sha256_bytes(line.encode("utf-8")),
            "error": f"{type(exc).__name__}:{exc}",
        })

timezone_name, cron_timezone = resolve_timezone(cron_env)
events = (
    scheduled_events(parsed_jobs, cron_timezone)
    if len(parsed_jobs) == expected_relevant_count
    and not cron_parse_errors
    else []
)
safe_window = (
    find_safe_window(events, cron_timezone)
    if events or (
        len(parsed_jobs) == expected_relevant_count
        and not cron_parse_errors
    )
    else None
)

lock_detection = detect_existing_lock(relevant_lines)

if (
    len(relevant_lines) != expected_relevant_count
    or crontab_result["exit_code"] != 0
):
    cron_control_method = "UNRESOLVED"
elif lock_detection["detected"]:
    cron_control_method = "EXISTING_MAINTENANCE_LOCK"
elif cron_parse_errors:
    cron_control_method = (
        "TEMPORARY_CRONTAB_CONTROL_REQUIRES_SEPARATE_APPROVAL"
    )
elif safe_window is not None:
    cron_control_method = "SCHEDULE_AVOIDANCE_ONLY"
else:
    cron_control_method = (
        "TEMPORARY_CRONTAB_CONTROL_REQUIRES_SEPARATE_APPROVAL"
    )

cron_execution_control_resolved = cron_control_method in {
    "SCHEDULE_AVOIDANCE_ONLY",
    "EXISTING_MAINTENANCE_LOCK",
}

cron_records = []
for line in relevant_lines:
    fields = line.split(maxsplit=5)
    schedule = " ".join(fields[:5]) if len(fields) >= 6 else fields[0]
    command = fields[5] if len(fields) >= 6 else " ".join(fields[1:])
    cron_records.append({
        "raw_line_sha256": sha256_bytes(line.encode("utf-8")),
        "schedule": schedule,
        "redacted_command": redact_line(command),
        "redacted_normalized_line": redact_line(line),
    })

write_json(
    packet_root / "cron-window-control-plan.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "crontab_command_exit_code": crontab_result["exit_code"],
        "raw_crontab_sha256": sha256_bytes(raw_crontab.encode("utf-8")),
        "raw_crontab_saved": False,
        "secret_values_saved": False,
        "current_active_job_count": len(current_active),
        "historical_candidate_count": len(historical_candidates),
        "expected_relevant_cron_job_count": expected_relevant_count,
        "matched_relevant_cron_job_count": len(relevant_lines),
        "relevant_jobs": cron_records,
        "cron_timezone": timezone_name,
        "cron_environment_non_secret": {
            key: value
            for key, value in sorted(cron_env.items())
            if key in {"CRON_TZ", "SHELL", "PATH", "HOME", "MAILTO"}
        },
        "parse_errors": cron_parse_errors,
        "existing_lock_detection": lock_detection,
        "control_method": cron_control_method,
        "execution_control_resolved": cron_execution_control_resolved,
        "candidate_safe_window": safe_window,
        "future_execution_requirements": [
            "Re-read current crontab immediately before freeze.",
            "Require raw crontab SHA and the three relevant normalized lines to match the reviewed packet, or require a new review.",
            "For SCHEDULE_AVOIDANCE_ONLY, recompute a fresh guarded window using the reviewed timezone and parser.",
            "Start freeze only inside a separately approved fresh guarded window.",
            "Abort before SIGTERM if any relevant cron event falls inside the guarded interval.",
            "Do not edit crontab under this packet.",
        ],
        "crontab_changed": False,
        "writer_freeze_execution": "HOLD",
    },
)

db_path = repo_root / "data/database/ebook_affiliate.db"
db_members_current = [
    lstat_metadata(db_path, hash_content=True),
    lstat_metadata(Path(str(db_path) + "-wal"), hash_content=False),
    lstat_metadata(Path(str(db_path) + "-shm"), hash_content=False),
]
require(
    db_members_current[0]["content_sha256"] == expected_db_sha,
    "CURRENT_DB_SHA_MISMATCH",
)

reserved_backup_dir = (
    repo_root
    / "backups"
    / "production_db_freeze"
    / f"i2f3e-i-execution-{run_id}"
)
backup_plan = backup_contract(db_path, reserved_backup_dir)
backup_copy_conditions_resolved = (
    db_members_current[0]["exists"] is True
    and db_members_current[0]["is_regular_file"] is True
    and db_members_current[0]["is_symlink"] is False
    and backup_plan["reserved_directory_exists_now"] is False
)

write_json(
    packet_root / "current-db-file-set-metadata-readonly.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "status": "INFORMATIONAL_PRE_FREEZE_NOT_BACKUP_SOURCE",
        "members": db_members_current,
        "db_sha_verified": True,
        "wal_shm_content_hashed": False,
        "production_database_sql_connection_used": False,
        "sql_executed": False,
    },
)

write_json(
    packet_root / "future-root-post-stop-check-plan.json",
    root_post_stop_check_plan(db_path),
)

write_json(
    packet_root / "filesystem-backup-contract.json",
    backup_plan,
)

future_stop_contract = {
    "schema_version": "1.0",
    "phase": phase,
    "status": (
        "RESOLVED_PENDING_SEPARATE_EXECUTION_APPROVAL"
        if identity_matches_prior
        and listener["target_pid_owned"]
        and process_state == "RUNNING_SINGLE_MATCH"
        else "BLOCKED_CURRENT_IDENTITY_OR_LISTENER_MISMATCH"
    ),
    "execution_allowed": False,
    "method": "SIGTERM_TO_EXACT_PID_AFTER_IDENTITY_REVALIDATION",
    "reviewed_pid": current_identity["pid"] if current_identity else None,
    "reviewed_identity_sha256": (
        current_identity["identity_sha256"]
        if current_identity
        else None
    ),
    "required_identity_fields": [
        "pid",
        "starttime_ticks",
        "cmdline_argv",
        "cwd",
        "exe",
        "uid",
        "session_id",
        "process_group_id",
    ],
    "future_command_template": [
        "kill",
        "-TERM",
        "<EXACT_REVALIDATED_PID>",
    ],
    "max_wait_seconds": STOP_WAIT_SECONDS,
    "poll_interval_seconds": 1,
    "sigkill_allowed": False,
    "post_stop_requirements": [
        "Reviewed process identity no longer exists.",
        "No matching GUI process remains.",
        "127.0.0.1:8765 listener is absent.",
        "Root DB/WAL/SHM open handle count equals zero.",
    ],
    "stop_conditions": [
        "Abort if process identity differs from reviewed identity.",
        "Abort if more than one matching GUI process exists.",
        "Abort if listener is not owned by the reviewed process.",
        "Abort if cron control is not separately approved and active.",
        "Abort if protected SHA verification fails.",
    ],
    "writer_stop_performed_now": False,
    "process_signal_sent_now": False,
}

write_json(
    packet_root / "future-gui-stop-contract.json",
    future_stop_contract,
)

restart_profile = {
    "schema_version": "1.0",
    "phase": phase,
    "profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "source_contract_phase": "TST-5D-W2B-I2F-3E-H",
    "source_contract": h_restart_input,
    "execution_allowed": False,
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "post_restart_requirements": [
        "Capture $! as the candidate new PID.",
        "Create a new process identity contract from PID, starttime, argv, cwd, exe, UID, SID and PGID.",
        "Require exactly one matching GUI process.",
        "Require 127.0.0.1:8765 listener owned by the new process.",
        "Require no duplicate GUI instance.",
        "Require protected SHA inventory unchanged.",
        "Do not execute WordPress or other external actions.",
    ],
    "rollback_if_restart_fails": [
        "Do not retry automatically.",
        "Preserve log and new process identity evidence.",
        "Confirm no partial 127.0.0.1:8765 listener remains.",
        "Do not restore database automatically.",
        "Require a new human decision.",
    ],
}

write_json(
    packet_root / "safe-minimal-restart-profile.json",
    restart_profile,
)

execution_steps = [
    {
        "order": 1,
        "name": "REVALIDATE_PROTECTED_SHA_AND_CRON",
        "execution_allowed_now": False,
        "stop_condition": "Any protected SHA or reviewed relevant cron line differs.",
    },
    {
        "order": 2,
        "name": "ENTER_APPROVED_CRON_WINDOW",
        "execution_allowed_now": False,
        "stop_condition": "Fresh guarded window is absent or not separately approved.",
    },
    {
        "order": 3,
        "name": "REVALIDATE_GUI_PROCESS_IDENTITY",
        "execution_allowed_now": False,
        "stop_condition": "PID/starttime/argv/cwd/exe/UID/listener ownership mismatch.",
    },
    {
        "order": 4,
        "name": "SIGTERM_EXACT_GUI_PROCESS",
        "execution_allowed_now": False,
        "stop_condition": "Identity mismatch or separate execution approval absent.",
    },
    {
        "order": 5,
        "name": "WAIT_FOR_GUI_EXIT_AND_PORT_RELEASE",
        "execution_allowed_now": False,
        "stop_condition": f"Process or port remains after {STOP_WAIT_SECONDS} seconds; SIGKILL forbidden.",
    },
    {
        "order": 6,
        "name": "ROOT_VERIFY_DB_WAL_SHM_OPEN_HANDLES_ZERO",
        "execution_allowed_now": False,
        "stop_condition": "Any open handle remains or source member is unsafe.",
    },
    {
        "order": 7,
        "name": "CREATE_FROZEN_FILESYSTEM_BACKUP",
        "execution_allowed_now": False,
        "stop_condition": "Source changes during copy, hash mismatch, fsync failure or manifest failure.",
    },
    {
        "order": 8,
        "name": "RESTART_SAFE_MINIMAL_MAINTENANCE_MODE",
        "execution_allowed_now": False,
        "stop_condition": "Port not free, duplicate process, restart contract mismatch or separate approval absent.",
    },
    {
        "order": 9,
        "name": "VERIFY_NEW_IDENTITY_LISTENER_AND_PROTECTED_SHA",
        "execution_allowed_now": False,
        "stop_condition": "Readiness, single-process or protected SHA check fails.",
    },
    {
        "order": 10,
        "name": "EXIT_FREEZE_WITH_WORDPRESS_ACTIONS_HELD",
        "execution_allowed_now": False,
        "stop_condition": "Freeze elapsed time exceeds maximum or rollback review is required.",
    },
]

execution_eligibility = (
    cron_execution_control_resolved
    and backup_copy_conditions_resolved
    and identity_matches_prior
    and listener["target_pid_owned"]
    and process_state == "RUNNING_SINGLE_MATCH"
    and h_result.get("both_exact_routes_resolved") is True
)

eligibility_status = (
    "READY_FOR_HUMAN_REVIEW_NOT_EXECUTION"
    if execution_eligibility
    else "BLOCKED_PENDING_CONDITION_RESOLUTION"
)

write_json(
    packet_root / "future-freeze-backup-restart-sequence.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "status": eligibility_status,
        "execution_allowed": False,
        "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
        "cron_guard_before_seconds": CRON_GUARD_BEFORE_SECONDS,
        "cron_guard_after_seconds": CRON_GUARD_AFTER_SECONDS,
        "steps": execution_steps,
        "global_stop_conditions": [
            "Maximum freeze time would be exceeded.",
            "Any reviewed process identity component changes.",
            "Any protected SHA changes.",
            "Any relevant cron schedule changes.",
            "DB/WAL/SHM open handle count is not zero.",
            "Any backup copy or fsync validation fails.",
            "Restart creates zero or multiple GUI processes.",
            "127.0.0.1:8765 is not owned by the new GUI process.",
        ],
        "rollback_conditions": [
            "Stop failed without clean exit.",
            "Port remained occupied.",
            "Backup validation failed.",
            "Restart failed or duplicate process appeared.",
            "Protected SHA changed.",
        ],
        "automatic_retry_allowed": False,
        "automatic_restore_allowed": False,
        "separate_execution_approval_required": True,
        "separate_restore_approval_required": True,
        "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
        "wordpress_external_actions_after_restart": "HOLD",
        "full_operational_parity_after_restart": "NOT_ESTABLISHED",
        "writer_freeze_execution": "HOLD",
    },
)

protected_after = protected_sha_inventory()
write_json(packet_root / "protected-sha-after.json", protected_after)
require(
    [item["sha256"] for item in protected_before["files"]]
    == [item["sha256"] for item in protected_after["files"]],
    "PROTECTED_SHA_CHANGED",
)

semantic_validation = {
    "schema_version": "1.0",
    "phase": phase,
    "correction_label": "3E_E_MANIFEST_PATH_CORRECTION",
    "original_3e_i_result": "FAILED_MISSING_REQUIRED_INPUT_PATHS",
    "result": "PASS_3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_PREPARATION_NO_EXECUTION",
    "process_state": process_state,
    "matching_process_count": len(pids),
    "current_identity_matches_g_r1": identity_matches_prior,
    "listener_owned_by_current_gui": listener["target_pid_owned"],
    "cron_control_method": cron_control_method,
    "cron_execution_control_resolved": cron_execution_control_resolved,
    "matched_relevant_cron_job_count": len(relevant_lines),
    "expected_relevant_cron_job_count": expected_relevant_count,
    "backup_copy_conditions_resolved": backup_copy_conditions_resolved,
    "reserved_backup_directory_exists_now": reserved_backup_dir.exists(),
    "exact_stop_route_resolved": future_stop_contract["status"]
    == "RESOLVED_PENDING_SEPARATE_EXECUTION_APPROVAL",
    "exact_restart_route_resolved": h_result.get("both_exact_routes_resolved") is True,
    "execution_eligibility": execution_eligibility,
    "execution_eligibility_status": eligibility_status,
    "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
    "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "process_signal_sent": False,
    "writer_stop_performed": False,
    "gui_stopped_or_restarted": False,
    "crontab_changed": False,
    "production_database_opened": False,
    "production_database_sql_connection_used": False,
    "sql_executed": False,
    "backup_created": False,
    "restore_executed": False,
    "migration_executed": False,
    "external_network_used": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(
    packet_root / "packet-semantic-validation.json",
    semantic_validation,
)

packet_files_before_manifest = sorted(
    path for path in packet_root.iterdir() if path.is_file()
)
manifest_entries = [
    {
        "name": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }
    for path in packet_files_before_manifest
]

packet_manifest = {
    "schema_version": "1.0",
    "phase": phase,
    "created_at_utc": now_utc(),
    "status": "NO_EXECUTION_PACKET_WRITER_FREEZE_AND_BACKUP_NOT_APPROVED",
    "result": "PASS_3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_GENERATED",
    "packet_file_count_excluding_manifest": len(manifest_entries),
    "packet_files": manifest_entries,
    "cron_control_method": cron_control_method,
    "execution_eligibility": execution_eligibility,
    "execution_eligibility_status": eligibility_status,
    "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
    "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET",
}
write_json(packet_root / "packet-manifest.json", packet_manifest)

result = {
    "schema_version": "1.0",
    "phase": phase,
    "correction_label": "3E_E_MANIFEST_PATH_CORRECTION",
    "original_3e_i_result": "FAILED_MISSING_REQUIRED_INPUT_PATHS",
    "completed_at_utc": now_utc(),
    "result": "PASS_W2B_I2F3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET_PREPARED_NO_EXECUTION",
    "evidence_root": evidence_rel,
    "input_evidence_roots": {
        "3e_e": e_rel,
        "3e_f1": f1_rel,
        "3e_g_r1": g_r1_rel,
        "3e_h": h_rel,
    },
    "process_state": process_state,
    "matching_process_count": len(pids),
    "current_gui_pid": current_identity["pid"] if current_identity else None,
    "current_process_identity_sha256": (
        current_identity["identity_sha256"]
        if current_identity
        else None
    ),
    "current_identity_matches_g_r1": identity_matches_prior,
    "listener_owned_by_current_gui": listener["target_pid_owned"],
    "cron_control_method": cron_control_method,
    "cron_execution_control_resolved": cron_execution_control_resolved,
    "matched_relevant_cron_job_count": len(relevant_lines),
    "expected_relevant_cron_job_count": expected_relevant_count,
    "backup_copy_conditions_resolved": backup_copy_conditions_resolved,
    "reserved_backup_directory": str(reserved_backup_dir),
    "reserved_backup_directory_exists_now": reserved_backup_dir.exists(),
    "exact_stop_route_status": future_stop_contract["status"],
    "exact_restart_route_status": "RESOLVED_PENDING_HUMAN_REVIEW",
    "execution_eligibility": execution_eligibility,
    "execution_eligibility_status": eligibility_status,
    "maximum_writer_freeze_seconds": MAX_FREEZE_SECONDS,
    "restart_profile": "SAFE_MINIMAL_MAINTENANCE_MODE",
    "wordpress_external_actions_after_restart": "HOLD",
    "full_operational_parity_after_restart": "NOT_ESTABLISHED",
    "packet_file_count": len(manifest_entries) + 1,
    "packet_manifest_sha256": sha256(packet_root / "packet-manifest.json"),
    "packet_semantic_validation_sha256": sha256(
        packet_root / "packet-semantic-validation.json"
    ),
    "execution": {
        "process_signal_sent": False,
        "writer_stop_performed": False,
        "gui_stopped_or_restarted": False,
        "crontab_changed": False,
        "timer_changed": False,
        "systemd_changed": False,
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
    },
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_I_R1_WRITER_FREEZE_BACKUP_EXECUTION_PACKET",
}
write_json(evidence_root / "result.json", result)

manifest_path = evidence_root / "evidence-manifest.txt"
manifest_lines = []
for artifact in sorted(
    evidence_root.rglob("*"),
    key=lambda item: item.relative_to(evidence_root).as_posix(),
):
    if artifact.is_file() and artifact != manifest_path:
        manifest_lines.append(
            f"{sha256(artifact)}  {artifact.relative_to(evidence_root).as_posix()}"
        )
manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative_path = line.split("  ", 1)
    artifact = evidence_root / relative_path
    require(artifact.is_file(), f"EVIDENCE_MANIFEST_FILE_MISSING:{relative_path}")
    require(
        sha256(artifact) == expected,
        f"EVIDENCE_MANIFEST_SHA_MISMATCH:{relative_path}",
    )

files = sorted(path for path in evidence_root.rglob("*") if path.is_file())
directories = sorted(
    (path for path in evidence_root.rglob("*") if path.is_dir()),
    key=lambda path: len(path.relative_to(evidence_root).parts),
    reverse=True,
)

repo_stat = repo_root.stat()
for artifact in [*files, *directories, evidence_root]:
    metadata = artifact.lstat()
    require(not stat.S_ISLNK(metadata.st_mode), f"EVIDENCE_SYMLINK_FORBIDDEN:{artifact}")
    require(metadata.st_uid == repo_stat.st_uid, f"EVIDENCE_UID_INVALID:{artifact}")
    require(metadata.st_gid == repo_stat.st_gid, f"EVIDENCE_GID_INVALID:{artifact}")

for artifact in files:
    os.chmod(artifact, 0o444)
for directory in directories:
    os.chmod(directory, 0o555)
os.chmod(evidence_root, 0o555)

for artifact in files:
    require(
        stat.S_IMODE(artifact.stat().st_mode) == 0o444,
        f"FILE_SEAL_FAILED:{artifact}",
    )
for directory in [*directories, evidence_root]:
    require(
        stat.S_IMODE(directory.stat().st_mode) == 0o555,
        f"DIRECTORY_SEAL_FAILED:{directory}",
    )

print("CORRECTION_LABEL=3E_E_MANIFEST_PATH_CORRECTION")
print("ORIGINAL_3E_I_RESULT=FAILED_MISSING_REQUIRED_INPUT_PATHS")
print(f"RESULT={result['result']}")
print(f"EVIDENCE_ROOT={evidence_rel}")
print(f"PROCESS_STATE={process_state}")
print(f"MATCHING_PROCESS_COUNT={len(pids)}")
print(f"CURRENT_GUI_PID={result['current_gui_pid']}")
print(f"CURRENT_PROCESS_IDENTITY_SHA={result['current_process_identity_sha256']}")
print(f"CURRENT_IDENTITY_MATCHES_G_R1={'true' if identity_matches_prior else 'false'}")
print(f"LISTENER_OWNED_BY_CURRENT_GUI={'true' if listener['target_pid_owned'] else 'false'}")
print(f"CRON_CONTROL_METHOD={cron_control_method}")
print(f"CRON_EXECUTION_CONTROL_RESOLVED={'true' if cron_execution_control_resolved else 'false'}")
print(f"MATCHED_RELEVANT_CRON_JOB_COUNT={len(relevant_lines)}")
print(f"EXPECTED_RELEVANT_CRON_JOB_COUNT={expected_relevant_count}")
print(f"CRON_TIMEZONE={timezone_name}")
print(f"CANDIDATE_SAFE_WINDOW_AVAILABLE={'true' if safe_window is not None else 'false'}")
print(f"BACKUP_COPY_CONDITIONS_RESOLVED={'true' if backup_copy_conditions_resolved else 'false'}")
print(f"RESERVED_BACKUP_DIRECTORY={reserved_backup_dir}")
print(f"RESERVED_BACKUP_DIRECTORY_EXISTS_NOW={'true' if reserved_backup_dir.exists() else 'false'}")
print(f"EXACT_STOP_ROUTE_STATUS={future_stop_contract['status']}")
print("EXACT_RESTART_ROUTE_STATUS=RESOLVED_PENDING_HUMAN_REVIEW")
print(f"EXECUTION_ELIGIBILITY={'true' if execution_eligibility else 'false'}")
print(f"EXECUTION_ELIGIBILITY_STATUS={eligibility_status}")
print(f"MAXIMUM_WRITER_FREEZE_SECONDS={MAX_FREEZE_SECONDS}")
print("RESTART_PROFILE=SAFE_MINIMAL_MAINTENANCE_MODE")
print("WORDPRESS_EXTERNAL_ACTIONS_AFTER_RESTART=HOLD")
print("FULL_OPERATIONAL_PARITY_AFTER_RESTART=NOT_ESTABLISHED")
print(f"PACKET_FILE_COUNT={result['packet_file_count']}")
print(f"PACKET_MANIFEST_SHA={result['packet_manifest_sha256']}")
print(f"PACKET_SEMANTIC_VALIDATION_SHA={result['packet_semantic_validation_sha256']}")
print(f"RESULT_SHA={sha256(evidence_root / 'result.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(evidence_root / 'evidence-manifest.txt')}")
print("RAW_CRONTAB_SAVED=false")
print("CRONTAB_SECRET_VALUES_SAVED=false")
print("PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("CRONTAB_CHANGED=false")
print("SYSTEMD_CHANGED=false")
print("TIMER_CHANGED=false")
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
print("NEXT_GATE=HUMAN_REVIEW_3E_I_WRITER_FREEZE_BACKUP_EXECUTION_PACKET")
PY

trap - ERR
printf 'SCRIPT_EXIT_CODE=0\n'
