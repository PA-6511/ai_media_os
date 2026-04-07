from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"
DEFAULT_DAILY_CHECKLIST_PATH = DOCS_DIR / "daily_checklist_latest.md"
DEFAULT_RUNBOOK_PATH = DOCS_DIR / "runbook_latest.md"
DEFAULT_OPS_DECISION_DASHBOARD_PATH = DEFAULT_REPORT_DIR / "ops_decision_dashboard_latest.html"
DEFAULT_OPS_PORTAL_PATH = DEFAULT_REPORT_DIR / "ops_portal_latest.html"
DEFAULT_ARTIFACT_INDEX_PATH = DEFAULT_REPORT_DIR / "artifact_index_latest.html"
DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_RELEASE_TREND_MD_PATH = DEFAULT_REPORT_DIR / "release_readiness_trend_latest.md"
DEFAULT_STATUS_BADGE_JSON_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_href(path_str: str | None) -> str | None:
    if not path_str:
        return None
    try:
        return os.path.relpath(path_str, start=str(DEFAULT_REPORT_DIR)).replace("\\", "/")
    except Exception:
        return None


def _exists(path_str: str | None) -> bool:
    return bool(path_str) and Path(path_str).exists()


def _item_html(label: str, path_str: str | None) -> str:
    if _exists(path_str):
        href = _to_href(path_str)
        if href:
            name = html.escape(Path(path_str).name)
            return (
                f"<li><span class='k'>{html.escape(label)}</span>"
                f"<a href='{html.escape(href)}' target='_blank' rel='noopener'>{name}</a>"
                f"<span class='p'>{html.escape(path_str)}</span></li>"
            )

    return (
        f"<li><span class='k'>{html.escape(label)}</span>"
        "<span class='na'>N/A</span>"
        "<span class='p'>not found</span></li>"
    )


def _load_release_readiness() -> dict | None:
    path = DEFAULT_RELEASE_READINESS_JSON_PATH
    if not path.exists() or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def load_latest_status_badge() -> dict | None:
    """status_badge_latest.json を読み込み、dict を返す。"""
    path = DEFAULT_STATUS_BADGE_JSON_PATH
    if not path.exists() or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def build_status_badge_block(badge: dict | None) -> str:
    """運用ステータスバッジの表示ブロック HTML を返す。"""
    if not badge:
        return (
            "<section class='badge'>"
            "<div class='badge-pill level-unknown'>N/A</div>"
            "<div class='badge-main'>N/A | Health N/A | N/A</div>"
            "<div class='badge-sub'>badge_level=unknown / decision=N/A / health=N/A / anomaly=N/A</div>"
            "</section>"
        )

    badge_text = html.escape(str(badge.get("badge_text", "N/A")))
    badge_level = html.escape(str(badge.get("badge_level", "unknown")))
    decision = html.escape(str(badge.get("decision", "N/A")))
    health_score = html.escape(str(badge.get("health_score", "N/A")))
    health_grade = html.escape(str(badge.get("health_grade", "N/A")))
    anomaly_overall = html.escape(str(badge.get("anomaly_overall", "N/A")))

    level_class = {
        "ok": "level-ok",
        "warning": "level-warning",
        "critical": "level-critical",
    }.get(str(badge.get("badge_level", "")).lower(), "level-unknown")

    return (
        "<section class='badge'>"
        f"<div class='badge-pill {level_class}'>{decision}</div>"
        f"<div class='badge-main'>{badge_text}</div>"
        "<div class='badge-sub'>"
        f"badge_level={badge_level} / decision={decision} / health={health_score} ({health_grade}) / anomaly={anomaly_overall}"
        "</div>"
        "</section>"
    )


