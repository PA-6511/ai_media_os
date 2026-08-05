from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload_human_review.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_result.json"
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


def test_payload_immutable_binding() -> None:
    assert hashlib.sha256(
        PAYLOAD.read_bytes()
    ).hexdigest() == (
        "30a70be4110e863a85e2896f69f5b3e5"
        "1d814a6fd82d5489f899d8a244166d8f"
    )

    assert stat.S_IMODE(
        PAYLOAD.stat().st_mode
    ) == 0o600


def test_review_digest_and_verdict() -> None:
    value = load(REVIEW)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "human_review_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["review_verdict"] == (
        "APPROVED_NO_CHANGE_REQUIRED"
    )


def test_review_used_structural_href_validation() -> None:
    validation = load(REVIEW)[
        "validation_results"
    ]

    assert validation[
        "href_html_entity_decoded"
    ] is True
    assert validation[
        "decoded_href_exact_secret_link_match"
    ] is True
    assert validation[
        "dmm_anchor_count_one"
    ] is True


def test_no_regeneration_or_reconsumption() -> None:
    value = load(RESULT)

    assert value["payload_regenerated"] is False
    assert value["payload_modified"] is False
    assert value["authorization_reissued"] is False
    assert value["authorization_reconsumed"] is False


def test_result_digest_and_readiness() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_POST_SUCCESS_HTML_ENTITY_"
        "VALIDATOR_FIXED_EXISTING_PAYLOAD_"
        "REVIEW_APPROVED_NO_REGENERATION"
    )
    assert value[
        "ready_for_wordpress_draft_creation_authorization_gate"
    ] is True
    assert value[
        "ready_for_wordpress_draft_creation"
    ] is False


def test_external_boundaries_closed() -> None:
    value = load(RESULT)

    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "wordpress_draft_created"
    ] is False
    assert value[
        "wordpress_published"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
