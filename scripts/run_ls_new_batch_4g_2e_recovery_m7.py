#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_final_affiliate_link_"
    "one_shot_generation_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m7_execute_now_approval.json"
)
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_consumption.json"
)
LINK_ARTIFACT = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m7_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m7_"
    "dmm_final_affiliate_link_generation_report.md"
)

CREDENTIAL_FILE = Path(
    "/etc/ai-media-os/credential.env"
)
CREDENTIAL_KEY = "DMM_AFFILIATE_ID"

EXPECTED_PRODUCT_URL = (
    "https://book.dmm.com/product/"
    "861056/b950yshes32617/"
)
EXPECTED_M6_AUTH_FILE_SHA256 = (
    "8e751212054d5722863984bec7faad5c"
    "0c851f28fdbebe18d5b441f34e36b4d9"
)
EXPECTED_M6_AUTH_DIGEST = (
    "0607dd3774aa592369a1a22ac2692372"
    "ad57d70fe3a70d5eee387d47a27ec3f5"
)
EXPECTED_M6_RESULT_DIGEST = (
    "c1e4d2eee53f598fd99995004525bc6f"
    "9cad18647c8b0d204302c55c39cbdea8"
)
EXPECTED_M6_APPROVAL_DIGEST = (
    "785085ee4b2a7043bd8f20df86141b32"
    "6c95beec9131c70f13e517b5c7c0a537"
)
EXPECTED_M5_REVIEW_DIGEST = (
    "92c59e79b7f8ff9b3dae934d1912f524"
    "9ccd4ce0c754cb5a5070e0b8264be892"
)
EXPECTED_CRED1_RESULT_DIGEST = (
    "7a173b74bef53781a3b2fe2e2cc2d3f3"
    "63a096b937508c241d454311d072ec7e"
)
EXPECTED_ARTICLE_FILE_SHA256 = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)

SOURCE_PATHS = {
    "m6_policy": ROOT / (
        "config/"
        "new_release_wp_fresh_dmm_final_affiliate_link_"
        "generation_authorization_gate_policy.json"
    ),
    "m6_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m6_"
        "authorization_gate_approval.json"
    ),
    "m6_authorization": ROOT / (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_final_affiliate_link_generation_authorization.json"
    ),
    "m6_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m6_result.json"
    ),
    "m5_review": ROOT / (
        "exchange/reviews/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_historical_m4_evidence_human_review.json"
    ),
    "cred1_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m6_cred1_result.json"
    ),
    "article": ROOT / (
        "exchange/content/new_release/fresh/"
        "new-release-comic-20260703-001.article.json"
    )
}

CRED1_COMMITMENT_CONTEXT = (
    b"LS-NEW-BATCH-4G-2E-RECOVERY-M6-CRED1"
    b"\x00DMM_AFFILIATE_ID\x00"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON_ROOT_NOT_OBJECT:{path.name}",
    )

    return value


def verify_self_digest(
    value: dict[str, Any],
    field: str,
    expected: str | None = None,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        canonical_digest(comparable) == stored,
        f"DIGEST_VERIFICATION_FAILED:{field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"EXPECTED_DIGEST_MISMATCH:{field}",
        )

    return stored


def fsync_directory(directory: Path) -> None:
    directory_fd = os.open(
        directory,
        os.O_RDONLY | os.O_DIRECTORY,
    )

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_atomic_exclusive_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.tmp.",
        dir=str(path.parent),
    )
    temporary_path = Path(temporary_name)

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            closefd=True,
        ) as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.link(temporary_path, path)
        temporary_path.unlink()
        fsync_directory(path.parent)

    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass

        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass

        raise


def write_atomic_exclusive_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.tmp.",
        dir=str(path.parent),
    )
    temporary_path = Path(temporary_name)

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            closefd=True,
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        os.link(temporary_path, path)
        temporary_path.unlink()
        fsync_directory(path.parent)

    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass

        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass

        raise


def strip_optional_quotes(value: str) -> str:
    value = value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]

    return value


