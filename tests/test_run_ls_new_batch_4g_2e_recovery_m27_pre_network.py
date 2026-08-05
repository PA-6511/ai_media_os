from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT = ROOT / (
    "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_authenticated_get_preflight_snapshot.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_pre_network_result.json"
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


def test_snapshot_digest_and_mode() -> None:
    verify(
        SNAPSHOT,
        "snapshot_digest_sha256",
    )


def test_result_digest_and_mode() -> None:
    verify(
        RESULT,
        "result_digest_sha256",
    )


def test_request_method_boundary() -> None:
    snapshot = load(SNAPSHOT)

    assert snapshot[
        "get_request_count"
    ] in {
        0,
        1,
    }
    assert snapshot[
        "non_get_request_count"
    ] == 0
    assert snapshot[
        "automatic_retry_count"
    ] == 0
    assert snapshot[
        "redirect_followed"
    ] is False


def test_no_write_or_authorization_consumption() -> None:
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
        "authorization_consumption_performed"
    ] is False
    assert result[
        "authorization_consumed"
    ] is False
    assert result[
        "authorization_reused"
    ] is False
    assert result[
        "automatic_reissue_performed"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"


def test_backlist_remains_excluded() -> None:
    result = load(RESULT)

    assert result[
        "backlist_carousel_included"
    ] is False
    assert result[
        "backlist_carousel_implemented"
    ] is False


def test_safe_evidence_contains_no_credentials() -> None:
    combined = (
        SNAPSHOT.read_text(
            encoding="utf-8"
        )
        + RESULT.read_text(
            encoding="utf-8"
        )
    )

    assert "WORDPRESS_APP_PASSWORD" not in combined
    assert '"Authorization"' not in combined
    assert "Basic " not in combined
    assert "https://" not in combined
    assert "http://" not in combined


def test_preflight_state_consistency() -> None:
    snapshot = load(SNAPSHOT)
    result = load(RESULT)

    assert result[
        "preflight_passed"
    ] == snapshot[
        "preflight_passed"
    ]

    if result["preflight_passed"]:
        assert result["status"] == (
            "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_AUTHENTICATED_GET_ONLY_PREFLIGHT_"
            "READY_FOR_EXPLICIT_EXECUTE_NOW_CONFIRMATION"
        )
        assert result[
            "get_request_count"
        ] == 1
        assert result[
            "non_get_request_count"
        ] == 0
        assert result[
            "http_status_code"
        ] == 200
        assert result[
            "current_post_id_matches"
        ] is True
        assert result[
            "current_status_is_publish"
        ] is True
        assert result[
            "current_title_matches"
        ] is True
        assert result[
            "current_categories_match"
        ] is True
        assert result[
            "current_content_matches_rollback"
        ] is True
        assert result[
            "update_content_matches_m24"
        ] is True
        assert result[
            "request_body_digest_matches"
        ] is True
        assert result[
            "ready_for_execute_now_confirmation"
        ] is True
    else:
        assert result["status"] == (
            "BLOCKED_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_"
            "UPDATE_AUTHENTICATED_PREFLIGHT_MISMATCH_"
            "NO_WORDPRESS_WRITE"
        )
        assert result[
            "ready_for_execute_now_confirmation"
        ] is False

    assert result[
        "ready_for_wordpress_update"
    ] is False
