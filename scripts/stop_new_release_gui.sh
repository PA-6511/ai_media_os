#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$REPO_ROOT/run/new_release_gui.pid"
HOST="127.0.0.1"
PORT="8765"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    *)
      echo "unsupported_argument=$1" >&2
      exit 2
      ;;
  esac
done

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "invalid_port=$PORT" >&2
  exit 2
fi

process_matches() {
  local pid="$1"
  local command_line

  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1

  command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  [[ -n "$command_line" ]] || return 1
  [[ "$command_line" == *"scripts/new_release_multistore_app.py"* ]] || return 1
  [[ "$command_line" == *"--host $HOST"* ]] || return 1
  [[ "$command_line" == *"--port $PORT"* ]] || return 1

  return 0
}

wait_for_exit() {
  local pid="$1"

  python3 - "$pid" <<'PY'
import os
import signal
import sys
import time

pid = int(sys.argv[1])
deadline = time.monotonic() + 10.0

while time.monotonic() < deadline:
    try:
        os.kill(pid, 0)
    except OSError:
        raise SystemExit(0)
    time.sleep(0.25)

raise SystemExit(1)
PY
}

if [[ ! -f "$PID_FILE" ]]; then
  echo "status=STOPPED"
  echo "pid="
  echo "bind_host=$HOST"
  echo "port=$PORT"
  exit 0
fi

pid="$(tr -d '[:space:]' < "$PID_FILE")"

if ! process_matches "$pid"; then
  rm -f "$PID_FILE"
  echo "status=STOPPED"
  echo "pid="
  echo "bind_host=$HOST"
  echo "port=$PORT"
  exit 0
fi

kill "$pid"

if ! wait_for_exit "$pid"; then
  kill -KILL "$pid" 2>/dev/null || true
fi

rm -f "$PID_FILE"

echo "status=STOPPED"
echo "pid=$pid"
echo "bind_host=$HOST"
echo "port=$PORT"