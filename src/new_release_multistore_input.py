from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SCHEMA_ID = "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2"
INPUT_CONTRACT_ID = "FRESH_NEW_RELEASE_COMIC_MULTISTORE_INPUT_V2"
PHASE_ID = "LS-NEW-BATCH-MULTISTORE-V2-IMPORT"
SCHEMA_VERSION = "2.0.0"
ARTICLE_TYPE = "electronic_book_new_release"


class ImportArtifactConflictError(FileExistsError):
    """Raised when an import would overwrite complete or partial artifacts."""

    def __init__(
        self,
        *,
        state: str,
        batch_ids: list[str],
        existing_paths: list[str],
        expected_path_count: int,
    ) -> None:
        self.state = state
        self.batch_ids = batch_ids
        self.existing_paths = existing_paths
        self.expected_path_count = expected_path_count
        super().__init__(
            "Import artifacts already exist "
            f"(state={state}, batch_ids={batch_ids}, "
            f"existing_count={len(existing_paths)}, "
            f"expected_count={expected_path_count})"
        )


REQUIRED_COLUMNS = [
    "batch_id",
    "item_id",
    "title",
    "release_date",
    "category",
    "rakuten_kobo_url",
    "image_url",
    "wordpress_status",
    "schema_id",
    "record_status",
    "publish_ready",
    "pr_required",
    "price_notice_required",
    "dmm_match_status",
    "amazon_match_status",
    "source_row_sha256",
]

NON_EMPTY_COLUMNS = [
    "batch_id",
    "item_id",
    "title",
    "release_date",
    "category",
    "source_row_sha256",
    "rakuten_kobo_url",
    "image_url",
]

TRUE_VALUES = {"true", "1", "yes", "y"}
FALSE_VALUES = {"false", "0", "no", "n", ""}

DMM_VERIFIED_PREFIXES = ("AUTO_APPROVED", "MANUAL_VERIFIED")
AMAZON_VERIFIED_EXACT = {
    "MANUAL_VERIFIED",
    "ASIN_LINK_GENERATED",
    "AUTO_APPROVED",
    "AUTO_APPROVED_MANUAL_LINK",
}
AMAZON_VERIFIED_PREFIXES = ("AUTO_APPROVED", "MANUAL_VERIFIED")
AMAZON_WARNING_STATUSES = {"", "MANUAL_ASIN_REQUIRED", "REVIEW_REQUIRED", "NOT_FOUND"}

FORBIDDEN_SCHEMES = {"javascript", "data", "file"}
FORBIDDEN_EPISODE_TOKENS = ("単話", "分冊", "話売り")
STORE_LINK_REL = "nofollow sponsored noopener"
STORE_LINK_TARGET = "_blank"


class ImportValidationError(Exception):
    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_metadata_space(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(_clean_text(value))).strip()


def _normalize_authors(value: Any) -> list[str]:
    authors: list[str] = []
    seen: set[str] = set()
    for raw_part in _clean_text(value).split("|"):
        part = _normalize_metadata_space(raw_part)
        if part and part not in seen:
            authors.append(part)
            seen.add(part)
    return authors


def parse_bool(value: Any) -> bool:
    normalized = _clean_text(value).lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ImportValidationError("BOOLEAN_INVALID", f"Unsupported boolean value: {value!r}")


