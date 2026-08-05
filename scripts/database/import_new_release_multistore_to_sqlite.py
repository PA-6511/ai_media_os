from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
repository_root_text = str(REPOSITORY_ROOT)
if repository_root_text not in sys.path:
    sys.path.insert(0, repository_root_text)


from app.adapters.new_release_multistore_adapter import (  # noqa: E402
    adapt_multistore_csv,
    map_item_type,
)
from app.db.config import DATABASE_BACKEND  # noqa: E402
from app.db.repositories.import_repository import ImportRepository  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.csv_import_service import CsvImportService  # noqa: E402


EXPECTED_SOURCE_SCHEMA_ID = "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2"
EXPECTED_INPUT_CONTRACT_ID = "FRESH_NEW_RELEASE_COMIC_MULTISTORE_INPUT_V2"
SAFE_BATCH_ID = re.compile(r"^[A-Za-z0-9._-]+$")
STORE_NAMES = {
    "rakuten_kobo": "rakuten_kobo",
    "dmm_books": "dmm",
    "amazon_kindle": "amazon",
}
CANONICAL_FIELDNAMES = (
    "source_name",
    "source_item_id",
    "title",
    "isbn",
    "normalized_title",
    "volume_label",
    "author_name",
    "author",
    "publisher_name",
    "publisher",
    "series_name",
    "release_date",
    "item_type",
    "wordpress_status",
    "store_name",
    "store_item_id",
    "product_url",
    "affiliate_url",
    "price",
    "currency",
    "discount_rate",
    "point_rate",
    "source_row_sha256",
    "verified_at",
    "verification_method",
)


class ManifestValidationError(ValueError):
    """Raised before database access when ready-artifact evidence is unsafe."""


@dataclass(frozen=True)
class ReadyBatch:
    repository_root: Path
    batch_dir: Path
    manifest_path: Path
    blocked_path: Path
    result_log_path: Path
    batch_id: str
    item_paths: tuple[Path, ...]
    ready_payloads: tuple[dict[str, Any], ...]
    ready_input_count: int
    blocked_count: int
    warning_count: int
    blocked_rows: tuple[dict[str, Any], ...]
    blocked_reasons: tuple[dict[str, Any], ...]


@dataclass
class ReadyImportSummary:
    ready_input_count: int
    blocked_count: int
    warning_count: int
    processed: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    offer_created: int = 0
    offer_updated: int = 0
    offer_unchanged: int = 0
    failed: int = 0
    database_write_performed: bool = False
    external_network_performed: bool = False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import prevalidated ready artifacts from a new-release "
            "multistore batch into the ebook operational database."
        )
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        type=Path,
        help=(
            "Legacy unvalidated CSV input (DRY_RUN only). "
            "Use --manifest or --batch-dir for --execute."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Prevalidated batch manifest.json",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help="Prevalidated batch directory containing manifest.json",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Commit database changes. Default is DRY_RUN.",
    )
    parser.add_argument(
        "--keep-adapted-csv",
        type=Path,
        default=None,
        help="Optional new path where canonical rows are saved.",
    )
    args = parser.parse_args(argv)
    selected_inputs = sum(
        value is not None
        for value in (args.input_csv, args.manifest, args.batch_dir)
    )
    if selected_inputs != 1:
        parser.error(
            "select exactly one input: input_csv, --manifest, or --batch-dir"
        )
    return args


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ManifestValidationError(f"{label} must be a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{label} must contain a JSON object: {path}")
    return value


def _require_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ManifestValidationError(f"{field} must be a non-negative integer")
    return value


def _repository_root_from_batch_dir(batch_dir: Path) -> Path:
    if (
        batch_dir.parent.name != "batches"
        or batch_dir.parent.parent.name != "new_release"
        or batch_dir.parent.parent.parent.name != "inputs"
        or batch_dir.parent.parent.parent.parent.name != "exchange"
    ):
        raise ManifestValidationError(
            "batch directory must be below "
            "exchange/inputs/new_release/batches"
        )
    return batch_dir.parent.parent.parent.parent.parent


