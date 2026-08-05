#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cgi
import csv
import hashlib
import html
import io
import json
import logging
import os
import secrets
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field, replace
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
repository_root_text = str(REPOSITORY_ROOT)
if repository_root_text not in sys.path:
    sys.path.insert(0, repository_root_text)

from src.new_release_multistore_input import (
    ImportArtifactConflictError,
    import_multistore_csv,
    write_import_artifacts,
)


LOGGER = logging.getLogger(__name__)

WORDPRESS_DRAFT_LOCK = threading.Lock()
WORDPRESS_DRAFT_IN_PROGRESS: set[str] = set()
METADATA_AUTOFILL_LOCK = threading.Lock()
BULK_AFFILIATE_LOCK = threading.Lock()


APP_TITLE = "新刊マルチストア入力V2 ローカルWebアプリ"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SESSION_TTL_SECONDS = 3600
BULK_AFFILIATE_TOKEN_TTL_SECONDS = 15 * 60
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SESSION_COOKIE_NAME = "multistore_app_session"
ALLOWED_INPUT_TYPES = {"collected", "manual"}
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
OLD_FORMAT_FILENAME_TOKEN = "ls_new_batch_input"
OLD_FORMAT_HEADER_HINTS = {"batch_id", "item_id", "title", "rakuten_kobo_url"}
V2_SCHEMA_ID = "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2"
AMAZON_OMITTED_WARNING_CODE = "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION"

TEMPLATE_COLUMNS = [
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
    "verified_at",
    "verification_method",
    "dmm_item_url",
    "dmm_affiliate_url",
    "dmm_content_id",
    "amazon_asin",
    "amazon_item_url",
    "amazon_affiliate_url",
    "edition_type",
    "available_store_count",
    "isbn",
    "isbn13",
    "item_number",
    "volume_label",
    "volume_number",
    "authors",
    "author",
    "author_name",
    "publisher",
    "publisher_name",
    "series_name",
    "series",
    "rakuten_kobo_price",
    "rakuten_kobo_currency",
    "rakuten_kobo_affiliate_url",
    "item_price",
    "price",
    "price_amount",
    "currency",
    "currency_code",
    "affiliate_url",
]


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: HTTPStatus = HTTPStatus.BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class PreparedUpload:
    original_filename: str
    input_type: str
    detected_encoding: str
    converted_to_utf8_bom: bool
    temp_dir: Path
    csv_path: Path


@dataclass
class BulkAffiliateSelectionToken:
    token: str
    selected_ebook_item_ids: tuple[str, ...]
    filters_query: str
    return_to: str
    issued_at: float
    expires_at: float
    nonce: str
    operation: str = "BULK_AFFILIATE_REGISTRATION"
    used: bool = False
    dry_run_input_hash: str = ""


@dataclass
class SessionData:
    session_id: str
    op_token: str
    expires_at: float
    imported_batch_ids: set[str] = field(default_factory=set)
    validation_bundle: dict[str, Any] | None = None
    raw_result: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    converted_csv_bytes: bytes | None = None
    converted_filename: str | None = None
    converted_preview: dict[str, Any] | None = None
    review_ready_tokens: dict[str, str] = field(
        default_factory=dict,
        repr=False,
    )
    daily_summary_preview: Any | None = field(default=None, repr=False)
    bulk_affiliate_tokens: dict[str, BulkAffiliateSelectionToken] = field(
        default_factory=dict,
        repr=False,
    )
    bulk_affiliate_results: dict[str, dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )

    def issue_bulk_affiliate_token(
        self,
        *,
        selected_ebook_item_ids: list[str],
        filters_query: str,
        return_to: str,
        now_ts: float | None = None,
    ) -> BulkAffiliateSelectionToken:
        now = time.time() if now_ts is None else now_ts
        token = secrets.token_urlsafe(32)
        value = BulkAffiliateSelectionToken(
            token=token,
            selected_ebook_item_ids=tuple(selected_ebook_item_ids),
            filters_query=filters_query,
            return_to=return_to,
            issued_at=now,
            expires_at=now + BULK_AFFILIATE_TOKEN_TTL_SECONDS,
            nonce=secrets.token_urlsafe(24),
        )
        self.bulk_affiliate_tokens[token] = value
        return value

    def get_bulk_affiliate_token(
        self,
        token: str,
        *,
        now_ts: float | None = None,
    ) -> BulkAffiliateSelectionToken:
        value = self.bulk_affiliate_tokens.get(token)
        if value is None or value.operation != "BULK_AFFILIATE_REGISTRATION":
            raise AppError("BULK_AFFILIATE_INVALID_TOKEN")
        now = time.time() if now_ts is None else now_ts
        if value.expires_at < now:
            self.bulk_affiliate_tokens.pop(token, None)
            raise AppError("BULK_AFFILIATE_TOKEN_EXPIRED")
        if value.used:
            raise AppError("BULK_AFFILIATE_TOKEN_REUSED")
        return value

class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}

    def create(self, now_ts: float | None = None) -> SessionData:
        now = now_ts if now_ts is not None else time.time()
        session = SessionData(
            session_id=secrets.token_urlsafe(24),
            op_token=secrets.token_urlsafe(24),
            expires_at=now + SESSION_TTL_SECONDS,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str | None, now_ts: float | None = None) -> SessionData | None:
        if not session_id:
            return None
        now = now_ts if now_ts is not None else time.time()
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session.expires_at < now:
            self._sessions.pop(session_id, None)
            return None
        return session


def _ensure_loopback_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized in {"127.0.0.1", "localhost"}:
        return "127.0.0.1"
    raise ValueError("host must be 127.0.0.1 or localhost")


def _validate_common_upload_rules(filename: str, raw_bytes: bytes) -> None:
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise AppError("アップロードサイズは最大10MiBです。")
    if not filename.lower().endswith(".csv"):
        raise AppError(".csv ファイルのみアップロードできます。")
    if b"\x00" in raw_bytes:
        raise AppError("NUL文字を含むファイルは受け付けできません。")


def _detect_manual_encoding(raw_bytes: bytes) -> str:
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        raw_bytes.decode("cp932")
        return "cp932"
    except UnicodeDecodeError as exc:
        raise AppError("手動調整CSVは UTF-8 / UTF-8 BOM / CP932 のみ対応です。") from exc


def _write_secure_temp_csv(raw_bytes: bytes, suffix: str = ".csv") -> tuple[Path, Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="multistore_app_", dir="/tmp"))
    path = temp_dir / f"upload{suffix}"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw_bytes)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    return temp_dir, path


def prepare_uploaded_csv(filename: str, raw_bytes: bytes, input_type: str) -> PreparedUpload:
    if input_type not in ALLOWED_INPUT_TYPES:
        raise AppError("入力種別が不正です。")

    _validate_common_upload_rules(filename, raw_bytes)

    if input_type == "manual":
        encoding = _detect_manual_encoding(raw_bytes)
        converted = False
        payload_bytes = raw_bytes
        if encoding == "cp932":
            text = raw_bytes.decode("cp932")
            payload_bytes = text.encode("utf-8-sig")
            converted = True
            encoding = "cp932"
        temp_dir, csv_path = _write_secure_temp_csv(payload_bytes)
        return PreparedUpload(
            original_filename=filename,
            input_type=input_type,
            detected_encoding=encoding,
            converted_to_utf8_bom=converted,
            temp_dir=temp_dir,
            csv_path=csv_path,
        )

    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        detected = "utf-8-sig"
    else:
        try:
            raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError("収集CSVは UTF-8 または UTF-8 BOM のみ対応です。") from exc
        detected = "utf-8"
    temp_dir, csv_path = _write_secure_temp_csv(raw_bytes)
    return PreparedUpload(
        original_filename=filename,
        input_type=input_type,
        detected_encoding=detected,
        converted_to_utf8_bom=False,
        temp_dir=temp_dir,
        csv_path=csv_path,
    )


def prevalidate_csv_upload(filename: str, raw_bytes: bytes, input_type: str) -> dict[str, Any]:
    prepared = prepare_uploaded_csv(filename=filename, raw_bytes=raw_bytes, input_type=input_type)
    raw_result = import_multistore_csv(prepared.csv_path)
    summary = summarize_result(raw_result, prepared=prepared)
    return {
        "prepared": prepared,
        "raw_result": raw_result,
        "summary": summary,
    }


