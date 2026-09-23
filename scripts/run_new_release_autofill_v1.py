from __future__ import annotations

import argparse
import calendar
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
import os
from pathlib import Path
import subprocess
import time
import sys
from typing import Any, Callable
from zoneinfo import ZoneInfo

from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.models import EbookItem
from app.db.session import SessionLocal
from app.services.ebook_metadata_autofill_service import (
    EbookMetadataAutofillService,
)


JST = ZoneInfo("Asia/Tokyo")


def current_month() -> str:
    return datetime.now(JST).strftime("%Y-%m")


def month_bounds(value: str) -> tuple[date, date]:
    try:
        year_text, month_text = value.split("-", 1)
        year = int(year_text)
        month = int(month_text)
        first = date(year, month, 1)
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            "month must be YYYY-MM"
        ) from exc

    last = date(
        year,
        month,
        calendar.monthrange(year, month)[1],
    )
    return first, last


def select_month_item_ids(
    *,
    start_date: date,
    end_date: date,
    max_items: int,
) -> list[str]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(EbookItem.id)
            .where(
                EbookItem.source_name
                == "new_release_multistore",
                EbookItem.is_excluded.is_(False),
                EbookItem.release_date >= start_date,
                EbookItem.release_date <= end_date,
            )
            .order_by(
                (
                    EbookItem.release_date
                    < datetime.now(JST).date()
                ).asc(),
                EbookItem.release_date.asc(),
                EbookItem.id.asc(),
            )
            .limit(max_items)
        ).all()

        session.rollback()

    return [str(value) for value in rows]


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]

    if isinstance(value, (str, int, float, bool)):
        return value

    if value is None:
        return None

    return str(value)


def _safe_component(
    fn: Callable[[], Any],
) -> dict[str, Any]:
    try:
        return {
            "status": "OK",
            "detail": _jsonable(fn()),
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
        }



