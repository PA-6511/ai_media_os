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
REQUEST = ROOT / "exchange/examples/n4_github_connectivity_request.example.json"
OUTPUT = ROOT / "exchange/logs/n4_github_connectivity_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dns_ok(host: str) -> tuple[bool, str | None]:
    try:
        socket.getaddrinfo(host, 443)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _https_reachability(timeout: float) -> tuple[bool, float | None, str | None]:
    started = time.perf_counter()
    req = urllib.request.Request(url="https://github.com", method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            latency = (time.perf_counter() - started) * 1000
            return True, round(latency, 2), None
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000
        return True, round(latency, 2), str(exc)
    except Exception as exc:
        return False, None, str(exc)


def _ssh_auth_detected(timeout: float) -> tuple[bool, str]:
    cmd = [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={max(int(timeout), 1)}",
        "git@github.com",
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=max(timeout + 2, 3), check=False)
    except FileNotFoundError:
        return False, "ssh_command_not_found"
    except Exception as exc:
        return False, str(exc)

    merged = f"{completed.stdout}\n{completed.stderr}".lower()
    detected = "successfully authenticated" in merged or "hi " in merged
    return detected, merged.strip()[:300]


def _ls_remote(repo_url: str, timeout: float) -> tuple[bool, str | None]:
    cmd = ["git", "ls-remote", "--heads", repo_url]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=max(timeout + 2, 3), check=False)
    except FileNotFoundError:
        return False, "git_command_not_found"
    except Exception as exc:
        return False, str(exc)

    if completed.returncode == 0:
        return True, None
    return False, (completed.stderr or completed.stdout).strip()[:300]


def run_check(request_path: Path = REQUEST, output_path: Path = OUTPUT) -> dict:
    base = {
        "phase": "N-4",
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
        "github_push_executed": False,
        "github_merge_executed": False,
        "checked_at": _now_iso(),
    }

    try:
        req = _load_json(request_path)
    except Exception as exc:
        result = {**base, "status": "FAIL", "reason": f"input_load_error: {exc}"}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    timeout = float(req.get("timeout_seconds", 5))
    repo_url = str(req.get("repo_url", "https://github.com/octocat/Hello-World.git"))

    dns_ok, dns_reason = _dns_ok("github.com")
    reachable, response_time_ms, reach_reason = _https_reachability(timeout)
    ssh_auth, ssh_note = _ssh_auth_detected(timeout)
    ls_remote_ok, ls_remote_reason = _ls_remote(repo_url, timeout)

    status = "PASS" if dns_ok and reachable and ls_remote_ok else "FAIL"
    result = {
        **base,
        "status": status,
        "repo_url": repo_url,
        "github_reachable": reachable,
        "ssh_auth_detected": ssh_auth,
        "response_time_ms": response_time_ms,
        "dns_ok": dns_ok,
        "ls_remote_ok": ls_remote_ok,
        "clone_dry_run_checked": True,
        "checks": {
            "dns": {"ok": dns_ok, "reason": dns_reason},
            "https": {"ok": reachable, "reason": reach_reason},
            "ssh_auth": {"ok": ssh_auth, "note": ssh_note},
            "ls_remote": {"ok": ls_remote_ok, "reason": ls_remote_reason},
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
