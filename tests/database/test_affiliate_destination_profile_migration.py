from __future__ import annotations

import os
from pathlib import Path
import subprocess

from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC = ROOT / ".venv" / "bin" / "alembic"
REVISION = "e4b7c9d2a6f1"
PREVIOUS_REVISION = "c8a1e7f9b2d4"


def _run_alembic(database_path: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_BACKEND": "sqlite",
            "DATABASE_URL": f"sqlite:///{database_path}",
            "PYTHONPATH": str(ROOT),
        }
    )
    subprocess.run(
        [str(ALEMBIC), *arguments],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_empty_sqlite_upgrade_and_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "empty-upgrade.db"
    _run_alembic(database_path, "upgrade", REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert "affiliate_destination_profiles" in tables
        assert "store_offer_affiliate_links" in tables
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == REVISION
    finally:
        engine.dispose()

    _run_alembic(database_path, "downgrade", PREVIOUS_REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert "affiliate_destination_profiles" not in tables
        assert "store_offer_affiliate_links" not in tables
        assert "store_offers" in tables
    finally:
        engine.dispose()


def test_existing_schema_upgrade_migrates_only_matching_blog_data(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "existing-upgrade.db"
    _run_alembic(database_path, "upgrade", PREVIOUS_REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    matching_url = (
        "https://al.dmm.com/?lurl=https%3A%2F%2Fbook.dmm.com%2Fproduct%2F"
        "4493998%2Fb000fhftx08481%2F&af_id=legacy-blog-008"
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO ebook_items "
                "(id, source_name, source_item_id, title, item_type, "
                "workflow_status, wordpress_status, x_status, affiliate_status, "
                "image_status, review_status, publish_ready, is_excluded, "
                "created_at, updated_at) VALUES "
                "('item-1', 'test', 'source-1', '作品', 'tankobon', 'NEW', "
                "'NOT_CREATED', 'NOT_CREATED', 'UNCHECKED', 'UNCHECKED', "
                "'NOT_REVIEWED', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO store_offers "
                "(id, ebook_item_id, store_name, store_item_id, product_url, "
                "affiliate_url, last_checked_at) VALUES "
                "('offer-1', 'item-1', 'dmm', 'b000fhftx08481', "
                "'https://book.dmm.com/product/4493998/b000fhftx08481/', "
                ":matching_url, CURRENT_TIMESTAMP), "
                "('offer-2', 'item-1', 'dmm', 'other-product', "
                "'https://book.dmm.com/product/other/other-product/', "
                "'https://al.dmm.com/?af_id=unknown-999', CURRENT_TIMESTAMP)"
            ),
            {"matching_url": matching_url},
        )
        connection.execute(
            text(
                "INSERT INTO affiliate_account_settings "
                "(service_name, affiliate_id, url_template, enabled, "
                "updated_at, updated_by) VALUES "
                "('dmm', 'legacy-blog-008', NULL, 1, CURRENT_TIMESTAMP, 'test')"
            )
        )
    engine.dispose()

    _run_alembic(database_path, "upgrade", REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            profiles = connection.execute(
                text(
                    "SELECT destination_key, destination_type, affiliate_id "
                    "FROM affiliate_destination_profiles ORDER BY destination_key"
                )
            ).all()
            links = connection.execute(
                text(
                    "SELECT store_offer_id, affiliate_url "
                    "FROM store_offer_affiliate_links"
                )
            ).all()
            assert profiles == [
                ("blog_main", "wordpress", "legacy-blog-008")
            ]
            assert all(profile.destination_key != "x_main" for profile in profiles)
            assert links == [("offer-1", matching_url)]
            assert connection.scalar(
                text("SELECT COUNT(*) FROM ebook_items")
            ) == 1
            assert connection.scalar(
                text("SELECT COUNT(*) FROM store_offers")
            ) == 2
            assert connection.scalar(
                text(
                    "SELECT affiliate_url FROM store_offers WHERE id = 'offer-1'"
                )
            ) == matching_url
    finally:
        engine.dispose()
