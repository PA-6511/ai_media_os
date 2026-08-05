from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "content_generation_gate_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "content_generation_gate_request.example.json"
)
CONTRACT = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "content_generation_contract.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_i_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_i_"
    "content_generation_gate_report.md"
)
RESERVED_OUTPUT = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
BUILDER = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_i.py"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_i_blocked.py"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def module():
    spec = importlib.util.spec_from_file_location(
        "recovery_i_builder",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None

    item = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(item)
    return item


def test_policy_is_contract_fixation_only() -> None:
    policy = load(POLICY)

    assert (
        policy["operation_mode"]
        == (
            "APPROVED_CONTENT_GENERATION_"
            "CONTRACT_FIXATION_ONLY"
        )
    )
    assert (
        policy["execution_boundary"][
            "content_generation_contract_fixation_allowed"
        ]
        is True
    )
    assert (
        policy["execution_boundary"][
            "article_content_generation_allowed"
        ]
        is False
    )


def test_contract_uses_fixed_template_and_article() -> None:
    contract = load(CONTRACT)

    assert (
        contract["contract_id"]
        == (
            "FRESH_NEW_RELEASE_COMIC_"
            "CONTENT_GENERATION_V1"
        )
    )
    assert (
        contract["template_contract_id"]
        == "POST185_STANDARD_TEMPLATE_V1_FIXED"
    )
    assert contract["work_title"] == "ダークギャザリング"
    assert contract["volume_label"] == "第20巻"
    assert contract["wordpress_status"] == "draft"


def test_contract_digest_is_valid() -> None:
    contract = load(CONTRACT)
    without_digest = copy.deepcopy(
        contract
    )
    stored = without_digest.pop(
        "content_generation_contract_digest_sha256"
    )

    assert digest(without_digest) == stored


def test_advertising_disclosure_is_required() -> None:
    contract = load(CONTRACT)
    disclosure = contract[
        "advertising_disclosure"
    ]

    assert disclosure["required"] is True
    assert set(disclosure["allowed_labels"]) == {
        "PR",
        "広告",
    }
    assert disclosure["omission_allowed"] is False


def test_fabrication_is_prohibited() -> None:
    contract = load(CONTRACT)
    rules = contract["factuality_rules"]

    assert rules["verified_source_only"] is True
    assert rules["fabricated_information_allowed"] is False
    assert rules["fabricated_synopsis_allowed"] is False
    assert rules["fabricated_discount_allowed"] is False
    assert rules["fabricated_point_return_allowed"] is False


def test_dmm_recheck_is_inherited_and_pending() -> None:
    contract = load(CONTRACT)
    dmm = contract["dmm_recheck_rules"]

    assert (
        dmm[
            "latest_alias_recheck_requirement_inherited"
        ]
        is True
    )
    assert dmm["latest_alias_recheck_completed"] is False
    assert (
        dmm[
            "recheck_required_before_payload_generation"
        ]
        is True
    )
    assert (
        dmm[
            "dmm_url_rendering_before_recheck_allowed"
        ]
        is False
    )


def test_reserved_content_output_is_absent() -> None:
    assert not RESERVED_OUTPUT.exists()


def test_request_has_no_generation_or_execution() -> None:
    request = load(REQUEST)

    assert (
        request[
            "content_generation_contract_fixation_requested"
        ]
        is True
    )
    assert (
        request["article_content_generation_requested"]
        is False
    )
    assert (
        request["content_output_creation_requested"]
        is False
    )
    assert (
        request["fresh_payload_creation_requested"]
        is False
    )
    assert request["payload_binding_requested"] is False
    assert (
        request[
            "production_category_id_payload_injection_requested"
        ]
        is False
    )
    assert request["network_connection_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["execution_requested"] is False


def test_content_generation_request_is_rejected() -> None:
    builder = module()
    request = copy.deepcopy(
        load(REQUEST)
    )
    request[
        "article_content_generation_requested"
    ] = True

    try:
        builder.validate_request_and_sources(
            request,
            load(POLICY),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "content generation request was accepted"
        )


def test_blocked_runner_returns_three() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    result = json.loads(
        completed.stderr
    )

    assert (
        result["content_generation_contract_fixed"]
        is True
    )
    assert result["article_content_generated"] is False
    assert result["content_output_created"] is False
    assert result["fresh_payload_created"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_ready_for_offline_generation_approval_only() -> None:
    result = load(RESULT)

    assert (
        result["status"]
        == (
            "PASS_FRESH_ARTICLE_CONTENT_GENERATION_"
            "CONTRACT_FIXED_NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
        )
    )
    assert result["content_output_exists"] is False
    assert result["article_content_generated"] is False
    assert result["fresh_payload_created"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result[
            "ready_for_offline_article_content_generation_approval"
        ]
        is True
    )
    assert (
        result["ready_for_article_content_generation"]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_safety_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert (
        "Advertising disclosure required: `true`"
        in report
    )
    assert (
        "Fabricated information allowed: `false`"
        in report
    )
    assert (
        "DMM recheck completed: `false`"
        in report
    )
    assert "Content output exists: `false`" in report
    assert "Article content generated: `false`" in report
    assert "Fresh payload created: `false`" in report
    assert "Category ID injected: `false`" in report
    assert "WordPress write performed: `false`" in report
