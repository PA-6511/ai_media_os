from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from dataclasses import asdict, is_dataclass
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import EbookItem, StoreOffer
from app.db.repositories.import_repository import ImportRepository
from app.db.session import SessionLocal
from app.services.amazon_manual_offer_service import AmazonManualOfferService
from app.services.rakuten_kobo_manual_offer_resolver import (
    fetch_official_kobo_items_by_title,
)
from app.services.manual_store_offer_service import (
    ManualStoreOfferService,
)

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def env_file() -> dict[str, str]:
    path = Path("/etc/ai-media-os/credential.env")
    result = {}
    if not path.is_file():
        return result

    for line in path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def load_runtime_credentials() -> None:
    # Direct CLI execution does not inherit systemd EnvironmentFile.
    # Load the same credential.env without overriding explicitly-set env vars.
    for key, value in env_file().items():
        os.environ.setdefault(key, value)


def tracking_id(cli_value: str | None) -> str:
    if cli_value:
        return cli_value.strip()

    values = {**env_file(), **os.environ}

    for key in (
        "AMAZON_TRACKING_ID",
        "AMAZON_ASSOCIATE_TAG",
        "AMAZON_AFFILIATE_TAG",
        "AMAZON_TAG",
    ):
        value = str(values.get(key) or "").strip()
        if value:
            return value

    raise RuntimeError(
        "AMAZON_TRACKING_ID_NOT_FOUND: "
        "use --tracking-id"
    )


