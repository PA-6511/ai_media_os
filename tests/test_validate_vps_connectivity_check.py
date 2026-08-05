import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_vps_connectivity_check import run_validation

VALID_INPUT = ROOT / "exchange/logs/vps_connectivity_check.example.json"


def _load_valid() -> dict:
    return json.loads(VALID_INPUT.read_text(encoding="utf-8"))


def _write(data: dict, td: str) -> Path:
    target = Path(td) / "connectivity.json"
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return target


def test_valid_record_passes():
    result = run_validation(VALID_INPUT)
    assert result["status"] == "PASS"
    assert result["production_status"] == "NO_GO"


def test_missing_check_id_aborts():
    data = _load_valid()
    data.pop("check_id", None)
    with tempfile.TemporaryDirectory() as td:
        path = _write(data, td)
        result = run_validation(path)
        assert result["status"] == "ABORT"


def test_secrets_exposed_true_aborts():
    data = _load_valid()
    data["secrets_exposed"] = True
    with tempfile.TemporaryDirectory() as td:
        path = _write(data, td)
        result = run_validation(path)
        assert result["status"] == "ABORT"


def test_packet_loss_range_aborts():
    data = _load_valid()
    data["packet_loss_percent"] = 120
    with tempfile.TemporaryDirectory() as td:
        path = _write(data, td)
        result = run_validation(path)
        assert result["status"] == "ABORT"