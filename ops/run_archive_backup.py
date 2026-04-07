from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config.ops_settings_loader import get_ops_setting
from ops.archive_builder import DATA_DIR, build_archive
from ops.archive_rotator import rotate_archives


def main(argv: list[str] | None = None) -> int:
    """アーカイブ作成とローテーションを実行する。"""
    default_keep = int(get_ops_setting("archive.keep_generations", 7))
    default_archive_dir = DATA_DIR / "archives"

    parser = argparse.ArgumentParser(description="運用成果物を zip バックアップする")
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=default_archive_dir,
        help="アーカイブ保存先 (デフォルト: data/archives)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=default_keep,
        help="保持世代数 (デフォルト: 7)",
    )
    args = parser.parse_args(argv)

    try:
        archive_path = build_archive(args.archive_dir)
        removed = rotate_archives(args.archive_dir, keep=args.keep)

        print(f"archive created: {archive_path}")
        print(f"keep generations: {max(args.keep, 1)}")
        print(f"removed archives: {len(removed)}")
        for p in removed:
            print(f"  - {p}")
        return 0
    except Exception as exc:
        print(f"archive backup failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