def validate_identifier(identifier: str) -> None:
    require(
        identifier != "",
        "DMM_IDENTIFIER_EMPTY",
    )
    require(
        not any(
            character.isspace()
            for character in identifier
        ),
        "DMM_IDENTIFIER_WHITESPACE_REJECTED",
    )
    require(
        "://" not in identifier,
        "DMM_IDENTIFIER_URL_REJECTED",
    )
    require(
        re.fullmatch(
            r"[A-Za-z0-9]+-[0-9]{3}",
            identifier,
        )
        is not None,
        "DMM_IDENTIFIER_FORMAT_INVALID",
    )

    normalized = identifier.casefold()

    forbidden_exact = {
        "aaa-001",
        "test-001",
        "demo-001",
        "dummy-001",
        "sample-001",
        "example-001",
        "placeholder-001",
        "changeme-001",
        "yourid-001",
        "xxxx-001",
        "xxxxx-001",
        "post185-001",
    }

    forbidden_fragments = {
        "dummy",
        "sample",
        "example",
        "placeholder",
        "changeme",
        "yourid",
        "post185",
    }

    require(
        normalized not in forbidden_exact,
        "DMM_IDENTIFIER_DUMMY_REJECTED",
    )
    require(
        not any(
            fragment in normalized
            for fragment in forbidden_fragments
        ),
        "DMM_IDENTIFIER_PLACEHOLDER_REJECTED",
    )


def read_registered_identifier() -> tuple[str, dict[str, Any]]:
    require(
        CREDENTIAL_FILE.exists(),
        "CREDENTIAL_FILE_MISSING",
    )
    require(
        not CREDENTIAL_FILE.is_symlink(),
        "CREDENTIAL_FILE_SYMLINK_REJECTED",
    )
    require(
        CREDENTIAL_FILE.is_file(),
        "CREDENTIAL_FILE_NOT_REGULAR",
    )

    credential_stat = CREDENTIAL_FILE.stat()
    mode = stat.S_IMODE(credential_stat.st_mode)

    require(
        mode == 0o600,
        "CREDENTIAL_FILE_MODE_NOT_0600",
    )
    require(
        credential_stat.st_uid == os.geteuid(),
        "CREDENTIAL_FILE_OWNER_MISMATCH",
    )

    matches: list[str] = []

    for raw_line in CREDENTIAL_FILE.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        key, separator, raw_value = line.partition("=")

        if separator != "=":
            continue

        if key.strip() != CREDENTIAL_KEY:
            continue

        matches.append(
            strip_optional_quotes(raw_value)
        )

    require(
        len(matches) == 1,
        "DMM_IDENTIFIER_KEY_COUNT_MUST_BE_ONE",
    )

    identifier = matches[0]
    validate_identifier(identifier)

    metadata = {
        "source_path": str(CREDENTIAL_FILE),
        "source_key": CREDENTIAL_KEY,
        "source_file_mode": f"{mode:04o}",
        "source_owner_uid": credential_stat.st_uid,
        "source_owner_gid": credential_stat.st_gid,
        "source_owner_matches_execution_user": True,
        "source_is_regular_file": True,
        "source_is_symlink": False,
        "identifier_format_validated": True,
        "identifier_value_output": False,
        "identifier_value_persisted_in_normal_evidence": False
    }

    return identifier, metadata


def verify_cred1_commitment(
    identifier: str,
    cred1_result: dict[str, Any],
) -> None:
    commitment = cred1_result[
        "identifier_commitment"
    ]

    require(
        commitment["algorithm"]
        == "PBKDF2-HMAC-SHA256",
        "CRED1_COMMITMENT_ALGORITHM_MISMATCH",
    )

    calculated = hashlib.pbkdf2_hmac(
        "sha256",
        identifier.encode("utf-8"),
        (
            CRED1_COMMITMENT_CONTEXT
            + bytes.fromhex(
                commitment["salt_hex"]
            )
        ),
        commitment["iterations"],
    ).hex()

    require(
        calculated == commitment["commitment_hex"],
        "CRED1_IDENTIFIER_COMMITMENT_MISMATCH",
    )


