#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PHASE="TST-5D-W2B-I2F-3E-G"
REPO_ROOT="/home/deploy/ai_media_os"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

F1_REL="${BASE_REL}/i2f3e-f1-evidence-copy-normalization-reseal-20260725T140856Z-509951"
F1_ROOT="${REPO_ROOT}/${F1_REL}"

EXPECTED_F1_RESULT_SHA="05eb0ac5f36e4e8b346be8a633cecb3d5798469f5901f1d799074bb7a43450ce"
EXPECTED_F1_PROVENANCE_SHA="4e05d14be765be28e6f6ae6be147e34b917164cd50ce053ae84e09757dc662ec"
EXPECTED_F1_EVIDENCE_MANIFEST_SHA="b71be1255a523257354cf089b50eaab4ea96151fca738f97a9398e15a84d08fb"

EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_RUNTIME_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"

TARGET_SCRIPT="${REPO_ROOT}/scripts/new_release_multistore_app.py"
TARGET_HOST="127.0.0.1"
TARGET_PORT="8765"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_REL="${BASE_REL}/i2f3e-g-gui-stop-restart-route-resolution-readonly-${RUN_ID}"
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
      printf 'PRODUCTION_DB_OPENED=false\n'
      printf 'SQL_EXECUTED=false\n'
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

test -f "$F1_ROOT/corrective-result.json"
test -f "$F1_ROOT/provenance-record.json"
test -f "$F1_ROOT/evidence-manifest.txt"
test -f "$F1_ROOT/corrected-packet-snapshot/stop-restart-scope-plan.json"
test -f "$TARGET_SCRIPT"

echo "${EXPECTED_F1_RESULT_SHA}  ${F1_ROOT}/corrective-result.json" | sha256sum -c -
echo "${EXPECTED_F1_PROVENANCE_SHA}  ${F1_ROOT}/provenance-record.json" | sha256sum -c -
echo "${EXPECTED_F1_EVIDENCE_MANIFEST_SHA}  ${F1_ROOT}/evidence-manifest.txt" | sha256sum -c -

cp --reflink=never --preserve=none \
  "$F1_ROOT/corrective-result.json" \
  "$INPUT_ROOT/3e-f1-corrective-result.json"

cp --reflink=never --preserve=none \
  "$F1_ROOT/provenance-record.json" \
  "$INPUT_ROOT/3e-f1-provenance-record.json"

cp --reflink=never --preserve=none \
  "$F1_ROOT/evidence-manifest.txt" \
  "$INPUT_ROOT/3e-f1-evidence-manifest.txt"

cp --reflink=never --preserve=none \
  "$F1_ROOT/corrected-packet-snapshot/stop-restart-scope-plan.json" \
  "$INPUT_ROOT/3e-f-stop-restart-scope-plan.json"

cat > "$PACKET_ROOT/human-approval-verbatim.txt" <<'APPROVAL'
承認：
F1_CORRECTED_EVIDENCE_REVIEW=APPROVE
3E_F1_EVIDENCE_COPY_NORMALIZATION_AND_RESEAL=PASS
APPROVE_3E_G_GUI_GRACEFUL_STOP_RESTART_ROUTE_RESOLUTION_READONLY

許可範囲：
1. 電子書籍GUI scripts/new_release_multistore_app.py --host 127.0.0.1 --port 8765 の
   現行PID、PPID、start time、cmdline、cwd、exe、UID、cgroup、session、process groupを読み取り確認する。
2. PID 1配下となった経緯と、systemd service、user service、transient scope、nohup、
   shell background、VS Code terminal、manual commandのいずれで起動されたかを読み取り調査する。
3. /proc/<pid>/fd/0、fd/1、fd/2の参照先を読み取り確認し、
   stdin、stdout、stderrの復旧条件を記録する。
4. /proc/<pid>/environを秘密値をEvidenceへ出力しない方式で解析し、
   DB path、repo root、host、port、Python executable、runtime modeに関係する非秘密項目だけを記録する。
5. systemctl、systemctl --user、loginctl、ps、pstree、/proc、journalctlの読み取り専用照会を行う。
6. Repository内のGUI起動手順、service unit候補、README、scripts、運用Evidenceを静的検索する。
7. graceful stop方法を EXISTING_SERVICE_STOP、SIGTERM_TO_EXACT_PID、
   APPLICATION_SHUTDOWN_ENDPOINT、FOREGROUND_TERMINAL_INTERRUPT、UNRESOLVED から判定する。
8. exact restart commandについて、実行せずに working directory、Python executable、script path、
   arguments、environment source、stdout/stderr destination、background/foreground方式、
   PID管理方法、readiness checkを固定する。
9. 起動前後の想定検証、失敗時rollback、PID再利用防止、host/port競合確認を準備Packetへ記録する。
10. 新しい一意なshadow/evidence領域へ保存する。

禁止事項：
process signal送信、GUI停止・再起動、writer停止、systemctl stop/start/restart、
service作成・変更、cron変更、timer変更、Production DB接続、SQL実行、backup、restore、
migration、manifest変更、source/test変更、git add、git commit、deployment、外部通信、
Slack Worker起動、production approval、production release承認は禁止する。

追加条件：
1. /proc/<pid>/environのtoken、password、secret、credential、key、cookie、authorization値は保存・表示しない。
2. PIDだけに依存せず、cmdline、start time、exe、cwdを含むprocess identity contractを作成する。
3. exact stopとexact restartの両方が確定しなければWRITER_FREEZE_EXECUTIONはHOLDのままとする。
4. 3E-G成功後もWriter freezeへ自動遷移せず、人間レビューを次ゲートとする。

WRITER_FREEZE_EXECUTION=HOLD
PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

