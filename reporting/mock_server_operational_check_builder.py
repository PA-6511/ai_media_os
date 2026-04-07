from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


RUNTIME_JSON_PATH = DEFAULT_REPORT_DIR / "mock_server_runtime_latest.json"
REQUEST_TIMEOUT_SECONDS = 3.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _load_runtime_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists() or not path.is_file():
        return None, "runtime json not found"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"failed to parse runtime json: {exc}"

    if not isinstance(payload, dict):
        return None, "runtime json must be an object"

    return payload, None


def _extract_host_port(runtime_payload: dict[str, Any]) -> tuple[str | None, int | None, str | None]:
    host_raw = runtime_payload.get("final_host", runtime_payload.get("host"))
    port_raw = runtime_payload.get("final_port", runtime_payload.get("port"))

    if not isinstance(host_raw, str) or not host_raw.strip():
        return None, None, "host not found in runtime json"

    try:
        port = int(port_raw)
    except Exception:  # noqa: BLE001
        return None, None, f"invalid port in runtime json: {port_raw!r}"

    if port < 1 or port > 65535:
        return None, None, f"port out of range in runtime json: {port}"

    return host_raw.strip(), port, None


def _request_json(url: str, timeout_seconds: float) -> tuple[int | None, dict[str, Any] | None, str | None]:
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status_code = int(response.getcode())
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), None, f"HTTP error: {exc.code} {exc.reason}"
    except urllib.error.URLError as exc:
        return None, None, f"connection error: {exc.reason}"
    except TimeoutError:
        return None, None, f"timeout after {timeout_seconds:.1f}s"
    except Exception as exc:  # noqa: BLE001
        return None, None, f"unexpected request error: {exc}"

    try:
        payload = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        return status_code, None, f"response is not JSON: {exc}"

    if not isinstance(payload, dict):
        return status_code, None, "response JSON must be an object"

    return status_code, payload, None


def _make_check_item(name: str, ok: bool, detail: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    item = {
        "name": name,
        "ok": ok,
        "detail": detail,
    }
    if extra:
        item.update(extra)
    return item


def build_mock_server_operational_check() -> dict[str, Any]:
    generated_at = _now_iso()
    checks: list[dict[str, Any]] = []

    runtime_payload, runtime_error = _load_runtime_json(RUNTIME_JSON_PATH)
    runtime_ok = runtime_error is None and runtime_payload is not None
    checks.append(
        _make_check_item(
            name="runtime_json_exists_and_parseable",
            ok=runtime_ok,
            detail="runtime json loaded" if runtime_ok else str(runtime_error),
            extra={
                "path": _normalize_path(RUNTIME_JSON_PATH),
            },
        )
    )

    host: str | None = None
    port: int | None = None
    if runtime_payload is not None:
        host, port, host_port_error = _extract_host_port(runtime_payload)
        checks.append(
            _make_check_item(
                name="runtime_host_port_valid",
                ok=host_port_error is None,
                detail="host/port are valid" if host_port_error is None else host_port_error,
                extra={
                    "host": host,
                    "port": port,
                },
            )
        )
    else:
        checks.append(
            _make_check_item(
                name="runtime_host_port_valid",
                ok=False,
                detail="skipped: runtime json unavailable",
            )
        )

    target_base_url: str | None = None
    if host is not None and port is not None:
        target_base_url = f"http://{host}:{port}"

        health_url = f"{target_base_url}/health"
        health_status, health_payload, health_error = _request_json(health_url, REQUEST_TIMEOUT_SECONDS)
        health_ok = health_error is None and health_status == 200 and bool(health_payload.get("ok", False))
        checks.append(
            _make_check_item(
                name="health_endpoint",
                ok=health_ok,
                detail="/health returned ok=true" if health_ok else str(health_error or "unexpected health response"),
                extra={
                    "url": health_url,
                    "status_code": health_status,
                    "response_ok": None if health_payload is None else health_payload.get("ok"),
                },
            )
        )

        index_url = f"{target_base_url}/api/index"
        index_status, index_payload, index_error = _request_json(index_url, REQUEST_TIMEOUT_SECONDS)
        endpoint_count = None if index_payload is None else index_payload.get("endpoint_count")
        has_endpoints_array = isinstance(index_payload.get("endpoints"), list) if index_payload is not None else False
        index_ok = index_error is None and index_status == 200 and has_endpoints_array
        checks.append(
            _make_check_item(
                name="api_index_endpoint",
                ok=index_ok,
                detail="/api/index returned endpoint index" if index_ok else str(index_error or "unexpected api/index response"),
                extra={
                    "url": index_url,
                    "status_code": index_status,
                    "endpoint_count": endpoint_count,
                    "has_endpoints_array": has_endpoints_array,
                },
            )
        )
    else:
        checks.append(
            _make_check_item(
                name="health_endpoint",
                ok=False,
                detail="skipped: host/port unavailable",
            )
        )
        checks.append(
            _make_check_item(
                name="api_index_endpoint",
                ok=False,
                detail="skipped: host/port unavailable",
            )
        )

    pass_count = sum(1 for item in checks if item.get("ok") is True)
    fail_count = len(checks) - pass_count
    overall_ok = fail_count == 0

    return {
        "ok": overall_ok,
        "status": "PASS" if overall_ok else "FAIL",
        "generated_at": generated_at,
        "service": "ai_media_os_mock_server_operational_check",
        "runtime_json": _normalize_path(RUNTIME_JSON_PATH),
        "target_base_url": target_base_url,
        "summary": {
            "total_checks": len(checks),
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
        "checks": checks,
    }
