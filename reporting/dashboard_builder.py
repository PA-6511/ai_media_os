from __future__ import annotations

# dashboard_builder.py
# 日次レポート dict と履歴から、ダッシュボード向けモデルとHTMLを構築する。

from html import escape
from typing import Any


def _as_int(value: Any) -> int:
    """安全に int へ変換する。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_slug_list(value: Any) -> list[str]:
    """slug 一覧を安全に list[str] へ変換する。"""
    if not isinstance(value, list):
        return []
    return [str(v) for v in value]


def _to_history_row(report: dict[str, Any]) -> dict[str, Any]:
    """履歴テーブル1行分のデータを作る。"""
    return {
        "report_date": str(report.get("report_date", "")),
        "success_count": _as_int(report.get("success_count", 0)),
        "skipped_count": _as_int(report.get("skipped_count", 0)),
        "failed_count": _as_int(report.get("failed_count", 0)),
        "draft_count": _as_int(report.get("draft_count", 0)),
        "retry_queued_count": _as_int(report.get("retry_queued_count", 0)),
        "combined_count": _as_int(report.get("combined_count", 0)),
        "price_only_count": _as_int(report.get("price_only_count", 0)),
        "release_only_count": _as_int(report.get("release_only_count", 0)),
    }


def build_dashboard_model(
    report: dict[str, Any],
    recent_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """日次レポートから表示用モデルを構築する。"""
    report_date = str(report.get("report_date", "unknown"))
    generated_at = str(report.get("generated_at", ""))

    success_count = _as_int(report.get("success_count", 0))
    skipped_count = _as_int(report.get("skipped_count", 0))
    failed_count = _as_int(report.get("failed_count", 0))
    draft_count = _as_int(report.get("draft_count", 0))
    retry_queued_count = _as_int(report.get("retry_queued_count", 0))

    combined_count = _as_int(report.get("combined_count", 0))
    price_only_count = _as_int(report.get("price_only_count", 0))
    release_only_count = _as_int(report.get("release_only_count", 0))

    failed_slugs = _as_slug_list(report.get("failed_slugs", []))
    skipped_slugs = _as_slug_list(report.get("skipped_slugs", []))
    draft_slugs = _as_slug_list(report.get("draft_slugs", []))

    total_processed = success_count + skipped_count + failed_count

    history_rows = [_to_history_row(r) for r in (recent_reports or [])]

    return {
        "report_date": report_date,
        "generated_at": generated_at,
        "counts": {
            "success": success_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "draft": draft_count,
            "retry_queued": retry_queued_count,
            "total_processed": total_processed,
        },
        "signals": {
            "combined": combined_count,
            "price_only": price_only_count,
            "release_only": release_only_count,
        },
        "slugs": {
            "failed": failed_slugs,
            "skipped": skipped_slugs,
            "draft": draft_slugs,
        },
        "recent_history": history_rows,
    }


def _render_slug_list(title: str, slugs: list[str]) -> str:
    """slug 一覧セクションを HTML 文字列で返す。"""
    if not slugs:
        items_html = '<li class="empty">- なし</li>'
    else:
        items_html = "\n".join(f"<li>{escape(slug)}</li>" for slug in slugs)

    return f"""
      <section class=\"panel\">
        <h3>{escape(title)}</h3>
        <ul class=\"slug-list\">
          {items_html}
        </ul>
      </section>
    """


def build_recent_history_table(reports: list[dict[str, Any]]) -> str:
    """直近履歴テーブルの HTML を生成する。"""
    if not reports:
        return "<p class=\"muted\">履歴データがありません。</p>"

    # 新しい日付を上に表示
    ordered = sorted(reports, key=lambda r: str(r.get("report_date", "")), reverse=True)

    rows_html: list[str] = []
    for r in ordered:
        rows_html.append(
            "<tr>"
            f"<td>{escape(str(r.get('report_date', '')))}</td>"
            f"<td>{_as_int(r.get('success_count', 0))}</td>"
            f"<td>{_as_int(r.get('skipped_count', 0))}</td>"
            f"<td>{_as_int(r.get('failed_count', 0))}</td>"
            f"<td>{_as_int(r.get('draft_count', 0))}</td>"
            f"<td>{_as_int(r.get('retry_queued_count', 0))}</td>"
            f"<td>{_as_int(r.get('combined_count', 0))}</td>"
            f"<td>{_as_int(r.get('price_only_count', 0))}</td>"
            f"<td>{_as_int(r.get('release_only_count', 0))}</td>"
            "</tr>"
        )

    body = "\n".join(rows_html)

    return f"""
      <div class=\"table-wrap\">
        <table class=\"history-table\">
          <thead>
            <tr>
              <th>report_date</th>
              <th>success</th>
              <th>skipped</th>
              <th>failed</th>
              <th>draft</th>
              <th>retry_queued</th>
              <th>combined</th>
              <th>price_only</th>
              <th>release_only</th>
            </tr>
          </thead>
          <tbody>
            {body}
          </tbody>
        </table>
      </div>
    """


def build_dashboard_html(model: dict[str, Any]) -> str:
    """表示用モデルから静的 HTML を生成する。"""
    report_date = escape(str(model.get("report_date", "unknown")))
    generated_at = escape(str(model.get("generated_at", "")))

    counts = model.get("counts", {})
    signals = model.get("signals", {})
    slugs = model.get("slugs", {})
    recent_history = model.get("recent_history", [])

    failed_section = _render_slug_list("Failed Slugs", slugs.get("failed", []))
    skipped_section = _render_slug_list("Skipped Slugs", slugs.get("skipped", []))
    draft_section = _render_slug_list("Draft Slugs", slugs.get("draft", []))
    history_table = build_recent_history_table(recent_history)

    return f"""<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>AI Media OS Dashboard</title>
  <style>
    :root {{
      --bg: #f4f7f4;
      --panel: #ffffff;
      --text: #1e2a1f;
      --muted: #5f6f60;
      --line: #d9e3da;
      --accent: #246b45;
      --warn: #b06b00;
      --danger: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN", sans-serif;
      color: var(--text);
      background: linear-gradient(140deg, #edf6ef, #f8fbf8 45%, #eef4ff);
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .header {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }}
    .header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
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
      border-radius: 12px;
      padding: 14px;
    }}
    .card .label {{ color: var(--muted); font-size: 12px; margin-bottom: 8px; }}
    .card .value {{ font-size: 28px; font-weight: 700; line-height: 1; }}
    .value.warn {{ color: var(--warn); }}
    .value.danger {{ color: var(--danger); }}
    .value.accent {{ color: var(--accent); }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 12px;
    }}
    .panel h3 {{ margin: 0 0 10px 0; font-size: 16px; }}

    .panels {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}

    .slug-list {{ margin: 0; padding-left: 18px; max-height: 300px; overflow: auto; }}
    .slug-list li {{ margin: 4px 0; font-size: 13px; }}
    .slug-list li.empty {{ list-style: none; color: var(--muted); margin-left: -18px; }}

    .table-wrap {{ overflow-x: auto; }}
    .history-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      min-width: 920px;
    }}
    .history-table th,
    .history-table td {{
      border: 1px solid var(--line);
      padding: 8px;
      text-align: right;
      white-space: nowrap;
    }}
    .history-table th:first-child,
    .history-table td:first-child {{ text-align: left; }}
    .history-table thead th {{
      background: #eef6f0;
      font-weight: 700;
    }}

    .muted {{ color: var(--muted); font-size: 13px; }}
    .footer {{ color: var(--muted); font-size: 12px; margin-top: 14px; }}
  </style>
