from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


SCHEMA_VERSION = "1.0"

BOOTSTRAP_PATH = DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json"
MOCK_API_HOME_PATH = DEFAULT_REPORT_DIR / "mock_api_home_latest.json"
GUI_PREVIEW_PATH = DEFAULT_REPORT_DIR / "ops_gui_preview_latest.html"
GUI_HANDOFF_PATH = DEFAULT_REPORT_DIR / "ops_gui_handoff_latest.json"
GUI_STARTER_PACK_PATH = DEFAULT_REPORT_DIR / "ops_gui_starter_pack_latest.json"
GUI_INTEGRITY_PATH = DEFAULT_REPORT_DIR / "ops_gui_integrity_latest.json"
MOCK_SERVER_RUNTIME_PATH = DEFAULT_REPORT_DIR / "mock_server_runtime_latest.json"
MOCK_SERVER_OP_CHECK_PATH = DEFAULT_REPORT_DIR / "mock_server_operational_check_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _exists_file(path: Path) -> bool:
    return path.exists() and path.is_file()


def _read_json_obj(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not _exists_file(path):
        return None, "file not found"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json parse error: {exc}"

    if not isinstance(payload, dict):
        return None, "json must be an object"

    return payload, None


def _status_from_flags(is_ok: bool, warning: bool = False) -> str:
    if is_ok:
        return "PASS"
    if warning:
        return "WARNING"
    return "FAIL"


def _build_file_exists_check(key: str, path: Path) -> dict[str, Any]:
    exists = _exists_file(path)
    return {
        "key": key,
        "status": _status_from_flags(exists),
        "message": f"{path.name} exists" if exists else f"{path.name} is missing",
        "path": _normalize_path(path),
        "exists": exists,
    }


def _build_integrity_check(path: Path) -> dict[str, Any]:
    payload, error = _read_json_obj(path)
    if error is not None or payload is None:
        return {
            "key": "integrity_status",
            "status": "FAIL",
            "message": f"ops_gui_integrity_latest.json unavailable ({error})",
            "path": _normalize_path(path),
        }

    overall = str(payload.get("overall") or "").upper()
    if overall == "PASS":
        status = "PASS"
        message = "ops_gui_integrity_latest.json overall=PASS"
    elif overall == "WARNING":
        status = "WARNING"
        message = "ops_gui_integrity_latest.json overall=WARNING"
    else:
        status = "FAIL"
        message = f"ops_gui_integrity_latest.json overall={overall or 'UNKNOWN'}"

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "key": "integrity_status",
        "status": status,
        "message": message,
        "path": _normalize_path(path),
        "integrity_overall": overall or None,
        "integrity_summary": summary,
    }


def _build_mock_server_entrypoint_check(runtime_path: Path, op_check_path: Path) -> dict[str, Any]:
    runtime_payload, runtime_error = _read_json_obj(runtime_path)
    op_payload, op_error = _read_json_obj(op_check_path)

    runtime_ok = runtime_error is None and runtime_payload is not None
    op_status = str((op_payload or {}).get("status") or "").upper()
    op_ok = op_error is None and op_payload is not None and op_status == "PASS"

    if runtime_ok and op_ok:
        host = runtime_payload.get("final_host", runtime_payload.get("host"))
        port = runtime_payload.get("final_port", runtime_payload.get("port"))
        return {
            "key": "mock_server_entrypoint_confirmed",
            "status": "PASS",
            "message": "mock server runtime and operational check are confirmed",
            "runtime_json": _normalize_path(runtime_path),
            "operational_check_json": _normalize_path(op_check_path),
            "target": f"http://{host}:{port}",
        }

    if runtime_ok and not op_ok:
        detail = f"operational check unavailable ({op_error})" if op_error else f"operational check status={op_status or 'UNKNOWN'}"
        return {
            "key": "mock_server_entrypoint_confirmed",
            "status": "WARNING",
            "message": f"runtime exists but mock server operational check is not PASS ({detail})",
            "runtime_json": _normalize_path(runtime_path),
            "operational_check_json": _normalize_path(op_check_path),
        }

    return {
        "key": "mock_server_entrypoint_confirmed",
        "status": "WARNING",
        "message": f"runtime json unavailable ({runtime_error})",
        "runtime_json": _normalize_path(runtime_path),
        "operational_check_json": _normalize_path(op_check_path),
    }


def _overall(checks: list[dict[str, Any]]) -> str:
    statuses = [str(item.get("status") or "FAIL").upper() for item in checks]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "WARNING" for status in statuses):
        return "WARNING"
    return "PASS"


def _missing_items(checks: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for check in checks:
        status = str(check.get("status") or "FAIL").upper()
        if status != "PASS":
            missing.append(str(check.get("key") or "unknown"))
    return missing


def build_ops_gui_acceptance() -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        _build_file_exists_check("bootstrap_exists", BOOTSTRAP_PATH),
        _build_file_exists_check("mock_api_home_exists", MOCK_API_HOME_PATH),
        _build_file_exists_check("gui_preview_exists", GUI_PREVIEW_PATH),
        _build_file_exists_check("gui_handoff_exists", GUI_HANDOFF_PATH),
        _build_file_exists_check("gui_starter_pack_exists", GUI_STARTER_PACK_PATH),
        _build_integrity_check(GUI_INTEGRITY_PATH),
        _build_mock_server_entrypoint_check(MOCK_SERVER_RUNTIME_PATH, MOCK_SERVER_OP_CHECK_PATH),
    ]

    overall = _overall(checks)
    missing_items = _missing_items(checks)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "service": "ops_gui_acceptance",
        "overall": overall,
        "checks": checks,
        "missing_items": missing_items,
        "summary": {
            "total_checks": len(checks),
            "pass_count": sum(1 for item in checks if str(item.get("status")).upper() == "PASS"),
            "warning_count": sum(1 for item in checks if str(item.get("status")).upper() == "WARNING"),
            "fail_count": sum(1 for item in checks if str(item.get("status")).upper() == "FAIL"),
            "ready_for_gui_impl": overall == "PASS",
        },
        "status": {
            "fail_safe": True,
        },
    }
