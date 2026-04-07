from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from gui.mock_server import BASE_DIR, HOST, PORT, create_mock_server

RUNTIME_JSON_PATH = BASE_DIR / "data" / "reports" / "mock_server_runtime_latest.json"


def _write_runtime_json(payload: dict[str, Any]) -> None:
    """Persist runtime info so GUI tooling can read the active port without parsing logs."""
    try:
        RUNTIME_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_JSON_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] warning: could not write runtime JSON: {exc}", flush=True)


def _remove_runtime_json() -> None:
    """Remove the runtime file on shutdown so stale info is not left behind."""
    try:
        if RUNTIME_JSON_PATH.exists():
            RUNTIME_JSON_PATH.unlink()
    except Exception:  # noqa: BLE001
        pass


MAX_PORT_ATTEMPTS = 10


def _resolve_port(cli_port: int | None) -> int:
    if cli_port is not None:
        return cli_port

    env_port = os.getenv("MOCK_SERVER_PORT", "").strip()
    if not env_port:
        return PORT

    try:
        return int(env_port)
    except ValueError as exc:
        raise ValueError(f"invalid MOCK_SERVER_PORT: {env_port}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AI Media OS GUI mock HTTP server")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"port number (default: MOCK_SERVER_PORT or {PORT})",
    )
    return parser


def _candidate_ports(start_port: int, max_attempts: int = MAX_PORT_ATTEMPTS) -> Iterable[int]:
    for offset in range(max_attempts):
        yield start_port + offset


def _setup_sigterm_handler(httpd_ref: list) -> None:  # noqa: ANN401
    """Shut down serve_forever() cleanly on SIGTERM.

    serve_forever() runs on the main thread.  Calling server.shutdown() from
    the *same* thread deadlocks because shutdown() blocks on __is_shut_down.wait().
    Solution: call shutdown() from a short-lived daemon thread so the main thread
    can keep running the select-loop until shutdown_request is seen.
    """

    def _handler(signum: int, frame: object) -> None:  # noqa: ANN001,ARG001
        print("[shutdown] SIGTERM received — shutting down via background thread", flush=True)
        server = httpd_ref[0] if httpd_ref else None
        if server is not None:
            t = threading.Thread(target=server.shutdown, daemon=True, name="sigterm-shutdown")
            t.start()

    try:
        signal.signal(signal.SIGTERM, _handler)
    except (OSError, ValueError):
        pass


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    httpd = None
    try:
        start_port = _resolve_port(args.port)
        if start_port < 1 or start_port > 65535:
            raise ValueError(f"invalid port: {start_port} (must be 1-65535)")

        tried_ports: list[int] = []
        selected_port: int | None = None
        for candidate_port in _candidate_ports(start_port):
            if candidate_port > 65535:
                break

            tried_ports.append(candidate_port)
            print(f"[startup:try ] {HOST}:{candidate_port}", flush=True)

            try:
                httpd = create_mock_server(host=HOST, port=candidate_port)
                selected_port = candidate_port
                break
            except OSError as exc:
                if getattr(exc, "errno", None) == 98:  # EADDRINUSE
                    print(f"[startup:busy] {candidate_port} (EADDRINUSE)", flush=True)
                    continue
                print(f"[startup:err ] bind error (errno={getattr(exc, 'errno', '?')}): {exc}", flush=True)
                traceback.print_exc(file=sys.stderr)
                return 1

        if httpd is None or selected_port is None:
            tried = ", ".join(str(p) for p in tried_ports)
            print(f"[startup:err ] no available port found. tried: [{tried}]", flush=True)
            return 1

        # Register SIGTERM handler so `kill PID` does graceful cleanup.
        httpd_ref: list = [httpd]
        _setup_sigterm_handler(httpd_ref)

        sock_name = httpd.socket.getsockname()
        final_host: str = sock_name[0]
        final_port: int = sock_name[1]
        server_url = f"http://{final_host}:{final_port}"
        pid = os.getpid()
        started_at = datetime.now(timezone.utc).isoformat()

        skipped = [p for p in tried_ports if p != final_port]

        # --- Prominent READY banner so GUI devs can immediately spot the final port ---
        print("", flush=True)
        print("=" * 60, flush=True)
        print(f"  MOCK SERVER READY", flush=True)
        print(f"  final_port  : {final_port}", flush=True)
        print(f"  server_url  : {server_url}/", flush=True)
        if skipped:
            print(f"  skipped     : {skipped}", flush=True)
        print(f"  pid         : {pid}", flush=True)
        print(f"  started_at  : {started_at}", flush=True)
        print(
            f"  endpoints   : /, /docs, /api/index, /health,",
            flush=True,
        )
        print(
            f"                /api/home, /api/bootstrap, /api/header,",
            flush=True,
        )
        print(
            f"                /api/sidebar, /api/tabs",
            flush=True,
        )
        print("  stop        : Ctrl+C or SIGTERM", flush=True)
        print("=" * 60, flush=True)
        print("", flush=True)

        # Persist runtime info for GUI tooling
        runtime_payload: dict[str, Any] = {
            "ok": True,
            "service": "ai_media_os_mock_server",
            "final_port": final_port,
            "final_host": final_host,
            "server_url": server_url,
            "pid": pid,
            "started_at": started_at,
            "skipped_ports": skipped,
            "runtime_json_path": str(RUNTIME_JSON_PATH),
        }
        _write_runtime_json(runtime_payload)
        print(f"[startup] runtime JSON : {RUNTIME_JSON_PATH}", flush=True)
        print("", flush=True)

        # --- blocking serve loop (runs on main thread until shutdown) ---
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[shutdown] KeyboardInterrupt received", flush=True)

        return 0

    except ValueError as exc:
        print(f"[startup] error: {exc}", flush=True)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] unexpected error: {exc}", flush=True)
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        if httpd is not None:
            print("[shutdown] closing server socket ...", flush=True)
            try:
                httpd.server_close()
            except Exception:  # noqa: BLE001
                pass
            print("[shutdown] done", flush=True)
        _remove_runtime_json()


if __name__ == "__main__":
    sys.exit(main())