</head>
<body>
  <main class=\"container\">
    <header class=\"header\">
      <h1>AI Media OS 簡易運用ダッシュボード</h1>
      <div class=\"sub\">レポート日: {report_date} / 生成時刻: {generated_at}</div>
    </header>

    <section class=\"grid\">
      <article class=\"card\"><div class=\"label\">Success</div><div class=\"value accent\">{counts.get("success", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Skipped</div><div class=\"value\">{counts.get("skipped", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Failed</div><div class=\"value danger\">{counts.get("failed", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Draft</div><div class=\"value\">{counts.get("draft", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Retry Queued</div><div class=\"value warn\">{counts.get("retry_queued", 0)}</div></article>
    </section>

    <section class=\"grid\">
      <article class=\"card\"><div class=\"label\">Combined</div><div class=\"value\">{signals.get("combined", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Price Only</div><div class=\"value\">{signals.get("price_only", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Release Only</div><div class=\"value\">{signals.get("release_only", 0)}</div></article>
      <article class=\"card\"><div class=\"label\">Total Processed</div><div class=\"value\">{counts.get("total_processed", 0)}</div></article>
    </section>

    <section class=\"panel\">
      <h3>直近7日 ミニ履歴</h3>
      {history_table}
    </section>

    <section class=\"panels\">
      {failed_section}
      {skipped_section}
      {draft_section}
    </section>

    <div class=\"footer\">Generated from daily_report_YYYYMMDD.json</div>
  </main>
</body>
</html>
"""