def _recorded_path(
    value: Any,
    *,
    field: str,
    repository_root: Path,
    expected_path: Path,
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} is missing")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    if candidate.is_symlink():
        raise ManifestValidationError(f"{field} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ManifestValidationError(f"{field} does not exist: {candidate}") from exc
    if resolved != expected_path.resolve(strict=False):
        raise ManifestValidationError(
            f"{field} does not match the expected artifact path"
        )
    return resolved


def _validate_safety(value: Any, *, label: str) -> None:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{label}.safety is missing")
    required_false = (
        "external_network_performed",
        "wordpress_write_performed",
        "wordpress_publish_performed",
    )
    for field in required_false:
        if value.get(field) is not False:
            raise ManifestValidationError(f"{label}.safety.{field} must be false")
    if value.get("input_status_fixed_to_draft") is not True:
        raise ManifestValidationError(
            f"{label}.safety.input_status_fixed_to_draft must be true"
        )


def _validate_ready_payload(
    payload: dict[str, Any],
    *,
    path: Path,
    batch_id: str,
) -> None:
    if payload.get("source_schema_id") != EXPECTED_SOURCE_SCHEMA_ID:
        raise ManifestValidationError(f"ready item has invalid source_schema_id: {path}")
    if payload.get("input_contract_id") != EXPECTED_INPUT_CONTRACT_ID:
        raise ManifestValidationError(f"ready item has invalid input_contract_id: {path}")
    if payload.get("batch_id") != batch_id:
        raise ManifestValidationError(f"ready item batch_id mismatch: {path}")
    content_item_id = payload.get("content_item_id")
    if not isinstance(content_item_id, str) or not content_item_id:
        raise ManifestValidationError(f"ready item content_item_id is missing: {path}")
    if path.name != f"{content_item_id}.input.json":
        raise ManifestValidationError(f"ready item filename does not match content_item_id: {path}")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        raise ManifestValidationError(f"ready item title is missing: {path}")
    wordpress = payload.get("wordpress")
    if not isinstance(wordpress, dict) or wordpress.get("status") != "draft":
        raise ManifestValidationError(f"ready item wordpress status must be draft: {path}")
    if wordpress.get("write_allowed") is not False:
        raise ManifestValidationError(f"ready item wordpress write must be disabled: {path}")
    if wordpress.get("publish_allowed") is not False:
        raise ManifestValidationError(f"ready item wordpress publish must be disabled: {path}")
    _validate_safety(payload.get("safety"), label=f"ready item {path.name}")
    stores = payload.get("store_navigation")
    if not isinstance(stores, list) or not stores:
        raise ManifestValidationError(f"ready item store_navigation is missing: {path}")
    seen_stores: set[str] = set()
    for store in stores:
        if not isinstance(store, dict):
            raise ManifestValidationError(f"ready item store entry is invalid: {path}")
        key = store.get("key")
        url = store.get("url")
        if key not in STORE_NAMES:
            raise ManifestValidationError(f"ready item store key is unsupported: {path}")
        if key in seen_stores:
            raise ManifestValidationError(f"ready item contains a duplicate store: {path}")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ManifestValidationError(f"ready item store URL is invalid: {path}")
        seen_stores.add(key)


def _blocked_reason_summary(
    blocked_rows: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    counter: Counter[tuple[str, str, str]] = Counter()
    for row in blocked_rows:
        error = row.get("error") if isinstance(row, dict) else None
        if not isinstance(error, dict):
            raise ManifestValidationError("blocked row error evidence is invalid")
        code = error.get("code")
        message = error.get("message")
        field = error.get("field") or ""
        if not isinstance(code, str) or not isinstance(message, str):
            raise ManifestValidationError("blocked row reason is incomplete")
        counter[(code, message, str(field))] += 1
    return tuple(
        {
            "code": code,
            "message": message,
            "field": field or None,
            "count": count,
        }
        for (code, message, field), count in sorted(counter.items())
    )


def load_ready_batch(manifest_path: Path) -> ReadyBatch:
    if manifest_path.name != "manifest.json":
        raise ManifestValidationError("manifest filename must be manifest.json")
    if manifest_path.is_symlink():
        raise ManifestValidationError("manifest must not be a symlink")
    try:
        manifest_path = manifest_path.resolve(strict=True)
    except OSError as exc:
        raise ManifestValidationError(f"manifest does not exist: {manifest_path}") from exc
    batch_dir = manifest_path.parent
    repository_root = _repository_root_from_batch_dir(batch_dir)
    manifest = _load_json_object(manifest_path, label="manifest")

    batch_ids = manifest.get("batch_ids")
    if not isinstance(batch_ids, list) or len(batch_ids) != 1:
        raise ManifestValidationError("manifest must contain exactly one batch_id")
    batch_id = batch_ids[0]
    if not isinstance(batch_id, str) or not SAFE_BATCH_ID.fullmatch(batch_id):
        raise ManifestValidationError("manifest batch_id is unsafe")
    if batch_dir.name != batch_id:
        raise ManifestValidationError("manifest batch_id does not match batch directory")
    if manifest.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "PASS_WITH_BLOCKED_ROWS"}:
        raise ManifestValidationError("manifest status is not importable")

    ready_count = _require_nonnegative_int(
        manifest.get("ready_count"), field="manifest.ready_count"
    )
    blocked_count = _require_nonnegative_int(
        manifest.get("blocked_count"), field="manifest.blocked_count"
    )
    warning_count = _require_nonnegative_int(
        manifest.get("warning_count"), field="manifest.warning_count"
    )
    _validate_safety(manifest.get("safety"), label="manifest")
    _recorded_path(
        manifest.get("manifest_path"),
        field="manifest.manifest_path",
        repository_root=repository_root,
        expected_path=manifest_path,
    )

    items_dir = (batch_dir / "items").resolve(strict=False)
    item_values = manifest.get("item_paths")
    if not isinstance(item_values, list) or len(item_values) != ready_count:
        raise ManifestValidationError("manifest item_paths count does not match ready_count")
    item_paths: list[Path] = []
    ready_payloads: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    seen_item_ids: set[str] = set()
    for index, value in enumerate(item_values):
        if not isinstance(value, str) or not value:
            raise ManifestValidationError(f"manifest item_paths[{index}] is invalid")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = repository_root / candidate
        if candidate.is_symlink():
            raise ManifestValidationError("manifest item path must not be a symlink")
        try:
            item_path = candidate.resolve(strict=True)
        except OSError as exc:
            raise ManifestValidationError(f"manifest item path is missing: {candidate}") from exc
        if item_path.parent != items_dir or not item_path.name.endswith(".input.json"):
            raise ManifestValidationError("manifest item path escapes the batch items directory")
        if item_path in seen_paths:
            raise ManifestValidationError("manifest contains a duplicate item path")
        payload = _load_json_object(item_path, label="ready item")
        _validate_ready_payload(payload, path=item_path, batch_id=batch_id)
        item_id = payload["content_item_id"]
        if item_id in seen_item_ids:
            raise ManifestValidationError("manifest contains a duplicate content_item_id")
        seen_paths.add(item_path)
        seen_item_ids.add(item_id)
        item_paths.append(item_path)
        ready_payloads.append(payload)

    blocked_expected = (
        repository_root
        / "exchange"
        / "reviews"
        / "new_release"
        / "batches"
        / f"{batch_id}.multistore_blocked.json"
    )
    blocked_path = _recorded_path(
        manifest.get("blocked_path"),
        field="manifest.blocked_path",
        repository_root=repository_root,
        expected_path=blocked_expected,
    )
    blocked = _load_json_object(blocked_path, label="blocked evidence")
    blocked_rows = blocked.get("blocked_rows")
    if not isinstance(blocked_rows, list) or len(blocked_rows) != blocked_count:
        raise ManifestValidationError("blocked evidence count does not match manifest")
    if blocked.get("batch_id") != batch_id:
        raise ManifestValidationError("blocked evidence batch_id mismatch")
    if blocked.get("warning_count") != warning_count:
        raise ManifestValidationError("blocked evidence warning_count mismatch")
    _validate_safety(blocked.get("safety"), label="blocked evidence")
    blocked_reasons = _blocked_reason_summary(blocked_rows)

    result_expected = (
        repository_root
        / "exchange"
        / "logs"
        / f"{batch_id}.multistore_import_result.json"
    )
    result_log_path = _recorded_path(
        manifest.get("result_log_path"),
        field="manifest.result_log_path",
        repository_root=repository_root,
        expected_path=result_expected,
    )
    result_log = _load_json_object(result_log_path, label="result log")
    for field, expected in (
        ("ready_count", ready_count),
        ("blocked_count", blocked_count),
        ("warning_count", warning_count),
    ):
        if result_log.get(field) != expected:
            raise ManifestValidationError(f"result log {field} mismatch")
    if result_log.get("batch_ids") != [batch_id]:
        raise ManifestValidationError("result log batch_ids mismatch")
    _validate_safety(result_log.get("safety"), label="result log")

    return ReadyBatch(
        repository_root=repository_root,
        batch_dir=batch_dir,
        manifest_path=manifest_path,
        blocked_path=blocked_path,
        result_log_path=result_log_path,
        batch_id=batch_id,
        item_paths=tuple(item_paths),
        ready_payloads=tuple(ready_payloads),
        ready_input_count=ready_count,
        blocked_count=blocked_count,
        warning_count=warning_count,
        blocked_rows=tuple(blocked_rows),
        blocked_reasons=blocked_reasons,
    )


def _authors_text(value: Any) -> str:
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ManifestValidationError("ready item authors must contain strings")
        return "|".join(item.strip() for item in value if item.strip())
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    raise ManifestValidationError("ready item authors is invalid")


def ready_payload_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    content_item_id = payload["content_item_id"]
    identifiers = payload.get("identifiers")
    if not isinstance(identifiers, dict):
        raise ManifestValidationError("ready item identifiers must be an object")
    category = str(payload.get("primary_category") or "").strip()
    item_type = "tankobon" if category in {"コミック", "comic", "manga"} else map_item_type(category)
    author_name = _authors_text(payload.get("authors"))
    publisher_name = str(payload.get("publisher") or "").strip()
    common = {
        "source_name": "new_release_multistore",
        "source_item_id": content_item_id,
        "title": str(payload["title"]).strip(),
        "isbn": str(
            identifiers.get("isbn13") or identifiers.get("isbn") or ""
        ).strip(),
        "normalized_title": str(payload.get("display_title") or payload["title"]).strip(),
        "volume_label": str(payload.get("volume_label") or "").strip(),
        "author_name": author_name,
        "author": author_name,
        "publisher_name": publisher_name,
        "publisher": publisher_name,
        "series_name": str(
            payload.get("series_name") or payload.get("series") or ""
        ).strip(),
        "release_date": str(payload.get("release_date") or "").strip(),
        "item_type": item_type,
        "wordpress_status": "draft",
    }
    rows: list[dict[str, str]] = []
    source_evidence = payload.get("source_evidence")
    if not isinstance(source_evidence, dict):
        source_evidence = {}
    for store in payload["store_navigation"]:
        store_name = STORE_NAMES[store["key"]]
        store_item_id = f"{store_name}:{content_item_id}"
        if store_name == "dmm":
            store_item_id = str(
                identifiers.get("dmm_content_id") or store_item_id
            ).strip()
        elif store_name == "amazon" and identifiers.get("amazon_asin"):
            store_item_id = str(identifiers["amazon_asin"]).strip().upper()
        rows.append(
            {
                **common,
                "store_name": store_name,
                "store_item_id": store_item_id,
                "product_url": str(
                    store.get("product_url") or store["url"]
                ).strip(),
                "affiliate_url": str(
                    store.get("affiliate_url") or ""
                ).strip(),
                "price": str(store.get("price") or "").strip(),
                "currency": str(store.get("currency") or "").strip(),
                "discount_rate": "",
                "point_rate": "",
                "source_row_sha256": str(
                    store.get("source_row_sha256")
                    or source_evidence.get("source_row_sha256")
                    or ""
                ).strip(),
                "verified_at": (
                    str(
                        store.get("verified_at")
                        or source_evidence.get("verified_at")
                        or ""
                    ).strip()
                    if store_name == "rakuten_kobo"
                    else ""
                ),
                "verification_method": (
                    str(
                        store.get("verification_method")
                        or source_evidence.get("verification_method")
                        or ""
                    ).strip()
                    if store_name == "rakuten_kobo"
                    else ""
                ),
            }
        )
    return rows


def write_ready_canonical_csv(batch: ReadyBatch, output_path: Path) -> None:
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite adapted CSV: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDNAMES)
        writer.writeheader()
        for payload in batch.ready_payloads:
            writer.writerows(ready_payload_rows(payload))


