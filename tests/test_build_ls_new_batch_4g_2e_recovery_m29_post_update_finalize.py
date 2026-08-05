from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FINALIZATION = ROOT / (
    "exchange/finalizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "post_update_finalization.json"
)
CLOSURE = ROOT / (
    "exchange/closures/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_tawawa_reference_layout_"
    "update_series_closure.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m29_post_update_finalize_result.json"
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


def test_finalization_closure_and_result_digests() -> None:
    verify(
        FINALIZATION,
        "finalization_digest_sha256",
    )
    verify(
        CLOSURE,
        "closure_digest_sha256",
    )
    verify(
        RESULT,
        "result_digest_sha256",
    )


def test_final_wordpress_state_fixed() -> None:
    value = load(FINALIZATION)

    assert value[
        "update_completed"
    ] is True
    assert value[
        "post_response_validated"
    ] is True
    assert value[
        "independent_get_verification_completed"
    ] is True
    assert value[
        "final_state_verified"
    ] is True
    assert value[
        "wordpress_post_id"
    ] == 192
    assert value[
        "final_status"
    ] == "publish"
    assert value[
        "final_category_ids"
    ] == [10]
    assert value[
        "final_comment_status"
    ] == "closed"
    assert value[
        "final_content_sha256"
    ] == (
        "dc938ae164c70130a5fb27692d71c97c"
        "c367a8985c44c2c333801b337ee6caf4"
    )


def test_consumption_and_permanent_closure() -> None:
    value = load(CLOSURE)

    assert value[
        "authorization_consumed"
    ] is True
    assert value[
        "confirmation_consumed"
    ] is True
    assert value[
        "consumption_count"
    ] == 1
    assert value[
        "authorization_reuse_permanently_closed"
    ] is True
    assert value[
        "automatic_retry_permanently_closed"
    ] is True
    assert value[
        "automatic_reissue_permanently_closed"
    ] is True
    assert value[
        "second_post_permanently_closed"
    ] is True
    assert value[
        "m27_execute_rerun_permanently_closed"
    ] is True
    assert value[
        "m28_verify_rerun_permanently_closed"
    ] is True
    assert value[
        "current_update_series_reexecution_permanently_closed"
    ] is True


def test_backlist_requirement_carried_forward() -> None:
    finalization = load(FINALIZATION)
    closure = load(CLOSURE)

    assert finalization[
        "backlist_future_requirement_carried_forward"
    ] is True
    assert finalization[
        "backlist_carousel_implemented_in_current_series"
    ] is False
    assert finalization[
        "backlist_carousel_included_in_current_update"
    ] is False
    assert finalization[
        "backlist_carousel_implementation_authorized"
    ] is False

    assert closure[
        "backlist_future_requirement_carried_forward"
    ] is True
    assert closure[
        "backlist_implementation_authorized"
    ] is False
    assert closure[
        "suggested_separate_future_phase"
    ] == "LS-NEW-SERIES-BACKLIST-1"


def test_no_network_or_wordpress_operation_in_m29() -> None:
    result = load(RESULT)

    assert result[
        "dns_resolution_performed"
    ] is False
    assert result[
        "network_connection_performed"
    ] is False
    assert result[
        "http_communication_performed"
    ] is False
    assert result[
        "wordpress_access_performed"
    ] is False
    assert result[
        "wordpress_get_performed"
    ] is False
    assert result[
        "wordpress_post_performed"
    ] is False
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
        "authorization_consumption_performed_in_current_phase"
    ] is False


def test_series_is_closed_and_all_execution_gates_are_closed() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_WORDPRESS_TAWAWA_REFERENCE_LAYOUT_UPDATE_"
        "POST_UPDATE_FINALIZATION_RECORDED_LOCAL_ONLY_"
        "SERIES_CLOSED_NO_WORDPRESS_ACCESS"
    )
    assert result[
        "current_update_series_closed"
    ] is True
    assert result[
        "required_next_phase_for_current_update_series"
    ] is None
    assert result[
        "ready_for_retry"
    ] is False
    assert result[
        "ready_for_second_post"
    ] is False
    assert result[
        "ready_for_wordpress_update"
    ] is False
    assert result[
        "ready_for_wordpress_publish"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"


def test_source_artifacts_not_modified_and_rollback_retained() -> None:
    result = load(RESULT)

    assert result[
        "source_artifacts_modified"
    ] is False
    assert result[
        "rollback_evidence_retained"
    ] is True


def test_output_contains_no_secrets_urls_or_wordpress_content() -> None:
    combined = (
        FINALIZATION.read_text(
            encoding="utf-8"
        )
        + CLOSURE.read_text(
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
