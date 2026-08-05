from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.services.x_draft_generation_service import (
    XDraftGenerationError,
    XDraftGenerationService,
    XDraftInput,
    author_to_hashtag,
    build_feedback_id,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/x_draft_module_contract.json"


def valid_input(**overrides: object) -> XDraftInput:
    values = {
        "ebook_item_id": "ebook-20260717-001",
        "title": "テスト作品",
        "volume_label": "第1巻",
        "release_date": "2026-07-17",
        "category": "コミック新刊",
        "author_name": "山田 太郎",
        "article_url": "https://books.example.jp/posts/test-work",
        "wordpress_draft_id": 12345,
        "wordpress_status": "DRAFT",
    }
    values.update(overrides)
    return XDraftInput(**values)


def test_generate_returns_expected_contract_values() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    result = service.generate(valid_input())

    assert result.ebook_item_id == "ebook-20260717-001"
    assert result.wordpress_draft_id == 12345
    assert result.template_id == "X_DRAFT_NEW_RELEASE_SIMPLE_V1"
    assert result.record_stage == "DRAFT_GENERATED"
    assert result.x_status == "DRAFT"
    assert result.review_status == "IN_REVIEW"
    assert result.contains_pr is True
    assert result.selected_url == (
        "https://books.example.jp/posts/test-work"
    )


def test_generated_text_uses_fixed_template() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    result = service.generate(valid_input())

    assert result.generated_text == (
        "配信開始です\n"
        "#PR #電子書籍\n"
        "『テスト作品』第1巻\n"
        "#山田太郎\n"
        "\n"
        "https://books.example.jp/posts/test-work"
    )
    assert result.character_count == len(result.generated_text)
    assert result.character_count <= 280


def test_initialize_request_matches_existing_x_fb_interface() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    result = service.generate(valid_input())
    request = result.initialize_request

    assert request["action"] == "INITIALIZE"
    assert request["feedback_id"] == result.feedback_id
    assert request["article_item_id"] == result.ebook_item_id
    assert request["wordpress_post_id"] == result.wordpress_draft_id
    assert request["template_id"] == result.template_id
    assert request["generated_text"] == result.generated_text

    assert request["article_context"] == {
        "title": "テスト作品",
        "volume_label": "第1巻",
        "release_date": "2026-07-17",
        "category": "コミック新刊",
        "author_name": "山田 太郎",
        "article_url": "https://books.example.jp/posts/test-work",
        "wordpress_status": "DRAFT",
    }

    assert request["wording_labels"] == [
        "TITLE_FIRST",
        "ARTICLE_CTA",
        "INFORMATIONAL_TONE",
        "MULTIPLE_HASHTAGS",
    ]


def test_result_is_frozen() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)
    result = service.generate(valid_input())

    with pytest.raises(FrozenInstanceError):
        result.generated_text = "変更禁止"  # type: ignore[misc]


def test_input_is_nfkc_normalized() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    result = service.generate(
        valid_input(
            title="ＴＥＳＴ作品",
            volume_label="　第１巻　",
            author_name=" 山田　太郎 ",
        )
    )

    assert "『TEST作品』第1巻" in result.generated_text
    assert "#山田太郎" in result.generated_text


@pytest.mark.parametrize(
    "release_date",
    [
        "2026/07/17",
        "2026-02-30",
        "17-07-2026",
    ],
)
def test_invalid_release_date_is_rejected(
    release_date: str,
) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="release_date must use YYYY-MM-DD",
    ):
        service.generate(
            valid_input(release_date=release_date)
        )


def test_empty_release_date_is_rejected() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="release_date must not be empty",
    ):
        service.generate(
            valid_input(release_date="")
        )


def test_empty_category_is_rejected() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="category must not be empty",
    ):
        service.generate(
            valid_input(category="")
        )


def test_author_to_hashtag_removes_spaces_and_separators() -> None:
    assert author_to_hashtag("山田 太郎") == "#山田太郎"
    assert author_to_hashtag("山田・太郎") == "#山田太郎"
    assert author_to_hashtag("#山田／太郎") == "#山田太郎"


@pytest.mark.parametrize(
    "status",
    [
        "NOT_CREATED",
        "PUBLISHED",
        "ERROR",
        "APPROVED",
    ],
)
def test_non_draft_wordpress_status_is_rejected(
    status: str,
) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="wordpress_status must be DRAFT",
    ):
        service.generate(valid_input(wordpress_status=status))


