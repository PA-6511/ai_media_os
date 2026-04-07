from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_KPI_SNAPSHOTS_PATH = BASE_DIR / "data" / "kpi" / "kpi_snapshots.jsonl"


def load_kpi_snapshots(
    limit: int = 10,
    path: Path | None = None,
) -> list[dict]:
    """kpi_snapshots.jsonl から最新 limit 件を返す（新しい順）。

    ファイルが存在しない場合や読み込みエラー時は空リストを返す。
    """
    target = path or DEFAULT_KPI_SNAPSHOTS_PATH
    if not target.exists() or not target.is_file():
        return []

    try:
        raw_lines = [
            line for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return []

    records: list[dict] = []
    for line in raw_lines:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
        except json.JSONDecodeError:
            continue

    if limit > 0:
        records = records[-limit:]

    return list(reversed(records))


def load_latest_kpi_snapshot(path: Path | None = None) -> dict | None:
    """kpi_snapshots.jsonl から最新1件を返す。無い場合は None。"""
    snapshots = load_kpi_snapshots(limit=1, path=path)
    if not snapshots:
        return None
    latest = snapshots[0]
    return latest if isinstance(latest, dict) else None


def extract_kpi_summary(snapshot: dict | None) -> dict:
    """snapshot から運用表示向けの共通サマリーを抽出する。"""
    snap = snapshot or {}
    return {
        "generated_at": snap.get("generated_at"),
        "health_score": snap.get("health_score", "N/A"),
        "health_grade": snap.get("health_grade", "N/A"),
        "anomaly_overall": snap.get("anomaly_overall", "N/A"),
        "alert_total": snap.get("alert_total", 0),
        "retry_queued_count": snap.get("retry_queued_count", 0),
        "success_count": snap.get("success_count", 0),
        "skipped_count": snap.get("skipped_count", 0),
        "failed_count": snap.get("failed_count", 0),
        "combined_count": snap.get("combined_count", 0),
        "price_only_count": snap.get("price_only_count", 0),
        "release_only_count": snap.get("release_only_count", 0),
        "latest_archive": snap.get("latest_archive"),
    }


def _basename(path_str: str | None) -> str:
    if not path_str:
        return "N/A"
    return Path(path_str).name


def _fmt_at(generated_at: str | None) -> str:
    if not generated_at:
        return "N/A"
    # "2026-03-14T01:15:46.549113+00:00" → "2026-03-14 01:15:46 UTC"
    try:
        ts = generated_at.replace("T", " ")
        ts = ts.split(".")[0]
        ts = ts.split("+")[0]
        return ts + " UTC"
    except Exception:
        return generated_at


def format_kpi_snapshots(snapshots: list[dict]) -> str:
    """スナップショットリストを人間向けに整形した文字列を返す。"""
    if not snapshots:
        return "KPI snapshots: (no records found)"

    total = len(snapshots)
    lines: list[str] = [
        f"KPI Snapshots  ({total} record{'s' if total != 1 else ''})",
        "=" * 56,
    ]

    for i, snap in enumerate(snapshots, start=1):
        health_score = snap.get("health_score", "N/A")
        health_grade = snap.get("health_grade", "?")
        anomaly = snap.get("anomaly_overall", "N/A")
        alert_total = snap.get("alert_total", 0)
        success = snap.get("success_count", 0)
        skipped = snap.get("skipped_count", 0)
        failed = snap.get("failed_count", 0)
        combined = snap.get("combined_count", 0)
        price_only = snap.get("price_only_count", 0)
        release_only = snap.get("release_only_count", 0)
        archive_name = _basename(snap.get("latest_archive"))
        generated_at = _fmt_at(snap.get("generated_at"))

        lines.append(f"#{i}  {generated_at}")
        lines.append(f"   Health  : {health_score} ({health_grade})")
        lines.append(f"   Anomaly : {anomaly}  alerts={alert_total}")
        lines.append(
            f"   Success : {success:<4}  Skipped : {skipped:<4}  Failed : {failed}"
        )
        lines.append(
            f"   Combined: {combined:<4}  PriceOnly: {price_only:<4}  ReleaseOnly: {release_only}"
        )
        lines.append(f"   Archive : {archive_name}")
        if i < total:
            lines.append("-" * 56)

    lines.append("=" * 56)
    return "\n".join(lines)
