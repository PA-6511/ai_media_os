#!/usr/bin/env bash
# ---------------------------------------------------------------
# scripts/run_ai_post_queue.sh
#
# AI 投稿キューを実行するラッパースクリプト。
# Google Sheets から投稿キューを読み込み、OpenAI で記事生成後、
# WordPress へ投稿する。
#
# 使い方:
#   cd ~/ai_media_os
#   bash scripts/run_ai_post_queue.sh [--max-items N] [--dry-run]
#
# 環境変数 (事前に .env に設定):
#   SPREADSHEET_ID            必須 - 投稿キュー Google Spreadsheet ID
#   GOOGLE_SERVICE_ACCOUNT_JSON 必須 - サービスアカウント JSON (base64 or path)
#   OPENAI_API_KEY            必須 - OpenAI API キー
#   SLACK_WEBHOOK_URL         推奨 - 通知先 Slack Webhook URL
#   WP_BASE_URL               必須 - WordPress サイト URL
#   WP_USERNAME               必須 - WordPress ユーザー名
#   WP_APP_PASSWORD           必須 - WordPress アプリパスワード
#
# 互換 alias:
#   WP_USER           -> WP_USERNAME
#   DRY_RUN           -> WP_DRY_RUN
#   MAX_ROWS_PER_RUN  -> SCHEDULER_MAX_ITEMS / MAX_ITEMS
# ---------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/data/logs"
RUN_LOG="${LOG_DIR}/run_ai_post_queue.log"

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
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') | ${level} | run_ai_post_queue | $*" | tee -a "${RUN_LOG}"
}

_log INFO "start | pwd=${PROJECT_DIR}"

# --- 環境変数 alias を吸収 ---
if [[ -n "${WP_USER:-}" && -z "${WP_USERNAME:-}" ]]; then
    export WP_USERNAME="${WP_USER}"
fi

if [[ -n "${DRY_RUN:-}" && -z "${WP_DRY_RUN:-}" ]]; then
    export WP_DRY_RUN="${DRY_RUN}"
fi

# scheduler 側の dry_run 既定値に上書きされないよう、
# WP_DRY_RUN 指定時は SCHEDULER_DRY_RUN にも同値を渡す。
if [[ -n "${WP_DRY_RUN:-}" && -z "${SCHEDULER_DRY_RUN:-}" ]]; then
    export SCHEDULER_DRY_RUN="${WP_DRY_RUN}"
fi

if [[ -n "${MAX_ROWS_PER_RUN:-}" ]]; then
    if [[ -z "${SCHEDULER_MAX_ITEMS:-}" ]]; then
        export SCHEDULER_MAX_ITEMS="${MAX_ROWS_PER_RUN}"
    fi
    if [[ -z "${MAX_ITEMS:-}" ]]; then
        export MAX_ITEMS="${MAX_ROWS_PER_RUN}"
    fi
fi

# --- 必須環境変数チェック ---
MISSING_VARS=()
for var in SPREADSHEET_ID GOOGLE_SERVICE_ACCOUNT_JSON OPENAI_API_KEY WP_BASE_URL WP_USERNAME WP_APP_PASSWORD; do
    if [[ -z "${!var:-}" ]]; then
        MISSING_VARS+=("${var}")
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    _log ERROR "missing required env vars: ${MISSING_VARS[*]}"
    _log ERROR "set them in ${ENV_FILE} before running"
    exit 1
fi

# --- 引数を Python スクリプトへ転送 ---
cd "${PROJECT_DIR}"

_log INFO "running python scheduler (run_once)"

python3 -m scheduler.job_runner "$@" 2>&1 | tee -a "${RUN_LOG}"
EXIT_CODE="${PIPESTATUS[0]}"

_log INFO "done | exit_code=${EXIT_CODE}"
exit "${EXIT_CODE}"
