from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EbookItem, StoreOffer
from app.services.csv_import_service import CsvImportService, CsvImportSummary


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_CREATE_ONLY = "PRODUCTION_CREATE_ONLY"


class ProductionCreateOnlyImportError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProductionCreateOnlyImportResult:
    mode: str
    artifact_sha256: str
    url_runtime_validation: str
    summary: CsvImportSummary


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_header_sha256(header: list[str]) -> str:
    return hashlib.sha256(",".join(header).encode("utf-8")).hexdigest()


def normalize_isbn(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = re.sub(r"[-‐‑‒–—―−\s]", "", normalized)
    if normalized and not re.fullmatch(r"\d{13}", normalized):
        raise ProductionCreateOnlyImportError(
            "ISBN13_INVALID",
            "ISBN must normalize to exactly 13 digits",
        )
    return normalized


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    return re.sub(r"\s+", " ", normalized).casefold()


def _resolved_reference(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPOSITORY_ROOT / path
    return path.resolve()


def _load_json(path: Path, missing_code: str) -> dict[str, Any]:
    if not path.is_file():
        raise ProductionCreateOnlyImportError(
            missing_code,
            f"required JSON file is missing: {path}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProductionCreateOnlyImportError(
            "IMPORT_SCHEMA_JSON_INVALID",
            f"invalid JSON: {path}: {exc}",
        ) from exc
    if not isinstance(value, dict):
        raise ProductionCreateOnlyImportError(
            "IMPORT_SCHEMA_JSON_INVALID",
            f"JSON root must be an object: {path}",
        )
    return value


def _reject_unsafe_host(parts: SplitResult) -> None:
    hostname = parts.hostname
    if not hostname:
        raise ProductionCreateOnlyImportError(
            "URL_HOST_REQUIRED",
            "URL hostname is required",
        )
    lowered = hostname.rstrip(".").lower()
    if lowered == "localhost" or lowered.endswith(".localhost"):
        raise ProductionCreateOnlyImportError(
            "URL_LOCAL_PRIVATE_ADDRESS_FORBIDDEN",
            "localhost URLs are forbidden",
        )
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    ):
        raise ProductionCreateOnlyImportError(
            "URL_LOCAL_PRIVATE_ADDRESS_FORBIDDEN",
            "local, private, or non-routable IP URLs are forbidden",
        )


def validate_https_url(value: str, *, field: str) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ProductionCreateOnlyImportError(
            "URL_CONTROL_CHARACTER_FORBIDDEN",
            f"{field} contains a control character",
        )
    parts = urlsplit(value.strip())
    code = (
        "PRODUCT_URL_HTTPS_REQUIRED"
        if field == "product_url"
        else "AFFILIATE_URL_HTTPS_REQUIRED"
    )
    if parts.scheme.lower() != "https":
        raise ProductionCreateOnlyImportError(
            code,
            f"{field} must use HTTPS",
        )
    if parts.username is not None or parts.password is not None:
        raise ProductionCreateOnlyImportError(
            "URL_USERINFO_FORBIDDEN",
            f"{field} must not contain userinfo",
        )
    _reject_unsafe_host(parts)
    try:
        parts.port
    except ValueError as exc:
        raise ProductionCreateOnlyImportError(
            "URL_PORT_INVALID",
            f"{field} has an invalid port",
        ) from exc
    return value.strip()


def normalize_url(value: str, *, field: str) -> str:
    validated = validate_https_url(value, field=field)
    parts = urlsplit(validated)
    hostname = (parts.hostname or "").lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if parts.port is not None:
        netloc += f":{parts.port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", netloc, path, parts.query, ""))


