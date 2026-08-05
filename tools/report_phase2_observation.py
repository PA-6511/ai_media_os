#!/usr/bin/env python3
"""Phase2 Observation Reporter.

自動化した Phase2 観測スクリプト。毎日 09:00 に実行。

機能:
  1. ai_post_queue_cron.log を確認（異常終了の有無）
  2. Google Sheets「投稿キュー」を確認（当日 DRAFTED 行）
  3. Phase2 health check を実行
  4. 日次判定（OK/NG）を決定
  5. data/logs/phase2_observation_state.json に連続OK日数を保存
  6. Slack へ結果を通知

Usage:
    python3 tools/report_phase2_observation.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from monitoring.slack_notifier import send_slack_message
from src.sheets import fetch_all_rows, get_sheet

# ============================================================================
# CONSTANTS
# ============================================================================

LOG_CRON = BASE_DIR / "logs" / "ai_post_queue_cron.log"
STATE_FILE = BASE_DIR / "data" / "logs" / "phase2_observation_state.json"
PHASE2_HEALTH_CHECK = BASE_DIR / "tools" / "phase2_health_check.py"

TODAY = datetime.now(timezone.utc).astimezone().date()
TODAY_STR = TODAY.isoformat()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _load_state() -> dict[str, Any]:
    """Load current observation state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"consecutive_ok_days": 0, "last_ok_date": None}


