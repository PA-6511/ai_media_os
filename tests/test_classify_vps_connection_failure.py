import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.classify_vps_connection_failure import classify

TAXONOMY = ROOT / "config/vps_connection_failure_taxonomy.json"
CONNECTIVITY = ROOT / "exchange/logs/vps_connectivity_check.example.json"


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_classification_returns_categories():
    evaluation = {
        "overall_status": "WARN_DRY_RUN_ONLY",
        "tcp_22_fail_rate": 40,
        "average_latency_ms": 400,
        "average_packet_loss_percent": 8,
        "ssh_auth_dry_run_fail_count": 1,
        "ssh_banner_fail_count": 0,
    }
    with tempfile.TemporaryDirectory() as td:
        eval_path = Path(td) / "evaluation.json"
        out_path = Path(td) / "classification.json"
        _write(eval_path, evaluation)
        result = classify(TAXONOMY, eval_path, CONNECTIVITY, out_path)
        assert result["status"] == "PASS"
        assert "TCP_22_BLOCKED" in result["classification"]
        assert "HIGH_LATENCY" in result["classification"]
        assert out_path.exists()


def test_abort_status_maps_local_client_issue():
    evaluation = {"overall_status": "ABORT"}
    with tempfile.TemporaryDirectory() as td:
        eval_path = Path(td) / "evaluation.json"
        out_path = Path(td) / "classification.json"
        _write(eval_path, evaluation)
        result = classify(TAXONOMY, eval_path, CONNECTIVITY, out_path)
        assert result["status"] == "PASS"
        assert "LOCAL_CLIENT_ISSUE" in result["classification"]


def test_missing_taxonomy_aborts():
    with tempfile.TemporaryDirectory() as td:
        eval_path = Path(td) / "evaluation.json"
        out_path = Path(td) / "classification.json"
        _write(eval_path, {"overall_status": "PASS_DRY_RUN_ONLY"})
        result = classify(Path(td) / "missing.json", eval_path, CONNECTIVITY, out_path)
        assert result["status"] == "ABORT"