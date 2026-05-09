#!/usr/bin/env python3
"""Phase2 Unlock Applier.

max_items=1 → max_items=2 への安全な昇格実装。
必ず consecutive_ok_days >= 3 かつ human approval（--yes フラグ）が必要。

使い方:
    python3 tools/apply_phase2_unlock.py --unlock max_items_2 --yes

この2つの引数が両方ないと STOP する。

主な動き:
  1. CLI 引数チェック（--unlock と --yes が両方必須）
  2. 6つの検証チェック（いずれか失敗したら STOP）
  3. cron バックアップ作成
  4. cron 変更（max-items 1 → 2）
  5. health check 実行
  6. NG なら自動ロールバック
  7. Slack 通知
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

# ============================================================================
# CONSTANTS
# ============================================================================

STATE_FILE = BASE_DIR / "data" / "logs" / "phase2_observation_state.json"
PHASE2_HEALTH_CHECK = BASE_DIR / "tools" / "phase2_health_check.py"
BACKUP_DIR = BASE_DIR / "data" / "backups"
CRONTAB_BACKUP = BACKUP_DIR / "crontab_before_max_items_2.txt"

# Expected cron patterns
CURRENT_CRON_PATTERN = "--max-items 1"
NEW_CRON_PATTERN = "--max-items 2"

# ============================================================================
# VALIDATION CHECKS
# ============================================================================


def _check_state_file() -> tuple[bool, dict[str, Any]]:
    """Check 1: State file exists and is readable."""
    if not STATE_FILE.exists():
        return False, {"error": "state file not found", "path": str(STATE_FILE)}
    
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return True, state
    except Exception as exc:  # noqa: BLE001
        return False, {"error": f"failed to read state: {exc}"}


def _check_consecutive_ok_days(state: dict[str, Any]) -> tuple[bool, int]:
    """Check 2: consecutive_ok_days >= 3."""
    consecutive = state.get("consecutive_ok_days", 0)
    if consecutive >= 3:
        return True, consecutive
    return False, consecutive


def _run_phase2_health_check() -> tuple[bool, str]:
    """Check 3: Phase2 health is OK.
    
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


def _check_no_error_rows() -> tuple[bool, str]:
    """Check 4: No ERROR rows in Sheets."""
    try:
        from src.sheets import fetch_all_rows, get_sheet
        sheet = get_sheet()
        rows = fetch_all_rows(sheet)
    except Exception:  # noqa: BLE001
        return False, "failed to fetch sheets"
    
    error_rows = [r for r in rows if r.get("status") == "ERROR"]
    if error_rows:
        return False, f"ERROR rows found: {len(error_rows)}"
    
    return True, "OK"


