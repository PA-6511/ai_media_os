from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

M24_RENDERED = ROOT / (
    "exchange/rendered/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_v1.html"
)
M24_PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_payload_v1.json"
)
M25_REQUIREMENT = ROOT / (
    "exchange/requirements/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_backlist_cover_affiliate_carousel_"
    "future_requirement.json"
)

AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_one_shot_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m26_result.json"
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


def verify(
    path: Path,
    field: str,
) -> dict:
    value = load(path)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field)

    assert digest(comparable) == stored
    assert stat.S_IMODE(
        path.stat().st_mode
    ) == 0o600

    return value


def test_authorization_digest_and_binding() -> None:
    value = verify(
        AUTHORIZATION,
        "authorization_digest_sha256",
    )

    assert value[
        "wordpress_post_id"
    ] == 192

    assert value[
        "bound_rendered_content_sha256"
    ] == (
        "dc938ae164c70130a5fb27692d71c97c"
        "c367a8985c44c2c333801b337ee6caf4"
    )

    assert value[
        "bound_update_payload_digest_sha256"
    ] == (
        "52ed18792454e5806b739059911c8117"
        "810cafcadacf35fb77429b608673cd60"
    )

    assert value[
        "bound_human_review_evidence_digest_sha256"
    ] == (
        "7fd7a9f0f5317435160010fac811b77d"
        "876f77919ad2b5905c6cdea82f8f1806"
    )


def test_single_use_boundary() -> None:
    value = load(AUTHORIZATION)

    assert value["single_use"] is True
    assert value[
        "maximum_update_count"
    ] == 1
    assert value[
        "authorization_consumed"
    ] is False
    assert value[
        "consumption_count"
    ] == 0
    assert value[
        "reuse_allowed"
    ] is False
    assert value[
        "automatic_retry_allowed"
    ] is False
    assert value[
        "automatic_reissue_allowed"
    ] is False
    assert value[
        "current_phase_execution_allowed"
    ] is False


def test_payload_fields_and_content_binding() -> None:
    payload = load(M24_PAYLOAD)
    authorization = load(AUTHORIZATION)

    body = payload[
        "wordpress_request_body"
    ]

    assert set(body.keys()) == {
        "content",
        "comment_status",
    }

    assert body[
        "comment_status"
    ] == "closed"

    assert body[
        "content"
    ] == M24_RENDERED.read_text(
        encoding="utf-8"
    )

    assert authorization[
        "request_body_digest_sha256"
    ] == digest(body)

    for field in [
        "title",
        "status",
        "categories",
        "slug",
        "excerpt",
        "featured_media",
    ]:
        assert field not in body


def test_backlist_requirement_excluded() -> None:
    requirement = load(
        M25_REQUIREMENT
    )
    authorization = load(
        AUTHORIZATION
    )
    rendered = M24_RENDERED.read_text(
        encoding="utf-8"
    )

    assert requirement[
        "implementation_authorized"
    ] is False
    assert requirement[
        "included_in_current_wordpress_update"
    ] is False

    assert authorization[
        "backlist_carousel_included"
    ] is False
    assert authorization[
        "backlist_carousel_implementation_authorized"
    ] is False

    assert (
        "SERIES_BACKLIST_COVER_AFFILIATE_CAROUSEL_V1"
        not in rendered
    )
    assert (
        "LS-NEW-SERIES-BACKLIST-1"
        not in rendered
    )


def test_result_status_and_next_gate() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
        "UPDATE_ONE_SHOT_AUTHORIZATION_ISSUED_"
        "LOCAL_ONLY_NO_WORDPRESS_ACCESS"
    )

    assert value[
        "authorization_issued"
    ] is True
    assert value[
        "authorization_consumed"
    ] is False

    assert value[
        "ready_for_authenticated_preflight"
    ] is True
    assert value[
        "ready_for_execute_now_confirmation"
    ] is False
    assert value[
        "ready_for_wordpress_update"
    ] is False


def test_no_wordpress_or_consumption_operation() -> None:
    value = load(RESULT)

    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "dns_resolution_performed"
    ] is False
    assert value[
        "http_request_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_update_performed"
    ] is False
    assert value[
        "wordpress_republish_performed"
    ] is False
    assert value[
        "wordpress_delete_performed"
    ] is False
    assert value[
        "authorization_consumption_performed"
    ] is False
    assert value[
        "authorization_reuse_performed"
    ] is False
    assert value[
        "automatic_retry_performed"
    ] is False
    assert value[
        "automatic_reissue_performed"
    ] is False
    assert value[
        "x_post_performed"
    ] is False
    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"


def test_output_modes() -> None:
    for path in [
        AUTHORIZATION,
        RESULT,
    ]:
        assert stat.S_IMODE(
            path.stat().st_mode
        ) == 0o600
