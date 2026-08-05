#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "config/new_release_batch_input_schema.json"
CONTRACT_PATH = ROOT / "config/post185_standard_template_contract.json"

DEFAULT_INPUT_PATH = (
    ROOT / "exchange/examples/new_release_batch_input.example.csv"
)
DEFAULT_OUTPUT_PATH = (
    ROOT / "exchange/examples/new_release_batch_normalized.example.json"
)

RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_1_result.json"
REPORT_PATH = ROOT / "reports/ls_new_batch_1_input_schema_report.md"

PRICE_PATTERN = re.compile(r"^[0-9]+$")

DUMMY_HOSTS = {
    "example.com",
    "www.example.com",
    "example.org",
    "www.example.org",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"required file missing: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"JSON root must be an object: {path}")

    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    return unicodedata.normalize("NFKC", value.strip())


def parse_boolean(
    value: str,
    field_name: str,
    row_number: int,
) -> bool:
    normalized = normalize_text(value).lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValidationError(
        f"row {row_number}: {field_name} must be true or false"
    )


def parse_price(
    value: str,
    field_name: str,
    row_number: int,
) -> int | None:
    normalized = normalize_text(value)

    if normalized == "":
        return None

    if not PRICE_PATTERN.fullmatch(normalized):
        raise ValidationError(
            f"row {row_number}: {field_name} must be "
            "a non-negative integer without commas"
        )

    return int(normalized)


def parse_release_date(value: str, row_number: int) -> str:
    normalized = normalize_text(value)

    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"row {row_number}: release_date must use YYYY-MM-DD"
        ) from exc

    return parsed.isoformat()


def parse_url(
    value: str,
    field_name: str,
    row_number: int,
) -> str | None:
    normalized = normalize_text(value)

    if normalized == "":
        return None

    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").lower()

    if parsed.scheme != "https" or not hostname:
        raise ValidationError(
            f"row {row_number}: {field_name} must be a valid HTTPS URL"
        )

    if (
        hostname in DUMMY_HOSTS
        or hostname.endswith(".example")
        or "placeholder" in hostname
        or "dummy" in hostname
    ):
        raise ValidationError(
            f"row {row_number}: {field_name} must not use a dummy URL"
        )

    return normalized


def validate_schema(
    schema: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        schema.get("phase_id") == "LS-NEW-BATCH-1",
        "schema phase_id mismatch",
    )
    checks.append("schema_phase_id")

    require(
        schema.get("schema_id") == "NEW_RELEASE_BATCH_INPUT_SCHEMA_V1",
        "schema_id mismatch",
    )
    checks.append("schema_identity")

    require(
        contract.get("contract_id")
        == "POST185_STANDARD_TEMPLATE_V1_FIXED",
        "post 185 template contract is not fixed",
    )
    require(
        schema.get("template_contract_id")
        == contract.get("contract_id"),
        "schema template contract reference mismatch",
    )
    checks.append("post185_contract_reference")

    header_order = schema.get("header_order")
    required_fields = schema.get("required_fields")
    nullable_fields = schema.get("nullable_fields")

    require(
        isinstance(header_order, list) and len(header_order) == 21,
        "header_order must contain 21 fields",
    )
    require(
        len(header_order) == len(set(header_order)),
        "header_order contains duplicate field names",
    )
    require(
        isinstance(required_fields, list),
        "required_fields must be a list",
    )
    require(
        isinstance(nullable_fields, list),
        "nullable_fields must be a list",
    )
    require(
        set(required_fields).issubset(set(header_order)),
        "required_fields contains an unknown field",
    )
    require(
        set(nullable_fields).issubset(set(header_order)),
        "nullable_fields contains an unknown field",
    )
    checks.append("header_and_field_definition")

    boundary = schema.get("execution_boundary", {})

    require(
        boundary.get("normalized_json_write_allowed") is True,
        "normalized JSON write must be allowed",
    )
    require(
        boundary.get("wordpress_write_allowed") is False,
        "WordPress write must remain blocked",
    )
    require(
        boundary.get("wordpress_publish_allowed") is False,
        "WordPress publish must remain blocked",
    )
    require(
        boundary.get("x_post_allowed") is False,
        "X posting must remain blocked",
    )
    require(
        boundary.get("external_api_call_allowed") is False,
        "external API calls must remain blocked",
    )
    require(
        boundary.get("production_status") == "NO_GO",
        "production status must be NO_GO",
    )
    require(
        boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety state must be DRY_RUN_ONLY",
    )
    checks.append("execution_boundary")

    return checks