# All substantive inspection and redaction is performed in one Python process.
python3 - \
  "$REPO_ROOT" \
  "$F1_ROOT" \
  "$F1_REL" \
  "$EVIDENCE_ROOT" \
  "$EVIDENCE_REL" \
  "$PACKET_ROOT" \
  "$TARGET_SCRIPT" \
  "$TARGET_HOST" \
  "$TARGET_PORT" \
  "$EXPECTED_DB_SHA" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_WORKFLOW_SHA" \
  "$EXPECTED_MIGRATION_SHA" \
  "$EXPECTED_SLACK_RUNTIME_SHA" \
  "$EXPECTED_PROMOTED_TEST_SHA" <<'PY'
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pwd
import re
import shlex
import socket
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

(
    repo_root_s,
    f1_root_s,
    f1_rel,
    evidence_root_s,
    evidence_rel,
    packet_root_s,
    target_script_s,
    target_host,
    target_port,
    expected_db_sha,
    expected_manifest_sha,
    expected_workflow_sha,
    expected_migration_sha,
    expected_slack_runtime_sha,
    expected_promoted_test_sha,
) = sys.argv[1:]

repo_root = Path(repo_root_s).resolve()
f1_root = Path(f1_root_s).resolve()
evidence_root = Path(evidence_root_s).resolve()
packet_root = Path(packet_root_s).resolve()
target_script = Path(target_script_s).resolve()

phase = "TST-5D-W2B-I2F-3E-G"
now_utc = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path}")
    return value

def read_proc_bytes(pid: int, name: str) -> bytes:
    return (Path("/proc") / str(pid) / name).read_bytes()

def read_proc_text(pid: int, name: str) -> str:
    return read_proc_bytes(pid, name).decode("utf-8", errors="replace")

def read_link(path: Path) -> str | None:
    try:
        return os.readlink(path)
    except (FileNotFoundError, PermissionError, OSError):
        return None