def run_kobo(
    *,
    execute: bool,
    start_date: date,
    end_date: date,
    max_items: int,
    pacing_seconds: float,
    item_ids: list[str] | None = None,
) -> Any:
    from app.db.models import StoreOffer
    from app.services.monthly_comic_release_sync import (
        _kobo_enrich,
    )
    from app.services.rakuten_kobo_normal_e_orchestrator import (
        RakutenKoboNormalEOrchestrator,
    )

    targets = (
        list(item_ids)
        if item_ids is not None
        else select_month_item_ids(
            start_date=start_date,
            end_date=end_date,
            max_items=max_items,
        )
    )

    results: list[dict[str, Any]] = []

    for index, item_id in enumerate(targets):
        if not execute:
            results.append(
                {
                    "ebook_item_id": item_id,
                    "status": "SKIPPED_DRY_RUN",
                }
            )
            continue

        # Existing offer:
        # use the existing item-scoped Normal-E path
        # for identity / price / affiliate completion.
        with SessionLocal() as session:
            existing = session.scalar(
                select(StoreOffer).where(
                    StoreOffer.ebook_item_id
                    == item_id,
                    StoreOffer.store_name
                    == "rakuten_kobo",
                ).limit(1)
            )

            if existing is not None:
                try:
                    detail = (
                        RakutenKoboNormalEOrchestrator(
                            session
                        ).run(item_id)
                    )

                    session.commit()

                    results.append(
                        {
                            "ebook_item_id":
                                item_id,
                            "status":
                                "NORMAL_E",
                            "detail":
                                _jsonable(detail),
                        }
                    )

                except Exception as exc:
                    session.rollback()

                    results.append(
                        {
                            "ebook_item_id":
                                item_id,
                            "status":
                                "FAILED",
                            "reason_code":
                                (
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                        }
                    )

            else:
                session.rollback()

                # Missing offer:
                # reuse existing high-confidence
                # item-scoped creation path.
                results.append(
                    _kobo_enrich(
                        item_id,
                        execute=True,
                    )
                )

        if (
            pacing_seconds > 0
            and index + 1 < len(targets)
        ):
            time.sleep(pacing_seconds)

    return {
        "selected_count": len(targets),
        "results": results,
    }




def run_dmm(
    *,
    execute: bool,
    start_date: date,
    end_date: date,
    max_items: int,
    pacing_seconds: float,
    item_ids: list[str] | None = None,
) -> Any:
    from app.services.monthly_comic_release_sync import (
        _dmm_enrich,
    )

    targets = (
        list(item_ids)
        if item_ids is not None
        else select_month_item_ids(
            start_date=start_date,
            end_date=end_date,
            max_items=max_items,
        )
    )

    results: list[dict[str, Any]] = []

    for index, item_id in enumerate(targets):
        results.append(
            _dmm_enrich(
                item_id,
                execute=execute,
            )
        )

        if (
            pacing_seconds > 0
            and index + 1 < len(targets)
        ):
            time.sleep(pacing_seconds)

    return {
        "selected_count": len(targets),
        "results": results,
    }




def run_amazon(
    *,
    execute: bool,
    month: str,
    max_items: int,
    request_interval_seconds: float,
    item_ids: list[str] | None = None,
) -> dict[str, Any]:
    script = (
        REPO_ROOT
        / "scripts"
        / "database"
        / "run_amazon_creators_kindle_sync.py"
    )

    if item_ids is None:
        start_date, end_date = (
            month_bounds(month)
        )

        targets = select_month_item_ids(
            start_date=start_date,
            end_date=end_date,
            max_items=max_items,
        )
    else:
        targets = list(item_ids)

    if not targets:
        return {
            "provider_status": "PASS",
            "selected_count": 0,
            "database_write_performed": False,
            "status_counts": {},
            "result_path": "",
        }

    command = [
        sys.executable,
        str(script),
        "--month",
        month,
        "--request-interval-seconds",
        str(request_interval_seconds),
        "--run-label",
        "new_release_autofill_v1",
    ]

    for item_id in targets:
        command.extend(
            [
                "--item-id",
                item_id,
            ]
        )

    if execute:
        command.append("--execute")

    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = str(
        completed.stdout or ""
    ).strip()

    summary: dict[str, Any] = {}

    # Existing Amazon runner emits one final
    # JSON summary line.
    for line in reversed(
        stdout.splitlines()
    ):
        line = line.strip()

        if not line:
            continue

        try:
            value = json.loads(line)
        except Exception:
            continue

        if isinstance(value, dict):
            summary = value
            break

    provider_status = str(
        summary.get("status") or ""
    ).strip()

    result = {
        "provider_status":
            provider_status,
        "returncode":
            completed.returncode,
        "selected_count":
            len(targets),
        "database_write_performed":
            bool(
                summary.get(
                    "database_write_performed"
                )
            ),
        "status_counts":
            summary.get(
                "status_counts"
            )
            or {},
        "result_path":
            str(
                summary.get(
                    "result_path"
                )
                or ""
            ),
    }

    if provider_status == "BLOCKED_CREDENTIALS":
        return result

    if completed.returncode != 0:
        raise RuntimeError(
            "AMAZON_CREATORS_RUN_FAILED:"
            + (
                provider_status
                or str(
                    completed.returncode
                )
            )
        )

    return result



def _preview_apply_possible(
    preview: Any,
) -> bool:
    value = getattr(
        preview,
        "apply_possible",
        False,
    )

    if callable(value):
        value = value()

    return bool(value)


def _preview_fingerprint(
    preview: Any,
) -> str:
    for name in (
        "fingerprint",
        "preview_fingerprint",
    ):
        value = getattr(
            preview,
            name,
            None,
        )
        if value:
            return str(value)

    for name, value in vars(preview).items():
        if (
            "fingerprint" in name.lower()
            and value
        ):
            return str(value)

    raise RuntimeError(
        "metadata_preview_fingerprint_missing"
    )


def _run_rakuten_detail_fallback(
    *,
    ebook_item_id: str,
    execute: bool,
) -> dict[str, Any]:
    from app.services.monthly_comic_release_sync import (
        ComicReleaseRecord,
        enrich_rakuten_product_metadata,
    )

    result: dict[str, Any] = {
        "ebook_item_id": ebook_item_id,
        "status": "NOOP",
        "proposed_fields": [],
        "applied_fields": [],
    }

    with SessionLocal() as session:
        item = session.get(
            EbookItem,
            ebook_item_id,
        )

        if item is None:
            result["status"] = "ITEM_NOT_FOUND"
            return result

        source_url = str(
            item.source_url or ""
        ).strip()

        if "/rb/" not in source_url:
            result["status"] = "SKIPPED_NO_RAKUTEN_DETAIL"
            session.rollback()
            return result

        target_fields = (
            "isbn",
            "author_name",
            "publisher_name",
            "series_name",
            "volume_label",
        )

        missing = [
            field
            for field in target_fields
            if not str(
                getattr(item, field, None) or ""
            ).strip()
        ]

        if not missing:
            result["status"] = "NOOP_COMPLETE"
            session.rollback()
            return result

        record = ComicReleaseRecord(
            source_item_id=str(
                item.source_item_id
                or item.id
            ),
            title=str(item.title or ""),
            release_date=item.release_date,
            source_url=source_url,
            author_name=(
                str(item.author_name).strip()
                if item.author_name
                else None
            ),
            publisher_name=(
                str(item.publisher_name).strip()
                if item.publisher_name
                else None
            ),
            imprint_name=None,
            series_name=(
                str(item.series_name).strip()
                if item.series_name
                else None
            ),
            volume_label=(
                str(item.volume_label).strip()
                if item.volume_label
                else None
            ),
            isbn=(
                str(item.isbn).strip()
                if item.isbn
                else None
            ),
            raw={
                "parser":
                    "new_release_autofill_v1",
            },
        )

        session.rollback()

    try:
        enriched_rows = (
            enrich_rakuten_product_metadata(
                [record],
                detail_limit=1,
                detail_workers=1,
                cache_dir=(
                    REPO_ROOT
                    / "exchange"
                    / "cache"
                    / "new_release_autofill_v1"
                ),
                cache_ttl_hours=168,
            )
        )
    except Exception as exc:
        result["status"] = "ERROR"
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )
        return result

    if not enriched_rows:
        result["status"] = "NO_DETAIL_RESULT"
        return result

    enriched = enriched_rows[0]

    proposed: dict[str, str] = {}

    for field in (
        "isbn",
        "author_name",
        "publisher_name",
        "series_name",
        "volume_label",
    ):
        before = str(
            getattr(record, field, None) or ""
        ).strip()

        candidate = str(
            getattr(enriched, field, None) or ""
        ).strip()

        if not before and candidate:
            proposed[field] = candidate

    result["proposed_fields"] = sorted(
        proposed
    )

    if not proposed:
        result["status"] = "NO_DETAIL_CHANGE"
        return result

    if not execute:
        result["status"] = "DRY_RUN_READY"
        return result

    with SessionLocal() as session:
        item = session.get(
            EbookItem,
            ebook_item_id,
        )

        if item is None:
            result["status"] = "ITEM_NOT_FOUND"
            session.rollback()
            return result

        applied = []

        for field, candidate in proposed.items():
            current = str(
                getattr(item, field, None) or ""
            ).strip()

            # Blank-only is authoritative.
            if current:
                continue

            setattr(
                item,
                field,
                candidate,
            )
            applied.append(field)

        if applied:
            session.commit()
            result["status"] = "APPLIED"
        else:
            session.rollback()
            result["status"] = "NOOP_RACE_PROTECTED"

        result["applied_fields"] = sorted(
            applied
        )

    return result


