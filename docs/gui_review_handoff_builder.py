from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "data" / "reports"

DEFAULT_GUI_HANDOFF_PATH = REPORT_DIR / "ops_gui_handoff_latest.json"
DEFAULT_GUI_INTEGRITY_PATH = REPORT_DIR / "ops_gui_integrity_latest.json"
DEFAULT_GUI_HEALTH_PATH = REPORT_DIR / "ops_gui_health_latest.json"
DEFAULT_ARTIFACT_TIMESTAMPS_PATH = REPORT_DIR / "ops_artifact_timestamps_latest.json"


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


def _path_or_na(value: Any) -> str:
    raw = str(value or "").strip()
    return raw if raw else "N/A"


def _find_updated_at(payload: dict[str, Any], key: str) -> str:
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), list) else []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        if str(item.get("key") or "") == key:
            return str(item.get("updated_at") or "N/A")
    return "N/A"


def _find_updated_at_by_path(payload: dict[str, Any], path_value: str) -> str:
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), list) else []
    target = str(path_value or "").strip()
    if not target:
        return "N/A"
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        if str(item.get("path") or "").strip() == target:
            return str(item.get("updated_at") or "N/A")
    return "N/A"


def _file_updated_at(path_value: str) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return "N/A"
    p = Path(raw)
    if not p.is_absolute():
        p = (BASE_DIR / raw).resolve()
    if not p.exists() or not p.is_file():
        return "N/A"
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()


def _review_points(handoff: dict[str, Any], integrity: dict[str, Any], health: dict[str, Any]) -> list[str]:
    points: list[str] = []

    missing_keys = integrity.get("status", {}).get("missing_keys") if isinstance(integrity.get("status"), dict) else []
    if isinstance(missing_keys, list) and missing_keys:
        points.append(f"欠損成果物を先に解消: {', '.join(str(x) for x in missing_keys[:5])}")

    warning_count = int((integrity.get("summary") if isinstance(integrity.get("summary"), dict) else {}).get("warning_count") or 0)
    fail_count = int((integrity.get("summary") if isinstance(integrity.get("summary"), dict) else {}).get("fail_count") or 0)
    points.append(f"integrity の warning/fail を確認: warning={warning_count}, fail={fail_count}")

    anomaly = str(health.get("anomaly_overall") or "N/A").upper()
    alert_count = int(health.get("alert_count") or 0)
    points.append(f"anomaly/alert の状態を確認: anomaly={anomaly}, alerts={alert_count}")

    read_order = handoff.get("read_order") if isinstance(handoff.get("read_order"), list) else []
    if read_order:
        points.append(f"read_order の先頭3件を辿る: {', '.join(str(x) for x in read_order[:3])}")
    else:
        points.append("read_order が空のため handoff 生成を再実行")

    return points


def _next_steps(integrity: dict[str, Any], health: dict[str, Any]) -> list[str]:
    steps: list[str] = []

    integrity_overall = str(integrity.get("overall") or "UNKNOWN").upper()
    anomaly = str(health.get("anomaly_overall") or "N/A").upper()

    if integrity_overall in {"FAIL", "WARNING"}:
        steps.append("python3 -m reporting.run_ops_gui_integrity_build を再実行し、missing_refs と FAIL を解消")

    if anomaly in {"WARNING", "CRITICAL"}:
        steps.append("ops_alert_center_latest.json を確認し、警告要因をレビュー観点に反映")

    steps.append("python3 -m gui.run_mock_server で mock API を起動し、/health 応答を確認")
    steps.append("ops_gui_preview_latest.html を開き、entrypoints の画面遷移を目視確認")

    deduped: list[str] = []
    for step in steps:
        if step not in deduped:
            deduped.append(step)
    return deduped


