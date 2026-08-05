#!/usr/bin/env python3
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/n2_wordpress_api_stability_policy.json"
REQUEST = ROOT / "exchange/examples/n2_wordpress_api_stability_request.example.json"
OUTPUT = ROOT / "exchange/logs/n2_wordpress_api_stability_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _single_request(url: str, method: str, timeout: float) -> tuple[bool, int | None, float | None, bool, str | None]:
    started = time.perf_counter()
    try:
        req = urllib.request.Request(url=url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.perf_counter() - started) * 1000
            return True, int(resp.status), round(latency, 2), False, None
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000
        # A non-2xx response still means communication worked.
        return True, int(exc.code), round(latency, 2), False, str(exc)
    except Exception as exc:
        is_timeout = isinstance(exc, TimeoutError) or "timed out" in str(exc).lower()
        return False, None, None, is_timeout, str(exc)


def run_check(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict:
    base = {
        "phase": "N-2",
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

    try:
        policy = _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "FAIL",
            "reason": f"input_load_error: {exc}",
            "samples": [],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    method = str(req.get("method", "GET")).upper()
    allowed_methods = set(policy.get("allowed_methods", ["GET", "HEAD"]))
    if method not in allowed_methods:
        result = {
            **base,
            "status": "FAIL",
            "reason": f"method_not_allowed: {method}",
            "samples": [],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    endpoint = str(req.get("endpoint_url", "")).strip()
    iterations = max(int(req.get("iterations", 5)), 1)
    timeout = float(req.get("timeout_seconds", 3))
    retry_limit = max(int(req.get("retry_limit", 1)), 0)

    success_count = 0
    fail_count = 0
    response_times: list[float] = []
    samples: list[dict] = []

    for index in range(iterations):
        attempt = 0
        ok = False
        status_code = None
        latency_ms = None
        timeout_hit = False
        error_reason = None

        while attempt <= retry_limit:
            ok, status_code, latency_ms, timeout_hit, error_reason = _single_request(endpoint, method, timeout)
            if ok:
                break
            attempt += 1

        if ok:
            success_count += 1
            if latency_ms is not None:
                response_times.append(latency_ms)
        else:
            fail_count += 1

        samples.append(
            {
                "index": index,
                "response_time_ms": latency_ms,
                "http_status": status_code,
                "timeout": timeout_hit,
                "retry_count": min(attempt, retry_limit),
                "status": "PASS" if ok else "FAIL",
                "error": error_reason,
            }
        )

    success_rate = (success_count / iterations) * 100
    thresholds = policy.get("thresholds", {})
    pass_line = float(thresholds.get("pass_success_rate_percent", 99))
    warn_line = float(thresholds.get("warn_success_rate_percent", 95))
    status = "PASS" if success_rate >= pass_line else "WARN" if success_rate >= warn_line else "FAIL"

    avg = round(sum(response_times) / len(response_times), 2) if response_times else None
    mx = round(max(response_times), 2) if response_times else None
    mn = round(min(response_times), 2) if response_times else None

    result = {
        **base,
        "status": status,
        "endpoint_url": endpoint,
        "method": method,
        "iterations": iterations,
        "success_rate_percent": round(success_rate, 2),
        "success_count": success_count,
        "fail_count": fail_count,
        "average_response_time_ms": avg,
        "max_response_time_ms": mx,
        "min_response_time_ms": mn,
        "samples": samples,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
