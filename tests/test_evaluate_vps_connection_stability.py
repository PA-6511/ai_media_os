import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_vps_connection_stability import run_evaluation

VALID_INPUT = ROOT / "exchange/logs/vps_stability_samples.example.json"


def _load_valid() -> dict:
    return json.loads(VALID_INPUT.read_text(encoding="utf-8"))


def _write(data: dict, td: str) -> tuple[Path, Path]:
    src = Path(td) / "samples.json"
    out = Path(td) / "evaluation.json"
    src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return src, out


def test_valid_samples_pass_or_warn():
    with tempfile.TemporaryDirectory() as td:
        src, out = _write(_load_valid(), td)
        result = run_evaluation(src, out)
        assert result["status"] == "PASS"
        assert result["overall_status"] in {"PASS_DRY_RUN_ONLY", "WARN_DRY_RUN_ONLY", "FAIL_DRY_RUN_ONLY"}
        assert out.exists()


def test_sample_count_less_than_five_warns():
    data = _load_valid()
    data["samples"] = data["samples"][:4]
    with tempfile.TemporaryDirectory() as td:
        src, out = _write(data, td)
        result = run_evaluation(src, out)
        assert result["overall_status"] == "WARN_DRY_RUN_ONLY"


def test_high_fail_rate_results_fail():
    data = _load_valid()
    for sample in data["samples"]:
        sample["tcp_22_result"] = "FAIL"
    with tempfile.TemporaryDirectory() as td:
        src, out = _write(data, td)
        result = run_evaluation(src, out)
        assert result["overall_status"] == "FAIL_DRY_RUN_ONLY"


def test_secrets_exposed_aborts():
    data = _load_valid()
    data["samples"][0]["secrets_exposed"] = True
    with tempfile.TemporaryDirectory() as td:
        src, out = _write(data, td)
        result = run_evaluation(src, out)
        assert result["overall_status"] == "ABORT"