def _load_release_trend_summary() -> dict | None:
    path = DEFAULT_RELEASE_TREND_MD_PATH
    if not path.exists() or not path.is_file():
        return None

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    parsed: dict[str, str] = {}
    for line in lines:
        text = line.strip()
        if not text or ":" not in text:
            continue

        if text.startswith("total_days:"):
            parsed["total_days"] = text.split(":", 1)[1].strip()
        elif text.startswith("latest_decision:"):
            parsed["latest_decision"] = text.split(":", 1)[1].strip()
        elif text.startswith("- release_count:"):
            parsed["release_count"] = text.split(":", 1)[1].strip()
        elif text.startswith("- review_count:"):
            parsed["review_count"] = text.split(":", 1)[1].strip()
        elif text.startswith("- hold_count:"):
            parsed["hold_count"] = text.split(":", 1)[1].strip()

    return {
        "path": str(path),
        "trend_total_days": parsed.get("total_days", "N/A"),
        "trend_release_count": parsed.get("release_count", "N/A"),
        "trend_review_count": parsed.get("review_count", "N/A"),
        "trend_hold_count": parsed.get("hold_count", "N/A"),
        "latest_decision": parsed.get("latest_decision", "N/A"),
    }


def build_release_trend_summary_block(summary: dict | None) -> str:
    """release readiness trend の短い要約ブロック HTML を返す。"""
    trend_link = _item_html("Release Readiness Trend (MD)", str(DEFAULT_RELEASE_TREND_MD_PATH))

    if not summary:
        return (
            "<section class='card'>"
            "<h2>Release Trend Snapshot</h2>"
            "<ul>"
            f"{trend_link}"
            "<li><span class='k'>trend_total_days</span><span class='na'>N/A</span><span class='p'>trend summary not found</span></li>"
            "<li><span class='k'>trend_counts</span><span class='na'>N/A</span><span class='p'>release/review/hold unavailable</span></li>"
            "<li><span class='k'>latest_decision</span><span class='na'>N/A</span><span class='p'>N/A</span></li>"
            "</ul>"
            "</section>"
        )

    total_days = html.escape(str(summary.get("trend_total_days", "N/A")))
    release_count = html.escape(str(summary.get("trend_release_count", "N/A")))
    review_count = html.escape(str(summary.get("trend_review_count", "N/A")))
    hold_count = html.escape(str(summary.get("trend_hold_count", "N/A")))
    latest_decision = html.escape(str(summary.get("latest_decision", "N/A")))

    return (
        "<section class='card'>"
        "<h2>Release Trend Snapshot</h2>"
        "<ul>"
        f"{trend_link}"
        f"<li><span class='k'>trend_total_days</span><span>{total_days}</span><span class='p'>直近の日次判定数</span></li>"
        f"<li><span class='k'>trend_counts</span><span>release={release_count} review={review_count} hold={hold_count}</span><span class='p'>release/review/hold 集計</span></li>"
        f"<li><span class='k'>latest_decision</span><span>{latest_decision}</span><span class='p'>trend 最新日判定</span></li>"
        "</ul>"
        "</section>"
    )


