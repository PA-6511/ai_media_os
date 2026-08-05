from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import hmac
import html
import json
from pathlib import Path
import re
import unicodedata

from sqlalchemy.orm import Session

from app.db.repositories.ebook_metadata_autofill_repository import (
    EbookMetadataAutofillContext,
    EbookMetadataAutofillRepository,
    VerifiedMetadataRecord,
)


FIELD_ORDER = ("volume_label", "author_name", "publisher_name")
FIELD_REASONS = {
    "volume_label": "VOLUME_CONFLICT",
    "author_name": "AUTHOR_CONFLICT",
    "publisher_name": "PUBLISHER_CONFLICT",
}
SOURCE_PRIORITY = {
    "HUMAN_INPUT": 0,
    "NORMALIZED_EBOOK_ITEM": 1,
    "RAKUTEN_KOBO": 2,
    "TITLE_SUFFIX": 4,
}
AUDIT_BOOLEAN_FIELDS = (
    "external_communication_attempted",
    "wordpress_update_attempted",
    "database_update_attempted",
    "database_update_succeeded",
)


class EbookMetadataAutofillError(ValueError):
    pass


def _require_boolean(field_name: str, value: object) -> bool:
    if type(value) is not bool:
        raise EbookMetadataAutofillError(
            f"{field_name} must be an explicit boolean"
        )
    return value


def _validate_evidence_audit_booleans(evidence: dict[str, object]) -> None:
    for field_name in AUDIT_BOOLEAN_FIELDS:
        if field_name not in evidence:
            raise EbookMetadataAutofillError(
                f"missing required evidence field: {field_name}"
            )
        _require_boolean(field_name, evidence[field_name])


@dataclass(frozen=True)
class MetadataCandidate:
    value: str
    source_type: str
    confidence: str


@dataclass(frozen=True)
class MetadataFieldResult:
    field_name: str
    before: str | None
    candidate: str | None
    status: str
    source_type: str | None
    confidence: str | None
    source_types: tuple[str, ...] = ()
    reason: str | None = None
    conflict_values: tuple[str, ...] = ()
    apply_allowed: bool = False


@dataclass(frozen=True)
class MetadataAutofillPreview:
    ebook_item_id: str
    operation: str
    dry_run: bool
    metadata_status: str
    field_results: tuple[MetadataFieldResult, ...]
    fingerprint: str

    @property
    def apply_possible(self) -> bool:
        return any(result.apply_allowed for result in self.field_results)

    def result_for(self, field_name: str) -> MetadataFieldResult:
        return next(
            result
            for result in self.field_results
            if result.field_name == field_name
        )


