import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n1_vps_connectivity_check import run_check


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_policy() -> dict:
    return {
        "targets": [
            {
                "host": "example.com",
                "https_url": "https://example.com",
                "tcp_port": 443,
                "icmp_required": False,
            }
        ]
    }


def _base_request() -> dict:
    return {
        "targets": [
            {
                "host": "example.com",
                "https_url": "https://example.com",
                "tcp_port": 443,
                "icmp_required": False,
                "timeout_seconds": 1,
            }
        ]
    }


def test_run_check_pass(tmp_path: Path, monkeypatch):
    import scripts.run_n1_vps_connectivity_check as target

    monkeypatch.setattr(target, "_dns_check", lambda host: (True, 1.0, None))
    monkeypatch.setattr(target, "_tcp_check", lambda host, port, timeout: (True, 2.0, None))
    monkeypatch.setattr(target, "_https_check", lambda url, timeout: (True, 3.0, 200, None))
    monkeypatch.setattr(target, "_icmp_check", lambda host, timeout: (None, None, "ping_not_available"))

    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(policy, _base_policy())
    _write_json(request, _base_request())

    result = run_check(policy, request, output)
    assert result["status"] == "PASS"
    assert result["reachable"] is True
    assert output.exists()


def test_run_check_fail_when_unreachable(tmp_path: Path, monkeypatch):
    import scripts.run_n1_vps_connectivity_check as target

    monkeypatch.setattr(target, "_dns_check", lambda host: (False, None, "dns_error"))
    monkeypatch.setattr(target, "_tcp_check", lambda host, port, timeout: (False, None, "tcp_error"))
    monkeypatch.setattr(target, "_https_check", lambda url, timeout: (False, None, None, "https_error"))
    monkeypatch.setattr(target, "_icmp_check", lambda host, timeout: (False, None, "icmp_error"))

    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(policy, _base_policy())
    _write_json(request, _base_request())

    result = run_check(policy, request, output)
    assert result["status"] == "FAIL"
    assert result["reachable"] is False
