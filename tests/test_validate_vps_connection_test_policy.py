import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_vps_connection_test_policy import run_validation

VALID_CONFIG = ROOT / "config/vps_connection_test_policy.json"


def _load_valid() -> dict:
    return json.loads(VALID_CONFIG.read_text(encoding="utf-8"))


def _write_temp(data: dict) -> tuple[Path, Path]:
    td = tempfile.TemporaryDirectory()
    cfg = Path(td.name) / "policy.json"
    out = Path(td.name) / "result.json"
    cfg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return cfg, out


def test_valid_policy_passes():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_validation(VALID_CONFIG, out)
        assert result["status"] == "PASS"
        assert result["policy_valid"] is True
        assert result["mode"] == "CONNECTION_TEST"
        assert result["execution"] == "DRY_RUN"
        assert result["production_status"] == "NO_GO"
        assert out.exists()


def test_wrong_mode_aborts():
    data = _load_valid()
    data["mode"] = "LIVE"
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "policy.json"
        out = Path(td) / "result.json"
        cfg.write_text(json.dumps(data), encoding="utf-8")
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"


def test_forbidden_key_aborts():
    data = _load_valid()
    data["api_token"] = "dummy"
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "policy.json"
        out = Path(td) / "result.json"
        cfg.write_text(json.dumps(data), encoding="utf-8")
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"


def test_allowed_checks_mismatch_aborts():
    data = _load_valid()
    data["allowed_checks"] = ["ping", "tcp_22"]
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "policy.json"
        out = Path(td) / "result.json"
        cfg.write_text(json.dumps(data), encoding="utf-8")
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"