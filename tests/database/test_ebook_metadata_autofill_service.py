from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType
import urllib.request

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import CatalogEditHistory, EbookItem, StoreOffer
from app.db.repositories.ebook_metadata_autofill_repository import (
    EbookMetadataAutofillContext,
    VerifiedMetadataRecord,
)
from app.services.ebook_metadata_autofill_service import (
    AUDIT_BOOLEAN_FIELDS,
    EbookMetadataAutofillError,
    EbookMetadataAutofillService,
    build_evidence,
    build_metadata_autofill_preview,
    extract_volume_candidates,
    normalize_authors,
    normalize_publisher,
    normalize_volume_label,
    write_evidence,
)


def _assert_audit_booleans(
    evidence: dict[str, object],
    expected: dict[str, bool],
) -> None:
    assert set(AUDIT_BOOLEAN_FIELDS).issubset(evidence)
    assert {
        field_name: evidence[field_name]
        for field_name in AUDIT_BOOLEAN_FIELDS
    } == expected
    assert all(
        type(evidence[field_name]) is bool
        for field_name in AUDIT_BOOLEAN_FIELDS
    )


def _context(
    *,
    title: str = "作品",
    volume_label: str | None = None,
    author_name: str | None = None,
    publisher_name: str | None = None,
    records: tuple[VerifiedMetadataRecord, ...] = (),
    human_reviewed_fields: frozenset[str] = frozenset(),
) -> EbookMetadataAutofillContext:
    return EbookMetadataAutofillContext(
        ebook_item_id="target",
        title=title,
        volume_label=volume_label,
        author_name=author_name,
        publisher_name=publisher_name,
        human_reviewed_fields=human_reviewed_fields,
        verified_records=records,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("作品 15", ("第15巻",)),
        ("第15巻", ("第15巻",)),
        ("15巻", ("第15巻",)),
        ("Vol.15", ("第15巻",)),
        ("Volume 15", ("第15巻",)),
        ("作品 (15)", ("第15巻",)),
        ("作品 （15）", ("第15巻",)),
        ("合本版 3", ("第3巻",)),
        ("作品 10年分", ()),
        ("作品 2026年", ()),
        ("作品 50%オフ", ()),
        ("作品 100話", ()),
        ("作品 ISBN 1234", ()),
        ("作品 商品ID 123", ()),
        ("作品 価格 500", ()),
        ("作品 12 サブタイトル", ()),
    ],
)
def test_extract_volume_candidates(value: str, expected: tuple[str, ...]) -> None:
    assert extract_volume_candidates(value) == expected


@pytest.mark.parametrize(
    "value",
    ["020", "０２０", "0020", "００２０", "020巻", "第020巻"],
)
def test_volume_normalization_removes_positive_leading_zeroes(value: str) -> None:
    assert normalize_volume_label(value) == "第20巻"


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "00",
        "０",
        "０００",
        "〇",
        "零",
        "⓪",
        "第0巻",
        "第〇巻",
        "第零巻",
    ],
)
def test_zero_volume_values_are_preserved_without_auto_conversion(
    value: str,
) -> None:
    result = build_metadata_autofill_preview(
        _context(volume_label=value)
    ).result_for("volume_label")

    assert normalize_volume_label(value) is None
    assert result.before == value
    assert result.status == "EXISTING_VALUE_PRESERVED"
    assert result.apply_allowed is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Ⅰ", "第1巻"),
        ("Ⅱ", "第2巻"),
        ("Ⅳ", "第4巻"),
        ("Ⅹ", "第10巻"),
        ("ⅩⅩ", "第20巻"),
        ("第Ⅳ巻", "第4巻"),
        ("IV", "第4巻"),
        ("XX", "第20巻"),
        ("第XX巻", "第20巻"),
        ("①", "第1巻"),
        ("②", "第2巻"),
        ("⑳", "第20巻"),
        ("第⑳巻", "第20巻"),
        ("一", "第1巻"),
        ("二", "第2巻"),
        ("十", "第10巻"),
        ("十一", "第11巻"),
        ("二十", "第20巻"),
        ("二十一", "第21巻"),
        ("百二十", "第120巻"),
        ("第二十巻", "第20巻"),
        ("二十巻", "第20巻"),
        ("〇二〇", "第20巻"),
        ("第020巻", "第20巻"),
    ],
)
def test_volume_normalization_supports_numeral_variants(
    value: str,
    expected: str,
) -> None:
    assert normalize_volume_label(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "上巻",
        "下巻",
        "前編",
        "後編",
        "合本版",
        "番外編",
        "通常の文字列",
        "IIII",
        "VX",
        "IC",
        "ROMAN",
    ],
)
def test_volume_normalization_rejects_non_numeric_labels_and_invalid_roman(
    value: str,
) -> None:
    assert normalize_volume_label(value) is None


