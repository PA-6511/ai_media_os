#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.integrations.rakuten_kobo_api_client import (
    GetOnlyTransport,
    RakutenKoboApiClient,
    RakutenKoboApiError,
    RakutenKoboRequestConfiguration,
    RequestsGetTransport,
)
from app.integrations.rakuten_kobo_live_configuration import (
    load_repository_live_configuration,
)
from app.services.rakuten_kobo_collector import (
    RakutenKoboCollector,
    RakutenKoboCollectorError,
)
from scripts.convert_rakuten_kobo_response_to_csv import write_response_csv


DEFAULT_OUTPUT_DIRECTORY = Path("exchange/raw/rakuten_kobo")
DEFAULT_EVIDENCE_DIRECTORY = Path("exchange/logs/rakuten_kobo_collection")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Safely collect or validate an immutable Rakuten Kobo JSON response. "
            "The default performs no network, CSV, database, or WordPress action."
        )
    )
    parser.add_argument("--execute-fetch", action="store_true")
    parser.add_argument("--confirm-get-only", action="store_true")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    parser.add_argument(
        "--evidence-directory",
        type=Path,
        default=DEFAULT_EVIDENCE_DIRECTORY,
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help="Validate a previously collector-saved raw JSON without network access.",
    )
    parser.add_argument(
        "--convert-csv",
        type=Path,
        help="Explicitly convert --input-json using the existing converter.",
    )
    parser.add_argument("--batch-id")
    parser.add_argument("--verified-at")
    parser.add_argument("--title")
    parser.add_argument("--item-number")
    return parser


def execute_cli(
    argv: Sequence[str] | None = None,
    *,
    repository_root: Path = ROOT,
    transport: GetOnlyTransport | None = None,
    live_configuration_loader: Callable[
        ..., RakutenKoboRequestConfiguration | None
    ] = load_repository_live_configuration,
) -> dict[str, object]:
    arguments = list(argv or ())
    args = build_parser().parse_args(arguments)
    root = repository_root.resolve(strict=True)
    output_directory = _under_root(root, args.output_directory)
    evidence_directory = _under_root(root, args.evidence_directory)
    collector = RakutenKoboCollector(
        repository_root=root,
        output_directory=output_directory,
        evidence_directory=evidence_directory,
    )

    if args.convert_csv is not None:
        if args.input_json is None or not args.batch_id or not args.verified_at:
            return _offline_result(
                "CONVERTER_ARGUMENTS_REQUIRED",
                error_summary="--input-json, --batch-id, and --verified-at are required",
            )
        raw, inspection = collector.load_saved_response(args.input_json)
        if not inspection.converter_ready:
            return _offline_result(
                "SAVED_RESPONSE_NOT_CONVERTER_READY",
                converter_ready=False,
                error_summary=inspection.error_summary,
            )
        output_csv = _under_root(root, args.convert_csv)
        response = json.loads(raw.decode("utf-8"))
        rows = write_response_csv(
            response,
            output_path=output_csv,
            batch_id=args.batch_id,
            verified_at=args.verified_at,
        )
        return _offline_result(
            "CSV_CREATED",
            converter_ready=True,
            csv_created=True,
            output_csv=_display_path(output_csv, root),
            converted_row_count=len(rows),
        )

    if args.input_json is not None:
        try:
            inspection = collector.validate_saved_response(args.input_json)
        except RakutenKoboCollectorError as exc:
            return _offline_result("VALIDATION_FAILED", error_summary=exc.safe_summary)
        return _offline_result(
            "VALIDATION_PASS" if inspection.converter_ready else "VALIDATION_FAILED",
            converter_ready=inspection.converter_ready,
            error_summary=inspection.error_summary,
        )

    if not args.execute_fetch:
        return _offline_result("DRY_RUN")
    if not args.confirm_get_only:
        return _offline_result("BLOCKED_CONFIRM_GET_ONLY_REQUIRED")
    if not _option_was_supplied(arguments, "--output-directory"):
        return _offline_result("BLOCKED_OUTPUT_DIRECTORY_CONFIRMATION_REQUIRED")
    expected_output = root / DEFAULT_OUTPUT_DIRECTORY
    if output_directory != expected_output:
        return _offline_result("BLOCKED_OUTPUT_DIRECTORY_MISMATCH")
    expected_evidence = root / DEFAULT_EVIDENCE_DIRECTORY
    if evidence_directory != expected_evidence:
        return _offline_result("BLOCKED_EVIDENCE_DIRECTORY_MISMATCH")

    title = str(args.title or "").strip() or None
    item_number = str(args.item_number or "").strip() or None
    if title is None and item_number is None:
        return _offline_result("BLOCKED_SEARCH_SELECTOR_REQUIRED")
    selector_type = (
        "title+itemNumber"
        if title is not None and item_number is not None
        else "title"
        if title is not None
        else "itemNumber"
    )
    try:
        configuration = live_configuration_loader(
            title=title,
            item_number=item_number,
        )
    except RakutenKoboApiError as exc:
        return _offline_result("NOT_CONFIGURED", error_summary=exc.safe_summary)
    if configuration is None:
        return _offline_result(
            "NOT_CONFIGURED",
            error_summary="Rakuten Kobo API credentials are not configured",
        )
    client = RakutenKoboApiClient(transport or RequestsGetTransport())
    try:
        response = client.fetch(configuration)
    except RakutenKoboApiError as exc:
        outcome = collector.record_fetch_failure(
            endpoint_host=configuration.endpoint_host,
            error_summary=exc.safe_summary,
            external_get_attempted=True,
            search_selector_type=selector_type,
            failure_details=exc.failure_details,
        )
        return _outcome_result(outcome)
    return _outcome_result(
        collector.collect_fetched_response(
            response,
            search_selector_type=selector_type,
        )
    )


