#!/usr/bin/env bash
# ---------------------------------------------------------------
# gui/stop_mock_server.sh
#
# run_mock_server_bg.sh で起動したサーバーを安全に停止する。
#
# 使い方:
#   cd ~/ai_media_os
#   bash gui/stop_mock_server.sh
# ---------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PID_FILE="${PROJECT_DIR}/data/run/mock_server.pid"
RUNTIME_JSON="${PROJECT_DIR}/data/reports/mock_server_runtime_latest.json"

if [[ ! -f "${PID_FILE}" ]]; then
    echo "[stop] no PID file found: ${PID_FILE}"
    echo "[stop] server may not be running (or was started manually)"
    # フォールバック: ポートで検索して終了
    PIDS=$(ss -ltnp 2>/dev/null \
        | grep -oP '(?<=pid=)\d+' \
        | sort -u || true)
    if [[ -z "${PIDS}" ]]; then
        echo "[stop] no mock server processes found via ss"
    fi
    exit 0
fi

PID=$(cat "${PID_FILE}")

if ! kill -0 "${PID}" 2>/dev/null; then
    echo "[stop] process ${PID} is not running (already stopped?)"
    rm -f "${PID_FILE}"
    rm -f "${RUNTIME_JSON}"
    echo "[stop] stale files removed"
    exit 0
fi

echo "[stop] sending SIGTERM to pid=${PID} ..."
kill -TERM "${PID}" 2>/dev/null || true

# --- SIGTERM 後 3 秒待つ ---
for i in $(seq 1 6); do
    sleep 0.5
    if ! kill -0 "${PID}" 2>/dev/null; then
        echo "[stop] process ${PID} stopped via SIGTERM (${i} × 0.5s)"
        break
    fi
done

# nohup 環境では SIGTERM→SIGINT 変換が遅れることがある → SIGINT を直接送る
if kill -0 "${PID}" 2>/dev/null; then
    echo "[stop] still alive — sending SIGINT (KeyboardInterrupt) ..."
    kill -INT "${PID}" 2>/dev/null || true
    for i in $(seq 1 6); do
        sleep 0.5
        if ! kill -0 "${PID}" 2>/dev/null; then
            echo "[stop] process ${PID} stopped via SIGINT (${i} × 0.5s)"
            break
        fi
    done
fi

# まだ生きていれば SIGKILL
if kill -0 "${PID}" 2>/dev/null; then
    echo "[stop] still alive — sending SIGKILL (force)"
    kill -9 "${PID}" 2>/dev/null || true
    sleep 0.5
fi

# クリーンアップ
rm -f "${PID_FILE}"
rm -f "${RUNTIME_JSON}"

echo "[stop] done"
