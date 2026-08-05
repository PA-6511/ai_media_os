import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_n6_n10_overall_report import generate_report


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_full_evidence_report(tmp_path: Path):
    n6_n9 = {
        "N-6": tmp_path / "exchange/logs/n6.json",
        "N-7": tmp_path / "exchange/logs/n7.json",
        "N-8": tmp_path / "exchange/logs/n8.json",
        "N-9": tmp_path / "exchange/logs/n9.json",
    }
    n1_n5 = {
        "N-1": tmp_path / "exchange/logs/n1.json",
        "N-2": tmp_path / "exchange/logs/n2.json",
        "N-3": tmp_path / "exchange/logs/n3.json",
        "N-4": tmp_path / "exchange/logs/n4.json",
        "N-5": tmp_path / "exchange/logs/n5.json",
    }
    for p in {**n6_n9, **n1_n5}.values():
        _write(p, {"status": "PASS"})

    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    report = generate_report(n6_n9, n1_n5, out_json, out_md)

    assert report["n6_n9_required_count"] == 4
    assert report["n6_n9_found_count"] == 4
    assert report["n6_n9_missing_count"] == 0
    assert report["n1_n5_found_count"] == 5
    assert report["overall_status"] == "PASS_DRY_RUN_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["execution"] == "DRY_RUN"
    assert report["executed_external_changes"] == 0
    assert out_json.exists()
    assert out_md.exists()


def test_missing_n7_appears_in_fail_list(tmp_path: Path):
    n6_n9 = {
        "N-6": tmp_path / "exchange/logs/n6.json",
        "N-7": tmp_path / "exchange/logs/MISSING_n7.json",
        "N-8": tmp_path / "exchange/logs/n8.json",
        "N-9": tmp_path / "exchange/logs/n9.json",
    }
    n1_n5 = {
        "N-1": tmp_path / "exchange/logs/n1.json",
        "N-2": tmp_path / "exchange/logs/n2.json",
        "N-3": tmp_path / "exchange/logs/n3.json",
        "N-4": tmp_path / "exchange/logs/n4.json",
        "N-5": tmp_path / "exchange/logs/n5.json",
    }
    for phase, p in {**n6_n9, **n1_n5}.items():
        if "MISSING" not in p.name:
            _write(p, {"status": "PASS"})

    report = generate_report(
        n6_n9,
        n1_n5,
        tmp_path / "exchange/logs/o.json",
        tmp_path / "exchange/logs/o.md",
    )
    assert report["n6_n9_missing_count"] == 1
    assert any("N-7" in item and "MISSING" in item for item in report["fail_list"])