def safe_run(
    command: list[str],
    *,
    timeout: int = 10,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
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
    except FileNotFoundError as exc:
        return {
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }

SECRET_KEY_RE = re.compile(
    r"(TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE|API_KEY|ACCESS_KEY|"
    r"COOKIE|AUTHORIZATION|SESSION|BEARER|SIGNING|CLIENT_SECRET)",
    re.IGNORECASE,
)

SAFE_ENV_EXACT = {
    "PWD",
    "OLDPWD",
    "HOME",
    "USER",
    "LOGNAME",
    "VIRTUAL_ENV",
    "PYTHONPATH",
    "PYTHONHOME",
    "HOST",
    "PORT",
    "APP_ENV",
    "ENVIRONMENT",
    "RUNTIME_MODE",
    "MODE",
    "WP_DRY_RUN",
    "AI_MEDIA_OS_REPO_ROOT",
    "REPO_ROOT",
    "EBOOK_DB_PATH",
    "EBOOK_AFFILIATE_DB_PATH",
    "DATABASE_PATH",
    "SQLITE_PATH",
}

SAFE_ENV_PREFIXES = (
    "EBOOK_",
    "AI_MEDIA_",
    "NEW_RELEASE_",
)

def sanitize_environment(raw: bytes) -> dict[str, Any]:
    selected: dict[str, str] = {}
    redacted_names: list[str] = []
    ignored_count = 0

    for entry in raw.split(b"\0"):
        if not entry or b"=" not in entry:
            continue

        key_b, value_b = entry.split(b"=", 1)
        key = key_b.decode("utf-8", errors="replace")
        value = value_b.decode("utf-8", errors="replace")

        if SECRET_KEY_RE.search(key):
            redacted_names.append(key)
            continue

        allowed = key in SAFE_ENV_EXACT or key.startswith(SAFE_ENV_PREFIXES)
        if not allowed:
            ignored_count += 1
            continue

        # URL-like database values may contain credentials. Keep only safe SQLite paths.
        if key in {"DATABASE_URL", "DB_URL"} or "URL" in key:
            if value.startswith("sqlite:///"):
                selected[key] = "sqlite:///" + value.removeprefix("sqlite:///")
            else:
                selected[key] = "<REDACTED_NON_SQLITE_URL>"
            continue

        # Allow only reasonably short, single-line non-secret values.
        value = value.replace("\r", "\\r").replace("\n", "\\n")
        selected[key] = value[:1024]

    return {
        "selected_non_secret_values": dict(sorted(selected.items())),
        "redacted_secret_variable_names": sorted(set(redacted_names)),
        "redacted_secret_variable_count": len(set(redacted_names)),
        "ignored_variable_count": ignored_count,
        "raw_environment_saved": False,
        "secret_values_saved": False,
    }

def proc_cmdline(pid: int) -> list[str]:
    raw = read_proc_bytes(pid, "cmdline")
    return [
        part.decode("utf-8", errors="replace")
        for part in raw.split(b"\0")
        if part
    ]

def proc_status(pid: int) -> dict[str, str]:
    values: dict[str, str] = {}
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

    # fields after comm start at process state (field 3)
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

def process_identity(pid: int) -> dict[str, Any]:
    stat_fields = proc_stat_fields(pid)
    status = proc_status(pid)
    cmdline = proc_cmdline(pid)
    proc_root = Path("/proc") / str(pid)

    uid_parts = status.get("Uid", "").split()
    uid = int(uid_parts[0]) if uid_parts else None
    username = pwd.getpwuid(uid).pw_name if uid is not None else None

    fds: dict[str, str | None] = {}
    for fd in ("0", "1", "2"):
        fds[fd] = read_link(proc_root / "fd" / fd)

    return {
        "pid": pid,
        "ppid": stat_fields["ppid"],
        "process_group_id": stat_fields["pgrp"],
        "session_id": stat_fields["session"],
        "tty_nr": stat_fields["tty_nr"],
        "state": stat_fields["state"],
        "comm": stat_fields["comm"],
        "starttime_ticks": stat_fields["starttime_ticks"],
        "start_time_utc": process_start_iso(stat_fields["starttime_ticks"]),
        "cmdline_argv": cmdline,
        "cmdline_shell_quoted": shlex.join(cmdline),
        "cwd": read_link(proc_root / "cwd"),
        "exe": read_link(proc_root / "exe"),
        "root": read_link(proc_root / "root"),
        "uid": uid,
        "username": username,
        "gid_status": status.get("Gid"),
        "cgroup_lines": read_proc_text(pid, "cgroup").splitlines(),
        "stdin_target": fds["0"],
        "stdout_target": fds["1"],
        "stderr_target": fds["2"],
        "environment": sanitize_environment(read_proc_bytes(pid, "environ")),
    }

def matching_gui_processes() -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    for entry in sorted(Path("/proc").iterdir(), key=lambda p: p.name):
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            argv = proc_cmdline(pid)
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue

        if not argv:
            continue

        normalized = [str(Path(arg).resolve()) if arg.endswith(".py") and Path(arg).exists() else arg for arg in argv]

        script_match = str(target_script) in normalized or str(target_script) in argv
        host_match = "--host" in argv and target_host in argv
        port_match = "--port" in argv and target_port in argv

        if script_match and host_match and port_match:
            try:
                matches.append(process_identity(pid))
            except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
                continue

    return matches

def ancestry(pid: int, limit: int = 32) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    current = pid

    while current > 0 and current not in seen and len(chain) < limit:
        seen.add(current)
        try:
            identity = process_identity(current)
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            chain.append({"pid": current, "inspection": "UNAVAILABLE"})
            break

        # Do not retain ancestor environments.
        identity.pop("environment", None)
        chain.append(identity)
        current = int(identity["ppid"])

    return chain

def redact_text(text: str) -> str:
    redacted_lines: list[str] = []
    assignment_re = re.compile(
        r"(?i)\b(token|password|passwd|secret|credential|private[_-]?key|"
        r"api[_-]?key|access[_-]?key|cookie|authorization|bearer)\b"
        r"(\s*[:=]\s*)([^\s]+)"
    )
    cli_option_re = re.compile(
        r"(?i)(--(?:token|password|passwd|secret|credential|private-key|"
        r"api-key|access-key|cookie|authorization|bearer))"
        r"(\s+|=)([^\s]+)"
    )

    for raw_line in text.splitlines():
        line = assignment_re.sub(lambda m: f"{m.group(1)}{m.group(2)}<REDACTED>", raw_line)
        line = cli_option_re.sub(lambda m: f"{m.group(1)}{m.group(2)}<REDACTED>", line)
        if len(line) > 4000:
            line = line[:4000] + "<TRUNCATED>"
        redacted_lines.append(line)

    return "\n".join(redacted_lines)

def command_metadata(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    result = safe_run(command, env=env)
    return {
        "command": command,
        "exit_code": result["exit_code"],
        "timed_out": result["timed_out"],
        "stdout": redact_text(str(result["stdout"])),
        "stderr": redact_text(str(result["stderr"])),
    }

def identify_systemd_units(cgroup_lines: list[str]) -> dict[str, list[str]]:
    services: set[str] = set()
    scopes: set[str] = set()
    slices: set[str] = set()

    for line in cgroup_lines:
        _, _, path = line.partition(":")
        _, _, path = path.partition(":")
        for component in path.split("/"):
            if component.endswith(".service"):
                services.add(component)
            elif component.endswith(".scope"):
                scopes.add(component)
            elif component.endswith(".slice"):
                slices.add(component)

    return {
        "services": sorted(services),
        "scopes": sorted(scopes),
        "slices": sorted(slices),
    }

def static_search() -> dict[str, Any]:
    roots = [
        repo_root / "scripts",
        repo_root / "app",
        repo_root / "config",
        repo_root / "reports",
        repo_root / "docs",
        repo_root,
    ]
    allowed_suffixes = {
        ".py", ".sh", ".md", ".txt", ".json", ".yaml", ".yml",
        ".service", ".timer", ".ini", ".toml", ".conf",
    }
    patterns = [
        re.compile(r"new_release_multistore_app\.py"),
        re.compile(r"\b8765\b"),
        re.compile(r"\bnohup\b"),
        re.compile(r"systemctl\s+(?:--user\s+)?(?:start|stop|restart)"),
        re.compile(r"\.service\b"),
    ]

    excluded_parts = {
        ".git", ".venv", "__pycache__", "exchange", "backups",
        "data", "node_modules", ".pytest_cache",
    }

    seen_paths: set[Path] = set()
    matches: list[dict[str, Any]] = []
    files_scanned = 0

    for root in roots:
        if not root.exists():
            continue

        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            try:
                resolved = path.resolve()
            except OSError:
                continue

            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)

            if any(part in excluded_parts for part in resolved.parts):
                continue
            if not resolved.is_file():
                continue
            if resolved.suffix.lower() not in allowed_suffixes and resolved.name not in {"README", "Makefile"}:
                continue
            try:
                if resolved.stat().st_size > 2_000_000:
                    continue
                text = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            files_scanned += 1
            for line_number, raw_line in enumerate(text.splitlines(), start=1):
                if not any(pattern.search(raw_line) for pattern in patterns):
                    continue
                line = redact_text(raw_line.strip())
                matches.append(
                    {
                        "path": str(resolved.relative_to(repo_root)),
                        "line_number": line_number,
                        "line": line[:2000],
                    }
                )
                if len(matches) >= 300:
                    return {
                        "files_scanned": files_scanned,
                        "match_count": len(matches),
                        "truncated": True,
                        "matches": matches,
                    }

    return {
        "files_scanned": files_scanned,
        "match_count": len(matches),
        "truncated": False,
        "matches": matches,
    }

def listener_inventory(pid: int | None) -> dict[str, Any]:
    ss_result = safe_run(["ss", "-ltnp"])
    lines = redact_text(str(ss_result["stdout"])).splitlines()
    relevant = [
        line
        for line in lines
        if f":{target_port}" in line or target_host in line
    ]

    pid_text = str(pid) if pid is not None else None
    pid_mentioned = bool(pid_text and any(f"pid={pid_text}" in line for line in relevant))

    return {
        "command": ["ss", "-ltnp"],
        "exit_code": ss_result["exit_code"],
        "timed_out": ss_result["timed_out"],
        "target_host": target_host,
        "target_port": int(target_port),
        "relevant_lines": relevant,
        "target_pid_mentioned": pid_mentioned,
        "network_connection_opened": False,
        "status": "LOCAL_KERNEL_SOCKET_INVENTORY_ONLY",
    }

def fd_route(target: str | None) -> dict[str, Any]:
    if target is None:
        return {"target": None, "classification": "UNAVAILABLE", "restart_reproducible": False}
    if target.startswith("/dev/pts/"):
        return {"target": target, "classification": "TERMINAL", "restart_reproducible": False}
    if target == "/dev/null":
        return {"target": target, "classification": "DEV_NULL", "restart_reproducible": True}
    if target.startswith("pipe:["):
        return {"target": target, "classification": "PIPE", "restart_reproducible": False}
    if target.startswith("socket:["):
        return {"target": target, "classification": "SOCKET", "restart_reproducible": False}
    if target.startswith("/"):
        return {
            "target": target,
            "classification": "FILESYSTEM_PATH",
            "restart_reproducible": True,
        }
    return {"target": target, "classification": "OTHER", "restart_reproducible": False}

def detect_pidfile_references(search_results: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for match in search_results["matches"]:
        line_lower = match["line"].lower()
        if "pid" in line_lower and (
            "new_release_multistore_app" in line_lower or "8765" in line_lower
        ):
            results.append(match)
    return results[:50]

def classify_launch(
    identity: dict[str, Any],
    chain: list[dict[str, Any]],
    units: dict[str, list[str]],
) -> str:
    ancestor_text = " ".join(
        item.get("cmdline_shell_quoted", "")
        for item in chain
        if isinstance(item, dict)
    ).lower()

    if units["services"]:
        return "SYSTEMD_SERVICE"
    if units["scopes"] and any("run-" in scope or "app-" in scope for scope in units["scopes"]):
        return "SYSTEMD_TRANSIENT_SCOPE"
    if "vscode-server" in ancestor_text or "remote-cli" in ancestor_text or "code-server" in ancestor_text:
        return "VSCODE_REMOTE_TERMINAL_OR_BACKGROUND"
    if identity["stdin_target"] and str(identity["stdin_target"]).startswith("/dev/pts/"):
        return "FOREGROUND_OR_TERMINAL_BACKGROUND"
    if identity["ppid"] == 1:
        return "ORPHANED_MANUAL_BACKGROUND_OR_NOHUP"
    if any(shell in ancestor_text for shell in ("bash", "zsh", "sh ", "fish")):
        return "SHELL_MANAGED_PROCESS"
    return "UNRESOLVED"

def exact_identity_contract(identity: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "pid": identity["pid"],
        "starttime_ticks": identity["starttime_ticks"],
        "start_time_utc": identity["start_time_utc"],
        "cmdline_argv": identity["cmdline_argv"],
        "cmdline_shell_quoted": identity["cmdline_shell_quoted"],
        "cwd": identity["cwd"],
        "exe": identity["exe"],
        "uid": identity["uid"],
        "username": identity["username"],
        "session_id": identity["session_id"],
        "process_group_id": identity["process_group_id"],
    }
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fields["identity_sha256"] = hashlib.sha256(canonical).hexdigest()
    fields["pid_reuse_prevention_checks"] = [
        "PID exists immediately before any future stop action.",
        "starttime_ticks equals the reviewed value.",
        "cmdline_argv equals the reviewed value.",
        "cwd equals the reviewed value.",
        "exe equals the reviewed value.",
        "uid equals the reviewed value.",
        "target port ownership is rechecked.",
    ]
    return fields

def protected_sha_inventory() -> dict[str, Any]:
    paths = [
        ("production_database", repo_root / "data/database/ebook_affiliate.db", expected_db_sha),
        ("production_manifest", repo_root / "config/slack_worker_release_source_manifest.json", expected_manifest_sha),
        ("workflow_source", repo_root / "app/db/repositories/workflow_state_repository.py", expected_workflow_sha),
        ("migration_source", repo_root / "migrations/versions/00241611109d_add_unique_wordpress_post_id.py", expected_migration_sha),
        ("slack_runtime_source", repo_root / "scripts/run_slack_approval_socket.py", expected_slack_runtime_sha),
        ("promoted_test", repo_root / "tests/test_slack_approval_socket_hold_remediation_offline.py", expected_promoted_test_sha),
    ]

    entries = []
    for label, path, expected in paths:
        require(path.is_file(), f"PROTECTED_PATH_MISSING:{path}")
        actual = sha256(path)
        require(actual == expected, f"PROTECTED_SHA_MISMATCH:{label}:{actual}")
        metadata = path.stat()
        entries.append(
            {
                "label": label,
                "path": str(path),
                "sha256": actual,
                "size_bytes": metadata.st_size,
                "inode": metadata.st_ino,
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            }
        )

    return {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "files": entries,
        "production_database_opened": False,
        "sql_executed": False,
    }

f1_result = read_json(f1_root / "corrective-result.json")
require(f1_result.get("result") == "PASS_W2B_I2F3E_F1_EVIDENCE_COPY_NORMALIZED_AND_RESEALED", "F1_RESULT_INVALID")
require(f1_result.get("source_evidence_mutated") is False, "F1_SOURCE_MUTATION_FLAG_INVALID")
require(f1_result.get("writer_freeze_execution") == "HOLD", "F1_WRITER_FREEZE_INVALID")
require(f1_result.get("production_release_decision") == "HOLD", "F1_RELEASE_DECISION_INVALID")

protected_before = protected_sha_inventory()
write_json(packet_root / "protected-sha-before.json", protected_before)

matches = matching_gui_processes()
process_state = (
    "RUNNING_SINGLE_MATCH"
    if len(matches) == 1
    else "NOT_FOUND"
    if len(matches) == 0
    else "MULTIPLE_MATCHES"
)

identity = matches[0] if len(matches) == 1 else None
chain = ancestry(identity["pid"]) if identity else []
units = identify_systemd_units(identity["cgroup_lines"]) if identity else {
    "services": [],
    "scopes": [],
    "slices": [],
}

system_queries: dict[str, Any] = {}
user_runtime = f"/run/user/{os.getuid()}"
user_env = dict(os.environ)
if Path(user_runtime).is_dir():
    user_env["XDG_RUNTIME_DIR"] = user_runtime

if identity:
    pid = identity["pid"]
    system_queries["ps"] = command_metadata([
        "ps", "-o",
        "pid,ppid,sid,pgid,lstart,etimes,tty,stat,user,group,comm,args",
        "-p", str(pid),
    ])
    system_queries["pstree"] = command_metadata(["pstree", "-aps", str(pid)])
    system_queries["systemctl_status_pid"] = command_metadata([
        "systemctl", "status", str(pid), "--no-pager", "--full",
    ])
    system_queries["systemctl_show_pid"] = command_metadata([
        "systemctl", "show", str(pid),
        "--property=Id,Names,Description,LoadState,ActiveState,SubState,"
        "FragmentPath,SourcePath,MainPID,ControlPID,User,Group,ExecStart,"
        "StandardInput,StandardOutput,StandardError",
        "--no-pager",
    ])
    system_queries["systemctl_user_status_pid"] = command_metadata([
        "systemctl", "--user", "status", str(pid), "--no-pager", "--full",
    ], env=user_env)
    system_queries["systemctl_user_show_pid"] = command_metadata([
        "systemctl", "--user", "show", str(pid),
        "--property=Id,Names,Description,LoadState,ActiveState,SubState,"
        "FragmentPath,SourcePath,MainPID,ControlPID,ExecStart,"
        "StandardInput,StandardOutput,StandardError",
        "--no-pager",
    ], env=user_env)
    system_queries["loginctl_user_status"] = command_metadata([
        "loginctl", "user-status", identity["username"] or str(identity["uid"]),
        "--no-pager",
    ])
    system_queries["loginctl_list_sessions"] = command_metadata([
        "loginctl", "list-sessions", "--no-legend", "--no-pager",
    ])
    system_queries["journal_metadata_by_pid"] = command_metadata([
        "journalctl",
        f"_PID={pid}",
        "-n", "20",
        "--no-pager",
        "-o", "json",
        "--output-fields=_PID,_COMM,_EXE,_SYSTEMD_UNIT,_SYSTEMD_USER_UNIT,"
        "_SYSTEMD_CGROUP,_SYSTEMD_SESSION,_UID,_GID",
    ])
else:
    system_queries["process_missing_note"] = {
        "status": "TARGET_GUI_PROCESS_NOT_FOUND",
        "commands_not_run": True,
    }

search_results = static_search()
listener = listener_inventory(identity["pid"] if identity else None)

launch_origin = classify_launch(identity, chain, units) if identity else "UNRESOLVED"

stdio = {
    "stdin": fd_route(identity["stdin_target"] if identity else None),
    "stdout": fd_route(identity["stdout_target"] if identity else None),
    "stderr": fd_route(identity["stderr_target"] if identity else None),
}

pidfile_references = detect_pidfile_references(search_results)

stop_method = "UNRESOLVED"
exact_stop_status = "UNRESOLVED"
exact_stop_contract: dict[str, Any] = {
    "method": "UNRESOLVED",
    "execution_allowed": False,
}

if identity:
    if units["services"]:
        stop_method = "EXISTING_SERVICE_STOP"
        exact_stop_status = "RESOLVED_PENDING_HUMAN_REVIEW"
        exact_stop_contract = {
            "method": stop_method,
            "unit_candidates": units["services"],
            "command_template": ["systemctl", "stop", "<EXACT_REVIEWED_UNIT>"],
            "identity_revalidation_required": True,
            "execution_allowed": False,
        }
    elif identity["stdin_target"] and str(identity["stdin_target"]).startswith("/dev/pts/"):
        stop_method = "FOREGROUND_TERMINAL_INTERRUPT"
        exact_stop_status = "UNRESOLVED_TERMINAL_OWNERSHIP_REQUIRED"
        exact_stop_contract = {
            "method": stop_method,
            "terminal": identity["stdin_target"],
            "command_template": "Ctrl-C in the exact owning foreground terminal",
            "identity_revalidation_required": True,
            "execution_allowed": False,
        }
    elif launch_origin in {
        "ORPHANED_MANUAL_BACKGROUND_OR_NOHUP",
        "VSCODE_REMOTE_TERMINAL_OR_BACKGROUND",
        "SHELL_MANAGED_PROCESS",
        "SYSTEMD_TRANSIENT_SCOPE",
    }:
        stop_method = "SIGTERM_TO_EXACT_PID"
        exact_stop_status = "RESOLVED_PENDING_HUMAN_REVIEW"
        exact_stop_contract = {
            "method": stop_method,
            "signal": "SIGTERM",
            "command_template": [
                "kill", "-TERM", str(identity["pid"]),
            ],
            "process_identity_contract_required": True,
            "wait_for_exit_seconds": 30,
            "kill_9_allowed": False,
            "execution_allowed": False,
        }

identity_contract = exact_identity_contract(identity) if identity else {
    "status": "UNAVAILABLE_TARGET_PROCESS_NOT_SINGLE",
}

restart_argv = identity["cmdline_argv"] if identity else []
restart_working_directory = identity["cwd"] if identity else None
restart_python = restart_argv[0] if restart_argv else None
restart_script = restart_argv[1] if len(restart_argv) > 1 else None
restart_arguments = restart_argv[2:] if len(restart_argv) > 2 else []

environment_info = identity["environment"] if identity else {
    "selected_non_secret_values": {},
    "redacted_secret_variable_names": [],
    "redacted_secret_variable_count": 0,
    "ignored_variable_count": 0,
    "raw_environment_saved": False,
    "secret_values_saved": False,
}

if not identity:
    environment_source_status = "UNRESOLVED_PROCESS_NOT_SINGLE"
elif units["services"]:
    environment_source_status = "RESOLVED_FROM_SYSTEMD_UNIT_AND_ALLOWLISTED_LIVE_VALUES"
else:
    environment_source_status = "PARTIAL_ALLOWLISTED_LIVE_PROCESS_VALUES_ONLY"

stdio_reproducible = (
    identity is not None
    and stdio["stdout"]["restart_reproducible"]
    and stdio["stderr"]["restart_reproducible"]
)

background_mode = "UNRESOLVED"
if identity:
    if identity["stdin_target"] and str(identity["stdin_target"]).startswith("/dev/pts/"):
        background_mode = "TERMINAL_ATTACHED"
    elif identity["ppid"] == 1:
        background_mode = "DETACHED_BACKGROUND"
    else:
        background_mode = "PROCESS_TREE_MANAGED"

pid_management_method = "NONE_DETECTED"
if units["services"]:
    pid_management_method = "SYSTEMD_MAINPID"
elif pidfile_references:
    pid_management_method = "PIDFILE_OR_PID_REFERENCE_CANDIDATE_REQUIRES_REVIEW"
elif identity and identity["ppid"] == 1:
    pid_management_method = "MANUAL_PROCESS_DISCOVERY_BY_IDENTITY_CONTRACT"

restart_components = {
    "single_process_match": len(matches) == 1,
    "working_directory_known": bool(restart_working_directory),
    "python_executable_known": bool(restart_python),
    "script_path_known": bool(restart_script),
    "arguments_known": bool(restart_argv),
    "environment_source_known": environment_source_status
    == "RESOLVED_FROM_SYSTEMD_UNIT_AND_ALLOWLISTED_LIVE_VALUES",
    "stdout_destination_reproducible": bool(identity and stdio["stdout"]["restart_reproducible"]),
    "stderr_destination_reproducible": bool(identity and stdio["stderr"]["restart_reproducible"]),
    "background_foreground_mode_known": background_mode != "UNRESOLVED",
    "pid_management_method_known": pid_management_method != "NONE_DETECTED",
    "readiness_check_defined": True,
}

exact_restart_resolved = all(restart_components.values())
exact_restart_status = (
    "RESOLVED_PENDING_HUMAN_REVIEW"
    if exact_restart_resolved
    else "UNRESOLVED_MISSING_REPRODUCIBLE_RUNTIME_COMPONENTS"
)

restart_shell_command = (
    f"cd {shlex.quote(restart_working_directory)} && "
    + shlex.join(restart_argv)
    if restart_working_directory and restart_argv
    else None
)

restart_contract = {
    "status": exact_restart_status,
    "execution_allowed": False,
    "working_directory": restart_working_directory,
    "python_executable_argv0": restart_python,
    "resolved_proc_exe": identity["exe"] if identity else None,
    "script_path": restart_script,
    "arguments": restart_arguments,
    "argv": restart_argv,
    "shell_command_without_redirection": restart_shell_command,
    "environment_source_status": environment_source_status,
    "selected_non_secret_environment": environment_info["selected_non_secret_values"],
    "secret_environment_values_saved": False,
    "stdout_destination": stdio["stdout"],
    "stderr_destination": stdio["stderr"],
    "stdin_destination": stdio["stdin"],
    "background_foreground_mode": background_mode,
    "pid_management_method": pid_management_method,
    "readiness_check": {
        "type": "LOCAL_LISTENER_AND_PROCESS_IDENTITY",
        "host": target_host,
        "port": int(target_port),
        "commands_for_future_approved_execution": [
            ["ss", "-ltnp"],
            ["ps", "-o", "pid,ppid,sid,pgid,lstart,tty,stat,user,comm,args", "-p", "<NEW_PID>"],
        ],
        "http_request_required": False,
        "external_network_required": False,
    },
    "component_resolution": restart_components,
}

rollback_plan = {
    "status": "PLAN_ONLY_NOT_EXECUTED",
    "execution_allowed": False,
    "pre_stop_checks": [
        "Revalidate exact process identity contract.",
        "Confirm no duplicate GUI process exists.",
        "Confirm target listener is owned by the reviewed process.",
        "Confirm approved freeze window and cron window control are active.",
        "Capture fresh protected SHA inventory.",
    ],
    "post_stop_checks": [
        "Confirm reviewed process identity no longer exists.",
        "Confirm 127.0.0.1:8765 listener is absent.",
        "Confirm DB/WAL/SHM open handles are zero using the separately approved root check.",
        "Do not proceed if a new PID reuses the old numeric PID with different starttime_ticks.",
    ],
    "restart_checks": [
        "Revalidate the restart contract before execution.",
        "Confirm host and port are free.",
        "Start only once.",
        "Capture new PID and build a new identity contract.",
        "Confirm listener appears on 127.0.0.1:8765.",
        "Confirm no second GUI instance exists.",
        "Confirm no source or manifest SHA changed.",
    ],
    "rollback_if_restart_fails": [
        "Do not retry in a loop.",
        "Preserve stdout/stderr and process identity evidence.",
        "Confirm no partial listener remains.",
        "Keep writer freeze active only within its approved maximum duration.",
        "Require a new human decision before any alternate launch route.",
    ],
}

route_resolution = {
    "schema_version": "1.0",
    "phase": phase,
    "captured_at_utc": now_utc(),
    "target": {
        "script": str(target_script),
        "host": target_host,
        "port": int(target_port),
    },
    "process_state": process_state,
    "matching_process_count": len(matches),
    "process_identity": identity,
    "process_ancestry": chain,
    "systemd_membership_candidates": units,
    "launch_origin_classification": launch_origin,
    "stdio_routes": stdio,
    "system_queries": system_queries,
    "repository_static_search": search_results,
    "pidfile_reference_candidates": pidfile_references,
    "listener_inventory": listener,
    "graceful_stop_method": stop_method,
    "exact_stop_status": exact_stop_status,
    "exact_stop_contract": exact_stop_contract,
    "exact_restart_status": exact_restart_status,
    "exact_restart_contract": restart_contract,
    "process_identity_contract": identity_contract,
    "rollback_and_validation_plan": rollback_plan,
    "environment_redaction": {
        "raw_environment_saved": False,
        "secret_values_saved": False,
        "redacted_secret_variable_count": environment_info["redacted_secret_variable_count"],
        "redacted_secret_variable_names": environment_info["redacted_secret_variable_names"],
        "ignored_variable_count": environment_info["ignored_variable_count"],
    },
    "execution": {
        "process_signal_sent": False,
        "writer_stop_performed": False,
        "gui_stopped_or_restarted": False,
        "systemctl_stop_start_restart_executed": False,
        "service_created_or_modified": False,
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
    },
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_G_GUI_STOP_RESTART_ROUTE_PACKET",
}
write_json(packet_root / "gui-stop-restart-route-resolution.json", route_resolution)

write_json(
    packet_root / "process-identity-contract.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "process_state": process_state,
        "contract": identity_contract,
        "execution_allowed": False,
        "pid_only_targeting_forbidden": True,
        "writer_freeze_execution": "HOLD",
    },
)

write_json(
    packet_root / "exact-stop-contract.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "method": stop_method,
        "status": exact_stop_status,
        "contract": exact_stop_contract,
        "execution_allowed": False,
        "writer_freeze_execution": "HOLD",
    },
)

