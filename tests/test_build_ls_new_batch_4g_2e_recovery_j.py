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
    "offline_content_generation_approval_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "offline_content_generation_approval_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_j_"
    "offline_content_generation_approval.json"
)
AUTHORIZATION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_authorization.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_j_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_j_"
    "offline_content_generation_approval_report.md"
)
RESERVED_OUTPUT = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
BUILDER = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_j.py"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_j_blocked.py"
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
        "recovery_j_builder",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None

    item = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(item)
    return item


def test_policy_is_authorization_recording_only() -> None:
    policy = load(POLICY)

    assert (
        policy["operation_mode"]
        == (
            "APPROVED_OFFLINE_CONTENT_GENERATION_"
            "AUTHORIZATION_RECORDING_ONLY"
        )
    )
    assert (
        policy["execution_boundary"][
            "authorization_recording_allowed"
        ]
        is True
    )
    assert (
        policy["execution_boundary"][
            "article_content_generation_allowed"
        ]
        is False
    )


def test_approval_digest_is_valid() -> None:
    approval = load(APPROVAL)
    without_digest = copy.deepcopy(
        approval
    )
    stored = without_digest.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(without_digest) == stored
    assert (
        approval["approval_label"]
        == (
            "FRESH_ARTICLE_OFFLINE_"
            "CONTENT_GENERATION_APPROVED"
        )
    )
    assert approval["human_explicit_approval"] is True
    assert approval["execution_allowed"] is False


def test_authorization_digest_is_valid() -> None:
    authorization = load(AUTHORIZATION)
    without_digest = copy.deepcopy(
        authorization
    )
    stored = without_digest.pop(
        "authorization_digest_sha256"
    )

    assert digest(without_digest) == stored


def test_authorization_is_single_use_for_k() -> None:
    authorization = load(AUTHORIZATION)

    assert (
        authorization["authorized_next_phase_id"]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K"
    )
    assert authorization["single_use"] is True
    assert authorization["authorization_consumed"] is False
    assert (
        authorization["authorization_reuse_allowed"]
        is False
    )
    assert (
        authorization["different_article_use_allowed"]
        is False
    )


def test_template_resolution_is_still_required() -> None:
    authorization = load(AUTHORIZATION)

    assert (
        authorization[
            "template_artifact_resolution_required"
        ]
        is True
    )
    assert (
        authorization["template_artifact_resolved"]
        is False
    )


def test_dmm_rendering_remains_blocked() -> None:
    authorization = load(AUTHORIZATION)
    dmm = authorization["dmm_recheck"]

    assert dmm["requirement_inherited"] is True
    assert dmm["completed"] is False
    assert dmm["url_rendering_allowed"] is False
    assert dmm["final_link_use_allowed"] is False


def test_reserved_output_is_absent() -> None:
    assert not RESERVED_OUTPUT.exists()


def test_request_does_not_generate_content() -> None:
    request = load(REQUEST)

    assert (
        request["authorization_recording_requested"]
        is True
    )
    assert (
        request[
            "next_phase_offline_content_generation_authorized"
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
    assert request["wordpress_write_requested"] is False
    assert request["execution_requested"] is False


def test_current_phase_content_request_is_rejected() -> None:
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
            "current phase content generation was accepted"
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

    assert result["authorization_recorded"] is True
    assert result["authorization_consumed"] is False
    assert result["article_content_generated"] is False
    assert result["content_output_created"] is False
    assert result["fresh_payload_created"] is False
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_ready_for_k_only() -> None:
    result = load(RESULT)

    assert (
        result["status"]
        == (
            "PASS_FRESH_ARTICLE_OFFLINE_CONTENT_"
            "GENERATION_AUTHORIZATION_RECORDED_"
            "NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
        )
    )
    assert (
        result["authorized_next_phase_id"]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K"
    )
    assert result["single_use_authorization"] is True
    assert result["authorization_consumed"] is False
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
            "ready_for_one_shot_offline_article_content_generation"
        ]
        is True
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Single use: `true`" in report
    assert "Authorization consumed: `false`" in report
    assert "Template resolved: `false`" in report
    assert "Content output exists: `false`" in report
    assert "Article content generated: `false`" in report
    assert "Fresh payload created: `false`" in report
    assert "WordPress write performed: `false`" in report