def _normalized_fieldnames(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        return [name.lstrip("\ufeff") for name in reader.fieldnames]


def _csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return sum(1 for _ in reader)


def _detected_schema_ids(path: Path, has_schema_column: bool) -> list[str]:
    if not has_schema_column:
        return []
    found: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            schema = str((row or {}).get("schema_id", "")).strip()
            if schema:
                found.add(schema)
            if len(found) >= 10:
                break
    return sorted(found)


def _format_structure_errors(raw_result: dict[str, Any]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for item in raw_result.get("structure_errors") or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "UNKNOWN_STRUCTURE_ERROR")
        message = str(item.get("message") or "CSV構造エラーが検出されました。")
        formatted.append({"code": code, "message": message})
    return formatted


def _is_old_format_candidate(filename: str, fieldnames: list[str]) -> bool:
    lowered_name = filename.lower()
    if OLD_FORMAT_FILENAME_TOKEN in lowered_name:
        return True
    return OLD_FORMAT_HEADER_HINTS.issubset(set(fieldnames))


def summarize_result(raw_result: dict[str, Any], *, prepared: PreparedUpload | None = None) -> dict[str, Any]:
    ready_payloads = raw_result.get("ready_payloads") or []
    warnings = raw_result.get("warnings") or []
    blocked_rows = raw_result.get("blocked_rows") or []
    structure_errors = _format_structure_errors(raw_result)
    fieldnames: list[str] = []
    row_count = 0
    detected_schema_ids: list[str] = []
    missing_required_columns: list[str] = []
    unknown_columns: list[str] = []
    old_format_candidate = False
    if prepared is not None:
        try:
            fieldnames = _normalized_fieldnames(prepared.csv_path)
            row_count = _csv_row_count(prepared.csv_path)
            missing_required_columns = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
            unknown_columns = [name for name in fieldnames if name not in TEMPLATE_COLUMNS]
            detected_schema_ids = _detected_schema_ids(prepared.csv_path, "schema_id" in fieldnames)
            old_format_candidate = _is_old_format_candidate(prepared.original_filename, fieldnames)
        except Exception:
            structure_errors.append(
                {
                    "code": "CSV_SUMMARY_PARSE_ERROR",
                    "message": "CSV構造情報の読み取りに失敗しました。",
                }
            )
    importable = bool(raw_result.get("ready_count", len(ready_payloads)) > 0 and _collect_batch_ids(raw_result))
    return {
        "status": raw_result.get("status", "ERROR"),
        "ready_count": raw_result.get("ready_count", len(ready_payloads)),
        "blocked_count": raw_result.get("blocked_count", len(blocked_rows)),
        "warning_count": raw_result.get("warning_count", len(warnings)),
        "batch_ids": list(raw_result.get("batch_ids") or []),
        "ready_payloads": ready_payloads,
        "warnings": warnings,
        "blocked_rows": blocked_rows,
        "structure_errors": structure_errors,
        "missing_required_columns": missing_required_columns,
        "unknown_columns": unknown_columns,
        "detected_schema_ids": detected_schema_ids,
        "data_row_count": row_count,
        "validation_state": raw_result.get("status", "ERROR"),
        "importable": importable,
        "old_format_candidate": old_format_candidate,
        "fieldnames": fieldnames,
    }


def _row_source_sha256(row: dict[str, Any]) -> str:
    normalized = json.dumps(
        {k: str(v or "").strip() for k, v in sorted(row.items(), key=lambda item: item[0])},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _map_old_row_to_v2(row: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    mapped: dict[str, str] = {}
    for column in TEMPLATE_COLUMNS:
        mapped[column] = str(row.get(column, "") or "").strip()

    mapped["schema_id"] = V2_SCHEMA_ID
    mapped["wordpress_status"] = "draft"
    mapped["record_status"] = "READY_FOR_DRAFT"
    mapped["publish_ready"] = "true"
    mapped["pr_required"] = "true"
    mapped["price_notice_required"] = "true"
    mapped["dmm_match_status"] = mapped.get("dmm_match_status") or "NOT_FOUND"
    mapped["amazon_match_status"] = mapped.get("amazon_match_status") or "NOT_FOUND"
    mapped["edition_type"] = mapped.get("edition_type") or "volume"
    if not mapped.get("source_row_sha256"):
        mapped["source_row_sha256"] = _row_source_sha256(row)

    missing = [name for name in REQUIRED_COLUMNS if not mapped.get(name, "").strip()]
    return mapped, missing


def build_old_format_conversion_preview(prepared: PreparedUpload) -> dict[str, Any]:
    with prepared.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [name.lstrip("\ufeff") for name in (reader.fieldnames or [])]
        rows = [{k.lstrip("\ufeff"): v for k, v in raw.items()} for raw in reader]

    old_candidate = _is_old_format_candidate(prepared.original_filename, fieldnames)
    if not old_candidate:
        raise AppError("旧LS-NEW-BATCH形式候補ではないため、変換プレビューを実行できません。")

    converted_rows: list[dict[str, str]] = []
    preview_rows: list[dict[str, Any]] = []
    excluded_count = 0
    for index, row in enumerate(rows, start=2):
        mapped, missing = _map_old_row_to_v2(row)
        status = "READY" if not missing else "REQUIRES_REVIEW"
        preview_rows.append(
            {
                "row_number": index,
                "status": status,
                "missing_required": missing,
                "item_id": mapped.get("item_id", ""),
                "title": mapped.get("title", ""),
            }
        )
        if missing:
            excluded_count += 1
            continue
        converted_rows.append(mapped)

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=TEMPLATE_COLUMNS)
    writer.writeheader()
    for row in converted_rows:
        writer.writerow(row)
    converted_csv_bytes = b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")

    converted_bundle = prevalidate_csv_upload(
        filename=f"converted_{prepared.original_filename}",
        raw_bytes=converted_csv_bytes,
        input_type="manual",
    )
    return {
        "old_format_candidate": True,
        "preview_rows": preview_rows,
        "converted_row_count": len(converted_rows),
        "excluded_row_count": excluded_count,
        "converted_csv_bytes": converted_csv_bytes,
        "converted_bundle": converted_bundle,
        "detected_headers": fieldnames,
    }


def _collect_batch_ids(raw_result: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for value in raw_result.get("batch_ids") or []:
        if isinstance(value, str) and value.strip():
            ids.append(value.strip())
    for payload in raw_result.get("ready_payloads") or []:
        batch_id = payload.get("batch_id") if isinstance(payload, dict) else None
        if isinstance(batch_id, str) and batch_id.strip():
            ids.append(batch_id.strip())
    for row in raw_result.get("blocked_rows") or []:
        batch_id = row.get("batch_id") if isinstance(row, dict) else None
        if isinstance(batch_id, str) and batch_id.strip():
            ids.append(batch_id.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for batch_id in ids:
        if batch_id not in seen:
            deduped.append(batch_id)
            seen.add(batch_id)
    return deduped


def _require_importable_raw_result(session: SessionData) -> dict[str, Any]:
    if not isinstance(session.raw_result, dict):
        raise AppError(
            "事前検証結果の原本が保持されていないため、成果物生成を停止しました。CSVを再検証してください。"
        )

    raw_result = session.raw_result
    ready_payloads = raw_result.get("ready_payloads")
    blocked_rows = raw_result.get("blocked_rows")
    if not isinstance(ready_payloads, list) or not isinstance(blocked_rows, list):
        raise AppError(
            "事前検証結果の原本が保持されていないため、成果物生成を停止しました。CSVを再検証してください。"
        )

    structure_errors = raw_result.get("structure_errors") or []
    if structure_errors and raw_result.get("ready_count", 0) == 0:
        raise AppError(
            "CSV形式が新刊マルチストアV2入力仕様と一致していません。表示された構造エラーを修正するか、V2テンプレートを使用してください。"
        )

    batch_ids = _collect_batch_ids(raw_result)
    if not batch_ids:
        raise AppError(
            "事前検証結果の原本が保持されていないため、成果物生成を停止しました。CSVを再検証してください。"
        )
    raw_result["batch_ids"] = batch_ids
    return raw_result


def import_with_session_guard(
    session: SessionData,
    repo_root: Path,
    explicit_confirmation: bool,
) -> dict[str, Any]:
    if not explicit_confirmation:
        raise AppError("明示確認チェックが必要です。")
    if not session.validation_bundle:
        raise AppError("先に事前検証を実行してください。")

    raw_result = _require_importable_raw_result(session)
    batch_ids = _collect_batch_ids(raw_result)
    if len(batch_ids) != 1:
        raise AppError(
            "1回のインポートで処理できるbatch_idは1件だけです。"
            f" 検出件数: {len(batch_ids)}"
        )
    batch_id = batch_ids[0]
    if batch_id in session.imported_batch_ids:
        raise AppError(
            "同一セッションで同じbatch_idの二重インポートはできません。"
            f" batch_id: {batch_id}",
            status=HTTPStatus.CONFLICT,
        )
    try:
        write_result = write_import_artifacts(raw_result, repo_root)
    except ImportArtifactConflictError as exc:
        LOGGER.warning(
            "Import artifact conflict [stage=write_import_artifacts, "
            "state=%s, batch_ids=%s, existing_count=%d, expected_count=%d]",
            exc.state,
            exc.batch_ids,
            len(exc.existing_paths),
            exc.expected_path_count,
        )
        batch_label = ", ".join(exc.batch_ids)
        if exc.state == "complete":
            raise AppError(
                "このbatch_idはインポート済みです。既存成果物は変更していません。"
                f" batch_id: {batch_label}",
                status=HTTPStatus.CONFLICT,
            ) from exc
        raise AppError(
            "部分書き込みを検出したため停止しました。既存成果物は変更していません。"
            f" batch_id: {batch_label}",
            status=HTTPStatus.CONFLICT,
        ) from exc
    except Exception:
        LOGGER.exception(
            "Import artifact write failed "
            "[stage=write_import_artifacts, batch_ids=%s]",
            raw_result.get("batch_ids", []),
        )
        raise
    session.imported_batch_ids.add(batch_id)
    return write_result


def generate_template_csv_bytes() -> bytes:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=TEMPLATE_COLUMNS)
    writer.writeheader()
    writer.writerow(
        {
            "batch_id": "BATCH_EXAMPLE_001",
            "item_id": "ITEM_EXAMPLE_001",
            "title": "タイトル例",
            "release_date": "2026-07-13",
            "category": "コミック",
            "rakuten_kobo_url": "https://books.rakuten.co.jp/example",
            "image_url": "https://example.com/image.jpg",
            "wordpress_status": "draft",
            "schema_id": "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2",
            "record_status": "READY_FOR_DRAFT",
            "publish_ready": "true",
            "pr_required": "true",
            "price_notice_required": "true",
            "dmm_match_status": "",
            "amazon_match_status": "",
            "source_row_sha256": "sample_sha256",
            "dmm_item_url": "",
            "dmm_affiliate_url": "",
            "dmm_content_id": "",
            "amazon_asin": "",
            "amazon_item_url": "",
            "amazon_affiliate_url": "",
            "edition_type": "volume",
            "available_store_count": "1",
        }
    )
    body = stream.getvalue().encode("utf-8")
    return b"\xef\xbb\xbf" + body


def _escape(text: Any) -> str:
    return html.escape(str(text), quote=True)


def _render_preview_url(value: Any, *, empty_text: str = "") -> str:
    raw_value = str(value or "")
    display_value = raw_value or empty_text
    escaped_value = _escape(display_value)
    if not raw_value or any(character.isspace() for character in raw_value):
        return escaped_value
    try:
        parsed = urlparse(raw_value)
        valid = (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.netloc)
            and parsed.hostname is not None
        )
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        return escaped_value
    return (
        f'<a href="{escaped_value}" target="_blank" '
        f'rel="noopener noreferrer">{escaped_value}</a>'
    )


def _render_warning_items(warnings: list[dict[str, Any]]) -> str:
    amazon_unconfirmed_count = sum(
        1
        for warning in warnings
        if warning.get("code") == AMAZON_OMITTED_WARNING_CODE
    )
    items: list[str] = []
    if amazon_unconfirmed_count:
        items.append(f"<li>Amazon未確認: {_escape(amazon_unconfirmed_count)}件</li>")
    items.extend(
        f"<li>{_escape(warning.get('code', ''))}: {_escape(warning.get('message', ''))}</li>"
        for warning in warnings
        if warning.get("code") != AMAZON_OMITTED_WARNING_CODE
    )
    return "".join(items)


def _render_import_result(import_result: dict[str, Any]) -> str:
    manifest_records = import_result.get("manifest_records") or []
    blocked_records = import_result.get("blocked_records") or []
    result_log_records = import_result.get("result_log_records") or []

    ready_count = import_result.get("ready_count")
    if ready_count is None:
        ready_count = len(import_result.get("item_paths") or [])
    blocked_count = import_result.get("blocked_count")
    if blocked_count is None:
        blocked_count = sum(
            int(record.get("blocked_count", 0))
            for record in manifest_records
            if isinstance(record, dict)
        )
    warning_count = import_result.get("warning_count")
    if warning_count is None:
        warning_count = max(
            (
                int(record.get("warning_count", 0))
                for record in manifest_records
                if isinstance(record, dict)
            ),
            default=0,
        )
    batch_ids = import_result.get("batch_ids") or [
        batch_id
        for record in manifest_records
        if isinstance(record, dict)
        for batch_id in (record.get("batch_ids") or [])
    ]
    manifest_paths = [
        record.get("manifest_path")
        for record in manifest_records
        if isinstance(record, dict) and record.get("manifest_path")
    ]
    blocked_paths = [
        record.get("blocked_path")
        for record in blocked_records
        if isinstance(record, dict) and record.get("blocked_path")
    ]
    result_log_paths = [
        record.get("result_log_path")
        for record in result_log_records
        if isinstance(record, dict) and record.get("result_log_path")
    ]

    def render_paths(label: str, paths: list[Any]) -> str:
        values = "".join(f"<li>{_escape(path)}</li>" for path in paths)
        return f"<p>{label}</p><ul>{values}</ul>"

    return f"""
    <section>
      <h2>インポート結果表示</h2>
      <p>インポート成功件数: {_escape(ready_count)}</p>
      <p>除外件数: {_escape(blocked_count)}</p>
      <p>警告件数: {_escape(warning_count)}</p>
      <p>batch_id: {_escape(', '.join(str(value) for value in batch_ids))}</p>
      {render_paths('manifest保存先', manifest_paths)}
      {render_paths('blocked保存先', blocked_paths)}
      {render_paths('result log保存先', result_log_paths)}
    </section>
    """


def render_page_html(session: SessionData, page_state: dict[str, Any]) -> str:
    validation = page_state.get("validation")
    conversion_preview = page_state.get("conversion_preview")
    import_result = page_state.get("import_result")
    error = page_state.get("error")

    summary_html = ""
    if validation:
        prepared: PreparedUpload = validation["prepared"]
        result = validation["summary"]
        ready_payloads = result.get("ready_payloads", [])
        warnings = result.get("warnings", [])
        blocked = result.get("blocked_rows", [])
        structure_errors = result.get("structure_errors", [])
        missing_required_columns = result.get("missing_required_columns", [])
        unknown_columns = result.get("unknown_columns", [])
        detected_schema_ids = result.get("detected_schema_ids", [])
        validation_state = result.get("validation_state", "ERROR")
        importable = bool(result.get("importable"))
        old_candidate = bool(result.get("old_format_candidate"))
        ready_items = "".join(f"<li>{_escape(item.get('content_item_id', ''))}: {_escape(item.get('title', ''))}</li>" for item in ready_payloads)
        warning_items = _render_warning_items(warnings)
        blocked_items = "".join(
            f"<li>row {_escape(row.get('row_number', ''))}: {_escape(row.get('error', {}).get('code', ''))} / {_escape(row.get('error', {}).get('message', ''))}</li>"
            for row in blocked
        )
        structure_items = "".join(
            f"<li>{_escape(item.get('code', ''))}: {_escape(item.get('message', ''))}</li>" for item in structure_errors
        )
        missing_items = "".join(f"<li>{_escape(name)}</li>" for name in missing_required_columns)
        unknown_items = "".join(f"<li>{_escape(name)}</li>" for name in unknown_columns)
        schema_items = "".join(f"<li>{_escape(value)}</li>" for value in detected_schema_ids)
        conversion_cta = ""
        if old_candidate:
            conversion_cta = f"""
                <form method="post" action="/convert-preview" enctype="application/x-www-form-urlencoded">
                    <input type="hidden" name="op_token" value="{_escape(session.op_token)}" />
                    <button type="submit">V2形式へ変換プレビュー</button>
                </form>
            """
        summary_html = f"""
        <section>
          <h2>事前検証結果</h2>
          <p>元ファイル名: {_escape(prepared.original_filename)}</p>
          <p>入力種別: {_escape('手動調整CSV' if prepared.input_type == 'manual' else '収集CSV')}</p>
          <p>検出文字コード: {_escape(prepared.detected_encoding)}</p>
          <p>変換を行ったか: {_escape('はい' if prepared.converted_to_utf8_bom else 'いいえ')}</p>
          <p>検証状態: {_escape(validation_state)}</p>
          <p>読み込んだデータ行数: {_escape(result.get('data_row_count', 0))}</p>
          <p>インポート可能: {_escape('はい' if importable else 'いいえ')}</p>
          <p>正常件数: {_escape(result.get('ready_count', 0))}</p>
          <p>警告件数: {_escape(result.get('warning_count', 0))}</p>
          <p>除外件数: {_escape(result.get('blocked_count', 0))}</p>
          <h3>CSV構造エラー一覧</h3>
          <ul>{structure_items}</ul>
          <h3>不足必須列一覧</h3>
          <ul>{missing_items}</ul>
          <h3>未知列一覧</h3>
          <ul>{unknown_items}</ul>
          <h3>検出したschema_id</h3>
          <ul>{schema_items}</ul>
          {conversion_cta}
          <h3>正常作品一覧</h3>
          <ul>{ready_items}</ul>
          <h3>警告一覧</h3>
          <ul>{warning_items}</ul>
          <h3>除外理由一覧</h3>
          <ul>{blocked_items}</ul>
        </section>
        """

    conversion_html = ""
    if conversion_preview:
        preview_rows = conversion_preview.get("preview_rows", [])
        preview_items = "".join(
            f"<li>row {_escape(row.get('row_number', ''))}: {_escape(row.get('status', ''))} / missing={_escape(','.join(row.get('missing_required', [])))}</li>"
            for row in preview_rows
        )
        converted_summary = conversion_preview.get("converted_bundle", {}).get("summary", {})
        conversion_html = f"""
        <section>
          <h2>V2変換プレビュー</h2>
          <p>変換後行数: {_escape(conversion_preview.get('converted_row_count', 0))}</p>
          <p>要確認・除外行数: {_escape(conversion_preview.get('excluded_row_count', 0))}</p>
          <p>変換後検証状態: {_escape(converted_summary.get('validation_state', 'ERROR'))}</p>
          <p>変換後インポート可能: {_escape('はい' if converted_summary.get('importable') else 'いいえ')}</p>
          <a href="/converted.csv" download="converted_v2.csv">変換後V2 CSVをダウンロード</a>
          <h3>変換行プレビュー</h3>
          <ul>{preview_items}</ul>
        </section>
        """

    import_html = ""
    if import_result is not None:
        import_html = _render_import_result(import_result)

    error_html = ""
    if error:
        error_html = f"<section><p class='error'>{_escape(error)}</p></section>"

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(APP_TITLE)}</title>
  <style>
    body {{ font-family: sans-serif; margin: 1.2rem; background: #f7f7f7; color: #222; }}
    .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }}
    h1 {{ margin-top: 0; }}
    label {{ display: block; margin: 0.4rem 0; }}
    button {{ padding: 0.5rem 0.9rem; margin-right: 0.6rem; }}
    .error {{ color: #b00020; font-weight: 700; }}
  </style>
</head>
<body>
  <nav>
    <a href="/">CSV取込・事前検証</a>
    <a href="/database-search">SQLite検索</a>
        <a href="/supplement-import">不足作品補完</a>
  </nav>
  <h1>{_escape(APP_TITLE)}</h1>
  {error_html}
  <div class="card">
    <h2>CSVアップロード</h2>
    <form method="post" action="/prevalidate" enctype="multipart/form-data">
      <input type="hidden" name="op_token" value="{_escape(session.op_token)}" />
      <label>入力種別選択</label>
      <label><input type="radio" name="input_type" value="collected" checked /> 収集CSV</label>
      <label><input type="radio" name="input_type" value="manual" /> 手動調整CSV</label>
      <label>CSVファイル選択 <input type="file" name="csv_file" accept=".csv,text/csv" required /></label>
      <button type="submit">事前検証ボタン</button>
      <a href="/template.csv" download="manual_adjust_template.csv">手動調整用テンプレートCSVの取得</a>
    </form>
  </div>
  {summary_html}
    {conversion_html}
  <div class="card">
    <h2>Block AIへインポート</h2>
    <form method="post" action="/import" enctype="application/x-www-form-urlencoded">
      <input type="hidden" name="op_token" value="{_escape(session.op_token)}" />
            <label><input type="checkbox" name="explicit_confirmation" value="true" {'disabled' if not (session.summary and session.summary.get('importable')) else ''} /> 明示確認チェックボックス</label>
            <button type="submit" {'disabled' if not (session.summary and session.summary.get('importable')) else ''}>Block AIへインポートボタン</button>
    </form>
  </div>
  {import_html}
</body>
</html>
"""


class MultiStoreAppHandler(BaseHTTPRequestHandler):
    server_version = "MultiStoreApp/1.0"

    def _app(self) -> "MultiStoreAppServer":
        return self.server  # type: ignore[return-value]

    def _security_headers(self) -> None:
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

    def _send_html(self, status: int, body: str, session: SessionData | None = None) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if session:
            self.send_header(
                "Set-Cookie",
                f"{SESSION_COOKIE_NAME}={session.session_id}; Path=/; HttpOnly; SameSite=Strict",
            )
        self.end_headers()
        self.wfile.write(raw)

    def _send_csv(self, status: int, body: bytes, filename: str) -> None:
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, message: str) -> None:
        raw = message.encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_javascript(self, status: int, body: str) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "text/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_session(self) -> SessionData:
        cookie_header = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        session_id = cookie.get(SESSION_COOKIE_NAME).value if cookie.get(SESSION_COOKIE_NAME) else None
        store = self._app().session_store
        session = store.get(session_id)
        if session:
            return session
        return store.create()

    def _verify_token(self, session: SessionData, token: str | None) -> None:
        if not token or token != session.op_token:
            raise AppError("トークン検証に失敗しました。")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/assets/ebook-metadata-autofill.js":
            asset_path = REPOSITORY_ROOT / "app" / "gui" / "ebook_metadata_autofill.js"
            self._send_javascript(
                HTTPStatus.OK,
                asset_path.read_text(encoding="utf-8"),
            )
            return
        if parsed.path == "/assets/ebook-bulk-selection.js":
            asset_path = REPOSITORY_ROOT / "app" / "gui" / "ebook_bulk_selection.js"
            self._send_javascript(
                HTTPStatus.OK,
                asset_path.read_text(encoding="utf-8"),
            )
            return
        if parsed.path == "/assets/ebook-bulk-affiliate.js":
            asset_path = REPOSITORY_ROOT / "app" / "gui" / "ebook_bulk_affiliate.js"
            self._send_javascript(
                HTTPStatus.OK,
                asset_path.read_text(encoding="utf-8"),
            )
            return
        if parsed.path == "/template.csv":
            self._send_csv(HTTPStatus.OK, generate_template_csv_bytes(), "manual_adjust_template.csv")
            return
        if parsed.path == "/converted.csv":
            session = self._read_session()
            if not session.converted_csv_bytes:
                self._send_text(HTTPStatus.NOT_FOUND, "converted csv not found")
                return
            filename = session.converted_filename or "converted_v2.csv"
            self._send_csv(HTTPStatus.OK, session.converted_csv_bytes, filename)
            return
        if parsed.path == "/database-search":
            from app.gui.ebook_database_web import (
                render_database_search_page,
            )

            session = self._read_session()
            page = render_database_search_page(
                parsed.query,
                set(session.review_ready_tokens),
                csrf_token=session.op_token,
                daily_summary_preview=session.daily_summary_preview,
            )
            self._send_html(
                HTTPStatus.OK,
                page,
                session=session,
            )
            return
        if parsed.path == "/database-bulk-affiliate":
            self._handle_database_bulk_affiliate_page(parsed.query)
            return
        if parsed.path == "/database-bulk-affiliate/result":
            self._handle_database_bulk_affiliate_result(parsed.query)
            return
        if parsed.path == "/affiliate-settings":
            from app.gui.ebook_database_web import (
                render_affiliate_settings_page,
            )

            session = self._read_session()
            page = render_affiliate_settings_page(parsed.query)
            self._send_html(HTTPStatus.OK, page, session=session)
            return
        if parsed.path == "/supplement-import":
            from app.db.models import SupplementImportRun
            from app.db.session import SessionLocal
            from app.gui.ebook_database_web import (
                render_supplement_import_page,
            )
            from app.services.supplement_import_service import (
                SupplementImportService,
            )

            session = self._read_session()
            query = parse_qs(parsed.query, keep_blank_values=True)
            import_run_id = (query.get("run_id") or [""])[0]
            import_run = None
            candidates = ()
            if import_run_id:
                with SessionLocal() as database_session:
                    import_run = database_session.get(
                        SupplementImportRun,
                        import_run_id,
                    )
                    if import_run is not None:
                        candidates = SupplementImportService(
                            database_session
                        ).list_candidates(import_run.id)
                        database_session.expunge(import_run)
                        for candidate in candidates:
                            database_session.expunge(candidate)
            page = render_supplement_import_page(
                parsed.query,
                csrf_token=session.op_token,
                import_run=import_run,
                candidates=candidates,
            )
            self._send_html(HTTPStatus.OK, page, session=session)
            return
        if parsed.path != "/":
            self._send_text(HTTPStatus.NOT_FOUND, "not found")
            return
        session = self._read_session()
        page = render_page_html(session, page_state={})
        self._send_html(HTTPStatus.OK, page, session=session)

    def _read_database_urlencoded_form(
        self,
        *,
        max_bytes: int = 8192,
    ) -> dict[str, list[str]] | None:
        content_type = (
            self.headers.get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        if content_type != "application/x-www-form-urlencoded":
            return None

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            return None

        if content_length <= 0 or content_length > max_bytes:
            return None

        try:
            request_body = self.rfile.read(
                content_length
            ).decode("utf-8")
            return parse_qs(
                request_body,
                keep_blank_values=True,
            )
        except (UnicodeDecodeError, ValueError):
            return None

    def _redirect_database_result(
        self,
        *,
        return_to: str,
        parameter: str,
        code: str,
        session: SessionData | None = None,
    ) -> None:
        from urllib.parse import urlencode, urlsplit, urlunsplit

        from app.services.workflow_action_service import (
            safe_database_return_path,
        )

        safe_return_to = safe_database_return_path(return_to)
        parsed = urlsplit(safe_return_to)
        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )
        query[parameter] = [code]
        location = urlunsplit(
            (
                "",
                "",
                parsed.path,
                urlencode(query, doseq=True),
                "",
            )
        )

        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        if session is not None:
            self.send_header(
                "Set-Cookie",
                (
                    f"{SESSION_COOKIE_NAME}={session.session_id}; "
                    "Path=/; HttpOnly; SameSite=Strict"
                ),
            )
        self.end_headers()

    @staticmethod
    def _daily_summary_return_path(
        return_to: str, summary_date: str
    ) -> str:
        from urllib.parse import urlencode, urlsplit, urlunsplit

        from app.services.workflow_action_service import (
            safe_database_return_path,
        )

        safe_return_to = safe_database_return_path(return_to)
        parsed = urlsplit(safe_return_to)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if summary_date:
            query["summary_date"] = [summary_date]
        return urlunsplit(
            (
                "",
                "",
                parsed.path,
                urlencode(query, doseq=True),
                "",
            )
        )

    def _handle_database_workflow_update(
        self,
    ) -> None:
        from urllib.parse import (
            parse_qs,
            urlencode,
            urlsplit,
            urlunsplit,
        )

        from app.db.session import SessionLocal
        from app.services.workflow_action_service import (
            WorkflowActionError,
            execute_workflow_action,
            safe_database_return_path,
        )

        form: dict[str, list[str]] = {}

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0] if values else ""

        def redirect_with_result(code: str) -> None:
            return_to = safe_database_return_path(
                first("return_to")
            )

            parsed = urlsplit(return_to)
            query = parse_qs(
                parsed.query,
                keep_blank_values=True,
            )
            query["workflow_update"] = [code]

            location = urlunsplit(
                (
                    "",
                    "",
                    parsed.path,
                    urlencode(query, doseq=True),
                    "",
                )
            )

            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        content_type = (
            self.headers.get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        if content_type != (
            "application/x-www-form-urlencoded"
        ):
            redirect_with_result("invalid_request")
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            content_length = 0

        if content_length <= 0 or content_length > 8192:
            redirect_with_result("invalid_request")
            return

        try:
            request_body = self.rfile.read(
                content_length
            ).decode("utf-8")

            form = parse_qs(
                request_body,
                keep_blank_values=True,
            )
        except (UnicodeDecodeError, ValueError):
            redirect_with_result("invalid_request")
            return

        try:
            with SessionLocal() as session:
                execute_workflow_action(
                    session,
                    item_id=first("item_id"),
                    new_status=first("new_status"),
                    csrf_token=first("csrf_token"),
                    changed_by="human:local_gui",
                    note=(
                        "Workflow status updated "
                        "from local database GUI"
                    ),
                )
        except WorkflowActionError as exc:
            redirect_with_result(exc.code)
            return

        redirect_with_result("success")

    def _handle_review_ready_request(self) -> None:
        import hmac

        from app.db.session import SessionLocal
        from app.services.local_review_ready_approval_service import (
            LocalReviewReadyApprovalError,
            LocalReviewReadyApprovalService,
        )
        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        browser_session = self._read_session()
        form = self._read_database_urlencoded_form()

        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="review_ready_result",
                code="invalid_request",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def redirect(code: str) -> None:
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="review_ready_result",
                code=code,
                session=browser_session,
            )

        csrf_token = first("csrf_token")
        if not hmac.compare_digest(
            csrf_token,
            get_workflow_action_token(),
        ):
            redirect("invalid_token")
            return

        if "approval_type" in form:
            redirect("invalid_approval_type")
            return

        ebook_item_id = first("ebook_item_id")

        try:
            with SessionLocal() as session:
                result = LocalReviewReadyApprovalService(
                    session
                ).create_request(
                    ebook_item_id=ebook_item_id,
                    requested_by="human:local_gui",
                    ttl_minutes=60,
                )
        except LocalReviewReadyApprovalError as exc:
            redirect(exc.code)
            return
        except Exception:
            LOGGER.exception(
                "Review-ready approval request failed for %s",
                ebook_item_id,
            )
            redirect("internal_error")
            return

        browser_session.review_ready_tokens[
            result.ticket.request_id
        ] = result.ticket.token
        redirect("request_created")

    def _handle_review_ready_decision(self) -> None:
        import hmac

        from app.db.session import SessionLocal
        from app.services.local_review_ready_approval_service import (
            LocalReviewReadyApprovalError,
            LocalReviewReadyApprovalService,
        )
        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        browser_session = self._read_session()
        form = self._read_database_urlencoded_form()

        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="review_ready_result",
                code="invalid_request",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def redirect(code: str) -> None:
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="review_ready_result",
                code=code,
                session=browser_session,
            )

        csrf_token = first("csrf_token")
        if not hmac.compare_digest(
            csrf_token,
            get_workflow_action_token(),
        ):
            redirect("invalid_token")
            return

        if (
            "approval_type" in form
            or "approval_token" in form
            or "token" in form
        ):
            redirect("invalid_request")
            return

        ebook_item_id = first("ebook_item_id")
        request_id = first("approval_request_id")
        decision = first("decision").upper()
        note = first("note")
        approval_token = browser_session.review_ready_tokens.get(
            request_id
        )

        if not approval_token:
            redirect("approval_token_unavailable")
            return

        try:
            with SessionLocal() as session:
                LocalReviewReadyApprovalService(
                    session
                ).decide_request(
                    ebook_item_id=ebook_item_id,
                    approval_request_id=request_id,
                    token=approval_token,
                    decision=decision,
                    decided_by="human:local_gui",
                    note=note,
                )
        except LocalReviewReadyApprovalError as exc:
            if exc.code in {
                "already_decided",
                "expired",
                "stale_state",
            }:
                browser_session.review_ready_tokens.pop(
                    request_id,
                    None,
                )
            redirect(exc.code)
            return
        except Exception:
            LOGGER.exception(
                "Review-ready approval decision failed for %s",
                request_id,
            )
            redirect("internal_error")
            return

        browser_session.review_ready_tokens.pop(request_id, None)
        redirect(
            "approved" if decision == "APPROVE" else "rejected"
        )

    def _handle_review_ready_reissue(self) -> None:
        import hmac

        from app.db.session import SessionLocal
        from app.services.local_review_ready_approval_service import (
            LocalReviewReadyApprovalError,
            LocalReviewReadyApprovalService,
        )
        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        browser_session = self._read_session()
        form = self._read_database_urlencoded_form()
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="review_ready_result",
                code="invalid_request",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def redirect(code: str) -> None:
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="review_ready_result",
                code=code,
                session=browser_session,
            )

        if not hmac.compare_digest(
            first("csrf_token"),
            get_workflow_action_token(),
        ):
            redirect("invalid_token")
            return
        if any(
            name in form
            for name in ("approval_type", "approval_token", "token")
        ):
            redirect("invalid_request")
            return

        item_id = first("ebook_item_id")
        request_id = first("approval_request_id")
        try:
            with SessionLocal() as session:
                result = LocalReviewReadyApprovalService(
                    session
                ).reissue_request(
                    ebook_item_id=item_id,
                    approval_request_id=request_id,
                    token_available=(
                        request_id
                        in browser_session.review_ready_tokens
                    ),
                    requested_by="human:local_gui",
                    ttl_minutes=60,
                )
        except LocalReviewReadyApprovalError as exc:
            redirect(exc.code)
            return
        except Exception:
            LOGGER.exception(
                "Review-ready approval reissue failed for %s",
                request_id,
            )
            redirect("internal_error")
            return

        browser_session.review_ready_tokens.pop(request_id, None)
        browser_session.review_ready_tokens[
            result.ticket.request_id
        ] = result.ticket.token
        redirect("request_reissued")

    def _handle_database_wordpress_draft_create(self) -> None:
        import hmac
        from urllib.parse import (
            parse_qs,
            urlencode,
            urlsplit,
            urlunsplit,
        )

        from sqlalchemy import select

        from app.db.models import EbookItem, WorkflowApprovalRequest
        from app.db.repositories.workflow_state_repository import (
            WorkflowStateRepository,
        )
        from app.db.repositories.store_offer_affiliate_link_repository import (
            StoreOfferAffiliateLinkRepository,
        )
        from app.db.session import SessionLocal
        from app.integrations.wordpress_rest_client import (
            WordPressRestClient,
        )
        from app.services.workflow_action_service import (
            get_workflow_action_token,
            safe_database_return_path,
        )
        from app.services.wordpress_draft_execution_service import (
            WordPressDraftExecutionError,
            WordPressDraftExecutionStore,
            execute_approved_wordpress_draft_once,
        )
        from app.services.new_release_wordpress_draft_lite import (
            NewReleaseWordPressDraftLiteError,
            build_wordpress_store_offers,
        )

        form: dict[str, list[str]] = {}

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def has_exactly_one(name: str) -> bool:
            return len(form.get(name, [])) == 1

        def redirect_success(result: Any) -> None:
            return_to = safe_database_return_path(
                first("return_to")
            )
            parsed = urlsplit(return_to)
            query = parse_qs(
                parsed.query,
                keep_blank_values=True,
            )
            query["wordpress_draft_result"] = [result.status]
            query["wordpress_post_id"] = [
                str(result.wordpress_post_id)
            ]
            query["image_status"] = [result.image_status]
            query["featured_media_set"] = [
                str(bool(result.featured_media_set)).lower()
            ]
            image_error_summary = str(
                getattr(result, "image_error_summary", "") or ""
            ).strip()
            if image_error_summary:
                query["image_error_summary"] = [image_error_summary]
            price_status = str(
                getattr(result, "price_status", "") or ""
            ).strip()
            if price_status:
                query["price_status"] = [price_status]
            missing_price_stores = tuple(
                getattr(result, "missing_price_stores", ()) or ()
            )
            if missing_price_stores:
                query["missing_price_stores"] = [
                    ",".join(missing_price_stores)
                ]
            price_review_reasons = tuple(
                getattr(result, "price_review_reasons", ()) or ()
            )
            if price_review_reasons:
                query["price_review_reasons"] = [
                    ",".join(price_review_reasons)
                ]

            location = urlunsplit(
                (
                    "",
                    "",
                    parsed.path,
                    urlencode(query, doseq=True),
                    "",
                )
            )

            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        content_type = (
            self.headers.get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        if content_type != "application/x-www-form-urlencoded":
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid request")
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            content_length = 0

        if content_length <= 0 or content_length > 4096:
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid request")
            return

        try:
            request_body = self.rfile.read(content_length).decode(
                "utf-8"
            )
            form = parse_qs(
                request_body,
                keep_blank_values=True,
            )
        except (UnicodeDecodeError, ValueError):
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid request")
            return

        ebook_item_id = first("ebook_item_id")
        allowed_fields = {
            "csrf_token",
            "ebook_item_id",
            "explicit_confirmation",
            "return_to",
        }
        if set(form) - allowed_fields:
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid request fields")
            return

        if not all(
            has_exactly_one(name)
            for name in {
                "ebook_item_id",
                "explicit_confirmation",
                "return_to",
            }
        ):
            self._send_text(HTTPStatus.BAD_REQUEST, "invalid request fields")
            return

        csrf_token = first("csrf_token")
        if (
            not has_exactly_one("csrf_token")
            or not csrf_token
            or not hmac.compare_digest(
            csrf_token,
            get_workflow_action_token(),
            )
        ):
            self._send_text(HTTPStatus.FORBIDDEN, "invalid csrf token")
            return

        if first("explicit_confirmation") != "create_wordpress_draft":
            self._send_text(
                HTTPStatus.BAD_REQUEST,
                "explicit confirmation is required",
            )
            return

        if not ebook_item_id:
            self._send_text(HTTPStatus.BAD_REQUEST, "ebook_item_id is required")
            return

        # Normalize the redirect target before any database or network work.
        safe_database_return_path(first("return_to"))

        try:
            with SessionLocal() as session:
                if hasattr(session, "expire_all"):
                    session.expire_all()
                item = session.get(EbookItem, ebook_item_id)

                if item is None:
                    self._send_text(HTTPStatus.BAD_REQUEST, "ebook item was not found")
                    return

                if bool(getattr(item, "is_excluded", False)):
                    self._send_text(HTTPStatus.BAD_REQUEST, "excluded item is not eligible")
                    return

                if str(getattr(item, "wordpress_post_id", "") or "").strip():
                    self._send_text(HTTPStatus.CONFLICT, "draft already exists")
                    return

                if getattr(item, "workflow_status", "") != "READY":
                    self._send_text(HTTPStatus.BAD_REQUEST, "workflow_status must be READY")
                    return

                if getattr(item, "review_status", "") != "APPROVED":
                    self._send_text(HTTPStatus.BAD_REQUEST, "review_status must be APPROVED")
                    return

                if bool(getattr(item, "publish_ready", False)):
                    self._send_text(HTTPStatus.BAD_REQUEST, "publish_ready must remain false")
                    return

                if str(getattr(item, "wordpress_status", "NOT_CREATED") or "NOT_CREATED").upper() not in {"", "NOT_CREATED"}:
                    self._send_text(HTTPStatus.BAD_REQUEST, "wordpress_status must be NOT_CREATED")
                    return

                missing_metadata = [
                    field_name
                    for field_name in ("author_name", "publisher_name")
                    if not str(getattr(item, field_name, "") or "").strip()
                ]
                if missing_metadata:
                    self._send_text(
                        HTTPStatus.BAD_REQUEST,
                        "METADATA_REVIEW_REQUIRED: missing "
                        + ", ".join(missing_metadata),
                    )
                    return

                # ORM-backed runtime sessions can also reject unresolved
                # verified-source conflicts before any WordPress client is
                # constructed. Lightweight test doubles retain the direct
                # missing-field guard above.
                if isinstance(item, EbookItem):
                    from app.services.ebook_metadata_autofill_service import (
                        EbookMetadataAutofillService,
                    )

                    metadata_preview = EbookMetadataAutofillService(
                        session
                    ).preview(ebook_item_id)
                    if (
                        metadata_preview.metadata_status
                        == "METADATA_REVIEW_REQUIRED"
                    ):
                        self._send_text(
                            HTTPStatus.BAD_REQUEST,
                            "METADATA_REVIEW_REQUIRED: unresolved metadata conflict",
                        )
                        return

                approval_request = session.scalar(
                    select(WorkflowApprovalRequest)
                    .where(
                        WorkflowApprovalRequest.ebook_item_id == ebook_item_id,
                        WorkflowApprovalRequest.approval_type == "REVIEW_READY",
                        WorkflowApprovalRequest.status == "APPROVED",
                        WorkflowApprovalRequest.decided_at.is_not(None),
                        WorkflowApprovalRequest.expected_current_status == "REVIEW",
                        WorkflowApprovalRequest.requested_status == "READY",
                    )
                    .order_by(
                        WorkflowApprovalRequest.decided_at.desc(),
                        WorkflowApprovalRequest.requested_at.desc(),
                        WorkflowApprovalRequest.id.desc(),
                    )
                    .limit(1)
                )

                if approval_request is None:
                    self._send_text(
                        HTTPStatus.BAD_REQUEST,
                        "approved REVIEW_READY request was not found",
                    )
                    return

                affiliate_link_repository = (
                    StoreOfferAffiliateLinkRepository(session)
                )

                def select_wordpress_offers(current_item: Any) -> tuple[Any, ...]:
                    def resolve_dmm_wordpress_link(candidate: Any) -> str | None:
                        offer_id = str(
                            getattr(candidate, "id", "") or ""
                        ).strip()
                        if not offer_id:
                            return None
                        link = affiliate_link_repository.get_dmm_wordpress_link(
                            store_offer_id=offer_id
                        )
                        if link is None:
                            return None
                        return str(link.affiliate_url or "").strip() or None

                    return build_wordpress_store_offers(
                        getattr(current_item, "offers", []) or [],
                        dmm_wordpress_link_resolver=(
                            resolve_dmm_wordpress_link
                        ),
                    )

                try:
                    wordpress_offers = select_wordpress_offers(item)
                except NewReleaseWordPressDraftLiteError as exc:
                    self._send_text(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                preferred_offer = next(
                    (
                        candidate
                        for candidate in wordpress_offers
                        if candidate.store_name == "amazon"
                    ),
                    wordpress_offers[0] if wordpress_offers else None,
                )

                if preferred_offer is None:
                    self._send_text(HTTPStatus.BAD_REQUEST, "eligible offer was not found")
                    return

                base_url = (
                    os.environ.get("WORDPRESS_BASE_URL")
                    or os.environ.get("WP_BASE_URL")
                    or ""
                )
                username = (
                    os.environ.get("WORDPRESS_USERNAME")
                    or os.environ.get("WP_USERNAME")
                    or ""
                )
                password = (
                    os.environ.get("WORDPRESS_APPLICATION_PASSWORD")
                    or os.environ.get("WP_APPLICATION_PASSWORD")
                    or os.environ.get("WP_APP_PASSWORD")
                    or ""
                )

                if not str(base_url).strip().startswith("https://"):
                    self._send_text(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        "wordpress HTTPS configuration is required",
                    )
                    return

                try:
                    client = WordPressRestClient(
                        base_url=base_url,
                        username=username,
                        application_password=password,
                    )
                except Exception:
                    self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "wordpress client is not configured")
                    return

                try:
                    approval_request_id = approval_request.id

                    def refresh_current_state() -> tuple[Any, Any, Any, Any]:
                        if hasattr(session, "expire_all"):
                            session.expire_all()
                        current_item = session.get(
                            EbookItem,
                            ebook_item_id,
                        )
                        current_approval = session.get(
                            WorkflowApprovalRequest,
                            approval_request_id,
                        )
                        if current_item is None:
                            raise WordPressDraftExecutionError(
                                "item_not_found",
                                "ebook item disappeared before external POST",
                            )
                        if current_approval is None:
                            raise WordPressDraftExecutionError(
                                "approval_not_eligible",
                                "approval request disappeared before external POST",
                            )
                        current_offers = select_wordpress_offers(current_item)
                        current_offer = next(
                            (
                                candidate
                                for candidate in current_offers
                                if candidate.store_name == "amazon"
                            ),
                            current_offers[0] if current_offers else None,
                        )
                        if current_offer is None:
                            raise WordPressDraftExecutionError(
                                "invalid_offer",
                                "eligible offer disappeared before external POST",
                            )
                        return (
                            current_item,
                            current_approval,
                            current_offers,
                            current_offer,
                        )

                    result = execute_approved_wordpress_draft_once(
                        ebook_item_id=ebook_item_id,
                        item=item,
                        approval_request=approval_request,
                        offers=wordpress_offers,
                        preferred_offer=preferred_offer,
                        wordpress_client=client,
                        state_repository=WorkflowStateRepository(session),
                        commit=session.commit,
                        rollback=session.rollback,
                        execution_store=WordPressDraftExecutionStore(
                            self._app().repo_root
                        ),
                        refresh_current_state=refresh_current_state,
                    )
                except WordPressDraftExecutionError as exc:
                    status = HTTPStatus.BAD_REQUEST
                    if exc.code in {
                        "already_created",
                        "execution_claim_exists",
                        "reconciliation_required",
                    }:
                        status = HTTPStatus.CONFLICT
                    self._send_text(status, str(exc))
                    return
                except Exception:
                    LOGGER.exception("WordPress draft creation failed for %s", ebook_item_id)
                    self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, "wordpress draft creation failed")
                    return

            redirect_success(result)
        except Exception:
            LOGGER.exception(
                "Unexpected WordPress draft route failure for %s",
                ebook_item_id,
            )
            self._send_text(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "wordpress draft creation failed",
            )

    def _handle_database_wordpress_schedule(self, *, cancel: bool = False) -> None:
        from app.db.session import SessionLocal
        from app.integrations.wordpress_rest_client import WordPressRestClient
        from app.services.wordpress_draft_execution_service import (
            default_wordpress_draft_execution_store,
        )
        from app.services.wordpress_post_schedule_service import (
            WordPressPostScheduleError,
            WordPressPostScheduleExecutionStore,
            WordPressPostScheduleService,
        )

        form = self._read_database_urlencoded_form()
        return_to = ""
        parameter = "wordpress_schedule_result"
        if form is None:
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="invalid_request",
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        return_to = first("return_to")
        browser_session = self._read_session()
        if not self._database_form_is_authorized(
            form,
            expected_token=browser_session.op_token,
        ):
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="invalid_token",
            )
            return
        required = {
            "csrf_token",
            "ebook_item_id",
            "wordpress_post_id",
            "return_to",
            "operation",
        }
        operation = first("operation").upper()
        if operation in {"SCHEDULE", "RESCHEDULE"}:
            required.add("publish_at")
            required.add("wordpress_category_id")
        elif operation == "CATEGORY_UPDATE":
            required.add("wordpress_category_id")
        if set(form) != required or any(len(form[name]) != 1 for name in required):
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="invalid_request",
            )
            return
        if (cancel and operation != "CANCEL_SCHEDULE") or (
            not cancel and operation not in {"SCHEDULE", "RESCHEDULE", "CATEGORY_UPDATE"}
        ):
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="invalid_request",
            )
            return

        base_url = os.environ.get("WORDPRESS_BASE_URL") or os.environ.get("WP_BASE_URL") or ""
        username = os.environ.get("WORDPRESS_USERNAME") or os.environ.get("WP_USERNAME") or ""
        password = (
            os.environ.get("WORDPRESS_APPLICATION_PASSWORD")
            or os.environ.get("WP_APPLICATION_PASSWORD")
            or os.environ.get("WP_APP_PASSWORD")
            or ""
        )
        if not str(base_url).strip().startswith("https://"):
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="internal_error",
            )
            return
        try:
            client = WordPressRestClient(
                base_url=base_url,
                username=username,
                application_password=password,
            )
            with SessionLocal() as session:
                service = WordPressPostScheduleService(
                    session,
                    wordpress_client=client,
                    execution_store=WordPressPostScheduleExecutionStore(
                        self._app().repo_root
                    ),
                    draft_execution_store=default_wordpress_draft_execution_store(),
                )
                arguments = {
                    "ebook_item_id": first("ebook_item_id"),
                    "wordpress_post_id": first("wordpress_post_id"),
                }
                if operation == "SCHEDULE":
                    service.schedule_post(
                        **arguments,
                        publish_at_local=first("publish_at"),
                        category_id=first("wordpress_category_id"),
                    )
                    result_code = "scheduled"
                elif operation == "RESCHEDULE":
                    service.reschedule_post(
                        **arguments,
                        publish_at_local=first("publish_at"),
                        category_id=first("wordpress_category_id"),
                    )
                    result_code = "rescheduled"
                elif operation == "CATEGORY_UPDATE":
                    service.update_category(
                        **arguments,
                        category_id=first("wordpress_category_id"),
                    )
                    result_code = "category_updated"
                else:
                    service.cancel_schedule(**arguments)
                    result_code = "cancelled"
        except WordPressPostScheduleError as exc:
            result_code = exc.code
        except Exception:
            LOGGER.exception(
                "WordPress schedule route failed for %s", first("ebook_item_id")
            )
            result_code = "internal_error"
        self._redirect_database_result(
            return_to=return_to,
            parameter=parameter,
            code=result_code,
        )

    def _database_form_is_authorized(
        self,
        form: dict[str, list[str]],
        *,
        expected_token: str | None = None,
    ) -> bool:
        import hmac
        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        values = form.get("csrf_token") or []
        supplied = values[0].strip() if values else ""
        return bool(supplied) and hmac.compare_digest(
            supplied,
            expected_token or get_workflow_action_token(),
        )

    def _read_json_object(self, *, max_bytes: int = 16384) -> dict[str, Any] | None:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return None
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if content_length < 2 or content_length > max_bytes:
            return None
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _handle_database_bulk_selection_validate(self) -> None:
        import hmac
        from urllib.parse import urlencode

        from app.db.read_only_session import ReadOnlySessionLocal
        from app.gui.ebook_database_view_model import EbookDatabaseViewModel
        from app.gui.ebook_database_web import (
            DATABASE_SEARCH_FILTER_PARAMETERS,
            database_query_from_state,
            parse_database_search_query,
        )
        from app.services.ebook_bulk_selection_service import (
            EbookBulkSelectionService,
        )

        form = self._read_database_urlencoded_form()
        browser_session = self._read_session()
        service_failure = EbookBulkSelectionService.failure

        def send_failure(status: int, code: str) -> None:
            self._send_json(status, service_failure(code).to_dict())

        if form is None:
            send_failure(HTTPStatus.BAD_REQUEST, "BULK_SELECTION_QUERY_FAILED")
            return

        csrf_values = form.get("csrf_token") or []
        csrf_token = csrf_values[0].strip() if len(csrf_values) == 1 else ""
        if not csrf_token or not hmac.compare_digest(
            csrf_token, browser_session.op_token
        ):
            send_failure(HTTPStatus.FORBIDDEN, "BULK_SELECTION_CSRF_FAILED")
            return

        untrusted_capability_fields = {
            "affiliate_registration_capability",
            "wordpress_draft_capability",
            "wordpress_schedule_capability",
        }
        allowed_fields = (
            DATABASE_SEARCH_FILTER_PARAMETERS
            | {
                "page",
                "csrf_token",
                "selected_ebook_item_ids",
            }
            | untrusted_capability_fields
        )
        if set(form) - allowed_fields:
            send_failure(HTTPStatus.BAD_REQUEST, "BULK_SELECTION_QUERY_FAILED")
            return
        if any(
            len(values) != 1
            for name, values in form.items()
            if name not in {
                "selected_ebook_item_ids",
                *untrusted_capability_fields,
            }
        ):
            send_failure(HTTPStatus.BAD_REQUEST, "BULK_SELECTION_QUERY_FAILED")
            return

        query_pairs = [
            (name, value)
            for name, values in form.items()
            if name in DATABASE_SEARCH_FILTER_PARAMETERS or name == "page"
            for value in values
        ]
        selected_ids = form.get("selected_ebook_item_ids") or []
        try:
            state = parse_database_search_query(urlencode(query_pairs))
            query = database_query_from_state(state)
            filters = EbookDatabaseViewModel.filters_for_query(query)
            with ReadOnlySessionLocal() as database_session:
                result = EbookBulkSelectionService(
                    database_session
                ).validate(selected_ids, filters=filters)
        except Exception:
            LOGGER.exception("Bulk selection validation query failed")
            send_failure(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "BULK_SELECTION_QUERY_FAILED",
            )
            return

        self._send_json(
            HTTPStatus.OK if result.ok else HTTPStatus.BAD_REQUEST,
            result.to_dict(),
        )

    @staticmethod
    def _bulk_affiliate_error(code: str) -> dict[str, str]:
        from app.services.ebook_bulk_affiliate_registration_service import (
            ERROR_MESSAGES,
        )

        messages = {
            **ERROR_MESSAGES,
            "BULK_AFFILIATE_INVALID_TOKEN": "選択情報を確認できませんでした",
            "BULK_AFFILIATE_TOKEN_EXPIRED": "選択情報の有効期限が切れました",
            "BULK_AFFILIATE_TOKEN_REUSED": "この登録操作は既に完了しています",
            "BULK_AFFILIATE_CSRF_FAILED": "操作確認に失敗しました",
            "BULK_AFFILIATE_INVALID_STORE": "対象媒体が不正です",
            "BULK_AFFILIATE_INPUT_HASH_MISMATCH": "dry-run後に入力が変更されました",
            "BULK_AFFILIATE_TRANSACTION_FAILED": "一括登録を完了できませんでした",
            "BULK_AFFILIATE_READBACK_FAILED": "登録後の再確認に失敗しました",
        }
        return {
            "code": code,
            "message": messages.get(code, "入力内容を確認してください"),
        }

    def _send_bulk_affiliate_failure(self, status: int, code: str) -> None:
        self._send_json(
            status,
            {"ok": False, "errors": [self._bulk_affiliate_error(code)]},
        )

    @staticmethod
    def _bulk_affiliate_inputs(
        form: dict[str, list[str]],
        selected_ids: tuple[str, ...],
    ) -> dict[str, dict[str, Any]]:
        from app.services.ebook_bulk_affiliate_registration_service import (
            BulkAffiliateStoreInput,
            SUPPORTED_STORES,
        )

        allowed_fields = {
            "store_item_id",
            "product_url",
            "affiliate_url",
            "price",
            "image_url",
            "overwrite",
            "expected_hash",
        }
        valid_prefixes = {
            f"offer__{item_id}__{store_name}__"
            for item_id in selected_ids
            for store_name in SUPPORTED_STORES
        }
        for name, values in form.items():
            if not name.startswith("offer__"):
                continue
            prefix, separator, field_name = name.rpartition("__")
            if (
                not separator
                or f"{prefix}__" not in valid_prefixes
                or field_name not in allowed_fields
                or len(values) != 1
            ):
                raise AppError("BULK_AFFILIATE_INVALID_STORE")

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0] if len(values) == 1 else ""

        return {
            item_id: {
                store_name: BulkAffiliateStoreInput(
                    store_item_id=first(
                        f"offer__{item_id}__{store_name}__store_item_id"
                    ),
                    product_url=first(
                        f"offer__{item_id}__{store_name}__product_url"
                    ),
                    affiliate_url=first(
                        f"offer__{item_id}__{store_name}__affiliate_url"
                    ),
                    price=first(f"offer__{item_id}__{store_name}__price"),
                    image_url=first(
                        f"offer__{item_id}__{store_name}__image_url"
                    ),
                    overwrite=(
                        form.get(
                            f"offer__{item_id}__{store_name}__overwrite"
                        )
                        == ["true"]
                    ),
                    expected_hash=first(
                        f"offer__{item_id}__{store_name}__expected_hash"
                    ),
                )
                for store_name in SUPPORTED_STORES
            }
            for item_id in selected_ids
        }

    @staticmethod
    def _bulk_affiliate_csrf_valid(
        form: dict[str, list[str]], session: SessionData
    ) -> bool:
        import hmac

        values = form.get("csrf_token") or []
        supplied = values[0] if len(values) == 1 else ""
        return bool(supplied) and hmac.compare_digest(
            supplied, session.op_token
        )

    def _handle_database_bulk_affiliate_prepare(self) -> None:
        from urllib.parse import urlencode

        from app.db.read_only_session import ReadOnlySessionLocal
        from app.gui.ebook_database_view_model import EbookDatabaseViewModel
        from app.gui.ebook_database_web import (
            DATABASE_SEARCH_FILTER_PARAMETERS,
            database_query_from_state,
            parse_database_search_query,
        )
        from app.services.ebook_bulk_selection_service import (
            EbookBulkSelectionService,
        )
        from app.services.workflow_action_service import (
            safe_database_return_path,
        )

        form = self._read_database_urlencoded_form(max_bytes=65536)
        session = self._read_session()
        if form is None:
            self._send_text(
                HTTPStatus.BAD_REQUEST, "入力内容を確認してください"
            )
            return
        return_to = safe_database_return_path(
            (form.get("return_to") or [""])[0]
        )
        if not self._bulk_affiliate_csrf_valid(form, session):
            self._redirect_database_result(
                return_to=return_to,
                parameter="bulk_affiliate_result",
                code="csrf_failed",
                session=session,
            )
            return
        selected_ids = form.get("selected_ebook_item_ids") or []
        query_pairs = [
            (name, value)
            for name, values in form.items()
            if name in DATABASE_SEARCH_FILTER_PARAMETERS or name == "page"
            for value in values
        ]
        try:
            filters_query = urlencode(query_pairs)
            state = parse_database_search_query(filters_query)
            filters = EbookDatabaseViewModel.filters_for_query(
                database_query_from_state(state)
            )
            with ReadOnlySessionLocal() as database_session:
                validation = EbookBulkSelectionService(
                    database_session
                ).validate(selected_ids, filters=filters)
            if not validation.ok:
                mapped = {
                    "BULK_SELECTION_EMPTY": "empty_selection",
                    "BULK_SELECTION_LIMIT_EXCEEDED": "limit_exceeded",
                }.get(validation.errors[0].code, "invalid_selection")
                self._redirect_database_result(
                    return_to=return_to,
                    parameter="bulk_affiliate_result",
                    code=mapped,
                    session=session,
                )
                return
            token = session.issue_bulk_affiliate_token(
                selected_ebook_item_ids=[
                    item.ebook_item_id for item in validation.items
                ],
                filters_query=filters_query,
                return_to=return_to,
            )
        except Exception:
            LOGGER.exception("Bulk affiliate prepare failed")
            self._redirect_database_result(
                return_to=return_to,
                parameter="bulk_affiliate_result",
                code="prepare_failed",
                session=session,
            )
            return
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header(
            "Location",
            "/database-bulk-affiliate?"
            + urlencode({"token": token.token}),
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={session.session_id}; Path=/; "
            "HttpOnly; SameSite=Strict",
        )
        self.end_headers()

    def _handle_database_bulk_affiliate_page(self, raw_query: str) -> None:
        from app.db.read_only_session import ReadOnlySessionLocal
        from app.gui.ebook_database_web import render_bulk_affiliate_page
        from app.services.ebook_bulk_affiliate_registration_service import (
            EbookBulkAffiliateRegistrationService,
        )

        session = self._read_session()
        token_text = (parse_qs(raw_query).get("token") or [""])[0]
        try:
            token = session.get_bulk_affiliate_token(token_text)
            with ReadOnlySessionLocal() as database_session:
                items = list(
                    EbookBulkAffiliateRegistrationService(
                        database_session
                    ).prefill(list(token.selected_ebook_item_ids))
                )
                page = render_bulk_affiliate_page(
                    selection_token=token.token,
                    csrf_token=session.op_token,
                    items=items,
                    return_to=token.return_to,
                )
        except AppError as exc:
            error = self._bulk_affiliate_error(str(exc))
            self._send_html(
                HTTPStatus.BAD_REQUEST,
                f"<h1>{html.escape(error['message'])}</h1>",
                session=session,
            )
            return
        except Exception:
            LOGGER.exception("Bulk affiliate page failed")
            self._send_html(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "<h1>確認画面を表示できませんでした</h1>",
                session=session,
            )
            return
        self._send_html(HTTPStatus.OK, page, session=session)

    def _handle_database_bulk_affiliate_dry_run(self) -> None:
        from app.db.read_only_session import ReadOnlySessionLocal
        from app.services.ebook_bulk_affiliate_registration_service import (
            BulkAffiliateError,
            EbookBulkAffiliateRegistrationService,
        )

        form = self._read_database_urlencoded_form(max_bytes=262144)
        session = self._read_session()
        if form is None:
            self._send_bulk_affiliate_failure(
                HTTPStatus.BAD_REQUEST, "BULK_AFFILIATE_INVALID_URL"
            )
            return
        if not self._bulk_affiliate_csrf_valid(form, session):
            self._send_bulk_affiliate_failure(
                HTTPStatus.FORBIDDEN, "BULK_AFFILIATE_CSRF_FAILED"
            )
            return
        try:
            token = session.get_bulk_affiliate_token(
                (form.get("selection_token") or [""])[0]
            )
            inputs = self._bulk_affiliate_inputs(
                form, token.selected_ebook_item_ids
            )
            with ReadOnlySessionLocal() as database_session:
                plan = EbookBulkAffiliateRegistrationService(
                    database_session
                ).plan(list(token.selected_ebook_item_ids), inputs)
            if plan.ok:
                token.dry_run_input_hash = plan.input_hash
            self._send_json(
                HTTPStatus.OK if plan.ok else HTTPStatus.BAD_REQUEST,
                plan.to_safe_dict(),
            )
        except AppError as exc:
            self._send_bulk_affiliate_failure(
                HTTPStatus.BAD_REQUEST, str(exc)
            )
        except BulkAffiliateError as exc:
            self._send_bulk_affiliate_failure(
                HTTPStatus.BAD_REQUEST, exc.code
            )
        except Exception:
            LOGGER.exception("Bulk affiliate dry-run failed")
            self._send_bulk_affiliate_failure(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "BULK_AFFILIATE_TRANSACTION_FAILED",
            )

    def _handle_database_bulk_affiliate_apply(self) -> None:
        from urllib.parse import urlencode

        from app.db.read_only_session import ReadOnlySessionLocal
        from app.db.session import SessionLocal
        from app.services.ebook_bulk_affiliate_registration_service import (
            BulkAffiliateError,
            EbookBulkAffiliateRegistrationService,
        )

        form = self._read_database_urlencoded_form(max_bytes=262144)
        session = self._read_session()
        if form is None or not self._bulk_affiliate_csrf_valid(
            form or {}, session
        ):
            self._send_html(
                HTTPStatus.FORBIDDEN,
                "<h1>操作確認に失敗しました</h1>",
                session=session,
            )
            return
        try:
            with BULK_AFFILIATE_LOCK:
                token = session.get_bulk_affiliate_token(
                    (form.get("selection_token") or [""])[0]
                )
                if form.get("operation_confirmation") != ["true"]:
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_OVERWRITE_NOT_CONFIRMED"
                    )
                supplied_hash = (
                    form.get("dry_run_input_hash") or [""]
                )[0]
                if (
                    not supplied_hash
                    or supplied_hash != token.dry_run_input_hash
                ):
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_INPUT_HASH_MISMATCH"
                    )
                inputs = self._bulk_affiliate_inputs(
                    form, token.selected_ebook_item_ids
                )
                with SessionLocal() as database_session:
                    with database_session.begin():
                        plan = EbookBulkAffiliateRegistrationService(
                            database_session
                        ).apply(
                            list(token.selected_ebook_item_ids),
                            inputs,
                            expected_input_hash=supplied_hash,
                            operator="human:local_gui",
                        )
                token.used = True
                with ReadOnlySessionLocal() as read_session:
                    readback_ok = EbookBulkAffiliateRegistrationService(
                        read_session
                    ).verify_readback(plan)
                if not readback_ok:
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_READBACK_FAILED"
                    )
                result_token = secrets.token_urlsafe(24)
                session.bulk_affiliate_results[result_token] = {
                    "result": plan.to_safe_dict(),
                    "return_to": token.return_to,
                }
        except AppError as exc:
            error = self._bulk_affiliate_error(str(exc))
            self._send_html(
                HTTPStatus.BAD_REQUEST,
                f"<h1>{html.escape(error['message'])}</h1>",
                session=session,
            )
            return
        except BulkAffiliateError as exc:
            error = self._bulk_affiliate_error(exc.code)
            self._send_html(
                HTTPStatus.BAD_REQUEST,
                f"<h1>{html.escape(error['message'])}</h1>",
                session=session,
            )
            return
        except Exception:
            LOGGER.exception("Bulk affiliate transaction failed")
            self._send_html(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "<h1>一括登録を完了できませんでした</h1>",
                session=session,
            )
            return
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header(
            "Location",
            "/database-bulk-affiliate/result?"
            + urlencode({"token": result_token}),
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _handle_database_bulk_affiliate_result(self, raw_query: str) -> None:
        from app.gui.ebook_database_web import (
            render_bulk_affiliate_result_page,
        )

        session = self._read_session()
        result_token = (parse_qs(raw_query).get("token") or [""])[0]
        stored = session.bulk_affiliate_results.get(result_token)
        if stored is None:
            self._send_html(
                HTTPStatus.NOT_FOUND,
                "<h1>完了結果が見つかりません</h1>",
                session=session,
            )
            return
        self._send_html(
            HTTPStatus.OK,
            render_bulk_affiliate_result_page(
                result=stored["result"],
                return_to=stored["return_to"],
            ),
            session=session,
        )

    def _metadata_api_error(
        self,
        status: int,
        code: str,
        message: str,
        **details: object,
    ) -> None:
        self._send_json(
            status,
            {"error": {"code": code, "message": message}, **details},
        )

    @staticmethod
    def _metadata_protection_reasons(item: Any) -> list[str]:
        reasons: list[str] = []
        if item.review_status != "NOT_REVIEWED":
            reasons.append("REVIEW_STATUS_PROTECTED")
        if item.publish_ready is True:
            reasons.append("PUBLISH_READY_PROTECTED")
        if str(item.wordpress_post_id or "").strip():
            reasons.append("WORDPRESS_DRAFT_EXISTS")
        return reasons

    @staticmethod
    def _metadata_payload(
        preview: Any,
        *,
        title: str,
        evidence: dict[str, object],
        evidence_path: Path,
        protection_reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        protected = bool(protection_reasons)
        return {
            "ebook_item_id": preview.ebook_item_id,
            "title": title,
            "operation": preview.operation,
            "dry_run": preview.dry_run,
            "metadata_status": (
                "WORKFLOW_STATE_PROTECTED"
                if protected
                else preview.metadata_status
            ),
            "apply_possible": False if protected else preview.apply_possible,
            "protection_reasons": protection_reasons or [],
            "fingerprint": preview.fingerprint,
            "evidence_path": str(evidence_path),
            "external_communication_attempted": evidence["external_communication_attempted"],
            "wordpress_update_attempted": evidence["wordpress_update_attempted"],
            "database_update_attempted": evidence["database_update_attempted"],
            "database_update_succeeded": evidence["database_update_succeeded"],
            "field_results": [asdict(result) for result in preview.field_results],
        }

    def _handle_metadata_autofill_api(self, ebook_item_id: str, operation: str) -> None:
        import hmac

        from app.db.models import EbookItem
        from app.services.ebook_metadata_autofill_service import (
            EbookMetadataAutofillError,
            EbookMetadataAutofillService,
            build_evidence,
            write_evidence,
        )
        from app.services.workflow_action_service import get_workflow_action_token

        payload = self._read_json_object()
        allowed_fields = (
            {"csrf_token"}
            if operation == "preview"
            else {"csrf_token", "confirmed_fingerprint", "confirm_ebook_item_id"}
        )
        if payload is None or set(payload) != allowed_fields:
            self._metadata_api_error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "リクエスト形式が不正です。")
            return
        csrf_token = payload.get("csrf_token")
        if not isinstance(csrf_token, str) or not hmac.compare_digest(
            csrf_token, get_workflow_action_token()
        ):
            self._metadata_api_error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "操作確認に失敗しました。")
            return
        if not ebook_item_id:
            self._metadata_api_error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "対象IDが不正です。")
            return

        evidence_directory = (
            self._app().repo_root / "exchange" / "logs" / "ebook_metadata_autofill"
        )
        changed_by = (
            "system:local_gui_metadata_autofill_preview"
            if operation == "preview"
            else "system:local_gui_metadata_autofill_confirmed"
        )
        try:
            if operation == "preview":
                from app.db.read_only_session import ReadOnlySessionLocal

                with ReadOnlySessionLocal() as session:
                    item = session.get(EbookItem, ebook_item_id)
                    if item is None:
                        raise EbookMetadataAutofillError("item_not_found")
                    title = item.title
                    protection_reasons = self._metadata_protection_reasons(item)
                    result = EbookMetadataAutofillService(session).preview(ebook_item_id)
                evidence_result = (
                    replace(result, metadata_status="WORKFLOW_STATE_PROTECTED")
                    if protection_reasons
                    else result
                )
                evidence = build_evidence(
                    evidence_result,
                    database_update_attempted=False,
                    database_update_succeeded=False,
                    changed_by=changed_by,
                )
                evidence["protection_reasons"] = protection_reasons
                evidence_path = write_evidence(evidence, evidence_directory)
                self._send_json(
                    HTTPStatus.OK,
                    self._metadata_payload(
                        result,
                        title=title,
                        evidence=evidence,
                        evidence_path=evidence_path,
                        protection_reasons=protection_reasons,
                    ),
                )
                return

            confirmed_id = payload.get("confirm_ebook_item_id")
            fingerprint = payload.get("confirmed_fingerprint")
            if (
                not isinstance(confirmed_id, str)
                or confirmed_id != ebook_item_id
                or not isinstance(fingerprint, str)
                or not fingerprint
            ):
                self._metadata_api_error(HTTPStatus.BAD_REQUEST, "TARGET_MISMATCH", "確認対象IDが一致しません。")
                return

            from app.db.session import SessionLocal

            with METADATA_AUTOFILL_LOCK:
                with SessionLocal() as session:
                    item = session.get(EbookItem, ebook_item_id)
                    if item is None:
                        raise EbookMetadataAutofillError("item_not_found")
                    title = item.title
                    service = EbookMetadataAutofillService(session)
                    current = service.preview(ebook_item_id)
                    if not hmac.compare_digest(fingerprint, current.fingerprint):
                        raise EbookMetadataAutofillError("preview_changed")
                    protection_reasons = self._metadata_protection_reasons(item)
                    if protection_reasons:
                        protected_result = replace(
                            current,
                            operation="APPLY",
                            dry_run=False,
                            metadata_status="WORKFLOW_STATE_PROTECTED",
                        )
                        protected_evidence = build_evidence(
                            protected_result,
                            database_update_attempted=False,
                            database_update_succeeded=False,
                            changed_by=changed_by,
                        )
                        protected_evidence["protection_reasons"] = protection_reasons
                        evidence_path = write_evidence(
                            protected_evidence,
                            evidence_directory,
                        )
                        self._metadata_api_error(
                            HTTPStatus.CONFLICT,
                            "WORKFLOW_STATE_PROTECTED",
                            (
                                "WordPress下書きが存在するため、先に投稿との整合処理が必要です。"
                                if "WORDPRESS_DRAFT_EXISTS" in protection_reasons
                                else "基本情報を更新すると再審査が必要になるため、この画面からは更新できません。"
                            ),
                            metadata_status="WORKFLOW_STATE_PROTECTED",
                            protection_reasons=protection_reasons,
                            evidence_path=str(evidence_path),
                            database_update_attempted=False,
                            database_update_succeeded=False,
                        )
                        return
                    if not current.apply_possible:
                        blocked_result = replace(
                            current,
                            operation="APPLY",
                            dry_run=False,
                        )
                        blocked_evidence = build_evidence(
                            blocked_result,
                            database_update_attempted=False,
                            database_update_succeeded=False,
                            changed_by=changed_by,
                        )
                        write_evidence(blocked_evidence, evidence_directory)
                        blocked = any(
                            field.status in {"CONFLICT", "HUMAN_REVIEW_PROTECTED"}
                            for field in current.field_results
                        )
                        status = HTTPStatus.CONFLICT if blocked else HTTPStatus.UNPROCESSABLE_ENTITY
                        code = "METADATA_BLOCKED" if blocked else "NO_APPLICABLE_METADATA"
                        message = (
                            "候補競合または人間入力保護のため反映できません。"
                            if blocked
                            else "反映可能な基本情報候補がありません。"
                        )
                        self._metadata_api_error(status, code, message)
                        return
                    result = service.apply(
                        ebook_item_id=ebook_item_id,
                        confirmed_fingerprint=fingerprint,
                        changed_by=changed_by,
                    )
                    session.commit()
                evidence = build_evidence(
                    result,
                    database_update_attempted=service.database_update_attempted,
                    database_update_succeeded=True,
                    changed_by=changed_by,
                )
                evidence_path = write_evidence(evidence, evidence_directory)
            self._send_json(
                HTTPStatus.OK,
                self._metadata_payload(
                    result,
                    title=title,
                    evidence=evidence,
                    evidence_path=evidence_path,
                ),
            )
        except EbookMetadataAutofillError as exc:
            code = str(exc)
            failed_evidence_path = None
            if operation == "apply" and "current" in locals():
                failed_result = replace(
                    current,
                    operation="APPLY",
                    dry_run=False,
                )
                failed_evidence = build_evidence(
                    failed_result,
                    database_update_attempted=bool(
                        "service" in locals() and service.database_update_attempted
                    ),
                    database_update_succeeded=False,
                    changed_by=changed_by,
                )
                try:
                    failed_evidence_path = write_evidence(
                        failed_evidence,
                        evidence_directory,
                    )
                except Exception:
                    LOGGER.exception(
                        "Metadata autofill failure evidence write failed for %s",
                        ebook_item_id,
                    )
            if code == "item_not_found":
                self._metadata_api_error(HTTPStatus.NOT_FOUND, "ITEM_NOT_FOUND", "対象作品が見つかりません。")
            elif code in {"preview_changed", "stale_metadata"} or code.startswith("stale_metadata:"):
                self._metadata_api_error(
                    HTTPStatus.CONFLICT,
                    "PREVIEW_CHANGED",
                    "プレビュー後に基本情報が変更されました。",
                    metadata_status="PREVIEW_CHANGED",
                    evidence_path=(
                        str(failed_evidence_path)
                        if failed_evidence_path is not None
                        else ""
                    ),
                    database_update_attempted=False,
                    database_update_succeeded=False,
                )
            else:
                self._metadata_api_error(HTTPStatus.CONFLICT, "METADATA_BLOCKED", "基本情報を安全に反映できません。")
        except Exception:
            LOGGER.exception("Metadata autofill API failed for item %s", ebook_item_id)
            self._metadata_api_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "基本情報更新中に内部エラーが発生しました。")

    def _handle_database_catalog_edit(self) -> None:
        from app.db.session import SessionLocal
        from app.services.catalog_edit_service import (
            CatalogEditError,
            CatalogEditService,
        )

        form = self._read_database_urlencoded_form(max_bytes=16384)
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="catalog_edit_result",
                code="invalid_input",
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        def optional(name: str) -> str | None:
            return first(name) if name in form else None

        if not self._database_form_is_authorized(form):
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="catalog_edit_result",
                code="invalid_input",
            )
            return
        try:
            with SessionLocal() as session:
                result = CatalogEditService(session).save(
                    ebook_item_id=first("ebook_item_id"),
                    title=optional("title"),
                    volume_label=first("volume_label"),
                    authors=first("authors"),
                    publisher=first("publisher"),
                    imprint=optional("imprint"),
                    item_type=optional("item_type"),
                    release_date=optional("release_date"),
                    price=first("price"),
                    currency=first("currency"),
                    reason=first("reason"),
                    is_single_episode=(
                        first("is_single_episode").lower() == "true"
                    ),
                    is_split_edition=(
                        first("is_split_edition").lower() == "true"
                    ),
                    apply_to_future_series=(
                        first("apply_to_future_series").lower() == "true"
                    ),
                )
                session.commit()
        except CatalogEditError as exc:
            code = "item_not_found" if str(exc) == "item_not_found" else "invalid_input"
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="catalog_edit_result",
                code=code,
            )
            return
        except Exception:
            LOGGER.exception("Catalog edit failed for item %s", first("ebook_item_id"))
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="catalog_edit_result",
                code="internal_error",
            )
            return
        self._redirect_database_result(
            return_to=first("return_to"),
            parameter="catalog_edit_result",
            code=(
                "series_rule_skipped"
                if result.series_rule_skipped
                else "unchanged"
                if result.unchanged
                else "success"
            ),
        )

    def _handle_database_supplement_cancel(self) -> None:
        from app.db.session import SessionLocal
        from app.services.supplement_import_cancellation_service import (
            SupplementImportCancellationError,
            SupplementImportCancellationService,
        )

        form = self._read_database_urlencoded_form(max_bytes=16384)
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="supplement_cancel_result",
                code="CANCEL_INVALID_INPUT",
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        browser_session = self._read_session()
        if not self._database_form_is_authorized(
            form, expected_token=browser_session.op_token
        ):
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="supplement_cancel_result",
                code="CANCEL_INVALID_CSRF",
                session=browser_session,
            )
            return
        if not all(
            (
                first("ebook_item_id"),
                first("candidate_id"),
                first("expected_title"),
                first("confirmed").lower() == "true",
            )
        ):
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="supplement_cancel_result",
                code="CANCEL_INVALID_INPUT",
                session=browser_session,
            )
            return
        try:
            with SessionLocal() as database_session:
                result = SupplementImportCancellationService(
                    database_session,
                    repository_root=self._app().repo_root,
                ).cancel_registration(
                    ebook_item_id=first("ebook_item_id"),
                    candidate_id=first("candidate_id"),
                    expected_title=first("expected_title"),
                    operator="human:local_gui",
                )
                database_session.commit()
        except SupplementImportCancellationError as exc:
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="supplement_cancel_result",
                code=str(exc),
                session=browser_session,
            )
            return
        except Exception:
            LOGGER.exception(
                "Supplement cancellation failed for item %s",
                first("ebook_item_id"),
            )
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="supplement_cancel_result",
                code="CANCEL_INTERNAL_ERROR",
                session=browser_session,
            )
            return
        self._redirect_database_result(
            return_to=f"/supplement-import?run_id={result.import_run_id}",
            parameter="supplement_result",
            code=result.code,
            session=browser_session,
        )

    def _handle_database_metadata_autofill(self) -> None:
        from app.services.ebook_metadata_autofill_service import (
            EbookMetadataAutofillError,
            EbookMetadataAutofillService,
            build_evidence,
            write_evidence,
        )

        form = self._read_database_urlencoded_form(max_bytes=16384)
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="metadata_autofill_result",
                code="invalid_input",
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        return_to = first("return_to")
        if not self._database_form_is_authorized(form):
            self._redirect_database_result(
                return_to=return_to,
                parameter="metadata_autofill_result",
                code="invalid_input",
            )
            return

        operation = first("operation")
        ebook_item_id = first("ebook_item_id")
        try:
            if operation == "preview":
                from app.db.read_only_session import ReadOnlySessionLocal
                from app.gui.ebook_database_web import (
                    render_metadata_autofill_preview_page,
                )
                from app.services.workflow_action_service import (
                    get_workflow_action_token,
                    safe_database_return_path,
                )

                with ReadOnlySessionLocal() as session:
                    preview = EbookMetadataAutofillService(session).preview(
                        ebook_item_id
                    )
                page = render_metadata_autofill_preview_page(
                    preview,
                    csrf_token=get_workflow_action_token(),
                    return_to=safe_database_return_path(return_to),
                )
                self._send_html(
                    HTTPStatus.OK,
                    page,
                    session=self._read_session(),
                )
                return

            if operation != "apply" or first("confirmed").lower() != "true":
                raise EbookMetadataAutofillError("invalid_confirmation")

            from app.db.session import SessionLocal

            with SessionLocal() as session:
                result = EbookMetadataAutofillService(session).apply(
                    ebook_item_id=ebook_item_id,
                    confirmed_fingerprint=first("preview_fingerprint"),
                    changed_by="human:local_gui_metadata_autofill",
                )
                session.commit()

            evidence = build_evidence(
                result,
                database_update_attempted=True,
                database_update_succeeded=True,
                changed_by="human:local_gui_metadata_autofill",
            )
            try:
                write_evidence(
                    evidence,
                    self._app().repo_root
                    / "exchange"
                    / "logs"
                    / "ebook_metadata_autofill",
                )
            except Exception:
                LOGGER.exception(
                    "Metadata autofill evidence write failed for %s",
                    ebook_item_id,
                )
                self._redirect_database_result(
                    return_to=return_to,
                    parameter="metadata_autofill_result",
                    code="evidence_error",
                )
                return
        except EbookMetadataAutofillError as exc:
            code = str(exc)
            if code not in {"item_not_found", "preview_changed"}:
                code = "invalid_input"
            self._redirect_database_result(
                return_to=return_to,
                parameter="metadata_autofill_result",
                code=code,
            )
            return
        except Exception:
            LOGGER.exception("Metadata autofill failed for %s", ebook_item_id)
            self._redirect_database_result(
                return_to=return_to,
                parameter="metadata_autofill_result",
                code="internal_error",
            )
            return

        self._redirect_database_result(
            return_to=return_to,
            parameter="metadata_autofill_result",
            code=(
                "partially_applied"
                if result.metadata_status == "METADATA_PARTIALLY_APPLIED"
                else "applied"
                if any(
                    field.status == "APPLIED"
                    for field in result.field_results
                )
                else "unchanged"
            ),
        )

    def _handle_affiliate_settings_save(self) -> None:
        from app.db.session import SessionLocal
        from app.services.affiliate_account_settings_service import (
            AffiliateAccountSettingsService,
        )

        form = self._read_database_urlencoded_form(max_bytes=16384)
        if form is None:
            self._redirect_database_result(
                return_to="/affiliate-settings",
                parameter="affiliate_settings_result",
                code="invalid_input",
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        if not self._database_form_is_authorized(form):
            self._redirect_database_result(
                return_to="/affiliate-settings",
                parameter="affiliate_settings_result",
                code="invalid_token",
            )
            return
        try:
            with SessionLocal() as session:
                operation = first("operation")
                if operation == "save_destination_profile":
                    from app.db.repositories.affiliate_destination_profile_repository import (
                        AffiliateDestinationProfileRepository,
                    )

                    destination_key = first("destination_key")
                    definitions = {
                        "blog_main": ("wordpress", "メインブログ"),
                        "x_main": ("x", "公式X"),
                    }
                    definition = definitions.get(destination_key)
                    if (
                        first("provider") != "dmm"
                        or definition is None
                        or first("destination_type") != definition[0]
                    ):
                        raise ValueError("invalid destination profile")
                    AffiliateDestinationProfileRepository(session).upsert(
                        provider="dmm",
                        destination_type=definition[0],
                        destination_key=destination_key,
                        display_name=definition[1],
                        affiliate_id=first("affiliate_id"),
                        channel=first("channel"),
                        channel_id=first("channel_id"),
                        is_active=(
                            first("is_active").lower()
                            in {"1", "true", "on"}
                        ),
                    )
                    session.commit()
                    code = "success"
                else:
                    service = AffiliateAccountSettingsService(session)
                if operation == "delete":
                    service.unregister(service_name=first("service_name"))
                    code = "deleted"
                elif operation == "save":
                    service.register(
                        service_name=first("service_name"),
                        affiliate_id=first("affiliate_id"),
                        url_template=first("url_template"),
                        enabled=first("enabled").lower() in {"1", "true", "on"},
                    )
                    code = "success"
                elif operation != "save_destination_profile":
                    raise ValueError("invalid operation")
        except ValueError:
            self._redirect_database_result(
                return_to="/affiliate-settings",
                parameter="affiliate_settings_result",
                code="invalid_input",
            )
            return
        except Exception:
            LOGGER.exception("Affiliate settings save failed")
            self._redirect_database_result(
                return_to="/affiliate-settings",
                parameter="affiliate_settings_result",
                code="internal_error",
            )
            return
        self._redirect_database_result(
            return_to="/affiliate-settings",
            parameter="affiliate_settings_result",
            code=code,
        )

    def _handle_database_dmm_offer_save(self) -> None:
        import html
        from app.db.session import SessionLocal
        from app.services.dmm_manual_offer_service import (
            DmmManualOfferError,
            DmmManualOfferService,
        )

        browser_session = self._read_session()
        form = self._read_database_urlencoded_form(max_bytes=32768)
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="dmm_offer_result",
                code="invalid_input",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        if not self._database_form_is_authorized(form):
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="dmm_offer_result",
                code="invalid_token",
                session=browser_session,
            )
            return
        try:
            with SessionLocal() as session:
                service = DmmManualOfferService(session)
                preview = service.preview_input(
                    ebook_item_id=first("ebook_item_id"),
                    dmm_input=first("dmm_input"),
                    price=first("price"),
                    currency=first("currency"),
                )
                if first("operation") == "preview":
                    hidden = "".join(
                        f'<input type="hidden" name="{html.escape(name)}" value="{html.escape(first(name), quote=True)}">'
                        for name in (
                            "csrf_token", "ebook_item_id", "return_to",
                            "dmm_input", "price", "currency",
                        )
                    )
                    warning_labels = {
                        "rel_sponsored_missing": "rel=sponsored がありません（登録は可能です）。",
                        "affiliate_id_not_configured": "保存済みDMM affiliate IDがないため登録できません。",
                        "affiliate_id_mismatch": "HTMLのaffiliate IDが保存済みIDと一致しないため登録できません。",
                        "affiliate_profile_not_found": "HTMLのaffiliate IDに一致するDMM掲載先設定がないため登録できません。",
                        "affiliate_profile_ambiguous": "同じaffiliate IDが複数の掲載先に設定されているため登録できません。",
                        "affiliate_profile_inactive": "一致したDMM掲載先設定が無効なため登録できません。",
                        "dmm_destination_profile_not_configured": "有効なDMM掲載先設定がないため登録できません。",
                        "product_name_missing": "aタグの商品名が空のため登録できません。",
                        "title_mismatch": "商品名が選択中の作品タイトルと大きく異なるため登録できません。",
                    }
                    warning_html = "".join(
                        f"<li>{html.escape(warning_labels.get(code, code))}</li>"
                        for code in preview.warnings
                    )
                    if warning_html:
                        warning_html = f"<h2>警告</h2><ul>{warning_html}</ul>"
                    destination_html = "".join(
                        "<li>"
                        f"{html.escape(destination.display_name)} "
                        f"({html.escape(destination.destination_key)}): "
                        + (
                            "未設定"
                            if not destination.configured
                            else "無効"
                            if not destination.active
                            else "生成可能"
                            if destination.generation_available
                            else "生成不可"
                        )
                        + "</li>"
                        for destination in preview.destination_links
                    )
                    save_html = ""
                    if preview.registration_allowed:
                        save_html = f"""
                        <form method="post" action="/database-dmm-offer">{hidden}<input type="hidden" name="operation" value="save">
                        <label><input type="checkbox" name="confirmed" value="true" required> 解析結果と対象作品を確認しました</label>
                        <button type="submit">この内容で登録</button></form>"""
                    else:
                        save_html = "<p><strong>警告を解消するまで登録できません。</strong></p>"
                    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>DMMリンク確認</title></head><body>
                    <h1>DMMリンク解析結果プレビュー</h1>
                    <p>商品名: {html.escape(preview.product_name or '（URL入力のため取得なし）')}</p>
                    <p>商品管理番号: <code>{html.escape(preview.product_group_id)}</code></p>
                    <p>商品ID: <code>{html.escape(preview.store_item_id)}</code></p>
                    <p>商品URL: <code>{_render_preview_url(preview.product_url)}</code></p>
                    <p>HTML内アフィリエイトURL: <code>{_render_preview_url(preview.source_affiliate_url, empty_text='（URL入力）')}</code></p>
                    <p>後方互換ブログURL: <code>{_render_preview_url(preview.affiliate_url, empty_text='（ブログ用未設定）')}</code></p>
                    <p>affiliate ID: <code>{html.escape(preview.affiliate_id or '（保存済みIDから生成）')}</code></p>
                    <p>一致した掲載先: <strong>{html.escape(preview.matched_destination_name or '（URL入力または一致なし）')}</strong></p>
                    <h2>掲載先別リンク</h2><ul>{destination_html}</ul>
                    <p>service: <code>{html.escape(preview.service)}</code> / channel: <code>{html.escape(preview.channel)}</code> / channel_id: <code>{html.escape(preview.channel_id)}</code></p>
                    <p>価格: {html.escape(str(preview.price_amount or ''))} {html.escape(preview.currency or '')}</p>
                    {warning_html}
                    {save_html}
                    <a href="{html.escape(first('return_to'), quote=True)}">戻る</a></body></html>"""
                    self._send_html(HTTPStatus.OK, page, session=browser_session)
                    return
                if first("operation") != "save":
                    raise DmmManualOfferError("invalid operation")
                result = service.save(
                    preview=preview,
                    confirmed=first("confirmed").lower() == "true",
                )
                session.commit()
        except DmmManualOfferError as exc:
            message = str(exc)
            code = (
                "item_not_found" if message == "item_not_found"
                else "not_configured" if "not_configured" in message
                else "invalid_input"
            )
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="dmm_offer_result",
                code=code,
                session=browser_session,
            )
            return
        except Exception:
            LOGGER.exception("DMM manual offer save failed for item %s", first("ebook_item_id"))
            self._redirect_database_result(
                return_to=first("return_to"),
                parameter="dmm_offer_result",
                code="internal_error",
                session=browser_session,
            )
            return
        self._redirect_database_result(
            return_to=first("return_to"),
            parameter="dmm_offer_result",
            code="unchanged" if result.unchanged else "success",
            session=browser_session,
        )

    def _handle_database_manual_store_offer_create(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from app.db.session import SessionLocal
        from app.services.manual_store_offer_service import (
            ManualStoreOfferError,
            ManualStoreOfferService,
        )

        parameter = "manual_store_offer_result"
        browser_session = self._read_session()
        form = self._read_database_urlencoded_form(max_bytes=16384)
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter=parameter,
                code="INVALID_INPUT",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name) or []
            return values[0].strip() if values else ""

        return_to = first("return_to")
        if not self._database_form_is_authorized(
            form,
            expected_token=browser_session.op_token,
        ):
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="INVALID_CSRF",
                session=browser_session,
            )
            return
        if first("confirmed").lower() != "true":
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="CONFIRMATION_REQUIRED",
                session=browser_session,
            )
            return
        try:
            observed_at = None
            if first("observed_at"):
                observed_at = datetime.fromisoformat(first("observed_at"))
                if observed_at.tzinfo is None:
                    observed_at = observed_at.replace(
                        tzinfo=ZoneInfo("Asia/Tokyo")
                    )
            with SessionLocal() as session:
                result = ManualStoreOfferService(session).create_offer(
                    ebook_item_id=first("ebook_item_id"),
                    store_name=first("store_name"),
                    product_url=first("product_url"),
                    affiliate_url=first("affiliate_url"),
                    price=first("price"),
                    currency=first("currency"),
                    availability_status=first("availability_status"),
                    observed_at=observed_at,
                    operator="human:local_gui",
                )
                session.commit()
        except (ManualStoreOfferError, ValueError) as exc:
            code = str(exc)
            if code != "STORE_OFFER_ALREADY_EXISTS":
                code = "INVALID_INPUT"
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code=code,
                session=browser_session,
            )
            return
        except Exception:
            LOGGER.exception(
                "Manual store offer creation failed for item %s",
                first("ebook_item_id"),
            )
            self._redirect_database_result(
                return_to=return_to,
                parameter=parameter,
                code="INTERNAL_ERROR",
                session=browser_session,
            )
            return
        self._redirect_database_result(
            return_to=return_to,
            parameter=parameter,
            code=result.code,
            session=browser_session,
        )

    def _handle_database_amazon_offer_save(self) -> None:
        """GUIからAmazon手動リンクをstore_offersへ保存する。"""

        import hmac
        import html
        from urllib.parse import (
            parse_qs,
            urlencode,
            urlsplit,
            urlunsplit,
        )

        from app.db.models import EbookItem
        from app.db.session import SessionLocal
        from app.services.affiliate_account_settings_service import (
            AffiliateAccountSettingsService,
        )
        from app.services.amazon_manual_link_service import (
            AmazonManualLinkError,
            AmazonManualLinkService,
        )
        from app.services.amazon_manual_offer_service import (
            AmazonManualOfferService,
        )
        from app.services.workflow_action_service import (
            get_workflow_action_token,
            safe_database_return_path,
        )

        content_type = (
            self.headers.get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        if content_type != "application/x-www-form-urlencoded":
            self._send_text(
                HTTPStatus.BAD_REQUEST,
                "invalid request",
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            content_length = 0

        if content_length <= 0 or content_length > 4096:
            self._send_text(
                HTTPStatus.BAD_REQUEST,
                "invalid request",
            )
            return

        try:
            request_body = self.rfile.read(content_length).decode(
                "utf-8"
            )
            form = parse_qs(
                request_body,
                keep_blank_values=True,
            )
        except (UnicodeDecodeError, ValueError):
            self._send_text(
                HTTPStatus.BAD_REQUEST,
                "invalid request",
            )
            return

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def redirect_result(
            code: str,
            *,
            asin: str = "",
        ) -> None:
            return_to = safe_database_return_path(
                first("return_to")
            )
            parsed = urlsplit(return_to)
            query = parse_qs(
                parsed.query,
                keep_blank_values=True,
            )

            query["amazon_offer_result"] = [code]

            if asin:
                query["amazon_offer_asin"] = [asin]

            location = urlunsplit(
                (
                    "",
                    "",
                    parsed.path,
                    urlencode(query, doseq=True),
                    "",
                )
            )

            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        csrf_token = first("csrf_token")
        expected_token = get_workflow_action_token()

        if (
            not csrf_token
            or not hmac.compare_digest(
                csrf_token,
                expected_token,
            )
        ):
            redirect_result("invalid_token")
            return

        ebook_item_id = first("ebook_item_id")
        asin = first("asin")

        if not ebook_item_id:
            redirect_result("invalid_request")
            return

        try:
            with SessionLocal() as session:
                affiliate_settings_service = (
                    AffiliateAccountSettingsService(session)
                )

                tracking_id = (
                    affiliate_settings_service.get_affiliate_id(
                        service_name="amazon",
                    )
                )

                if not tracking_id:
                    redirect_result(
                        "tracking_id_not_configured"
                    )
                    return

                item = session.get(
                    EbookItem,
                    ebook_item_id,
                )

                if item is None:
                    redirect_result("item_not_found")
                    return

                try:
                    preview = AmazonManualLinkService().generate(
                        asin=asin,
                        tracking_id=tracking_id,
                    )
                except AmazonManualLinkError:
                    session.rollback()
                    redirect_result("invalid_input")
                    return

                if first("operation") == "preview":
                    browser_session = self._read_session()
                    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>Amazonリンク確認</title></head><body>
                    <h1>Amazonリンク保存前プレビュー</h1>
                    <p>商品URL: <code>{_render_preview_url(preview.product_url)}</code></p>
                    <p>アフィリエイトURL: <code>{_render_preview_url(preview.affiliate_url)}</code></p>
                    <form method="post" action="/database-amazon-offer">
                      <input type="hidden" name="csrf_token" value="{html.escape(csrf_token, quote=True)}">
                      <input type="hidden" name="ebook_item_id" value="{html.escape(ebook_item_id, quote=True)}">
                      <input type="hidden" name="asin" value="{html.escape(asin, quote=True)}">
                      <input type="hidden" name="return_to" value="{html.escape(first('return_to'), quote=True)}">
                      <input type="hidden" name="operation" value="save">
                      <label><input type="checkbox" name="confirmed" value="true" required> 内容を確認しました</label>
                      <button type="submit">確認して保存</button>
                    </form></body></html>"""
                    self._send_html(
                        HTTPStatus.OK,
                        page,
                        session=browser_session,
                    )
                    return

                if first("operation") not in {"", "save"} or (
                    first("operation") == "save"
                    and first("confirmed").lower() != "true"
                ):
                    redirect_result("invalid_request")
                    return

                service = AmazonManualOfferService(session)

                try:
                    result = service.save(
                        ebook_item_id=ebook_item_id,
                        asin=asin,
                        tracking_id=tracking_id,
                    )
                    session.commit()
                except AmazonManualLinkError:
                    session.rollback()
                    redirect_result("invalid_input")
                    return
                except ValueError:
                    session.rollback()
                    redirect_result("invalid_input")
                    return
                except Exception:
                    session.rollback()
                    LOGGER.exception(
                        "Amazon manual offer save failed for %s",
                        ebook_item_id,
                    )
                    redirect_result("internal_error")
                    return

        except Exception:
            LOGGER.exception(
                "Amazon manual offer database operation failed for %s",
                ebook_item_id,
            )
            redirect_result("internal_error")
            return

        redirect_result(
            "unchanged" if getattr(result, "unchanged", False) else "success",
            asin=result.asin,
        )


    def _handle_daily_summary_selection(self) -> None:
        import hmac
        from datetime import date

        from app.db.session import SessionLocal
        from app.services.daily_summary_selection_service import (
            DailySummarySelectionError,
            DailySummarySelectionService,
        )

        browser_session = self._read_session()
        form = self._read_database_urlencoded_form()
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="daily_summary_result",
                code="invalid_request",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def redirect(code: str) -> None:
            self._redirect_database_result(
                return_to=self._daily_summary_return_path(
                    first("return_to"), first("summary_date")
                ),
                parameter="daily_summary_result",
                code=code,
                session=browser_session,
            )

        if not hmac.compare_digest(first("csrf_token"), browser_session.op_token):
            redirect("invalid_token")
            return
        included_values = [value.strip().lower() for value in form.get("included", [])]
        if not included_values or any(value not in {"true", "false"} for value in included_values):
            redirect("invalid_request")
            return
        try:
            summary_date = date.fromisoformat(first("summary_date"))
            with SessionLocal() as session:
                DailySummarySelectionService(session).set_human_selection(
                    ebook_item_id=first("ebook_item_id"),
                    summary_date=summary_date,
                    included="true" in included_values,
                    selected_by="human:local_gui",
                )
                session.commit()
        except (ValueError, DailySummarySelectionError):
            redirect("invalid_request")
            return
        except Exception:
            LOGGER.exception("Daily summary selection update failed")
            redirect("internal_error")
            return
        browser_session.daily_summary_preview = None
        redirect("selection_saved")

    def _daily_summary_wordpress_client(self):
        from app.integrations.wordpress_rest_client import WordPressRestClient

        base_url = os.environ.get("WORDPRESS_BASE_URL") or os.environ.get("WP_BASE_URL") or ""
        username = os.environ.get("WORDPRESS_USERNAME") or os.environ.get("WP_USERNAME") or ""
        password = (
            os.environ.get("WORDPRESS_APPLICATION_PASSWORD")
            or os.environ.get("WP_APPLICATION_PASSWORD")
            or os.environ.get("WP_APP_PASSWORD")
            or ""
        )
        return WordPressRestClient(
            base_url=base_url,
            username=username,
            application_password=password,
        )

    def _handle_daily_summary_action(self) -> None:
        import hmac
        from datetime import date

        from app.db.session import SessionLocal
        from app.services.daily_summary_selection_service import DailySummarySelectionService
        from app.services.daily_summary_wordpress_draft_service import (
            DailySummaryDraftError,
            DailySummaryWordPressDraftService,
        )
        browser_session = self._read_session()
        form = self._read_database_urlencoded_form()
        if form is None:
            self._redirect_database_result(
                return_to="",
                parameter="daily_summary_result",
                code="invalid_request",
                session=browser_session,
            )
            return

        def first(name: str) -> str:
            values = form.get(name, [])
            return values[0].strip() if values else ""

        def redirect(code: str) -> None:
            self._redirect_database_result(
                return_to=self._daily_summary_return_path(
                    first("return_to"), first("summary_date")
                ),
                parameter="daily_summary_result",
                code=code,
                session=browser_session,
            )

        if not hmac.compare_digest(first("csrf_token"), browser_session.op_token):
            redirect("invalid_token")
            return
        operation = first("operation")
        if operation not in {
            "auto_select", "exclude_all", "reset_auto", "preview", "generate_dry_run"
        }:
            redirect("invalid_request")
            return
        try:
            summary_date = date.fromisoformat(first("summary_date"))
        except ValueError:
            redirect("invalid_request")
            return

        if operation in {"auto_select", "exclude_all", "reset_auto"}:
            try:
                with SessionLocal() as session:
                    service = DailySummarySelectionService(session)
                    if operation == "auto_select":
                        service.sync_auto_candidates(summary_date=summary_date)
                        result_code = "auto_selected"
                    elif operation == "exclude_all":
                        service.set_all_excluded(
                            summary_date=summary_date, selected_by="human:local_gui"
                        )
                        result_code = "all_excluded"
                    else:
                        service.reset_to_auto(
                            summary_date=summary_date, selected_by="human:local_gui"
                        )
                        result_code = "reset_to_auto"
                    session.commit()
            except Exception:
                LOGGER.exception("Daily summary bulk selection failed")
                redirect("internal_error")
                return
            browser_session.daily_summary_preview = None
            redirect(result_code)
            return

        try:
            with SessionLocal() as session:
                service = DailySummaryWordPressDraftService(
                    session, wordpress_client=self._daily_summary_wordpress_client()
                )
                if operation == "generate_dry_run":
                    preview = service.execute(summary_date=summary_date, dry_run=True)
                    session.commit()
                    result_code = "dry_run_ready"
                else:
                    preview = service.preview(summary_date)
                    result_code = "preview_ready" if preview.generation_allowed else "generation_blocked"
                browser_session.daily_summary_preview = preview
        except DailySummaryDraftError:
            redirect("generation_blocked")
            return
        except Exception:
            LOGGER.exception("Daily summary preview failed")
            redirect("internal_error")
            return
        redirect(result_code)

    def _handle_supplement_action(self, operation: str) -> None:
        from datetime import date
        from urllib.parse import urlencode

        from app.db.session import SessionLocal
        from app.services.rakuten_comic_calendar_parser import (
            SupplementParseError,
        )
        from app.services.supplement_import_service import (
            SOURCE_URL,
            SupplementImportError,
            SupplementImportService,
        )

        browser_session = self._read_session()
        form = self._read_database_urlencoded_form(max_bytes=1024 * 1024)

        def first(name: str) -> str:
            return str((form or {}).get(name, [""])[0]).strip()

        target_date_text = first("target_date") or first("release_date")
        import_run_id = first("import_run_id")

        def redirect(code: str, run_id: str = "") -> None:
            query = {"target_date": target_date_text}
            if run_id or import_run_id:
                query["run_id"] = run_id or import_run_id
            self._redirect_database_result(
                return_to=f"/supplement-import?{urlencode(query)}",
                parameter="supplement_result",
                code=code,
                session=browser_session,
            )

        if form is None:
            redirect("db_error")
            return
        try:
            self._verify_token(browser_session, first("csrf_token"))
        except AppError:
            redirect("csrf_error")
            return

        try:
            target_date = date.fromisoformat(target_date_text)
            release_date = date.fromisoformat(
                first("release_date") or target_date_text
            )
        except ValueError:
            redirect("invalid_date")
            return

        try:
            with SessionLocal() as database_session:
                with database_session.begin():
                    service = SupplementImportService(database_session)
                    if operation == "parse":
                        raw_text = first("raw_text")
                        if not raw_text:
                            raise SupplementImportError("EMPTY_TEXT")
                        run = service.parse_text(
                            raw_text=raw_text,
                            target_release_date=target_date,
                            changed_by="local_web",
                        )
                        import_run_id = run.id
                        result_code = "parsed"
                    elif operation == "edit":
                        service.update_candidate(
                            candidate_id=first("candidate_id"),
                            title=first("title"),
                            volume_label=first("volume_label") or None,
                            release_date=release_date,
                            publisher_name=first("publisher_name") or None,
                            author_name=first("author_name") or None,
                            imprint_name=first("imprint_name") or None,
                        )
                        result_code = "candidate_updated"
                    elif operation == "selection":
                        service.set_selected(
                            candidate_id=first("candidate_id"),
                            selected=first("selected") == "true",
                        )
                        result_code = "selection_updated"
                    elif operation == "import":
                        result = service.import_selected(
                            import_run_id=import_run_id,
                            changed_by="local_web",
                        )
                        result_code = (
                            "already_imported"
                            if result.idempotent
                            else "imported"
                        )
                    elif operation == "manual":
                        if first("source_url") != SOURCE_URL:
                            raise SupplementImportError("SOURCE_URL_INVALID")
                        title = first("title")
                        if not title:
                            raise SupplementImportError("TITLE_MISSING")
                        volume = first("volume_label")
                        title_line = title + (
                            f" 第{volume}巻" if volume else ""
                        )
                        run = service.parse_text(
                            raw_text="\n".join(
                                (
                                    title_line,
                                    first("publisher_name") or "未入力",
                                    first("author_name") or "未入力",
                                )
                            ),
                            target_release_date=release_date,
                            changed_by="local_web",
                        )
                        import_run_id = run.id
                        candidate = service.list_candidates(run.id)[0]
                        service.update_candidate(
                            candidate_id=candidate.id,
                            title=title,
                            volume_label=volume or None,
                            release_date=release_date,
                            publisher_name=first("publisher_name") or None,
                            author_name=first("author_name") or None,
                            imprint_name=first("imprint_name") or None,
                        )
                        if candidate.match_status == "NEW_CANDIDATE":
                            service.set_selected(
                                candidate_id=candidate.id, selected=True
                            )
                            result = service.import_selected(
                                import_run_id=run.id,
                                changed_by="local_web",
                            )
                            result_code = (
                                "already_imported"
                                if result.idempotent
                                else "imported"
                            )
                        elif candidate.match_status == "EXACT_DUPLICATE":
                            result_code = "exact_duplicate"
                        else:
                            result_code = "manual_review"
                    else:
                        raise SupplementImportError("OPERATION_INVALID")
        except SupplementParseError as exc:
            redirect("empty_text" if str(exc) == "EMPTY_TEXT" else "no_items")
            return
        except SupplementImportError as exc:
            code = {
                "EMPTY_TEXT": "empty_text",
                "TITLE_MISSING": "title_missing",
                "EXACT_DUPLICATE": "exact_duplicate",
                "POSSIBLE_DUPLICATE": "possible_duplicate",
                "NO_CANDIDATES_SELECTED": "no_selection",
            }.get(str(exc), "db_error")
            redirect(code)
            return
        except Exception:
            LOGGER.exception("Supplement import action failed")
            redirect("db_error")
            return
        redirect(result_code, import_run_id)

    def do_POST(self) -> None:  # noqa: N802
        parsed_path = urlparse(self.path).path
        if parsed_path == "/api/database-bulk-selection/validate":
            self._handle_database_bulk_selection_validate()
            return
        if parsed_path == "/database-bulk-affiliate/prepare":
            self._handle_database_bulk_affiliate_prepare()
            return
        if parsed_path == "/api/database-bulk-affiliate/dry-run":
            self._handle_database_bulk_affiliate_dry_run()
            return
        if parsed_path == "/database-bulk-affiliate/apply":
            self._handle_database_bulk_affiliate_apply()
            return
        supplement_operations = {
            "/supplement-parse": "parse",
            "/supplement-candidate-edit": "edit",
            "/supplement-candidate-selection": "selection",
            "/supplement-import-selected": "import",
            "/supplement-manual-add": "manual",
        }
        if parsed_path in supplement_operations:
            self._handle_supplement_action(supplement_operations[parsed_path])
            return
        metadata_parts = parsed_path.strip("/").split("/")
        if (
            len(metadata_parts) == 5
            and metadata_parts[:2] == ["api", "ebooks"]
            and metadata_parts[3] == "metadata"
            and metadata_parts[4] in {"preview", "apply"}
        ):
            self._handle_metadata_autofill_api(
                unquote(metadata_parts[2]), metadata_parts[4]
            )
            return
        if self.path.split("?", 1)[0] == "/affiliate-settings":
            self._handle_affiliate_settings_save()
            return
        if self.path.split("?", 1)[0] == "/database-daily-summary-selection":
            self._handle_daily_summary_selection()
            return
        if self.path.split("?", 1)[0] == "/database-daily-summary-action":
            self._handle_daily_summary_action()
            return
        if self.path.split("?", 1)[0] == "/database-catalog-edit":
            self._handle_database_catalog_edit()
            return
        if self.path.split("?", 1)[0] == "/database-supplement-cancel":
            self._handle_database_supplement_cancel()
            return
        if self.path.split("?", 1)[0] == "/database-metadata-autofill":
            self._handle_database_metadata_autofill()
            return
        if self.path.split("?", 1)[0] == "/database-dmm-offer":
            self._handle_database_dmm_offer_save()
            return
        if self.path.split("?", 1)[0] == "/database-manual-store-offer":
            self._handle_database_manual_store_offer_create()
            return
        if (
            self.path.split("?", 1)[0]
            == "/database-review-ready-request"
        ):
            self._handle_review_ready_request()
            return
        if (
            self.path.split("?", 1)[0]
            == "/database-review-ready-decision"
        ):
            self._handle_review_ready_decision()
            return
        if (
            self.path.split("?", 1)[0]
            == "/database-review-ready-reissue"
        ):
            self._handle_review_ready_reissue()
            return
        if (
            self.path.split("?", 1)[0]
            == "/database-amazon-offer"
        ):
            self._handle_database_amazon_offer_save()
            return
        if (
            self.path.split("?", 1)[0]
            == "/database-workflow"
        ):
            self._handle_database_workflow_update()
            return
        if (
            self.path.split("?", 1)[0]
            == "/database-wordpress-draft"
        ):
            self._handle_database_wordpress_draft_create()
            return
        if self.path.split("?", 1)[0] == "/database-wordpress-schedule":
            self._handle_database_wordpress_schedule()
            return
        if self.path.split("?", 1)[0] == "/database-wordpress-schedule-cancel":
            self._handle_database_wordpress_schedule(cancel=True)
            return

        try:
            parsed = urlparse(self.path)
            session = self._read_session()
            if parsed.path == "/prevalidate":
                self._handle_prevalidate(session)
                return
            if parsed.path == "/import":
                self._handle_import(session)
                return
            if parsed.path == "/convert-preview":
                self._handle_convert_preview(session)
                return
            self._send_text(HTTPStatus.NOT_FOUND, "not found")
        except AppError as exc:
            session = self._read_session()
            page = render_page_html(session, page_state={"error": str(exc), "validation": session.validation_bundle})
            self._send_html(exc.status, page, session=session)
        except Exception:
            request_id = secrets.token_hex(8)
            LOGGER.exception("Unexpected error during %s [request_id=%s]", self.path, request_id)
            self._send_text(HTTPStatus.INTERNAL_SERVER_ERROR, f"internal server error (request_id={request_id})")

    def _parse_multipart(self) -> cgi.FieldStorage:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > MAX_UPLOAD_BYTES + 1024 * 128:
            raise AppError("アップロードサイズは最大10MiBです。")
        return cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": str(content_length),
            },
            keep_blank_values=True,
        )

    def _handle_prevalidate(self, session: SessionData) -> None:
        form = self._parse_multipart()
        token = form.getfirst("op_token")
        self._verify_token(session, token)

        input_type = form.getfirst("input_type", "")
        file_item = form["csv_file"] if "csv_file" in form else None
        if isinstance(file_item, list):
            file_item = file_item[0] if file_item else None
        if file_item is None or not getattr(file_item, "filename", ""):
            raise AppError("CSVファイルを選択してください。")

        upload_file = getattr(file_item, "file", None)
        if upload_file is None:
            raise AppError("CSV読込に失敗しました。")

        raw_bytes = upload_file.read()
        if not isinstance(raw_bytes, bytes):
            raise AppError("CSV読込に失敗しました。")

        bundle = prevalidate_csv_upload(file_item.filename, raw_bytes, input_type)
        session.validation_bundle = bundle
        session.raw_result = bundle["raw_result"]
        session.summary = bundle["summary"]
        session.converted_csv_bytes = None
        session.converted_filename = None
        session.converted_preview = None
        page = render_page_html(session, page_state={"validation": bundle})
        self._send_html(HTTPStatus.OK, page, session=session)

    def _handle_convert_preview(self, session: SessionData) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        params = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
        token = params.get("op_token", [None])[0]
        self._verify_token(session, token)
        if not session.validation_bundle:
            raise AppError("先に事前検証を実行してください。")

        prepared = session.validation_bundle["prepared"]
        preview = build_old_format_conversion_preview(prepared)
        converted_bundle = preview["converted_bundle"]
        session.converted_csv_bytes = preview["converted_csv_bytes"]
        session.converted_filename = f"converted_{prepared.original_filename}"
        session.converted_preview = preview
        session.validation_bundle = converted_bundle
        session.raw_result = converted_bundle["raw_result"]
        session.summary = converted_bundle["summary"]
        page = render_page_html(
            session,
            page_state={
                "validation": session.validation_bundle,
                "conversion_preview": preview,
            },
        )
        self._send_html(HTTPStatus.OK, page, session=session)

    def _handle_import(self, session: SessionData) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        params = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
        token = params.get("op_token", [None])[0]
        self._verify_token(session, token)

        explicit_confirmation = params.get("explicit_confirmation", [""])[0] == "true"
        write_result = import_with_session_guard(
            session=session,
            repo_root=self._app().repo_root,
            explicit_confirmation=explicit_confirmation,
        )
        page = render_page_html(
            session,
            page_state={
                "validation": session.validation_bundle,
                "import_result": write_result,
            },
        )
        self._send_html(HTTPStatus.OK, page, session=session)


class MultiStoreAppServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], repo_root: Path):
        super().__init__(server_address, handler_cls)
        self.repo_root = repo_root
        self.session_store = SessionStore()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    host = _ensure_loopback_host(args.host)
    repo_root = Path(args.repo_root).resolve()

    httpd = MultiStoreAppServer((host, int(args.port)), MultiStoreAppHandler, repo_root=repo_root)
    print(f"Serving on http://{host}:{int(args.port)}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