def build_ops_home_html() -> str:
    """runbook/checklist/decision を統合した運用トップページを生成する。"""
    generated_at = _now_iso()
    idx = build_artifact_index(report_dir=DEFAULT_REPORT_DIR, archive_dir=DEFAULT_ARCHIVE_DIR)
    readiness = _load_release_readiness()
    trend_summary = _load_release_trend_summary()
    status_badge = load_latest_status_badge()

    decision = "N/A"
    action = "N/A"
    if readiness:
        decision = str(readiness.get("decision", "N/A"))
        action = str(readiness.get("recommended_action", "N/A"))

    nav_rows = "\n".join(
        [
            _item_html("Daily Checklist", str(DEFAULT_DAILY_CHECKLIST_PATH)),
            _item_html("Runbook", str(DEFAULT_RUNBOOK_PATH)),
            _item_html("Ops Decision Dashboard", idx.get("latest_ops_decision_dashboard") or str(DEFAULT_OPS_DECISION_DASHBOARD_PATH)),
            _item_html("Ops Portal", str(DEFAULT_OPS_PORTAL_PATH)),
            _item_html("Artifact Index", str(DEFAULT_ARTIFACT_INDEX_PATH)),
        ]
    )

    report_rows = "\n".join(
        [
            _item_html("Latest Daily Report", idx.get("latest_daily_report_json")),
            _item_html("Latest Weekly Report", idx.get("latest_weekly_report_json")),
            _item_html("Latest Monthly Report", idx.get("latest_monthly_report_json")),
            _item_html("Latest Archive", idx.get("latest_archive")),
        ]
    )

    trend_section = build_release_trend_summary_block(trend_summary)
    badge_section = build_status_badge_block(status_badge)

    return f"""<!DOCTYPE html>
<html lang=\"ja\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>AI Media OS Ops Home</title>
  <style>
    :root {{
      --bg: #f4f7f2;
      --card: #ffffff;
      --line: #d7dfd2;
      --ink: #1a2921;
      --muted: #5b6e62;
      --accent: #0e6b8a;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: linear-gradient(180deg, #f9fcf8, var(--bg));
      color: var(--ink);
      font-family: "Segoe UI", "Hiragino Kaku Gothic ProN", sans-serif;
    }}
    .wrap {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ margin: 0; font-size: 1.6rem; }}
    .meta {{ color: var(--muted); font-size: 0.86rem; margin-top: 6px; }}

    .hero {{
      margin-top: 16px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
      box-shadow: 0 1px 6px rgba(0, 30, 50, 0.07);
    }}
    .decision {{ font-size: 1.9rem; font-weight: 800; letter-spacing: 1px; margin: 0; }}
    .action {{ margin-top: 8px; padding-left: 10px; border-left: 3px solid var(--accent); font-weight: 600; }}

        .badge {{
            margin-top: 14px;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 14px 16px;
            box-shadow: 0 1px 6px rgba(0, 30, 50, 0.07);
        }}
        .badge-pill {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.04em;
        }}
        .level-ok {{ background: #e4f4e8; color: #1a6a34; }}
        .level-warning {{ background: #fff3d9; color: #8a5a00; }}
        .level-critical {{ background: #ffe2e0; color: #9a231c; }}
        .level-unknown {{ background: #edf1f5; color: #51606d; }}
        .badge-main {{ margin-top: 8px; font-size: 1.2rem; font-weight: 800; }}
        .badge-sub {{ margin-top: 6px; color: #3f5a4f; font-size: 0.86rem; }}

    .card {{
      margin-top: 14px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 16px;
    }}
    h2 {{ margin: 0 0 10px; font-size: 1.04rem; }}
    ul {{ list-style: none; margin: 0; padding: 0; }}
    li {{
      display: grid;
      grid-template-columns: 220px minmax(180px, 1fr);
      gap: 8px 12px;
      padding: 8px 0;
      border-bottom: 1px dashed var(--line);
    }}
    li:last-child {{ border-bottom: none; }}
    .k {{ color: var(--muted); }}
    a {{ color: var(--accent); text-decoration: none; font-weight: 700; }}
    a:hover {{ text-decoration: underline; }}
    .p {{ grid-column: 2; color: #3f5a4f; font-family: ui-monospace, monospace; font-size: 0.81rem; word-break: break-all; }}
    .na {{ color: #8a988f; font-style: italic; }}

    @media (max-width: 720px) {{
      li {{ grid-template-columns: 1fr; }}
      .p {{ grid-column: 1; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>AI Media OS Ops Home</h1>
    <div class=\"meta\">generated_at: {html.escape(generated_at)}</div>

        {badge_section}

    <section class=\"hero\">
      <h2>Today's Decision</h2>
      <p class=\"decision\">{html.escape(decision.upper())}</p>
      <div class=\"action\">recommended_action: {html.escape(action)}</div>
    </section>

    <section class=\"card\">
      <h2>Quick Links</h2>
      <ul>
{nav_rows}
      </ul>
    </section>

    <section class=\"card\">
      <h2>Latest Reports</h2>
      <ul>
{report_rows}
      </ul>
    </section>

    {trend_section}
  </div>
</body>
</html>
"""
