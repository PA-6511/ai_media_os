#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/home/deploy/ai_media_os"
PY="$ROOT/.venv/bin/python"
CLI="$ROOT/scripts/run_ebook_autonomy_daily_cycle.py"

LOCK="$ROOT/exchange/state/ebook_autonomy_daily_cycle.lock"

cd "$ROOT"

mkdir -p \
    "$ROOT/exchange/state" \
    "$ROOT/exchange/evidence/ebook_autonomy/daily_cycle"

exec 9>"$LOCK"

if ! flock -n 9; then
    echo "EBOOK_AUTONOMY_SYSTEMD=SKIP_BUSY"
    echo "ACTION=SAFE_SKIP"
    exit 0
fi

echo
echo "======================================================"
echo " EBOOK AUTONOMY SYSTEMD DAILY CYCLE V1"
echo "======================================================"
echo "STARTED_AT=$(TZ=Asia/Tokyo date --iso-8601=seconds)"
echo

# DAILY_CYCLE_X_PROCESS_GATE_V2
export EBOOK_AUTONOMY_DAILY_X_ENABLED=0

set +e

"$PY" "$CLI" \
    --mode live \
    --components new_release,new_release_autofill,sale,campaign,enrichment

RC=$?

set -e

echo
echo "FINISHED_AT=$(TZ=Asia/Tokyo date --iso-8601=seconds)"
echo "DAILY_CYCLE_RC=$RC"

if [[ "$RC" -eq 0 ]]; then
    echo "EBOOK_AUTONOMY_SYSTEMD=PASS"
else
    echo "EBOOK_AUTONOMY_SYSTEMD=FAILED"
fi

exit "$RC"
