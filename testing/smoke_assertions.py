from __future__ import annotations

# smoke_assertions.py
# 各スモークテストケースの出力・終了コード・ファイル存在を検証するアサーション群。
#
# 設計方針:
#   - 各 assert_* 関数は SmokeResult を受け取り、(passed, failures) を返す。
#   - passed=True  → 全チェック PASS
#   - passed=False → failures にエラーメッセージリストが入る。
#   - 関数は副作用を持たず、純粋に検証するだけ。

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ------------------------------------------------------------------ #
# SmokeResult  (runner からここへ渡される)
# ------------------------------------------------------------------ #

@dataclass
class SmokeResult:
    """1テストケースの実行結果。"""

    test_name: str
    returncode: int
    stdout: str
    stderr: str
    elapsed_sec: float
    env: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------ #
# 内部ヘルパー
# ------------------------------------------------------------------ #

def _check_returncode(result: SmokeResult, expected: int = 0) -> list[str]:
    if result.returncode != expected:
        return [
            f"終了コード: 期待={expected}, 実際={result.returncode} "
            f"(stderr 先頭: {result.stderr[:200]!r})"
        ]
    return []


def _check_contains(result: SmokeResult, patterns: list[str]) -> list[str]:
    """stdout に全パターンが含まれるかチェック。"""
    failures: list[str] = []
    for pat in patterns:
        if pat not in result.stdout:
            failures.append(f"stdout に {pat!r} が見つからない")
    return failures


def _check_any_contains(result: SmokeResult, candidates: list[str], label: str) -> list[str]:
    """stdout に candidates のいずれかが含まれるかチェック。"""
    for c in candidates:
        if c in result.stdout:
            return []
    return [f"stdout に {label} ({' / '.join(repr(c) for c in candidates)}) のいずれも見つからない"]


def _check_no_traceback(result: SmokeResult) -> list[str]:
    """Traceback が stderr に出ていないかチェック。"""
    if "Traceback (most recent call last)" in result.stderr:
        snippet = result.stderr[:400]
        return [f"stderr に Traceback が出力されている: {snippet!r}"]
    return []


def _extract_int(text: str, key: str) -> int | None:
    """'key: <数値>' を抽出して int で返す。見つからなければ None。"""
    m = re.search(rf"{re.escape(key)}[:\s]+(\d+)", text)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------ #
# 個別アサーション
# ------------------------------------------------------------------ #

def assert_main_dry_run(result: SmokeResult) -> tuple[bool, list[str]]:
    """main.py の dry-run を検証する。

    チェック内容:
    - 終了コード 0
    - Traceback なし
    - ステップ番号 [1/4] ～ [4/4] が出力される
    - 成功件数 / スキップ件数 / 失敗件数 の集計行が出る
    """
    failures: list[str] = []
    failures += _check_returncode(result)
    failures += _check_no_traceback(result)
    failures += _check_contains(result, [
        "[1/4]",
        "[2/4]",
        "[3/4]",
        "[4/4]",
        "成功件数:",
        "スキップ件数:",
        "失敗件数:",
    ])
    return (not failures), failures


def assert_price_change_refresh(result: SmokeResult) -> tuple[bool, list[str]]:
    """run_price_change_refresh の出力を検証する。

    チェック内容:
    - 終了コード 0
    - Traceback なし
    - checked_count が出力される
    - price_only_count または combined_count が出力される
    - 'price change refresh finished' が出力される
    """
    failures: list[str] = []
    failures += _check_returncode(result)
    failures += _check_no_traceback(result)
    failures += _check_contains(result, [
        "checked_count:",
        "price change refresh finished",
    ])
    failures += _check_any_contains(
        result,
        ["price_only_count:", "combined_count:"],
        "price_only_count / combined_count",
    )
    return (not failures), failures


def assert_release_refresh(result: SmokeResult) -> tuple[bool, list[str]]:
    """run_release_refresh の出力を検証する。

    チェック内容:
    - 終了コード 0
    - Traceback なし
    - checked_count が出力される
    - release_only_count または combined_count が出力される
    - 'release refresh finished' が出力される
    """
    failures: list[str] = []
    failures += _check_returncode(result)
    failures += _check_no_traceback(result)
    failures += _check_contains(result, [
        "checked_count:",
        "release refresh finished",
    ])
    failures += _check_any_contains(
        result,
        ["release_only_count:", "combined_count:"],
        "release_only_count / combined_count",
    )
    return (not failures), failures


def assert_show_retry_queue(result: SmokeResult) -> tuple[bool, list[str]]:
    """show_retry_queue の出力を検証する。

    チェック内容:
    - 終了コード 0
    - Traceback なし
    - 'retry_queue status counts:' が出力される
    - queued: / retrying: / resolved: / give_up: が出力される
    """
    failures: list[str] = []
    failures += _check_returncode(result)
    failures += _check_no_traceback(result)
    failures += _check_contains(result, [
        "retry_queue status counts:",
        "queued:",
        "retrying:",
        "resolved:",
        "give_up:",
    ])
    return (not failures), failures


def assert_show_status_report(result: SmokeResult) -> tuple[bool, list[str]]:
    """show_status_report の出力を検証する。

    チェック内容:
    - 終了コード 0
    - Traceback なし
    - 'status 集計:' が出力される
    - draft: / published: / skipped: / failed: が出力される
    """
    failures: list[str] = []
    failures += _check_returncode(result)
    failures += _check_no_traceback(result)
    failures += _check_contains(result, [
        "status 集計:",
        "draft:",
        "published:",
        "skipped:",
        "failed:",
    ])
    return (not failures), failures


# ------------------------------------------------------------------ #
# アサーション登録テーブル (runner が参照)
# ------------------------------------------------------------------ #

#: test_name -> assert 関数 のマッピング
ASSERTION_MAP: dict[str, Any] = {
    "main_dry_run": assert_main_dry_run,
    "price_change_refresh": assert_price_change_refresh,
    "release_refresh": assert_release_refresh,
    "show_retry_queue": assert_show_retry_queue,
    "show_status_report": assert_show_status_report,
}
