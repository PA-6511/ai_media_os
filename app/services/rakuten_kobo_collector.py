from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from app.integrations.rakuten_kobo_api_client import (
    DEFAULT_MAX_RESPONSE_BYTES,
    FetchedRakutenKoboResponse,
    RakutenKoboFailureDetails,
)


DEFAULT_MAX_ITEMS = 1_000
DEFAULT_MAX_JSON_DEPTH = 32
RAW_FILENAME_SUFFIX = ".json"


class RakutenKoboCollectorError(RuntimeError):
    def __init__(self, code: str, *, cause: BaseException | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.cause_type = type(cause).__name__ if cause is not None else None

    @property
    def safe_summary(self) -> str:
        if self.cause_type:
            return f"{self.code};cause={self.cause_type}"
        return self.code


@dataclass(frozen=True)
class ResponseInspection:
    converter_ready: bool
    item_count: int | None
    error_summary: str | None


@dataclass(frozen=True)
class RawSaveResult:
    path: Path
    sha256: str
    size_bytes: int
    duplicate_detected: bool


@dataclass(frozen=True)
class CollectionOutcome:
    status: str
    collection_id: str
    raw_response_path: Path | None
    evidence_path: Path
    converter_ready: bool
    duplicate_detected: bool
    evidence: Mapping[str, Any]


class RakutenKoboCollector:
    def __init__(
        self,
        *,
        repository_root: Path,
        output_directory: Path,
        evidence_directory: Path,
        maximum_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        maximum_items: int = DEFAULT_MAX_ITEMS,
        maximum_json_depth: int = DEFAULT_MAX_JSON_DEPTH,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve(strict=True)
        self.output_directory = _repository_path(
            self.repository_root, output_directory
        )
        self.evidence_directory = _repository_path(
            self.repository_root, evidence_directory
        )
        if maximum_response_bytes <= 0 or maximum_items <= 0:
            raise ValueError("collector limits must be positive")
        if maximum_json_depth < 3:
            raise ValueError("maximum_json_depth must be at least 3")
        self.maximum_response_bytes = int(maximum_response_bytes)
        self.maximum_items = int(maximum_items)
        self.maximum_json_depth = int(maximum_json_depth)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def collect_fetched_response(
        self,
        response: FetchedRakutenKoboResponse,
        *,
        search_selector_type: str | None = None,
    ) -> CollectionOutcome:
        fetched_at = _utc(self._now())
        collection_id = str(uuid.uuid4())
        evidence: dict[str, Any] = {
            "operation": "rakuten_kobo_response_collection",
            "collection_id": collection_id,
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "http_method": "GET",
            "endpoint_host": _safe_host(response.endpoint_host),
            "response_status": int(response.status_code),
            "content_type": _media_type(response.content_type),
            "response_size_bytes": len(response.body),
            "raw_response_sha256": hashlib.sha256(response.body).hexdigest(),
            "raw_response_path": None,
            "response_content_length_present": False,
            "response_content_length": None,
            "provider_error_code": None,
            "provider_error_message": None,
            "failure_category": None,
            "retryable": None,
            "request_path": None,
            "request_query_key_names": [],
            "request_header_names": [],
            "search_selector_type": _safe_selector_type(
                search_selector_type
            ),
            "search_result_count": None,
            "duplicate_detected": False,
            "external_get_attempted": True,
            "external_get_succeeded": True,
            "raw_save_attempted": False,
            "raw_save_succeeded": False,
            "converter_ready": False,
            "database_write_performed": False,
            "wordpress_write_performed": False,
            "error_summary": None,
        }
        raw_path: Path | None = None
        status = "FAILED"
        inspection = ResponseInspection(False, None, None)
        try:
            if len(response.body) > self.maximum_response_bytes:
                raise RakutenKoboCollectorError("RESPONSE_SIZE_LIMIT_EXCEEDED")
            evidence["raw_save_attempted"] = True
            saved = save_raw_response_bytes(
                response.body,
                repository_root=self.repository_root,
                output_directory=self.output_directory,
                fetched_at=fetched_at,
            )
            raw_path = saved.path
            evidence.update(
                {
                    "raw_response_path": _display_path(
                        saved.path, self.repository_root
                    ),
                    "duplicate_detected": saved.duplicate_detected,
                    "raw_save_succeeded": True,
                }
            )
            inspection = inspect_response_bytes(
                response.body,
                maximum_bytes=self.maximum_response_bytes,
                maximum_items=self.maximum_items,
                maximum_depth=self.maximum_json_depth,
            )
            evidence["converter_ready"] = inspection.converter_ready
            evidence["search_result_count"] = inspection.item_count
            evidence["error_summary"] = inspection.error_summary
            status = (
                "PASS"
                if inspection.converter_ready
                else "SAVED_NOT_CONVERTER_READY"
            )
        except RakutenKoboCollectorError as exc:
            evidence["error_summary"] = exc.safe_summary
        evidence_path = self._write_evidence(
            collection_id=collection_id,
            fetched_at=fetched_at,
            evidence=evidence,
        )
        return CollectionOutcome(
            status=status,
            collection_id=collection_id,
            raw_response_path=raw_path,
            evidence_path=evidence_path,
            converter_ready=inspection.converter_ready,
            duplicate_detected=bool(evidence["duplicate_detected"]),
            evidence=evidence,
        )

    def record_fetch_failure(
        self,
        *,
        endpoint_host: str,
        error_summary: str,
        external_get_attempted: bool,
        search_selector_type: str | None = None,
        failure_details: RakutenKoboFailureDetails | None = None,
    ) -> CollectionOutcome:
        fetched_at = _utc(self._now())
        collection_id = str(uuid.uuid4())
        details = failure_details or RakutenKoboFailureDetails()
        evidence: dict[str, Any] = {
            "operation": "rakuten_kobo_response_collection",
            "collection_id": collection_id,
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "http_method": "GET",
            "endpoint_host": _safe_host(details.request_host or endpoint_host),
            "response_status": details.response_status,
            "content_type": details.response_content_type,
            "response_size_bytes": details.response_body_byte_count,
            "raw_response_sha256": details.response_body_sha256,
            "raw_response_path": None,
            "response_content_length_present": (
                details.response_content_length_present
            ),
            "response_content_length": details.response_content_length,
            "provider_error_code": details.provider_error_code,
            "provider_error_message": details.provider_error_message,
            "failure_category": details.failure_category,
            "retryable": details.retryable,
            "request_path": details.request_path,
            "request_query_key_names": list(
                details.request_query_key_names
            ),
            "request_header_names": list(details.request_header_names),
            "search_selector_type": _safe_selector_type(
                search_selector_type
            ),
            "search_result_count": None,
            "duplicate_detected": False,
            "external_get_attempted": bool(external_get_attempted),
            "external_get_succeeded": False,
            "raw_save_attempted": False,
            "raw_save_succeeded": False,
            "converter_ready": False,
            "database_write_performed": False,
            "wordpress_write_performed": False,
            "error_summary": _safe_error_summary(error_summary),
        }
        evidence_path = self._write_evidence(
            collection_id=collection_id,
            fetched_at=fetched_at,
            evidence=evidence,
        )
        return CollectionOutcome(
            status="FETCH_FAILED",
            collection_id=collection_id,
            raw_response_path=None,
            evidence_path=evidence_path,
            converter_ready=False,
            duplicate_detected=False,
            evidence=evidence,
        )

    def validate_saved_response(self, path: Path) -> ResponseInspection:
        _, inspection = self.load_saved_response(path)
        return inspection

    def load_saved_response(
        self, path: Path
    ) -> tuple[bytes, ResponseInspection]:
        raw = read_saved_raw_response(
            path,
            repository_root=self.repository_root,
            output_directory=self.output_directory,
            maximum_bytes=self.maximum_response_bytes,
        )
        inspection = inspect_response_bytes(
            raw,
            maximum_bytes=self.maximum_response_bytes,
            maximum_items=self.maximum_items,
            maximum_depth=self.maximum_json_depth,
        )
        return raw, inspection

    def _write_evidence(
        self,
        *,
        collection_id: str,
        fetched_at: datetime,
        evidence: Mapping[str, Any],
    ) -> Path:
        _validate_evidence(evidence)
        timestamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
        name = f"{timestamp}-rakuten-kobo-collection-{collection_id}.json"
        body = (
            json.dumps(
                dict(evidence),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")
        return _atomic_write_new(
            self.evidence_directory,
            name,
            body,
            repository_root=self.repository_root,
        )


def inspect_response_bytes(
    raw: bytes,
    *,
    maximum_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    maximum_items: int = DEFAULT_MAX_ITEMS,
    maximum_depth: int = DEFAULT_MAX_JSON_DEPTH,
) -> ResponseInspection:
    if len(raw) > maximum_bytes:
        return ResponseInspection(False, None, "RESPONSE_SIZE_LIMIT_EXCEEDED")
    try:
        text = raw.decode("utf-8")
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return ResponseInspection(False, None, "INVALID_JSON")
    if _json_depth_exceeds(value, maximum_depth):
        return ResponseInspection(False, None, "JSON_DEPTH_LIMIT_EXCEEDED")
    if not isinstance(value, dict):
        return ResponseInspection(False, None, "ROOT_OBJECT_REQUIRED")
    items = value.get("Items")
    if not isinstance(items, list):
        return ResponseInspection(False, None, "ITEMS_LIST_REQUIRED")
    if len(items) > maximum_items:
        return ResponseInspection(False, len(items), "ITEM_COUNT_LIMIT_EXCEEDED")
    for index, wrapper in enumerate(items):
        if not isinstance(wrapper, dict):
            return ResponseInspection(
                False, len(items), f"ITEM_WRAPPER_OBJECT_REQUIRED:index={index}"
            )
        if not isinstance(wrapper.get("Item"), dict):
            return ResponseInspection(
                False, len(items), f"ITEM_OBJECT_REQUIRED:index={index}"
            )
    return ResponseInspection(True, len(items), None)


def save_raw_response_bytes(
    raw: bytes,
    *,
    repository_root: Path,
    output_directory: Path,
    fetched_at: datetime,
) -> RawSaveResult:
    root = repository_root.resolve(strict=True)
    directory = _repository_path(root, output_directory)
    _ensure_directory(directory, repository_root=root)
    digest = hashlib.sha256(raw).hexdigest()
    duplicate = _find_duplicate(directory, digest)
    if duplicate is not None:
        return RawSaveResult(duplicate, digest, len(raw), True)
    timestamp = _utc(fetched_at).strftime("%Y%m%dT%H%M%SZ")
    name = f"{timestamp}-rakuten-kobo-{digest[:16]}{RAW_FILENAME_SUFFIX}"
    path = _atomic_write_new(
        directory,
        name,
        raw,
        repository_root=root,
    )
    persisted = _read_file_nofollow(path, maximum_bytes=len(raw) + 1)
    if hashlib.sha256(persisted).hexdigest() != digest or persisted != raw:
        raise RakutenKoboCollectorError("RAW_SHA256_VERIFICATION_FAILED")
    if stat.S_IMODE(os.lstat(path).st_mode) != 0o600:
        raise RakutenKoboCollectorError("RAW_MODE_VERIFICATION_FAILED")
    return RawSaveResult(path, digest, len(raw), False)


def read_saved_raw_response(
    path: Path,
    *,
    repository_root: Path,
    output_directory: Path,
    maximum_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> bytes:
    root = repository_root.resolve(strict=True)
    directory = _repository_path(root, output_directory)
    expected = _repository_path(root, path)
    if expected.parent != directory or not _raw_filename(expected.name):
        raise RakutenKoboCollectorError("RAW_PATH_NOT_COLLECTOR_MANAGED")
    info = os.lstat(expected)
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise RakutenKoboCollectorError("RAW_FILE_MODE_OR_TYPE_INVALID")
    raw = _read_file_nofollow(expected, maximum_bytes=maximum_bytes)
    expected_prefix = expected.stem.rsplit("-", 1)[-1]
    if hashlib.sha256(raw).hexdigest()[:16] != expected_prefix:
        raise RakutenKoboCollectorError("RAW_FILENAME_SHA256_MISMATCH")
    return raw


def _find_duplicate(directory: Path, digest: str) -> Path | None:
    suffix = f"-rakuten-kobo-{digest[:16]}{RAW_FILENAME_SUFFIX}"
    directory_fd = _open_directory(directory)
    try:
        for name in sorted(os.listdir(directory_fd)):
            if not name.endswith(suffix):
                continue
            info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise RakutenKoboCollectorError("DUPLICATE_CANDIDATE_INVALID")
            try:
                candidate = _read_relative_file(
                    directory_fd,
                    name,
                    maximum_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                )
            except RakutenKoboCollectorError:
                raise
            if hashlib.sha256(candidate).hexdigest() == digest:
                return directory / name
        return None
    finally:
        os.close(directory_fd)


def _atomic_write_new(
    directory: Path,
    name: str,
    body: bytes,
    *,
    repository_root: Path,
) -> Path:
    if Path(name).name != name or not name:
        raise RakutenKoboCollectorError("INVALID_OUTPUT_NAME")
    _ensure_directory(directory, repository_root=repository_root)
    directory_fd = _open_directory(directory)
    temporary_name = f".{name}.tmp-{uuid.uuid4().hex}"
    descriptor: int | None = None
    published = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(
            temporary_name,
            flags,
            0o600,
            dir_fd=directory_fd,
        )
        offset = 0
        while offset < len(body):
            written = os.write(descriptor, body[offset:])
            if written <= 0:
                raise RakutenKoboCollectorError("SHORT_WRITE")
            offset += written
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        _atomic_rename_noreplace(
            directory_fd=directory_fd,
            source_name=temporary_name,
            destination_name=name,
        )
        published = True
        os.fsync(directory_fd)
        return directory / name
    except FileExistsError as exc:
        raise RakutenKoboCollectorError("OUTPUT_ALREADY_EXISTS", cause=exc) from exc
    except RakutenKoboCollectorError:
        raise
    except OSError as exc:
        raise RakutenKoboCollectorError("ATOMIC_SAVE_FAILED", cause=exc) from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if not published:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except OSError:
                pass
        os.close(directory_fd)


def _atomic_rename_noreplace(
    *, directory_fd: int, source_name: str, destination_name: str
) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as exc:
        raise RakutenKoboCollectorError(
            "ATOMIC_RENAME_NOREPLACE_UNAVAILABLE", cause=exc
        ) from exc
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        directory_fd,
        os.fsencode(source_name),
        directory_fd,
        os.fsencode(destination_name),
        1,
    )
    if result == 0:
        return
    number = ctypes.get_errno()
    if number == errno.EEXIST:
        raise FileExistsError(number, os.strerror(number), destination_name)
    raise RakutenKoboCollectorError(
        "ATOMIC_RENAME_FAILED", cause=OSError(number, os.strerror(number))
    )


def _ensure_directory(directory: Path, *, repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    candidate = Path(os.path.abspath(directory))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise RakutenKoboCollectorError("OUTPUT_OUTSIDE_REPOSITORY", cause=exc) from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RakutenKoboCollectorError("SYMLINK_PATH_REJECTED")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RakutenKoboCollectorError("SYMLINK_PATH_REJECTED")
    info = os.lstat(directory)
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise RakutenKoboCollectorError("OUTPUT_DIRECTORY_INVALID")


def _open_directory(directory: Path) -> int:
    return os.open(
        directory,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )


def _read_file_nofollow(path: Path, *, maximum_bytes: int) -> bytes:
    if path.is_symlink():
        raise RakutenKoboCollectorError("SYMLINK_PATH_REJECTED")
    directory_fd = _open_directory(path.parent)
    try:
        return _read_relative_file(directory_fd, path.name, maximum_bytes=maximum_bytes)
    finally:
        os.close(directory_fd)


def _read_relative_file(directory_fd: int, name: str, *, maximum_bytes: int) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise RakutenKoboCollectorError("RAW_FILE_NOT_REGULAR")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, maximum_bytes + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > maximum_bytes:
                raise RakutenKoboCollectorError("RESPONSE_SIZE_LIMIT_EXCEEDED")
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError as exc:
        raise RakutenKoboCollectorError("RAW_READ_FAILED", cause=exc) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _json_depth_exceeds(value: Any, maximum_depth: int) -> bool:
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > maximum_depth:
            return True
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return False


def _repository_path(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    normalized = Path(os.path.abspath(candidate))
    try:
        normalized.relative_to(root)
    except ValueError as exc:
        raise RakutenKoboCollectorError("PATH_OUTSIDE_REPOSITORY", cause=exc) from exc
    return normalized


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _raw_filename(name: str) -> bool:
    if not name.endswith(RAW_FILENAME_SUFFIX):
        return False
    parts = name.removesuffix(RAW_FILENAME_SUFFIX).split("-")
    return len(parts) >= 4 and parts[-3:-1] == ["rakuten", "kobo"] and len(parts[-1]) == 16


def _media_type(value: str) -> str | None:
    media_type = str(value or "").split(";", 1)[0].strip().lower()
    return media_type[:128] or None


def _safe_host(value: str) -> str:
    host = str(value or "").strip().lower()
    if not host or len(host) > 253 or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for c in host):
        return "invalid-host"
    return host


def _safe_error_summary(value: str) -> str:
    safe = str(value or "UNKNOWN_ERROR")[:256]
    if any(token in safe.lower() for token in ("http://", "https://", "authorization", "?")):
        return "REDACTED_ERROR"
    return safe


def _safe_selector_type(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in {"title", "itemNumber", "title+itemNumber"}:
        raise RakutenKoboCollectorError("INVALID_SEARCH_SELECTOR_TYPE")
    return value


def _validate_evidence(evidence: Mapping[str, Any]) -> None:
    expected = {
        "operation",
        "collection_id",
        "fetched_at",
        "http_method",
        "endpoint_host",
        "response_status",
        "content_type",
        "response_size_bytes",
        "raw_response_sha256",
        "raw_response_path",
        "response_content_length_present",
        "response_content_length",
        "provider_error_code",
        "provider_error_message",
        "failure_category",
        "retryable",
        "request_path",
        "request_query_key_names",
        "request_header_names",
        "search_selector_type",
        "search_result_count",
        "duplicate_detected",
        "external_get_attempted",
        "external_get_succeeded",
        "raw_save_attempted",
        "raw_save_succeeded",
        "converter_ready",
        "database_write_performed",
        "wordpress_write_performed",
        "error_summary",
    }
    if set(evidence) != expected:
        raise RakutenKoboCollectorError("EVIDENCE_SCHEMA_INVALID")
    if evidence["http_method"] != "GET":
        raise RakutenKoboCollectorError("EVIDENCE_METHOD_INVALID")
    request_path = evidence["request_path"]
    if request_path is not None and (
        not isinstance(request_path, str)
        or not request_path.startswith("/")
        or any(token in request_path for token in ("?", "#", "://"))
    ):
        raise RakutenKoboCollectorError("EVIDENCE_REQUEST_PATH_INVALID")
    for field_name in ("request_query_key_names", "request_header_names"):
        names = evidence[field_name]
        if not isinstance(names, list) or any(
            not isinstance(name, str) or not name or len(name) > 128
            for name in names
        ):
            raise RakutenKoboCollectorError("EVIDENCE_NAME_LIST_INVALID")
    serialized = json.dumps(evidence, ensure_ascii=False).lower()
    for forbidden in (
        "application_id",
        "application id",
        "access_key",
        "access key",
        "affiliate_id",
        "affiliate id",
        "authorization",
        "cookie",
        "set-cookie",
        "http://",
        "https://",
        "response_body",
    ):
        if forbidden in serialized:
            raise RakutenKoboCollectorError("EVIDENCE_SECRET_FIELD_REJECTED")
