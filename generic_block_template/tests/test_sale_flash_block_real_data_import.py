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


def _build_policy(tmp_path: Path, incoming_csv: Path, fixture_csv: Path, report_json: Path, report_md: Path, history_dir: Path) -> Path:
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
            "report_json": str(report_json),
            "report_md": str(report_md),
        },
    }

    policy_path = tmp_path / "real_data_import_policy.json"
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    return policy_path


def test_sfb11_validation_fails_on_invalid_rows(tmp_path: Path):
    validate = _load_module("sfb11_validate", SCRIPTS / "validate_real_sale_csv.py")

    incoming_csv = tmp_path / "incoming.csv"
    fixture_csv = tmp_path / "fixture.csv"
    report_json = tmp_path / "report.json"
    report_md = tmp_path / "report.md"
    history_dir = tmp_path / "history"

    _write_csv(
        incoming_csv,
        [
            {
                "source": "manual_csv",
                "title": "Valid Title",
                "author": "Valid Author",
                "isbn": "9780000000001",
                "asin": "",
                "campaign": "SUMMER_FLASH",
                "sale_status": "candidate",
                "confidence": "0.90",
                "note": "ok",
            },
            {
                "source": "manual_csv",
                "title": "",
                "author": "Missing Title",
                "isbn": "",
                "asin": "",
                "campaign": "SUMMER_FLASH",
                "sale_status": "candidate",
                "confidence": "not-a-number",
                "note": "invalid row",
            },
        ],
    )

    policy_path = _build_policy(tmp_path, incoming_csv, fixture_csv, report_json, report_md, history_dir)

    result = validate.validate_real_sale_csv(
        policy_json=policy_path,
        input_csv=incoming_csv,
        report_json=report_json,
        report_md=report_md,
    )

    assert result["status"] == "FAIL"
    assert result["invalid_row_count"] == 1
    assert result["accepted_row_count"] == 1
    assert report_json.exists()
    assert report_md.exists()


def test_sfb11_import_writes_fixture_and_backups(tmp_path: Path):
    importer = _load_module("sfb11_import", SCRIPTS / "import_real_sale_csv_to_fixture.py")

    incoming_csv = tmp_path / "incoming.csv"
    fixture_csv = tmp_path / "fixture.csv"
    report_json = tmp_path / "report.json"
    report_md = tmp_path / "report.md"
    history_dir = tmp_path / "history"

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
                "source": "manual_csv",
                "title": "Book A duplicate",
                "author": "Author A",
                "isbn": "9780000000001",
                "asin": "B0REAL00001",
                "campaign": "SUMMER_FLASH",
                "sale_status": "candidate",
                "confidence": "0.82",
                "note": "duplicate by asin",
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
                "note": "valid search candidate",
            },
        ],
    )

    policy_path = _build_policy(tmp_path, incoming_csv, fixture_csv, report_json, report_md, history_dir)

    result = importer.import_real_sale_csv_to_fixture(
        policy_json=policy_path,
        input_csv=incoming_csv,
        fixture_csv=fixture_csv,
        report_json=report_json,
        report_md=report_md,
    )

    assert result["status"] == "PASS"
    assert result["imported_row_count"] == 2
    assert len(result["backup_artifacts"]) >= 2

    fixture_rows = list(csv.DictReader(fixture_csv.open("r", encoding="utf-8", newline="")))
    assert len(fixture_rows) == 2
    assert fixture_rows[0]["asin"] == "B0REAL00001"
    assert fixture_rows[1]["title"] == "Book B"

    assert report_json.exists()
    assert report_md.exists()