def to_jsonable(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if value is None or isinstance(
        value, (str, int, float, bool)
    ):
        return value
    return repr(value)



TRIAL_OR_SAMPLE_TERMS = (
    "試読",
    "試し読み",
    "立ち読み",
    "サンプル",
    "無料版",
    "preview",
    "sample",
)

SERIALIZED_TERMS = (
    "連載版",
    "連載",
    "単話",
    "分冊",
    "話売り",
)


def _kobo_text(value) -> str:
    return unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip()


def _kobo_title_key(value) -> str:
    text = _kobo_text(value)

    # Edition notes do not identify a different volume.
    text = re.sub(r"【[^】]*】", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"（[^）]*）", "", text)
    text = re.sub(r"\([^)]*\)", "", text)

    # Remove only a trailing volume notation.
    text = re.sub(
        r"(?:第\s*)?\d+\s*巻\s*$",
        "",
        text,
    )
    text = re.sub(
        r"[:：]\s*(?:第\s*)?\d+\s*$",
        "",
        text,
    )

    return re.sub(
        r"[\W_]+",
        "",
        text,
        flags=re.UNICODE,
    ).casefold()


def _kobo_volume(value) -> int | None:
    text = _kobo_text(value)

    for pattern in (
        r"(?:第\s*)?(\d+)\s*巻",
        r"[:：]\s*(?:第\s*)?(\d+)"
        r"(?=\s*(?:【|\[|（|\(|$))",
    ):
        matched = re.search(pattern, text)
        if matched:
            return int(matched.group(1))

    return None


def _kobo_date_key(value) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = _kobo_text(value)

    if not text:
        return None

    matched = re.search(
        r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        text,
    )

    if matched:
        return (
            f"{int(matched.group(1)):04d}-"
            f"{int(matched.group(2)):02d}-"
            f"{int(matched.group(3)):02d}"
        )

    matched = re.fullmatch(
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        text,
    )

    if matched:
        return (
            f"{int(matched.group(1)):04d}-"
            f"{int(matched.group(2)):02d}-"
            f"{int(matched.group(3)):02d}"
        )

    return None


def _kobo_value(candidate: dict, key: str) -> str:
    return str(candidate.get(key) or "").strip()


def select_high_confidence_kobo_candidate(
    *,
    title: str,
    item_type: str | None,
    volume_label: str | None,
    release_date,
    publisher_name: str | None,
    candidates,
):
    """Return exactly one safe Kobo candidate, otherwise require review."""
    requested_title_key = _kobo_title_key(title)
    requested_volume = (
        _kobo_volume(volume_label)
        or _kobo_volume(title)
    )
    requested_date = _kobo_date_key(release_date)
    requested_publisher_key = _kobo_title_key(
        publisher_name,
    )

    diagnostics = {
        "decision": "REVIEW_REQUIRED",
        "requested_volume": requested_volume,
        "rejected": [],
    }

    # The fast path creates tankobon items.  Do not infer an edition
    # for other item types or titles without a clear volume.
    if (
        str(item_type or "").strip().casefold()
        != "tankobon"
        or requested_volume is None
        or not requested_title_key
    ):
        diagnostics["reason"] = (
            "AUTO_SELECTION_REQUIRES_TANKOBON_VOLUME"
        )
        return None, diagnostics

    accepted = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        candidate_title = _kobo_value(candidate, "title")
        candidate_number = _kobo_value(
            candidate,
            "itemNumber",
        )
        candidate_text = _kobo_text(candidate_title).casefold()

        def reject(reason: str) -> None:
            diagnostics["rejected"].append({
                "item_number": candidate_number or None,
                "reason": reason,
            })

        if any(
            term in candidate_text
            for term in TRIAL_OR_SAMPLE_TERMS
        ):
            reject("TRIAL_OR_SAMPLE")
            continue

        if any(
            term in candidate_text
            for term in SERIALIZED_TERMS
        ):
            reject("SERIALIZED_OR_SPLIT_EDITION")
            continue

        if _kobo_title_key(candidate_title) != requested_title_key:
            reject("TITLE_MISMATCH")
            continue

        if _kobo_volume(candidate_title) != requested_volume:
            reject("VOLUME_MISMATCH")
            continue

        candidate_date = _kobo_date_key(
            candidate.get("salesDate"),
        )
        if (
            requested_date
            and candidate_date
            and candidate_date != requested_date
        ):
            reject("PUBLICATION_DATE_MISMATCH")
            continue

        candidate_publisher_key = _kobo_title_key(
            candidate.get("publisherName"),
        )
        if (
            requested_publisher_key
            and candidate_publisher_key
            and candidate_publisher_key
            != requested_publisher_key
        ):
            reject("PUBLISHER_MISMATCH")
            continue

        product_url = _kobo_value(candidate, "itemUrl")
        affiliate_url = _kobo_value(
            candidate,
            "affiliateUrl",
        )

        try:
            price = int(candidate.get("itemPrice"))
        except (
            TypeError,
            ValueError,
        ):
            price = 0

        if price <= 0:
            reject("PRICE_NOT_PAID_EDITION")
            continue

        if not re.fullmatch(
            r"(?:\d{13}|[0-9a-fA-F]{32})",
            candidate_number,
        ):
            reject("CANONICAL_ITEM_NUMBER_INVALID")
            continue

        if not product_url or not affiliate_url:
            reject("STORE_URL_MISSING")
            continue

        accepted.append(candidate)

    if len(accepted) != 1:
        diagnostics["reason"] = (
            "NO_HIGH_CONFIDENCE_CANDIDATE"
            if not accepted
            else "AMBIGUOUS_HIGH_CONFIDENCE_CANDIDATES"
        )
        diagnostics["accepted_item_numbers"] = [
            _kobo_value(candidate, "itemNumber")
            for candidate in accepted
        ]
        return None, diagnostics

    diagnostics["decision"] = "AUTO_SELECTED"
    diagnostics["item_number"] = _kobo_value(
        accepted[0],
        "itemNumber",
    )
    return accepted[0], diagnostics


def kobo_offer_kwargs(candidate: dict) -> dict:
    return {
        "store_name": "rakuten_kobo",
        "product_url": _kobo_value(candidate, "itemUrl"),
        "affiliate_url": _kobo_value(
            candidate,
            "affiliateUrl",
        ),
        "price": str(int(candidate["itemPrice"])),
        "currency": "JPY",
        "availability_status": "FOUND",
        "observed_at": datetime.now(timezone.utc),
        "operator": "asin_fast_intake",
        "canonical_store_item_id": _kobo_value(
            candidate,
            "itemNumber",
        ),
    }



def find_by_asin(session, asin: str):
    stmt = (
        select(EbookItem)
        .join(StoreOffer)
        .where(
            StoreOffer.store_name == "amazon",
            StoreOffer.store_item_id == asin,
        )
        .limit(1)
    )
    return session.scalar(stmt)


def find_by_title(session, title: str):
    return session.scalar(
        select(EbookItem)
        .where(EbookItem.title == title)
        .order_by(EbookItem.created_at.desc())
        .limit(1)
    )


def dmm_discover(session, ebook_item_id: str):
    try:
        from app.services.dmm_initial_discovery_service import (
            DmmInitialDiscoveryService,
        )
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "reason": repr(exc),
        }

    try:
        try:
            service = DmmInitialDiscoveryService(session)
        except TypeError:
            service = DmmInitialDiscoveryService()

        for method_name in (
            "discover",
            "discover_item",
            "run",
            "execute",
        ):
            method = getattr(
                service,
                method_name,
                None,
            )
            if not callable(method):
                continue

            sig = inspect.signature(method)
            kwargs = {}

            for name, parameter in sig.parameters.items():
                if name in {
                    "ebook_item_id",
                    "item_id",
                }:
                    kwargs[name] = ebook_item_id
                elif parameter.default is inspect.Parameter.empty:
                    break
            else:
                result = method(**kwargs)
                return {
                    "status": "CALLED",
                    "method": method_name,
                    "result": to_jsonable(result),
                }

        return {
            "status": "UNAVAILABLE",
            "reason": "NO_COMPATIBLE_PUBLIC_METHOD",
        }

    except Exception as exc:
        return {
            "status": "FAILED",
            "reason": repr(exc),
        }