def _outcome_result(outcome) -> dict[str, object]:
    return {
        "status": outcome.status,
        "collection_id": outcome.collection_id,
        "raw_response_path": (
            str(outcome.evidence.get("raw_response_path"))
            if outcome.raw_response_path is not None
            else None
        ),
        "evidence_path": str(outcome.evidence_path),
        "converter_ready": outcome.converter_ready,
        "duplicate_detected": outcome.duplicate_detected,
        "raw_response_saved": bool(
            outcome.evidence["raw_save_succeeded"]
        ),
        "external_get_attempted": bool(
            outcome.evidence["external_get_attempted"]
        ),
        "external_get_succeeded": bool(
            outcome.evidence["external_get_succeeded"]
        ),
        "csv_created": False,
        "database_write_performed": False,
        "wordpress_write_performed": False,
    }


def _offline_result(
    status: str,
    *,
    converter_ready: bool = False,
    csv_created: bool = False,
    error_summary: str | None = None,
    output_csv: str | None = None,
    converted_row_count: int | None = None,
) -> dict[str, object]:
    return {
        "status": status,
        "external_get_attempted": False,
        "external_get_succeeded": False,
        "raw_save_attempted": False,
        "raw_save_succeeded": False,
        "raw_response_saved": False,
        "converter_ready": converter_ready,
        "csv_created": csv_created,
        "output_csv": output_csv,
        "converted_row_count": converted_row_count,
        "database_write_performed": False,
        "wordpress_write_performed": False,
        "error_summary": error_summary,
    }


def _under_root(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    normalized = Path(candidate).absolute()
    try:
        normalized.relative_to(root)
    except ValueError as exc:
        raise RakutenKoboCollectorError("PATH_OUTSIDE_REPOSITORY", cause=exc) from exc
    return normalized


def _option_was_supplied(arguments: Sequence[str], option: str) -> bool:
    return any(value == option or value.startswith(option + "=") for value in arguments)


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = execute_cli(sys.argv[1:] if argv is None else argv)
    except RakutenKoboCollectorError as exc:
        result = _offline_result("FAILED", error_summary=exc.safe_summary)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["status"] in {"DRY_RUN", "VALIDATION_PASS", "CSV_CREATED", "PASS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
