from copy import deepcopy

import pytest

from test_ebook_new_release_autonomy_consumer import autonomy_context, expected

try:
    from app.services.ebook_new_release_autonomy_shadow_compare import (
        compare_legacy_new_release_item_to_context as _compare,
    )
except ModuleNotFoundError:
    _compare = None


def compare(*args, **kwargs):
    if _compare is None:
        pytest.fail("New Release Autonomy Shadow Comparator has not been implemented")
    return _compare(*args, **kwargs)


def test_exact_equivalent_item_matches():
    result = compare(expected(), autonomy_context())
    assert result.status == "MATCH"
    assert result.differences == ()


@pytest.mark.parametrize("field,value", [
    ("item_id", "other"),
    ("title", "別作品"),
    ("release_date", "2026-09-15"),
    ("approval_state", "PENDING"),
    ("image_url", "https://images.example.jp/other.jpg"),
])
def test_scalar_difference_is_reported(field, value):
    legacy = expected()
    legacy[field] = value
    result = compare(legacy, autonomy_context())
    assert result.status == "MISMATCH"
    assert [(difference.field, difference.legacy, difference.context)
            for difference in result.differences] == [(field, value, expected()[field])]


def test_one_store_url_difference_is_reported():
    legacy = expected()
    legacy["stores"] = deepcopy(legacy["stores"])
    legacy["stores"]["rakuten"]["url"] = "https://affiliate.example/other"
    result = compare(legacy, autonomy_context())
    assert result.status == "MISMATCH"
    assert [(difference.field, difference.legacy, difference.context)
            for difference in result.differences] == [(
                "stores.rakuten.url", "https://affiliate.example/other",
                "https://affiliate.example/r",
            )]


def test_matching_missing_cover_is_comparable():
    result = compare(expected(cover_url=None), autonomy_context(cover_url=None))
    assert result.status == "MATCH"


@pytest.mark.parametrize("legacy,context", [
    ({}, autonomy_context()),
    (expected(), None),
    ({**expected(), "item_id": ""}, autonomy_context()),
    ({**expected(), "release_date": ""}, autonomy_context()),
    ({**expected(), "approval_state": ""}, autonomy_context()),
    ({**expected(), "stores": []}, autonomy_context()),
    ({**expected(), "stores": {"kindle": {"url": "x"}}}, autonomy_context()),
])
def test_incomplete_inputs_are_not_comparable(legacy, context):
    result = compare(legacy, context)
    assert result.status == "NOT_COMPARABLE"
    assert result.differences == ()