def determine_item_status(record: dict[str, Any]) -> str:
    store_urls = [
        record["store_links"]["amazon"],
        record["store_links"]["rakuten_kobo"],
        record["store_links"]["dmm"],
    ]

    prices = [
        record["prices_jpy"]["amazon"],
        record["prices_jpy"]["rakuten_kobo"],
        record["prices_jpy"]["dmm"],
    ]

    if all(url is None for url in store_urls):
        return "STORE_PAGE_NOT_FOUND"

    if record["image"]["url"] is None:
        return "MISSING_IMAGE"

    if all(price is None for price in prices):
        return "NEEDS_PRICE_CONFIRMATION"

    return "READY_FOR_DRAFT"


def build_idempotency_key(
    batch_id: str,
    item_id: str,
    title: str,
    volume_label: str,
    release_date_value: str,
) -> str:
    source = "\x1f".join(
        [
            batch_id,
            item_id,
            title,
            volume_label,
            release_date_value,
        ]
    )

    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def normalize_row(
    row: dict[str, str],
    row_number: int,
    schema: dict[str, Any],
) -> dict[str, Any]:
    required_fields = schema["required_fields"]
    allowed_values = schema["allowed_values"]

    values = {
        field: normalize_text(row.get(field))
        for field in schema["header_order"]
    }

    for field in required_fields:
        if values[field] == "":
            raise ValidationError(
                f"row {row_number}: required field is blank: {field}"
            )

    category = values["category"]
    image_source = values["image_source"]
    description_mode = values["description_mode"]
    wordpress_status = values["wordpress_status"]

    if category not in allowed_values["category"]:
        raise ValidationError(
            f"row {row_number}: unsupported category: {category}"
        )

    if image_source not in allowed_values["image_source"]:
        raise ValidationError(
            f"row {row_number}: unsupported image_source: {image_source}"
        )

    if description_mode not in allowed_values["description_mode"]:
        raise ValidationError(
            f"row {row_number}: unsupported description_mode: "
            f"{description_mode}"
        )

    if wordpress_status not in allowed_values["wordpress_status"]:
        raise ValidationError(
            f"row {row_number}: wordpress_status must remain draft"
        )

    authors = [
        normalize_text(author)
        for author in values["authors"].split(
            schema["multi_value_separator"]
        )
        if normalize_text(author)
    ]

    if not authors:
        raise ValidationError(
            f"row {row_number}: authors must contain at least one name"
        )

    release_date_value = parse_release_date(
        values["release_date"],
        row_number,
    )

    publisher_confirmation_url = parse_url(
        values["publisher_confirmation_url"],
        "publisher_confirmation_url",
        row_number,
    )
    amazon_url = parse_url(
        values["amazon_url"],
        "amazon_url",
        row_number,
    )
    rakuten_kobo_url = parse_url(
        values["rakuten_kobo_url"],
        "rakuten_kobo_url",
        row_number,
    )
    dmm_url = parse_url(
        values["dmm_url"],
        "dmm_url",
        row_number,
    )
    image_url = parse_url(
        values["image_url"],
        "image_url",
        row_number,
    )

    if image_source == "none" and image_url is not None:
        raise ValidationError(
            f"row {row_number}: image_source none cannot have image_url"
        )

    record: dict[str, Any] = {
        "source_row_number": row_number,
        "batch_id": values["batch_id"],
        "item_id": values["item_id"],
        "title": values["title"],
        "volume_label": values["volume_label"],
        "release_date": release_date_value,
        "publisher": values["publisher"],
        "authors": authors,
        "category": category,
        "source": {
            "discovery": values["source_discovery"],
            "publisher_confirmation_url": publisher_confirmation_url,
        },
        "store_links": {
            "amazon": amazon_url,
            "rakuten_kobo": rakuten_kobo_url,
            "dmm": dmm_url,
        },
        "prices_jpy": {
            "amazon": parse_price(
                values["amazon_price_jpy"],
                "amazon_price_jpy",
                row_number,
            ),
            "rakuten_kobo": parse_price(
                values["rakuten_kobo_price_jpy"],
                "rakuten_kobo_price_jpy",
                row_number,
            ),
            "dmm": parse_price(
                values["dmm_price_jpy"],
                "dmm_price_jpy",
                row_number,
            ),
        },
        "image": {
            "source": image_source,
            "url": image_url,
        },
        "description_mode": description_mode,
        "x_post_required": parse_boolean(
            values["x_post_required"],
            "x_post_required",
            row_number,
        ),
        "wordpress_status": wordpress_status,
    }

    record["idempotency_key"] = build_idempotency_key(
        batch_id=record["batch_id"],
        item_id=record["item_id"],
        title=record["title"],
        volume_label=record["volume_label"],
        release_date_value=record["release_date"],
    )

    record["item_status"] = determine_item_status(record)

    return record