def _save_state(state: dict[str, Any]) -> None:
    """Save observation state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _check_cron_log() -> tuple[bool, str]:
    """Check ai_post_queue_cron.log for errors.
    
    Returns:
        (is_ok, details)
    """
    if not LOG_CRON.exists():
        return False, "cron log not found"

    try:
        content = LOG_CRON.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to read cron log: {exc}"

    # Check for error patterns in the entire log for today
    error_keywords = ["traceback", "error", "exception", "failed"]
    
    # Get all lines
    lines = content.split("\n")
    
    # Find today's logs (lines containing today's date)
    today_logs = []
    for line in lines:
        if TODAY_STR in line:
            today_logs.append(line)
    
    if not today_logs:
        return False, "no logs for today found"
    
    # Check for errors in today's logs
    for line in today_logs:
        lower = line.lower()
        for keyword in error_keywords:
            if keyword in lower:
                return False, f"error keyword found: {keyword}"
    
    return True, "OK"


def _check_sheets_drafted_row() -> tuple[bool, dict[str, Any]]:
    """Check Google Sheets for DRAFTED row.
    
    Returns:
        (is_ok, row_data)
    """
    try:
        sheet = get_sheet()
        rows = fetch_all_rows(sheet)
    except Exception as exc:  # noqa: BLE001
        return False, {"error": str(exc)}

    if not rows:
        return False, {"error": "no rows found"}

    # Find latest DRAFTED row (prefer today's, fallback to latest)
    drafted_rows = [r for r in rows if r.get("status") == "DRAFTED"]
    if not drafted_rows:
        return False, {"error": "no DRAFTED rows found"}

    # Use the most recent DRAFTED row
    latest_row = drafted_rows[0]

    # Check required fields
    wp_post_id = latest_row.get("wp_post_id", "").strip()
    wp_draft_url = latest_row.get("wp_draft_url", "").strip()

    if not wp_post_id:
        return False, {
            "error": "wp_post_id is empty",
            "row_id": latest_row.get("row_id"),
        }

    if not wp_draft_url:
        return False, {
            "error": "wp_draft_url is empty",
            "row_id": latest_row.get("row_id"),
        }

    return True, latest_row


def _check_error_rows() -> tuple[bool, str]:
    """Check if ERROR rows exist.
    
    Returns:
        (no_errors, details)
    """
    try:
        sheet = get_sheet()
        rows = fetch_all_rows(sheet)
    except Exception:  # noqa: BLE001
        return False, "failed to fetch rows"

    error_rows = [r for r in rows if r.get("status") == "ERROR"]
    if error_rows:
        return False, f"ERROR rows found: {len(error_rows)}"

    return True, "OK"


def _run_phase2_health_check() -> tuple[bool, str]:
    """Run phase2_health_check.py.
    
    Returns:
        (is_ok, output)
    """
    try:
        result = subprocess.run(
            [sys.executable, str(PHASE2_HEALTH_CHECK), "--strict-log"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        is_ok = result.returncode == 0
        return is_ok, output
    except subprocess.TimeoutExpired:
        return False, "health check timeout"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _determine_daily_result(
    cron_ok: bool,
    sheets_ok: bool,
    no_errors_ok: bool,
    health_ok: bool,
) -> str:
    """Determine daily_result: OK or NG."""
    if cron_ok and sheets_ok and no_errors_ok and health_ok:
        return "OK"
    return "NG"


def _update_consecutive_ok_days(state: dict[str, Any], daily_result: str) -> int:
    """Update and return consecutive_ok_days."""
    if daily_result == "OK":
        last_ok = state.get("last_ok_date")
        if last_ok == TODAY_STR:
            # Already counted today
            return state.get("consecutive_ok_days", 0)
        # Increment for new day
        consecutive = state.get("consecutive_ok_days", 0) + 1
        state["last_ok_date"] = TODAY_STR
        state["consecutive_ok_days"] = consecutive
        return consecutive
    else:
        # Reset on NG
        state["consecutive_ok_days"] = 0
        state["last_ok_date"] = None
        return 0


def _format_slack_message(
    daily_result: str,
    consecutive_ok_days: int,
    checks: dict[str, str],
    latest_row: dict[str, Any],
) -> str:
    """Format Slack notification message."""
    lines = [
        "[ai_media_os] Phase2 Observation Report",
        "",
        f"date: {TODAY_STR}",
        f"daily_result: {daily_result}",
        f"consecutive_ok_days: {consecutive_ok_days}/3",
        "",
        "checks:",
    ]

    for check_name, check_status in checks.items():
        lines.append(f"  {check_name}: {check_status}")

    if latest_row:
        lines.extend([
            "",
            "latest_row:",
            f"  row_id: {latest_row.get('row_id', 'N/A')}",
            f"  status: {latest_row.get('status', 'N/A')}",
            f"  wp_post_id: {latest_row.get('wp_post_id', 'N/A')}",
            f"  wp_draft_url: {latest_row.get('wp_draft_url', 'N/A')[:50]}...",
        ])

    lines.append("")
    lines.append("next_action:")
    if daily_result == "NG":
        lines.append("  NG: 停止して原因確認")
    elif consecutive_ok_days < 3:
        lines.append(f"  OK {consecutive_ok_days}/3: 観測継続")
    else:
        lines.extend([
            "  OK 3/3: 解禁候補を人間確認",
            "",
            "Unlock candidate:",
            "  1. max_items=2",
            "  2. 半自動公開フロー検討",
            "",
            "Human approval required.",
        ])

    return "\n".join(lines)


def main(argv: list[str] | None = None, *, dry_run: bool = False) -> int:
    """Main observation runner."""
    parser = argparse.ArgumentParser(description="Phase2 Observation Reporter")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode (no Slack notification, no state save)",
    )
    args = parser.parse_args(argv)
    dry_run = args.dry_run or dry_run

    print("=" * 68)
    print("Phase2 Observation Report")
    print("=" * 68)
    print(f"date: {TODAY_STR}")
    print(f"dry_run: {dry_run}")
    print("")

    # ========================================================================
    # 1. Check cron log
    # ========================================================================
    print("1. Checking cron log...")
    cron_ok, cron_msg = _check_cron_log()
    print(f"   cron_log: {cron_ok} ({cron_msg})")

    # ========================================================================
    # 2. Check Sheets DRAFTED row
    # ========================================================================
    print("2. Checking Google Sheets DRAFTED row...")
    sheets_ok, latest_row = _check_sheets_drafted_row()
    if sheets_ok:
        print(f"   sheets_drafted: OK")
        print(f"     row_id: {latest_row.get('row_id')}")
        print(f"     wp_post_id: {latest_row.get('wp_post_id')}")
    else:
        print(f"   sheets_drafted: NG ({latest_row.get('error', 'unknown error')})")
        latest_row = {}

    # ========================================================================
    # 3. Check ERROR rows
    # ========================================================================
    print("3. Checking ERROR rows...")
    no_errors_ok, error_msg = _check_error_rows()
    print(f"   no_error_rows: {no_errors_ok} ({error_msg})")

    # ========================================================================
    # 4. Run Phase2 health check
    # ========================================================================
    print("4. Running Phase2 health check...")
    health_ok, health_output = _run_phase2_health_check()
    health_summary = health_output.split("\n")[-2] if health_output.split("\n") else "unknown"
    print(f"   phase2_health: {health_ok} ({health_summary})")

    # ========================================================================
    # 5. Determine daily result
    # ========================================================================
    daily_result = _determine_daily_result(cron_ok, sheets_ok, no_errors_ok, health_ok)
    print("")
    print(f"daily_result: {daily_result}")

    # ========================================================================
    # 6. Update state
    # ========================================================================
    state = _load_state()
    consecutive_ok_days = _update_consecutive_ok_days(state, daily_result)
    print(f"consecutive_ok_days: {consecutive_ok_days}/3")

    if not dry_run:
        _save_state(state)
        print(f"state saved: {STATE_FILE}")

    # ========================================================================
    # 7. Slack notification
    # ========================================================================
    checks = {
        "cron_log": "OK" if cron_ok else "NG",
        "sheets_drafted": "OK" if sheets_ok else "NG",
        "no_error_rows": "OK" if no_errors_ok else "NG",
        "phase2_health": "OK" if health_ok else "NG",
    }

    slack_message = _format_slack_message(
        daily_result,
        consecutive_ok_days,
        checks,
        latest_row,
    )

    print("")
    print("Slack notification:")
    print(slack_message)
    print("")

    if not dry_run:
        slack_ok = send_slack_message(slack_message)
        print(f"slack_notify: {'OK' if slack_ok else 'NG'}")
    else:
        print("[DRY-RUN] Slack notification skipped")

    # ========================================================================
    # Summary
    # ========================================================================
    print("")
    print("=" * 68)
    print("Summary")
    print("=" * 68)
    print(f"date: {TODAY_STR}")
    print(f"daily_result: {daily_result}")
    print(f"consecutive_ok_days: {consecutive_ok_days}/3")
    print(f"state_file: {STATE_FILE}")
    print(f"dry_run: {dry_run}")
    print("")

    return 0 if daily_result == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
