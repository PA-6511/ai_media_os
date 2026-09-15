from dataclasses import replace
from datetime import date
import builtins
import os

import pytest

from app.services.ebook_context import EbookDisplayCover, EbookStore
from test_ebook_wordpress_consumer import context_fixture

try:
    from app.services.ebook_new_release_autonomy_consumer import (
        build_new_release_autonomy_input as _build,
    )
except ModuleNotFoundError:
    _build = None


def build(*args, **kwargs):
    if _build is None:
        pytest.fail("New Release Autonomy Consumer has not been implemented")
    return _build(*args, **kwargs)


def autonomy_context(*, cover_url="https://images.example.jp/resolved.jpg"):
    context = context_fixture("AVAILABLE")
    return replace(
        context,
        release=date(2026, 9, 14),
        publication=replace(context.publication, review_status="APPROVED"),
        stores=(
            EbookStore("amazon", "a-1", "https://product.example/a",
                       "https://affiliate.example/a", "AVAILABLE"),
            EbookStore("rakuten_kobo", "r-1", "https://product.example/r",
                       "https://affiliate.example/r", "AVAILABLE"),
            EbookStore("dmm", "d-1", "https://product.example/d", None, "CHECKING"),
        ),
        display_cover=EbookDisplayCover(
            cover_url, "AMAZON", "AVAILABLE" if cover_url else "MISSING", "", 1,
        ),
    )


def expected(*, cover_url="https://images.example.jp/resolved.jpg"):
    return {
        "item_id": "db-1",
        "title": "作品 1巻",
        "release_date": "2026-09-14",
        "approval_state": "APPROVED",
        "stores": {
            "kindle": {"url": "https://affiliate.example/a"},
            "rakuten": {"url": "https://affiliate.example/r"},
            "dmm": {"url": ""},
        },
        "image_url": cover_url or "",
    }


def test_projects_legacy_compatible_minimum_facts():
    assert build(autonomy_context()) == expected()


def test_missing_display_url_remains_comparable_fact():
    assert build(autonomy_context(cover_url=None)) == expected(cover_url=None)


@pytest.mark.parametrize("context", [
    None,
    replace(autonomy_context(), identity=replace(autonomy_context().identity, id=None)),
    replace(autonomy_context(), title=""),
    replace(autonomy_context(), release=None),
    replace(autonomy_context(), publication=replace(autonomy_context().publication, review_status=None)),
    replace(autonomy_context(), display_cover=None),
])
def test_missing_required_facts_return_none(context):
    assert build(context) is None


def test_ambiguous_affiliate_order_is_not_invented():
    context = autonomy_context()
    context = replace(context, stores=context.stores + (
        EbookStore("kindle", "a-2", "https://product.example/a2",
                   "https://affiliate.example/a2", "AVAILABLE"),
    ))
    assert build(context) is None


def test_consumer_is_pure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Autonomy Consumer must remain pure")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "execute", forbidden)
    monkeypatch.setattr(Session, "commit", forbidden)
    monkeypatch.setattr(Session, "rollback", forbidden)
    assert build(autonomy_context()) == expected()