def build_gui_review_handoff_markdown() -> str:
    handoff = _safe_read_json(DEFAULT_GUI_HANDOFF_PATH)
    integrity = _safe_read_json(DEFAULT_GUI_INTEGRITY_PATH)
    health = _safe_read_json(DEFAULT_GUI_HEALTH_PATH)
    artifact_timestamps = _safe_read_json(DEFAULT_ARTIFACT_TIMESTAMPS_PATH)

    entrypoints = handoff.get("entrypoints") if isinstance(handoff.get("entrypoints"), dict) else {}
    preview = handoff.get("preview") if isinstance(handoff.get("preview"), dict) else {}
    api_mock = handoff.get("api_mock") if isinstance(handoff.get("api_mock"), dict) else {}

    bootstrap = _path_or_na(entrypoints.get("bootstrap"))
    gui_schema = _path_or_na(entrypoints.get("gui_schema"))
    home_payload = _path_or_na(entrypoints.get("home_payload"))
    preview_html = _path_or_na(preview.get("gui_preview_html"))
    mock_api = _path_or_na(api_mock.get("home"))
    integrity_overall = str(integrity.get("overall") or "N/A")

    preview_updated_at = _find_updated_at(artifact_timestamps, "gui_preview")
    if preview_updated_at == "N/A":
        preview_updated_at = _find_updated_at_by_path(artifact_timestamps, str((REPORT_DIR / "ops_gui_preview_latest.html").resolve()))
    if preview_updated_at == "N/A":
        preview_updated_at = _file_updated_at(preview_html)

    mock_api_updated_at = _find_updated_at(artifact_timestamps, "mock_api")
    if mock_api_updated_at == "N/A":
        mock_api_updated_at = _find_updated_at_by_path(artifact_timestamps, str((REPORT_DIR / "mock_api_home_latest.json").resolve()))

    review_points = _review_points(handoff, integrity, health)
    next_steps = _next_steps(integrity, health)

    lines: list[str] = []
    lines.append("# GUI Review Handoff")
    lines.append("")
    lines.append(f"generated_at: {_now_iso()}")
    lines.append("")
    lines.append("## 目的")
    lines.append("")
    lines.append("GUI 実装担当とレビュー担当が、最小時間で確認対象と優先順位を把握するためのハンドオフです。")
    lines.append("")
    lines.append("## 主要 entrypoints")
    lines.append("")
    lines.append(f"- bootstrap: {bootstrap}")
    lines.append(f"- gui_schema: {gui_schema}")
    lines.append(f"- home_payload: {home_payload}")
    lines.append("")
    lines.append("## preview 確認先")
    lines.append("")
    lines.append(f"- preview_html: {preview_html}")
    lines.append(f"- preview_html_updated_at: {preview_updated_at}")
    lines.append("")
    lines.append("## mock API 確認先")
    lines.append("")
    lines.append(f"- mock_api: {mock_api}")
    lines.append("- mock_api_health_endpoint: http://127.0.0.1:8765/health")
    lines.append(f"- mock_api_updated_at: {mock_api_updated_at}")
    lines.append("")
    lines.append("## integrity 状況")
    lines.append("")
    lines.append(f"- integrity_overall: {integrity_overall}")
    lines.append(f"- pass_count: {int((integrity.get('summary') if isinstance(integrity.get('summary'), dict) else {}).get('pass_count') or 0)}")
    lines.append(f"- warning_count: {int((integrity.get('summary') if isinstance(integrity.get('summary'), dict) else {}).get('warning_count') or 0)}")
    lines.append(f"- fail_count: {int((integrity.get('summary') if isinstance(integrity.get('summary'), dict) else {}).get('fail_count') or 0)}")
    lines.append("")
    lines.append("## review_points")
    lines.append("")
    for point in review_points:
        lines.append(f"- {point}")
    lines.append("")
    lines.append("## next_steps")
    lines.append("")
    for step in next_steps:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## status")
    lines.append("")
    lines.append(f"- handoff_loaded: {bool(handoff)}")
    lines.append(f"- integrity_loaded: {bool(integrity)}")
    lines.append(f"- health_loaded: {bool(health)}")
    lines.append(f"- artifact_timestamps_loaded: {bool(artifact_timestamps)}")
    lines.append("- fail_safe: true")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
