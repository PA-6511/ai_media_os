from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_historical_m4_"
    "evidence_human_review_policy.json"
)
FIX_APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m5_fix1_"
    "policy_schema_fix_approval.json"
)
M5_APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m5_"
    "historical_evidence_human_review_approval.json"
)
REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_historical_m4_evidence_human_review.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m5_result.json"
)
BUILDER = ROOT / (
    "scripts/"
    "build_ls_new_batch_4g_2e_recovery_m5.py"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_execution_boundary_schema_fixed() -> None:
    policy = load(POLICY)
    boundary = policy[
        "execution_boundary"
    ]

    assert (
        boundary[
            "historical_result_reclassification_allowed"
        ]
        is False
    )
    assert (
        policy["historical_preservation"][
            "historical_result_reclassification_allowed"
        ]
        is False
    )


def test_policy_is_review_only() -> None:
    boundary = load(POLICY)[
        "execution_boundary"
    ]

    assert (
        boundary[
            "human_review_evidence_creation_allowed"
        ]
        is True
    )
    assert (
        boundary["network_connection_allowed"]
        is False
    )
    assert boundary["http_request_allowed"] is False
    assert boundary["dmm_recheck_allowed"] is False
    assert (
        boundary[
            "final_affiliate_link_generation_allowed"
        ]
        is False
    )


def test_fix_approval_digest() -> None:
    approval = load(FIX_APPROVAL)
    comparable = copy.deepcopy(
        approval
    )
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval[
        "human_explicit_approval"
    ] is True


def test_m5_approval_digest() -> None:
    approval = load(M5_APPROVAL)
    comparable = copy.deepcopy(
        approval
    )
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored


def test_review_digest() -> None:
    review = load(REVIEW)
    comparable = copy.deepcopy(review)
    stored = comparable.pop(
        "human_review_evidence_digest_sha256"
    )

    assert digest(comparable) == stored


def test_review_verdict() -> None:
    review = load(REVIEW)

    assert review["review_verdict"] == (
        "APPROVED_HISTORICAL_EVIDENCE_"
        "AS_DMM_PRODUCT_MATCH"
    )
    assert all(
        review["review_checks"].values()
    )


def test_reviewed_identity() -> None:
    evidence = load(REVIEW)[
        "reviewed_historical_evidence"
    ]

    assert evidence[
        "normalized_volume"
    ] == "第20巻"
    assert evidence[
        "author"
    ] == "近藤憲一"
    assert evidence[
        "publisher"
    ] == "集英社"
    assert evidence[
        "series_id"
    ] == "861056"
    assert evidence[
        "canonical_product_url"
    ] == (
        "https://book.dmm.com/"
        "product/861056/"
        "b950yshes32617/"
    )


def test_historical_sources_unchanged() -> None:
    approval = load(M5_APPROVAL)

    for binding in approval[
        "source_bindings"
    ].values():
        path = ROOT / binding["path"]

        assert file_sha256(path) == (
            binding["file_sha256"]
        )


def test_historical_result_not_reclassified() -> None:
    review = load(REVIEW)

    treatment = review[
        "historical_evidence_treatment"
    ]

    assert (
        treatment["m4_result_modified"]
        is False
    )
    assert (
        treatment["m4_result_reclassified"]
        is False
    )
    assert (
        treatment["m4_recheck_modified"]
        is False
    )
    assert (
        treatment["m4_consumption_modified"]
        is False
    )


def test_candidate_not_final_affiliate_link() -> None:
    conclusion = load(REVIEW)[
        "review_conclusion"
    ]

    assert (
        conclusion[
            "dmm_product_url_candidate_verified"
        ]
        is True
    )
    assert (
        conclusion[
            "final_affiliate_link_generated"
        ]
        is False
    )
    assert (
        conclusion[
            "article_dmm_slot_activation_allowed"
        ]
        is False
    )


def test_result_ready_for_m6_gate_only() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_DMM_HISTORICAL_M4_"
        "EVIDENCE_HUMAN_REVIEW_"
        "APPROVED_NO_NETWORK_"
        "NO_RECLASSIFICATION"
    )
    assert (
        result[
            "ready_for_ls_new_batch_4g_2e_recovery_m6"
        ]
        is True
    )
    assert (
        result[
            "ready_for_final_affiliate_link_generation_gate"
        ]
        is True
    )
    assert (
        result[
            "ready_for_final_affiliate_link_generation"
        ]
        is False
    )


def test_production_boundary_closed() -> None:
    result = load(RESULT)

    assert (
        result[
            "historical_m4_result_reclassified"
        ]
        is False
    )
    assert (
        result["new_authorization_created"]
        is False
    )
    assert (
        result["network_connection_performed"]
        is False
    )
    assert (
        result["dmm_recheck_performed"]
        is False
    )
    assert (
        result["final_affiliate_link_generated"]
        is False
    )
    assert result["article_modified"] is False
    assert (
        result["fresh_payload_created"]
        is False
    )
    assert (
        result["wordpress_access_performed"]
        is False
    )
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_builder_has_no_network_execution() -> None:
    source = BUILDER.read_text(
        encoding="utf-8"
    )

    for forbidden in [
        "urllib.request",
        "requests.get(",
        "urlopen(",
        "opener.open(",
        "http.client",
        "import socket",
    ]:
        assert forbidden not in source
