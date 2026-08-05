from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.build_x_r11_local_wordpress_draft_template_contract import (
    LocalTemplateContractError,
    load_json,
    validate_template_contract,
)


REPOSITORY_ROOT = Path(
    __file__
).resolve().parents[1]

CONTRACT_PATH = (
    REPOSITORY_ROOT
    / "config"
    / "x_r11_local_wordpress_draft_template_contract.json"
)

TEMPLATE_PATH = (
    REPOSITORY_ROOT
    / "templates"
    / "wordpress"
    / "x_r11_new_release_draft_v1.html"
)


def load_valid_values() -> tuple[
    dict,
    str,
]:
    contract = load_json(
        CONTRACT_PATH
    )

    template_html = (
        TEMPLATE_PATH.read_text(
            encoding="utf-8"
        )
    )

    return contract, template_html


def test_repository_local_template_contract_is_valid() -> None:
    contract, template_html = (
        load_valid_values()
    )

    result = validate_template_contract(
        contract,
        template_html,
    )

    assert result[
        "contract_validation_passed"
    ] is True

    assert result[
        "wordpress_category_id"
    ] == 43

    assert result[
        "maximum_post_create_count"
    ] == 1

    assert result[
        "fixed_price_embedded"
    ] is False


def test_missing_required_marker_is_rejected() -> None:
    contract, template_html = (
        load_valid_values()
    )

    tampered = template_html.replace(
        "ebook-pr-disclosure",
        "removed-pr-marker",
    )

    with pytest.raises(
        LocalTemplateContractError,
        match="markers are missing",
    ):
        validate_template_contract(
            contract,
            tampered,
        )


def test_unknown_placeholder_is_rejected() -> None:
    contract, template_html = (
        load_valid_values()
    )

    tampered = (
        template_html
        + "\n<p>{{unexpected_value}}</p>\n"
    )

    with pytest.raises(
        LocalTemplateContractError,
        match="unknown placeholders",
    ):
        validate_template_contract(
            contract,
            tampered,
        )


def test_forbidden_script_tag_is_rejected() -> None:
    contract, template_html = (
        load_valid_values()
    )

    tampered = (
        template_html
        + "\n<script>alert(1)</script>\n"
    )

    with pytest.raises(
        LocalTemplateContractError,
        match="forbidden HTML tags",
    ):
        validate_template_contract(
            contract,
            tampered,
        )


def test_wrong_category_contract_is_rejected() -> None:
    contract, template_html = (
        load_valid_values()
    )

    tampered_contract = copy.deepcopy(
        contract
    )

    tampered_contract[
        "wordpress_category"
    ]["id"] = 990001

    with pytest.raises(
        LocalTemplateContractError,
        match="category contract mismatch",
    ):
        validate_template_contract(
            tampered_contract,
            template_html,
        )
