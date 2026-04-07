from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from ops.archive_builder import ARCHIVE_NAME_PREFIX, DATA_DIR


DEFAULT_ARCHIVE_DIR = DATA_DIR / "archives"


def find_latest_archive(archive_dir: Path = DEFAULT_ARCHIVE_DIR) -> Path:
    """最新の ops_archive_*.zip を返す。"""
    if not archive_dir.exists() or not archive_dir.is_dir():
        raise FileNotFoundError(f"archive ディレクトリが見つかりません: {archive_dir}")

    candidates = sorted(
        [path for path in archive_dir.glob(f"{ARCHIVE_NAME_PREFIX}*.zip") if path.is_file()],
        key=lambda p: p.name,
    )
    if not candidates:
        raise FileNotFoundError(f"archive が見つかりません: {archive_dir}")
    return candidates[-1]


def summarize_archive_entries(entries: list[str]) -> dict[str, int]:
    """zip 内の主要カテゴリ件数を集計する。"""
    reports_count = 0
    logs_count = 0
    test_outputs_count = 0
    db_count = 0

    for entry in entries:
        normalized = entry.strip()
        if not normalized or normalized.endswith("/"):
            continue
        if normalized.startswith("data/reports/"):
            reports_count += 1
        elif normalized.startswith("data/logs/"):
            logs_count += 1
        elif normalized.startswith("data/test_outputs/"):
            test_outputs_count += 1
        elif normalized.startswith("data/") and normalized.endswith(".db") and "/" not in normalized[len("data/") :]:
            db_count += 1

    return {
        "reports_count": reports_count,
        "logs_count": logs_count,
        "test_outputs_count": test_outputs_count,
        "db_count": db_count,
        "total_entries": len([entry for entry in entries if entry and not entry.endswith("/")]),
    }


def inspect_archive(path: Path) -> dict:
    """zip を検査し、中身一覧と集計結果を返す。"""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"archive が見つかりません: {path}")

    try:
        with ZipFile(path, mode="r") as zf:
            bad_member = zf.testzip()
            entries = zf.namelist()
    except BadZipFile as exc:
        raise ValueError(f"壊れた zip です: {path} ({exc})") from exc
    except OSError as exc:
        raise OSError(f"archive の読み込みに失敗しました: {path} ({exc})") from exc

    summary = summarize_archive_entries(entries)
    return {
        "path": str(path),
        "is_valid": bad_member is None,
        "bad_member": bad_member,
        "entries": entries,
        "summary": summary,
    }
