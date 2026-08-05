from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONFIRMATION = ROOT / (
    "exchange/confirmations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "execute_now_confirmation.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_execute_now_confirmation_result.json"
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


def test_confirmation_digest_and_state() -> None:
    value = verify(
        CONFIRMATION,
        "confirmation_digest_sha256",
    )

    assert value[
        "execute_now_confirmation_recorded"
    ] is True
    assert value[
        "confirmation_consumed"
    ] is False
    assert value[
        "wordpress_post_id"
    ] == 192


def test_update_scope() -> None:
    value = load(CONFIRMATION)

    assert value[
        "confirmed_update_fields"
    ] == [
        "content",
        "comment_status",
    ]
    assert value[
        "expected_pre_update_comment_status"
    ] == "open"
    assert value[
        "target_comment_status"
    ] == "closed"

    assert value[
        "title_change_allowed"
    ] is False
    assert value[
        "status_change_allowed"
    ] is False
    assert value[
        "categories_change_allowed"
    ] is False
    assert value[
        "slug_change_allowed"
    ] is False
    assert value[
        "excerpt_change_allowed"
    ] is False
    assert value[
        "featured_media_change_allowed"
    ] is False


def test_single_use_boundary() -> None:
    value = load(CONFIRMATION)

    assert value["single_use"] is True
    assert value[
        "maximum_update_count"
    ] == 1
    assert value[
        "authorization_consumed"
    ] is False
    assert value[
        "authorization_consumption_count"
    ] == 0
    assert value[
        "authorization_reuse_allowed"
    ] is False
    assert value[
        "automatic_retry_allowed"
    ] is False
    assert value[
        "automatic_reissue_allowed"
    ] is False


def test_backlist_excluded() -> None:
    value = load(CONFIRMATION)

    assert value[
        "backlist_carousel_included"
    ] is False


def test_no_network_or_wordpress_operation() -> None:
    value = load(RESULT)

    assert value[
        "dns_resolution_performed"
    ] is False
    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "http_request_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "wordpress_get_performed"
    ] is False
    assert value[
        "wordpress_post_performed"
    ] is False
    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_update_performed"
    ] is False
    assert value[
        "authorization_consumption_performed"
    ] is False
    assert value[
        "authorization_consumed"
    ] is False


def test_result_status_and_next_gate() -> None:
    value = verify(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
        "EXECUTE_NOW_CONFIRMATION_RECORDED_LOCAL_ONLY_"
        "NO_WORDPRESS_ACCESS"
    )
    assert value[
        "ready_for_separate_one_shot_update_execution_approval"
    ] is True
    assert value[
        "ready_for_wordpress_update_in_current_phase"
    ] is False
    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"


def test_output_contains_no_secrets() -> None:
    combined = (
        CONFIRMATION.read_text(
            encoding="utf-8"
        )
        + RESULT.read_text(
            encoding="utf-8"
        )
    )

    assert "WORDPRESS_APP_PASSWORD" not in combined
    assert "WORDPRESS_USERNAME" not in combined
    assert '"Authorization"' not in combined
    assert "Basic " not in combined
    assert "https://" not in combined
    assert "http://" not in combined
    assert "al.dmm.com" not in combined
