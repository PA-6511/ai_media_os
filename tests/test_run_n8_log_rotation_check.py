import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_n8_log_rotation_check import run_check


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pass_with_small_logs(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "sample.json").write_text("{}", encoding="utf-8")

    _write(policy, {"warn_size_mb": 10, "fail_size_mb": 100, "log_targets": ["exchange/logs"]})
    _write(request, {"log_target_dirs": [str(log_dir)], "warn_size_mb": 10, "fail_size_mb": 100})

    result = run_check(policy, request, output)
    assert result["status"] == "PASS"
    assert result["log_rotation_executed"] is False
    assert result["log_deleted"] is False
    assert output.exists()


def test_warn_when_dir_large(tmp_path: Path):
    policy = tmp_path / "config/p.json"
    request = tmp_path / "exchange/examples/r.json"
    output = tmp_path / "exchange/logs/o.json"
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "big.log").write_bytes(b"x" * (11 * 1024 * 1024))

    _write(policy, {"warn_size_mb": 10, "fail_size_mb": 100, "log_targets": ["exchange/logs"]})
    _write(request, {"log_target_dirs": [str(log_dir)], "warn_size_mb": 10, "fail_size_mb": 100})

    result = run_check(policy, request, output)
    assert result["status"] == "WARN"
    assert len(result["warns"]) >= 1
