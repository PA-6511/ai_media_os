from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ARCHIVE_NAME_PREFIX = "ops_archive_"


def collect_archive_targets() -> list[Path]:
    """バックアップ対象の既存パスを収集する。"""
    targets: list[Path] = []

    candidate_dirs = [
        DATA_DIR / "reports",
        DATA_DIR / "logs",
        DATA_DIR / "test_outputs",
    ]
    for path in candidate_dirs:
        if path.exists() and path.is_dir():
            targets.append(path)

    for db_path in sorted(DATA_DIR.glob("*.db")):
        if db_path.is_file():
            targets.append(db_path)

    return targets


def _build_archive_name(now: datetime | None = None) -> str:
    ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{ARCHIVE_NAME_PREFIX}{ts}.zip"


def _add_directory_to_zip(zip_file: ZipFile, directory: Path, base_dir: Path) -> None:
    """ディレクトリを再帰的に zip へ追加する。"""
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        arcname = str(path.relative_to(base_dir))
        zip_file.write(path, arcname=arcname)


def build_archive(output_dir: Path) -> Path:
    """対象ファイルを zip にまとめて保存する。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = collect_archive_targets()

    archive_path = output_dir / _build_archive_name()
    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for target in targets:
            if target.is_dir():
                _add_directory_to_zip(zf, target, base_dir=BASE_DIR)
            elif target.is_file():
                arcname = str(target.relative_to(BASE_DIR))
                zf.write(target, arcname=arcname)

    return archive_path
