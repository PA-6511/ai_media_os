from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "data" / "reports"
DOCS_DIR = BASE_DIR / "docs"

DEFAULT_BOOTSTRAP_PATH = REPORT_DIR / "ops_bootstrap_latest.json"
DEFAULT_MOCK_API_PATH = REPORT_DIR / "mock_api_home_latest.json"
DEFAULT_GUI_PREVIEW_PATH = REPORT_DIR / "ops_gui_preview_latest.html"
DEFAULT_GUI_HANDOFF_PATH = REPORT_DIR / "ops_gui_handoff_latest.json"
DEFAULT_GUI_SCHEMA_PATH = REPORT_DIR / "ops_gui_schema_latest.json"
DEFAULT_GUI_HEALTH_PATH = REPORT_DIR / "ops_gui_health_latest.json"
DEFAULT_DECISION_SUMMARY_PATH = REPORT_DIR / "ops_decision_summary_latest.json"
DEFAULT_RELEASE_READINESS_PATH = REPORT_DIR / "release_readiness_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _check_line(label: str, ok: bool, detail: str) -> str:
    mark = "[x]" if ok else "[ ]"
    return f"- {mark} {label}: {detail}"


def _exists_detail(path: Path) -> tuple[bool, str]:
    if path.exists() and path.is_file():
        return True, str(path)
    return False, f"missing ({path})"


def _next_actions(decision_summary: dict[str, Any], gui_health: dict[str, Any], release_readiness: dict[str, Any]) -> list[str]:
    actions: list[str] = []

    recommended_action = str(decision_summary.get("recommended_action") or "").strip()
    if recommended_action:
        actions.append(recommended_action)

    anomaly = str(gui_health.get("anomaly_overall") or "N/A").upper()
    if anomaly in {"WARNING", "CRITICAL", "FAIL"}:
        actions.append("anomaly 状態を確認し、GUI 公開前に warning/critical の内容をレビュー")

    readiness_decision = str(release_readiness.get("decision") or decision_summary.get("decision") or "review").lower()
    if readiness_decision in {"review", "hold", "block", "critical"}:
        actions.append("release readiness を再確認し、go-live 判定を更新")

    if not actions:
        actions.append("GUI 運用開始可。初回ポーリングと mock API 疎通のみ最終確認")

    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def build_gui_go_live_checklist_markdown() -> str:
    gui_health = _safe_read_json(DEFAULT_GUI_HEALTH_PATH)
    decision_summary = _safe_read_json(DEFAULT_DECISION_SUMMARY_PATH)
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_PATH)
    gui_handoff = _safe_read_json(DEFAULT_GUI_HANDOFF_PATH)

    bootstrap_ok, bootstrap_detail = _exists_detail(DEFAULT_BOOTSTRAP_PATH)
    mock_api_ok, mock_api_detail = _exists_detail(DEFAULT_MOCK_API_PATH)
    preview_ok, preview_detail = _exists_detail(DEFAULT_GUI_PREVIEW_PATH)
    handoff_ok, handoff_detail = _exists_detail(DEFAULT_GUI_HANDOFF_PATH)
    schema_ok, schema_detail = _exists_detail(DEFAULT_GUI_SCHEMA_PATH)

    anomaly_overall = str(gui_health.get("anomaly_overall") or "N/A")
    health_score = gui_health.get("health_score")
    health_grade = gui_health.get("health_grade")
    health_ok = bool(gui_health.get("ok"))
    alert_count = int((gui_health.get("alert_count") or 0))

    readiness_decision = str(release_readiness.get("decision") or decision_summary.get("decision") or "N/A")
    decision = str(decision_summary.get("decision") or "N/A")
    severity = str(decision_summary.get("severity") or "N/A")
    reason = str(decision_summary.get("reason") or "N/A")
    recommended_action = str(decision_summary.get("recommended_action") or release_readiness.get("recommended_action") or "N/A")

    read_order = gui_handoff.get("read_order") if isinstance(gui_handoff.get("read_order"), list) else []
    next_actions = _next_actions(decision_summary, gui_health, release_readiness)

    lines: list[str] = []
    lines.append("# AI Media OS GUI Go-Live Checklist")
    lines.append("")
    lines.append(f"generated_at: {_now_iso()}")
    lines.append("")
    lines.append("## GUI成果物存在確認")
    lines.append("")
    lines.append(_check_line("bootstrap generated", bootstrap_ok, bootstrap_detail))
    lines.append(_check_line("gui schema generated", schema_ok, schema_detail))
    lines.append(_check_line("gui preview generated", preview_ok, preview_detail))
    lines.append(_check_line("handoff package generated", handoff_ok, handoff_detail))
    lines.append("")
    lines.append("## Mock API 準備状況")
    lines.append("")
    lines.append(_check_line("mock api json ready", mock_api_ok, mock_api_detail))
    lines.append(f"- read_order_count: {len(read_order)}")
    lines.append("- first_read_assets:")
    if read_order:
        for path in read_order[:5]:
            lines.append(f"  - {path}")
    else:
        lines.append("  - N/A")
    lines.append("")
    lines.append("## 運用判断")
    lines.append("")
    lines.append(f"- anomaly_overall: {anomaly_overall}")
    lines.append(f"- health: {health_score} ({health_grade})")
    lines.append(f"- gui_health_ok: {health_ok}")
    lines.append(f"- alert_count: {alert_count}")
    lines.append(f"- release_readiness: {readiness_decision}")
    lines.append(f"- gui_decision: {decision}")
    lines.append(f"- severity: {severity}")
    lines.append(f"- reason: {reason}")
    lines.append(f"- recommended_action: {recommended_action}")
    lines.append("")
    lines.append("## Check Items")
    lines.append("")
    lines.append(f"- anomaly が OK または WARNING: {'YES' if anomaly_overall in {'OK', 'WARNING'} else 'NO'}")
    lines.append(f"- release readiness が release / review / hold のいずれか: {'YES' if readiness_decision.lower() in {'release', 'review', 'hold'} else 'NO'}")
    lines.append(f"- mock API 用 JSON が生成済み: {'YES' if mock_api_ok else 'NO'}")
    lines.append(f"- GUI preview が生成済み: {'YES' if preview_ok else 'NO'}")
    lines.append(f"- handoff package が生成済み: {'YES' if handoff_ok else 'NO'}")
    lines.append("")
    lines.append("## Next Action")
    lines.append("")
    for action in next_actions:
        lines.append(f"- {action}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"