def generate_final_url(identifier: str) -> str:
    query_pairs = [
        ("lurl", EXPECTED_PRODUCT_URL),
        ("af_id", identifier),
        ("ch", "link_tool"),
        ("ch_id", "link"),
    ]

    query = urlencode(
        query_pairs,
        doseq=False,
        safe="",
        encoding="utf-8",
        errors="strict",
        quote_via=quote,
    )

    return f"https://al.dmm.com/?{query}"


def validate_final_url(
    final_url: str,
    identifier: str,
) -> None:
    parsed = urlsplit(final_url)

    require(
        parsed.scheme == "https",
        "FINAL_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "al.dmm.com",
        "FINAL_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "FINAL_URL_EXPLICIT_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "FINAL_URL_USERINFO_REJECTED",
    )
    require(
        parsed.path == "/",
        "FINAL_URL_PATH_INVALID",
    )
    require(
        parsed.fragment == "",
        "FINAL_URL_FRAGMENT_REJECTED",
    )

    query_pairs = parse_qsl(
        parsed.query,
        keep_blank_values=True,
        strict_parsing=True,
        encoding="utf-8",
        errors="strict",
    )

    expected_pairs = [
        ("lurl", EXPECTED_PRODUCT_URL),
        ("af_id", identifier),
        ("ch", "link_tool"),
        ("ch_id", "link"),
    ]

    require(
        query_pairs == expected_pairs,
        "FINAL_URL_QUERY_BINDING_MISMATCH",
    )
    require(
        final_url != EXPECTED_PRODUCT_URL,
        "DIRECT_PRODUCT_URL_REJECTED",
    )
    require(
        "/latest" not in EXPECTED_PRODUCT_URL,
        "LATEST_ALIAS_REJECTED",
    )
    require(
        len(final_url) <= 2048,
        "FINAL_URL_LENGTH_LIMIT_EXCEEDED",
    )

    destination = urlsplit(EXPECTED_PRODUCT_URL)

    require(
        destination.scheme == "https",
        "DESTINATION_SCHEME_INVALID",
    )
    require(
        destination.hostname == "book.dmm.com",
        "DESTINATION_HOST_INVALID",
    )
    require(
        destination.port is None,
        "DESTINATION_EXPLICIT_PORT_REJECTED",
    )
    require(
        destination.path
        == "/product/861056/b950yshes32617/",
        "DESTINATION_PRODUCT_PATH_MISMATCH",
    )
    require(
        destination.query == ""
        and destination.fragment == "",
        "DESTINATION_QUERY_OR_FRAGMENT_REJECTED",
    )


