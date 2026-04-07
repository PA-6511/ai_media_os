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
DEFAULT_CHECKLIST_PATH = DOCS_DIR / "daily_checklist_latest.md"
DEFAULT_RUNBOOK_PATH = DOCS_DIR / "runbook_latest.md"
DEFAULT_OPS_DECISION_DASHBOARD_PATH = DEFAULT_REPORT_DIR / "ops_decision_dashboard_latest.html"
DEFAULT_RELEASE_TREND_MD_PATH = DEFAULT_REPORT_DIR / "release_readiness_trend_latest.md"
DEFAULT_STATUS_BADGE_JSON_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _exists(path_str: str | None) -> bool:
    if not path_str:
        return False
    return Path(path_str).exists()


def _to_href(path_str: str | None) -> str | None:
    if not path_str:
        return None
    path = Path(path_str)
    try:
        return os.path.relpath(str(path), start=str(DEFAULT_REPORT_DIR)).replace("\\", "/")
    except Exception:
        return None


def _item_html(label: str, path_str: str | None) -> str:
    if path_str and _exists(path_str):
        href = _to_href(path_str)
        name = html.escape(Path(path_str).name)
        path_text = html.escape(path_str)
        if href:
            return (
                f"<li><span class='k'>{html.escape(label)}</span>"
                f"<a href='{html.escape(href)}' target='_blank' rel='noopener'>{name}</a>"
                f"<span class='p'>{path_text}</span></li>"
            )
    return (
        f"<li><span class='k'>{html.escape(label)}</span>"
        "<span class='na'>N/A</span>"
        "<span class='p'>not found</span></li>"
    )


def load_latest_release_readiness_summary(path_str: str | None) -> dict | None:
    """release_readiness_latest.json を読み込み、dict を返す。"""
    if not path_str:
        return None
    path = Path(path_str)
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


def build_status_badge_section(badge: dict | None) -> str:
    """ステータスバッジのセクション HTML 断片を返す。"""
    if not badge:
        rows = [
            "<li><span class='k'>badge_text</span><span class='na'>N/A | Health N/A | N/A</span><span class='p'>status badge not found</span></li>",
            "<li><span class='k'>badge_level</span><span class='na'>unknown</span><span class='p'>N/A</span></li>",
            "<li><span class='k'>decision / health / anomaly</span><span class='na'>N/A</span><span class='p'>decision=N/A health=N/A anomaly=N/A</span></li>",
        ]
        return "\n".join(rows)

    badge_text = html.escape(str(badge.get("badge_text", "N/A")))
    badge_level = html.escape(str(badge.get("badge_level", "unknown")))
    decision = html.escape(str(badge.get("decision", "N/A")))
    health_score = html.escape(str(badge.get("health_score", "N/A")))
    health_grade = html.escape(str(badge.get("health_grade", "N/A")))
    anomaly_overall = html.escape(str(badge.get("anomaly_overall", "N/A")))

    rows = [
        f"<li><span class='k'>badge_text</span><span><strong>{badge_text}</strong></span><span class='p'>一目で状態把握できる短縮表示</span></li>",
        f"<li><span class='k'>badge_level</span><span>{badge_level}</span><span class='p'>ok/warning/critical/unknown</span></li>",
        (
            "<li><span class='k'>decision / health / anomaly</span>"
            f"<span>{decision} / {health_score} ({health_grade}) / {anomaly_overall}</span>"
            f"<span class='p'>decision={decision} health_score={health_score} health_grade={health_grade} anomaly_overall={anomaly_overall}</span></li>"
        ),
    ]
    return "\n".join(rows)


def load_latest_release_readiness_trend_summary() -> dict | None:
    """release_readiness_trend_latest.md から主要サマリーを抽出する。"""
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

        if text.startswith("generated_at:"):
            parsed["generated_at"] = text.split(":", 1)[1].strip()
        elif text.startswith("total_days:"):
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


