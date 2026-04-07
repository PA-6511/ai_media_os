from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
MONTHLY_REPORT_PATTERN = re.compile(r"^monthly_report_(\d{6})\.json$")


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_ranked_slug_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug", "")).strip()
        if not slug:
            continue
        rows.append({"slug": slug, "count": _as_int(item.get("count", 0))})
    return rows


def load_latest_monthly_report(report_dir: Path = DEFAULT_REPORT_DIR) -> tuple[dict[str, Any], Path]:
    """最新の monthly_report_YYYYMM.json を読み込む。"""
    if not report_dir.exists() or not report_dir.is_dir():
        raise FileNotFoundError(f"レポートディレクトリが見つかりません: {report_dir}")

    dated_paths: list[tuple[str, Path]] = []
    for path in report_dir.glob("monthly_report_*.json"):
        matched = MONTHLY_REPORT_PATTERN.match(path.name)
        if matched:
            dated_paths.append((matched.group(1), path))

    if not dated_paths:
        raise FileNotFoundError(
            "monthly_report JSON が見つかりません。先に reporting.run_monthly_report を実行してください。"
        )

    dated_paths.sort(key=lambda x: x[0])
    latest_path = dated_paths[-1][1]

    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"monthly_report JSON が不正です: {latest_path} ({exc})") from exc
    except OSError as exc:
        raise OSError(f"monthly_report の読み込みに失敗しました: {latest_path} ({exc})") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"monthly_report の形式が不正です: {latest_path}")

    return payload, latest_path


def build_monthly_dashboard_model(report: dict[str, Any]) -> dict[str, Any]:
    """月次レポートから月次ダッシュボード表示モデルを構築する。"""
    counts = {
        "success": _as_int(report.get("total_success_count", 0)),
        "skipped": _as_int(report.get("total_skipped_count", 0)),
        "failed": _as_int(report.get("total_failed_count", 0)),
        "draft": _as_int(report.get("total_draft_count", 0)),
        "retry_queued": _as_int(report.get("total_retry_queued_count", 0)),
    }
    counts["total_processed"] = counts["success"] + counts["skipped"] + counts["failed"]

    signals = {
        "combined": _as_int(report.get("total_combined_count", 0)),
        "price_only": _as_int(report.get("total_price_only_count", 0)),
        "release_only": _as_int(report.get("total_release_only_count", 0)),
    }

    return {
        "report_month": str(report.get("report_month", "unknown")),
        "daily_report_count": _as_int(report.get("daily_report_count", 0)),
        "counts": counts,
        "signals": signals,
        "top_failed_slugs": _as_ranked_slug_rows(report.get("top_failed_slugs", [])),
        "top_skipped_slugs": _as_ranked_slug_rows(report.get("top_skipped_slugs", [])),
    }


def _render_ranked_slug_table(title: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        body = '<tr><td colspan="3" class="empty">- なし</td></tr>'
    else:
        body = "\n".join(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{escape(str(row.get('slug', '')))}</td>"
            f"<td>{_as_int(row.get('count', 0))}</td>"
            "</tr>"
            for idx, row in enumerate(rows, 1)
        )

    return f"""
      <section class=\"panel\">
        <h3>{escape(title)}</h3>
        <div class=\"table-wrap\">
          <table class=\"slug-table\">
            <thead>
              <tr>
                <th>#</th>
                <th>slug</th>
                <th>count</th>
              </tr>
            </thead>
            <tbody>
              {body}
            </tbody>
          </table>
        </div>
      </section>
    """


def build_monthly_dashboard_html(model: dict[str, Any]) -> str:
    """月次ダッシュボード HTML を生成する。"""
    report_month = escape(str(model.get("report_month", "unknown")))
    daily_report_count = _as_int(model.get("daily_report_count", 0))
    counts = model.get("counts", {})
    signals = model.get("signals", {})

    failed_table = _render_ranked_slug_table("Top Failed Slugs", model.get("top_failed_slugs", []))
    skipped_table = _render_ranked_slug_table("Top Skipped Slugs", model.get("top_skipped_slugs", []))

    return f"""<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>AI Media OS Monthly Dashboard</title>
  <style>
    :root {{
      --bg: #f5f8f1;
      --panel: #ffffff;
      --text: #213126;
      --muted: #5d6b60;
      --line: #dbe5d8;
      --accent: #2a7a57;
      --warn: #b67812;
      --danger: #b42318;
      --soft: #edf5ee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN", sans-serif;
      color: var(--text);
      background: linear-gradient(135deg, #eef7ef, #f8fbf6 42%, #eef3f9);
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    .header {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 22px;
      margin-bottom: 16px;
    }}
    .eyebrow {{ color: var(--accent); font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
    .header h1 {{ margin: 6px 0 8px 0; font-size: 26px; }}
    .sub {{ color: var(--muted); font-size: 14px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 10px 24px rgba(33, 49, 38, 0.04);
    }}
    .label {{ color: var(--muted); font-size: 12px; margin-bottom: 8px; }}
    .value {{ font-size: 30px; font-weight: 700; line-height: 1; }}
    .value.accent {{ color: var(--accent); }}
    .value.warn {{ color: var(--warn); }}
    .value.danger {{ color: var(--danger); }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 12px;
    }}
    .panel h3 {{ margin: 0 0 10px 0; font-size: 16px; }}
    .panels {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 12px;
    }}
    .table-wrap {{ overflow-x: auto; }}
    .slug-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .slug-table th, .slug-table td {{ border: 1px solid var(--line); padding: 8px; text-align: left; }}
    .slug-table th:last-child, .slug-table td:last-child {{ text-align: right; }}
    .slug-table thead th {{ background: var(--soft); }}
    .slug-table td.empty {{ text-align: center; color: var(--muted); }}
    .footer {{ color: var(--muted); font-size: 12px; margin-top: 14px; }}
  </style>
</head>
<body>
  <main class=\"container\">
    <header class=\"header\">
      <div class=\"eyebrow\">Monthly Operations</div>
      <h1>AI Media OS 月次ダッシュボード</h1>
      <div class=\"sub\">対象月: {report_month} / 日次レポート数: {daily_report_count}</div>
    </header>

    <section class=\"grid\">
      <article class=\"card\"><div class=\"label\">Success</div><div class=\"value accent\">{counts.get("success", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Skipped</div><div class=\"value\">{counts.get("skipped", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Failed</div><div class=\"value danger\">{counts.get("failed", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Draft</div><div class=\"value\">{counts.get("draft", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Retry Queued</div><div class=\"value warn\">{counts.get("retry_queued", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Daily Report Count</div><div class=\"value\">{daily_report_count}</div></article>
    </section>

    <section class=\"grid\">
      <article class=\"card\"><div class=\"label\">Combined</div><div class=\"value\">{signals.get("combined", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Price Only</div><div class=\"value\">{signals.get("price_only", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Release Only</div><div class=\"value\">{signals.get("release_only", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Total Processed</div><div class=\"value\">{counts.get("total_processed", 0)}</div></article>
    </section>

    <section class=\"panels\">
      {failed_table}
      {skipped_table}
    </section>

    <div class=\"footer\">Generated from monthly_report_YYYYMM.json</div>
  </main>
</body>
</html>
"""
