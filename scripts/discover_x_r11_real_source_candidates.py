from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "REAL-SOURCE-DISCOVERY"
)

SUPPORTED_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "exchange",
    "reports",
    "tests",
    "migrations",
    "node_modules",
    "backup",
    "backups",
    "archive",
}

TITLE_COLUMNS = (
    "title",
    "book_title",
    "product_title",
    "作品名",
    "書名",
)

RELEASE_DATE_COLUMNS = (
    "release_date",
    "publication_date",
    "発売日",
    "配信日",
)

PUBLISHER_COLUMNS = (
    "publisher",
    "publisher_name",
    "出版社",
)

ITEM_ID_COLUMNS = (
    "ebook_item_id",
    "item_id",
    "product_id",
    "isbn",
)

URL_COLUMNS = (
    "amazon_url",
    "amazon_affiliate_url",
    "rakuten_url",
    "rakuten_kobo_url",
    "dmm_url",
    "dmm_books_url",
    "affiliate_url",
    "product_url",
    "store_url",
    "url",
)

SYNTHETIC_TITLE_TOKENS = (
    "sample",
    "test",
    "dummy",
    "demo",
    "fixture",
    "サンプル",
    "テスト",
    "ダミー",
    "デモ",
    "検証用",
    "動作確認",
)

PLACEHOLDER_HOSTS = {
    "example.com",
    "www.example.com",
    "example.org",
    "www.example.org",
    "example.net",
    "www.example.net",
    "localhost",
    "127.0.0.1",
    "::1",
}

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MAX_ROWS_PER_FILE = 2000


