#!/usr/bin/env bash
# ---------------------------------------------------------------
# gui/run_mock_server_bg.sh
#
# バックグラウンドで mock server を起動し、
# PID / ログ / runtime JSON を所定パスに保存する。
#
# 使い方:
#   cd ~/ai_media_os
#   bash gui/run_mock_server_bg.sh [--port PORT]
# ---------------------------------------------------------------
set -euo pipefail

# --- パス定数 ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="${PROJECT_DIR}/data/logs/mock_server.out"
PID_FILE="${PROJECT_DIR}/data/run/mock_server.pid"
RUNTIME_JSON="${PROJECT_DIR}/data/reports/mock_server_runtime_latest.json"

# --- 引数 ---
PORT_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            PORT_ARG="--port $2"
            shift 2
            ;;
        *)
            echo "[bg] unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# --- ディレクトリ準備 ---
mkdir -p "${PROJECT_DIR}/data/logs" \
         "${PROJECT_DIR}/data/run" \
         "${PROJECT_DIR}/data/reports"

# --- 既存プロセスの確認 ---
if [[ -f "${PID_FILE}" ]]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "[bg] mock server already running: pid=${OLD_PID}"
        echo "[bg] stop it first with:  bash gui/stop_mock_server.sh"
        exit 1
    else
        echo "[bg] stale PID file removed (pid=${OLD_PID} not running)"
        rm -f "${PID_FILE}"
    fi
fi

# --- バックグラウンド起動 ---
echo "[bg] starting mock server ..."
echo "[bg] log  : ${LOG_FILE}"
echo "[bg] pid  : ${PID_FILE}"

# nohup で起動し、stdout/stderr をログファイルへ
nohup python3 -m gui.run_mock_server ${PORT_ARG} \
    > "${LOG_FILE}" 2>&1 &

SERVER_PID=$!
echo "${SERVER_PID}" > "${PID_FILE}"
echo "[bg] pid=${SERVER_PID} saved to ${PID_FILE}"

# --- READY バナーが出るまで待機 (最大 10 秒) ---
echo "[bg] waiting for MOCK SERVER READY ..."
READY=0
for i in $(seq 1 20); do
    sleep 0.5
    if grep -q "MOCK SERVER READY" "${LOG_FILE}" 2>/dev/null; then
        READY=1
        break
    fi
    # プロセスが死んでいたら即終了
    if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
        echo "[bg] ERROR: server process exited unexpectedly"
        echo "[bg] --- log tail ---"
        tail -20 "${LOG_FILE}" || true
        rm -f "${PID_FILE}"
        exit 1
    fi
done

if [[ $READY -eq 0 ]]; then
    echo "[bg] WARNING: READY banner not seen within 10s. Log tail:"
    tail -20 "${LOG_FILE}" || true
fi

# --- 確定ポートを runtime JSON から表示 ---
if [[ -f "${RUNTIME_JSON}" ]]; then
    FINAL_PORT=$(python3 -c \
        "import json; print(json.load(open('${RUNTIME_JSON}'))['final_port'])" \
        2>/dev/null || echo "unknown")
    SERVER_URL=$(python3 -c \
        "import json; print(json.load(open('${RUNTIME_JSON}'))['server_url'])" \
        2>/dev/null || echo "unknown")
    echo ""
    echo "============================================================"
    echo "  MOCK SERVER BACKGROUND"
    echo "  pid         : ${SERVER_PID}"
    echo "  final_port  : ${FINAL_PORT}"
    echo "  server_url  : ${SERVER_URL}/"
    echo "  log         : ${LOG_FILE}"
    echo "  pid_file    : ${PID_FILE}"
    echo "  runtime_json: ${RUNTIME_JSON}"
    echo ""
    echo "  confirm:  curl ${SERVER_URL}/health"
    echo "  stop:     bash gui/stop_mock_server.sh"
    echo "============================================================"
    echo ""
else
    echo "[bg] server started (pid=${SERVER_PID})"
    echo "[bg] runtime JSON not yet found — check log: ${LOG_FILE}"
fi
