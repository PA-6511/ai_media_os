from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"
DEFAULT_RELEASE_READINESS_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_RELEASE_READINESS_MD_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.md"
DEFAULT_OUTPUT_PATH = DEFAULT_REPORT_DIR / "ops_decision_dashboard_latest.html"
DEFAULT_DAILY_CHECKLIST_PATH = DOCS_DIR / "daily_checklist_latest.md"
DEFAULT_OPS_PORTAL_PATH = DEFAULT_REPORT_DIR / "ops_portal_latest.html"
DEFAULT_ARTIFACT_INDEX_PATH = DEFAULT_REPORT_DIR / "artifact_index_latest.html"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_href(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return os.path.relpath(str(path), start=str(DEFAULT_REPORT_DIR)).replace("\\", "/")
    except Exception:
        return None


def _decision_class(decision: str) -> str:
    d = decision.strip().lower()
    if d == "release":
        return "decision-release"
    if d == "review":
        return "decision-review"
    if d == "hold":
        return "decision-hold"
    return "decision-unknown"


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _primary_cards(summary: dict[str, Any]) -> str:
    generated_at = html.escape(str(summary.get("generated_at", "N/A")))
    anomaly_overall = html.escape(str(summary.get("anomaly_overall", "N/A")))
    health_score = html.escape(str(summary.get("health_score", "N/A")))
    health_grade = html.escape(str(summary.get("health_grade", "N/A")))
    retry_queued = html.escape(str(summary.get("retry_queued", "N/A")))
    integrity_overall = html.escape(str(summary.get("integrity_overall", "N/A")))

    return f"""
    <div class=\"grid\">
      <article class=\"card\"><h3>Generated At</h3><p>{generated_at}</p></article>
      <article class=\"card\"><h3>Anomaly</h3><p>{anomaly_overall}</p></article>
      <article class=\"card\"><h3>Health</h3><p>{health_score} ({health_grade})</p></article>
      <article class=\"card\"><h3>Retry Queued</h3><p>{retry_queued}</p></article>
      <article class=\"card\"><h3>Integrity</h3><p>{integrity_overall}</p></article>
    </div>
    """


def _reasons_html(summary: dict[str, Any]) -> str:
    reasons = summary.get("reasons") if isinstance(summary.get("reasons"), list) else []
    if not reasons:
        return "<li>No reasons available</li>"
    return "\n".join(f"<li>{html.escape(str(reason))}</li>" for reason in reasons)


def _links_html() -> str:
    links: list[tuple[str, Path]] = [
        ("Daily Checklist", DEFAULT_DAILY_CHECKLIST_PATH),
        ("Ops Portal", DEFAULT_OPS_PORTAL_PATH),
        ("Artifact Index", DEFAULT_ARTIFACT_INDEX_PATH),
        ("Release Readiness JSON", DEFAULT_RELEASE_READINESS_PATH),
        ("Release Readiness Markdown", DEFAULT_RELEASE_READINESS_MD_PATH),
    ]

    items: list[str] = []
    for label, target in links:
        exists = target.exists() and target.is_file()
        href = _to_href(target)
        if exists and href:
            items.append(
                "<li>"
                f"<a href='{html.escape(href)}' target='_blank' rel='noopener'>{html.escape(label)}</a>"
                f"<span>{html.escape(str(target))}</span>"
                "</li>"
            )
        else:
            items.append(
                "<li>"
                f"<span>{html.escape(label)}</span>"
                "<span>not found</span>"
                "</li>"
            )

    return "\n".join(items)


def load_latest_release_readiness() -> dict | None:
    """最新の release_readiness_latest.json を読み込む。"""
    path = DEFAULT_RELEASE_READINESS_PATH
    if not path.exists() or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def _fallback_summary() -> dict[str, Any]:
    return {
        "generated_at": _now_iso(),
        "decision": "unknown",
        "anomaly_overall": "N/A",
        "health_score": "N/A",
        "health_grade": "N/A",
        "retry_queued": "N/A",
        "integrity_overall": "N/A",
        "reasons": ["release_readiness_latest.json が見つからないため判定不能"],
        "recommended_action": "ops.run_release_readiness_check を実行して最新判定を生成",
        "anomaly_alert_total": 0,
        "anomaly_warning_count": 0,
        "anomaly_critical_count": 0,
        "integrity_pass_count": 0,
        "integrity_warning_count": 0,
        "integrity_fail_count": 0,
    }


def build_ops_decision_dashboard_html(summary: dict | None) -> str:
    """運用判定専用の軽量HTMLダッシュボードを生成する。"""
    source = summary if isinstance(summary, dict) else _fallback_summary()

    decision = str(source.get("decision", "unknown")).upper()
    decision_css = _decision_class(str(source.get("decision", "unknown")))
    recommended_action = html.escape(str(source.get("recommended_action", "N/A")))

    anomaly_alert_total = _safe_int(source.get("anomaly_alert_total"), 0)
    anomaly_warning_count = _safe_int(source.get("anomaly_warning_count"), 0)
    anomaly_critical_count = _safe_int(source.get("anomaly_critical_count"), 0)
    integrity_pass_count = _safe_int(source.get("integrity_pass_count"), 0)
    integrity_warning_count = _safe_int(source.get("integrity_warning_count"), 0)
    integrity_fail_count = _safe_int(source.get("integrity_fail_count"), 0)

    primary_cards = _primary_cards(source)
    reasons = _reasons_html(source)
    links = _links_html()

    return f"""<!DOCTYPE html>
<html lang=\"ja\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>AI Media OS Ops Decision Dashboard</title>
  <style>
    :root {{
      --paper: #f4f8f5;
      --ink: #18231f;
      --muted: #4d6158;
      --line: #c8d6cd;
      --card: #ffffff;
      --release: #0b8f46;
      --review: #bf8a00;
      --hold: #b32a2a;
      --unknown: #2f4f66;
      --accent: #0a5e7a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "IBM Plex Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
      background:
        radial-gradient(circle at 12% 15%, #ddeee2 0%, transparent 28%),
        radial-gradient(circle at 90% 12%, #d8e8f0 0%, transparent 30%),
        linear-gradient(180deg, #f9fdf8 0%, var(--paper) 100%);
      padding: 24px 16px 32px;
    }}
    .wrap {{ max-width: 1040px; margin: 0 auto; }}
    h1 {{ margin: 0; font-size: 1.72rem; letter-spacing: 0.2px; }}
    .sub {{ margin-top: 8px; color: var(--muted); font-size: 0.92rem; }}

    .hero {{
      margin-top: 18px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 8px 22px rgba(15, 53, 36, 0.08);
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }}
    .decision-badge {{
      display: inline-block;
      padding: 10px 16px;
      border-radius: 999px;
      font-size: 2rem;
      line-height: 1;
      font-weight: 800;
      letter-spacing: 1.4px;
      color: #fff;
      width: fit-content;
      animation: fade-in 420ms ease-out;
    }}
    .decision-release {{ background: linear-gradient(135deg, #0b8f46, #26b267); }}
    .decision-review {{ background: linear-gradient(135deg, #b37a00, #dba11e); }}
    .decision-hold {{ background: linear-gradient(135deg, #9f2424, #d03f3f); }}
    .decision-unknown {{ background: linear-gradient(135deg, #315870, #4f7b95); }}

    .action {{
      border-left: 4px solid var(--accent);
      background: #f4fbff;
      padding: 10px 12px;
      border-radius: 10px;
      font-weight: 600;
    }}

    .grid {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
    }}
    .card h3 {{ margin: 0; font-size: 0.84rem; color: var(--muted); font-weight: 600; }}
    .card p {{ margin: 8px 0 2px; font-size: 1.04rem; font-weight: 700; }}

    .section {{
      margin-top: 14px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
    }}
    .section h2 {{ margin: 0 0 10px; font-size: 1.02rem; }}

    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 6px 0; }}

    .metrics {{
      margin-top: 8px;
      display: grid;
      grid-template-columns: repeat(2, minmax(180px, 1fr));
      gap: 10px;
    }}
    .metrics pre {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #f7fbf8;
      padding: 10px 12px;
      font-family: "IBM Plex Mono", "Consolas", monospace;
      font-size: 0.86rem;
      white-space: pre-wrap;
      line-height: 1.5;
    }}

    .links {{ list-style: none; margin: 0; padding: 0; }}
    .links li {{
      display: grid;
      grid-template-columns: minmax(180px, 260px) 1fr;
      gap: 10px;
      padding: 6px 0;
      border-bottom: 1px dashed var(--line);
    }}
    .links li:last-child {{ border-bottom: none; }}
    .links a {{ color: #0d5ca3; text-decoration: none; font-weight: 700; }}
    .links a:hover {{ text-decoration: underline; }}
    .links span {{ color: var(--muted); font-family: "IBM Plex Mono", "Consolas", monospace; font-size: 0.8rem; word-break: break-all; }}

    @keyframes fade-in {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(140px, 1fr)); }}
      .metrics {{ grid-template-columns: 1fr; }}
      .links li {{ grid-template-columns: 1fr; }}
    }}

    @media (max-width: 560px) {{
      .decision-badge {{ font-size: 1.6rem; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>AI Media OS Ops Decision Dashboard</h1>
    <div class=\"sub\">today-focused view / generated for rapid operational judgment</div>

    <section class=\"hero\">
      <div class=\"decision-badge {decision_css}\">{html.escape(decision)}</div>
      <div class=\"action\">recommended_action: {recommended_action}</div>
    </section>

    {primary_cards}

    <section class=\"section\">
      <h2>Reasons</h2>
      <ul>
        {reasons}
      </ul>
    </section>

    <section class=\"section\">
      <h2>Anomaly / Integrity Counts</h2>
      <div class=\"metrics\">
        <pre>alert_total      : {anomaly_alert_total}
warning_count   : {anomaly_warning_count}
critical_count  : {anomaly_critical_count}</pre>
        <pre>integrity PASS   : {integrity_pass_count}
integrity WARNING: {integrity_warning_count}
integrity FAIL   : {integrity_fail_count}</pre>
      </div>
    </section>

    <section class=\"section\">
      <h2>Related Links</h2>
      <ul class=\"links\">
        {links}
      </ul>
    </section>
  </div>
</body>
</html>
"""