class RealSourceDiscoveryError(RuntimeError):
    """Raised when real-source discovery cannot proceed."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RealSourceDiscoveryError(message)


def first_value(
    row: dict[str, Any],
    columns: tuple[str, ...],
) -> Any:
    for column in columns:
        value = row.get(column)

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


def is_synthetic_title(
    value: Any,
) -> bool:
    title = str(
        value or ""
    ).strip().lower()

    if not title:
        return True

    return any(
        token in title
        for token in SYNTHETIC_TITLE_TOKENS
    )


def assess_url(
    value: Any,
) -> dict[str, Any]:
    raw_url = str(
        value or ""
    ).strip()

    if not raw_url:
        return {
            "url": None,
            "host": None,
            "valid": False,
            "reason": "URL_MISSING",
        }

    parsed = urlparse(raw_url)
    host = (
        parsed.hostname or ""
    ).lower()

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return {
            "url": raw_url,
            "host": host or None,
            "valid": False,
            "reason": "URL_SCHEME_INVALID",
        }

    if not host:
        return {
            "url": raw_url,
            "host": None,
            "valid": False,
            "reason": "URL_HOST_MISSING",
        }

    if host in PLACEHOLDER_HOSTS:
        return {
            "url": raw_url,
            "host": host,
            "valid": False,
            "reason": "PLACEHOLDER_URL",
        }

    return {
        "url": raw_url,
        "host": host,
        "valid": True,
        "reason": None,
    }


def collect_urls(
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    assessments: list[dict[str, Any]] = []

    for column in URL_COLUMNS:
        value = row.get(column)

        if value in (
            None,
            "",
        ):
            continue

        assessment = assess_url(value)
        assessment["source_column"] = column
        assessments.append(assessment)

    store_offers = row.get(
        "store_offers"
    )

    if isinstance(store_offers, list):
        for index, offer in enumerate(
            store_offers,
            start=1,
        ):
            if not isinstance(offer, dict):
                continue

            value = first_value(
                offer,
                URL_COLUMNS,
            )

            if value in (
                None,
                "",
            ):
                continue

            assessment = assess_url(value)
            assessment["source_column"] = (
                f"store_offers[{index}]"
            )
            assessment["store"] = first_value(
                offer,
                (
                    "store",
                    "store_name",
                    "provider",
                    "platform",
                ),
            )
            assessments.append(
                assessment
            )

    return assessments


def candidate_from_row(
    *,
    source_path: Path,
    source_format: str,
    row_number: int,
    row: dict[str, Any],
) -> tuple[
    dict[str, Any] | None,
    list[str],
]:
    title = first_value(
        row,
        TITLE_COLUMNS,
    )
    release_date = first_value(
        row,
        RELEASE_DATE_COLUMNS,
    )
    publisher = first_value(
        row,
        PUBLISHER_COLUMNS,
    )
    item_id = first_value(
        row,
        ITEM_ID_COLUMNS,
    )

    url_assessments = collect_urls(row)

    valid_urls = [
        assessment
        for assessment in url_assessments
        if assessment["valid"]
    ]

    blockers: list[str] = []

    if is_synthetic_title(title):
        blockers.append(
            "SYNTHETIC_OR_MISSING_TITLE"
        )

    if release_date in (
        None,
        "",
    ):
        blockers.append(
            "RELEASE_DATE_MISSING"
        )

    if not valid_urls:
        blockers.append(
            "NO_VALID_RETAIL_URL"
        )

    if blockers:
        return None, blockers

    fingerprint_payload = {
        "title": str(title).strip(),
        "release_date": str(
            release_date
        ).strip(),
        "urls": sorted(
            assessment["url"]
            for assessment in valid_urls
        ),
    }

    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    candidate = {
        "candidate_fingerprint_sha256": (
            fingerprint
        ),
        "source_path": str(
            source_path.resolve()
        ),
        "source_format": source_format,
        "source_row_number": row_number,
        "item_id": item_id,
        "title": title,
        "release_date": release_date,
        "publisher": publisher,
        "valid_retail_url_count": len(
            valid_urls
        ),
        "valid_retail_urls": (
            valid_urls
        ),
        "candidate_selected": False,
        "database_import_allowed": False,
        "wordpress_draft_creation_allowed": (
            False
        ),
    }

    return candidate, []


def iter_json_objects(
    value: Any,
    *,
    depth: int = 0,
) -> list[dict[str, Any]]:
    if depth > 8:
        return []

    objects: list[dict[str, Any]] = []

    if isinstance(value, dict):
        objects.append(value)

        for nested in value.values():
            objects.extend(
                iter_json_objects(
                    nested,
                    depth=depth + 1,
                )
            )

    elif isinstance(value, list):
        for nested in value:
            objects.extend(
                iter_json_objects(
                    nested,
                    depth=depth + 1,
                )
            )

    return objects


def scan_csv(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, int],
]:
    candidates: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            if row_number > (
                MAX_ROWS_PER_FILE + 1
            ):
                break

            candidate, blockers = (
                candidate_from_row(
                    source_path=path,
                    source_format="CSV",
                    row_number=row_number,
                    row=dict(row),
                )
            )

            if candidate is not None:
                candidates.append(candidate)

            for blocker in blockers:
                rejection_counts[blocker] = (
                    rejection_counts.get(
                        blocker,
                        0,
                    )
                    + 1
                )

    return candidates, rejection_counts


def scan_json(
    path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, int],
]:
    candidates: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}

    if path.suffix.lower() == ".jsonl":
        objects: list[dict[str, Any]] = []

        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as file:
            for line in file:
                if len(objects) >= MAX_ROWS_PER_FILE:
                    break

                line = line.strip()

                if not line:
                    continue

                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if isinstance(value, dict):
                    objects.append(value)
    else:
        try:
            value = json.loads(
                path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
        except json.JSONDecodeError:
            return [], {
                "INVALID_JSON": 1,
            }

        objects = iter_json_objects(value)[
            :MAX_ROWS_PER_FILE
        ]

    for row_number, row in enumerate(
        objects,
        start=1,
    ):
        candidate, blockers = (
            candidate_from_row(
                source_path=path,
                source_format=(
                    path.suffix[1:].upper()
                ),
                row_number=row_number,
                row=row,
            )
        )

        if candidate is not None:
            candidates.append(candidate)

        for blocker in blockers:
            rejection_counts[blocker] = (
                rejection_counts.get(
                    blocker,
                    0,
                )
                + 1
            )

    return candidates, rejection_counts


def path_is_excluded(
    path: Path,
    search_root: Path,
) -> bool:
    relative = path.relative_to(
        search_root
    )

    return any(
        part in EXCLUDED_DIRECTORY_NAMES
        for part in relative.parts[:-1]
    )


def discover_real_source_candidates(
    *,
    search_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    search_root = search_root.resolve()
    output_path = output_path.resolve()

    require(
        search_root.is_dir(),
        (
            "search root is missing: "
            f"{search_root}"
        ),
    )

    scanned_files: list[str] = []
    skipped_files: list[dict[str, str]] = []
    candidates: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}

    for path in sorted(
        search_root.rglob("*")
    ):
        if not path.is_file():
            continue

        if path_is_excluded(
            path,
            search_root,
        ):
            continue

        suffix = path.suffix.lower()

        if suffix not in SUPPORTED_SUFFIXES:
            continue

        if path.resolve() == output_path:
            continue

        try:
            size = path.stat().st_size
        except OSError as exc:
            skipped_files.append(
                {
                    "path": str(path),
                    "reason": (
                        f"STAT_FAILED:{exc}"
                    ),
                }
            )
            continue

        if size > MAX_FILE_SIZE_BYTES:
            skipped_files.append(
                {
                    "path": str(path),
                    "reason": "FILE_TOO_LARGE",
                }
            )
            continue

        scanned_files.append(
            str(path.resolve())
        )

        try:
            if suffix == ".csv":
                file_candidates, counts = (
                    scan_csv(path)
                )
            else:
                file_candidates, counts = (
                    scan_json(path)
                )
        except Exception as exc:
            skipped_files.append(
                {
                    "path": str(path),
                    "reason": (
                        f"SCAN_FAILED:{exc}"
                    ),
                }
            )
            continue

        candidates.extend(
            file_candidates
        )

        for blocker, count in counts.items():
            rejection_counts[blocker] = (
                rejection_counts.get(
                    blocker,
                    0,
                )
                + count
            )

    unique_candidates: dict[
        str,
        dict[str, Any],
    ] = {}

    for candidate in candidates:
        fingerprint = candidate[
            "candidate_fingerprint_sha256"
        ]

        unique_candidates.setdefault(
            fingerprint,
            candidate,
        )

    ordered_candidates = sorted(
        unique_candidates.values(),
        key=lambda item: (
            str(item["release_date"]),
            str(item["title"]),
            str(item["source_path"]),
        ),
        reverse=True,
    )

    if ordered_candidates:
        status = (
            "PASS_REAL_SOURCE_DISCOVERY_"
            "CANDIDATES_FOUND_NO_EXECUTION"
        )
        next_phase = (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "REAL-SOURCE-HUMAN-REVIEW"
        )
    else:
        status = (
            "PASS_REAL_SOURCE_DISCOVERY_"
            "NO_CANDIDATES_FOUND_NO_EXECUTION"
        )
        next_phase = (
            "MANUAL_REAL_SOURCE_INTAKE_PREP"
        )

    result = {
        "phase": PHASE,
        "status": status,
        "search_root": str(
            search_root
        ),
        "scanned_file_count": len(
            scanned_files
        ),
        "scanned_files": scanned_files,
        "skipped_files": skipped_files,
        "rejection_counts": (
            rejection_counts
        ),
        "raw_candidate_count": len(
            candidates
        ),
        "unique_candidate_count": len(
            ordered_candidates
        ),
        "candidates": ordered_candidates,
        "candidate_selected": False,
        "human_review_required": (
            bool(ordered_candidates)
        ),
        "automatic_selection_allowed": False,
        "database_import_allowed": False,
        "wordpress_draft_creation_allowed": (
            False
        ),
        "approval_request_creation_allowed": (
            False
        ),
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            next_phase
        ),
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "REAL_SOURCE_DISCOVERY_READ_ONLY"
        ),
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--search-root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--output-path",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = (
            discover_real_source_candidates(
                search_root=args.search_root,
                output_path=args.output_path,
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "candidate_selected": False,
                    "database_import_allowed": False,
                    "wordpress_draft_creation_allowed": (
                        False
                    ),
                    "normal_x_fb_write_allowed": False,
                    "production_execution": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "scanned_file_count": (
                    result[
                        "scanned_file_count"
                    ]
                ),
                "unique_candidate_count": (
                    result[
                        "unique_candidate_count"
                    ]
                ),
                "candidate_selected": False,
                "database_write": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "output_path": str(
                    args.output_path.resolve()
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
