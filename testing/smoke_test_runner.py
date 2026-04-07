from __future__ import annotations

# smoke_test_runner.py
# E2E スモークテストランナー。
# 主要パイプラインを順番に実行して、全体が壊れていないかを検証する。
#
# 実行方法:
#   python3 -m testing.smoke_test_runner
#
# 環境変数:
#   SMOKE_LOG_DIR: ログ出力先 (デフォルト: data/logs)
#   SMOKE_VERBOSE: 1 で各テスト stdout を表示 (デフォルト: 0)

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# prj root を path に追加
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from config.ops_settings_loader import get_ops_setting

from testing.smoke_assertions import (
    SmokeResult,
    ASSERTION_MAP,
)

# ------------------------------------------------------------------ #
# 設定定義
# ------------------------------------------------------------------ #

LOG_DIR = Path(os.getenv("SMOKE_LOG_DIR", "data/logs"))
VERBOSE = os.getenv("SMOKE_VERBOSE", "0").strip() in {"1", "true", "yes"}

# テスト定義: (名前, テスト識別子, コマンド)
SMOKE_TESTS: list[tuple[str, str, list[str]]] = [
    ("main.py (dry-run)", "main_dry_run", ["python3", "./main.py"]),
    ("run_price_change_refresh", "price_change_refresh", ["python3", "-m", "pipelines.run_price_change_refresh"]),
    ("run_release_refresh", "release_refresh", ["python3", "-m", "pipelines.run_release_refresh"]),
    ("show_retry_queue", "show_retry_queue", ["python3", "-m", "pipelines.show_retry_queue"]),
    ("show_status_report", "show_status_report", ["python3", "-m", "pipelines.show_status_report"]),
]


def _normalize_smoke_step_id(step_id: str) -> str:
    """設定値の別名を内部 test_id へ正規化する。"""
    alias_map = {
        "main": "main_dry_run",
        "main_dry_run": "main_dry_run",
        "run_price_change_refresh": "price_change_refresh",
        "price_change_refresh": "price_change_refresh",
        "run_release_refresh": "release_refresh",
        "release_refresh": "release_refresh",
        "show_retry_queue": "show_retry_queue",
        "show_status_report": "show_status_report",
    }
    return alias_map.get(step_id, step_id)


def _get_enabled_smoke_tests() -> list[tuple[str, str, list[str]]]:
    """ops_settings の enabled_steps に基づいて実行対象を返す。"""
    enabled_steps = get_ops_setting("smoke_test.enabled_steps", [])
    if not isinstance(enabled_steps, list) or not enabled_steps:
        return SMOKE_TESTS

    enabled_ids = {_normalize_smoke_step_id(str(step)) for step in enabled_steps}
    selected = [test for test in SMOKE_TESTS if test[1] in enabled_ids]

    # 設定ミスで空になった場合は安全側で全件実行
    return selected if selected else SMOKE_TESTS


# ------------------------------------------------------------------ #
# ユーティリティ
# ------------------------------------------------------------------ #

