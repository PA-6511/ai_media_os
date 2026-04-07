from __future__ import annotations

import gzip
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "data" / "logs"
ROTATE_LOG_PATH = LOG_DIR / "log_rotate.log"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generation_candidates(path: Path, generation: int) -> list[Path]:
    return [
        path.with_name(f"{path.name}.{generation}"),
        path.with_name(f"{path.name}.{generation}.gz"),
    ]


def _find_generation(path: Path, generation: int) -> Path | None:
    for candidate in _generation_candidates(path, generation):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _copy_as_plain(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def _copy_as_gzip(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, gzip.open(destination, "wb") as dst:
        shutil.copyfileobj(src, dst)


def _truncate_file(path: Path) -> None:
    # 元ファイル inode を維持して truncate すると、稼働中プロセスの file handle を壊しにくい。
    with path.open("r+b") as fh:
        fh.truncate(0)


def rotate_log(path: Path, keep: int, compress: bool) -> dict:
    """単一ログを世代ローテーションする。"""
    keep_count = max(int(keep), 1)
    result: dict = {
        "path": str(path),
        "status": "SKIP",
        "rotated": False,
        "keep": keep_count,
        "compress": bool(compress),
        "removed": [],
        "moved": [],
        "bytes_before": 0,
        "rotated_to": None,
        "error": None,
        "timestamp": _now_iso(),
    }

    if not path.exists() or not path.is_file():
        result["reason"] = "file_not_found"
        return result

    try:
        bytes_before = path.stat().st_size
        result["bytes_before"] = bytes_before
        if bytes_before <= 0:
            result["reason"] = "empty_file"
            return result

        oldest = _find_generation(path, keep_count)
        if oldest is not None:
            oldest.unlink()
            result["removed"].append(str(oldest))

        for generation in range(keep_count - 1, 0, -1):
            source = _find_generation(path, generation)
            if source is None:
                continue
            suffix = ".gz" if source.name.endswith(".gz") else ""
            target = path.with_name(f"{path.name}.{generation + 1}{suffix}")
            source.replace(target)
            result["moved"].append({"from": str(source), "to": str(target)})

        rotated_to = path.with_name(f"{path.name}.1.gz" if compress else f"{path.name}.1")
        if compress:
            _copy_as_gzip(path, rotated_to)
        else:
            _copy_as_plain(path, rotated_to)

        _truncate_file(path)
        result["rotated"] = True
        result["status"] = "ROTATED"
        result["rotated_to"] = str(rotated_to)
        return result
    except Exception as exc:  # noqa: BLE001
        result["status"] = "ERROR"
        result["error"] = str(exc)
        return result


def rotate_logs(paths: list[Path], keep: int, compress: bool) -> list[dict]:
    """複数ログをローテーションする。"""
    results: list[dict] = []
    for path in paths:
        results.append(rotate_log(path=path, keep=keep, compress=compress))
    return results


def summarize_rotation_results(results: list[dict]) -> dict:
    rotated = sum(1 for r in results if r.get("status") == "ROTATED")
    skipped = sum(1 for r in results if r.get("status") == "SKIP")
    errors = sum(1 for r in results if r.get("status") == "ERROR")
    return {
        "total": len(results),
        "rotated": rotated,
        "skipped": skipped,
        "errors": errors,
        "overall": "PASS" if errors == 0 else "FAIL",
    }


def write_rotation_log(results: list[dict], log_path: Path | None = None) -> Path:
    """ローテーション結果を ops ログへ追記する。"""
    output_path = log_path or ROTATE_LOG_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_rotation_results(results)

    lines: list[str] = []
    lines.append("")
    lines.append("=" * 80)
    lines.append("LOG ROTATION REPORT")
    lines.append(f"timestamp: {_now_iso()}")
    lines.append("=" * 80)
    for item in results:
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.append("summary:")
    lines.append(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    with output_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return output_path