def validate_csv_headers(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        raise ImportValidationError("CSV_HEADER_INVALID", "CSV header is missing.")

    normalized = [name.lstrip("\ufeff") for name in fieldnames]
    missing = [column for column in REQUIRED_COLUMNS if column not in normalized]
    if missing:
        raise ImportValidationError(
            "CSV_HEADER_MISSING_COLUMNS",
            f"Missing required columns: {', '.join(missing)}",
        )
    return normalized


def validate_http_url(value: Any, field_name: str) -> str:
    url = _clean_text(value)
    if not url:
        raise ImportValidationError("URL_REQUIRED", f"{field_name} is required.", field_name)

    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme in FORBIDDEN_SCHEMES or scheme not in {"http", "https"}:
        raise ImportValidationError("URL_SCHEME_FORBIDDEN", f"{field_name} must use http or https.", field_name)
    if not parts.netloc:
        raise ImportValidationError("URL_INVALID", f"{field_name} must include a host.", field_name)
    return url


def safe_filename(value: Any, max_length: int = 120) -> str:
    text = unicodedata.normalize("NFKC", _clean_text(value))
    if not text:
        raise ImportValidationError("UNSAFE_FILENAME", "Filename source cannot be empty.")

    sanitized_chars: list[str] = []
    for char in text:
        if char in {"/", "\\", "\x00"}:
            sanitized_chars.append("_")
            continue
        if ord(char) < 32:
            sanitized_chars.append("_")
            continue
        if unicodedata.category(char).startswith("Z"):
            sanitized_chars.append("_")
            continue
        if re.match(r"[A-Za-z0-9._-]", char):
            sanitized_chars.append(char)
        else:
            sanitized_chars.append("_")

    sanitized = re.sub(r"_+", "_", "".join(sanitized_chars)).strip("._-")
    if not sanitized or sanitized in {".", ".."}:
        raise ImportValidationError("UNSAFE_FILENAME", "Filename became unsafe after sanitization.")
    if sanitized.startswith(".."):
        raise ImportValidationError("UNSAFE_FILENAME", "Path traversal is not allowed.")
    return sanitized[:max_length]


def is_dmm_verified(status: Any) -> bool:
    normalized = _clean_text(status).upper()
    return any(normalized.startswith(prefix) for prefix in DMM_VERIFIED_PREFIXES)


def is_amazon_verified(status: Any) -> bool:
    normalized = _clean_text(status).upper()
    if normalized in AMAZON_VERIFIED_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in AMAZON_VERIFIED_PREFIXES)


def validate_amazon_asin(value: Any) -> str:
    asin = _clean_text(value)
    if not asin:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9]{10}", asin):
        raise ImportValidationError("AMAZON_ASIN_INVALID", "amazon_asin must be 10 alphanumeric characters.", "amazon_asin")
    return asin


def _contains_forbidden_episode_marker(row: dict[str, Any]) -> bool:
    edition_type = _clean_text(row.get("edition_type")).lower()
    if edition_type == "single_episode":
        return True

    for field in ("edition_type", "title", "category", "volume_label", "display_title"):
        value = _clean_text(row.get(field))
        if any(token in value for token in FORBIDDEN_EPISODE_TOKENS):
            return True
    return False


def _latest_path_forbidden(url: str) -> bool:
    path = urlsplit(url).path.rstrip("/")
    return path.endswith("/latest")


