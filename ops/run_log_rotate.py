from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from config.ops_settings_loader import get_ops_setting
from ops.log_rotator import BASE_DIR, rotate_logs, summarize_rotation_results, write_rotation_log


def _resolve_target_logs(raw_paths: Any) -> list[Path]:
    if not isinstance(raw_paths, list):
        return []

    resolved: list[Path] = []
    for item in raw_paths:
        if not isinstance(item, str):
            continue
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        resolved.append(candidate)
    return resolved


def main(argv: list[str] | None = None) -> int:
    settings = get_ops_setting("log_rotation", {})
    if not isinstance(settings, dict):
        settings = {}

    enabled_default = bool(settings.get("enabled", True))
    keep_default = int(settings.get("keep_generations", 7))
    compress_default = bool(settings.get("compress_rotated", False))
    targets_default = _resolve_target_logs(settings.get("target_logs", []))

    parser = argparse.ArgumentParser(description="運用ログの世代ローテーションを実行する")
    parser.add_argument("--keep", type=int, default=keep_default, help="保持世代数")
    parser.add_argument(
        "--compress",
        action="store_true",
        default=compress_default,
        help="ローテート世代を gzip 圧縮する",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="gzip 圧縮を無効化する (設定値を上書き)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="settings の enabled=false を無視して実行する",
    )
    args = parser.parse_args(argv)

    if not args.force and not enabled_default:
        print("log rotation is disabled by settings: log_rotation.enabled=false")
        return 0

    compress = False if args.no_compress else bool(args.compress)
    keep = max(int(args.keep), 1)
    targets = targets_default

    if not targets:
        print("no target logs configured")
        return 1

    results = rotate_logs(paths=targets, keep=keep, compress=compress)
    summary = summarize_rotation_results(results)
    report_path = write_rotation_log(results)

    print("Log rotation summary:")
    print(f"total: {summary['total']}")
    print(f"rotated: {summary['rotated']}")
    print(f"skipped: {summary['skipped']}")
    print(f"errors: {summary['errors']}")
    print(f"report: {report_path}")

    for item in results:
        status = item.get("status")
        path = item.get("path")
        rotated_to = item.get("rotated_to")
        reason = item.get("reason")
        error = item.get("error")

        if status == "ROTATED":
            print(f"[ROTATED] {path} -> {rotated_to}")
        elif status == "SKIP":
            print(f"[SKIP] {path} ({reason})")
        else:
            print(f"[ERROR] {path} ({error})")

    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())