def build_release_readiness_section(summary: dict | None) -> str:
    """release readiness の decision/recommended_action を HTML 断片で返す。"""
    decision_dashboard_path = str(DEFAULT_OPS_DECISION_DASHBOARD_PATH)
    dashboard_row = _item_html("Ops Decision Dashboard", decision_dashboard_path)

    if not summary:
        rows = [
            "<li><span class='k'>Release Decision</span><span class='na'>N/A</span><span class='p'>release readiness not found</span></li>",
            "<li><span class='k'>Recommended Action</span><span class='na'>N/A</span><span class='p'>N/A</span></li>",
            dashboard_row,
        ]
        return "\n".join(rows)

    decision = html.escape(str(summary.get("decision", "N/A")))
    action = html.escape(str(summary.get("recommended_action", "N/A")))
    reasons = summary.get("reasons") if isinstance(summary.get("reasons"), list) else []
    reason_text = " | ".join(str(r) for r in reasons[:3]) if reasons else "N/A"
    reason_text = html.escape(reason_text)

    rows = [
        f"<li><span class='k'>Release Decision</span><span>{decision}</span><span class='p'>today readiness decision</span></li>",
        f"<li><span class='k'>Recommended Action</span><span>{action}</span><span class='p'>{reason_text}</span></li>",
        dashboard_row,
    ]
    return "\n".join(rows)


def build_release_trend_section(summary: dict | None) -> str:
    """release readiness trend の要約を HTML 断片で返す。"""
    trend_path = str(DEFAULT_RELEASE_TREND_MD_PATH)
    trend_row = _item_html("Release Readiness Trend (MD)", trend_path)

    if not summary:
        rows = [
            trend_row,
            "<li><span class='k'>trend_total_days</span><span class='na'>N/A</span><span class='p'>trend summary not found</span></li>",
            "<li><span class='k'>trend_counts</span><span class='na'>N/A</span><span class='p'>release/review/hold unavailable</span></li>",
            "<li><span class='k'>latest_decision</span><span class='na'>N/A</span><span class='p'>N/A</span></li>",
        ]
        return "\n".join(rows)

    total_days = html.escape(str(summary.get("trend_total_days", "N/A")))
    release_count = html.escape(str(summary.get("trend_release_count", "N/A")))
    review_count = html.escape(str(summary.get("trend_review_count", "N/A")))
    hold_count = html.escape(str(summary.get("trend_hold_count", "N/A")))
    latest_decision = html.escape(str(summary.get("latest_decision", "N/A")))

    rows = [
        trend_row,
        f"<li><span class='k'>trend_total_days</span><span>{total_days}</span><span class='p'>直近の日次判定数</span></li>",
        (
            "<li><span class='k'>trend_counts</span>"
            f"<span>release={release_count} review={review_count} hold={hold_count}</span>"
            "<span class='p'>release/review/hold 集計</span></li>"
        ),
        f"<li><span class='k'>latest_decision</span><span>{latest_decision}</span><span class='p'>trend 最新日判定</span></li>",
    ]
    return "\n".join(rows)


