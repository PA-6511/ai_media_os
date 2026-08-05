from __future__ import annotations

import json
from pathlib import Path

from scripts.discover_x_r11_real_source_candidates import (
    discover_real_source_candidates,
)


def run_discovery(
    tmp_path: Path,
) -> dict:
    return discover_real_source_candidates(
        search_root=tmp_path / "repo",
        output_path=(
            tmp_path
            / "output"
            / "result.json"
        ),
    )


def test_real_csv_candidate_is_found(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    (
        repo / "real.csv"
    ).write_text(
        (
            "title,release_date,"
            "rakuten_kobo_url\n"
            "実在作品 第1巻,2026-07-18,"
            "https://books.rakuten.co.jp/"
            "rb/12345678/\n"
        ),
        encoding="utf-8",
    )

    result = run_discovery(tmp_path)

    assert result[
        "unique_candidate_count"
    ] == 1
    assert result["candidates"][0][
        "title"
    ] == "実在作品 第1巻"


def test_synthetic_title_is_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    (
        repo / "test.csv"
    ).write_text(
        (
            "title,release_date,"
            "rakuten_kobo_url\n"
            "テスト作品,2026-07-18,"
            "https://books.rakuten.co.jp/"
            "rb/12345678/\n"
        ),
        encoding="utf-8",
    )

    result = run_discovery(tmp_path)

    assert result[
        "unique_candidate_count"
    ] == 0
    assert result["rejection_counts"][
        "SYNTHETIC_OR_MISSING_TITLE"
    ] == 1


def test_placeholder_url_is_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    (
        repo / "placeholder.csv"
    ).write_text(
        (
            "title,release_date,"
            "rakuten_kobo_url\n"
            "実在作品,2026-07-18,"
            "https://example.com/item/1\n"
        ),
        encoding="utf-8",
    )

    result = run_discovery(tmp_path)

    assert result[
        "unique_candidate_count"
    ] == 0
    assert result["rejection_counts"][
        "NO_VALID_RETAIL_URL"
    ] == 1


def test_nested_json_offer_is_found(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    (
        repo / "items.json"
    ).write_text(
        json.dumps(
            {
                "items": [
                    {
                        "title": (
                            "実在作品 第2巻"
                        ),
                        "release_date": (
                            "2026-07-19"
                        ),
                        "store_offers": [
                            {
                                "store": (
                                    "rakuten_kobo"
                                ),
                                "url": (
                                    "https://"
                                    "books.rakuten.co.jp/"
                                    "rb/23456789/"
                                ),
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_discovery(tmp_path)

    assert result[
        "unique_candidate_count"
    ] == 1


def test_excluded_test_directory_is_ignored(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    test_dir = repo / "tests"
    test_dir.mkdir(parents=True)

    (
        test_dir / "real.csv"
    ).write_text(
        (
            "title,release_date,"
            "rakuten_kobo_url\n"
            "実在作品,2026-07-18,"
            "https://books.rakuten.co.jp/"
            "rb/12345678/\n"
        ),
        encoding="utf-8",
    )

    result = run_discovery(tmp_path)

    assert result[
        "scanned_file_count"
    ] == 0
    assert result[
        "unique_candidate_count"
    ] == 0
