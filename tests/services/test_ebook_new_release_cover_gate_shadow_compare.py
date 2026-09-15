from __future__ import annotations

from dataclasses import replace

import pytest

from test_ebook_new_release_autonomy_consumer import autonomy_context, expected

try:
    from app.services.ebook_new_release_cover_gate_shadow_compare import (
        compare_legacy_cover_gate_to_context as _compare,
        evaluate_cover_gate_image_url as _evaluate,
    )
except ModuleNotFoundError:
    _compare = None
    _evaluate = None


def compare(*args, **kwargs):
    if _compare is None:
        pytest.fail("New Release Cover Gate Shadow Comparator has not been implemented")
    return _compare(*args, **kwargs)


def evaluate(*args, **kwargs):
    if _evaluate is None:
        pytest.fail("New Release Cover Gate predicate has not been implemented")
    return _evaluate(*args, **kwargs)


def context_with_url(url):
    context = autonomy_context()
    return replace(context, display_cover=replace(context.display_cover, url=url))


def test_https_legacy_and_context_match_pass():
    result = compare(expected(), autonomy_context())

    assert result.status == "MATCH"
    assert result.legacy_gate.status == "PASS"
    assert result.context_gate.status == "PASS"
    assert result.differences == ()


def test_missing_cover_matches_block_after_existing_consumer_projection():
    legacy = expected(cover_url=None)
    result = compare(legacy, context_with_url(None))

    assert result.status == "MATCH"
    assert result.legacy_gate.status == "BLOCK"
    assert result.context_gate.status == "BLOCK"
    assert result.differences == ()


def test_placeholder_urls_use_the_existing_shell_markers():
    url = "https://images.example/no-image-placeholder.jpg"
    result = compare({**expected(), "image_url": url}, context_with_url(url))

    assert result.status == "MATCH"
    assert result.legacy_gate.status == "BLOCK"
    assert result.context_gate.status == "BLOCK"


def test_non_https_urls_match_block():
    url = "http://images.example/cover.jpg"
    result = compare({**expected(), "image_url": url}, context_with_url(url))

    assert result.status == "MATCH"
    assert result.legacy_gate.status == "BLOCK"
    assert result.context_gate.status == "BLOCK"


def test_different_urls_are_a_mismatch_even_when_both_pass():
    result = compare(expected(), context_with_url("https://images.example/other.jpg"))

    assert result.status == "MISMATCH"
    assert [(item.field, item.legacy, item.context) for item in result.differences] == [
        ("image_url", expected()["image_url"], "https://images.example/other.jpg")
    ]


def test_different_gate_decisions_are_a_mismatch():
    result = compare(expected(), context_with_url(None))

    assert result.status == "MISMATCH"
    assert [item.field for item in result.differences] == ["image_url", "gate.status"]


@pytest.mark.parametrize("legacy,context", [
    (None, autonomy_context()),
    ({}, autonomy_context()),
    ({**expected(), "item_id": ""}, autonomy_context()),
    (expected(), None),
    (expected(), replace(autonomy_context(), display_cover=None)),
])
def test_incomplete_inputs_are_not_comparable(legacy, context):
    result = compare(legacy, context)

    assert result.status == "NOT_COMPARABLE"
    assert result.differences == ()


@pytest.mark.parametrize("url,status", [
    ("https://images.example/cover.jpg", "PASS"),
    ("", "BLOCK"),
    ("https://images.example/noimage.jpg", "BLOCK"),
    ("http://images.example/cover.jpg", "BLOCK"),
])
def test_predicate_matches_existing_gate_semantics(url, status):
    assert evaluate(url).status == status