def main() -> int:
    execution_boundary_crossed = False
    credential_hash_before: str | None = None
    source_hashes_before: dict[str, str] = {}
    consumption_digest: str | None = None

    try:
        for prohibited_existing in [
            CONSUMPTION,
            LINK_ARTIFACT,
            RESULT,
            REPORT,
        ]:
            require(
                not prohibited_existing.exists(),
                (
                    "M7_OUTPUT_ALREADY_EXISTS:"
                    + prohibited_existing.name
                ),
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        verify_self_digest(
            approval,
            "approval_evidence_digest_sha256",
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M7",
            "POLICY_PHASE_MISMATCH",
        )
        require(
            policy["execution_boundary"][
                "offline_final_affiliate_link_generation_allowed"
            ]
            is True,
            "OFFLINE_GENERATION_NOT_ALLOWED",
        )
        require(
            policy["execution_boundary"][
                "network_connection_allowed"
            ]
            is False,
            "NETWORK_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "article_modification_allowed"
            ]
            is False,
            "ARTICLE_BOUNDARY_OPEN",
        )
        require(
            policy["execution_boundary"][
                "wordpress_access_allowed"
            ]
            is False,
            "WORDPRESS_BOUNDARY_OPEN",
        )

        source_hashes_before = {
            label: file_sha256(path)
            for label, path in SOURCE_PATHS.items()
        }

        require(
            source_hashes_before["m6_authorization"]
            == EXPECTED_M6_AUTH_FILE_SHA256,
            "M6_AUTHORIZATION_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes_before["article"]
            == EXPECTED_ARTICLE_FILE_SHA256,
            "ARTICLE_FILE_SHA_MISMATCH",
        )

        m6_policy = load_json(
            SOURCE_PATHS["m6_policy"]
        )
        m6_approval = load_json(
            SOURCE_PATHS["m6_approval"]
        )
        m6_authorization = load_json(
            SOURCE_PATHS["m6_authorization"]
        )
        m6_result = load_json(
            SOURCE_PATHS["m6_result"]
        )
        m5_review = load_json(
            SOURCE_PATHS["m5_review"]
        )
        cred1_result = load_json(
            SOURCE_PATHS["cred1_result"]
        )

        verify_self_digest(
            m6_approval,
            "approval_evidence_digest_sha256",
            EXPECTED_M6_APPROVAL_DIGEST,
        )
        verify_self_digest(
            m6_authorization,
            "authorization_digest_sha256",
            EXPECTED_M6_AUTH_DIGEST,
        )
        verify_self_digest(
            m6_result,
            "result_digest_sha256",
            EXPECTED_M6_RESULT_DIGEST,
        )
        verify_self_digest(
            m5_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M5_REVIEW_DIGEST,
        )
        verify_self_digest(
            cred1_result,
            "result_digest_sha256",
            EXPECTED_CRED1_RESULT_DIGEST,
        )

        require(
            m6_policy["execution_boundary"][
                "final_affiliate_link_generation_allowed"
            ]
            is False,
            "M6_POLICY_WAS_MUTATED",
        )
        require(
            m6_authorization["authorization_id"]
            == (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "M6_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m6_authorization["single_use"] is True,
            "M6_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m6_authorization[
                "authorization_consumed"
            ]
            is False,
            "M6_AUTHORIZATION_ISSUANCE_STATE_INVALID",
        )
        require(
            m6_authorization[
                "authorization_reuse_allowed"
            ]
            is False,
            "M6_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m6_authorization[
                "automatic_retry_allowed"
            ]
            is False,
            "M6_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m6_authorization["authorized_input"][
                "verified_product_url"
            ]
            == EXPECTED_PRODUCT_URL,
            "M6_PRODUCT_URL_BINDING_MISMATCH",
        )
        require(
            m6_authorization[
                "required_output_contract"
            ]["scheme"]
            == "https",
            "M6_FINAL_SCHEME_CONTRACT_MISMATCH",
        )
        require(
            m6_authorization[
                "required_output_contract"
            ]["host"]
            == "al.dmm.com",
            "M6_FINAL_HOST_CONTRACT_MISMATCH",
        )
        require(
            m6_result["status"]
            == (
                "PASS_DMM_FINAL_AFFILIATE_LINK_"
                "GENERATION_ONE_SHOT_AUTHORIZATION_"
                "FIXED_NO_GENERATION_NO_NETWORK"
            ),
            "M6_RESULT_STATUS_MISMATCH",
        )
        require(
            m6_result[
                "ready_for_ls_new_batch_4g_2e_recovery_m7"
            ]
            is True,
            "M6_NOT_READY_FOR_M7",
        )
        require(
            m6_result[
                "authorization_consumed"
            ]
            is False,
            "M6_RESULT_ALREADY_CONSUMED",
        )

        for binding in m6_authorization[
            "source_bindings"
        ].values():
            bound_path = ROOT / binding["path"]

            require(
                bound_path.exists(),
                "M6_BOUND_SOURCE_MISSING",
            )
            require(
                file_sha256(bound_path)
                == binding["file_sha256"],
                "M6_BOUND_SOURCE_CHANGED",
            )

        require(
            cred1_result["status"]
            == (
                "PASS_DMM_AFFILIATE_IDENTIFIER_"
                "SECURELY_REGISTERED_NO_SECRET_"
                "OUTPUT_NO_NETWORK"
            ),
            "CRED1_STATUS_MISMATCH",
        )
        require(
            cred1_result[
                "ready_for_m6_authorization_gate_retry"
            ]
            is True,
            "CRED1_READINESS_MISMATCH",
        )

        identifier, identifier_metadata = (
            read_registered_identifier()
        )
        verify_cred1_commitment(
            identifier,
            cred1_result,
        )

        credential_hash_before = file_sha256(
            CREDENTIAL_FILE
        )

        attempt_id = str(uuid.uuid4())

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M7"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "source_authorization": {
                "path": str(
                    SOURCE_PATHS[
                        "m6_authorization"
                    ].relative_to(ROOT)
                ),
                "authorization_id": (
                    m6_authorization[
                        "authorization_id"
                    ]
                ),
                "authorization_file_sha256": (
                    EXPECTED_M6_AUTH_FILE_SHA256
                ),
                "authorization_digest_sha256": (
                    EXPECTED_M6_AUTH_DIGEST
                )
            },
            "authorized_operation": (
                "ONE_SHOT_OFFLINE_DMM_FINAL_"
                "AFFILIATE_LINK_GENERATION"
            ),
            "authorization_consumed": True,
            "consumption_state": (
                "CONSUMED_EXECUTION_BOUNDARY_CROSSED"
            ),
            "execution_boundary_crossed": True,
            "consumed_before_generation": True,
            "consumed_on_future_success_or_failure": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "verified_product_binding_sha256": (
                hashlib.sha256(
                    EXPECTED_PRODUCT_URL.encode("utf-8")
                ).hexdigest()
            ),
            "identifier_commitment_revalidated": True,
            "identifier_value_output": False,
            "identifier_value_persisted": False,
            "full_final_url_present": False,
            "network_connection_performed": False,
            "dmm_recheck_performed": False,
            "article_modification_performed": False,
            "wordpress_access_performed": False,
            "consumed_at_utc": utc_now()
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "consumption_evidence_digest_sha256"
        ] = canonical_digest(
            consumption_without_digest
        )

        write_atomic_exclusive_json(
            CONSUMPTION,
            consumption,
        )

        execution_boundary_crossed = True
        consumption_digest = consumption[
            "consumption_evidence_digest_sha256"
        ]

        final_url = generate_final_url(identifier)
        validate_final_url(
            final_url,
            identifier,
        )

        final_url_fingerprint = hashlib.sha256(
            final_url.encode("utf-8")
        ).hexdigest()

        link_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_FINAL_AFFILIATE_LINK_"
                "SECRET_ARTIFACT"
            ),
            "sensitivity": (
                "SECRET_AFFILIATE_LINK_MODE_0600"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M7"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "source_authorization_id": (
                m6_authorization[
                    "authorization_id"
                ]
            ),
            "source_authorization_digest_sha256": (
                EXPECTED_M6_AUTH_DIGEST
            ),
            "consumption_evidence_digest_sha256": (
                consumption_digest
            ),
            "final_affiliate_url": final_url,
            "final_affiliate_url_fingerprint_sha256": (
                final_url_fingerprint
            ),
            "verified_destination_url": (
                EXPECTED_PRODUCT_URL
            ),
            "verified_destination_url_sha256": (
                hashlib.sha256(
                    EXPECTED_PRODUCT_URL.encode(
                        "utf-8"
                    )
                ).hexdigest()
            ),
            "final_url_contract": {
                "scheme": "https",
                "host": "al.dmm.com",
                "path": "/",
                "query_parameter_order": [
                    "lurl",
                    "af_id",
                    "ch",
                    "ch_id"
                ],
                "lurl_exact_binding_verified": True,
                "af_id_exact_binding_verified": True,
                "ch_value": "link_tool",
                "ch_id_value": "link",
                "explicit_port_present": False,
                "userinfo_present": False,
                "fragment_present": False,
                "unknown_query_parameter_present": False
            },
            "identifier_binding": {
                **identifier_metadata,
                "cred1_result_digest_sha256": (
                    EXPECTED_CRED1_RESULT_DIGEST
                ),
                "cred1_commitment_revalidated": True,
                "identifier_value_separately_stored": False
            },
            "generated_offline": True,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "latest_alias_used": False,
            "past_article_link_reused": False,
            "post185_link_reused": False,
            "automatic_fallback_used": False,
            "article_url_injection_performed": False,
            "article_dmm_slot_activated": False,
            "article_modified": False,
            "fresh_payload_created": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "generated_at_utc": utc_now()
        }

        link_artifact = copy.deepcopy(
            link_without_digest
        )
        link_artifact[
            "secret_artifact_digest_sha256"
        ] = canonical_digest(link_without_digest)

        write_atomic_exclusive_json(
            LINK_ARTIFACT,
            link_artifact,
        )

        link_mode = stat.S_IMODE(
            LINK_ARTIFACT.stat().st_mode
        )

        require(
            link_mode == 0o600,
            "LINK_ARTIFACT_MODE_NOT_0600",
        )

        for label, path in SOURCE_PATHS.items():
            require(
                file_sha256(path)
                == source_hashes_before[label],
                f"SOURCE_ARTIFACT_CHANGED:{label}",
            )

        require(
            file_sha256(CREDENTIAL_FILE)
            == credential_hash_before,
            "CREDENTIAL_FILE_CHANGED",
        )

        identifier_after, _ = (
            read_registered_identifier()
        )

        require(
            identifier_after == identifier,
            "IDENTIFIER_CHANGED_DURING_EXECUTION",
        )

        verify_cred1_commitment(
            identifier_after,
            cred1_result,
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M7"
            ),
            "status": (
                "PASS_DMM_FINAL_AFFILIATE_LINK_"
                "GENERATED_OFFLINE_AUTHORIZATION_"
                "CONSUMED_NO_NETWORK"
            ),
            "decision": (
                "DMM_FINAL_AFFILIATE_LINK_SECRET_"
                "ARTIFACT_READY_FOR_HUMAN_REVIEW_"
                "AND_ARTICLE_INJECTION_GATE"
            ),
            "approval_label": (
                "DMM_FINAL_AFFILIATE_LINK_ONE_SHOT_"
                "GENERATION_EXECUTE_NOW_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "consumption_attempt_id": attempt_id,
            "authorization_consumption_path": str(
                CONSUMPTION.relative_to(ROOT)
            ),
            "authorization_consumption_file_sha256": (
                file_sha256(CONSUMPTION)
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "link_artifact_path": str(
                LINK_ARTIFACT.relative_to(ROOT)
            ),
            "link_artifact_file_sha256": (
                file_sha256(LINK_ARTIFACT)
            ),
            "link_artifact_digest_sha256": (
                link_artifact[
                    "secret_artifact_digest_sha256"
                ]
            ),
            "link_artifact_mode": f"{link_mode:04o}",
            "final_affiliate_url_fingerprint_sha256": (
                final_url_fingerprint
            ),
            "full_final_affiliate_url_output": False,
            "full_final_affiliate_url_in_normal_evidence": False,
            "affiliate_identifier_output": False,
            "affiliate_identifier_in_normal_evidence": False,
            "required_final_scheme_verified": True,
            "required_final_host_verified": True,
            "destination_exact_binding_verified": True,
            "registered_identifier_exact_binding_verified": True,
            "cred1_commitment_revalidated": True,
            "m6_authorization_modified": False,
            "m5_evidence_modified": False,
            "cred1_evidence_modified": False,
            "credential_file_modified": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "article_dmm_slot_activated": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_FINAL_LINK_GENERATED_SECRET_"
                "ARTIFACT_ONLY_AWAITING_HUMAN_REVIEW"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m8": True,
            "ready_for_article_url_injection": False,
            "ready_for_article_dmm_slot_activation": False,
            "ready_for_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "completed_at_utc": utc_now()
        }

        result = copy.deepcopy(result_without_digest)
        result[
            "result_digest_sha256"
        ] = canonical_digest(result_without_digest)

        write_atomic_exclusive_json(
            RESULT,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M7

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Authorization consumed: `true`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Link artifact path: `{result["link_artifact_path"]}`
- Link artifact mode: `0600`
- Full final URL output: `false`
- Affiliate identifier output: `false`
- Final URL fingerprint: `{final_url_fingerprint}`
- Required scheme verified: `true`
- Required host verified: `true`
- Destination exact binding verified: `true`
- Identifier exact binding verified: `true`
- CRED1 commitment revalidated: `true`
- Network accessed: `false`
- DMM recheck performed: `false`
- Article URL injected: `false`
- DMM slot activated: `false`
- Article modified: `false`
- Payload created: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for M8 human review gate: `true`
"""

        write_atomic_exclusive_text(
            REPORT,
            report,
        )

        del identifier
        del identifier_after
        del final_url

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except Exception as exc:
        controlled_error = (
            str(exc)
            if isinstance(exc, ValidationError)
            else "UNEXPECTED_M7_EXECUTION_FAILURE"
        )

        if execution_boundary_crossed:
            try:
                LINK_ARTIFACT.unlink()
            except FileNotFoundError:
                pass

            failure_without_digest = {
                "schema_version": "1.0.0",
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-RECOVERY-M7"
                ),
                "status": (
                    "FAILED_AFTER_AUTHORIZATION_"
                    "CONSUMPTION_NO_AUTOMATIC_RETRY"
                ),
                "decision": (
                    "M6_AUTHORIZATION_CONSUMED_"
                    "MANUAL_RECOVERY_REVIEW_REQUIRED"
                ),
                "error_code": controlled_error,
                "authorization_consumed": True,
                "authorization_reuse_allowed": False,
                "automatic_retry_allowed": False,
                "consumption_evidence_preserved": (
                    CONSUMPTION.exists()
                ),
                "consumption_evidence_digest_sha256": (
                    consumption_digest
                ),
                "secret_link_artifact_preserved": False,
                "full_final_affiliate_url_output": False,
                "affiliate_identifier_output": False,
                "network_connection_performed": False,
                "dmm_recheck_performed": False,
                "article_modified": False,
                "article_url_injection_performed": False,
                "article_dmm_slot_activated": False,
                "fresh_payload_created": False,
                "wordpress_access_performed": False,
                "production_status": "NO_GO",
                "ready_for_automatic_retry": False,
                "manual_recovery_review_required": True,
                "failed_at_utc": utc_now()
            }

            failure = copy.deepcopy(
                failure_without_digest
            )
            failure[
                "result_digest_sha256"
            ] = canonical_digest(
                failure_without_digest
            )

            try:
                write_atomic_exclusive_json(
                    RESULT,
                    failure,
                )
            except Exception:
                pass

            try:
                write_atomic_exclusive_text(
                    REPORT,
                    (
                        "# LS-NEW-BATCH-4G-2E-RECOVERY-M7\n\n"
                        "- Status: "
                        "`FAILED_AFTER_AUTHORIZATION_CONSUMPTION_"
                        "NO_AUTOMATIC_RETRY`\n"
                        "- Authorization consumed: `true`\n"
                        "- Automatic retry allowed: `false`\n"
                        "- Full final URL output: `false`\n"
                        "- Affiliate identifier output: `false`\n"
                        "- Production status: `NO_GO`\n"
                        "- Manual recovery review required: `true`\n"
                    ),
                )
            except Exception:
                pass

            print(
                json.dumps(
                    failure,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )

            return 1

        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M7"
                    ),
                    "status": (
                        "BLOCKED_BEFORE_AUTHORIZATION_"
                        "CONSUMPTION"
                    ),
                    "error_code": controlled_error,
                    "authorization_consumed": False,
                    "authorization_reuse_allowed": False,
                    "automatic_retry_allowed": False,
                    "full_final_affiliate_url_output": False,
                    "affiliate_identifier_output": False,
                    "network_connection_performed": False,
                    "article_modified": False,
                    "wordpress_access_performed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
