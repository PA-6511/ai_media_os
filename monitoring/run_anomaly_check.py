from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from config.ops_settings_loader import get_ops_setting
from monitoring.alert_thresholds import load_thresholds
from monitoring.anomaly_detector import detect_anomalies, summarize_alerts
from monitoring.anomaly_notifier import notify_anomaly_result


BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "data" / "reports"
SMOKE_LOG_PATH = BASE_DIR / "data" / "logs" / "smoke_test.log"
ANOMALY_LOG_PATH = BASE_DIR / "data" / "logs" / "anomaly_check.log"
REPORT_FILE_PATTERN = re.compile(r"^daily_report_(\d{8})\.json$")


def _setup_logger(log_path: Path) -> logging.Logger:
    """anomaly_check 専用ロガーを初期化する。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("monitoring.anomaly_check")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def _to_bool(value: str, default: bool) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _load_notify_config() -> dict[str, bool]:
    """Slack通知可否の設定を環境変数から読み込む。"""
    default_notify_on_ok = bool(get_ops_setting("anomaly.notify_on_ok", False))
    default_notify_on_warning = bool(get_ops_setting("anomaly.notify_on_warning", True))
    default_notify_on_critical = bool(get_ops_setting("anomaly.notify_on_critical", True))

    return {
        "notify_on_ok": _to_bool(
            os.getenv("ANOMALY_NOTIFY_ON_OK", ""),
            default=default_notify_on_ok,
        ),
        "notify_on_warning": _to_bool(
            os.getenv("ANOMALY_NOTIFY_ON_WARNING", ""),
            default=default_notify_on_warning,
        ),
        "notify_on_critical": _to_bool(
            os.getenv("ANOMALY_NOTIFY_ON_CRITICAL", ""),
            default=default_notify_on_critical,
        ),
    }


def _sorted_report_paths(report_dir: Path) -> list[Path]:
    """daily_report_YYYYMMDD.json を日付順で返す。"""
    if not report_dir.exists() or not report_dir.is_dir():
        return []

    dated: list[tuple[str, Path]] = []
    for path in report_dir.glob("daily_report_*.json"):
        matched = REPORT_FILE_PATTERN.match(path.name)
        if matched:
            dated.append((matched.group(1), path))

    dated.sort(key=lambda x: x[0])
    return [path for _, path in dated]


def _load_report(path: Path) -> dict[str, Any]:
    """日次レポート JSON を読み込む。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"日次レポート JSON が不正です: {path} ({exc})") from exc
    except OSError as exc:
        raise OSError(f"日次レポートの読み込みに失敗しました: {path} ({exc})") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"日次レポートの形式が不正です: {path}")
    return payload


def load_latest_daily_report(report_dir: Path = REPORT_DIR) -> tuple[dict[str, Any], Path]:
    """最新の日次レポートを読み込む。"""
    paths = _sorted_report_paths(report_dir)
    if not paths:
        raise FileNotFoundError(
            "日次レポートが見つかりません。先に reporting.run_daily_report を実行してください。"
        )

    latest_path = paths[-1]
    return _load_report(latest_path), latest_path


def load_report_history(report_dir: Path = REPORT_DIR, max_days: int = 7) -> list[dict[str, Any]]:
    """直近 N 日分の日次レポートを読み込む。"""
    paths = _sorted_report_paths(report_dir)
    selected = paths[-max_days:] if max_days > 0 else paths
    return [_load_report(path) for path in selected]


def _count_smoke_failures(smoke_log_path: Path = SMOKE_LOG_PATH) -> int:
    """smoke_test.log から FAIL 件数を数える。"""
    if not smoke_log_path.exists() or not smoke_log_path.is_file():
        return 0

    try:
        content = smoke_log_path.read_text(encoding="utf-8")
    except OSError:
        return 0

    # "Status: FAIL" の出現数を fail 件数として扱う
    return len(re.findall(r"Status:\s*FAIL", content))