def import_ready_batch(
    session: Any,
    batch: ReadyBatch,
    *,
    execute: bool = False,
) -> ReadyImportSummary:
    summary = ReadyImportSummary(
        ready_input_count=batch.ready_input_count,
        blocked_count=batch.blocked_count,
        warning_count=batch.warning_count,
    )
    repository = ImportRepository(session)
    try:
        for payload in batch.ready_payloads:
            rows = ready_payload_rows(payload)
            first_result = None
            try:
                for row in rows:
                    result = repository.import_row(row)
                    if first_result is None:
                        first_result = result
                    summary.offer_created += int(result.offer_created)
                    summary.offer_updated += int(result.offer_updated)
                    summary.offer_unchanged += int(result.offer_unchanged)
            except Exception as exc:
                summary.failed += 1
                raise ValueError(
                    "Ready artifact import failed for "
                    f"{payload.get('content_item_id')}: {exc}"
                ) from exc
            if first_result is None:
                summary.failed += 1
                raise ValueError("Ready artifact produced no import rows")
            summary.processed += 1
            summary.created += int(first_result.created)
            summary.updated += int(first_result.updated)
            summary.unchanged += int(first_result.unchanged)

        if summary.processed != batch.ready_input_count:
            raise ValueError("Processed count does not match ready_input_count")
        if summary.created + summary.updated + summary.unchanged != summary.processed:
            raise ValueError("Item outcome counts do not match processed count")
        if execute:
            session.commit()
            summary.database_write_performed = bool(
                summary.created
                or summary.updated
                or summary.offer_created
                or summary.offer_updated
            )
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    return summary


