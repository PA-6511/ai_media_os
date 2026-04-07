from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.ops_settings_loader import get_ops_setting
from ops.ops_summary_notifier import notify_ops_summary


BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "data" / "logs"
OPS_LOG_PATH = LOG_DIR / "ops_cycle.log"


BASE_STEP_ORDER = [
    "scheduler",
    "smoke_test",
    "anomaly_check",
    "daily_report",
    "dashboard_build",
    "archive_backup",
    "log_rotate",
    "release_readiness_check",
    "ops_home_build",
    "ops_summary_build",
    "ops_api_payload_build",
    "ops_status_light_build",
    "ops_manifest_build",
    "ops_home_payload_build",
    "ops_sidebar_build",
    "ops_tabs_build",
    "ops_header_build",
    "ops_widgets_build",
    "ops_layout_build",
    "ops_gui_schema_build",
    "ops_bootstrap_build",
    "ops_gui_preview_build",
    "mock_api_build",
]

GUI_STEP_NAMES = {
    "ops_sidebar_build",
    "ops_tabs_build",
    "ops_widgets_build",
    "ops_layout_build",
    "ops_header_build",
    "ops_gui_schema_build",
    "ops_gui_preview_build",
    "mock_api_build",
    "ops_bootstrap_build",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate_text(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}\n... (truncated {omitted} chars)"


def should_run_monthly_report(settings: dict[str, Any], now: datetime | None = None) -> bool:
    """月初または設定ON時に月次レポートを実行する。"""
    current = now or datetime.now(timezone.utc)
    return bool(settings.get("run_monthly_report", False)) or current.day == 1


def should_run_monthly_dashboard(
    settings: dict[str, Any],
    now: datetime | None = None,
    monthly_report_selected: bool = False,
) -> bool:
    """月次ダッシュボードを実行するか判定する。"""
    current = now or datetime.now(timezone.utc)
    return (
        bool(settings.get("run_monthly_dashboard", False))
        or monthly_report_selected
        or current.day == 1
    )


def should_run_weekly_report(settings: dict[str, Any]) -> bool:
    """設定ON時に週次レポートを実行する。"""
    return bool(settings.get("run_weekly_report", False))


def should_run_weekly_dashboard(
    settings: dict[str, Any],
    weekly_report_selected: bool = False,
) -> bool:
    """週次ダッシュボードを実行するか判定する。"""
    return bool(settings.get("run_weekly_dashboard", False)) or weekly_report_selected


def _build_step_definitions(default_dry_run: bool) -> dict[str, dict[str, Any]]:
    return {
        "scheduler": {
            "name": "scheduler",
            "cmd": ["python3", "-m", "scheduler.scheduler"],
            "timeout_sec": 900,
            "env_overrides": {
                "SCHEDULER_RUN_ONCE": "1",
                "SCHEDULER_MODE": "interval",
                "SCHEDULER_INTERVAL_SECONDS": "1",
                "WP_DRY_RUN": "1" if default_dry_run else "0",
            },
        },
        "smoke_test": {
            "name": "smoke_test",
            "cmd": ["python3", "-m", "testing.smoke_test_runner"],
            "timeout_sec": 1200,
            "env_overrides": {},
        },
        "anomaly_check": {
            "name": "anomaly_check",
            "cmd": ["python3", "-m", "monitoring.run_anomaly_check"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "daily_report": {
            "name": "daily_report",
            "cmd": ["python3", "-m", "reporting.run_daily_report"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "dashboard_build": {
            "name": "dashboard_build",
            "cmd": ["python3", "-m", "reporting.run_dashboard_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "archive_backup": {
            "name": "archive_backup",
            "cmd": ["python3", "-m", "ops.run_archive_backup"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "log_rotate": {
            "name": "log_rotate",
            "cmd": ["python3", "-m", "ops.run_log_rotate"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "release_readiness_check": {
            "name": "release_readiness_check",
            "cmd": ["python3", "-m", "ops.run_release_readiness_check"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_home_build": {
            "name": "ops_home_build",
            "cmd": ["python3", "-m", "reporting.run_ops_home_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_summary_build": {
            "name": "ops_summary_build",
            "cmd": ["python3", "-m", "reporting.run_ops_summary_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_api_payload_build": {
            "name": "ops_api_payload_build",
            "cmd": ["python3", "-m", "reporting.run_ops_api_payload_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_status_light_build": {
            "name": "ops_status_light_build",
            "cmd": ["python3", "-m", "reporting.run_ops_status_light_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_manifest_build": {
            "name": "ops_manifest_build",
            "cmd": ["python3", "-m", "reporting.run_ops_manifest_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_home_payload_build": {
            "name": "ops_home_payload_build",
            "cmd": ["python3", "-m", "reporting.run_ops_home_payload_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_sidebar_build": {
            "name": "ops_sidebar_build",
            "cmd": ["python3", "-m", "reporting.run_ops_sidebar_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_tabs_build": {
            "name": "ops_tabs_build",
            "cmd": ["python3", "-m", "reporting.run_ops_tabs_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_header_build": {
            "name": "ops_header_build",
            "cmd": ["python3", "-m", "reporting.run_ops_header_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_widgets_build": {
            "name": "ops_widgets_build",
            "cmd": ["python3", "-m", "reporting.run_ops_widgets_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_layout_build": {
            "name": "ops_layout_build",
            "cmd": ["python3", "-m", "reporting.run_ops_layout_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_gui_schema_build": {
            "name": "ops_gui_schema_build",
            "cmd": ["python3", "-m", "reporting.run_ops_gui_schema_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_bootstrap_build": {
            "name": "ops_bootstrap_build",
            "cmd": ["python3", "-m", "reporting.run_ops_bootstrap_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "ops_gui_preview_build": {
            "name": "ops_gui_preview_build",
            "cmd": ["python3", "-m", "reporting.run_ops_gui_preview_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "mock_api_build": {
            "name": "mock_api_build",
            "cmd": ["python3", "-m", "reporting.run_mock_api_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "monthly_report": {
            "name": "monthly_report",
            "cmd": ["python3", "-m", "reporting.run_monthly_report"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "monthly_dashboard": {
            "name": "monthly_dashboard",
            "cmd": ["python3", "-m", "reporting.run_monthly_dashboard_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "weekly_report_build": {
            "name": "weekly_report_build",
            "cmd": ["python3", "-m", "reporting.run_weekly_report"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
        "weekly_dashboard_build": {
            "name": "weekly_dashboard_build",
            "cmd": ["python3", "-m", "reporting.run_weekly_dashboard_build"],
            "timeout_sec": 300,
            "env_overrides": {},
        },
    }


def extend_steps_from_settings(
    settings: dict[str, Any],
    default_dry_run: bool,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """設定から実行ステップ一覧を構築する。"""
    step_map = _build_step_definitions(default_dry_run)

    enabled_steps = settings.get("enabled_steps", [])
    if isinstance(enabled_steps, list) and enabled_steps:
        enabled_set = {str(step) for step in enabled_steps}
        selected_names = [name for name in BASE_STEP_ORDER if name in enabled_set]
        for step in enabled_steps:
            name = str(step)
            if name in step_map and name not in selected_names:
                selected_names.append(name)
    else:
        enabled_set = set(BASE_STEP_ORDER)
        selected_names = list(BASE_STEP_ORDER)

    if not bool(settings.get("enable_gui_assets", True)):
        selected_names = [name for name in selected_names if name not in GUI_STEP_NAMES]
        enabled_set = {name for name in enabled_set if name not in GUI_STEP_NAMES}

    run_monthly = "monthly_report" in enabled_set or should_run_monthly_report(settings, now=now)
    run_monthly_dashboard = "monthly_dashboard" in enabled_set or should_run_monthly_dashboard(
        settings,
        now=now,
        monthly_report_selected=run_monthly,
    )

    if run_monthly and "monthly_report" not in selected_names:
        selected_names.append("monthly_report")
    if run_monthly_dashboard and "monthly_dashboard" not in selected_names:
        selected_names.append("monthly_dashboard")

    run_weekly = "weekly_report_build" in enabled_set or should_run_weekly_report(settings)
    run_weekly_dashboard = (
        "weekly_dashboard_build" in enabled_set
        or should_run_weekly_dashboard(settings, weekly_report_selected=run_weekly)
    )

    if run_weekly and "weekly_report_build" not in selected_names:
        selected_names.append("weekly_report_build")
    if run_weekly_dashboard and "weekly_dashboard_build" not in selected_names:
        selected_names.append("weekly_dashboard_build")

    return [step_map[name] for name in selected_names if name in step_map]


def run_step(
    name: str,
    cmd: list[str],
    timeout_sec: int = 600,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """1ステップを subprocess で実行し、結果 dict を返す。"""
    started_at = _now_iso()
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=env,
        )
        returncode = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        status = "PASS" if returncode == 0 else "FAIL"
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        stderr = f"timeout after {timeout_sec}s\n{stderr}".strip()
        status = "FAIL"
    except Exception as exc:  # noqa: BLE001
        returncode = 1
        stdout = ""
        stderr = f"unexpected error: {exc}"
        status = "FAIL"

    ended_at = _now_iso()
    return {
        "name": name,
        "cmd": cmd,
        "started_at": started_at,
        "ended_at": ended_at,
        "returncode": returncode,
        "status": status,
        "stdout_head": _truncate_text(stdout),
        "stderr_head": _truncate_text(stderr),
    }


def run_ops_cycle(continue_on_error: bool | None = None) -> list[dict[str, Any]]:
    """主要運用ステップを順番実行する。"""
    default_dry_run = bool(get_ops_setting("ops.default_dry_run", True))
    ops_cycle_settings = get_ops_setting("ops_cycle", {})
    if not isinstance(ops_cycle_settings, dict):
        ops_cycle_settings = {}

    configured_continue_on_error = bool(ops_cycle_settings.get("continue_on_error", True))
    continue_flag = configured_continue_on_error if continue_on_error is None else continue_on_error
    steps = extend_steps_from_settings(ops_cycle_settings, default_dry_run=default_dry_run)

    results: list[dict[str, Any]] = []
    total = len(steps)
    for idx, step in enumerate(steps, 1):
        result = run_step(
            name=step["name"],
            cmd=step["cmd"],
            timeout_sec=int(step["timeout_sec"]),
            env_overrides=step.get("env_overrides"),
        )
        results.append(result)
        print(f"[{idx}/{total}] {result['name']} ... {result['status']}")

        if result["status"] == "FAIL" and not continue_flag:
            break

    # 通知失敗で ops cycle 本体を失敗扱いにしない。
    try:
        notify_ops_summary(summarize_results(results))
    except Exception:
        pass

    return results


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """結果一覧をサマリー化する。"""
    pass_count = sum(1 for r in results if r.get("status") == "PASS")
    fail_count = sum(1 for r in results if r.get("status") == "FAIL")

    return {
        "total": len(results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "overall": "PASS" if fail_count == 0 else "FAIL",
    }


def write_ops_log(results: list[dict[str, Any]]) -> str:
    """ops cycle 実行ログを data/logs/ops_cycle.log に保存する。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    summary = summarize_results(results)

    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("OPS CYCLE LOG")
    lines.append(f"timestamp: {_now_iso()}")
    lines.append("=" * 80)
    lines.append("")

    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] step: {r.get('name', '')}")
        lines.append(f"timestamp_start: {r.get('started_at', '')}")
        lines.append(f"timestamp_end: {r.get('ended_at', '')}")
        lines.append(f"returncode: {r.get('returncode', '')}")
        lines.append(f"status: {r.get('status', '')}")
        lines.append(f"cmd: {' '.join(r.get('cmd', []))}")
        lines.append("stdout_head:")
        lines.append(r.get("stdout_head", "") or "(none)")
        lines.append("stderr_head:")
        lines.append(r.get("stderr_head", "") or "(none)")
        lines.append("-" * 80)

    lines.append("FINAL SUMMARY")
    lines.append(json.dumps(summary, ensure_ascii=False, indent=2))
    lines.append("")

    OPS_LOG_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(OPS_LOG_PATH)