def _pick_first_present(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _clean_text(row.get(key))
        if value:
            return value
    return ""


def _optional_non_negative_price(row: dict[str, Any]) -> str:
    raw = _pick_first_present(
        row,
        "rakuten_kobo_price",
        "item_price",
        "price",
        "price_amount",
    )
    if not raw:
        return ""
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation as exc:
        raise ImportValidationError(
            "PRICE_INVALID",
            "Rakuten Kobo price must be a non-negative number.",
            "rakuten_kobo_price",
        ) from exc
    if not value.is_finite() or value < 0:
        raise ImportValidationError(
            "PRICE_INVALID",
            "Rakuten Kobo price must be a non-negative number.",
            "rakuten_kobo_price",
        )
    return raw


def _required_non_empty(row: dict[str, Any]) -> None:
    for field in NON_EMPTY_COLUMNS:
        if not _clean_text(row.get(field)):
            raise ImportValidationError("REQUIRED_FIELD_EMPTY", f"{field} cannot be empty.", field)


def _compute_available_store_count(store_navigation: list[dict[str, str]]) -> int:
    return len(store_navigation)


def build_store_buttons_html(store_navigation: list[dict[str, str]]) -> str:
    button_lines = ['<div class="ebook-store-buttons">']
    for store in store_navigation:
        safe_url = validate_http_url(store["url"], f"{store['key']}_url")
        button_lines.append(
            "  <a"
            f' class="ebook-store-button affiliate-cta store-{html.escape(store["key"], quote=True)}"'
            f' href="{html.escape(safe_url, quote=True)}"'
            f' target="{STORE_LINK_TARGET}"'
            f' rel="{STORE_LINK_REL}">{html.escape(store["label"], quote=False)}</a>'
        )
    button_lines.append("</div>")
    return "\n".join(button_lines)


def build_payload(row: dict[str, Any], row_number: int, imported_at: str) -> dict[str, Any]:
    title = _clean_text(row.get("title"))
    kobo_url = validate_http_url(row.get("rakuten_kobo_url"), "rakuten_kobo_url")
    image_url = validate_http_url(row.get("image_url"), "image_url")

    rakuten_price = _optional_non_negative_price(row)
    rakuten_currency = _pick_first_present(
        row,
        "rakuten_kobo_currency",
        "currency",
        "currency_code",
    ).upper() or ("JPY" if rakuten_price else "")
    rakuten_affiliate_url = _pick_first_present(
        row,
        "rakuten_kobo_affiliate_url",
        "affiliate_url",
    )
    if rakuten_affiliate_url:
        validate_http_url(
            rakuten_affiliate_url,
            "rakuten_kobo_affiliate_url",
        )
    verified_at = _clean_text(row.get("verified_at"))
    verification_method = _clean_text(row.get("verification_method"))
    store_navigation = [
        {
            "key": "rakuten_kobo",
            "label": "楽天Koboで確認",
            "url": kobo_url,
            "product_url": kobo_url,
            "affiliate_url": rakuten_affiliate_url,
            "price": rakuten_price,
            "currency": rakuten_currency,
            "verified_at": verified_at,
            "verification_method": verification_method,
            "source_row_sha256": _clean_text(
                row.get("source_row_sha256")
            ),
        }
    ]

    dmm_url = _pick_first_present(row, "dmm_affiliate_url", "dmm_item_url")
    if dmm_url:
        validate_http_url(dmm_url, "dmm_url")
        if not is_dmm_verified(row.get("dmm_match_status")):
            raise ImportValidationError(
                "DMM_URL_WITH_UNVERIFIED_STATUS",
                "DMM URL requires a verified DMM match status.",
                "dmm_match_status",
            )
        if _latest_path_forbidden(dmm_url):
            raise ImportValidationError(
                "DMM_LATEST_URL_FORBIDDEN",
                "DMM latest listing URLs are not allowed.",
                "dmm_affiliate_url",
            )
        store_navigation.append(
            {
                "key": "dmm_books",
                "label": "DMMブックスで確認",
                "url": dmm_url,
                "product_url": _clean_text(row.get("dmm_item_url")) or dmm_url,
                "affiliate_url": _clean_text(row.get("dmm_affiliate_url")),
            }
        )

    amazon_url = _pick_first_present(row, "amazon_affiliate_url", "amazon_item_url")
    amazon_status = _clean_text(row.get("amazon_match_status")).upper()
    amazon_asin = validate_amazon_asin(row.get("amazon_asin"))
    if amazon_url:
        validate_http_url(amazon_url, "amazon_url")
        if not is_amazon_verified(amazon_status):
            raise ImportValidationError(
                "AMAZON_URL_WITH_UNVERIFIED_STATUS",
                "Amazon URL requires a verified Amazon match status.",
                "amazon_match_status",
            )
        store_navigation.append(
            {
                "key": "amazon_kindle",
                "label": "Amazon Kindle版を確認",
                "url": amazon_url,
                "product_url": _clean_text(row.get("amazon_item_url")) or amazon_url,
                "affiliate_url": _clean_text(row.get("amazon_affiliate_url")),
            }
        )

    available_store_count = _compute_available_store_count(store_navigation)
    provided_store_count = _clean_text(row.get("available_store_count"))
    if provided_store_count:
        try:
            parsed_count = int(provided_store_count)
        except ValueError as exc:
            raise ImportValidationError(
                "AVAILABLE_STORE_COUNT_MISMATCH",
                "available_store_count must be an integer when provided.",
                "available_store_count",
            ) from exc
        if parsed_count != available_store_count:
            raise ImportValidationError(
                "AVAILABLE_STORE_COUNT_MISMATCH",
                "available_store_count does not match the verified store count.",
                "available_store_count",
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "input_contract_id": INPUT_CONTRACT_ID,
        "source_schema_id": SCHEMA_ID,
        "batch_id": _clean_text(row.get("batch_id")),
        "content_item_id": _clean_text(row.get("item_id")),
        "article_type": ARTICLE_TYPE,
        "primary_category": _clean_text(row.get("category")),
        "title": title,
        "volume_label": _pick_first_present(row, "volume_label", "volume_number"),
        "display_title": _clean_text(row.get("display_title")) or title,
        "release_date": _clean_text(row.get("release_date")),
        "publisher": _normalize_metadata_space(
            _pick_first_present(row, "publisher", "publisher_name")
        ),
        "authors": _normalize_authors(
            _pick_first_present(row, "authors", "author", "author_name")
        ),
        "series_name": _pick_first_present(row, "series_name", "series"),
        "series": _pick_first_present(row, "series_name", "series"),
        "identifiers": {
            key: value
            for key, value in {
                "item_number": _clean_text(row.get("item_number")),
                "isbn13": _clean_text(row.get("isbn13")),
                "dmm_content_id": _clean_text(row.get("dmm_content_id")),
                "amazon_asin": amazon_asin,
            }.items()
            if value
        },
        "cover_image": {
            "url": image_url,
            "alt": _clean_text(row.get("image_alt")) or title,
        },
        "store_navigation": store_navigation,
        "available_store_count": available_store_count,
        "store_buttons_html": build_store_buttons_html(store_navigation),
        "disclosures": {
            "pr_required": True,
            "price_notice_required": True,
            "affiliate_link_present": True,
        },
        "wordpress": {
            "status": "draft",
            "write_allowed": False,
            "publish_allowed": False,
        },
        "safety": {
            "external_network_performed": False,
            "wordpress_write_performed": False,
            "wordpress_publish_performed": False,
            "input_status_fixed_to_draft": True,
            "human_review_required_before_write": True,
        },
        "source_evidence": {
            "source_row_sha256": _clean_text(row.get("source_row_sha256")),
            "verified_at": verified_at,
            "verification_method": verification_method,
            "source_store": "rakuten_kobo",
            "source_csv_row_number": row_number,
            "imported_at": imported_at,
            "original_record_status": _clean_text(row.get("record_status")),
        },
    }
    return payload


def validate_row(row: dict[str, Any], row_number: int, imported_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _required_non_empty(row)

    if _clean_text(row.get("schema_id")) != SCHEMA_ID:
        raise ImportValidationError("SCHEMA_ID_MISMATCH", "schema_id must match the required schema.", "schema_id")
    if _clean_text(row.get("record_status")) != "READY_FOR_DRAFT":
        raise ImportValidationError("RECORD_STATUS_INVALID", "record_status must be READY_FOR_DRAFT.", "record_status")
    if _clean_text(row.get("wordpress_status")) != "draft":
        raise ImportValidationError("WORDPRESS_STATUS_INVALID", "wordpress_status must be draft.", "wordpress_status")
    if not parse_bool(row.get("publish_ready")):
        raise ImportValidationError("PUBLISH_READY_INVALID", "publish_ready must be true.", "publish_ready")
    if not parse_bool(row.get("pr_required")):
        raise ImportValidationError("PR_REQUIRED_INVALID", "pr_required must be true.", "pr_required")
    if not parse_bool(row.get("price_notice_required")):
        raise ImportValidationError(
            "PRICE_NOTICE_REQUIRED_INVALID",
            "price_notice_required must be true.",
            "price_notice_required",
        )

    if _contains_forbidden_episode_marker(row):
        raise ImportValidationError(
            "SINGLE_EPISODE_FORBIDDEN",
            "single_episode and explicit single-episode markers are forbidden.",
            "edition_type",
        )

    warnings: list[dict[str, Any]] = []
    amazon_url = _pick_first_present(row, "amazon_affiliate_url", "amazon_item_url")
    amazon_status = _clean_text(row.get("amazon_match_status")).upper()
    if not amazon_url and amazon_status in AMAZON_WARNING_STATUSES:
        warnings.append(
            {
                "code": "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION",
                "message": "Amazon link is omitted pending manual confirmation.",
                "row_number": row_number,
            }
        )

    payload = build_payload(row, row_number, imported_at)
    return payload, warnings


def _result_status(structure_errors: list[dict[str, Any]], blocked_rows: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if structure_errors:
        return "ERROR"
    if blocked_rows and warnings:
        return "PASS_WITH_BLOCKED_ROWS"
    if blocked_rows:
        return "PASS_WITH_BLOCKED_ROWS"
    if warnings:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def import_multistore_csv(csv_path: str | Path) -> dict[str, Any]:
    path = Path(csv_path)
    imported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    result: dict[str, Any] = {
        "status": "ERROR",
        "source_csv_path": str(path),
        "ready_payloads": [],
        "blocked_rows": [],
        "warnings": [],
        "structure_errors": [],
        "batch_ids": [],
        "ready_count": 0,
        "blocked_count": 0,
        "warning_count": 0,
        "safety": {
            "wordpress_write_performed": False,
            "wordpress_publish_performed": False,
            "external_network_performed": False,
            "input_status_fixed_to_draft": True,
        },
    }

    if not path.exists() or not path.is_file():
        result["structure_errors"].append(
            {"code": "INPUT_FILE_MISSING", "message": "Input CSV file does not exist."}
        )
        result["status"] = "ERROR"
        return result

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            reader.fieldnames = validate_csv_headers(reader.fieldnames)

            for row_number, raw_row in enumerate(reader, start=2):
                row = {key.lstrip("\ufeff"): value for key, value in raw_row.items()}
                try:
                    payload, row_warnings = validate_row(row, row_number, imported_at)
                    result["ready_payloads"].append(payload)
                    result["warnings"].extend(row_warnings)
                except ImportValidationError as exc:
                    result["blocked_rows"].append(
                        {
                            "row_number": row_number,
                            "item_id": _clean_text(row.get("item_id")),
                            "batch_id": _clean_text(row.get("batch_id")),
                            "error": exc.to_dict(),
                        }
                    )
    except ImportValidationError as exc:
        result["structure_errors"].append(exc.to_dict())
    except UnicodeDecodeError:
        result["structure_errors"].append(
            {"code": "CSV_DECODE_ERROR", "message": "CSV must be valid UTF-8 or UTF-8 with BOM."}
        )

    result["batch_ids"] = sorted(
        {
            payload["batch_id"]
            for payload in result["ready_payloads"]
        }
        | {
            blocked["batch_id"]
            for blocked in result["blocked_rows"]
            if blocked["batch_id"]
        }
    )
    result["ready_count"] = len(result["ready_payloads"])
    result["blocked_count"] = len(result["blocked_rows"])
    result["warning_count"] = len(result["warnings"])
    result["status"] = _result_status(result["structure_errors"], result["blocked_rows"], result["warnings"])
    return result


def _json_dump(path: Path, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(body)


def _is_complete_artifact_set(expected_paths: list[Path]) -> bool:
    if not expected_paths or not all(path.is_file() for path in expected_paths):
        return False
    try:
        for path in expected_paths:
            json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return True


def _artifact_conflict(
    *,
    batch_ids: list[str],
    expected_paths: list[Path],
    batch_directories: list[Path],
) -> ImportArtifactConflictError | None:
    existing_paths = [path for path in expected_paths if path.exists()]
    existing_batch_directories = [path for path in batch_directories if path.exists()]
    if not existing_paths and not existing_batch_directories:
        return None

    complete = _is_complete_artifact_set(expected_paths)
    observed_paths = sorted(
        {str(path) for path in existing_paths + existing_batch_directories}
    )
    return ImportArtifactConflictError(
        state="complete" if complete else "partial",
        batch_ids=batch_ids,
        existing_paths=observed_paths,
        expected_path_count=len(expected_paths),
    )


def write_import_artifacts(result: dict[str, Any], repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    batch_ids = result.get("batch_ids") or ["unknown_batch"]
    safe_batch_ids = [safe_filename(batch_id) for batch_id in batch_ids]

    item_paths: list[tuple[Path, dict[str, Any]]] = []
    manifest_paths: list[Path] = []
    blocked_paths: list[Path] = []
    result_log_paths: list[Path] = []

    for payload in result.get("ready_payloads", []):
        safe_batch = safe_filename(payload["batch_id"])
        safe_item = safe_filename(payload["content_item_id"])
        item_path = root / "exchange" / "inputs" / "new_release" / "batches" / safe_batch / "items" / f"{safe_item}.input.json"
        item_paths.append((item_path, payload))

    for safe_batch in safe_batch_ids:
        manifest_paths.append(root / "exchange" / "inputs" / "new_release" / "batches" / safe_batch / "manifest.json")
        blocked_paths.append(root / "exchange" / "reviews" / "new_release" / "batches" / f"{safe_batch}.multistore_blocked.json")
        result_log_paths.append(root / "exchange" / "logs" / f"{safe_batch}.multistore_import_result.json")

    all_paths = [path for path, _ in item_paths] + manifest_paths + blocked_paths + result_log_paths
    batch_directories = [
        root / "exchange" / "inputs" / "new_release" / "batches" / safe_batch
        for safe_batch in safe_batch_ids
    ]
    conflict = _artifact_conflict(
        batch_ids=list(batch_ids),
        expected_paths=all_paths,
        batch_directories=batch_directories,
    )
    if conflict is not None:
        raise conflict

    for path in all_paths:
        path.parent.mkdir(parents=True, exist_ok=True)

    try:
        for path, payload in item_paths:
            _json_dump(path, payload)

        batch_to_items: dict[str, list[str]] = {}
        for item_path, payload in item_paths:
            batch_to_items.setdefault(payload["batch_id"], []).append(str(item_path))

        manifest_records: list[dict[str, Any]] = []
        blocked_records: list[dict[str, Any]] = []
        result_records: list[dict[str, Any]] = []

        for safe_batch, batch_id, manifest_path, blocked_path, result_log_path in zip(
            safe_batch_ids,
            batch_ids,
            manifest_paths,
            blocked_paths,
            result_log_paths,
            strict=False,
        ):
            manifest_payload = {
                "status": result["status"],
                "ready_count": len(
                    [
                        payload
                        for payload in result.get("ready_payloads", [])
                        if payload["batch_id"] == batch_id
                    ]
                ),
                "blocked_count": len(
                    [
                        row
                        for row in result.get("blocked_rows", [])
                        if row.get("batch_id") == batch_id
                    ]
                ),
                "warning_count": len(result.get("warnings", [])),
                "batch_ids": [batch_id],
                "manifest_path": str(manifest_path),
                "blocked_path": str(blocked_path),
                "result_log_path": str(result_log_path),
                "item_paths": batch_to_items.get(batch_id, []),
                "safety": result["safety"],
            }
            blocked_payload = {
                "status": result["status"],
                "batch_id": batch_id,
                "blocked_path": str(blocked_path),
                "blocked_rows": [
                    row
                    for row in result.get("blocked_rows", [])
                    if row.get("batch_id") == batch_id
                ],
                "warning_count": len(result.get("warnings", [])),
                "safety": result["safety"],
            }
            result_log_payload = {
                "status": result["status"],
                "ready_count": result["ready_count"],
                "blocked_count": result["blocked_count"],
                "warning_count": result["warning_count"],
                "batch_ids": result["batch_ids"],
                "manifest_path": str(manifest_path),
                "blocked_path": str(blocked_path),
                "result_log_path": str(result_log_path),
                "safety": result["safety"],
            }
            _json_dump(manifest_path, manifest_payload)
            _json_dump(blocked_path, blocked_payload)
            _json_dump(result_log_path, result_log_payload)
            manifest_records.append(manifest_payload)
            blocked_records.append(blocked_payload)
            result_records.append(result_log_payload)
    except FileExistsError as exc:
        conflict = _artifact_conflict(
            batch_ids=list(batch_ids),
            expected_paths=all_paths,
            batch_directories=batch_directories,
        )
        if conflict is not None:
            raise conflict from exc
        raise

    return {
        "status": result["status"],
        "ready_count": result["ready_count"],
        "blocked_count": result["blocked_count"],
        "warning_count": result["warning_count"],
        "batch_ids": list(result["batch_ids"]),
        "item_paths": [str(path) for path, _ in item_paths],
        "manifest_records": manifest_records,
        "blocked_records": blocked_records,
        "result_log_records": result_records,
    }
