from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONSUMPTION = ROOT / (
    "exchange/consumptions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_consumption.json"
)
SNAPSHOT = ROOT / (
    "exchange/executions/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_update_"
    "one_shot_execution_snapshot.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_execute_result.json"
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


def test_consumption_is_immutable_single_use() -> None:
    value = verify(
        CONSUMPTION,
        "consumption_digest_sha256",
    )

    assert value[
        "authorization_consumed"
    ] is True
    assert value[
        "confirmation_consumed"
    ] is True
    assert value[
        "authorization_consumption_count"
    ] == 1
    assert value[
        "confirmation_consumption_count"
    ] == 1
    assert value[
        "maximum_post_request_count"
    ] == 1
    assert value[
        "authorization_reuse_allowed"
    ] is False
    assert value[
        "automatic_retry_allowed"
    ] is False
    assert value[
        "automatic_reissue_allowed"
    ] is False
    assert value[
        "second_post_allowed"
    ] is False


def test_snapshot_and_result_digests() -> None:
    verify(
        SNAPSHOT,
        "snapshot_digest_sha256",
    )
    verify(
        RESULT,
        "result_digest_sha256",
    )


def test_exactly_one_post_no_retry() -> None:
    result = load(RESULT)

    assert result[
        "request_method"
    ] == "POST"
    assert result[
        "post_request_count"
    ] == 1
    assert result[
        "non_post_request_count"
    ] == 0
    assert result[
        "automatic_retry_count"
    ] == 0
    assert result[
        "redirect_followed"
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


def test_update_scope_and_backlist_boundary() -> None:
    result = load(RESULT)
    snapshot = load(SNAPSHOT)

    assert result[
        "allowed_update_fields"
    ] == [
        "content",
        "comment_status",
    ]
    assert result[
        "target_comment_status"
    ] == "closed"
    assert result[
        "backlist_carousel_included"
    ] is False

    assert snapshot[
        "title_sent"
    ] is False
    assert snapshot[
        "status_sent"
    ] is False
    assert snapshot[
        "categories_sent"
    ] is False
    assert snapshot[
        "slug_sent"
    ] is False
    assert snapshot[
        "excerpt_sent"
    ] is False
    assert snapshot[
        "featured_media_sent"
    ] is False


def test_consumption_and_next_gate() -> None:
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
        "automatic_retry_performed"
    ] is False
    assert result[
        "automatic_reissue_performed"
    ] is False
    assert result[
        "ready_for_post_update_get_verification"
    ] is True
    assert result[
        "production_status"
    ] == "NO_GO"


def test_outcome_consistency() -> None:
    result = load(RESULT)

    if result["response_validated"]:
        assert result["outcome"] == (
            "VALIDATED_HTTP_200_UPDATE_RESPONSE"
        )
        assert result["status"] == (
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_ONE_SHOT_POST_RESPONSE_VALIDATED_"
            "AWAITING_GET_ONLY_VERIFICATION"
        )
        assert result[
            "http_status_code"
        ] == 200
        assert result[
            "response_post_id_matches"
        ] is True
        assert result[
            "response_status_is_publish"
        ] is True
        assert result[
            "response_title_matches"
        ] is True
        assert result[
            "response_categories_match"
        ] is True
        assert result[
            "response_comment_status_is_closed"
        ] is True
        assert result[
            "response_content_matches_m24"
        ] is True
        assert result[
            "wordpress_update_performed"
        ] is True
    else:
        assert result["outcome"] in {
            "INDETERMINATE",
            "HTTP_NON_200",
            "RESPONSE_MISMATCH",
        }
        assert result[
            "wordpress_update_may_have_occurred"
        ] is True
        assert result[
            "ready_for_retry"
        ] is False


def test_no_delete_publish_or_x_operation() -> None:
    result = load(RESULT)

    assert result[
        "wordpress_republish_performed"
    ] is False
    assert result[
        "wordpress_delete_performed"
    ] is False
    assert result[
        "x_post_performed"
    ] is False
    assert result[
        "ready_for_wordpress_publish"
    ] is False


def test_evidence_contains_no_secrets_or_content() -> None:
    combined = (
        CONSUMPTION.read_text(
            encoding="utf-8"
        )
        + SNAPSHOT.read_text(
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
