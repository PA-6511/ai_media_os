from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCK_ROOT = ROOT / "blocks/sale_flash_block"
SCRIPTS = BLOCK_ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["source", "title", "author", "isbn", "asin", "campaign", "sale_status", "confidence", "note"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_policy(tmp_path: Path, incoming_csv: Path, fixture_csv: Path, history_dir: Path) -> Path:
    policy = {
        "phase": "SFB-11",
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "strict_stop_on_invalid_rows": True,
        "max_rows_per_import": 200,
        "required_columns": [
            "source",
            "title",
            "author",
            "isbn",
            "asin",
            "campaign",
            "sale_status",
            "confidence",
            "note",
        ],
        "required_non_empty_columns": ["source", "title", "author", "sale_status", "confidence"],
        "allowed_sources": ["manual_csv", "publisher_news_candidate"],
        "allowed_sale_status": ["candidate", "hold", "exclude"],
        "confidence_range": {"min": 0.0, "max": 1.0},
        "require_isbn_or_asin": True,
        "duplicate_strategy": "keep_first",
        "fixture_columns": [
            "source",
            "title",
            "author",
            "isbn",
            "asin",
            "campaign",
            "sale_status",
            "confidence",
            "note",
        ],
        "paths": {
            "incoming_csv": str(incoming_csv),
            "fixture_csv": str(fixture_csv),
            "history_dir": str(history_dir),
            "report_json": str(tmp_path / "sfb11_report.json"),
            "report_md": str(tmp_path / "sfb11_report.md"),
        },
    }

    policy_path = tmp_path / "real_data_import_policy.json"
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    return policy_path


def test_sfb11b_generates_evidence_and_keeps_no_go(tmp_path: Path):
    evidence = _load_module("sfb11b_evidence", SCRIPTS / "generate_real_data_import_dry_run_evidence.py")

    incoming_csv = tmp_path / "incoming.csv"
    fixture_csv = tmp_path / "fixture.csv"
    history_dir = tmp_path / "history"
    report_json = tmp_path / "sfb11b_evidence.json"
    report_md = tmp_path / "sfb11b_evidence.md"

    fixture_csv.write_text(
        "source,title,author,isbn,asin,campaign,sale_status,confidence,note\nold,Old Row,Old Author,9781999999999,,OLD,candidate,0.80,old data\n",
        encoding="utf-8",
    )

    _write_csv(
        incoming_csv,
        [
            {
                "source": "manual_csv",
                "title": "Book A",
                "author": "Author A",
                "isbn": "9780000000001",
                "asin": "B0REAL00001",
                "campaign": "SUMMER_FLASH",
                "sale_status": "candidate",
                "confidence": "0.91",
                "note": "first",
            },
            {
                "source": "publisher_news_candidate",
                "title": "Book B",
                "author": "Author B",
                "isbn": "9780000000002",
                "asin": "",
                "campaign": "NEWS_DIGEST",
                "sale_status": "candidate",
                "confidence": "0.77",
                "note": "search candidate",
            },
        ],
    )

    policy_path = _build_policy(tmp_path, incoming_csv, fixture_csv, history_dir)

    def fake_run_block() -> dict:
        return {
            "status": "PASS",
            "mode": "DRY_RUN",
            "production_status": "NO_GO",
            "wordpress_write_executed": False,
            "external_api_called": False,
            "external_network_called": False,
            "steps": {
                "normalize": "PASS",
                "quality_gate": "PASS",
                "sfb10b_pre_production_baseline_lock_report": "PASS",
            },
        }

    result = evidence.generate_real_data_import_dry_run_evidence(
        policy_json=policy_path,
        input_csv=incoming_csv,
        fixture_csv=fixture_csv,
        report_json=report_json,
        report_md=report_md,
        run_block_fn=fake_run_block,
    )

    assert result["status"] == "PASS"
    assert result["no_go_maintained"] is True
    assert result["validation"]["accepted_row_count"] == 2
    assert result["import"]["imported_row_count"] == 2
    assert result["fixture_diff"]["changed"] is True
    assert report_json.exists()
    assert report_md.exists()


def test_sfb11b_fails_when_no_go_invariant_breaks(tmp_path: Path):
    evidence = _load_module("sfb11b_evidence_fail", SCRIPTS / "generate_real_data_import_dry_run_evidence.py")

    incoming_csv = tmp_path / "incoming.csv"
    fixture_csv = tmp_path / "fixture.csv"
    history_dir = tmp_path / "history"
    report_json = tmp_path / "sfb11b_evidence_fail.json"
    report_md = tmp_path / "sfb11b_evidence_fail.md"

    fixture_csv.write_text(
        "source,title,author,isbn,asin,campaign,sale_status,confidence,note\nold,Old Row,Old Author,9781999999999,,OLD,candidate,0.80,old data\n",
        encoding="utf-8",
    )

    _write_csv(
        incoming_csv,
        [
            {
                "source": "manual_csv",
                "title": "Book A",
                "author": "Author A",
                "isbn": "9780000000001",
                "asin": "B0REAL00001",
                "campaign": "SUMMER_FLASH",
                "sale_status": "candidate",
                "confidence": "0.91",
                "note": "first",
            }
        ],
    )

    policy_path = _build_policy(tmp_path, incoming_csv, fixture_csv, history_dir)

    def broken_run_block() -> dict:
        return {
            "status": "PASS",
            "mode": "DRY_RUN",
            "production_status": "GO",
            "wordpress_write_executed": False,
            "external_api_called": False,
            "external_network_called": False,
            "steps": {"normalize": "PASS"},
        }

    result = evidence.generate_real_data_import_dry_run_evidence(
        policy_json=policy_path,
        input_csv=incoming_csv,
        fixture_csv=fixture_csv,
        report_json=report_json,
        report_md=report_md,
        run_block_fn=broken_run_block,
    )

    assert result["status"] == "FAIL"
    assert result["no_go_maintained"] is False
    assert result["reason"] == "no_go_invariant_broken"
    assert report_json.exists()
    assert report_md.exists()