def normalize_space(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", " ", str(value or "").strip())
    return normalized or None


def normalize_authors(value: str | None) -> str | None:
    parts: list[str] = []
    seen: set[str] = set()
    for raw_part in str(value or "").split("|"):
        part = normalize_space(raw_part)
        if part is None or part in seen:
            continue
        seen.add(part)
        parts.append(part)
    return "|".join(parts) or None


def normalize_publisher(value: str | None) -> str | None:
    return normalize_space(html.unescape(str(value or "")))


_EXPLICIT_VOLUME_PATTERNS = (
    re.compile(r"第\s*([0-9０-９]{1,4})\s*巻", re.IGNORECASE),
    re.compile(r"(?<![0-9０-９])([0-9０-９]{1,4})\s*巻", re.IGNORECASE),
    re.compile(
        r"(?<![A-Za-z])vol(?:ume)?\.?\s*([0-9０-９]{1,4})",
        re.IGNORECASE,
    ),
)
_PAREN_SUFFIX = re.compile(r"[\(（]\s*([0-9０-９]{1,4})\s*[\)）]\s*$")
_NUMBER_ONLY = re.compile(r"^\s*([0-9０-９]{1,4})\s*$")
_NUMBER_SUFFIX = re.compile(r"(?:^|\s)([0-9０-９]{1,4})\s*$")
_UNSAFE_SUFFIX_CONTEXT = re.compile(
    r"(?:ISBN|商品\s*ID|商品番号|商品コード|価格|￥|¥)\s*$",
    re.IGNORECASE,
)
_VOLUME_LABEL_WRAPPER = re.compile(
    r"^\s*(?:第\s*)?([^\s]+?)\s*(?:巻)?\s*$"
)
_VALID_ROMAN_NUMERAL = re.compile(
    r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})"
    r"(?:IX|IV|V?I{0,3})",
    re.IGNORECASE,
)
_ROMAN_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}
_KANJI_DIGITS = {
    "〇": 0,
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_KANJI_UNITS = {"十": 10, "百": 100, "千": 1000}


def _volume_number(value: str) -> int | None:
    normalized = unicodedata.normalize("NFKC", value)
    if not normalized.isdigit():
        return None
    number = int(normalized)
    return number if number > 0 else None


def _roman_volume_number(value: str) -> int | None:
    normalized = value.upper()
    if not normalized or _VALID_ROMAN_NUMERAL.fullmatch(normalized) is None:
        return None
    total = 0
    for index, character in enumerate(normalized):
        current = _ROMAN_VALUES[character]
        following = (
            _ROMAN_VALUES[normalized[index + 1]]
            if index + 1 < len(normalized)
            else 0
        )
        total += -current if current < following else current
    return total if total > 0 else None


def _kanji_volume_number(value: str) -> int | None:
    if value and all(character in _KANJI_DIGITS for character in value):
        digits = "".join(
            str(_KANJI_DIGITS[character]) for character in value
        )
        number = int(digits)
        return number if number > 0 else None
    if not value or any(
        character not in _KANJI_DIGITS and character not in _KANJI_UNITS
        for character in value
    ):
        return None
    total = 0
    pending_digit: int | None = None
    previous_unit = 10000
    for character in value:
        if character in _KANJI_DIGITS:
            if pending_digit is not None:
                return None
            pending_digit = _KANJI_DIGITS[character]
            continue
        unit = _KANJI_UNITS[character]
        if unit >= previous_unit:
            return None
        total += (pending_digit if pending_digit is not None else 1) * unit
        pending_digit = None
        previous_unit = unit
    total += pending_digit or 0
    return total if total > 0 else None


def extract_volume_candidates(value: str, *, is_title: bool = True) -> tuple[str, ...]:
    """Extract explicit markers and a conservative numeric title suffix."""

    text = str(value or "").strip()
    if not text:
        return ()
    numbers: list[int] = []

    def add(raw_number: str) -> None:
        number = _volume_number(raw_number)
        if number is not None and number not in numbers:
            numbers.append(number)

    for pattern in _EXPLICIT_VOLUME_PATTERNS:
        for match in pattern.finditer(text):
            add(match.group(1))

    suffix = _PAREN_SUFFIX.search(text)
    if suffix:
        add(suffix.group(1))

    number_only = _NUMBER_ONLY.fullmatch(text)
    if number_only:
        add(number_only.group(1))
    elif is_title:
        suffix = _NUMBER_SUFFIX.search(text)
        if suffix:
            prefix = text[: suffix.start(1)].rstrip()
            if not _UNSAFE_SUFFIX_CONTEXT.search(prefix):
                add(suffix.group(1))

    return tuple(f"第{number}巻" for number in numbers)


def normalize_volume_label(value: str | None) -> str | None:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    candidates = extract_volume_candidates(normalized, is_title=False)
    if len(candidates) == 1:
        return candidates[0]
    match = _VOLUME_LABEL_WRAPPER.fullmatch(normalized)
    if match is None:
        return None
    token = match.group(1)
    number = _roman_volume_number(token)
    if number is None:
        number = _kanji_volume_number(token)
    return f"第{number}巻" if number is not None else None


def _source_priority(source_type: str) -> tuple[int, str]:
    if source_type.startswith("VERIFIED_STORE:"):
        return (3, source_type)
    return (SOURCE_PRIORITY.get(source_type, 99), source_type)


def _candidate_result(
    *,
    field_name: str,
    before: str | None,
    candidates: list[MetadataCandidate],
    human_reviewed: bool,
) -> MetadataFieldResult:
    if field_name == "volume_label":
        normalizer = normalize_volume_label
    elif field_name == "author_name":
        normalizer = normalize_authors
    else:
        normalizer = normalize_publisher

    normalized_before = normalizer(before)
    normalized_candidates: list[MetadataCandidate] = []
    for candidate in candidates:
        normalized = normalizer(candidate.value)
        if normalized is None:
            continue
        normalized_candidates.append(replace(candidate, value=normalized))

    values = tuple(dict.fromkeys(c.value for c in normalized_candidates))
    source_types = tuple(
        dict.fromkeys(c.source_type for c in normalized_candidates)
    )
    selected = min(
        normalized_candidates,
        key=lambda candidate: _source_priority(candidate.source_type),
        default=None,
    )

    if human_reviewed:
        return MetadataFieldResult(
            field_name=field_name,
            before=before,
            candidate=normalized_before,
            status="HUMAN_REVIEW_PROTECTED",
            source_type="HUMAN_INPUT",
            confidence="VERIFIED",
            source_types=("HUMAN_INPUT",),
            reason="HUMAN_REVIEW_HISTORY",
        )

    if len(values) > 1:
        return MetadataFieldResult(
            field_name=field_name,
            before=before,
            candidate=None,
            status="CONFLICT",
            source_type=None,
            confidence=None,
            source_types=source_types,
            reason=FIELD_REASONS[field_name],
            conflict_values=values,
        )

    if before is not None and str(before).strip():
        if selected is not None and normalized_before == selected.value:
            status = "ALREADY_MATCHED"
        else:
            status = "EXISTING_VALUE_PRESERVED"
        return MetadataFieldResult(
            field_name=field_name,
            before=before,
            candidate=selected.value if selected else normalized_before,
            status=status,
            source_type=(
                selected.source_type if selected else "NORMALIZED_EBOOK_ITEM"
            ),
            confidence=selected.confidence if selected else "EXISTING",
            source_types=(
                source_types
                if source_types
                else ("NORMALIZED_EBOOK_ITEM",)
            ),
            reason=(
                FIELD_REASONS[field_name]
                if selected is not None and normalized_before != selected.value
                else None
            ),
        )

    if selected is None:
        return MetadataFieldResult(
            field_name=field_name,
            before=before,
            candidate=None,
            status="SOURCE_NOT_FOUND",
            source_type=None,
            confidence=None,
            reason="VERIFIED_SOURCE_NOT_FOUND",
        )

    return MetadataFieldResult(
        field_name=field_name,
        before=before,
        candidate=selected.value,
        status="READY",
        source_type=selected.source_type,
        confidence=selected.confidence,
        source_types=source_types,
        apply_allowed=True,
    )


def _record_candidates(
    records: tuple[VerifiedMetadataRecord, ...], field_name: str
) -> list[MetadataCandidate]:
    candidates: list[MetadataCandidate] = []
    for record in records:
        value = getattr(record, field_name)
        if str(value or "").strip():
            candidates.append(
                MetadataCandidate(
                    value=str(value),
                    source_type=record.source_type,
                    confidence=record.confidence,
                )
            )
    return candidates


def _overall_preview_status(
    results: tuple[MetadataFieldResult, ...]
) -> str:
    statuses = {result.status for result in results}
    missing_required = any(
        result.field_name in {"author_name", "publisher_name"}
        and result.status == "SOURCE_NOT_FOUND"
        for result in results
    )
    protected_empty = any(
        result.status == "HUMAN_REVIEW_PROTECTED"
        and not str(result.before or "").strip()
        for result in results
    )
    review_required = (
        "CONFLICT" in statuses
        or protected_empty
        or missing_required
        or any(
            result.reason in FIELD_REASONS.values()
            for result in results
        )
    )
    if review_required:
        return "METADATA_REVIEW_REQUIRED"
    if any(result.apply_allowed for result in results):
        return "METADATA_AUTOFILL_READY"
    if statuses == {"SOURCE_NOT_FOUND"}:
        return "METADATA_SOURCE_NOT_FOUND"
    return "METADATA_ALREADY_COMPLETE"


def _preview_fingerprint(
    ebook_item_id: str, results: tuple[MetadataFieldResult, ...]
) -> str:
    payload = {
        "ebook_item_id": ebook_item_id,
        "fields": [asdict(result) for result in results],
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_metadata_autofill_preview(
    context: EbookMetadataAutofillContext,
) -> MetadataAutofillPreview:
    volume_candidates = _record_candidates(
        context.verified_records, "volume_label"
    )
    volume_candidates.extend(
        MetadataCandidate(value=value, source_type="TITLE_SUFFIX", confidence="HIGH")
        for value in extract_volume_candidates(context.title, is_title=True)
    )
    candidates = {
        "volume_label": volume_candidates,
        "author_name": _record_candidates(
            context.verified_records, "author_name"
        ),
        "publisher_name": _record_candidates(
            context.verified_records, "publisher_name"
        ),
    }
    before_values = {
        "volume_label": context.volume_label,
        "author_name": context.author_name,
        "publisher_name": context.publisher_name,
    }
    results = tuple(
        _candidate_result(
            field_name=field_name,
            before=before_values[field_name],
            candidates=candidates[field_name],
            human_reviewed=field_name in context.human_reviewed_fields,
        )
        for field_name in FIELD_ORDER
    )
    return MetadataAutofillPreview(
        ebook_item_id=context.ebook_item_id,
        operation="PREVIEW",
        dry_run=True,
        metadata_status=_overall_preview_status(results),
        field_results=results,
        fingerprint=_preview_fingerprint(context.ebook_item_id, results),
    )


class EbookMetadataAutofillService:
    def __init__(self, session: Session) -> None:
        self.repository = EbookMetadataAutofillRepository(session)
        self.database_update_attempted = False

    def preview(self, ebook_item_id: str) -> MetadataAutofillPreview:
        context = self.repository.load_context(ebook_item_id.strip())
        if context is None:
            raise EbookMetadataAutofillError("item_not_found")
        return build_metadata_autofill_preview(context)

    def apply(
        self,
        *,
        ebook_item_id: str,
        confirmed_fingerprint: str,
        changed_by: str = "system:ebook_metadata_autofill",
    ) -> MetadataAutofillPreview:
        self.database_update_attempted = False
        preview = self.preview(ebook_item_id)
        if not confirmed_fingerprint or not hmac.compare_digest(
            confirmed_fingerprint, preview.fingerprint
        ):
            raise EbookMetadataAutofillError("preview_changed")
        values = {
            result.field_name: str(result.candidate)
            for result in preview.field_results
            if result.apply_allowed and result.candidate is not None
        }
        expected = {
            result.field_name: result.before
            for result in preview.field_results
            if result.field_name in values
        }
        self.database_update_attempted = True
        try:
            changed = self.repository.apply_empty_fields(
                ebook_item_id=preview.ebook_item_id,
                expected_before=expected,
                values=values,
                changed_by=changed_by,
            )
        except ValueError as exc:
            raise EbookMetadataAutofillError(str(exc)) from exc

        applied_results = tuple(
            replace(result, status="APPLIED", apply_allowed=False)
            if result.field_name in changed
            else result
            for result in preview.field_results
        )
        unresolved = any(
            result.status in {
                "CONFLICT",
                "SOURCE_NOT_FOUND",
                "HUMAN_REVIEW_PROTECTED",
                "EXISTING_VALUE_PRESERVED",
            }
            and (
                result.field_name in {"author_name", "publisher_name"}
                or result.status != "SOURCE_NOT_FOUND"
            )
            and not (
                result.status == "HUMAN_REVIEW_PROTECTED"
                and str(result.before or "").strip()
            )
            for result in applied_results
        )
        status = (
            "METADATA_PARTIALLY_APPLIED"
            if changed and unresolved
            else "METADATA_AUTOFILL_APPLIED"
            if changed
            else preview.metadata_status
        )
        return MetadataAutofillPreview(
            ebook_item_id=preview.ebook_item_id,
            operation="APPLY",
            dry_run=False,
            metadata_status=status,
            field_results=applied_results,
            fingerprint=preview.fingerprint,
        )


def build_evidence(
    preview: MetadataAutofillPreview,
    *,
    database_update_attempted: bool,
    database_update_succeeded: bool,
    changed_by: str,
    timestamp: datetime | None = None,
) -> dict[str, object]:
    database_update_attempted = _require_boolean(
        "database_update_attempted", database_update_attempted
    )
    database_update_succeeded = _require_boolean(
        "database_update_succeeded", database_update_succeeded
    )
    before_values = {
        result.field_name: result.before for result in preview.field_results
    }
    after_values = {
        result.field_name: (
            result.candidate
            if result.status in {"READY", "APPLIED"}
            else result.before
        )
        for result in preview.field_results
    }
    return {
        "ebook_item_id": preview.ebook_item_id,
        "operation": preview.operation,
        "dry_run": preview.dry_run,
        "metadata_status": preview.metadata_status,
        "before_values": before_values,
        "after_values": after_values,
        "field_results": [asdict(result) for result in preview.field_results],
        "source_types": {
            result.field_name: list(result.source_types)
            for result in preview.field_results
        },
        "confidence": {
            result.field_name: result.confidence
            for result in preview.field_results
        },
        "conflict_reasons": [
            result.reason
            for result in preview.field_results
            if result.reason
        ],
        "external_communication_attempted": False,
        "wordpress_update_attempted": False,
        "database_update_attempted": database_update_attempted,
        "database_update_succeeded": database_update_succeeded,
        "changed_by": changed_by,
        "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
    }


def write_evidence(
    evidence: dict[str, object], evidence_directory: Path
) -> Path:
    _validate_evidence_audit_booleans(evidence)
    evidence_directory.mkdir(parents=True, exist_ok=True)
    item_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(evidence["ebook_item_id"]))
    timestamp = str(evidence["timestamp"]).replace(":", "").replace("+", "_")
    operation = str(evidence["operation"]).lower()
    path = evidence_directory / f"{timestamp}_{item_id}_{operation}.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
