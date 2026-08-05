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
    "input_human_review_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "input_human_review_request.example.json"
)
SOURCE_INPUT = (
    ROOT
    / "exchange/inputs/new_release/fresh/"
    "new-release-comic-20260703-001.input.json"
)
REVIEW = (
    ROOT
    / "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001.human_review.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_h_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_h_"
    "human_review_report.md"
)
BUILDER = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_h.py"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_h_blocked.py"
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


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def module():
    spec = importlib.util.spec_from_file_location(
        "recovery_h_builder",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None

    item = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(item)
    return item


def test_policy_is_review_only() -> None:
    policy = load(POLICY)

    assert (
        policy["operation_mode"]
        == (
            "APPROVED_FRESH_ARTICLE_INPUT_"
            "HUMAN_REVIEW_RECORDING_ONLY"
        )
    )
    assert (
        policy["execution_boundary"][
            "human_review_recording_allowed"
        ]
        is True
    )
    assert (
        policy["execution_boundary"][
            "article_content_generation_allowed"
        ]
        is False
    )


def test_review_artifact_identity() -> None:
    review = load(REVIEW)

    assert (
        review["content_item_id"]
        == "new-release-comic-20260703-001"
    )
    assert review["work_title"] == "ダークギャザリング"
    assert review["volume_label"] == "第20巻"
    assert review["release_date"] == "2026-07-03"
    assert review["author_name"] == "近藤憲一"
    assert review["publisher_name"] == "集英社"
    assert review["price_amount"] == 616


def test_review_artifact_digest() -> None:
    review = load(REVIEW)
    without_digest = copy.deepcopy(
        review
    )
    stored = without_digest.pop(
        "human_review_digest_sha256"
    )

    assert digest(without_digest) == stored


def test_human_review_is_complete_in_separate_record() -> None:
    review = load(REVIEW)
    source = load(SOURCE_INPUT)

    assert review["human_review_recorded"] is True
    assert review["human_review_complete"] is True
    assert review["source_registration_modified"] is False
    assert source["human_review_complete"] is False
    assert source["article_content_generated"] is False


def test_source_registration_is_preserved() -> None:
    request = load(REQUEST)

    assert (
        file_sha256(SOURCE_INPUT)
        == request["source_input_file_sha256"]
    )
    assert (
        request[
            "source_registration_preservation_requested"
        ]
        is True
    )
    assert (
        request[
            "source_registration_modification_requested"
        ]
        is False
    )


def test_dmm_requirement_acknowledged_but_not_completed() -> None:
    review = load(REVIEW)
    checklist = review[
        "review_checklist"
    ]

    assert (
        checklist[
            "dmm_latest_alias_recheck_requirement_acknowledged"
        ]
        is True
    )
    assert (
        checklist[
            "dmm_latest_alias_recheck_completed"
        ]
        is False
    )


def test_request_has_no_generation_or_execution() -> None:
    request = load(REQUEST)

    assert request[
        "human_review_recording_requested"
    ] is True
    assert request[
        "dmm_recheck_execution_requested"
    ] is False
    assert request[
        "article_content_generation_requested"
    ] is False
    assert request[
        "fresh_payload_creation_requested"
    ] is False
    assert request[
        "payload_binding_requested"
    ] is False
    assert request[
        "production_category_id_payload_injection_requested"
    ] is False
    assert request[
        "wordpress_write_requested"
    ] is False
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


def test_category_injection_request_is_rejected() -> None:
    builder = module()
    request = copy.deepcopy(
        load(REQUEST)
    )
    request[
        "production_category_id_payload_injection_requested"
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
            "category injection request was accepted"
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

    assert result["human_review_complete"] is True
    assert result["article_content_generated"] is False
    assert result["fresh_payload_created"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_ready_for_content_generation_gate_only() -> None:
    result = load(RESULT)

    assert (
        result["status"]
        == (
            "PASS_FRESH_ARTICLE_INPUT_HUMAN_"
            "REVIEW_RECORDED_NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
        )
    )
    assert result["human_review_recorded"] is True
    assert result["human_review_complete"] is True
    assert result["source_registration_modified"] is False
    assert (
        result[
            "dmm_latest_alias_recheck_completed"
        ]
        is False
    )
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
            "ready_for_article_content_generation_gate"
        ]
        is True
    )
    assert (
        result[
            "ready_for_article_content_generation"
        ]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_safety_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Human review complete: `true`" in report
    assert "Source registration modified: `false`" in report
    assert "DMM recheck completed: `false`" in report
    assert "Article content generated: `false`" in report
    assert "Fresh payload created: `false`" in report
    assert "Category ID injected: `false`" in report
    assert "WordPress write performed: `false`" in report
