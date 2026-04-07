from __future__ import annotations

import argparse
import sys

from ops.ops_runner import run_ops_cycle, summarize_results, write_ops_log


def main(argv: list[str] | None = None) -> int:
    """運用ワンコマンド実行の CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(description="AI Media OS の運用サイクルを順番実行する")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="途中で失敗しても残りステップを継続する",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="途中で失敗したら即停止する",
    )

    args = parser.parse_args(argv)
    if args.stop_on_error:
        continue_on_error: bool | None = False
    elif args.continue_on_error:
        continue_on_error = True
    else:
        continue_on_error = None

    results = run_ops_cycle(continue_on_error=continue_on_error)
    summary = summarize_results(results)
    log_path = write_ops_log(results)

    print()
    print("Ops cycle summary:")
    print(f"PASS: {summary['pass_count']}")
    print(f"FAIL: {summary['fail_count']}")
    print(f"log: {log_path}")

    return 0 if summary["fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