def test_numeral_variant_normalization_is_limited_to_volume_label() -> None:
    record = VerifiedMetadataRecord(
        source_type="RAKUTEN_KOBO",
        confidence="VERIFIED",
        volume_label="Ⅳ",
        author_name="Author IV",
        publisher_name="Publisher ①",
    )
    preview = build_metadata_autofill_preview(
        _context(title="Title IV", records=(record,))
    )

    assert preview.result_for("volume_label").candidate == "第4巻"
    assert preview.result_for("author_name").candidate == "Author IV"
    assert preview.result_for("publisher_name").candidate == "Publisher ①"


def test_title_suffix_ignores_subtitle_year_and_finds_final_volume() -> None:
    assert extract_volume_candidates(
        "冷酷騎士の溺愛指導 -10年分の甘い愛にとろけ中- 15"
    ) == ("第15巻",)


def test_multiple_volume_candidates_require_review() -> None:
    preview = build_metadata_autofill_preview(
        _context(title="作品 Vol.14 特装版 15")
    )
    result = preview.result_for("volume_label")
    assert result.status == "CONFLICT"
    assert result.conflict_values == ("第14巻", "第15巻")
    assert preview.metadata_status == "METADATA_REVIEW_REQUIRED"


def test_author_and_publisher_normalization_preserve_order_roles_and_names() -> None:
    assert normalize_authors(
        " 宮藤華  | 原作：佐藤  太郎 |宮藤華|作画：山田花子 "
    ) == "宮藤華|原作：佐藤 太郎|作画：山田花子"
    assert normalize_publisher("  A&amp;B   出版  ") == "A&B 出版"


def test_verified_kobo_candidates_are_ready_and_deduplicated() -> None:
    record = VerifiedMetadataRecord(
        source_type="RAKUTEN_KOBO",
        confidence="VERIFIED",
        volume_label="15巻",
        author_name=" 著者A |著者B|著者A ",
        publisher_name=" 出版社 &amp; Co. ",
    )
    preview = build_metadata_autofill_preview(
        _context(title="作品 15", records=(record,))
    )
    assert preview.metadata_status == "METADATA_AUTOFILL_READY"
    assert preview.result_for("volume_label").candidate == "第15巻"
    assert preview.result_for("author_name").candidate == "著者A|著者B"
    assert preview.result_for("publisher_name").candidate == "出版社 & Co."


def test_matching_existing_values_are_recorded_as_already_matched() -> None:
    record = VerifiedMetadataRecord(
        source_type="RAKUTEN_KOBO",
        confidence="VERIFIED",
        volume_label="15巻",
        author_name="著者A | 著者B",
        publisher_name="出版社",
    )
    preview = build_metadata_autofill_preview(
        _context(
            title="作品 15",
            volume_label="第15巻",
            author_name="著者A|著者B",
            publisher_name="出版社",
            records=(record,),
        )
    )
    assert {
        result.status for result in preview.field_results
    } == {"ALREADY_MATCHED"}
    assert preview.metadata_status == "METADATA_ALREADY_COMPLETE"
    assert preview.apply_possible is False


