#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
GUI_SCRIPT="$REPO_ROOT/scripts/new_release_multistore_app.py"
RUN_DIR="$REPO_ROOT/run"
LOG_DIR="$REPO_ROOT/logs"
PID_FILE="$RUN_DIR/new_release_gui.pid"
LOG_FILE="$LOG_DIR/new_release_gui.log"
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

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "missing_python=$PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -f "$GUI_SCRIPT" ]]; then
  echo "missing_gui_script=$GUI_SCRIPT" >&2
  exit 1
fi

mkdir -p "$RUN_DIR" "$LOG_DIR"

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

discover_existing_pid() {
  local pid

  while IFS= read -r pid; do
    if process_matches "$pid"; then
      printf '%s\n' "$pid"
      return 0
    fi
  done < <(pgrep -f "scripts/new_release_multistore_app.py" || true)

  return 1
}

print_running() {
  local pid="$1"
  echo "status=RUNNING"
  echo "pid=$pid"
  echo "bind_host=$HOST"
  echo "port=$PORT"
}

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(tr -d '[:space:]' < "$PID_FILE")"
  if process_matches "$existing_pid"; then
    print_running "$existing_pid"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if existing_pid="$(discover_existing_pid)"; then
  printf '%s\n' "$existing_pid" > "$PID_FILE"
  print_running "$existing_pid"
  exit 0
fi

nohup "$PYTHON_BIN" "$GUI_SCRIPT" \
  --repo-root "$REPO_ROOT" \
  --host "$HOST" \
  --port "$PORT" \
  >> "$LOG_FILE" 2>&1 &
new_pid="$!"
printf '%s\n' "$new_pid" > "$PID_FILE"

if "$PYTHON_BIN" - "$HOST" "$PORT" <<'PY'
import socket
import sys
import time
from urllib import request

host = sys.argv[1]
port = int(sys.argv[2])
deadline = time.monotonic() + 10.0
url = f"http://{host}:{port}/"

while time.monotonic() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            pass
        with request.urlopen(url, timeout=1.0) as response:
            if 200 <= response.status < 500:
                raise SystemExit(0)
    except Exception:
        time.sleep(0.25)

raise SystemExit(1)
PY
then
  print_running "$new_pid"
  exit 0
fi

kill "$new_pid" 2>/dev/null || true
rm -f "$PID_FILE"

echo "status=FAILED" >&2
echo "log_tail_start" >&2
tail -n 20 "$LOG_FILE" >&2 || true
echo "log_tail_end" >&2
exit 1