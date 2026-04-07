from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


HOST = "127.0.0.1"
PORT = 8766
BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "data" / "reports"

ENDPOINT_FILE_MAP: dict[str, Path] = {
    "/api/home": REPORT_DIR / "mock_api_home_latest.json",
    "/api/bootstrap": REPORT_DIR / "ops_bootstrap_latest.json",
    "/api/header": REPORT_DIR / "ops_header_latest.json",
    "/api/sidebar": REPORT_DIR / "ops_sidebar_latest.json",
    "/api/tabs": REPORT_DIR / "ops_tabs_latest.json",
}


STATIC_ENDPOINT_DESCRIPTIONS: dict[str, str] = {
    "/": "service guidance for GUI developers",
    "/docs": "human-readable endpoint list",
    "/api/index": "JSON endpoint index with metadata",
    "/health": "health check endpoint",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists() or not path.is_file():
        return None, "source file not found"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"failed to parse source json: {exc}"

    if not isinstance(payload, dict):
        return None, "source json must be an object"

    return payload, None


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _build_endpoint_index(host: str, port: int) -> dict[str, Any]:
    endpoints: list[dict[str, str]] = []

    for endpoint in sorted(STATIC_ENDPOINT_DESCRIPTIONS.keys()):
        endpoints.append(
            {
                "path": endpoint,
                "description": STATIC_ENDPOINT_DESCRIPTIONS[endpoint],
            }
        )

    for endpoint, source_path in sorted(ENDPOINT_FILE_MAP.items()):
        endpoints.append(
            {
                "path": endpoint,
                "description": f"mock response from {_relative_path(source_path)}",
            }
        )

    return {
        "ok": True,
        "service": "ai_media_os_mock_server",
        "host": host,
        "port": port,
        "generated_at": _now_iso(),
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
    }


def _build_docs_text(index_payload: dict[str, Any]) -> str:
    lines = [
        "AI Media OS GUI Mock Server",
        "",
        f"host: {index_payload.get('host')}",
        f"port: {index_payload.get('port')}",
        f"generated_at: {index_payload.get('generated_at')}",
        "",
        "Available Endpoints:",
    ]

    endpoints = index_payload.get("endpoints", [])
    if isinstance(endpoints, list):
        for item in endpoints:
            if not isinstance(item, dict):
                continue
            path = item.get("path", "")
            description = item.get("description", "")
            lines.append(f"- {path}: {description}")

    return "\n".join(lines) + "\n"


class MockApiHandler(BaseHTTPRequestHandler):
    server_version = "AIMediaOSMock/1.0"

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _write_text(self, status_code: int, body_text: str) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _current_host_port(self) -> tuple[str, int]:
        try:
            server_host, server_port = self.server.server_address[:2]
        except Exception:  # noqa: BLE001
            return HOST, PORT
        return str(server_host), int(server_port)

    def _handle_file_endpoint(self, endpoint: str) -> None:
        source_path = ENDPOINT_FILE_MAP[endpoint]
        payload, error = _safe_read_json(source_path)

        if error is not None:
            self._write_json(
                404,
                {
                    "ok": False,
                    "error": error,
                    "endpoint": endpoint,
                    "source": _relative_path(source_path),
                    "generated_at": _now_iso(),
                },
            )
            return

        self._write_json(200, payload or {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        host, port = self._current_host_port()

        if path == "/api/index":
            self._write_json(200, _build_endpoint_index(host=host, port=port))
            return

        if path == "/docs":
            docs_text = _build_docs_text(_build_endpoint_index(host=host, port=port))
            self._write_text(200, docs_text)
            return

        if path == "/health":
            self._write_json(
                200,
                {
                    "ok": True,
                    "service": "ai_media_os_mock_server",
                    "host": host,
                    "port": port,
                    "generated_at": _now_iso(),
                },
            )
            return

        if path == "/":
            index_payload = _build_endpoint_index(host=host, port=port)
            self._write_json(
                200,
                {
                    "ok": True,
                    "service": "ai_media_os_mock_server",
                    "message": "open /docs for human-readable guide or /api/index for JSON index",
                    "host": index_payload["host"],
                    "port": index_payload["port"],
                    "generated_at": index_payload["generated_at"],
                    "available_endpoints": [item["path"] for item in index_payload["endpoints"]],
                },
            )
            return

        if path in ENDPOINT_FILE_MAP:
            self._handle_file_endpoint(path)
            return

        self._write_json(
            404,
            {
                "ok": False,
                "error": "endpoint not found",
                "path": path,
                "available_endpoints": [
                    item["path"] for item in _build_endpoint_index(host=host, port=port)["endpoints"]
                ],
                "generated_at": _now_iso(),
            },
        )

    def log_message(self, format_str: str, *args: Any) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        message = format_str % args
        print(f"[{timestamp}] {self.address_string()} {message}")


def create_mock_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), MockApiHandler)


def run_mock_server(host: str = HOST, port: int = PORT) -> None:
    server = create_mock_server(host=host, port=port)
    print(f"mock server started: http://{host}:{port}")
    print("endpoints: /, /docs, /api/index, /health, /api/home, /api/bootstrap, /api/header, /api/sidebar, /api/tabs")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("mock server stopping")
    finally:
        server.shutdown()
        server.server_close()
