import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_n_series_overall_report import generate_report


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_report_with_full_evidence(tmp_path: Path):
    evidence_paths = {
        "N-1": tmp_path / "exchange/logs/n1.json",
        "N-2": tmp_path / "exchange/logs/n2.json",
        "N-3": tmp_path / "exchange/logs/n3.json",
        "N-4": tmp_path / "exchange/logs/n4.json",
        "N-5": tmp_path / "exchange/logs/n5.json",
    }
    _write(evidence_paths["N-1"], {"status": "PASS"})
    _write(evidence_paths["N-2"], {"status": "WARN"})
    _write(evidence_paths["N-3"], {"status": "PASS", "slack_message_sent": False})
    _write(evidence_paths["N-4"], {"status": "PASS", "github_push_executed": False})
    _write(evidence_paths["N-5"], {"status": "PASS", "system_restart_executed": False})

    output_json = tmp_path / "exchange/logs/out.json"
    output_md = tmp_path / "exchange/logs/out.md"

    report = generate_report(evidence_paths, output_json, output_md)
    assert report["required_evidence_count"] == 5
    assert report["found_evidence_count"] == 5
    assert report["missing_evidence_count"] == 0
    assert report["overall_status"] == "PASS_DRY_RUN_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["execution"] == "DRY_RUN"
    assert output_json.exists()
    assert output_md.exists()


def test_generate_report_with_missing_evidence(tmp_path: Path):
    evidence_paths = {
        "N-1": tmp_path / "exchange/logs/n1.json",
        "N-2": tmp_path / "exchange/logs/n2.json",
        "N-3": tmp_path / "exchange/logs/missing.json",
        "N-4": tmp_path / "exchange/logs/n4.json",
        "N-5": tmp_path / "exchange/logs/n5.json",
    }
    _write(evidence_paths["N-1"], {"status": "PASS"})
    _write(evidence_paths["N-2"], {"status": "PASS"})
    _write(evidence_paths["N-4"], {"status": "PASS"})
    _write(evidence_paths["N-5"], {"status": "PASS"})

    report = generate_report(evidence_paths, tmp_path / "exchange/logs/o.json", tmp_path / "exchange/logs/o.md")
    assert report["missing_evidence_count"] == 1
    assert any("MISSING" in item for item in report["fail_list"])
