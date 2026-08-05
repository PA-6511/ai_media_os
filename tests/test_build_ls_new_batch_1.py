from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "config/new_release_batch_input_schema.json"
EXAMPLE_CSV_PATH = (
    ROOT / "exchange/examples/new_release_batch_input.example.csv"
)
NORMALIZED_PATH = (
    ROOT / "exchange/examples/new_release_batch_normalized.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_1_result.json"
REPORT_PATH = ROOT / "reports/ls_new_batch_1_input_schema_report.md"
SCRIPT_PATH = ROOT / "scripts/build_ls_new_batch_1.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_example_rows() -> tuple[list[str], list[dict[str, str]]]:
    with EXAMPLE_CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def run_builder(
    input_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--input",
            str(input_path),
            "--check-only",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_schema_identity_and_contract_reference() -> None:
    schema = load_json(SCHEMA_PATH)

    assert schema["phase_id"] == "LS-NEW-BATCH-1"
    assert schema["schema_id"] == "NEW_RELEASE_BATCH_INPUT_SCHEMA_V1"
    assert (
        schema["template_contract_id"]
        == "POST185_STANDARD_TEMPLATE_V1_FIXED"
    )


def test_schema_has_exact_21_column_header() -> None:
    schema = load_json(SCHEMA_PATH)
    header, _ = read_example_rows()

    assert len(schema["header_order"]) == 21
    assert header == schema["header_order"]


def test_schema_blocks_all_live_operations() -> None:
    schema = load_json(SCHEMA_PATH)
    boundary = schema["execution_boundary"]

    assert boundary["normalized_json_write_allowed"] is True
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["external_api_call_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "DRY_RUN_ONLY"


def test_example_is_normalized_to_typed_json() -> None:
    normalized = load_json(NORMALIZED_PATH)
    record = normalized["records"][0]

    assert normalized["record_count"] == 1
    assert record["authors"] == ["著者A", "著者B"]
    assert record["x_post_required"] is True
    assert record["prices_jpy"]["amazon"] is None
    assert record["store_links"]["amazon"] is None
    assert record["wordpress_status"] == "draft"


def test_idempotency_key_is_generated() -> None:
    normalized = load_json(NORMALIZED_PATH)
    key = normalized["records"][0]["idempotency_key"]

    assert isinstance(key, str)
    assert len(key) == 64
    assert all(character in "0123456789abcdef" for character in key)


def test_check_only_passes_without_live_execution() -> None:
    completed = run_builder(EXAMPLE_CSV_PATH)

    assert completed.returncode == 0

    result = json.loads(completed.stdout)

    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["wordpress_write_allowed"] is False
    assert result["x_post_allowed"] is False
    assert result["ready_for_ls_new_batch_2"] is True
    assert result["ready_for_x_fb_0"] is True


def test_duplicate_item_id_is_rejected(tmp_path: Path) -> None:
    header, rows = read_example_rows()

    duplicate_csv = tmp_path / "duplicate.csv"

    with duplicate_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerow(rows[0])
        writer.writerow(rows[0])

    completed = run_builder(duplicate_csv)

    assert completed.returncode == 1
    assert "duplicate item_id detected" in completed.stderr


def test_dummy_url_is_rejected(tmp_path: Path) -> None:
    header, rows = read_example_rows()
    row = dict(rows[0])
    row["amazon_url"] = "https://example.com/dummy-product"

    dummy_url_csv = tmp_path / "dummy-url.csv"

    with dummy_url_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerow(row)

    completed = run_builder(dummy_url_csv)

    assert completed.returncode == 1
    assert "must not use a dummy URL" in completed.stderr


def test_generated_evidence_is_safe_and_complete() -> None:
    assert RESULT_PATH.exists()
    assert REPORT_PATH.exists()

    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["production_status"] == "NO_GO"
    assert result["safety_state"] == "DRY_RUN_ONLY"
    assert result["next_phase_execution_allowed"] is False
    assert "WordPress write allowed: `false`" in report
    assert "X posting allowed: `false`" in report
