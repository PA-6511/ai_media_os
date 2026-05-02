#!/usr/bin/env bash
# ---------------------------------------------------------------
# scripts/run_sale_end_check.sh
#
# セール終了チェックを実行するラッパースクリプト。
# sale_end_date が過去になった sale_article を検出してログ・Slack 通知する。
# Google Sheets / OpenAI / WordPress への接続は不要。
#
# 使い方:
#   cd ~/ai_media_os
#   bash scripts/run_sale_end_check.sh [--dry-run]
#
# 環境変数 (任意):
#   SLACK_WEBHOOK_URL  - 通知先 Slack Webhook URL (未設定時は通知スキップ)
# ---------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/data/logs"
RUN_LOG="${LOG_DIR}/sale_end_check.log"

mkdir -p "${LOG_DIR}"

# --- .env 読み込み ---
ENV_FILE="${PROJECT_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi

_log() {
    local level="$1"
    shift
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') | ${level} | run_sale_end_check | $*" | tee -a "${RUN_LOG}"
}

_log INFO "start | pwd=${PROJECT_DIR}"

cd "${PROJECT_DIR}"

python3 scripts/sale_end_check.py "$@" 2>&1 | tee -a "${RUN_LOG}"
EXIT_CODE="${PIPESTATUS[0]}"

if [[ "${EXIT_CODE}" -eq 0 ]]; then
    _log INFO "done | no ended sales detected | exit_code=0"
elif [[ "${EXIT_CODE}" -eq 1 ]]; then
    _log WARNING "done | ended sales detected | exit_code=1"
else
    _log ERROR "done | unexpected exit_code=${EXIT_CODE}"
fi

exit "${EXIT_CODE}"
