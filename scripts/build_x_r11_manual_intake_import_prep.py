from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "MANUAL-INTAKE-IMPORT-PREP"
)

EXPECTED_REVIEW_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "MANUAL-INTAKE-HUMAN-REVIEW-PACK"
)

EXPECTED_REVIEW_STATUS = (
    "HUMAN_REVIEW_PACK_READY"
)

EXPECTED_REVIEW_STATE = (
    "AWAITING_EXPLICIT_HUMAN_APPROVAL"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_IMPORT_PREP_ONLY"
)

EXPECTED_APPROVAL_SCOPE = "IMPORT_PREP_ONLY"

NEXT_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_ONE_SHOT_IMPORT_ONLY"
)

PRODUCTION_DATABASE_PATH = (
    REPOSITORY_ROOT
    / "data/database/ebook_affiliate.db"
).resolve()

STORE_URL_MAPPING = (
    (
        "amazon_url",
        "amazon_kindle",
    ),
    (
        "rakuten_kobo_url",
        "rakuten_kobo",
    ),
    (
        "dmm_url",
        "dmm_books",
    ),
)

ITEM_TYPE_MAPPING = {
    "comic": "tankobon",
    "light_novel": "light_novel",
    "general_book": "general_book",
}

MANUAL_SOURCE_NAME = (
    "x_r11_manual_intake"
)


