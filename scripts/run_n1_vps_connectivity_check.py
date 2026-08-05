#!/usr/bin/env python3
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/n1_vps_connectivity_monitor_policy.json"
REQUEST = ROOT / "exchange/examples/n1_connectivity_check_request.example.json"
OUTPUT = ROOT / "exchange/logs/n1_vps_connectivity_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _result_base() -> dict:
    return {
        "phase": "N-1",
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
        "checked_at": _now_iso(),
    }


def _dns_check(host: str) -> tuple[bool, float | None, str | None]:
    started = time.perf_counter()
    try:
        socket.getaddrinfo(host, None)
        latency = (time.perf_counter() - started) * 1000
        return True, round(latency, 2), None
    except Exception as exc:
        return False, None, str(exc)


def _tcp_check(host: str, port: int, timeout: float) -> tuple[bool, float | None, str | None]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.perf_counter() - started) * 1000
            return True, round(latency, 2), None
    except Exception as exc:
        return False, None, str(exc)


def _https_check(url: str, timeout: float) -> tuple[bool, float | None, int | None, str | None]:
    started = time.perf_counter()
    req = urllib.request.Request(url=url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.perf_counter() - started) * 1000
            return True, round(latency, 2), int(resp.status), None
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000
        # HTTPError still proves route reachability.
        return True, round(latency, 2), int(exc.code), str(exc)
    except Exception as exc:
        return False, None, None, str(exc)


def _icmp_check(host: str, timeout: float) -> tuple[bool | None, float | None, str | None]:
    started = time.perf_counter()
    cmd = ["ping", "-c", "1", "-W", str(max(int(timeout), 1)), host]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=max(timeout + 1, 2), check=False)
    except FileNotFoundError:
        return None, None, "ping_not_available"
    except Exception as exc:
        return False, None, str(exc)

    latency = (time.perf_counter() - started) * 1000
    if completed.returncode == 0:
        return True, round(latency, 2), None
    return False, round(latency, 2), (completed.stderr or completed.stdout).strip() or "ping_failed"


def run_check(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict:
    base = _result_base()
    try:
        policy = _load_json(policy_path)
        request = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "FAIL",
            "reachable": False,
            "reason": f"input_load_error: {exc}",
            "targets": [],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    targets = request.get("targets") or policy.get("targets") or []
    results = []
    any_unreachable = False

    for target in targets:
        host = str(target.get("host", "")).strip()
        https_url = str(target.get("https_url") or f"https://{host}")
        tcp_port = int(target.get("tcp_port", 443))
        timeout = float(target.get("timeout_seconds", 3))
        icmp_required = bool(target.get("icmp_required", False))

        dns_ok, dns_latency, dns_reason = _dns_check(host)
        tcp_ok, tcp_latency, tcp_reason = _tcp_check(host, tcp_port, timeout)
        https_ok, https_latency, http_status, https_reason = _https_check(https_url, timeout)
        icmp_ok, icmp_latency, icmp_reason = _icmp_check(host, timeout)

        reachable = bool(dns_ok and (tcp_ok or https_ok) and (icmp_ok if icmp_required and icmp_ok is not None else True))
        if not reachable:
            any_unreachable = True

        item = {
            "host": host,
            "resolved": dns_ok,
            "latency_ms": {
                "dns": dns_latency,
                "tcp": tcp_latency,
                "https": https_latency,
                "icmp": icmp_latency,
            },
            "reachable": reachable,
            "status": "PASS" if reachable else "FAIL",
            "http_status": http_status,
            "checks": {
                "dns": {"ok": dns_ok, "reason": dns_reason},
                "tcp": {"ok": tcp_ok, "reason": tcp_reason, "port": tcp_port},
                "https": {"ok": https_ok, "reason": https_reason, "url": https_url},
                "icmp": {"ok": icmp_ok, "reason": icmp_reason, "required": icmp_required},
            },
        }
        results.append(item)

    overall_reachable = len(results) > 0 and not any_unreachable
    result = {
        **base,
        "status": "PASS" if overall_reachable else "FAIL",
        "reachable": overall_reachable,
        "targets": results,
        "target_count": len(results),
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