def _print_console_summary(summary: dict[str, Any], latest_report_path: Path) -> None:
    """コンソール向けの結果表示。"""
    now = datetime.now().isoformat(timespec="seconds")
    print()
    print("=" * 72)
    print("運用異常チェック結果")
    print("=" * 72)
    print(f"チェック時刻: {now}")
    print(f"最新レポート: {latest_report_path}")
    print(f"判定: {summary['overall_severity']}")
    print(f"alerts: total={summary['alert_count']} warning={summary['warning_count']} critical={summary['critical_count']}")
    print()

    if summary["alert_count"] == 0:
        print("異常は検知されませんでした。")
        return

    for idx, alert in enumerate(summary["alerts"], 1):
        print(
            f"[{idx}] {alert['severity']} {alert['rule_id']} | {alert['message']} "
            f"(source={alert['source']} value={alert['value']})"
        )
        details = alert.get("details") or {}
        excluded_fixture = details.get("excluded_fixture_count")
        if excluded_fixture is not None:
            print(
                f"    details: raw_failed={details.get('raw_failed_count')} "
                f"real_failed={details.get('real_failed_count')} "
                f"excluded_fixture={excluded_fixture}"
            )


def run_check(
    report_dir: Path = REPORT_DIR,
    smoke_log_path: Path = SMOKE_LOG_PATH,
    threshold_path: Path | None = None,
    recent_days: int = 7,
) -> dict[str, Any]:
    """異常判定を実行して結果を返す。"""
    thresholds = load_thresholds(threshold_path)
    latest_report, latest_path = load_latest_daily_report(report_dir)
    report_history = load_report_history(report_dir=report_dir, max_days=recent_days)
    smoke_failed_count = _count_smoke_failures(smoke_log_path)

    alerts = detect_anomalies(
        report=latest_report,
        thresholds=thresholds,
        report_history=report_history,
        smoke_failed_count=smoke_failed_count,
    )
    summary = summarize_alerts(alerts)

    return {
        "executed_at": datetime.now().isoformat(timespec="seconds"),
        "latest_report_path": str(latest_path),
        "latest_report": latest_report,
        "report_history_count": len(report_history),
        "smoke_failed_count": smoke_failed_count,
        "thresholds": thresholds,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(description="運用異常チェックを実行する")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORT_DIR,
        help="日次レポートディレクトリ (デフォルト: data/reports)",
    )
    parser.add_argument(
        "--smoke-log",
        type=Path,
        default=SMOKE_LOG_PATH,
        help="smoke_test.log パス (デフォルト: data/logs/smoke_test.log)",
    )
    parser.add_argument(
        "--threshold-path",
        type=Path,
        default=None,
        help="閾値設定 JSON パス (未指定時はデフォルト閾値)",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=7,
        help="連続日判定に使う日次レポートの最大件数",
    )

    args = parser.parse_args(argv)
    logger = _setup_logger(ANOMALY_LOG_PATH)
    notify_config = _load_notify_config()

    try:
        result = run_check(
            report_dir=args.report_dir,
            smoke_log_path=args.smoke_log,
            threshold_path=args.threshold_path,
            recent_days=args.recent_days,
        )
        summary = result["summary"]
        latest_report_path = Path(result["latest_report_path"])

        _print_console_summary(summary, latest_report_path)

        logger.info(
            "anomaly_check finished overall=%s alerts=%s warning=%s critical=%s latest_report=%s smoke_failed_count=%s",
            summary["overall_severity"],
            summary["alert_count"],
            summary["warning_count"],
            summary["critical_count"],
            latest_report_path,
            result["smoke_failed_count"],
        )
        for alert in summary["alerts"]:
            logger.warning(
                "alert severity=%s rule_id=%s message=%s source=%s value=%s threshold=%s",
                alert.get("severity"),
                alert.get("rule_id"),
                alert.get("message"),
                alert.get("source"),
                alert.get("value"),
                alert.get("threshold"),
            )

        # Slack通知は失敗しても本体は落とさない
        notified = notify_anomaly_result(result, config=notify_config)
        logger.info(
            "anomaly slack notify attempted=%s config_ok=%s config_warning=%s config_critical=%s",
            notified,
            notify_config["notify_on_ok"],
            notify_config["notify_on_warning"],
            notify_config["notify_on_critical"],
        )

        # CRITICAL を検知した場合は終了コード 2、WARNING は 1、OK は 0
        if summary["overall_severity"] == "CRITICAL":
            return 2
        if summary["overall_severity"] == "WARNING":
            return 1
        return 0

    except FileNotFoundError as exc:
        # 日次レポート自体が読めないケースは CRITICAL 相当として扱う
        logger.error("critical condition: daily report cannot be loaded error=%s", exc)
        print(f"CRITICAL: {exc}")
        return 2
    except ValueError as exc:
        logger.error("critical condition: daily report format invalid error=%s", exc)
        print(f"CRITICAL: {exc}")
        return 2
    except Exception as exc:
        logger.exception("anomaly_check failed error=%s", exc)
        print(f"エラーが発生しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
