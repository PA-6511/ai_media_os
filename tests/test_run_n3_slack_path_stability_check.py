import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n3_slack_path_stability_check import run_check


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_when_all_checks_true(tmp_path: Path, monkeypatch):
    import scripts.run_n3_slack_path_stability_check as target

    monkeypatch.setattr(target, "_dns_check", lambda host: (True, None))
    monkeypatch.setattr(target, "_tls_check", lambda host, timeout: (True, 10.0, None))
    monkeypatch.setattr(target, "_head_check", lambda url, timeout: (True, 20.0, 200, None))

    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(request, {"webhook_url": "https://hooks.slack.com/services/a/b/c", "timeout_seconds": 1})

    result = run_check(request, output)
    assert result["status"] == "PASS"
    assert result["path_reachable"] is True


def test_fail_with_invalid_url(tmp_path: Path):
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(request, {"webhook_url": "not-a-url"})

    result = run_check(request, output)
    assert result["status"] == "FAIL"