write_json(
    packet_root / "exact-restart-contract.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "status": exact_restart_status,
        "contract": restart_contract,
        "execution_allowed": False,
        "writer_freeze_execution": "HOLD",
    },
)

write_json(
    packet_root / "rollback-and-readiness-plan.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        **rollback_plan,
        "listener_inventory_snapshot": listener,
        "writer_freeze_execution": "HOLD",
    },
)

write_json(
    packet_root / "environment-redaction-report.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "selected_non_secret_values": environment_info["selected_non_secret_values"],
        "redacted_secret_variable_names": environment_info["redacted_secret_variable_names"],
        "redacted_secret_variable_count": environment_info["redacted_secret_variable_count"],
        "ignored_variable_count": environment_info["ignored_variable_count"],
        "raw_environment_saved": False,
        "secret_values_saved": False,
    },
)

write_json(
    packet_root / "repository-launch-route-search.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        **search_results,
        "source_modified": False,
        "search_only": True,
    },
)

write_json(
    packet_root / "system-and-session-readonly-inventory.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "queries": system_queries,
        "systemctl_stop_start_restart_executed": False,
        "systemd_changed": False,
        "journal_message_field_requested": False,
        "secret_values_saved": False,
    },
)

protected_after = protected_sha_inventory()
write_json(packet_root / "protected-sha-after.json", protected_after)
require(
    [item["sha256"] for item in protected_before["files"]]
    == [item["sha256"] for item in protected_after["files"]],
    "PROTECTED_SHA_CHANGED",
)

