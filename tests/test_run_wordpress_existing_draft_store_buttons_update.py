from __future__ import annotations

import pytest

from app.services.wordpress_existing_draft_store_buttons_update import (
    ExistingDraftStoreButtonsUpdateError,
    TARGET_EBOOK_ITEM_ID,
)
from scripts.run_wordpress_existing_draft_store_buttons_update import (
    _resolved_targets,
    parse_args,
)


def test_cli_defaults_to_dry_run_target():
    args = parse_args([])
    ebook_item_id, post_id, confirmation = _resolved_targets(args)
    assert args.execute is False
    assert ebook_item_id == TARGET_EBOOK_ITEM_ID
    assert post_id == "207"
    assert confirmation is None


@pytest.mark.parametrize(
    "argv",
    [
        ["--execute"],
        [
            "--execute",
            "--ebook-item-id",
            TARGET_EBOOK_ITEM_ID,
            "--wordpress-post-id",
            "207",
        ],
    ],
)
def test_cli_live_requires_all_explicit_identifiers(argv):
    with pytest.raises(ExistingDraftStoreButtonsUpdateError) as exc_info:
        _resolved_targets(parse_args(argv))
    assert exc_info.value.code == "live_arguments_missing"


def test_cli_accepts_complete_explicit_live_identifiers():
    args = parse_args(
        [
            "--execute",
            "--ebook-item-id",
            TARGET_EBOOK_ITEM_ID,
            "--wordpress-post-id",
            "207",
            "--confirm-wordpress-post-id",
            "207",
        ]
    )
    assert _resolved_targets(args) == (TARGET_EBOOK_ITEM_ID, "207", "207")
