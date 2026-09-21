from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Callable, Mapping, Sequence


MAX_BATCH_SIZE = 10
VALID_MODES = frozenset({"dry_run", "execute"})
ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")

_AMAZON_ASIN_PATTERNS = (
    re.compile(
        r"(?:/dp/|/gp/product/)([A-Za-z0-9]{10})(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[?&])asin=([A-Za-z0-9]{10})(?:[&#]|$)",
        re.IGNORECASE,
    ),
)


class FastIntakeBatchError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FastIntakeBatchInput:
    asin: str
    title: str


@dataclass(frozen=True)
class FastIntakeBatchRowResult:
    row_number: int
    asin: str
    title: str
    status: str
    code: str = ""
    message: str = ""
    payload: Mapping[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status == "SUCCESS"


@dataclass(frozen=True)
class FastIntakeBatchResult:
    mode: str
    requested_count: int
    success_count: int
    failed_count: int
    rows: tuple[FastIntakeBatchRowResult, ...]

    @property
    def ok(self) -> bool:
        return self.failed_count == 0

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "requested_count": self.requested_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "rows": [
                {
                    "row_number": row.row_number,
                    "asin": row.asin,
                    "title": row.title,
                    "status": row.status,
                    "code": row.code,
                    "message": row.message,
                    "payload": dict(row.payload or {}),
                }
                for row in self.rows
            ],
        }


SingleIntakeCallable = Callable[
    [str, str, str],
    Mapping[str, Any] | None,
]


def normalize_asin(value: str) -> str:
    raw = unicodedata.normalize("NFKC", str(value or "")).strip()

    if not raw:
        raise FastIntakeBatchError("ASIN_REQUIRED")

    direct = raw.upper()
    if ASIN_PATTERN.fullmatch(direct):
        return direct

    for pattern in _AMAZON_ASIN_PATTERNS:
        match = pattern.search(raw)
        if match:
            asin = match.group(1).upper()
            if ASIN_PATTERN.fullmatch(asin):
                return asin

    raise FastIntakeBatchError("ASIN_INVALID")


def normalize_title(value: str) -> str:
    title = unicodedata.normalize("NFKC", str(value or "")).strip()

    if not title:
        raise FastIntakeBatchError("TITLE_REQUIRED")

    return title


class EbookFastIntakeBatchService:
    """
    Maximum-10 row orchestrator for the existing one-book fast intake path.

    This service deliberately does not duplicate the current DB/import logic.
    The caller injects `single_intake`, which must execute exactly the same
    one-book path already used by the production fast-intake handler.

    One failed row does not abort the remaining rows.
    """

    def __init__(self, single_intake: SingleIntakeCallable) -> None:
        if not callable(single_intake):
            raise TypeError("single_intake must be callable")
        self.single_intake = single_intake

    def run(
        self,
        rows: Sequence[FastIntakeBatchInput],
        *,
        mode: str = "dry_run",
    ) -> FastIntakeBatchResult:
        normalized_mode = str(mode or "").strip()

        if normalized_mode not in VALID_MODES:
            raise FastIntakeBatchError("MODE_INVALID")

        if not rows:
            raise FastIntakeBatchError("BATCH_EMPTY")

        if len(rows) > MAX_BATCH_SIZE:
            raise FastIntakeBatchError("BATCH_LIMIT_EXCEEDED")

        results: list[FastIntakeBatchRowResult] = []

        # Prevent the same ASIN being processed twice in one submit.
        seen_asins: set[str] = set()

        for row_number, row in enumerate(rows, start=1):
            raw_asin = str(row.asin or "")
            raw_title = str(row.title or "")

            try:
                asin = normalize_asin(raw_asin)
                title = normalize_title(raw_title)

                if asin in seen_asins:
                    raise FastIntakeBatchError(
                        "DUPLICATE_ASIN_IN_BATCH"
                    )

                seen_asins.add(asin)

                payload = self.single_intake(
                    asin,
                    title,
                    normalized_mode,
                )

                if payload is None:
                    safe_payload: Mapping[str, Any] = {}
                elif isinstance(payload, Mapping):
                    safe_payload = payload
                else:
                    raise FastIntakeBatchError(
                        "SINGLE_INTAKE_INVALID_RESULT"
                    )

                results.append(
                    FastIntakeBatchRowResult(
                        row_number=row_number,
                        asin=asin,
                        title=title,
                        status="SUCCESS",
                        payload=safe_payload,
                    )
                )

            except FastIntakeBatchError as exc:
                results.append(
                    FastIntakeBatchRowResult(
                        row_number=row_number,
                        asin=raw_asin.strip(),
                        title=raw_title.strip(),
                        status="FAILED",
                        code=exc.code,
                        message=str(exc),
                    )
                )

            except Exception as exc:
                # Partial-success behavior is intentional:
                # one row must not abort the other nine.
                results.append(
                    FastIntakeBatchRowResult(
                        row_number=row_number,
                        asin=raw_asin.strip(),
                        title=raw_title.strip(),
                        status="FAILED",
                        code="SINGLE_INTAKE_FAILED",
                        message=str(exc),
                    )
                )

        success_count = sum(row.ok for row in results)

        return FastIntakeBatchResult(
            mode=normalized_mode,
            requested_count=len(results),
            success_count=success_count,
            failed_count=len(results) - success_count,
            rows=tuple(results),
        )