both_exact = (
    exact_stop_status == "RESOLVED_PENDING_HUMAN_REVIEW"
    and exact_restart_status == "RESOLVED_PENDING_HUMAN_REVIEW"
)

semantic_validation = {
    "schema_version": "1.0",
    "phase": phase,
    "result": "PASS_3E_G_GUI_STOP_RESTART_ROUTE_RESOLUTION_READONLY",
    "process_state": process_state,
    "matching_process_count": len(matches),
    "launch_origin_classification": launch_origin,
    "graceful_stop_method": stop_method,
    "exact_stop_status": exact_stop_status,
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": both_exact,
    "environment_secret_values_saved": False,
    "raw_environment_saved": False,
    "process_identity_contract_created": identity is not None,
    "pid_only_targeting_forbidden": True,
    "protected_sha_unchanged": True,
    "process_signal_sent": False,
    "writer_stop_performed": False,
    "gui_stopped_or_restarted": False,
    "production_database_opened": False,
    "sql_executed": False,
    "external_network_used": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(packet_root / "packet-semantic-validation.json", semantic_validation)

packet_files_before_manifest = sorted(
    path for path in packet_root.iterdir() if path.is_file()
)

packet_manifest_entries = [
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
    "status": "READONLY_ROUTE_RESOLUTION_PACKET_WRITER_FREEZE_NOT_APPROVED",
    "result": "PASS_3E_G_GUI_STOP_RESTART_ROUTE_PACKET_GENERATED",
    "packet_file_count_excluding_manifest": len(packet_manifest_entries),
    "packet_files": packet_manifest_entries,
    "process_state": process_state,
    "matching_process_count": len(matches),
    "graceful_stop_method": stop_method,
    "exact_stop_status": exact_stop_status,
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": both_exact,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_G_GUI_STOP_RESTART_ROUTE_PACKET",
}
write_json(packet_root / "packet-manifest.json", packet_manifest)

result = {
    "schema_version": "1.0",
    "phase": phase,
    "completed_at_utc": now_utc(),
    "result": "PASS_W2B_I2F3E_G_GUI_STOP_RESTART_ROUTE_RESOLUTION_READY",
    "evidence_root": evidence_rel,
    "input_f1_evidence_root": f1_rel,
    "process_state": process_state,
    "matching_process_count": len(matches),
    "current_pid": identity["pid"] if identity else None,
    "process_identity_sha256": identity_contract.get("identity_sha256"),
    "launch_origin_classification": launch_origin,
    "graceful_stop_method": stop_method,
    "exact_stop_status": exact_stop_status,
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": both_exact,
    "stdout_route_classification": stdio["stdout"]["classification"],
    "stderr_route_classification": stdio["stderr"]["classification"],
    "background_foreground_mode": background_mode,
    "pid_management_method": pid_management_method,
    "environment_secret_values_saved": False,
    "raw_environment_saved": False,
    "packet_file_count": len(packet_manifest_entries) + 1,
    "packet_manifest_sha256": sha256(packet_root / "packet-manifest.json"),
    "packet_semantic_validation_sha256": sha256(packet_root / "packet-semantic-validation.json"),
    "execution": route_resolution["execution"],
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_G_GUI_STOP_RESTART_ROUTE_PACKET",
}
write_json(evidence_root / "result.json", result)

# Final evidence manifest.
manifest_path = evidence_root / "evidence-manifest.txt"
manifest_lines: list[str] = []
for artifact in sorted(evidence_root.rglob("*"), key=lambda p: p.relative_to(evidence_root).as_posix()):
    if artifact.is_file() and artifact != manifest_path:
        manifest_lines.append(
            f"{sha256(artifact)}  {artifact.relative_to(evidence_root).as_posix()}"
        )
manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative_path = line.split("  ", 1)
    artifact = evidence_root / relative_path
    require(artifact.is_file(), f"EVIDENCE_MANIFEST_FILE_MISSING:{relative_path}")
    require(sha256(artifact) == expected, f"EVIDENCE_MANIFEST_SHA_MISMATCH:{relative_path}")

# Seal all new evidence. No sudo is used, so every artifact is deploy-owned.
files = sorted(path for path in evidence_root.rglob("*") if path.is_file())
directories = sorted(
    (path for path in evidence_root.rglob("*") if path.is_dir()),
    key=lambda p: len(p.relative_to(evidence_root).parts),
    reverse=True,
)

repo_uid = repo_root.stat().st_uid
repo_gid = repo_root.stat().st_gid

for artifact in [*files, *directories, evidence_root]:
    metadata = artifact.lstat()
    require(not stat.S_ISLNK(metadata.st_mode), f"EVIDENCE_SYMLINK_FORBIDDEN:{artifact}")
    require(metadata.st_uid == repo_uid, f"EVIDENCE_UID_INVALID:{artifact}:{metadata.st_uid}")
    require(metadata.st_gid == repo_gid, f"EVIDENCE_GID_INVALID:{artifact}:{metadata.st_gid}")

for artifact in files:
    os.chmod(artifact, 0o444)

for directory in directories:
    os.chmod(directory, 0o555)

os.chmod(evidence_root, 0o555)

for artifact in files:
    require(stat.S_IMODE(artifact.stat().st_mode) == 0o444, f"FILE_SEAL_FAILED:{artifact}")

for directory in [*directories, evidence_root]:
    require(stat.S_IMODE(directory.stat().st_mode) == 0o555, f"DIRECTORY_SEAL_FAILED:{directory}")

print(f"RESULT={result['result']}")
print(f"EVIDENCE_ROOT={evidence_rel}")
print(f"PROCESS_STATE={process_state}")
print(f"MATCHING_PROCESS_COUNT={len(matches)}")
print(f"CURRENT_GUI_PID={identity['pid'] if identity else 'NONE'}")
print(f"PROCESS_IDENTITY_SHA={identity_contract.get('identity_sha256', 'UNAVAILABLE')}")
print(f"LAUNCH_ORIGIN_CLASSIFICATION={launch_origin}")
print(f"GRACEFUL_STOP_METHOD={stop_method}")
print(f"EXACT_STOP_STATUS={exact_stop_status}")
print(f"EXACT_RESTART_STATUS={exact_restart_status}")
print(f"BOTH_EXACT_ROUTES_RESOLVED={'true' if both_exact else 'false'}")
print(f"STDIN_ROUTE_CLASSIFICATION={stdio['stdin']['classification']}")
print(f"STDOUT_ROUTE_CLASSIFICATION={stdio['stdout']['classification']}")
print(f"STDERR_ROUTE_CLASSIFICATION={stdio['stderr']['classification']}")
print(f"BACKGROUND_FOREGROUND_MODE={background_mode}")
print(f"PID_MANAGEMENT_METHOD={pid_management_method}")
print(f"REDACTED_SECRET_VARIABLE_COUNT={environment_info['redacted_secret_variable_count']}")
print("RAW_ENVIRONMENT_SAVED=false")
print("SECRET_ENVIRONMENT_VALUES_SAVED=false")
print(f"PACKET_FILE_COUNT={result['packet_file_count']}")
print(f"PACKET_MANIFEST_SHA={result['packet_manifest_sha256']}")
print(f"PACKET_SEMANTIC_VALIDATION_SHA={result['packet_semantic_validation_sha256']}")
print(f"RESULT_SHA={sha256(evidence_root / 'result.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(evidence_root / 'evidence-manifest.txt')}")
print("PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("SYSTEMD_CHANGED=false")
print("CRON_CHANGED=false")
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
print("NEXT_GATE=HUMAN_REVIEW_3E_G_GUI_STOP_RESTART_ROUTE_PACKET")
PY

trap - ERR
printf 'SCRIPT_EXIT_CODE=0\n'