def load_and_normalize_csv(
    input_path: Path,
    schema: dict[str, Any],
) -> dict[str, Any]:
    if not input_path.exists():
        raise ValidationError(f"input CSV missing: {input_path}")

    with input_path.open(
        "r",
        encoding=schema["encoding"],
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter=schema["delimiter"],
        )

        actual_header = reader.fieldnames or []
        expected_header = schema["header_order"]

        if actual_header != expected_header:
            raise ValidationError(
                "CSV header mismatch. "
                f"expected={expected_header}, actual={actual_header}"
            )

        records: list[dict[str, Any]] = []

        for row_number, row in enumerate(reader, start=2):
            if all(normalize_text(value) == "" for value in row.values()):
                continue

            records.append(
                normalize_row(
                    row=row,
                    row_number=row_number,
                    schema=schema,
                )
            )

    if not records:
        raise ValidationError("input CSV contains no data records")

    batch_ids = {record["batch_id"] for record in records}

    if len(batch_ids) != 1:
        raise ValidationError(
            "one CSV file must contain exactly one batch_id"
        )

    item_ids: set[str] = set()
    composite_keys: set[tuple[str, str, str]] = set()

    for record in records:
        item_id = record["item_id"]

        if item_id in item_ids:
            raise ValidationError(
                f"duplicate item_id detected: {item_id}"
            )

        item_ids.add(item_id)

        composite_key = (
            normalize_text(record["title"]).casefold(),
            normalize_text(record["volume_label"]).casefold(),
            record["release_date"],
        )

        if composite_key in composite_keys:
            raise ValidationError(
                "duplicate title/volume/release_date detected: "
                f"{record['title']} {record['volume_label']} "
                f"{record['release_date']}"
            )

        composite_keys.add(composite_key)

    batch_id = next(iter(batch_ids))
    status_counts = dict(
        sorted(
            Counter(
                record["item_status"]
                for record in records
            ).items()
        )
    )

    return {
        "schema_version": "1.0.0",
        "schema_id": schema["schema_id"],
        "template_contract_id": schema["template_contract_id"],
        "batch_id": batch_id,
        "record_count": len(records),
        "item_status_counts": status_counts,
        "records": records,
        "execution_boundary": {
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
        },
    }


def build_result(
    schema_checks: list[str],
    normalized: dict[str, Any],
    input_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    return {
        "phase_id": "LS-NEW-BATCH-1",
        "status": "PASS_DESIGN_ONLY_NO_EXECUTION",
        "decision": "CSV_TO_NORMALIZED_JSON_INPUT_BASELINE_READY",
        "schema_id": normalized["schema_id"],
        "template_contract_id": normalized["template_contract_id"],
        "input_path": str(input_path.relative_to(ROOT)),
        "normalized_output_path": str(output_path.relative_to(ROOT)),
        "normalized_record_count": normalized["record_count"],
        "item_status_counts": normalized["item_status_counts"],
        "verified_checks": schema_checks
        + [
            "csv_header_exact_match",
            "required_field_validation",
            "type_normalization",
            "blank_to_null",
            "duplicate_detection",
            "idempotency_key_generation",
        ],
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_post_allowed": False,
        "external_api_call_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "ready_for_ls_new_batch_2": True,
        "ready_for_x_fb_0": True,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    statuses = "\n".join(
        f"- `{status}`: {count}"
        for status, count in result["item_status_counts"].items()
    )

    return f"""# LS-NEW-BATCH-1 Input Schema Report

## Result

- Phase: `LS-NEW-BATCH-1`
- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Schema: `{result["schema_id"]}`
- Template contract: `{result["template_contract_id"]}`
- Input: `{result["input_path"]}`
- Normalized output: `{result["normalized_output_path"]}`
- Record count: `{result["normalized_record_count"]}`

## Item Statuses

{statuses}

## Safety Boundary

- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X posting allowed: `false`
- External API call allowed: `false`
- Production status: `NO_GO`
- Safety state: `DRY_RUN_ONLY`

## Verified Checks

{checks}

## Next State

- `LS-NEW-BATCH-2` の新刊情報確認・正規化DRY RUNへ進行可能
- `X-FB-0` のX文言フィードバック記録基盤へ進行可能
- WordPress下書き作成、公開、X投稿は未許可
"""


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Source CSV path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Normalized JSON output path.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate and normalize in memory without writing files.",
    )

    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def main() -> int:
    args = parse_args()

    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    try:
        schema = load_json(SCHEMA_PATH)
        contract = load_json(CONTRACT_PATH)

        schema_checks = validate_schema(
            schema=schema,
            contract=contract,
        )

        normalized = load_and_normalize_csv(
            input_path=input_path,
            schema=schema,
        )

        result = build_result(
            schema_checks=schema_checks,
            normalized=normalized,
            input_path=input_path,
            output_path=output_path,
        )

        if not args.check_only:
            write_json(output_path, normalized)
            write_json(RESULT_PATH, result)

            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(
                build_report(result),
                encoding="utf-8",
            )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": "LS-NEW-BATCH-1",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "wordpress_write_allowed": False,
                    "external_api_call_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