def main() -> int:
    load_runtime_credentials()

    parser = argparse.ArgumentParser(
        description=(
            "Fast ASIN intake -> Amazon -> Kobo -> DMM"
        )
    )
    parser.add_argument("asin")
    parser.add_argument("--title")
    parser.add_argument("--tracking-id")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    asin = args.asin.strip().upper()

    if not ASIN_RE.fullmatch(asin):
        raise SystemExit(
            "ASIN_INVALID: exactly 10 alphanumeric characters required"
        )

    with SessionLocal() as session:
        item = find_by_asin(session, asin)

        title = str(args.title or "").strip()

        if item is not None and not title:
            title = item.title

        if not title:
            raise SystemExit(
                "TITLE_REQUIRED_FOR_NEW_ASIN: "
                "use --title until Amazon metadata API is connected"
            )

        if item is None:
            item = find_by_title(
                session,
                title,
            )

        created = False

        if item is None:
            result = ImportRepository(
                session
            ).import_row({
                "source_name": "amazon_asin_fast",
                "source_item_id": asin,
                "title": title,
                "item_type": "tankobon",
            })

            item = session.get(
                EbookItem,
                result.ebook_item_id,
            )
            created = bool(result.created)

        assert item is not None

        # Keep scalar identity before DRY_RUN rollback expires/removes
        # the newly-created ORM instance.
        ebook_item_id = str(item.id)

        amazon_status = {
            "status": "DRY_RUN",
        }

        if args.execute:
            tag = tracking_id(
                args.tracking_id
            )

            amazon = AmazonManualOfferService(
                session
            ).save(
                ebook_item_id=ebook_item_id,
                asin=asin,
                tracking_id=tag,
            )

            amazon_status = {
                "status": "SAVED",
                "asin": amazon.asin,
                "unchanged": amazon.unchanged,
            }

        existing_kobo = session.scalar(
            select(StoreOffer)
            .where(
                StoreOffer.ebook_item_id == ebook_item_id,
                StoreOffer.store_name == "rakuten_kobo",
            )
            .order_by(
                StoreOffer.last_checked_at.desc(),
                StoreOffer.id,
            )
            .limit(1)
        )

        if existing_kobo is not None:
            kobo_status = {
                "status": "ALREADY_SAVED",
                "offer_id": existing_kobo.id,
                "store_item_id": existing_kobo.store_item_id,
            }
        else:
            try:
                kobo_items = (
                    fetch_official_kobo_items_by_title(
                        title,
                        hits=5,
                    )
                )

                selected_kobo, kobo_selection = (
                    select_high_confidence_kobo_candidate(
                        title=item.title,
                        item_type=item.item_type,
                        volume_label=item.volume_label,
                        release_date=item.release_date,
                        publisher_name=item.publisher_name,
                        candidates=kobo_items,
                    )
                )

                kobo_status = {
                    "status": (
                        "AUTO_SELECTED_DRY_RUN"
                        if selected_kobo is not None
                        and not args.execute
                        else (
                            "NOT_FOUND"
                            if not kobo_items
                            else "REVIEW_REQUIRED"
                        )
                    ),
                    "count": len(kobo_items),
                    "selection": kobo_selection,
                    "candidates": [
                        to_jsonable(x)
                        for x in kobo_items[:5]
                    ],
                }

                if selected_kobo is not None:
                    kobo_status["selected"] = to_jsonable(
                        selected_kobo
                    )

                    if args.execute:
                        saved_kobo = (
                            ManualStoreOfferService(session)
                            .create_offer(
                                ebook_item_id=ebook_item_id,
                                **kobo_offer_kwargs(selected_kobo),
                            )
                        )
                        kobo_status.update({
                            "status": "SAVED",
                            "item_number": _kobo_value(
                                selected_kobo,
                                "itemNumber",
                            ),
                            "offer_id": saved_kobo.offer_id,
                            "idempotent": saved_kobo.idempotent,
                        })

            except Exception as exc:
                kobo_status = {
                    "status": "FAILED",
                    "reason": repr(exc),
                }

        dmm_status = (
            dmm_discover(
                session,
                ebook_item_id,
            )
            if args.execute
            else {
                "status": "SKIPPED_DRY_RUN"
            }
        )

        if args.execute:
            session.commit()
        else:
            session.rollback()

        print(json.dumps(
            {
                "status": "PASS",
                "mode": (
                    "EXECUTE"
                    if args.execute
                    else "DRY_RUN"
                ),
                "ebook_item_id": ebook_item_id,
                "created": created,
                "asin": asin,
                "title": title,
                "amazon": amazon_status,
                "rakuten_kobo": kobo_status,
                "dmm": dmm_status,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