def test_empty_wordpress_status_is_rejected() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="wordpress_status must not be empty",
    ):
        service.generate(valid_input(wordpress_status=""))


@pytest.mark.parametrize(
    "draft_id",
    [0, -1, -100],
)
def test_invalid_wordpress_draft_id_is_rejected(
    draft_id: int,
) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="wordpress_draft_id must be at least 1",
    ):
        service.generate(
            valid_input(wordpress_draft_id=draft_id)
        )


@pytest.mark.parametrize(
    "draft_id",
    [True, False, "123", 1.5],
)
def test_non_integer_wordpress_draft_id_is_rejected(
    draft_id: object,
) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="wordpress_draft_id must be an integer",
    ):
        service.generate(
            valid_input(wordpress_draft_id=draft_id)
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://books.example.jp/post/1",
        "ftp://books.example.jp/post/1",
        "books.example.jp/post/1",
        "",
    ],
)
def test_non_https_url_is_rejected(url: str) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(XDraftGenerationError):
        service.generate(valid_input(article_url=url))


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/post/1",
        "https://example.org/post/1",
        "https://localhost/post/1",
        "https://books.example.jp/placeholder/post",
        "https://books.example.jp/dummy/post",
        "https://books.example.jp/sample/post",
    ],
)
def test_placeholder_url_is_rejected(url: str) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="placeholder",
    ):
        service.generate(valid_input(article_url=url))


def test_url_with_credentials_is_rejected() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="credentials",
    ):
        service.generate(
            valid_input(
                article_url=(
                    "https://user:password@books.example.jp/post/1"
                )
            )
        )


def test_text_over_280_characters_is_rejected() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="exceeds character limit",
    ):
        service.generate(
            valid_input(
                title="長" * 260,
            )
        )


def test_title_contract_maximum_is_enforced_before_rendering() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    with pytest.raises(
        XDraftGenerationError,
        match="title must be at most 500 characters",
    ):
        service.generate(
            valid_input(
                title="長" * 501,
            )
        )


def test_feedback_id_is_deterministic() -> None:
    first = build_feedback_id(
        ebook_item_id="ebook-001",
        wordpress_draft_id=123,
        template_id="X_DRAFT_NEW_RELEASE_SIMPLE_V1",
    )
    second = build_feedback_id(
        ebook_item_id="ebook-001",
        wordpress_draft_id=123,
        template_id="X_DRAFT_NEW_RELEASE_SIMPLE_V1",
    )

    assert first == second
    assert first.startswith("xdraft-ebook-001-wp123-")
    assert len(first) < 100


def test_feedback_id_changes_when_wordpress_post_changes() -> None:
    first = build_feedback_id(
        ebook_item_id="ebook-001",
        wordpress_draft_id=123,
        template_id="X_DRAFT_NEW_RELEASE_SIMPLE_V1",
    )
    second = build_feedback_id(
        ebook_item_id="ebook-001",
        wordpress_draft_id=124,
        template_id="X_DRAFT_NEW_RELEASE_SIMPLE_V1",
    )

    assert first != second


def test_feedback_id_handles_japanese_item_id() -> None:
    feedback_id = build_feedback_id(
        ebook_item_id="作品番号-第一巻",
        wordpress_draft_id=123,
        template_id="X_DRAFT_NEW_RELEASE_SIMPLE_V1",
    )

    assert feedback_id.startswith("xdraft-")
    assert all(
        char.isascii()
        for char in feedback_id
    )


def test_result_can_be_serialized_to_json() -> None:
    service = XDraftGenerationService(CONTRACT_PATH)
    result = service.generate(valid_input())

    serialized = json.dumps(
        result.to_dict(),
        ensure_ascii=False,
    )

    assert "DRAFT_GENERATED" in serialized
    assert "INITIALIZE" in serialized
    assert "テスト作品" in serialized


def test_generation_performs_no_file_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = XDraftGenerationService(CONTRACT_PATH)

    before = list(tmp_path.rglob("*"))

    monkeypatch.chdir(tmp_path)
    service.generate(valid_input())

    after = list(tmp_path.rglob("*"))

    assert before == after
