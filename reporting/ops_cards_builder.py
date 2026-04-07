from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_MANIFEST_PATH = DEFAULT_REPORT_DIR / "ops_manifest_latest.json"
DEFAULT_STATUS_LIGHT_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_RELEASE_READINESS_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
SCHEMA_VERSION = "1.0"


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


def _normalize_path(value: Any) -> str | None:
    if not value:
        return None

    path_text = str(value).strip()
    if not path_text:
        return None

    p = Path(path_text)
    if p.is_absolute():
        try:
            return str(p.relative_to(BASE_DIR)).replace("\\", "/")
        except ValueError:
            return str(p)

    resolved = (BASE_DIR / path_text).resolve()
    if resolved.exists():
        try:
            return str(resolved.relative_to(BASE_DIR)).replace("\\", "/")
        except ValueError:
            return str(resolved)

    return path_text.replace("\\", "/")


def _str_or_na(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else "N/A"


def _card(title: str, subtitle: str, status: Any, path: Any) -> dict[str, Any]:
    return {
        "title": title,
        "subtitle": subtitle,
        "status": _str_or_na(status),
        "path": _normalize_path(path),
    }


def build_ops_cards() -> dict[str, Any]:
    manifest = _safe_read_json(DEFAULT_MANIFEST_PATH) or {}
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_PATH) or {}
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_PATH) or {}

    decision = status_light.get("decision") or release_readiness.get("decision")
    badge_text = status_light.get("badge_text")
    health_grade = status_light.get("health_grade") or release_readiness.get("health_grade")
    anomaly_overall = status_light.get("anomaly_overall") or release_readiness.get("anomaly_overall")
    recommended_action = status_light.get("recommended_action") or release_readiness.get("recommended_action")

    cards = [
        _card(
            "Today's Decision",
            "release / review / hold",
            decision,
            manifest.get("ops_portal_html"),
        ),
        _card(
            "Status Badge",
            _str_or_na(badge_text),
            decision,
            manifest.get("status_badge_json"),
        ),
        _card(
            "Daily Checklist",
            "daily operations checklist",
            "READY",
            manifest.get("daily_checklist_md"),
        ),
        _card(
            "Ops Portal",
            "operations portal overview",
            anomaly_overall,
            manifest.get("ops_portal_html"),
        ),
        _card(
            "Ops Home",
            "runbook and quick links",
            decision,
            manifest.get("ops_home_html"),
        ),
        _card(
            "Latest Daily Dashboard",
            "daily metrics dashboard",
            health_grade,
            manifest.get("daily_dashboard_html"),
        ),
        _card(
            "Latest Weekly Dashboard",
            "weekly metrics dashboard",
            "READY",
            manifest.get("weekly_dashboard_html"),
        ),
        _card(
            "Latest Monthly Dashboard",
            "monthly metrics dashboard",
            "READY",
            manifest.get("monthly_dashboard_html"),
        ),
        _card(
            "Latest Archive",
            "latest backup archive",
            "AVAILABLE" if status_light.get("latest_archive") else "N/A",
            status_light.get("latest_archive"),
        ),
        _card(
            "Latest Summary JSON",
            "ops summary aggregate",
            decision,
            manifest.get("ops_summary"),
        ),
        _card(
            "Runbook",
            _str_or_na(recommended_action),
            "READY",
            manifest.get("runbook_md"),
        ),
    ]

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "cards": cards,
    }