def _check_current_cron() -> tuple[bool, str]:
    """Check 5: Current cron has --max-items 1."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        crontab_content = result.stdout
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to read crontab: {exc}"
    
    # Find ai_media_os posting cron
    for line in crontab_content.split("\n"):
        if "ai_media_os" in line and "run_ai_post_queue.sh" in line:
            if CURRENT_CRON_PATTERN in line:
                return True, line.strip()
            else:
                return False, f"cron pattern mismatch: {line.strip()}"
    
    return False, "posting cron not found"


def _check_no_auto_publish() -> tuple[bool, str]:
    """Check 6: No auto-publish configuration.
    
    Check that WordPress auto-publish is not enabled.
    """
    # Check if WP_AUTO_PUBLISH env var is set
    if os.getenv("WP_AUTO_PUBLISH", "").lower() in ["true", "1", "yes"]:
        return False, "WP_AUTO_PUBLISH is enabled"
    
    # Check if cron has publish-related args
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        crontab_content = result.stdout
    except Exception:  # noqa: BLE001
        return False, "failed to read crontab"
    
    for line in crontab_content.split("\n"):
        if "ai_media_os" in line and "run_ai_post_queue.sh" in line:
            if "--publish" in line or "--live" in line or "WP_PUBLISH=1" in line:
                return False, "auto-publish flag found in cron"
    
    return True, "OK (draft only)"


# ============================================================================
# MAIN OPERATIONS
# ============================================================================


def _backup_crontab() -> tuple[bool, str]:
    """Backup current crontab."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        crontab_content = result.stdout
        CRONTAB_BACKUP.write_text(crontab_content, encoding="utf-8")
        return True, str(CRONTAB_BACKUP)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _apply_cron_change() -> tuple[bool, str]:
    """Apply cron change: --max-items 1 -> 2."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        crontab_content = result.stdout
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to read crontab: {exc}"
    
    # Replace the pattern
    if CURRENT_CRON_PATTERN not in crontab_content:
        return False, f"pattern '{CURRENT_CRON_PATTERN}' not found in crontab"
    
    new_content = crontab_content.replace(CURRENT_CRON_PATTERN, NEW_CRON_PATTERN)
    
    # Apply new crontab
    try:
        proc = subprocess.run(
            ["crontab", "-"],
            input=new_content,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return False, f"crontab update failed: {proc.stderr}"
        return True, "cron applied: max_items 1 -> 2"
    except Exception as exc:  # noqa: BLE001
        return False, f"crontab update error: {exc}"


def _restore_crontab() -> tuple[bool, str]:
    """Restore crontab from backup."""
    if not CRONTAB_BACKUP.exists():
        return False, "backup file not found"
    
    try:
        backup_content = CRONTAB_BACKUP.read_text(encoding="utf-8")
        proc = subprocess.run(
            ["crontab", "-"],
            input=backup_content,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return False, f"crontab restore failed: {proc.stderr}"
        return True, "cron restored from backup"
    except Exception as exc:  # noqa: BLE001
        return False, f"crontab restore error: {exc}"


def _format_unlock_message(
    consecutive_ok_days: int,
    current_cron: str,
) -> str:
    """Format success message for Slack."""
    lines = [
        "[ai_media_os] Phase2 Unlock Applied",
        "",
        "unlock:",
        "  max_items: 1 -> 2",
        "",
        "mode:",
        "  draft only",
        "  auto publish: disabled",
        "",
        "post_check:",
        "  phase2_health: OK",
        "",
        f"observation_days: {consecutive_ok_days}/3",
        "",
        "next_phase:",
        "  observe for 3 more days",
        "",
        "Human-approved unlock completed.",
    ]
    return "\n".join(lines)


def _format_rollback_message(reason: str) -> str:
    """Format rollback message for Slack."""
    lines = [
        "[ai_media_os] Phase2 Unlock Rollback",
        "",
        f"reason:",
        f"  {reason}",
        "",
        "action:",
        "  cron restored to max_items=1",
        "",
        "Human review required.",
    ]
    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================


def main(argv: list[str] | None = None) -> int:
    """Main unlock runner."""
    parser = argparse.ArgumentParser(description="Phase2 Unlock Applier")
    parser.add_argument(
        "--unlock",
        choices=["max_items_2"],
        required=True,
        help="Unlock action (required)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        required=True,
        help="Human approval confirmation (required)",
    )
    args = parser.parse_args(argv)

    print("=" * 68)
    print("Phase2 Unlock Applier")
    print("=" * 68)
    print(f"unlock: {args.unlock}")
    print(f"human_approval: {args.yes}")
    print("")

    # ========================================================================
    # VALIDATION CHECKS
    # ========================================================================
    print("VALIDATION CHECKS")
    print("-" * 68)

    # Check 1: State file
    print("1. Checking state file...")
    state_ok, state_data = _check_state_file()
    if not state_ok:
        print(f"   ✗ STOP: {state_data.get('error')}")
        return 1
    print(f"   ✓ OK: {STATE_FILE}")
    print(f"     consecutive_ok_days: {state_data.get('consecutive_ok_days')}")

    # Check 2: consecutive_ok_days >= 3
    print("2. Checking consecutive_ok_days >= 3...")
    consecutive_ok, consecutive_days = _check_consecutive_ok_days(state_data)
    if not consecutive_ok:
        print(f"   ✗ STOP: {consecutive_days}/3 (not yet 3 days)")
        return 1
    print(f"   ✓ OK: {consecutive_days}/3")

    # Check 3: Phase2 health
    print("3. Running Phase2 health check...")
    health_ok, health_output = _run_phase2_health_check()
    if not health_ok:
        print(f"   ✗ STOP: health check failed")
        print(f"     {health_output[:100]}")
        return 1
    print(f"   ✓ OK: phase2_health passed")

    # Check 4: No ERROR rows
    print("4. Checking for ERROR rows...")
    no_errors_ok, error_msg = _check_no_error_rows()
    if not no_errors_ok:
        print(f"   ✗ STOP: {error_msg}")
        return 1
    print(f"   ✓ OK: no ERROR rows")

    # Check 5: Current cron pattern
    print("5. Checking current cron pattern...")
    cron_ok, cron_line = _check_current_cron()
    if not cron_ok:
        print(f"   ✗ STOP: {cron_line}")
        return 1
    print(f"   ✓ OK: cron has --max-items 1")
    print(f"     {cron_line[:80]}")

    # Check 6: No auto-publish
    print("6. Checking for auto-publish configuration...")
    no_auto_ok, auto_msg = _check_no_auto_publish()
    if not no_auto_ok:
        print(f"   ✗ STOP: {auto_msg}")
        return 1
    print(f"   ✓ OK: {auto_msg}")

    print("")

    # ========================================================================
    # BACKUP
    # ========================================================================
    print("CRONTAB BACKUP")
    print("-" * 68)
    backup_ok, backup_path = _backup_crontab()
    if not backup_ok:
        print(f"✗ STOP: backup failed: {backup_path}")
        return 1
    print(f"✓ backup created: {backup_path}")
    print("")

    # ========================================================================
    # APPLY CHANGE
    # ========================================================================
    print("CRON CHANGE")
    print("-" * 68)
    change_ok, change_msg = _apply_cron_change()
    if not change_ok:
        print(f"✗ STOP: {change_msg}")
        return 1
    print(f"✓ {change_msg}")
    print("")

    # ========================================================================
    # POST-CHECK: HEALTH
    # ========================================================================
    print("POST-CHECK: Phase2 Health")
    print("-" * 68)
    health_ok_post, health_output_post = _run_phase2_health_check()
    if not health_ok_post:
        print(f"✗ NG: health check failed after unlock")
        print(f"     {health_output_post[:100]}")
        print("")
        print("ROLLBACK: Restoring cron...")
        rollback_ok, rollback_msg = _restore_crontab()
        if rollback_ok:
            print(f"✓ {rollback_msg}")
            # Send rollback notification
            rollback_slack = _format_rollback_message("phase2_health NG after unlock")
            send_slack_message(rollback_slack)
        else:
            print(f"✗ CRITICAL: rollback failed! {rollback_msg}")
            print("   Manual intervention required!")
            return 1
        return 1

    print(f"✓ phase2_health: OK")
    print("")

    # ========================================================================
    # SUCCESS: SLACK NOTIFICATION
    # ========================================================================
    print("SLACK NOTIFICATION")
    print("-" * 68)
    unlock_msg = _format_unlock_message(consecutive_days, cron_line)
    print(unlock_msg)
    print("")
    slack_ok = send_slack_message(unlock_msg)
    if slack_ok:
        print("✓ Slack notification sent")
    else:
        print("✗ Slack notification failed (but unlock was applied)")

    print("")
    print("=" * 68)
    print("Summary")
    print("=" * 68)
    print(f"status: SUCCESS")
    print(f"consecutive_ok_days: {consecutive_days}/3")
    print(f"cron_change: max_items 1 -> 2")
    print(f"backup: {backup_path}")
    print(f"health_check: OK")
    print(f"slack_notify: {'OK' if slack_ok else 'FAILED'}")
    print(f"next_action: observe for 3 more days")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
