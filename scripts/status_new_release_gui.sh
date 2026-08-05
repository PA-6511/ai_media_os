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

pid=""
status="STOPPED"

if [[ -f "$PID_FILE" ]]; then
  candidate_pid="$(tr -d '[:space:]' < "$PID_FILE")"
  if process_matches "$candidate_pid"; then
    pid="$candidate_pid"
    status="RUNNING"
  fi
fi

echo "status=$status"
echo "pid=$pid"
echo "bind_host=$HOST"
echo "port=$PORT"
echo "gui_url=http://$HOST:$PORT/"