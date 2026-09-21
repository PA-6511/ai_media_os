from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Mapping
from typing import Any
import unicodedata

from app.services.ebook_fast_intake_batch_service import (
    FastIntakeBatchError,
    normalize_asin,
    normalize_title,
)


VALID_MODES = frozenset({
    "dry_run",
    "execute",
})

STORE_ALIASES = {
    "amazon": "amazon",
    "kindle": "amazon",
    "amazon_kindle": "amazon",
    "kobo": "rakuten_kobo",
    "rakuten": "rakuten_kobo",
    "rakuten_kobo": "rakuten_kobo",
    "dmm": "dmm",
}

SUPPORTED_STORES = frozenset({
    "amazon",
    "rakuten_kobo",
    "dmm",
})


class MultistoreFastIntakeError(
    ValueError
):
    def __init__(
        self,
        code: str,
        *,
        store_name: str = "",
        diagnostic: str = "",
    ) -> None:
        super().__init__(code)

        self.code = code
        self.store_name = store_name
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class MultistoreFastIntakeInput:
    store_name: str
    product_input: str
    title: str


@dataclass(frozen=True)
class MultistoreFastIntakeResult:
    store_name: str
    product_input: str
    title: str
    mode: str
    payload: Mapping[str, Any]


StoreIntakeCallable = Callable[
    [
        str,
        str,
        str,
    ],
    Mapping[str, Any] | None,
]


def normalize_store_name(
    value: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip().casefold()

    store_name = STORE_ALIASES.get(
        normalized
    )

    if (
        store_name is None
        or store_name not in SUPPORTED_STORES
    ):
        raise MultistoreFastIntakeError(
            "STORE_UNSUPPORTED"
        )

    return store_name


def normalize_product_input(
    store_name: str,
    value: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip()

    if not normalized:
        raise MultistoreFastIntakeError(
            "PRODUCT_INPUT_REQUIRED",
            store_name=store_name,
        )

    if store_name == "amazon":
        try:
            return normalize_asin(
                normalized
            )
        except FastIntakeBatchError as exc:
            raise MultistoreFastIntakeError(
                exc.code,
                store_name=store_name,
            ) from exc

    return normalized


def normalize_multistore_title(
    value: str,
) -> str:
    try:
        return normalize_title(
            value
        )
    except FastIntakeBatchError as exc:
        raise MultistoreFastIntakeError(
            exc.code
        ) from exc


class EbookMultistoreFastIntakeService:
    def __init__(
        self,
        *,
        amazon_intake: StoreIntakeCallable,
        kobo_intake: StoreIntakeCallable,
        dmm_intake: StoreIntakeCallable,
    ) -> None:
        adapters = {
            "amazon": amazon_intake,
            "rakuten_kobo": kobo_intake,
            "dmm": dmm_intake,
        }

        for (
            store_name,
            adapter,
        ) in adapters.items():
            if not callable(adapter):
                raise TypeError(
                    f"{store_name}_intake "
                    "must be callable"
                )

        self._adapters = adapters

    def run_one(
        self,
        row: MultistoreFastIntakeInput,
        *,
        mode: str = "dry_run",
    ) -> MultistoreFastIntakeResult:
        normalized_mode = (
            str(mode or "").strip()
        )

        if (
            normalized_mode
            not in VALID_MODES
        ):
            raise MultistoreFastIntakeError(
                "MODE_INVALID"
            )

        store_name = normalize_store_name(
            row.store_name
        )

        product_input = (
            normalize_product_input(
                store_name,
                row.product_input,
            )
        )

        title = normalize_multistore_title(
            row.title
        )

        adapter = self._adapters[
            store_name
        ]

        try:
            payload = adapter(
                product_input,
                title,
                normalized_mode,
            )
        except MultistoreFastIntakeError:
            raise
        except Exception as exc:
            raise MultistoreFastIntakeError(
                "STORE_INTAKE_FAILED",
                store_name=store_name,
                diagnostic=str(exc),
            ) from exc

        if payload is None:
            safe_payload: Mapping[
                str,
                Any,
            ] = {}
        elif isinstance(
            payload,
            Mapping,
        ):
            safe_payload = payload
        else:
            raise MultistoreFastIntakeError(
                "STORE_INTAKE_INVALID_RESULT",
                store_name=store_name,
            )

        return MultistoreFastIntakeResult(
            store_name=store_name,
            product_input=product_input,
            title=title,
            mode=normalized_mode,
            payload=safe_payload,
        )
