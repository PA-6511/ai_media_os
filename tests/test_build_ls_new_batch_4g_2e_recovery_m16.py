from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_publication_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m16_result.json"
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


def verify_digest(
    path: Path,
    field: str,
) -> dict:
    value = load(path)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field)

    assert digest(comparable) == stored

    return value


def test_authorization_digest_and_mode() -> None:
    value = verify_digest(
        AUTHORIZATION,
        "authorization_digest_sha256",
    )

    assert stat.S_IMODE(
        AUTHORIZATION.stat().st_mode
    ) == 0o600
    assert value[
        "authorization_id"
    ] == (
        "WORDPRESS_PUBLICATION_ONE_SHOT_"
        "AUTHORIZATION_V1"
    )


def test_result_digest_and_status() -> None:
    value = verify_digest(
        RESULT,
        "result_digest_sha256",
    )

    assert value["status"] == (
        "PASS_WORDPRESS_PUBLICATION_ONE_SHOT_"
        "AUTHORIZATION_GATE_FIXED_NO_NETWORK_NO_WORDPRESS"
    )
    assert value["wordpress_post_id"] == 192


def test_single_use_unconsumed_contract() -> None:
    value = load(AUTHORIZATION)

    assert value["single_use"] is True
    assert value[
        "authorization_consumed"
    ] is False
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
        "maximum_publish_count"
    ] == 1


def test_publication_scope() -> None:
    value = load(AUTHORIZATION)

    assert value["wordpress_post_id"] == 192
    assert value[
        "required_current_post_status"
    ] == "draft"
    assert value[
        "allowed_target_post_status"
    ] == "publish"
    assert value[
        "explicit_execute_now_confirmation_required"
    ] is True
    assert value[
        "planned_execution_phase_id"
    ] == (
        "LS-NEW-BATCH-4G-2E-RECOVERY-M17"
    )


def test_no_external_operation() -> None:
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
        "wordpress_publish_performed"
    ] is False
    assert value[
        "credential_accessed"
    ] is False


def test_next_gate_and_production_closed() -> None:
    value = load(RESULT)

    assert value[
        "ready_for_wordpress_publication_preflight"
    ] is True
    assert value[
        "ready_for_wordpress_publication_execute_now_gate"
    ] is False
    assert value[
        "ready_for_wordpress_publish"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
