import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n4_github_connectivity_check import run_check


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_when_github_checks_pass(tmp_path: Path, monkeypatch):
    import scripts.run_n4_github_connectivity_check as target

    monkeypatch.setattr(target, "_dns_ok", lambda host: (True, None))
    monkeypatch.setattr(target, "_https_reachability", lambda timeout: (True, 100.0, None))
    monkeypatch.setattr(target, "_ssh_auth_detected", lambda timeout: (False, "not_authenticated"))
    monkeypatch.setattr(target, "_ls_remote", lambda repo_url, timeout: (True, None))

    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(request, {"repo_url": "https://github.com/octocat/Hello-World.git", "timeout_seconds": 1})

    result = run_check(request, output)
    assert result["status"] == "PASS"
    assert result["github_reachable"] is True
    assert result["ls_remote_ok"] is True


def test_fail_when_ls_remote_fails(tmp_path: Path, monkeypatch):
    import scripts.run_n4_github_connectivity_check as target

    monkeypatch.setattr(target, "_dns_ok", lambda host: (True, None))
    monkeypatch.setattr(target, "_https_reachability", lambda timeout: (True, 100.0, None))
    monkeypatch.setattr(target, "_ssh_auth_detected", lambda timeout: (False, "not_authenticated"))
    monkeypatch.setattr(target, "_ls_remote", lambda repo_url, timeout: (False, "network_error"))

    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    _write_json(request, {"repo_url": "https://github.com/octocat/Hello-World.git", "timeout_seconds": 1})

    result = run_check(request, output)
    assert result["status"] == "FAIL"
