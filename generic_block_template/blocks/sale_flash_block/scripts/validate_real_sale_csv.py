#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BLOCK_DIR = Path(__file__).resolve().parents[1]
POLICY_JSON = BLOCK_DIR / "config/real_data_import_policy.json"
INPUT_CSV = BLOCK_DIR / "data/incoming/sale_flash_candidates.csv"
REPORT_JSON = BLOCK_DIR / "logs/real_sale_csv_import_report.json"
REPORT_MD = BLOCK_DIR / "logs/real_sale_csv_import_report.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(base: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base / path)


def _row_duplicate_key(row: Dict[str, str]) -> str:
    asin = (row.get("asin") or "").strip().lower()
    if asin:
        return f"asin::{asin}"

    isbn = (row.get("isbn") or "").strip().lower()
    if isbn:
        return f"isbn::{isbn}"

    title = (row.get("title") or "").strip().lower()
    author = (row.get("author") or "").strip().lower()
    return f"title_author::{title}::{author}"


def _validate_row(
    row: Dict[str, str],
    required_non_empty: List[str],
    allowed_sources: List[str],
    allowed_sale_status: List[str],
    confidence_min: float,
    confidence_max: float,
    require_isbn_or_asin: bool,
) -> Tuple[List[str], Dict[str, Any]]:
    errors: List[str] = []
    normalized: Dict[str, Any] = {}

    for key, value in row.items():
        normalized[key] = (value or "").strip()

    for col in required_non_empty:
        if normalized.get(col, "") == "":
            errors.append(f"missing_required_value:{col}")

    source = normalized.get("source", "")
    if source and source not in allowed_sources:
        errors.append("invalid_source")

    sale_status = normalized.get("sale_status", "")
    if sale_status and sale_status not in allowed_sale_status:
        errors.append("invalid_sale_status")

    confidence_raw = normalized.get("confidence", "")
    if confidence_raw:
        try:
            confidence = float(confidence_raw)
            if confidence < confidence_min or confidence > confidence_max:
                errors.append("confidence_out_of_range")
        except ValueError:
            errors.append("invalid_confidence")
    else:
        errors.append("missing_required_value:confidence")

    if require_isbn_or_asin:
        if normalized.get("isbn", "") == "" and normalized.get("asin", "") == "":
            errors.append("isbn_or_asin_required")

    return errors, normalized


def _write_markdown(report: Dict[str, Any], output_md: Path) -> None:
    lines = [
        "# SFB-11 Real Sale CSV Import Report",
        "",
        f"- generated_at: {report.get('generated_at', '')}",
        f"- status: {report.get('status', 'FAIL')}",
        f"- phase: {report.get('phase', 'SFB-11')}",
        f"- input_csv: {report.get('input_csv', '')}",
        f"- total_rows: {report.get('total_rows', 0)}",
        f"- accepted_rows: {report.get('accepted_row_count', 0)}",
        f"- invalid_rows: {report.get('invalid_row_count', 0)}",
        f"- duplicate_rows: {report.get('duplicate_row_count', 0)}",
        "",
        "## Invalid Rows",
    ]

    invalid_rows = report.get("invalid_rows", [])
    if not invalid_rows:
        lines.append("- none")
    else:
        for item in invalid_rows[:20]:
            lines.append(
                f"- row {item.get('row_number')}: {', '.join(item.get('errors', []))}"
            )

    lines.extend(["", "## Duplicate Rows"])
    duplicate_rows = report.get("duplicate_rows", [])
    if not duplicate_rows:
        lines.append("- none")
    else:
        for item in duplicate_rows[:20]:
            lines.append(
                f"- row {item.get('row_number')}: duplicate_key={item.get('duplicate_key', '')}"
            )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_real_sale_csv(
    policy_json: Path = POLICY_JSON,
    input_csv: Path = INPUT_CSV,
    report_json: Path = REPORT_JSON,
    report_md: Path = REPORT_MD,
    write_report: bool = True,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-11",
        "generated_at": _iso_now(),
        "production_status": "NO_GO",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "input_csv": str(input_csv),
        "total_rows": 0,
        "accepted_row_count": 0,
        "invalid_row_count": 0,
        "duplicate_row_count": 0,
        "accepted_rows": [],
        "invalid_rows": [],
        "duplicate_rows": [],
    }

    try:
        policy = _read_json(policy_json)
        required_columns = list(policy.get("required_columns", []))
        required_non_empty = list(policy.get("required_non_empty_columns", []))
        allowed_sources = list(policy.get("allowed_sources", []))
        allowed_sale_status = list(policy.get("allowed_sale_status", []))
        confidence_cfg = policy.get("confidence_range", {})
        confidence_min = float(confidence_cfg.get("min", 0.0))
        confidence_max = float(confidence_cfg.get("max", 1.0))
        require_isbn_or_asin = bool(policy.get("require_isbn_or_asin", True))
        max_rows = int(policy.get("max_rows_per_import", 200))
        strict_stop = bool(policy.get("strict_stop_on_invalid_rows", True))
        duplicate_strategy = str(policy.get("duplicate_strategy", "keep_first"))

        with input_csv.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = list(reader.fieldnames or [])
            missing_columns = sorted(set(required_columns) - set(fields))
            if missing_columns:
                raise ValueError("missing required columns: " + ", ".join(missing_columns))

            seen_keys: set[str] = set()
            total_rows = 0

            for idx, row in enumerate(reader, start=2):
                total_rows += 1
                if total_rows > max_rows:
                    payload["invalid_rows"].append(
                        {
                            "row_number": idx,
                            "errors": ["max_rows_exceeded"],
                        }
                    )
                    continue

                row_errors, normalized = _validate_row(
                    row=row,
                    required_non_empty=required_non_empty,
                    allowed_sources=allowed_sources,
                    allowed_sale_status=allowed_sale_status,
                    confidence_min=confidence_min,
                    confidence_max=confidence_max,
                    require_isbn_or_asin=require_isbn_or_asin,
                )

                if row_errors:
                    payload["invalid_rows"].append(
                        {
                            "row_number": idx,
                            "errors": row_errors,
                            "row": normalized,
                        }
                    )
                    continue

                duplicate_key = _row_duplicate_key(normalized)
                if duplicate_key in seen_keys:
                    payload["duplicate_rows"].append(
                        {
                            "row_number": idx,
                            "duplicate_key": duplicate_key,
                            "row": normalized,
                        }
                    )
                    if duplicate_strategy == "keep_first":
                        continue

                seen_keys.add(duplicate_key)
                payload["accepted_rows"].append(normalized)

            payload["total_rows"] = total_rows

            payload["accepted_row_count"] = len(payload["accepted_rows"])
            payload["invalid_row_count"] = len(payload["invalid_rows"])
            payload["duplicate_row_count"] = len(payload["duplicate_rows"])

            if payload["invalid_row_count"] > 0 and strict_stop:
                payload["status"] = "FAIL"
            elif payload["accepted_row_count"] == 0:
                payload["status"] = "WARN"
            elif payload["duplicate_row_count"] > 0:
                payload["status"] = "WARN"
            else:
                payload["status"] = "PASS"

    except Exception as exc:
        payload["status"] = "FAIL"
        payload["error"] = str(exc)

    if write_report:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_markdown(payload, report_md)

    return payload


def main() -> int:
    result = validate_real_sale_csv()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
