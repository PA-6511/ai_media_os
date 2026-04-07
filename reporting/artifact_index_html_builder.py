from __future__ import annotations

import html
from pathlib import Path
from typing import Any


_LABEL: dict[str, str] = {
    "latest_daily_report_json":    "Latest Daily Report (JSON)",
    "latest_daily_report_txt":     "Latest Daily Report (TXT)",
    "latest_weekly_report_json":   "Latest Weekly Report (JSON)",
    "latest_weekly_report_txt":    "Latest Weekly Report (TXT)",
    "latest_monthly_report_json":  "Latest Monthly Report (JSON)",
    "latest_monthly_report_txt":   "Latest Monthly Report (TXT)",
    "latest_dashboard":            "Latest Dashboard",
    "latest_weekly_dashboard":     "Latest Weekly Dashboard",
    "latest_monthly_dashboard":    "Latest Monthly Dashboard",
    "latest_ops_decision_dashboard": "Latest Ops Decision Dashboard",
    "latest_release_readiness_json": "Latest Release Readiness (JSON)",
    "latest_release_readiness_md": "Latest Release Readiness (MD)",
    "latest_archive":              "Latest Archive",
}

_DETAIL_ORDER = list(_LABEL.keys())


def _esc(value: Any) -> str:
    return html.escape(str(value)) if value is not None else "<em>none</em>"


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "-"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1_024:
        return f"{n / 1_024:.1f} KB"
    return f"{n} B"


def _basename(path_str: str | None) -> str:
    if not path_str:
        return "-"
    return Path(path_str).name


def _latest_rows_html(index: dict) -> str:
    rows: list[str] = []
    for key, label in _LABEL.items():
        val = index.get(key)
        rows.append(
            f"    <tr><td class='label'>{html.escape(label)}</td>"
            f"<td class='val'>{_esc(_basename(val))}</td></tr>"
        )
    return "\n".join(rows)


def _counts_rows_html(index: dict) -> str:
    counts = [
        ("Daily Report",   index.get("daily_report_count", 0)),
        ("Weekly Report",  index.get("weekly_report_count", 0)),
        ("Monthly Report", index.get("monthly_report_count", 0)),
        ("Archive",        index.get("archive_count", 0)),
    ]
    rows = [
        f"    <tr><td class='label'>{html.escape(label)}</td>"
        f"<td class='val'>{html.escape(str(n))}</td></tr>"
        for label, n in counts
    ]
    return "\n".join(rows)


def _details_rows_html(details: dict) -> str:
    rows: list[str] = []
    for key in _DETAIL_ORDER:
        label = _LABEL.get(key, key)
        info = details.get(key)
        if info is None:
            rows.append(
                f"  <tr>"
                f"<td class='label'>{html.escape(label)}</td>"
                f"<td><em>none</em></td><td>-</td><td>-</td>"
                f"</tr>"
            )
        else:
            fname = _esc(_basename(info.get("path")))
            size = html.escape(_fmt_bytes(info.get("size_bytes")))
            updated = _esc(info.get("updated_at", "-"))
            rows.append(
                f"  <tr>"
                f"<td class='label'>{html.escape(label)}</td>"
                f"<td>{fname}</td>"
                f"<td>{size}</td>"
                f"<td class='ts'>{updated}</td>"
                f"</tr>"
            )
    return "\n".join(rows)


def build_artifact_index_html(index: dict) -> str:
    """artifact index dict を HTML 文字列に変換する。"""
    generated_at = _esc(index.get("generated_at", "-"))
    report_dir   = _esc(index.get("report_dir", "-"))
    archive_dir  = _esc(index.get("archive_dir", "-"))
    details      = index.get("details") or {}

    latest_rows  = _latest_rows_html(index)
    counts_rows  = _counts_rows_html(index)
    details_rows = _details_rows_html(details)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Media OS – Artifact Index</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f8; color: #222; margin: 0; padding: 24px; }}
  h1   {{ font-size: 1.4rem; margin: 0 0 4px; color: #1a3a5c; }}
  .meta {{ font-size: 0.78rem; color: #666; margin-bottom: 24px; }}
  .meta span {{ margin-right: 24px; }}
  section {{ background: #fff; border-radius: 8px; padding: 20px 24px;
             margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  h2 {{ font-size: 1rem; margin: 0 0 12px; color: #1a3a5c; border-bottom: 2px solid #e0e8f0; padding-bottom: 6px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.88rem; }}
  th   {{ background: #e8f0f8; text-align: left; padding: 6px 12px; font-weight: 600; }}
  td   {{ padding: 6px 12px; border-bottom: 1px solid #eef; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  .label {{ color: #555; white-space: nowrap; width: 220px; }}
  .val   {{ font-family: monospace; word-break: break-all; }}
  .ts    {{ font-family: monospace; font-size: 0.82rem; color: #555; white-space: nowrap; }}
</style>
</head>
<body>
<h1>AI Media OS – Artifact Index</h1>
<div class="meta">
  <span>Generated: {generated_at}</span>
  <span>Report Dir: {report_dir}</span>
  <span>Archive Dir: {archive_dir}</span>
</div>

<section>
  <h2>Latest Artifacts</h2>
  <table>
    <tr><th>Item</th><th>File</th></tr>
{latest_rows}
  </table>
</section>

<section>
  <h2>Counts</h2>
  <table>
    <tr><th>Category</th><th>Count</th></tr>
{counts_rows}
  </table>
</section>

<section>
  <h2>Details</h2>
  <table>
    <tr><th>Item</th><th>File</th><th>Size</th><th>Updated At (UTC)</th></tr>
{details_rows}
  </table>
</section>
</body>
</html>
"""