def ensure_log_dir() -> Path:
    """ログディレクトリを作成する（存在しなければ）。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def _truncate_text(text: str, max_lines: int = 10) -> str:
    """テキストを先頭 N 行まで切り詰める。"""
    lines = text.split("\n")
    selected = lines[:max_lines]
    result = "\n".join(selected)
    if len(lines) > max_lines:
        remaining = len(lines) - max_lines
        result += f"\n... (残り {remaining} 行)"
    return result


def _format_timestamp() -> str:
    """ISO 8601 形式のタイムスタンプを返す。"""
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ #
# テスト実行エンジン
# ------------------------------------------------------------------ #

def run_command(
    test_name: str,
    cmd: list[str],
    *,
    cwd: Path | None = None,
) -> SmokeResult:
    """コマンドを実行して SmokeResult を返す。

    Args:
        test_name: テスト名（ログ用）
        cmd: 実行するコマンド（リスト）
        cwd: 作業ディレクトリ（デフォルト: project root）

    Returns:
        SmokeResult オブジェクト
    """
    if cwd is None:
        cwd = _PROJECT_ROOT

    print(f"  実行: {' '.join(cmd)}")

    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,  # 5分タイムアウト
        )
        elapsed_sec = time.time() - start_time
        return SmokeResult(
            test_name=test_name,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed_sec=elapsed_sec,
        )
    except subprocess.TimeoutExpired:
        elapsed_sec = time.time() - start_time
        return SmokeResult(
            test_name=test_name,
            returncode=-1,
            stdout="",
            stderr="[TIMEOUT] コマンドが 300 秒以内に完了しませんでした",
            elapsed_sec=elapsed_sec,
        )
    except Exception as exc:
        elapsed_sec = time.time() - start_time
        return SmokeResult(
            test_name=test_name,
            returncode=-1,
            stdout="",
            stderr=f"[EXCEPTION] {type(exc).__name__}: {exc}",
            elapsed_sec=elapsed_sec,
        )


def run_all_tests() -> list[SmokeResult]:
    """全スモークテストを実行して結果リストを返す。"""
    results: list[SmokeResult] = []
    effective_tests = _get_enabled_smoke_tests()

    print(f"\n{'=' * 70}")
    print("E2E スモークテスト開始")
    print(f"{'=' * 70}\n")

    for i, (test_name, test_id, cmd) in enumerate(effective_tests, start=1):
        print(f"[{i}/{len(effective_tests)}] {test_name}")

        result = run_command(test_name, cmd)
        result.extra["test_id"] = test_id  # 後で参照するため記録
        results.append(result)

        # アサーション実行
        assert_fn = ASSERTION_MAP.get(test_id)
        if assert_fn:
            passed, failures = assert_fn(result)
        else:
            passed, failures = False, [f"不明なテストID: {test_id}"]

        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}")

        if VERBOSE:
            print(f"\n  --- stdout ---")
            print(textwrap.indent(_truncate_text(result.stdout, max_lines=15), "    "))
            if result.stderr:
                print(f"  --- stderr ---")
                print(textwrap.indent(_truncate_text(result.stderr, max_lines=5), "    "))
            print()

        if not passed:
            print(f"  エラー詳細:")
            for failure in failures:
                print(f"    - {failure}")
            print()

    return results


def write_log(results: list[SmokeResult]) -> Path:
    """実行結果をログファイルに書き込む。

    Args:
        results: SmokeResult リスト

    Returns:
        ログファイルのパス
    """
    ensure_log_dir()
    log_path = LOG_DIR / "smoke_test.log"

    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"# E2E Smoke Test Log\n")
        f.write(f"# Generated at: {_format_timestamp()}\n")
        f.write(f"\n")

        for i, result in enumerate(results, start=1):
            f.write(f"## Test {i}: {result.test_name}\n")
            f.write(f"Timestamp: {_format_timestamp()}\n")
            f.write(f"ReturnCode: {result.returncode}\n")
            f.write(f"ElapsedSec: {result.elapsed_sec:.2f}\n")

            # アサーション実行
            test_id = result.extra.get("test_id", "unknown")
            assert_fn = ASSERTION_MAP.get(test_id)
            if assert_fn:
                passed, failures = assert_fn(result)
            else:
                passed, failures = False, [f"不明なテストID: {test_id}"]

            f.write(f"Status: {'PASS' if passed else 'FAIL'}\n")

            if failures:
                f.write(f"Failures:\n")
                for failure in failures:
                    f.write(f"  - {failure}\n")

            f.write(f"\nStdout (先頭500字):\n")
            f.write(f"{_truncate_text(result.stdout, max_lines=20)}\n")

            f.write(f"\nStderr (先頭500字):\n")
            stderr_text = result.stderr or "(なし)"
            f.write(f"{_truncate_text(stderr_text, max_lines=10)}\n")

            f.write(f"\n" + "-" * 70 + "\n\n")

    return log_path


def print_summary(results: list[SmokeResult]) -> int:
    """テスト結果サマリーをコンソール出力する。"""
    total = len(results)
    passed_count = 0
    failed_names: list[str] = []

    for result in results:
        test_id = result.extra.get("test_id", "unknown")
        assert_fn = ASSERTION_MAP.get(test_id)
        if assert_fn:
            is_passed, _ = assert_fn(result)
        else:
            is_passed = False

        if is_passed:
            passed_count += 1
        else:
            failed_names.append(result.test_name)

    print(f"\n{'=' * 70}")
    print("スモークテスト サマリー")
    print(f"{'=' * 70}")
    print(f"総実行: {total}")
    print(f"成功:   {passed_count}")
    print(f"失敗:   {total - passed_count}")

    if failed_names:
        print(f"\n失敗したテスト:")
        for name in failed_names:
            print(f"  - {name}")

    log_path = LOG_DIR / "smoke_test.log"
    print(f"\nログ出力先: {log_path}")

    print(f"{'=' * 70}\n")

    return 0 if not failed_names else 1


# ------------------------------------------------------------------ #
# エントリポイント
# ------------------------------------------------------------------ #

def main() -> int:
    """メイン処理。"""
    # ログディレクトリ作成
    ensure_log_dir()

    # 全テスト実行
    results = run_all_tests()

    # ログ書き込み
    log_path = write_log(results)

    # サマリー出力
    exit_code = print_summary(results)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