@pytest.mark.parametrize(
    ("field_name", "reason"),
    [
        ("author_name", "AUTHOR_CONFLICT"),
        ("publisher_name", "PUBLISHER_CONFLICT"),
    ],
)
def test_verified_source_conflict_is_not_applied(
    field_name: str, reason: str
) -> None:
    first = VerifiedMetadataRecord(
        source_type="RAKUTEN_KOBO",
        confidence="VERIFIED",
        volume_label=None,
        author_name="著者A",
        publisher_name="出版社A",
    )
    second = VerifiedMetadataRecord(
        source_type="VERIFIED_STORE:DMM",
        confidence="VERIFIED",
        volume_label=None,
        author_name="著者B",
        publisher_name="出版社B",
    )
    preview = build_metadata_autofill_preview(
        _context(records=(first, second))
    )
    result = preview.result_for(field_name)
    assert result.status == "CONFLICT"
    assert result.reason == reason
    assert result.apply_allowed is False
    assert preview.metadata_status == "METADATA_REVIEW_REQUIRED"


def test_existing_values_and_human_review_history_are_never_overwritten() -> None:
    record = VerifiedMetadataRecord(
        source_type="RAKUTEN_KOBO",
        confidence="VERIFIED",
        volume_label="第2巻",
        author_name="新著者",
        publisher_name="新出版社",
    )
    preview = build_metadata_autofill_preview(
        _context(
            title="作品 2",
            volume_label="第1巻",
            author_name="旧著者",
            records=(record,),
            human_reviewed_fields=frozenset({"publisher_name"}),
        )
    )
    assert preview.result_for("volume_label").status == "EXISTING_VALUE_PRESERVED"
    assert preview.result_for("volume_label").reason == "VOLUME_CONFLICT"
    assert preview.result_for("author_name").status == "EXISTING_VALUE_PRESERVED"
    assert preview.result_for("publisher_name").status == "HUMAN_REVIEW_PROTECTED"
    assert not any(result.apply_allowed for result in preview.field_results)


def test_nonempty_human_reviewed_values_are_complete_not_unresolved() -> None:
    preview = build_metadata_autofill_preview(
        _context(
            title="作品",
            volume_label="第1巻",
            author_name="人間確認済み著者",
            publisher_name="人間確認済み出版社",
            human_reviewed_fields=frozenset(
                {"volume_label", "author_name", "publisher_name"}
            ),
        )
    )
    assert preview.metadata_status == "METADATA_ALREADY_COMPLETE"
    assert {
        result.status for result in preview.field_results
    } == {"HUMAN_REVIEW_PROTECTED"}


def test_missing_verified_author_and_publisher_require_review() -> None:
    preview = build_metadata_autofill_preview(_context(title="作品 3"))
    assert preview.result_for("volume_label").status == "READY"
    assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
    assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"
    assert preview.metadata_status == "METADATA_REVIEW_REQUIRED"


def _engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'autofill.db'}")
    Base.metadata.create_all(engine)
    return engine


def _add_target_and_verified_peer(session: Session) -> tuple[EbookItem, EbookItem]:
    target = EbookItem(
        source_name="new_release_catalog",
        source_item_id="target",
        isbn="9781234567897",
        title="対象作品 15",
        review_status="APPROVED",
        publish_ready=True,
    )
    peer = EbookItem(
        source_name="rakuten_kobo",
        source_item_id="kobo",
        isbn="9781234567897",
        title="対象作品 第15巻",
        volume_label="第15巻",
        author_name="著者A|著者B",
        publisher_name="出版社",
    )
    unrelated = EbookItem(
        source_name="rakuten_kobo",
        source_item_id="unrelated",
        isbn="9780306406157",
        title="別作品 9",
    )
    session.add_all((target, peer, unrelated))
    session.flush()
    session.add(
        StoreOffer(
            ebook_item_id=peer.id,
            store_name="rakuten_kobo",
            store_item_id="RK-15",
            source_row_sha256="a" * 64,
            verified_at=datetime.now(timezone.utc),
            verification_method="RAKUTEN_KOBO_API_RESPONSE",
        )
    )
    session.commit()
    return target, unrelated


