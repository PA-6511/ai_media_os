from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_PATH = BASE_DIR / "data" / "reports" / "mock_server_runtime_latest.json"
DEFAULT_TIMEOUT_SECONDS = 3.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_runtime(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists() or not path.is_file():
        return None, f"runtime json not found: {path}"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"failed to parse runtime json: {exc}"

    if not isinstance(payload, dict):
        return None, "runtime json must be an object"

    return payload, None


def _extract_host_port(runtime_payload: dict[str, Any]) -> tuple[str | None, int | None, str | None]:
    host_value = runtime_payload.get("final_host", runtime_payload.get("host"))
    port_value = runtime_payload.get("final_port", runtime_payload.get("port"))

    if not isinstance(host_value, str) or not host_value.strip():
        return None, None, "host is missing in runtime json"

    try:
        port_int = int(port_value)
    except Exception:  # noqa: BLE001
        return None, None, f"invalid port in runtime json: {port_value!r}"

    if port_int < 1 or port_int > 65535:
        return None, None, f"port out of range in runtime json: {port_int}"

    return host_value.strip(), port_int, None


def _check_health(host: str, port: int, timeout_seconds: float) -> tuple[dict[str, Any] | None, str | None, int | None]:
    url = f"http://{host}:{port}/health"
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status_code = int(response.getcode())
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return None, f"HTTP error: {exc.code} {exc.reason}", int(exc.code)
    except urllib.error.URLError as exc:
        return None, f"connection error: {exc.reason}", None
    except TimeoutError:
        return None, f"timeout after {timeout_seconds:.1f}s", None
    except Exception as exc:  # noqa: BLE001
        return None, f"unexpected request error: {exc}", None

    try:
        payload = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return None, f"/health returned non-JSON body: {exc}", status_code

    if not isinstance(payload, dict):
        return None, "/health response must be a JSON object", status_code

    return payload, None, status_code


def main() -> int:
    runtime_payload, runtime_error = _load_runtime(RUNTIME_PATH)
    now = _now_iso()

    if runtime_error is not None or runtime_payload is None:
        print("[mock-server-check] NG")
        print(f"- time          : {now}")
        print(f"- runtime_path  : {RUNTIME_PATH}")
        print(f"- reason        : {runtime_error}")
        print("- hint          : start server first (python3 -m gui.run_mock_server)")
        return 1

    host, port, host_port_error = _extract_host_port(runtime_payload)
    if host_port_error is not None or host is None or port is None:
        print("[mock-server-check] NG")
        print(f"- time          : {now}")
        print(f"- runtime_path  : {RUNTIME_PATH}")
        print(f"- reason        : {host_port_error}")
        return 1

    health_payload, health_error, status_code = _check_health(
        host=host,
        port=port,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )

    if health_error is not None or health_payload is None:
        print("[mock-server-check] NG")
        print(f"- time          : {now}")
        print(f"- runtime_path  : {RUNTIME_PATH}")
        print(f"- target        : http://{host}:{port}/health")
        if status_code is not None:
            print(f"- status_code   : {status_code}")
        print(f"- reason        : {health_error}")
        return 2

    ok_value = bool(health_payload.get("ok", False))
    if not ok_value:
        print("[mock-server-check] NG")
        print(f"- time          : {now}")
        print(f"- target        : http://{host}:{port}/health")
        print(f"- status_code   : {status_code}")
        print(f"- reason        : /health returned ok={health_payload.get('ok')!r}")
        print(f"- response      : {json.dumps(health_payload, ensure_ascii=False)}")
        return 3

    print("[mock-server-check] OK")
    print(f"- time          : {now}")
    print(f"- runtime_path  : {RUNTIME_PATH}")
    print(f"- target        : http://{host}:{port}/health")
    print(f"- status_code   : {status_code}")
    print(f"- service       : {health_payload.get('service', 'unknown')}")
    print(f"- generated_at  : {health_payload.get('generated_at', 'n/a')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