class ProductionEbookImportPreflightService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _load_single_row(
        self,
        artifact_path: Path,
        expected_header: list[str],
    ) -> dict[str, str]:
        with artifact_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            actual_header = list(reader.fieldnames or [])
            if actual_header != expected_header:
                raise ProductionCreateOnlyImportError(
                    "IMPORT_SCHEMA_HEADER_MISMATCH",
                    "CSV header does not match the exact contract",
                )
            rows = [
                {key: str(value or "").strip() for key, value in row.items()}
                for row in reader
                if any(str(value or "").strip() for value in row.values())
            ]
        if len(rows) != 1:
            raise ProductionCreateOnlyImportError(
                "IMPORT_CANDIDATE_COUNT_INVALID",
                "strict create-only import requires exactly one row",
            )
        return rows[0]

    def _validate_contract_and_manifest(
        self,
        *,
        artifact_path: Path,
        contract_path: Path,
        manifest_path: Path,
        runtime_evidence_path: Path,
    ) -> tuple[dict[str, str], str]:
        contract = _load_json(contract_path, "IMPORT_SCHEMA_CONTRACT_REQUIRED")
        manifest = _load_json(manifest_path, "IMPORT_MANIFEST_REQUIRED")

        schema_id = contract.get("schema_id")
        expected_header = contract.get("exact_header")
        if schema_id != "CANONICAL_EBOOK_IMPORT_CSV" or not isinstance(
            expected_header, list
        ):
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_CONTRACT_INVALID",
                "canonical CSV contract is invalid",
            )
        if manifest.get("schema_id") != schema_id:
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_ID_MISMATCH",
                "manifest schema_id does not match the contract",
            )
        if manifest.get("schema_version") != contract.get("schema_version"):
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_VERSION_MISMATCH",
                "manifest schema_version does not match the contract",
            )
        if manifest.get("import_mode") != PRODUCTION_CREATE_ONLY:
            raise ProductionCreateOnlyImportError(
                "IMPORT_MODE_INVALID",
                "manifest is not restricted to PRODUCTION_CREATE_ONLY",
            )
        if manifest.get("exact_header") != expected_header:
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_HEADER_MISMATCH",
                "manifest header does not match the contract",
            )
        if manifest.get("header_sha256") != canonical_header_sha256(expected_header):
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_HEADER_SHA256_MISMATCH",
                "manifest header digest does not match the contract",
            )
        if _resolved_reference(str(manifest.get("schema_contract_path") or "")) != contract_path.resolve():
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_CONTRACT_PATH_MISMATCH",
                "manifest is not bound to the supplied contract",
            )
        if manifest.get("schema_contract_sha256") != sha256_file(contract_path):
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_CONTRACT_SHA256_MISMATCH",
                "contract digest does not match the manifest",
            )
        if _resolved_reference(str(manifest.get("artifact_path") or "")) != artifact_path.resolve():
            raise ProductionCreateOnlyImportError(
                "IMPORT_ARTIFACT_PATH_MISMATCH",
                "manifest is not bound to the supplied CSV",
            )
        artifact_sha256 = sha256_file(artifact_path)
        if manifest.get("artifact_sha256") != artifact_sha256:
            raise ProductionCreateOnlyImportError(
                "IMPORT_ARTIFACT_SHA256_MISMATCH",
                "CSV digest does not match the manifest",
            )
        source_artifact = _resolved_reference(
            str(manifest.get("source_artifact") or "")
        )
        if (
            not source_artifact.is_file()
            or manifest.get("source_artifact_sha256") != sha256_file(source_artifact)
        ):
            raise ProductionCreateOnlyImportError(
                "IMPORT_SOURCE_ARTIFACT_SHA256_MISMATCH",
                "source artifact digest does not match the manifest",
            )
        evidence = _load_json(
            runtime_evidence_path,
            "URL_RUNTIME_VALIDATION_REQUIRED",
        )
        if _resolved_reference(str(manifest.get("url_validation_evidence_path") or "")) != runtime_evidence_path.resolve():
            raise ProductionCreateOnlyImportError(
                "URL_RUNTIME_EVIDENCE_PATH_MISMATCH",
                "manifest is not bound to the supplied URL evidence",
            )
        if manifest.get("url_validation_evidence_sha256") != sha256_file(runtime_evidence_path):
            raise ProductionCreateOnlyImportError(
                "URL_RUNTIME_EVIDENCE_SHA256_MISMATCH",
                "URL evidence digest does not match the manifest",
            )

        row = self._load_single_row(artifact_path, expected_header)
        required_fields = contract.get("required_non_empty_fields")
        if not isinstance(required_fields, list):
            raise ProductionCreateOnlyImportError(
                "IMPORT_SCHEMA_CONTRACT_INVALID",
                "required field contract is missing",
            )
        missing = [field for field in required_fields if not row.get(field, "").strip()]
        if missing:
            raise ProductionCreateOnlyImportError(
                "IMPORT_REQUIRED_FIELD_MISSING",
                "missing required fields: " + ", ".join(missing),
            )
        try:
            date.fromisoformat(row["release_date"])
        except ValueError as exc:
            raise ProductionCreateOnlyImportError(
                "RELEASE_DATE_INVALID",
                "release_date must be YYYY-MM-DD",
            ) from exc
        normalize_isbn(row["isbn"])
        if row["item_type"] not in set(contract.get("allowed_item_types") or []):
            raise ProductionCreateOnlyImportError(
                "ITEM_TYPE_INVALID",
                "item_type is not allowed by the contract",
            )
        try:
            if int(row["price"]) < 0:
                raise ValueError
        except ValueError as exc:
            raise ProductionCreateOnlyImportError(
                "PRICE_INVALID",
                "price must be a non-negative integer",
            ) from exc
        validate_https_url(row["item_url"], field="product_url")
        validate_https_url(row["affiliate_url"], field="affiliate_url")
        self._validate_runtime_evidence(evidence, row)
        return row, artifact_sha256

    def _validate_runtime_evidence(
        self,
        evidence: dict[str, Any],
        row: dict[str, str],
    ) -> None:
        if (
            evidence.get("status") != "PASS"
            or evidence.get("url_runtime_validation") != "PASS"
        ):
            raise ProductionCreateOnlyImportError(
                "URL_RUNTIME_VALIDATION_REQUIRED",
                "runtime URL validation has not passed",
            )
        try:
            datetime.fromisoformat(str(evidence.get("checked_at") or ""))
        except ValueError as exc:
            raise ProductionCreateOnlyImportError(
                "URL_RUNTIME_CHECKED_AT_INVALID",
                "runtime URL evidence checked_at is invalid",
            ) from exc
        validations = evidence.get("validations")
        if not isinstance(validations, list):
            raise ProductionCreateOnlyImportError(
                "URL_RUNTIME_VALIDATION_REQUIRED",
                "runtime URL validation entries are missing",
            )
        by_kind = {
            str(entry.get("kind")): entry
            for entry in validations
            if isinstance(entry, dict)
        }
        for kind, field in (
            ("product_url", "item_url"),
            ("affiliate_url", "affiliate_url"),
        ):
            entry = by_kind.get(kind)
            if not isinstance(entry, dict):
                raise ProductionCreateOnlyImportError(
                    "URL_RUNTIME_VALIDATION_REQUIRED",
                    f"runtime validation is missing for {kind}",
                )
            if entry.get("initial_url") != row[field]:
                raise ProductionCreateOnlyImportError(
                    "URL_RUNTIME_INITIAL_URL_MISMATCH",
                    f"runtime validation URL does not match {field}",
                )
            if entry.get("checked_by") != "human:remote_ssh":
                raise ProductionCreateOnlyImportError(
                    "URL_RUNTIME_CHECKER_INVALID",
                    "runtime URL evidence checker is invalid",
                )
            if entry.get("validation_result") != "PASS":
                raise ProductionCreateOnlyImportError(
                    "URL_RUNTIME_VALIDATION_REQUIRED",
                    f"runtime validation did not pass for {kind}",
                )
            status = entry.get("http_status")
            if not isinstance(status, int) or not 200 <= status < 300:
                raise ProductionCreateOnlyImportError(
                    "URL_RUNTIME_HTTP_STATUS_INVALID",
                    f"runtime HTTP status is invalid for {kind}",
                )
            if not str(entry.get("content_type") or "").lower().startswith("text/html"):
                raise ProductionCreateOnlyImportError(
                    "URL_RUNTIME_CONTENT_TYPE_INVALID",
                    f"runtime content type is invalid for {kind}",
                )
            validate_https_url(str(entry.get("final_url") or ""), field=kind)

    def _raise_if_duplicates(self, row: dict[str, str]) -> None:
        source_item = self.session.scalar(
            select(EbookItem.id).where(
                EbookItem.source_item_id == row["source_item_id"]
            ).limit(1)
        )
        if source_item is not None:
            raise ProductionCreateOnlyImportError(
                "DUPLICATE_SOURCE_ITEM_ID",
                "source_item_id already exists",
            )

        candidate_isbn = normalize_isbn(row["isbn"])
        for existing in self.session.scalars(
            select(EbookItem).where(EbookItem.isbn.is_not(None))
        ):
            if existing.isbn and normalize_isbn(existing.isbn) == candidate_isbn:
                raise ProductionCreateOnlyImportError(
                    "DUPLICATE_ISBN",
                    "ISBN already exists",
                )

        candidate_title = normalize_text(row["title"])
        candidate_volume = normalize_text(row["volume_label"])
        for existing in self.session.scalars(select(EbookItem)):
            if (
                normalize_text(existing.title) == candidate_title
                and normalize_text(existing.volume_label or "") == candidate_volume
            ):
                raise ProductionCreateOnlyImportError(
                    "DUPLICATE_TITLE_VOLUME",
                    "title and volume_label already exist",
                )

        store_item = self.session.scalar(
            select(StoreOffer.id).where(
                StoreOffer.store_name == row["store_name"],
                StoreOffer.store_item_id == row["store_item_id"],
            ).limit(1)
        )
        if store_item is not None:
            raise ProductionCreateOnlyImportError(
                "DUPLICATE_STORE_ITEM",
                "store_name and store_item_id already exist",
            )

        candidate_product = normalize_url(row["item_url"], field="product_url")
        for existing_url in self.session.scalars(
            select(StoreOffer.product_url).where(StoreOffer.product_url.is_not(None))
        ):
            if existing_url and normalize_url(existing_url, field="product_url") == candidate_product:
                raise ProductionCreateOnlyImportError(
                    "DUPLICATE_PRODUCT_URL",
                    "product_url already exists",
                )

        candidate_affiliate = normalize_url(
            row["affiliate_url"], field="affiliate_url"
        )
        for existing_url in self.session.scalars(
            select(StoreOffer.affiliate_url).where(StoreOffer.affiliate_url.is_not(None))
        ):
            if existing_url and normalize_url(existing_url, field="affiliate_url") == candidate_affiliate:
                raise ProductionCreateOnlyImportError(
                    "DUPLICATE_AFFILIATE_URL",
                    "affiliate_url already exists",
                )

    def import_file(
        self,
        artifact_path: Path,
        *,
        contract_path: Path,
        manifest_path: Path,
        runtime_evidence_path: Path,
        import_mode: str,
    ) -> ProductionCreateOnlyImportResult:
        if import_mode != PRODUCTION_CREATE_ONLY:
            raise ProductionCreateOnlyImportError(
                "IMPORT_MODE_INVALID",
                "strict service requires PRODUCTION_CREATE_ONLY",
            )
        row, artifact_sha256 = self._validate_contract_and_manifest(
            artifact_path=artifact_path.resolve(),
            contract_path=contract_path.resolve(),
            manifest_path=manifest_path.resolve(),
            runtime_evidence_path=runtime_evidence_path.resolve(),
        )
        if self.session.bind is None or self.session.bind.dialect.name != "sqlite":
            raise ProductionCreateOnlyImportError(
                "IMPORT_DATABASE_BACKEND_UNSUPPORTED",
                "strict create-only gate currently supports SQLite only",
            )
        try:
            self.session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            self._raise_if_duplicates(row)
            summary = CsvImportService(self.session).import_file(
                artifact_path,
                dry_run=False,
                commit=False,
            )
            expected = {
                "processed": 1,
                "created": 1,
                "updated": 0,
                "offer_created": 1,
                "offer_updated": 0,
                "failed": 0,
            }
            for field, value in expected.items():
                if getattr(summary, field) != value:
                    raise ProductionCreateOnlyImportError(
                        "IMPORT_CREATE_ONLY_SUMMARY_INVALID",
                        f"unexpected import result for {field}",
                    )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return ProductionCreateOnlyImportResult(
            mode=PRODUCTION_CREATE_ONLY,
            artifact_sha256=artifact_sha256,
            url_runtime_validation="PASS",
            summary=summary,
        )