def test_apply_updates_only_target_and_audits_without_wordpress_changes(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, unrelated = _add_target_and_verified_peer(session)
        target_id = target.id
        unrelated_id = unrelated.id
        service = EbookMetadataAutofillService(session)
        preview = service.preview(target_id)
        assert preview.apply_possible is True
        result = service.apply(
            ebook_item_id=target_id,
            confirmed_fingerprint=preview.fingerprint,
        )
        session.commit()
        assert result.metadata_status == "METADATA_AUTOFILL_APPLIED"

    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        unrelated = session.get(EbookItem, unrelated_id)
        assert target is not None and unrelated is not None
        assert (target.volume_label, target.author_name, target.publisher_name) == (
            "第15巻",
            "著者A|著者B",
            "出版社",
        )
        assert target.wordpress_status == "NOT_CREATED"
        assert target.wordpress_post_id is None
        assert target.review_status == "NOT_REVIEWED"
        assert target.publish_ready is False
        assert unrelated.volume_label is None
        history = session.scalars(
            select(CatalogEditHistory).where(
                CatalogEditHistory.ebook_item_id == target_id
            )
        ).all()
        assert {row.field_name for row in history} == {
            "volume_label",
            "author_name",
            "publisher_name",
            "review_status",
            "publish_ready",
        }
        history_by_field = {row.field_name: row for row in history}
        review_history = history_by_field["review_status"]
        assert review_history.before_value == "APPROVED"
        assert review_history.after_value == "NOT_REVIEWED"
        assert review_history.change_reason == (
            "metadata changed; review reset to safe state"
        )
        publish_history = history_by_field["publish_ready"]
        assert publish_history.before_value == "True"
        assert publish_history.after_value == "False"
        assert publish_history.change_reason == (
            "metadata changed; publish readiness reset"
        )


def test_volume_only_apply_preserves_other_fields_and_uses_no_external_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_external_call(*args: object, **kwargs: object) -> None:
        pytest.fail("external communication or WordPress client construction")

    monkeypatch.setattr(socket, "socket", forbidden_external_call)
    monkeypatch.setattr(socket, "create_connection", forbidden_external_call)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_external_call)
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        forbidden_external_call,
    )

    engine = _engine(tmp_path)
    with Session(engine) as session:
        target = EbookItem(
            source_name="new_release_catalog",
            source_item_id="one-piece-volume-only",
            title="ONE PIECE モノクロ版 115",
            author_name="尾田栄一郎",
            publisher_name="集英社",
            wordpress_status="DRAFT",
            wordpress_post_id=None,
            review_status="NOT_REVIEWED",
            publish_ready=False,
        )
        session.add(target)
        session.commit()
        target_id = target.id
        unchanged_field_names = {
            column.name for column in EbookItem.__table__.columns
        } - {"volume_label", "updated_at"}
        before = {
            field_name: getattr(target, field_name)
            for field_name in unchanged_field_names
        }

        service = EbookMetadataAutofillService(session)
        preview = service.preview(target_id)
        assert preview.result_for("volume_label").candidate == "第115巻"
        result = service.apply(
            ebook_item_id=target_id,
            confirmed_fingerprint=preview.fingerprint,
        )
        session.commit()
        assert result.operation == "APPLY"

    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        after = {
            field_name: getattr(target, field_name)
            for field_name in unchanged_field_names
        }
        assert target.volume_label == "第115巻"
        assert after == before
        assert target.wordpress_status == "DRAFT"
        assert target.wordpress_post_id is None
        history = session.scalars(
            select(CatalogEditHistory).where(
                CatalogEditHistory.ebook_item_id == target_id
            )
        ).all()
        assert [row.field_name for row in history] == ["volume_label"]


