from __future__ import annotations

from pathlib import Path


def rotate_archives(archive_dir: Path, keep: int = 7) -> list[Path]:
    """古いアーカイブを削除し、最新 keep 世代のみ残す。"""
    if keep < 1:
        keep = 1

    if not archive_dir.exists() or not archive_dir.is_dir():
        return []

    archives = sorted(
        [p for p in archive_dir.glob("ops_archive_*.zip") if p.is_file()],
        key=lambda p: p.name,
    )

    if len(archives) <= keep:
        return []

    to_delete = archives[: len(archives) - keep]
    removed: list[Path] = []
    for path in to_delete:
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            # 削除失敗は他ファイルの処理継続を優先
            continue

    return removed