class XR11ImportPrepError(RuntimeError):
    """Raised when Import Prep cannot be built safely."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11ImportPrepError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise XR11ImportPrepError(
            f"JSON is invalid: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def quote_identifier(
    value: str,
) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def read_table_schema(
    connection: sqlite3.Connection,
    table_name: str,
) -> dict[str, Any]:
    require(
        table_exists(
            connection,
            table_name,
        ),
        f"required table is missing: {table_name}",
    )

    quoted_table = quote_identifier(
        table_name
    )

    columns = [
        {
            "cid": int(row["cid"]),
            "name": str(row["name"]),
            "type": str(
                row["type"] or ""
            ),
            "notnull": bool(
                row["notnull"]
            ),
            "default": row["dflt_value"],
            "primary_key_position": int(
                row["pk"]
            ),
        }
        for row in connection.execute(
            (
                "PRAGMA table_info("
                f"{quoted_table}"
                ")"
            )
        ).fetchall()
    ]

    foreign_keys = [
        {
            "id": int(row["id"]),
            "sequence": int(row["seq"]),
            "referenced_table": str(
                row["table"]
            ),
            "from_column": str(
                row["from"]
            ),
            "to_column": (
                str(row["to"])
                if row["to"] is not None
                else None
            ),
            "on_update": str(
                row["on_update"]
            ),
            "on_delete": str(
                row["on_delete"]
            ),
        }
        for row in connection.execute(
            (
                "PRAGMA foreign_key_list("
                f"{quoted_table}"
                ")"
            )
        ).fetchall()
    ]

    indexes = []

    for index_row in connection.execute(
        (
            "PRAGMA index_list("
            f"{quoted_table}"
            ")"
        )
    ).fetchall():
        index_name = str(
            index_row["name"]
        )

        index_columns = [
            str(row["name"])
            for row in connection.execute(
                (
                    "PRAGMA index_info("
                    f"{quote_identifier(index_name)}"
                    ")"
                )
            ).fetchall()
        ]

        indexes.append(
            {
                "name": index_name,
                "unique": bool(
                    index_row["unique"]
                ),
                "columns": index_columns,
            }
        )

    return {
        "table_name": table_name,
        "columns": columns,
        "foreign_keys": foreign_keys,
        "indexes": indexes,
    }


def column_names(
    schema: dict[str, Any],
) -> set[str]:
    return {
        str(column["name"])
        for column in schema["columns"]
    }


def first_existing_column(
    columns: set[str],
    aliases: tuple[str, ...],
) -> str | None:
    for alias in aliases:
        if alias in columns:
            return alias

    return None


def assign_if_present(
    values: dict[str, Any],
    columns: set[str],
    aliases: tuple[str, ...],
    value: Any,
) -> str | None:
    column = first_existing_column(
        columns,
        aliases,
    )

    if column is not None:
        values[column] = value

    return column


def missing_required_columns(
    schema: dict[str, Any],
    values: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []

    for column in schema["columns"]:
        name = str(column["name"])
        column_type = str(
            column["type"]
        ).upper()

        if not column["notnull"]:
            continue

        if column["default"] is not None:
            continue

        if (
            column["primary_key_position"] > 0
            and "INT" in column_type
            and name not in values
        ):
            continue

        if (
            name not in values
            or values[name] is None
            or values[name] == ""
        ):
            blockers.append(
                (
                    "UNMAPPED_REQUIRED_COLUMN:"
                    f"{schema['table_name']}:{name}"
                )
            )

    return blockers


def build_insert_preview(
    table_name: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    columns = list(values)

    quoted_columns = ", ".join(
        quote_identifier(column)
        for column in columns
    )

    placeholders = ", ".join(
        f":{column}"
        for column in columns
    )

    return {
        "table": table_name,
        "sql": (
            f"INSERT INTO "
            f"{quote_identifier(table_name)} "
            f"({quoted_columns}) "
            f"VALUES ({placeholders})"
        ),
        "parameters": values,
        "execution_allowed": False,
    }


def find_ebook_duplicates(
    connection: sqlite3.Connection,
    schema: dict[str, Any],
    *,
    planned_id: str,
    title: str,
    release_date: str,
) -> list[dict[str, Any]]:
    columns = column_names(schema)

    id_column = first_existing_column(
        columns,
        (
            "id",
            "ebook_item_id",
            "item_id",
        ),
    )
    title_column = first_existing_column(
        columns,
        (
            "title",
            "book_title",
        ),
    )
    release_column = first_existing_column(
        columns,
        (
            "release_date",
            "publication_date",
        ),
    )

    matches: list[dict[str, Any]] = []

    if id_column is not None:
        row = connection.execute(
            (
                f"SELECT * FROM "
                f"{quote_identifier('ebook_items')} "
                f"WHERE {quote_identifier(id_column)} = ? "
                "LIMIT 1"
            ),
            (planned_id,),
        ).fetchone()

        if row is not None:
            matches.append(
                {
                    "match_type": (
                        "PLANNED_ID_ALREADY_EXISTS"
                    ),
                    "row": dict(row),
                }
            )

    if (
        title_column is not None
        and release_column is not None
    ):
        rows = connection.execute(
            (
                f"SELECT * FROM "
                f"{quote_identifier('ebook_items')} "
                f"WHERE TRIM("
                f"{quote_identifier(title_column)}) = ? "
                f"AND TRIM("
                f"{quote_identifier(release_column)}) = ? "
                "LIMIT 20"
            ),
            (
                title,
                release_date,
            ),
        ).fetchall()

        for row in rows:
            matches.append(
                {
                    "match_type": (
                        "TITLE_RELEASE_DATE_DUPLICATE"
                    ),
                    "row": dict(row),
                }
            )

    return matches


def find_offer_duplicates(
    connection: sqlite3.Connection,
    schema: dict[str, Any],
    *,
    planned_offers: list[dict[str, Any]],
    url_column: str | None,
    id_column: str | None,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    for offer in planned_offers:
        values = offer["values"]

        if (
            id_column is not None
            and id_column in values
        ):
            row = connection.execute(
                (
                    f"SELECT * FROM "
                    f"{quote_identifier('store_offers')} "
                    f"WHERE "
                    f"{quote_identifier(id_column)} = ? "
                    "LIMIT 1"
                ),
                (values[id_column],),
            ).fetchone()

            if row is not None:
                matches.append(
                    {
                        "match_type": (
                            "PLANNED_OFFER_ID_ALREADY_EXISTS"
                        ),
                        "row": dict(row),
                    }
                )

        if (
            url_column is not None
            and url_column in values
        ):
            rows = connection.execute(
                (
                    f"SELECT * FROM "
                    f"{quote_identifier('store_offers')} "
                    f"WHERE "
                    f"{quote_identifier(url_column)} = ? "
                    "LIMIT 20"
                ),
                (values[url_column],),
            ).fetchall()

            for row in rows:
                matches.append(
                    {
                        "match_type": (
                            "STORE_URL_DUPLICATE"
                        ),
                        "row": dict(row),
                    }
                )

    return matches


def derive_store_item_id(
    *,
    store_name: str,
    product_url: str,
) -> str:
    parsed = urlparse(product_url)

    path_segments = [
        segment
        for segment in parsed.path.split("/")
        if segment
    ]

    if (
        store_name == "rakuten_kobo"
        and parsed.hostname
        == "books.rakuten.co.jp"
        and len(path_segments) >= 2
        and path_segments[-2] == "rk"
    ):
        return path_segments[-1]

    url_digest = hashlib.sha256(
        product_url.encode("utf-8")
    ).hexdigest()[:32]

    return (
        f"{store_name}:"
        f"urlsha256:{url_digest}"
    )


def verify_review_pack_digest(
    review_pack: dict[str, Any],
) -> None:
    recorded_digest = review_pack.get(
        "human_review_pack_digest_sha256"
    )

    require(
        isinstance(recorded_digest, str)
        and recorded_digest,
        (
            "human review pack digest "
            "is missing"
        ),
    )

    payload = {
        key: value
        for key, value in review_pack.items()
        if key
        != "human_review_pack_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == recorded_digest,
        (
            "human review pack digest "
            "verification failed"
        ),
    )


def run_import_prep(
    *,
    human_review_pack_path: Path,
    approval_review_request_id: str,
    approval_candidate_digest: str,
    approval_label: str,
    approval_scope: str,
    production_database_path: Path,
    expected_production_database_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    human_review_pack_path = (
        human_review_pack_path.resolve()
    )
    production_database_path = (
        production_database_path.resolve()
    )
    expected_production_database_path = (
        expected_production_database_path.resolve()
    )
    output_root = output_root.resolve()

    require(
        production_database_path
        == expected_production_database_path,
        (
            "production database path must "
            "exactly match the fixed path"
        ),
    )
    require(
        production_database_path.is_file(),
        (
            "production database is missing: "
            f"{production_database_path}"
        ),
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    review_pack = load_json_object(
        human_review_pack_path
    )

    verify_review_pack_digest(
        review_pack
    )

    require(
        review_pack.get("phase")
        == EXPECTED_REVIEW_PHASE,
        "human review pack phase is invalid",
    )
    require(
        review_pack.get("status")
        == EXPECTED_REVIEW_STATUS,
        "human review pack status is invalid",
    )
    require(
        review_pack.get("review_state")
        == EXPECTED_REVIEW_STATE,
        "human review state is invalid",
    )
    require(
        review_pack.get(
            "duplicate_match_count"
        )
        == 0,
        (
            "human review pack contains "
            "duplicate matches"
        ),
    )
    require(
        review_pack.get(
            "explicit_approval_required"
        )
        is True,
        (
            "human review pack must require "
            "explicit approval"
        ),
    )
    require(
        review_pack.get(
            "approval_issued"
        )
        is False,
        (
            "source review pack approval state "
            "must remain unissued"
        ),
    )
    require(
        review_pack.get(
            "database_import_allowed"
        )
        is False,
        (
            "source review pack must not "
            "allow database import"
        ),
    )
    require(
        review_pack.get(
            "wordpress_draft_creation_allowed"
        )
        is False,
        (
            "source review pack must not "
            "allow WordPress write"
        ),
    )
    require(
        review_pack.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "source review pack must not "
            "allow normal X-FB write"
        ),
    )
    require(
        review_pack.get(
            "production_status"
        )
        == "NO_GO",
        (
            "source review pack production "
            "status must remain NO_GO"
        ),
    )

    require(
        approval_review_request_id
        == review_pack.get(
            "review_request_id"
        ),
        (
            "approval review_request_id "
            "does not match the review pack"
        ),
    )
    require(
        approval_candidate_digest
        == review_pack.get(
            "candidate_digest_sha256"
        ),
        (
            "approval candidate digest "
            "does not match the review pack"
        ),
    )
    require(
        approval_label
        == EXPECTED_APPROVAL_LABEL,
        "approval label is invalid",
    )
    require(
        approval_label
        == review_pack.get(
            "required_approval_label"
        ),
        (
            "approval label does not match "
            "the review pack"
        ),
    )
    require(
        approval_scope
        == EXPECTED_APPROVAL_SCOPE,
        "approval scope is invalid",
    )

    candidate = review_pack.get(
        "candidate"
    )

    require(
        isinstance(candidate, dict),
        "review candidate must be an object",
    )

    candidate_digest = canonical_digest(
        candidate
    )

    require(
        candidate_digest
        == approval_candidate_digest,
        (
            "candidate content digest "
            "does not match approval"
        ),
    )

    generated_at = (
        datetime.now(
            timezone.utc
        )
        .replace(tzinfo=None)
        .isoformat(
            sep=" ",
            timespec="microseconds",
        )
    )

    category = str(
        candidate.get("category")
        or ""
    ).strip()

    item_type = ITEM_TYPE_MAPPING.get(
        category
    )

    require(
        item_type is not None,
        (
            "candidate category cannot be "
            "mapped to ebook item_type"
        ),
    )

    planned_ebook_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            (
                "ai-media-os:x-r11:"
                f"ebook:{candidate_digest}"
            ),
        )
    )

    database_sha_before = sha256_file(
        production_database_path
    )

    connection = sqlite3.connect(
        (
            "file:"
            + quote(
                str(production_database_path)
            )
            + "?mode=ro"
        ),
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        connection.execute(
            "PRAGMA query_only = ON"
        )

        ebook_schema = read_table_schema(
            connection,
            "ebook_items",
        )
        offer_schema = read_table_schema(
            connection,
            "store_offers",
        )

        ebook_columns = column_names(
            ebook_schema
        )
        offer_columns = column_names(
            offer_schema
        )

        schema_blockers: list[str] = []

        ebook_values: dict[str, Any] = {}

        ebook_id_column = assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "id",
                "ebook_item_id",
                "item_id",
            ),
            planned_ebook_id,
        )
        ebook_title_column = assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "title",
                "book_title",
            ),
            candidate["title"],
        )
        ebook_release_column = assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "release_date",
                "publication_date",
            ),
            candidate["release_date"],
        )

        assign_if_present(
            ebook_values,
            ebook_columns,
            ("source_name",),
            MANUAL_SOURCE_NAME,
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("source_item_id",),
            candidate["intake_id"],
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("item_type",),
            item_type,
        )

        if ebook_id_column is None:
            schema_blockers.append(
                "EBOOK_ID_COLUMN_NOT_FOUND"
            )

        if ebook_title_column is None:
            schema_blockers.append(
                "EBOOK_TITLE_COLUMN_NOT_FOUND"
            )

        if ebook_release_column is None:
            schema_blockers.append(
                "EBOOK_RELEASE_DATE_COLUMN_NOT_FOUND"
            )

        assign_if_present(
            ebook_values,
            ebook_columns,
            ("volume_label",),
            candidate.get(
                "volume_label"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "publisher_name",
                "publisher",
            ),
            candidate.get(
                "publisher"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "author_name",
                "authors",
                "author",
            ),
            candidate.get(
                "authors"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "category",
                "category_slug",
            ),
            candidate.get(
                "category"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("source_discovery_url",),
            candidate.get(
                "source_discovery_url"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "publisher_confirmation_url",
            ),
            candidate.get(
                "publisher_confirmation_url"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("description_mode",),
            candidate.get(
                "description_mode"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("human_review_state",),
            candidate.get(
                "human_review_state"
            ),
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("wordpress_post_id",),
            None,
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("wordpress_status",),
            "NOT_CREATED",
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "excluded",
                "is_excluded",
            ),
            0,
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            (
                "source_type",
                "source",
            ),
            "manual_real_source",
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("created_at",),
            generated_at,
        )
        assign_if_present(
            ebook_values,
            ebook_columns,
            ("updated_at",),
            generated_at,
        )

        schema_blockers.extend(
            missing_required_columns(
                ebook_schema,
                ebook_values,
            )
        )

        offer_id_column = first_existing_column(
            offer_columns,
            (
                "id",
                "offer_id",
            ),
        )
        offer_ebook_id_column = (
            first_existing_column(
                offer_columns,
                (
                    "ebook_item_id",
                    "item_id",
                ),
            )
        )
        offer_store_column = (
            first_existing_column(
                offer_columns,
                (
                    "store",
                    "store_name",
                    "provider",
                    "retailer",
                    "platform",
                ),
            )
        )
        offer_store_item_id_column = (
            first_existing_column(
                offer_columns,
                ("store_item_id",),
            )
        )
        offer_product_url_column = (
            first_existing_column(
                offer_columns,
                (
                    "product_url",
                    "store_url",
                    "url",
                ),
            )
        )
        offer_affiliate_url_column = (
            first_existing_column(
                offer_columns,
                ("affiliate_url",),
            )
        )
        offer_last_checked_column = (
            first_existing_column(
                offer_columns,
                ("last_checked_at",),
            )
        )

        if offer_id_column is None:
            schema_blockers.append(
                "STORE_OFFER_ID_COLUMN_NOT_FOUND"
            )

        if offer_ebook_id_column is None:
            schema_blockers.append(
                "STORE_OFFER_EBOOK_ID_COLUMN_NOT_FOUND"
            )

        if offer_store_column is None:
            schema_blockers.append(
                "STORE_NAME_COLUMN_NOT_FOUND"
            )

        if offer_store_item_id_column is None:
            schema_blockers.append(
                "STORE_ITEM_ID_COLUMN_NOT_FOUND"
            )

        if offer_product_url_column is None:
            schema_blockers.append(
                "STORE_PRODUCT_URL_COLUMN_NOT_FOUND"
            )

        if offer_last_checked_column is None:
            schema_blockers.append(
                "STORE_LAST_CHECKED_AT_COLUMN_NOT_FOUND"
            )

        planned_offers: list[
            dict[str, Any]
        ] = []

        for (
            candidate_url_field,
            store_name,
        ) in STORE_URL_MAPPING:
            url_value = str(
                candidate.get(
                    candidate_url_field
                )
                or ""
            ).strip()

            if not url_value:
                continue

            planned_offer_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    (
                        "ai-media-os:x-r11:"
                        f"offer:{candidate_digest}:"
                        f"{store_name}"
                    ),
                )
            )

            values: dict[str, Any] = {}

            if offer_id_column is not None:
                values[
                    offer_id_column
                ] = planned_offer_id

            if (
                offer_ebook_id_column
                is not None
            ):
                values[
                    offer_ebook_id_column
                ] = planned_ebook_id

            if offer_store_column is not None:
                values[
                    offer_store_column
                ] = store_name

            store_item_id = (
                derive_store_item_id(
                    store_name=store_name,
                    product_url=url_value,
                )
            )

            if (
                offer_store_item_id_column
                is not None
            ):
                values[
                    offer_store_item_id_column
                ] = store_item_id

            if (
                offer_product_url_column
                is not None
            ):
                values[
                    offer_product_url_column
                ] = url_value

            if (
                offer_affiliate_url_column
                is not None
            ):
                values[
                    offer_affiliate_url_column
                ] = None

            if (
                offer_last_checked_column
                is not None
            ):
                values[
                    offer_last_checked_column
                ] = generated_at

            assign_if_present(
                values,
                offer_columns,
                (
                    "source_type",
                    "source",
                ),
                "manual_real_source",
            )
            assign_if_present(
                values,
                offer_columns,
                (
                    "affiliate_tracking_ready",
                    "tracking_ready",
                ),
                0,
            )
            assign_if_present(
                values,
                offer_columns,
                ("is_affiliate_url",),
                0,
            )
            assign_if_present(
                values,
                offer_columns,
                ("tracking_status",),
                "NOT_VERIFIED",
            )
            assign_if_present(
                values,
                offer_columns,
                ("created_at",),
                generated_at,
            )
            assign_if_present(
                values,
                offer_columns,
                ("updated_at",),
                generated_at,
            )

            schema_blockers.extend(
                missing_required_columns(
                    offer_schema,
                    values,
                )
            )

            planned_offers.append(
                {
                    "store": store_name,
                    "source_candidate_field": (
                        candidate_url_field
                    ),
                    "planned_offer_id": (
                        planned_offer_id
                    ),
                    "planned_store_item_id": (
                        store_item_id
                    ),
                    "retail_url_semantics": (
                        "PRODUCT_URL_NOT_AFFILIATE_URL"
                    ),
                    "values": values,
                }
            )

        if not planned_offers:
            schema_blockers.append(
                "NO_STORE_OFFER_PLANNED"
            )

        ebook_duplicates = (
            find_ebook_duplicates(
                connection,
                ebook_schema,
                planned_id=planned_ebook_id,
                title=str(
                    candidate["title"]
                ),
                release_date=str(
                    candidate["release_date"]
                ),
            )
        )

        offer_duplicates = (
            find_offer_duplicates(
                connection,
                offer_schema,
                planned_offers=(
                    planned_offers
                ),
                url_column=(
                    offer_product_url_column
                ),
                id_column=(
                    offer_id_column
                ),
            )
        )

    finally:
        connection.close()

    database_sha_after = sha256_file(
        production_database_path
    )

    require(
        database_sha_before
        == database_sha_after,
        (
            "production database changed "
            "during Import Prep"
        ),
    )

    duplicate_match_count = (
        len(ebook_duplicates)
        + len(offer_duplicates)
    )

    schema_blockers = sorted(
        set(schema_blockers)
    )

    if duplicate_match_count > 0:
        status = (
            "BLOCKED_IMPORT_PREP_"
            "DUPLICATE_FOUND"
        )
        prep_state = (
            "DUPLICATE_REQUIRES_RESOLUTION"
        )
        authorized_next_phase = None

    elif schema_blockers:
        status = (
            "BLOCKED_IMPORT_PREP_"
            "SCHEMA_MAPPING_INCOMPLETE"
        )
        prep_state = (
            "SCHEMA_MAPPING_REQUIRES_REVIEW"
        )
        authorized_next_phase = None

    else:
        status = (
            "PASS_IMPORT_PREP_READY_"
            "AWAITING_ONE_SHOT_IMPORT_APPROVAL"
        )
        prep_state = (
            "IMPORT_PLAN_READY_NOT_EXECUTABLE"
        )
        authorized_next_phase = (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "ONE-SHOT-IMPORT-FINAL-GATE"
        )

    approval_evidence = {
        "approval_received": True,
        "approval_review_request_id": (
            approval_review_request_id
        ),
        "approval_candidate_digest_sha256": (
            approval_candidate_digest
        ),
        "approval_label": approval_label,
        "approval_scope": approval_scope,
        "approval_consumed_for_phase": PHASE,
        "authorizes_import_prep": True,
        "authorizes_database_write": False,
        "authorizes_wordpress_write": False,
        "authorizes_normal_x_fb_write": False,
    }

    ebook_insert_preview = (
        build_insert_preview(
            "ebook_items",
            ebook_values,
        )
    )

    offer_insert_previews = [
        build_insert_preview(
            "store_offers",
            offer["values"],
        )
        for offer in planned_offers
    ]

    rollback_preview = {
        "execution_allowed": False,
        "order": [
            "DELETE_PLANNED_STORE_OFFERS",
            "DELETE_PLANNED_EBOOK_ITEM",
        ],
        "planned_offer_ids": [
            offer["planned_offer_id"]
            for offer in planned_offers
        ],
        "planned_ebook_id": (
            planned_ebook_id
        ),
        "conditions": [
            (
                "Only delete rows whose IDs "
                "exactly match this Import Prep pack"
            ),
            (
                "Rollback must execute inside "
                "the same transaction before COMMIT "
                "or under a separately approved "
                "recovery procedure"
            ),
        ],
    }

    transaction_plan = [
        {
            "step": 1,
            "action": (
                "Verify exact production DB path "
                "and pre-execution SHA-256"
            ),
        },
        {
            "step": 2,
            "action": (
                "Open one transaction and enable "
                "foreign-key enforcement"
            ),
        },
        {
            "step": 3,
            "action": (
                "Re-run planned-ID, title/date, "
                "and URL duplicate checks"
            ),
        },
        {
            "step": 4,
            "action": (
                "Insert exactly one ebook_items row"
            ),
        },
        {
            "step": 5,
            "action": (
                "Insert only the planned "
                "store_offers rows"
            ),
        },
        {
            "step": 6,
            "action": (
                "Verify inserted row counts, IDs, "
                "candidate digest, and foreign keys"
            ),
        },
        {
            "step": 7,
            "action": (
                "COMMIT only when every verification "
                "passes; otherwise ROLLBACK"
            ),
        },
    ]

    pack_payload = {
        "phase": PHASE,
        "status": "IMPORT_PREP_PACK_READY",
        "prep_state": prep_state,
        "generated_at": generated_at,
        "human_review_pack_path": str(
            human_review_pack_path
        ),
        "human_review_pack_sha256": (
            sha256_file(
                human_review_pack_path
            )
        ),
        "human_review_pack_digest_sha256": (
            review_pack[
                "human_review_pack_digest_sha256"
            ]
        ),
        "approval_evidence": (
            approval_evidence
        ),
        "candidate": candidate,
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "production_database_path": str(
            production_database_path
        ),
        "production_database_sha256": (
            database_sha_after
        ),
        "production_database_unchanged": True,
        "schema_snapshot": {
            "ebook_items": ebook_schema,
            "store_offers": offer_schema,
        },
        "schema_blockers": schema_blockers,
        "planned_ebook_id": (
            planned_ebook_id
        ),
        "planned_ebook_item_values": (
            ebook_values
        ),
        "planned_store_offers": (
            planned_offers
        ),
        "ebook_insert_preview": (
            ebook_insert_preview
        ),
        "store_offer_insert_previews": (
            offer_insert_previews
        ),
        "ebook_duplicate_matches": (
            ebook_duplicates
        ),
        "store_offer_duplicate_matches": (
            offer_duplicates
        ),
        "duplicate_match_count": (
            duplicate_match_count
        ),
        "transaction_plan": (
            transaction_plan
        ),
        "rollback_preview": (
            rollback_preview
        ),
        "affiliate_tracking_id_ready": False,
        "pr_disclosure_ready": False,
        "wordpress_draft_creation_allowed": False,
        "required_next_approval_label": (
            NEXT_APPROVAL_LABEL
        ),
        "one_shot_import_approval_issued": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "approval_request_write": False,
        "wordpress_write": False,
        "normal_x_fb_write_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "IMPORT_PREP_ONLY_NO_EXECUTION"
        ),
    }

    pack_digest = canonical_digest(
        pack_payload
    )

    pack = {
        **pack_payload,
        "import_prep_pack_digest_sha256": (
            pack_digest
        ),
    }

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    pack_path = (
        output_root
        / "x_r11_manual_intake_import_prep_pack.json"
    )
    result_path = (
        output_root
        / "x_r11_manual_intake_import_prep_result.json"
    )
    approval_receipt_path = (
        output_root
        / "x_r11_manual_intake_import_prep_approval_receipt.json"
    )

    approval_receipt_payload = {
        "phase": PHASE,
        "status": (
            "APPROVAL_CONSUMED_FOR_IMPORT_PREP_ONLY"
        ),
        **approval_evidence,
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "import_prep_pack_digest_sha256": (
            pack_digest
        ),
        "database_write_authorized": False,
        "production_execution_authorized": False,
        "production_status": "NO_GO",
    }

    approval_receipt = {
        **approval_receipt_payload,
        "approval_receipt_digest_sha256": (
            canonical_digest(
                approval_receipt_payload
            )
        ),
    }

    atomic_write_json(
        pack_path,
        pack,
    )
    atomic_write_json(
        approval_receipt_path,
        approval_receipt,
    )

    result = {
        "phase": PHASE,
        "status": status,
        "prep_state": prep_state,
        "approval_consumed_for_import_prep": (
            True
        ),
        "approval_authorizes_database_write": (
            False
        ),
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "planned_ebook_id": (
            planned_ebook_id
        ),
        "planned_store_offer_count": (
            len(planned_offers)
        ),
        "schema_blocker_count": (
            len(schema_blockers)
        ),
        "schema_blockers": schema_blockers,
        "duplicate_match_count": (
            duplicate_match_count
        ),
        "production_database_sha256_before": (
            database_sha_before
        ),
        "production_database_sha256_after": (
            database_sha_after
        ),
        "production_database_unchanged": True,
        "import_prep_pack_path": str(
            pack_path
        ),
        "import_prep_pack_digest_sha256": (
            pack_digest
        ),
        "approval_receipt_path": str(
            approval_receipt_path
        ),
        "required_next_approval_label": (
            NEXT_APPROVAL_LABEL
        ),
        "one_shot_import_approval_issued": (
            False
        ),
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "normal_x_fb_write_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "IMPORT_PREP_ONLY_NO_EXECUTION"
        ),
    }

    atomic_write_json(
        result_path,
        result,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--human-review-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--approval-review-request-id",
        required=True,
    )
    parser.add_argument(
        "--approval-candidate-digest",
        required=True,
    )
    parser.add_argument(
        "--approval-label",
        required=True,
    )
    parser.add_argument(
        "--approval-scope",
        required=True,
    )
    parser.add_argument(
        "--production-db",
        type=Path,
        default=PRODUCTION_DATABASE_PATH,
    )
    parser.add_argument(
        "--expected-production-db",
        type=Path,
        default=PRODUCTION_DATABASE_PATH,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_import_prep(
            human_review_pack_path=(
                args.human_review_pack
            ),
            approval_review_request_id=(
                args.approval_review_request_id
            ),
            approval_candidate_digest=(
                args.approval_candidate_digest
            ),
            approval_label=(
                args.approval_label
            ),
            approval_scope=(
                args.approval_scope
            ),
            production_database_path=(
                args.production_db
            ),
            expected_production_database_path=(
                args.expected_production_db
            ),
            output_root=args.output_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "approval_consumed": False,
                    "execution_allowed": False,
                    "database_import_allowed": False,
                    "database_write": False,
                    "wordpress_write": False,
                    "normal_x_fb_write_allowed": False,
                    "production_execution": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
