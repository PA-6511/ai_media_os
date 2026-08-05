import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n2_wordpress_api_stability_check import run_check


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_when_all_success(tmp_path: Path, monkeypatch):
    import scripts.run_n2_wordpress_api_stability_check as target

    monkeypatch.setattr(target, "_single_request", lambda url, method, timeout: (True, 200, 50.0, False, None))

    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(policy, {"allowed_methods": ["GET", "HEAD"], "thresholds": {"pass_success_rate_percent": 99, "warn_success_rate_percent": 95}})
    _write_json(request, {"endpoint_url": "https://example.com/wp-json", "method": "HEAD", "iterations": 5, "retry_limit": 1})

    result = run_check(policy, request, output)
    assert result["status"] == "PASS"
    assert result["success_count"] == 5
    assert output.exists()


def test_warn_when_success_rate_between_95_and_99(tmp_path: Path, monkeypatch):
    import scripts.run_n2_wordpress_api_stability_check as target

    calls = {"n": 0}

    def fake_request(url, method, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return False, None, None, True, "timeout"
        return True, 200, 80.0, False, None

    monkeypatch.setattr(target, "_single_request", fake_request)

    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(policy, {"allowed_methods": ["GET", "HEAD"], "thresholds": {"pass_success_rate_percent": 99, "warn_success_rate_percent": 95}})
    _write_json(request, {"endpoint_url": "https://example.com/wp-json", "method": "HEAD", "iterations": 20, "retry_limit": 0})

    result = run_check(policy, request, output)
    assert result["status"] == "WARN"


def test_fail_when_method_is_forbidden(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(policy, {"allowed_methods": ["GET", "HEAD"]})
    _write_json(request, {"endpoint_url": "https://example.com/wp-json", "method": "POST", "iterations": 1, "retry_limit": 0})

    result = run_check(policy, request, output)
    assert result["status"] == "FAIL"