def run_metadata(
    *,
    execute: bool,
    item_ids: list[str],
) -> dict[str, Any]:
    result = {
        "selected_count": len(item_ids),
        "previewed_count": 0,
        "apply_possible_count": 0,
        "applied_item_count": 0,
        "applied_field_count": 0,
        "failed_count": 0,
        "items": [],
    }

    for item_id in item_ids:
        detail_fallback = (
            _run_rakuten_detail_fallback(
                ebook_item_id=item_id,
                execute=execute,
            )
        )

        with SessionLocal() as session:
            service = EbookMetadataAutofillService(
                session
            )

            try:
                preview = service.preview(
                    item_id
                )
                result[
                    "previewed_count"
                ] += 1

                possible = (
                    _preview_apply_possible(
                        preview
                    )
                )

                item_result = {
                    "ebook_item_id": item_id,
                    "apply_possible": possible,
                    "applied_fields": [],
                    "rakuten_detail": (
                        detail_fallback
                    ),
                }

                if possible:
                    result[
                        "apply_possible_count"
                    ] += 1

                if execute and possible:
                    fingerprint = (
                        _preview_fingerprint(
                            preview
                        )
                    )

                    applied = service.apply(
                        ebook_item_id=item_id,
                        confirmed_fingerprint=(
                            fingerprint
                        ),
                        changed_by=(
                            "system:"
                            "new_release_autofill_v1"
                        ),
                    )

                    applied_fields = [
                        str(
                            getattr(
                                field,
                                "field_name",
                                "",
                            )
                        )
                        for field
                        in getattr(
                            applied,
                            "field_results",
                            (),
                        )
                        if str(
                            getattr(
                                field,
                                "status",
                                "",
                            )
                        ).upper()
                        == "APPLIED"
                    ]

                    session.commit()

                    item_result[
                        "applied_fields"
                    ] = applied_fields

                    if applied_fields:
                        result[
                            "applied_item_count"
                        ] += 1
                        result[
                            "applied_field_count"
                        ] += len(
                            applied_fields
                        )
                else:
                    session.rollback()

                result["items"].append(
                    item_result
                )

            except Exception as exc:
                session.rollback()
                result[
                    "failed_count"
                ] += 1
                result["items"].append(
                    {
                        "ebook_item_id":
                            item_id,
                        "status": "ERROR",
                        "error": (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    }
                )

    return result


def _component_item_ids(
    component: dict[str, Any],
) -> list[str]:
    detail = component.get("detail")

    if not isinstance(detail, dict):
        return []

    results = detail.get("results")

    if not isinstance(results, list):
        return []

    item_ids: list[str] = []

    for row in results:
        if not isinstance(row, dict):
            continue

        value = str(
            row.get("ebook_item_id") or ""
        ).strip()

        if value:
            item_ids.append(value)

    return item_ids


def run_autofill(
    args: argparse.Namespace,
) -> dict[str, Any]:
    target_date_text = str(
        getattr(
            args,
            "target_date",
            "",
        )
        or ""
    ).strip()

    if target_date_text:
        try:
            target_date = date.fromisoformat(
                target_date_text
            )
        except ValueError as exc:
            raise ValueError(
                "target_date must be YYYY-MM-DD"
            ) from exc

        start_date = target_date
        end_date = target_date
        target_month = target_date.strftime(
            "%Y-%m"
        )

    else:
        start_date, end_date = (
            month_bounds(args.month)
        )
        target_month = args.month

    item_ids = select_month_item_ids(
        start_date=start_date,
        end_date=end_date,
        max_items=args.max_items,
    )

    components: dict[str, Any] = {}

    components["kobo"] = _safe_component(
        lambda: run_kobo(
            execute=args.execute,
            start_date=start_date,
            end_date=end_date,
            max_items=args.max_items,
            pacing_seconds=(
                args.kobo_pacing_seconds
            ),
            item_ids=item_ids,
        )
    )

    components["dmm"] = _safe_component(
        lambda: run_dmm(
            execute=args.execute,
            start_date=start_date,
            end_date=end_date,
            max_items=args.max_items,
            pacing_seconds=(
                args.dmm_pacing_seconds
            ),
            item_ids=item_ids,
        )
    )

    if getattr(
        args,
        "skip_amazon",
        False,
    ):
        components["amazon"] = {
            "status": "SKIPPED",
            "detail": {
                "reason": "skip_amazon",
            },
        }
    else:
        components["amazon"] = _safe_component(
            lambda: run_amazon(
                execute=args.execute,
                month=target_month,
                max_items=args.max_items,
                request_interval_seconds=(
                    args
                    .amazon_request_interval_seconds
                ),
                item_ids=item_ids,
            )
        )

        amazon_detail = components[
            "amazon"
        ].get("detail")

        if (
            components["amazon"].get("status")
            == "OK"
            and isinstance(
                amazon_detail,
                dict,
            )
            and amazon_detail.get(
                "provider_status"
            )
            == "BLOCKED_CREDENTIALS"
        ):
            components["amazon"][
                "status"
            ] = "BLOCKED"

    # Store candidates first.
    # These are the records most likely to have
    # gained new verified evidence during this run.
    metadata_item_ids = list(
        dict.fromkeys(
            [
                *_component_item_ids(
                    components["kobo"]
                ),
                *_component_item_ids(
                    components["dmm"]
                ),
                *item_ids,
            ]
        )
    )

    components["metadata"] = _safe_component(
        lambda: run_metadata(
            execute=args.execute,
            item_ids=metadata_item_ids,
        )
    )

    has_error = any(
        component.get("status")
        == "ERROR"
        for component in components.values()
    )

    has_blocked = any(
        component.get("status")
        == "BLOCKED"
        for component in components.values()
    )

    if has_error:
        status = "PARTIAL"
    elif has_blocked:
        status = "PASS_WITH_BLOCKED"
    else:
        status = "PASS"

    return {
        "status": status,
        "mode": (
            "EXECUTE"
            if args.execute
            else "DRY_RUN"
        ),
        "month": target_month,
        "target_date": (
            target_date_text
            or None
        ),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "selected_count": len(item_ids),
        "selected_item_ids": item_ids,
        "metadata_target_count": len(
            metadata_item_ids
        ),
        "metadata_target_item_ids": (
            metadata_item_ids
        ),
        "components": components,
        "notes": [
            (
                "One component failure does not "
                "stop remaining enrichment."
            ),
            (
                "Store candidates are included "
                "in metadata autofill targets."
            ),
            (
                "Existing non-empty metadata "
                "protection remains authoritative."
            ),
            (
                "No new approval gate is introduced."
            ),
        ],
    }


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "NR-A1 v1: reuse existing metadata "
            "and multistore enrichment paths."
        )
    )

    parser.add_argument(
        "--month",
        default=current_month(),
        help="Target release month YYYY-MM.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--target-date",
        default="",
        help=(
            "Restrict processing to one release date "
            "YYYY-MM-DD."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Perform existing bounded DB writes. "
            "Without this flag, run in dry-run mode."
        ),
    )
    parser.add_argument(
        "--skip-amazon",
        action="store_true",
        help=(
            "Skip Amazon Creators enrichment "
            "without blocking Kobo/DMM/metadata."
        ),
    )

    parser.add_argument(
        "--kobo-pacing-seconds",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--dmm-pacing-seconds",
        type=float,
        default=5.0,
    )
    parser.add_argument(
        "--amazon-request-interval-seconds",
        type=float,
        default=1.25,
    )

    args = parser.parse_args(argv)

    if not 1 <= args.max_items <= 200:
        parser.error(
            "--max-items must be between 1 and 200"
        )

    # Validate early.
    month_bounds(args.month)

    if args.target_date:
        try:
            date.fromisoformat(
                args.target_date
            )
        except ValueError:
            parser.error(
                "--target-date must be YYYY-MM-DD"
            )

    return args


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    payload = run_autofill(args)

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    # PARTIAL is intentionally operationally successful:
    # one store failure must not block other enrichment.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
