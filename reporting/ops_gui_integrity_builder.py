from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


SCHEMA_VERSION = "1.0"

TARGETS: list[dict[str, Any]] = [
    {"target": "ops_bootstrap_latest.json", "path": DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json", "json": True},
    {"target": "ops_home_payload_latest.json", "path": DEFAULT_REPORT_DIR / "ops_home_payload_latest.json", "json": True},
    {"target": "ops_sidebar_latest.json", "path": DEFAULT_REPORT_DIR / "ops_sidebar_latest.json", "json": True},
    {"target": "ops_tabs_latest.json", "path": DEFAULT_REPORT_DIR / "ops_tabs_latest.json", "json": True},
    {"target": "ops_widgets_latest.json", "path": DEFAULT_REPORT_DIR / "ops_widgets_latest.json", "json": True},
    {"target": "ops_layout_latest.json", "path": DEFAULT_REPORT_DIR / "ops_layout_latest.json", "json": True},
    {"target": "ops_header_latest.json", "path": DEFAULT_REPORT_DIR / "ops_header_latest.json", "json": True},
    {"target": "ops_gui_schema_latest.json", "path": DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json", "json": True},
    {"target": "ops_gui_handoff_latest.json", "path": DEFAULT_REPORT_DIR / "ops_gui_handoff_latest.json", "json": True},
    {"target": "mock_api_home_latest.json", "path": DEFAULT_REPORT_DIR / "mock_api_home_latest.json", "json": True},
    {"target": "ops_manifest_latest.json", "path": DEFAULT_REPORT_DIR / "ops_manifest_latest.json", "json": True},
    {"target": "ops_gui_bundle_manifest_latest.json", "path": DEFAULT_REPORT_DIR / "ops_gui_bundle_manifest_latest.json", "json": True},
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_parse_json(path: Path) -> tuple[bool, dict[str, Any] | None]:
    if not path.exists() or not path.is_file():
        return False, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, None
    if not isinstance(payload, dict):
        return False, None
    return True, payload


def _status_for(exists: bool, json_valid: bool | None) -> str:
    if not exists:
        return "FAIL"
    if json_valid is False:
        return "FAIL"
    return "PASS"


def _resolve_repo_path(path_value: Any) -> Path | None:
    if path_value is None:
        return None
    raw = str(path_value).strip()
    if not raw:
        return None
    path_obj = Path(raw)
    if path_obj.is_absolute():
        return path_obj
    return BASE_DIR / raw.replace("\\", "/")


def _collect_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"path", "primary_path"} and isinstance(child, str):
                paths.append(child)
            elif key == "related_paths" and isinstance(child, list):
                paths.extend(str(item) for item in child if isinstance(item, str))
            else:
                paths.extend(_collect_paths(child))
    elif isinstance(value, list):
        for item in value:
            paths.extend(_collect_paths(item))
    return paths


def _consistency_checks(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    bootstrap = payloads.get("ops_bootstrap_latest.json") or {}
    bundle = payloads.get("ops_gui_bundle_manifest_latest.json") or {}
    handoff = payloads.get("ops_gui_handoff_latest.json") or {}

    bootstrap_sections = ["header", "status", "sidebar", "tabs", "home_payload"]
    missing_sections = [section for section in bootstrap_sections if section not in bootstrap]
    checks.append(
        {
            "target": "bootstrap_sections",
            "exists": True,
            "json_valid": True,
            "status": "PASS" if not missing_sections else "FAIL",
            "detail": "all required sections present" if not missing_sections else f"missing: {', '.join(missing_sections)}",
        }
    )

    referenced_paths = _collect_paths(bootstrap)
    missing_refs: list[str] = []
    for raw in sorted(set(referenced_paths)):
        resolved = _resolve_repo_path(raw)
        if resolved is None:
            continue
        if not resolved.exists() or not resolved.is_file():
            missing_refs.append(raw)
    checks.append(
        {
            "target": "bootstrap_path_references",
            "exists": True,
            "json_valid": True,
            "status": "PASS" if not missing_refs else "WARNING",
            "detail": "all referenced paths exist" if not missing_refs else f"missing_refs={len(missing_refs)}",
            "missing_refs": missing_refs[:20],
        }
    )

    bundle_entry = bundle.get("entrypoints") if isinstance(bundle.get("entrypoints"), dict) else {}
    handoff_entry = handoff.get("entrypoints") if isinstance(handoff.get("entrypoints"), dict) else {}
    handoff_api = handoff.get("api_mock") if isinstance(handoff.get("api_mock"), dict) else {}

    expected = {
        "bootstrap": "data/reports/ops_bootstrap_latest.json",
        "home_payload": "data/reports/ops_home_payload_latest.json",
        "mock_api": "data/reports/mock_api_home_latest.json",
        "gui_schema": "data/reports/ops_gui_schema_latest.json",
    }
    mismatches: list[str] = []

    if str(bundle_entry.get("bootstrap") or "") != expected["bootstrap"]:
        mismatches.append("bundle.bootstrap")
    if str(bundle_entry.get("home_payload") or "") != expected["home_payload"]:
        mismatches.append("bundle.home_payload")
    if str(bundle_entry.get("mock_api") or "") != expected["mock_api"]:
        mismatches.append("bundle.mock_api")

    if str(handoff_entry.get("bootstrap") or "") != expected["bootstrap"]:
        mismatches.append("handoff.bootstrap")
    if str(handoff_entry.get("home_payload") or "") != expected["home_payload"]:
        mismatches.append("handoff.home_payload")
    if str(handoff_entry.get("gui_schema") or "") != expected["gui_schema"]:
        mismatches.append("handoff.gui_schema")
    if str(handoff_api.get("home") or "") != expected["mock_api"]:
        mismatches.append("handoff.api_mock.home")

    checks.append(
        {
            "target": "entrypoints_consistency",
            "exists": True,
            "json_valid": True,
            "status": "PASS" if not mismatches else "FAIL",
            "detail": "bundle/handoff entrypoints are consistent" if not mismatches else f"mismatch: {', '.join(mismatches)}",
        }
    )

    return checks


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = [str(check.get("status") or "PASS").upper() for check in checks]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "WARNING" for status in statuses):
        return "WARNING"
    return "PASS"


def build_ops_gui_integrity() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}

    for spec in TARGETS:
        target = str(spec.get("target"))
        path = spec.get("path")
        expect_json = bool(spec.get("json"))

        if not isinstance(path, Path):
            continue

        exists = path.exists() and path.is_file()
        json_valid: bool | None = None
        parsed_payload: dict[str, Any] | None = None
        if expect_json:
            json_valid, parsed_payload = _safe_parse_json(path)
            if json_valid and parsed_payload is not None:
                payloads[target] = parsed_payload

        checks.append(
            {
                "target": target,
                "path": _to_rel_path(path),
                "exists": exists,
                "json_valid": json_valid,
                "status": _status_for(exists, json_valid),
            }
        )

    checks.extend(_consistency_checks(payloads))
    overall = _overall_status(checks)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "overall": overall,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "pass_count": sum(1 for check in checks if str(check.get("status")).upper() == "PASS"),
            "warning_count": sum(1 for check in checks if str(check.get("status")).upper() == "WARNING"),
            "fail_count": sum(1 for check in checks if str(check.get("status")).upper() == "FAIL"),
        },
        "status": {
            "fail_safe": True,
        },
    }