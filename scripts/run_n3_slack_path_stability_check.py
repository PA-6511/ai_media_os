#!/usr/bin/env python3
import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "exchange/examples/n3_slack_path_stability_request.example.json"
OUTPUT = ROOT / "exchange/logs/n3_slack_path_stability_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dns_check(host: str) -> tuple[bool, str | None]:
    try:
        socket.getaddrinfo(host, 443)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _tls_check(host: str, timeout: float) -> tuple[bool, float | None, str | None]:
    started = time.perf_counter()
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                latency = (time.perf_counter() - started) * 1000
                return True, round(latency, 2), None
    except Exception as exc:
        return False, None, str(exc)


def _head_check(url: str, timeout: float) -> tuple[bool, float | None, int | None, str | None]:
    started = time.perf_counter()
    req = urllib.request.Request(url=url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.perf_counter() - started) * 1000
            return True, round(latency, 2), int(resp.status), None
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000
        return True, round(latency, 2), int(exc.code), str(exc)
    except Exception as exc:
        return False, None, None, str(exc)


def run_check(request_path: Path = REQUEST, output_path: Path = OUTPUT) -> dict:
    base = {
        "phase": "N-3",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "wordpress_post_created": False,
        "external_state_change": False,
        "executor_action_allowed": False,
        "network_observation_only": True,
        "communication_test_only": True,
        "slack_message_sent": False,
        "checked_at": _now_iso(),
    }

    try:
        req = _load_json(request_path)
    except Exception as exc:
        result = {**base, "status": "FAIL", "reason": f"input_load_error: {exc}"}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    webhook_url = str(req.get("webhook_url", "")).strip()
    parsed = urllib.parse.urlparse(webhook_url)
    if parsed.scheme != "https" or not parsed.netloc:
        result = {**base, "status": "FAIL", "path_reachable": False, "dns_ok": False, "tls_ok": False, "reason": "invalid_webhook_url"}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    timeout = float(req.get("timeout_seconds", 3))
    host = parsed.hostname or ""
    dns_ok, dns_reason = _dns_check(host)
    tls_ok, tls_latency, tls_reason = _tls_check(host, timeout)
    path_reachable, latency_ms, http_status, path_reason = _head_check(webhook_url, timeout)
    status = "PASS" if dns_ok and tls_ok and path_reachable else "FAIL"

    result = {
        **base,
        "status": status,
        "webhook_url_host": host,
        "path_reachable": path_reachable,
        "latency_ms": latency_ms,
        "dns_ok": dns_ok,
        "tls_ok": tls_ok,
        "http_status": http_status,
        "checks": {
            "dns": {"ok": dns_ok, "reason": dns_reason},
            "tls": {"ok": tls_ok, "latency_ms": tls_latency, "reason": tls_reason},
            "path": {"ok": path_reachable, "reason": path_reason},
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