def _manifest_payload(
    *,
    batch: ReadyBatch,
    summary: ReadyImportSummary,
    execute: bool,
    adapted_csv: str | None,
) -> dict[str, Any]:
    values = asdict(summary)
    return {
        "status": "PASS",
        "mode": "EXECUTE" if execute else "DRY_RUN",
        "input_mode": "PREVALIDATED_READY_ARTIFACTS",
        "database_backend": DATABASE_BACKEND,
        "batch_id": batch.batch_id,
        "batch_dir": str(batch.batch_dir),
        "manifest": str(batch.manifest_path),
        "blocked_evidence": str(batch.blocked_path),
        "prevalidation_result_log": str(batch.result_log_path),
        "adapted_csv": adapted_csv,
        **values,
        "blocked_reasons": list(batch.blocked_reasons),
        "blocked_rows": list(batch.blocked_rows),
        "wordpress_write_performed": False,
        "x_post_performed": False,
    }


def _run_legacy_csv(args: argparse.Namespace) -> dict[str, Any]:
    if args.execute:
        raise RuntimeError(
            "Legacy CSV --execute is refused because ready/blocked evidence "
            "is not bound. Use --manifest or --batch-dir."
        )
    temporary_path: Path | None = None
    if args.keep_adapted_csv is not None:
        adapted_path = args.keep_adapted_csv
        if adapted_path.exists() or adapted_path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite adapted CSV: {adapted_path}")
    else:
        temp_file = tempfile.NamedTemporaryFile(
            prefix="new_release_multistore_",
            suffix=".csv",
            delete=False,
        )
        temp_file.close()
        temporary_path = Path(temp_file.name)
        adapted_path = temporary_path
    try:
        adapter_summary = adapt_multistore_csv(
            input_path=args.input_csv,
            output_path=adapted_path,
        )
        with SessionLocal() as session:
            import_summary = CsvImportService(session).import_file(
                adapted_path,
                dry_run=True,
            )
        return {
            "status": "PASS",
            "mode": "DRY_RUN",
            "input_mode": "LEGACY_UNVALIDATED_CSV_DRY_RUN_ONLY",
            "database_backend": DATABASE_BACKEND,
            "input_csv": str(args.input_csv),
            "adapted_csv": (
                str(adapted_path)
                if args.keep_adapted_csv is not None
                else "TEMPORARY_REMOVED"
            ),
            "adapter": asdict(adapter_summary),
            "import": asdict(import_summary),
            "database_write_performed": False,
            "external_network_performed": False,
            "wordpress_write_performed": False,
            "x_post_performed": False,
        }
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if DATABASE_BACKEND != "sqlite":
        raise RuntimeError(
            "SQL-B1-2 currently permits SQLite only. "
            f"Current backend: {DATABASE_BACKEND}"
        )

    if args.input_csv is not None:
        payload = _run_legacy_csv(args)
    else:
        manifest_path = (
            args.manifest
            if args.manifest is not None
            else args.batch_dir / "manifest.json"
        )
        batch = load_ready_batch(manifest_path)
        adapted_csv: str | None = None
        if args.keep_adapted_csv is not None:
            write_ready_canonical_csv(batch, args.keep_adapted_csv)
            adapted_csv = str(args.keep_adapted_csv)
        with SessionLocal() as session:
            summary = import_ready_batch(
                session,
                batch,
                execute=args.execute,
            )
        payload = _manifest_payload(
            batch=batch,
            summary=summary,
            execute=args.execute,
            adapted_csv=adapted_csv,
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
