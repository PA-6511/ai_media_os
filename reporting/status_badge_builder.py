from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_OUTPUT_JSON_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.json"
DEFAULT_OUTPUT_HTML_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.html"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def _to_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_decision(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"release", "review", "hold"}:
        return text.upper()
    return "N/A"


def _health_grade_from_score(score: int | None) -> str:
    if score is None:
        return "N/A"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def _normalize_health_grade(value: Any, health_score: int | None) -> str:
    text = str(value or "").strip().upper()
    if text in {"A", "B", "C", "D"}:
        return text
    return _health_grade_from_score(health_score)


def _normalize_anomaly(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"OK", "PASS", "NONE", "NORMAL"}:
        return "OK"
    if text == "WARNING":
        return "WARNING"
    if text in {"CRITICAL", "FAIL", "FAILED", "ERROR"}:
        return "CRITICAL"
    return "N/A"


def _badge_level(decision: str, anomaly_overall: str, health_grade: str, health_score: int | None) -> str:
    if decision == "HOLD" or anomaly_overall == "CRITICAL":
        return "critical"
    if health_grade == "D" or (health_score is not None and health_score < 60):
        return "critical"
    if decision == "REVIEW" or anomaly_overall == "WARNING":
        return "warning"
    if health_grade == "C" or (health_score is not None and health_score < 80):
        return "warning"
    if decision == "RELEASE" and anomaly_overall == "OK":
        return "ok"
    return "unknown"


def build_status_badge() -> dict[str, Any]:
    readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH) or {}

    decision = _normalize_decision(readiness.get("decision"))
    health_score = _to_int(readiness.get("health_score"))
    health_grade = _normalize_health_grade(readiness.get("health_grade"), health_score)
    anomaly_overall = _normalize_anomaly(readiness.get("anomaly_overall"))
    badge_level = _badge_level(decision, anomaly_overall, health_grade, health_score)

    badge_text = f"{decision} | Health {health_grade} | {anomaly_overall}"

    return {
        "generated_at": _now_iso(),
        "decision": decision,
        "health_score": health_score,
        "health_grade": health_grade,
        "anomaly_overall": anomaly_overall,
        "badge_text": badge_text,
        "badge_level": badge_level,
        "source": {
            "release_readiness_json": str(DEFAULT_RELEASE_READINESS_JSON_PATH)
            if DEFAULT_RELEASE_READINESS_JSON_PATH.exists()
            else None,
        },
    }


def build_status_badge_html(badge: dict[str, Any]) -> str:
    generated_at = html.escape(str(badge.get("generated_at", "N/A")))
    decision = html.escape(str(badge.get("decision", "N/A")))
    health_score = html.escape(str(badge.get("health_score", "N/A")))
    health_grade = html.escape(str(badge.get("health_grade", "N/A")))
    anomaly_overall = html.escape(str(badge.get("anomaly_overall", "N/A")))
    badge_text = html.escape(str(badge.get("badge_text", "N/A")))
    badge_level = html.escape(str(badge.get("badge_level", "unknown")))

    return f"""<style>
.ai-media-status-badge {{
  --badge-ok-bg: #e4f4e8;
  --badge-ok-ink: #1a6a34;
  --badge-warning-bg: #fff3d9;
  --badge-warning-ink: #8a5a00;
  --badge-critical-bg: #ffe2e0;
  --badge-critical-ink: #9a231c;
  --badge-unknown-bg: #edf1f5;
  --badge-unknown-ink: #51606d;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  color: #1f2d24;
  font-family: "Segoe UI", "Hiragino Kaku Gothic ProN", sans-serif;
  box-shadow: 0 1px 4px rgba(0, 24, 30, 0.08);
}}
.ai-media-status-badge[data-level="ok"] {{ border-color: #bddcc4; }}
.ai-media-status-badge[data-level="warning"] {{ border-color: #ecd28e; }}
.ai-media-status-badge[data-level="critical"] {{ border-color: #efb3ad; }}
.ai-media-status-badge[data-level="unknown"] {{ border-color: #cfd6de; }}
.ai-media-status-badge .pill {{
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}}
.ai-media-status-badge .text {{
  font-size: 0.95rem;
  font-weight: 700;
}}
.ai-media-status-badge .meta {{
  font-size: 0.75rem;
  color: #5d6f63;
}}
.ai-media-status-badge[data-level="ok"] .pill {{ background: var(--badge-ok-bg); color: var(--badge-ok-ink); }}
.ai-media-status-badge[data-level="warning"] .pill {{ background: var(--badge-warning-bg); color: var(--badge-warning-ink); }}
.ai-media-status-badge[data-level="critical"] .pill {{ background: var(--badge-critical-bg); color: var(--badge-critical-ink); }}
.ai-media-status-badge[data-level="unknown"] .pill {{ background: var(--badge-unknown-bg); color: var(--badge-unknown-ink); }}
</style>
<div class="ai-media-status-badge" data-level="{badge_level}" data-decision="{decision}" data-health-grade="{health_grade}" data-anomaly-overall="{anomaly_overall}">
  <span class="pill">{decision}</span>
  <span class="text">{badge_text}</span>
  <span class="meta">score={health_score} / generated_at={generated_at}</span>
</div>
"""