def build_ops_portal_html() -> str:
    """運用成果物への導線をまとめた HTML ポータルを生成する。"""
    idx = build_artifact_index(report_dir=DEFAULT_REPORT_DIR, archive_dir=DEFAULT_ARCHIVE_DIR)

    generated_at = _now_iso()

    latest_daily_dashboard = idx.get("latest_dashboard")
    latest_weekly_dashboard = idx.get("latest_weekly_dashboard")
    latest_monthly_dashboard = idx.get("latest_monthly_dashboard")
    latest_ops_decision_dashboard = idx.get("latest_ops_decision_dashboard")
    latest_artifact_index = str(DEFAULT_REPORT_DIR / "artifact_index_latest.html")

    latest_daily_report = idx.get("latest_daily_report_json")
    latest_weekly_report = idx.get("latest_weekly_report_json")
    latest_monthly_report = idx.get("latest_monthly_report_json")
    latest_archive = idx.get("latest_archive")
    latest_release_readiness_json = idx.get("latest_release_readiness_json")
    latest_release_readiness_md = idx.get("latest_release_readiness_md")
    latest_release_trend_md = str(DEFAULT_RELEASE_TREND_MD_PATH)

    daily_checklist = str(DEFAULT_CHECKLIST_PATH)
    runbook = str(DEFAULT_RUNBOOK_PATH)
    release_summary = load_latest_release_readiness_summary(latest_release_readiness_json)
    badge_summary = load_latest_status_badge()
    trend_summary = load_latest_release_readiness_trend_summary()
    badge_section = build_status_badge_section(badge_summary)
    release_section = build_release_readiness_section(release_summary)
    release_trend_section = build_release_trend_section(trend_summary)

    links_section = "\n".join(
        [
            _item_html("Daily Dashboard", latest_daily_dashboard),
            _item_html("Weekly Dashboard", latest_weekly_dashboard),
            _item_html("Monthly Dashboard", latest_monthly_dashboard),
            _item_html("Ops Decision Dashboard", latest_ops_decision_dashboard),
            _item_html("Artifact Index", latest_artifact_index),
            _item_html("Release Readiness (JSON)", latest_release_readiness_json),
            _item_html("Release Readiness (MD)", latest_release_readiness_md),
            _item_html("Release Readiness Trend (MD)", latest_release_trend_md),
            _item_html("Daily Checklist", daily_checklist),
            _item_html("Runbook", runbook),
        ]
    )

    latest_section = "\n".join(
        [
            _item_html("Latest Daily Report", latest_daily_report),
            _item_html("Latest Weekly Report", latest_weekly_report),
            _item_html("Latest Monthly Report", latest_monthly_report),
            _item_html("Latest Archive", latest_archive),
            _item_html("Latest Ops Decision Dashboard", latest_ops_decision_dashboard),
            _item_html("Latest Release Readiness JSON", latest_release_readiness_json),
            _item_html("Latest Release Readiness MD", latest_release_readiness_md),
            _item_html("Latest Release Readiness Trend MD", latest_release_trend_md),
        ]
    )

    return f"""<!DOCTYPE html>
<html lang=\"ja\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>AI Media OS Ops Portal</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --card: #ffffff;
      --line: #dbe3ee;
      --ink: #1c2a39;
      --muted: #5f7086;
      --accent: #1f6feb;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: linear-gradient(180deg, #f8fbff, var(--bg));
      color: var(--ink);
      font-family: "Segoe UI", "Hiragino Kaku Gothic ProN", sans-serif;
    }}
    .wrap {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ margin: 0 0 6px; font-size: 1.5rem; }}
    .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 16px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 14px;
      box-shadow: 0 1px 6px rgba(0, 32, 80, 0.06);
    }}
    h2 {{ margin: 0 0 10px; font-size: 1.05rem; }}
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
    a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
    a:hover {{ text-decoration: underline; }}
    .p {{ grid-column: 2; font-family: ui-monospace, monospace; font-size: 0.82rem; color: #3a4f6a; word-break: break-all; }}
    .na {{ color: #8a97a8; font-style: italic; }}
    @media (max-width: 700px) {{
      li {{ grid-template-columns: 1fr; }}
      .p {{ grid-column: 1; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>AI Media OS Ops Portal</h1>
    <div class=\"meta\">generated_at: {html.escape(generated_at)}</div>

        <section class=\"card\">
            <h2>Status Badge</h2>
            <ul>
{badge_section}
            </ul>
        </section>

    <section class=\"card\">
      <h2>Navigation</h2>
      <ul>
{links_section}
      </ul>
    </section>

    <section class=\"card\">
      <h2>Latest Artifacts</h2>
      <ul>
{latest_section}
      </ul>
    </section>

    <section class=\"card\">
      <h2>Release Readiness</h2>
      <ul>
{release_section}
      </ul>
    </section>

        <section class="card">
            <h2>Release Readiness Trend</h2>
            <ul>
{release_trend_section}
            </ul>
        </section>
  </div>
</body>
</html>
"""
