from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STORE_MANIFEST = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_safe_store_manifest.json"
)
DESKTOP_PREVIEW = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_desktop_safe_preview.html"
)
MOBILE_PREVIEW = ROOT / (
    "exchange/previews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_mobile_safe_preview.html"
)
REVIEW_PACKET = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_layout_human_review_preparation.json"
)
CHECKLIST = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m23_"
    "human_review_checklist.md"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m23_result.json"
)

FORBIDDEN = [
    "http://",
    "https://",
    "af_id=",
    "lurl=",
]


def load(
    path: Path,
) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(
    value,
) -> str:
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


def test_result_digest_and_status() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_RENDERED_LAYOUT_"
        "CORRECTION_HUMAN_REVIEW_PREPARATION_"
        "SAFE_PREVIEWS_READY_LOCAL_ONLY_"
        "NO_WORDPRESS_ACCESS"
    )

    assert value[
        "safe_desktop_preview_generated"
    ] is True
    assert value[
        "safe_mobile_preview_generated"
    ] is True
    assert value[
        "human_review_completed"
    ] is False
    assert value[
        "human_review_verdict"
    ] == "NOT_RECORDED"


def test_store_manifest_safe_fields() -> None:
    value = verify(
        STORE_MANIFEST,
        "store_manifest_digest_sha256",
    )

    stores = {
        item["store"]: item
        for item in value["stores"]
    }

    assert set(stores.keys()) == {
        "amazon",
        "rakuten_kobo",
        "dmm",
    }

    assert stores["amazon"][
        "state"
    ] == "disabled_no_source_link"

    assert stores["rakuten_kobo"][
        "state"
    ] == "disabled_no_source_link"

    assert stores["dmm"][
        "host"
    ] == "al.dmm.com"

    assert stores["dmm"][
        "url_fingerprint_sha256"
    ] is not None

    assert value[
        "full_store_url_present"
    ] is False
    assert value[
        "affiliate_identifier_present"
    ] is False


def test_desktop_preview_is_safe() -> None:
    value = DESKTOP_PREVIEW.read_text(
        encoding="utf-8"
    )
    lowered = value.lower()

    assert (
        'data-preview-mode="desktop"'
        in value
    )
    assert (
        'href="#preview-disabled"'
        in value
    )
    assert (
        "data:image/svg+xml;base64,"
        in value
    )

    for forbidden in FORBIDDEN:
        assert forbidden not in lowered


def test_mobile_preview_is_safe() -> None:
    value = MOBILE_PREVIEW.read_text(
        encoding="utf-8"
    )
    lowered = value.lower()

    assert (
        'data-preview-mode="mobile"'
        in value
    )
    assert (
        'href="#preview-disabled"'
        in value
    )
    assert (
        "data:image/svg+xml;base64,"
        in value
    )

    for forbidden in FORBIDDEN:
        assert forbidden not in lowered


def test_preview_forced_layout_rules() -> None:
    desktop = DESKTOP_PREVIEW.read_text(
        encoding="utf-8"
    )
    mobile = MOBILE_PREVIEW.read_text(
        encoding="utf-8"
    )

    assert (
        "grid-template-columns: "
        "minmax(260px, 38%) "
        "minmax(0, 1fr) !important"
        in desktop
    )

    assert (
        ".ebook-product-card__pr {\n"
        "  order: 1 !important;"
        in desktop
    )

    assert (
        ".ebook-product-card__stores {\n"
        "  order: 2 !important;"
        in desktop
    )

    assert (
        ".ebook-product-card__details {\n"
        "  order: 3 !important;"
        in desktop
    )

    assert (
        "grid-template-columns: "
        "minmax(0, 1fr) !important"
        in mobile
    )

    assert (
        ".ebook-product-card__details {\n"
        "  order: 1 !important;"
        in mobile
    )

    assert (
        ".ebook-product-card__pr {\n"
        "  order: 2 !important;"
        in mobile
    )

    assert (
        ".ebook-product-card__stores {\n"
        "  order: 3 !important;"
        in mobile
    )


def test_review_packet_awaits_human() -> None:
    value = verify(
        REVIEW_PACKET,
        "review_preparation_digest_sha256",
    )

    assert value[
        "human_review_status"
    ] == "AWAITING_VISUAL_REVIEW"
    assert value[
        "human_review_completed"
    ] is False
    assert value[
        "human_review_verdict"
    ] == "NOT_RECORDED"

    assert value[
        "comment_status_target"
    ] == "closed"

    assert value[
        "allowed_update_fields"
    ] == [
        "content",
        "comment_status",
    ]

    assert value[
        "ready_for_human_visual_review"
    ] is True

    assert value[
        "ready_for_wordpress_update_authorization_gate"
    ] is False


def test_checklist_and_output_modes() -> None:
    checklist = CHECKLIST.read_text(
        encoding="utf-8"
    )

    assert "デスクトップ" in checklist
    assert "スマートフォン" in checklist
    assert "comment_status=closed" in checklist

    for path in [
        STORE_MANIFEST,
        DESKTOP_PREVIEW,
        MOBILE_PREVIEW,
        REVIEW_PACKET,
        CHECKLIST,
        RESULT,
    ]:
        assert stat.S_IMODE(
            path.stat().st_mode
        ) == 0o600


def test_no_external_or_wordpress_operation() -> None:
    result = load(RESULT)

    assert result[
        "external_links_active_in_previews"
    ] is False
    assert result[
        "external_asset_requests_in_previews"
    ] is False
    assert result[
        "full_store_url_present_in_previews"
    ] is False
    assert result[
        "affiliate_identifier_present_in_previews"
    ] is False

    assert result[
        "network_connection_performed"
    ] is False
    assert result[
        "dns_resolution_performed"
    ] is False
    assert result[
        "http_request_performed"
    ] is False
    assert result[
        "wordpress_access_performed"
    ] is False
    assert result[
        "wordpress_write_performed"
    ] is False
    assert result[
        "wordpress_update_performed"
    ] is False
    assert result[
        "authorization_issued"
    ] is False
    assert result[
        "authorization_consumed"
    ] is False
    assert result[
        "authorization_reused"
    ] is False
    assert result[
        "execution_allowed"
    ] is False

    assert result[
        "ready_for_human_visual_review"
    ] is True
    assert result[
        "ready_for_wordpress_update_authorization_gate"
    ] is False
    assert result[
        "ready_for_wordpress_update"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"
