from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M13_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_writer_result.json"
)

EXPECTED_M12_AUTH_SHA = (
    "7c9662a7a13502e165862e4524278992"
    "28794bce6904a0215c45a5b54ba1142b"
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


def test_result_digest() -> None:
    value = load(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored


def test_writer_credential_structure_passed() -> None:
    value = load(RESULT)

    assert value[
        "writer_credential_regular_file"
    ] is True
    assert value[
        "writer_credential_symlink"
    ] is False
    assert value[
        "writer_credential_mode_0600"
    ] is True
    assert value[
        "writer_credential_owner_deploy"
    ] is True
    assert value[
        "required_key_count_exactly_one"
    ] is True
    assert value[
        "required_values_nonempty"
    ] is True


def test_secret_output_prohibited() -> None:
    value = load(RESULT)

    assert value[
        "credential_values_output"
    ] is False
    assert value[
        "credential_value_lengths_output"
    ] is False
    assert value[
        "credential_value_hashes_output"
    ] is False
    assert value[
        "credential_file_hash_computed"
    ] is False
    assert value[
        "credential_file_content_output"
    ] is False
    assert value[
        "authorization_header_output"
    ] is False


def test_m12_authorization_unchanged() -> None:
    value = load(RESULT)

    assert hashlib.sha256(
        M12_AUTH.read_bytes()
    ).hexdigest() == EXPECTED_M12_AUTH_SHA

    assert value[
        "m12_authorization_consumed"
    ] is False
    assert not M13_CONSUMPTION.exists()


def test_external_boundaries_closed() -> None:
    value = load(RESULT)

    assert value[
        "environment_export_performed"
    ] is False
    assert value[
        "readonly_credential_accessed"
    ] is False
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
        "wordpress_draft_created"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"
