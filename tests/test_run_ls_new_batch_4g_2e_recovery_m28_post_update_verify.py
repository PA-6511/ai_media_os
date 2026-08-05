from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

VERIFICATION = ROOT / (
    "exchange/verifications/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "post_update_get_verification.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m28_post_update_verify_result.json"
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


def test_verification_and_result_digests() -> None:
    verify(
        VERIFICATION,
        "verification_digest_sha256",
    )
    verify(
        RESULT,
        "result_digest_sha256",
    )


def test_exactly_one_get_no_retry() -> None:
    result = load(RESULT)

    assert result[
        "request_method"
    ] == "GET"
    assert result[
        "get_request_count"
    ] == 1
    assert result[
        "non_get_request_count"
    ] == 0
    assert result[
        "automatic_retry_count"
    ] == 0
    assert result[
        "redirect_followed"
    ] is False


def test_no_write_or_second_post() -> None:
    result = load(RESULT)

    assert result[
        "wordpress_write_performed"
    ] is False
    assert result[
        "wordpress_update_performed"
    ] is False
    assert result[
        "wordpress_republish_performed"
    ] is False
    assert result[
        "wordpress_delete_performed"
    ] is False
    assert result[
        "second_post_performed"
    ] is False
    assert result[
        "ready_for_retry"
    ] is False
    assert result[
        "ready_for_second_post"
    ] is False


def test_consumption_remains_fixed() -> None:
    result = load(RESULT)

    assert result[
        "authorization_consumed"
    ] is True
    assert result[
        "confirmation_consumed"
    ] is True
    assert result[
        "authorization_consumption_count"
    ] == 1
    assert result[
        "confirmation_consumption_count"
    ] == 1
    assert result[
        "authorization_reused"
    ] is False
    assert result[
        "automatic_reissue_performed"
    ] is False


def test_backlist_remains_excluded() -> None:
    result = load(RESULT)

    assert result[
        "backlist_carousel_included"
    ] is False


def test_final_state_consistency() -> None:
    result = load(RESULT)

    if result["final_state_verified"]:
        assert result["status"] == (
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "POST_UPDATE_GET_VERIFICATION_FINAL_STATE_MATCHED_"
            "NO_WRITE"
        )
        assert result[
            "http_status_code"
        ] == 200
        assert result[
            "final_post_id_matches"
        ] is True
        assert result[
            "final_status_is_publish"
        ] is True
        assert result[
            "final_title_matches"
        ] is True
        assert result[
            "final_categories_match"
        ] is True
        assert result[
            "final_comment_status_is_closed"
        ] is True
        assert result[
            "final_content_matches_m24"
        ] is True
        assert result[
            "ready_for_local_finalization"
        ] is True
    else:
        assert result["status"] == (
            "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
            "POST_UPDATE_GET_VERIFICATION_NOT_CONFIRMED_"
            "NO_WRITE_NO_RETRY"
        )
        assert result[
            "ready_for_local_finalization"
        ] is False

    assert result[
        "production_status"
    ] == "NO_GO"


def test_source_artifacts_not_modified() -> None:
    result = load(RESULT)

    assert result[
        "source_artifacts_modified"
    ] is False


def test_evidence_contains_no_secrets_or_content() -> None:
    combined = (
        VERIFICATION.read_text(
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
    assert "<article" not in combined
    assert "<div" not in combined