def test_preview_and_bad_confirmation_do_not_update_database(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        target_id = target.id
        service = EbookMetadataAutofillService(session)
        service.preview(target_id)
        with pytest.raises(EbookMetadataAutofillError, match="preview_changed"):
            service.apply(
                ebook_item_id=target_id,
                confirmed_fingerprint="wrong",
            )
        assert service.database_update_attempted is False
        session.rollback()
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        assert target.volume_label is None
        assert target.author_name is None
        assert target.publisher_name is None


def test_database_attempt_flag_is_true_when_repository_update_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        service = EbookMetadataAutofillService(session)
        preview = service.preview(target.id)

        def fail_update(**kwargs: object) -> tuple[str, ...]:
            raise ValueError("forced_update_failure")

        monkeypatch.setattr(
            service.repository,
            "apply_empty_fields",
            fail_update,
        )
        with pytest.raises(
            EbookMetadataAutofillError,
            match="forced_update_failure",
        ):
            service.apply(
                ebook_item_id=target.id,
                confirmed_fingerprint=preview.fingerprint,
            )
        assert service.database_update_attempted is True


def test_human_history_protects_even_an_empty_field(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        session.add(
            CatalogEditHistory(
                ebook_item_id=target.id,
                field_name="author_name",
                before_value="人間入力",
                after_value=None,
                change_reason="意図的に空欄へ戻した",
                changed_by="human:local_gui",
            )
        )
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "HUMAN_REVIEW_PROTECTED"
        assert preview.result_for("author_name").apply_allowed is False


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("source_row_sha256", None),
        ("source_row_sha256", "a" * 63),
        ("source_row_sha256", "a" * 65),
        ("source_row_sha256", "g" * 64),
        ("verified_at", None),
        ("verification_method", None),
        ("verification_method", ""),
        ("verification_method", "UNKNOWN"),
        ("verification_method", "MANUAL"),
        ("verification_method", "RAKUTEN_KOBO"),
        ("verification_method", "rakuten_kobo_api_response"),
        ("verification_method", "RAKUTEN_KOBO_API_RESPONSE_FAKE"),
    ],
)
def test_incomplete_kobo_verification_is_not_a_metadata_source(
    tmp_path: Path, field_name: str, invalid_value: object
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        peer_offer = session.scalar(
            select(StoreOffer).where(StoreOffer.store_item_id == "RK-15")
        )
        setattr(peer_offer, field_name, invalid_value)
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
        assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"


def test_non_kobo_offer_is_not_a_metadata_source(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        peer_offer = session.scalar(
            select(StoreOffer).where(StoreOffer.store_item_id == "RK-15")
        )
        assert peer_offer is not None
        peer_offer.store_name = "amazon"
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
        assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"


def test_valid_sha256_and_trusted_method_are_a_metadata_source(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "READY"
        assert preview.result_for("publisher_name").status == "READY"


def test_normalized_matching_isbn_is_a_metadata_source(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        target.isbn = " 978-1-2345-6789-7 "
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "READY"
        assert preview.result_for("publisher_name").status == "READY"


def test_verified_kobo_with_different_isbn_is_not_a_metadata_source(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        peer = session.scalar(
            select(EbookItem).where(EbookItem.source_item_id == "kobo")
        )
        assert peer is not None
        peer.isbn = "9780306406157"
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
        assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"


@pytest.mark.parametrize("side", ["source", "target"])
def test_invalid_isbn_is_not_a_metadata_source(
    tmp_path: Path,
    side: str,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        peer = session.scalar(
            select(EbookItem).where(EbookItem.source_item_id == "kobo")
        )
        assert peer is not None
        if side == "source":
            peer.isbn = "9781234567890"
        else:
            target.isbn = "9781234567890"
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
        assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"


def test_matching_item_number_without_isbn_is_not_a_metadata_source(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        peer = session.scalar(
            select(EbookItem).where(EbookItem.source_item_id == "kobo")
        )
        assert peer is not None
        target.isbn = None
        peer.isbn = None
        target.source_item_id = "MATCHING-ITEM-NUMBER"
        peer.source_item_id = "MATCHING-ITEM-NUMBER"
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
        assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"


@pytest.mark.parametrize("same_values", [False, True])
def test_same_isbn_verified_kobo_conflicts_are_reviewed_but_duplicates_are_not(
    tmp_path: Path, same_values: bool
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        second = EbookItem(
            source_name="rakuten_kobo",
            source_item_id="kobo-second",
            isbn=target.isbn,
            title="対象作品 第15巻",
            author_name="著者A|著者B" if same_values else "競合著者",
            publisher_name="出版社" if same_values else "競合出版社",
        )
        session.add(second)
        session.flush()
        session.add(
            StoreOffer(
                ebook_item_id=second.id,
                store_name="rakuten_kobo",
                store_item_id="RK-15-SECOND",
                source_row_sha256="b" * 64,
                verified_at=datetime.now(timezone.utc),
                verification_method="RAKUTEN_KOBO_API_RESPONSE",
            )
        )
        session.commit()
        preview = EbookMetadataAutofillService(session).preview(target.id)
        author = preview.result_for("author_name")
        publisher = preview.result_for("publisher_name")
        if same_values:
            assert author.status == "READY"
            assert publisher.status == "READY"
        else:
            assert author.status == "CONFLICT"
            assert author.reason == "AUTHOR_CONFLICT"
            assert publisher.status == "CONFLICT"
            assert publisher.reason == "PUBLISHER_CONFLICT"
            assert preview.metadata_status == "METADATA_REVIEW_REQUIRED"
            assert author.apply_allowed is False
            assert publisher.apply_allowed is False


def test_preview_evidence_persists_all_audit_booleans_as_false(
    tmp_path: Path,
) -> None:
    preview = build_metadata_autofill_preview(_context(title="作品 4"))
    evidence = build_evidence(
        preview,
        database_update_attempted=False,
        database_update_succeeded=False,
        changed_by="system:test",
        timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    path = write_evidence(evidence, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "affiliate" not in text.lower()
    assert "credential" not in text.lower()
    assert "password" not in text.lower()
    persisted = json.loads(text)
    _assert_audit_booleans(
        persisted,
        {
            "external_communication_attempted": False,
            "wordpress_update_attempted": False,
            "database_update_attempted": False,
            "database_update_succeeded": False,
        },
    )


def test_apply_success_evidence_persists_expected_audit_booleans(
    tmp_path: Path,
) -> None:
    applied = replace(
        build_metadata_autofill_preview(_context(title="作品 4")),
        operation="APPLY",
        dry_run=False,
    )
    evidence = build_evidence(
        applied,
        database_update_attempted=True,
        database_update_succeeded=True,
        changed_by="system:test",
        timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    persisted = json.loads(
        write_evidence(evidence, tmp_path).read_text(encoding="utf-8")
    )
    _assert_audit_booleans(
        persisted,
        {
            "external_communication_attempted": False,
            "wordpress_update_attempted": False,
            "database_update_attempted": True,
            "database_update_succeeded": True,
        },
    )


def test_cli_apply_failure_persists_attempt_without_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import ebook_metadata_autofill_service as service_module
    from scripts import run_ebook_metadata_autofill as runner

    preview = build_metadata_autofill_preview(_context(title="作品 4"))

    class FakeSession:
        def __enter__(self) -> FakeSession:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def commit(self) -> None:
            pytest.fail("commit must not run after a failed apply")

    class FailingService:
        def __init__(self, session: object) -> None:
            self.database_update_attempted = False

        def preview(self, ebook_item_id: str) -> object:
            return preview

        def apply(self, **kwargs: object) -> object:
            self.database_update_attempted = True
            raise EbookMetadataAutofillError("forced_update_failure")

    fake_session_module = ModuleType("app.db.session")
    fake_session_module.SessionLocal = FakeSession  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.db.session", fake_session_module)
    monkeypatch.setattr(
        service_module,
        "EbookMetadataAutofillService",
        FailingService,
    )

    with pytest.raises(EbookMetadataAutofillError, match="forced_update_failure"):
        runner.main(
            [
                "--ebook-item-id",
                preview.ebook_item_id,
                "--execute",
                "--confirm-ebook-item-id",
                preview.ebook_item_id,
                "--evidence-dir",
                str(tmp_path),
            ]
        )

    evidence_paths = list(tmp_path.glob("*_apply.json"))
    assert len(evidence_paths) == 1
    persisted = json.loads(evidence_paths[0].read_text(encoding="utf-8"))
    _assert_audit_booleans(
        persisted,
        {
            "external_communication_attempted": False,
            "wordpress_update_attempted": False,
            "database_update_attempted": True,
            "database_update_succeeded": False,
        },
    )


@pytest.mark.parametrize(
    ("database_update_attempted", "database_update_succeeded"),
    [
        (None, False),
        ("false", False),
        (False, None),
        (False, "false"),
    ],
)
def test_build_evidence_rejects_none_and_string_audit_values(
    database_update_attempted: object,
    database_update_succeeded: object,
) -> None:
    preview = build_metadata_autofill_preview(_context(title="作品 4"))
    with pytest.raises(EbookMetadataAutofillError, match="explicit boolean"):
        build_evidence(
            preview,
            database_update_attempted=database_update_attempted,  # type: ignore[arg-type]
            database_update_succeeded=database_update_succeeded,  # type: ignore[arg-type]
            changed_by="system:test",
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("external_communication_attempted", None),
        ("wordpress_update_attempted", "false"),
        ("database_update_attempted", None),
        ("database_update_succeeded", "false"),
    ],
)
def test_write_evidence_rejects_invalid_audit_values(
    tmp_path: Path,
    field_name: str,
    invalid_value: object,
) -> None:
    preview = build_metadata_autofill_preview(_context(title="作品 4"))
    evidence = build_evidence(
        preview,
        database_update_attempted=False,
        database_update_succeeded=False,
        changed_by="system:test",
    )
    evidence[field_name] = invalid_value
    with pytest.raises(EbookMetadataAutofillError, match="explicit boolean"):
        write_evidence(evidence, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_write_evidence_rejects_a_missing_audit_field(tmp_path: Path) -> None:
    preview = build_metadata_autofill_preview(_context(title="作品 4"))
    evidence = build_evidence(
        preview,
        database_update_attempted=False,
        database_update_succeeded=False,
        changed_by="system:test",
    )
    del evidence["external_communication_attempted"]
    with pytest.raises(
        EbookMetadataAutofillError,
        match="missing required evidence field",
    ):
        write_evidence(evidence, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_cli_dry_run_is_read_only_and_confirm_mismatch_stops_early(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target, _ = _add_target_and_verified_peer(session)
        target_id = target.id
    database_path = tmp_path / "autofill.db"
    evidence_dir = tmp_path / "evidence"
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_BACKEND": "sqlite",
            "DATABASE_URL": f"sqlite:///{database_path}",
            "AI_MEDIA_OS_TESTING": "1",
        }
    )
    command = [
        sys.executable,
        "scripts/run_ebook_metadata_autofill.py",
        "--ebook-item-id",
        target_id,
        "--evidence-dir",
        str(evidence_dir),
    ]
    dry_run = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert dry_run.returncode == 0, dry_run.stderr
    output = json.loads(dry_run.stdout)
    assert output["dry_run"] is True
    preview_expected = {
        "external_communication_attempted": False,
        "wordpress_update_attempted": False,
        "database_update_attempted": False,
        "database_update_succeeded": False,
    }
    _assert_audit_booleans(output, preview_expected)
    persisted_preview = json.loads(
        Path(output["evidence_path"]).read_text(encoding="utf-8")
    )
    _assert_audit_booleans(persisted_preview, preview_expected)
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None and target.volume_label is None

    execute = subprocess.run(
        command
        + [
            "--execute",
            "--confirm-ebook-item-id",
            target_id,
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert execute.returncode == 0, execute.stderr
    execute_output = json.loads(execute.stdout)
    assert execute_output["operation"] == "APPLY"
    assert execute_output["dry_run"] is False
    apply_expected = {
        "external_communication_attempted": False,
        "wordpress_update_attempted": False,
        "database_update_attempted": True,
        "database_update_succeeded": True,
    }
    _assert_audit_booleans(execute_output, apply_expected)
    persisted_apply = json.loads(
        Path(execute_output["evidence_path"]).read_text(encoding="utf-8")
    )
    _assert_audit_booleans(persisted_apply, apply_expected)
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        assert (target.volume_label, target.author_name, target.publisher_name) == (
            "第15巻",
            "著者A|著者B",
            "出版社",
        )
        assert target.wordpress_status == "NOT_CREATED"
        assert target.wordpress_post_id is None
        history_count_before_mismatch = len(
            session.scalars(
                select(CatalogEditHistory).where(
                    CatalogEditHistory.ebook_item_id == target_id
                )
            ).all()
        )

    mismatch = subprocess.run(
        command
        + [
            "--execute",
            "--confirm-ebook-item-id",
            "different-id",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert mismatch.returncode != 0
    assert "must exactly match" in mismatch.stderr
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None and target.volume_label == "第15巻"
        assert len(
            session.scalars(
                select(CatalogEditHistory).where(
                    CatalogEditHistory.ebook_item_id == target_id
                )
            ).all()
        ) == history_count_before_mismatch
