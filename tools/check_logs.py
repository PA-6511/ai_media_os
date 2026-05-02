"""tools/check_logs.py

ログファイルの末尾 N 行を表示する運用ツール。

Usage:
    cd ~/ai_media_os
    python tools/check_logs.py --lines 50
    python tools/check_logs.py --log pipeline_failures --lines 100
    python tools/check_logs.py --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "data" / "logs"

# 表示対象ログの優先順位リスト（--log 未指定時は先頭のものを表示）
DEFAULT_LOG_ORDER = [
    "pipeline_failures",
    "sale_end_check",
    "run_ai_post_queue",
    "ops_cycle",
    "scheduler",
    "anomaly_check",
    "combined_signal",
    "smoke_test",
    "price_change",
    "release_change",
    "log_rotate",
]


def _list_available_logs(log_dir: Path) -> list[str]:
    """利用可能なログファイル名（拡張子なし、ローテーション除く）を返す。"""
    names: list[str] = []
    seen: set[str] = set()
    for p in sorted(log_dir.glob("*.log")):
        stem = p.stem  # "pipeline_failures" etc.
        if stem not in seen:
            seen.add(stem)
            names.append(stem)
    return names


def _resolve_log_path(log_name: str, log_dir: Path) -> Path | None:
    """ログ名からパスを解決する。"""
    candidate = log_dir / f"{log_name}.log"
    if candidate.exists():
        return candidate
    # 部分一致フォールバック
    for p in sorted(log_dir.glob("*.log")):
        if log_name.lower() in p.stem.lower():
            return p
    return None


def _tail_lines(path: Path, n: int) -> list[str]:
    """ファイルの末尾 n 行を返す。"""
    with path.open("rb") as f:
        # 後ろから読む
        f.seek(0, 2)
        file_size = f.tell()
        if file_size == 0:
            return []

        buffer = bytearray()
        chunk_size = min(4096, file_size)
        pos = file_size
        lines_found = 0

        while pos > 0 and lines_found < n + 1:
            read_size = min(chunk_size, pos)
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            buffer = bytearray(chunk) + buffer
            lines_found = buffer.count(b"\n")

    text = buffer.decode("utf-8", errors="replace")
    all_lines = text.splitlines()
    return all_lines[-n:] if len(all_lines) > n else all_lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ai_media_os ログビューア",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""例:
  python tools/check_logs.py --lines 50
  python tools/check_logs.py --log pipeline_failures --lines 100
  python tools/check_logs.py --list
""",
    )
    parser.add_argument(
        "--lines", "-n",
        type=int,
        default=50,
        metavar="N",
        help="表示する末尾行数 (デフォルト: 50)",
    )
    parser.add_argument(
        "--log", "-l",
        default=None,
        metavar="LOGNAME",
        help="表示するログ名 (例: pipeline_failures)。未指定時は優先順に最初に見つかったログ",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="利用可能なログ一覧を表示して終了",
    )
    args = parser.parse_args(argv)

    if not LOG_DIR.exists():
        print(f"[error] ログディレクトリが存在しません: {LOG_DIR}", file=sys.stderr)
        return 1

    available = _list_available_logs(LOG_DIR)

    if args.list:
        print("利用可能なログ一覧:")
        for name in available:
            path = LOG_DIR / f"{name}.log"
            size_kb = path.stat().st_size // 1024 if path.exists() else 0
            print(f"  {name:<30} ({size_kb} KB)")
        return 0

    # 表示するログを決定
    if args.log:
        log_path = _resolve_log_path(args.log, LOG_DIR)
        if log_path is None:
            print(f"[error] ログが見つかりません: {args.log}", file=sys.stderr)
            print(f"利用可能なログ: {', '.join(available)}", file=sys.stderr)
            return 1
    else:
        # DEFAULT_LOG_ORDER の先頭から存在するものを使う
        log_path = None
        for name in DEFAULT_LOG_ORDER:
            candidate = LOG_DIR / f"{name}.log"
            if candidate.exists():
                log_path = candidate
                break
        if log_path is None and available:
            log_path = LOG_DIR / f"{available[0]}.log"
        if log_path is None:
            print("[error] 表示できるログが見つかりません", file=sys.stderr)
            return 1

    lines = _tail_lines(log_path, args.lines)
    print(f"=== {log_path.name} (末尾 {args.lines} 行) ===")
    if lines:
        for line in lines:
            print(line)
    else:
        print("(ログが空です)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
