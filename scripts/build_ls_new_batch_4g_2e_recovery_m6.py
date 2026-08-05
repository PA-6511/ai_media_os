#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_final_affiliate_link_"
    "generation_authorization_gate_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m6_"
    "authorization_gate_approval.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m6_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m6_"
    "final_affiliate_link_generation_"
    "authorization_gate_report.md"
)

CREDENTIAL_FILE = Path(
    "/etc/ai-media-os/credential.env"
)
CREDENTIAL_KEY = "DMM_AFFILIATE_ID"

EXPECTED_PRODUCT_URL = (
    "https://book.dmm.com/product/"
    "861056/b950yshes32617/"
)

EXPECTED_FILE_HASHES = {
    "m5_policy": (
        "d256052c6408d5e659d4805e90e444a8"
        "304b2749dc11c068ecf8714199b391de"
    ),
    "m5_fix1_approval": (
        "1467ddf8e101b391dd5794a3ba8cc819"
        "de52dbeac68dd20c8f6a0aa35d515b34"
    ),
    "m5_approval": (
        "04ddd0aa521b9796be11ab5643162eb5a"
        "695b5741fbbcd54975ea52754a4e884"
    ),
    "m5_review": (
        "29411ef1792b95f5d807d6eef3c22984"
        "84b53e116ccfc5a7cdc19b0eb90d2ccd"
    ),
    "m5_result": (
        "23c03cf88e923c79e37b0e6d1ccca227"
        "14855db3dba905d00b3d2fddc8f980ea"
    ),
    "cred1_policy": (
        "49a35085687254929fb36a0dd4c2c15f"
        "c8aab8a93f98c39b5eaad9927d316101"
    )
}

EXPECTED_DIGESTS = {
    "m5_review": (
        "92c59e79b7f8ff9b3dae934d1912f524"
        "9ccd4ce0c754cb5a5070e0b8264be892"
    ),
    "m5_fix1": (
        "140022e0587adeee27510ed2bf3c7e697"
        "d8a24109f69813639d8bd9882f4ed94"
    ),
    "cred1_approval": (
        "68f7249c35c44fb891a36e12b160d648"
        "d29bacffe9b64a511f13c3161609d6ab"
    ),
    "cred1_result": (
        "7a173b74bef53781a3b2fe2e2cc2d3f3"
        "63a096b937508c241d454311d072ec7e"
    )
}

SOURCE_PATHS = {
    "m5_policy": ROOT / (
        "config/"
        "new_release_wp_fresh_dmm_historical_m4_"
        "evidence_human_review_policy.json"
    ),
    "m5_fix1_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m5_fix1_"
        "policy_schema_fix_approval.json"
    ),
    "m5_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m5_"
        "historical_evidence_human_review_approval.json"
    ),
    "m5_review": ROOT / (
        "exchange/reviews/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_historical_m4_evidence_human_review.json"
    ),
    "m5_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m5_result.json"
    ),
    "m5_fix1_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m5_fix1_result.json"
    ),
    "cred1_policy": ROOT / (
        "config/"
        "new_release_wp_fresh_dmm_affiliate_identifier_"
        "secure_registration_policy.json"
    ),
    "cred1_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m6_cred1_"
        "secure_registration_approval.json"
    ),
    "cred1_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m6_cred1_result.json"
    )
}

CRED1_COMMITMENT_CONTEXT = (
    b"LS-NEW-BATCH-4G-2E-RECOVERY-M6-CRED1"
    b"\x00DMM_AFFILIATE_ID\x00"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"required file missing: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
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
        f"digest field missing: {field}",
    )
    require(
        digest(comparable) == stored,
        f"digest verification failed: {field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"digest mismatch: {field}",
        )

    return stored


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
        "DMM_AFFILIATE_IDENTIFIER_EMPTY",
    )
    require(
        not any(
            character.isspace()
            for character in identifier
        ),
        "DMM_AFFILIATE_IDENTIFIER_WHITESPACE_REJECTED",
    )
    require(
        "://" not in identifier,
        "DMM_AFFILIATE_IDENTIFIER_URL_REJECTED",
    )
    require(
        re.fullmatch(
            r"[A-Za-z0-9]+-[0-9]{3}",
            identifier,
        )
        is not None,
        "DMM_AFFILIATE_IDENTIFIER_FORMAT_INVALID",
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
        "DMM_AFFILIATE_IDENTIFIER_DUMMY_REJECTED",
    )
    require(
        not any(
            fragment in normalized
            for fragment in forbidden_fragments
        ),
        "DMM_AFFILIATE_IDENTIFIER_PLACEHOLDER_REJECTED",
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
    mode = stat.S_IMODE(
        credential_stat.st_mode
    )

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

        key, separator, raw_value = (
            line.partition("=")
        )

        if separator != "=":
            continue

        if key.strip() != CREDENTIAL_KEY:
            continue

        matches.append(
            strip_optional_quotes(raw_value)
        )

    require(
        len(matches) == 1,
        "DMM_AFFILIATE_IDENTIFIER_KEY_COUNT_MUST_BE_ONE",
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
        "identifier_value_persisted_in_authorization": False
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
        calculated
        == commitment["commitment_hex"],
        "CRED1_IDENTIFIER_COMMITMENT_MISMATCH",
    )


def write_exclusive_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
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


def write_exclusive_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    try:
        policy = load_json(POLICY)
        boundary = policy[
            "execution_boundary"
        ]

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M6",
            "policy phase mismatch",
        )
        require(
            boundary[
                "authorization_artifact_creation_allowed"
            ]
            is True,
            "authorization creation not allowed",
        )
        require(
            boundary[
                "final_affiliate_link_generation_allowed"
            ]
            is False,
            "link generation boundary must remain closed",
        )
        require(
            boundary["network_connection_allowed"]
            is False,
            "network boundary must remain closed",
        )
        require(
            boundary[
                "historical_result_reclassification_allowed"
            ]
            is False,
            "historical reclassification boundary open",
        )

        source_hashes_before = {
            label: file_sha256(path)
            for label, path in SOURCE_PATHS.items()
        }

        for label, expected in (
            EXPECTED_FILE_HASHES.items()
        ):
            require(
                source_hashes_before[label]
                == expected,
                f"source file hash mismatch: {label}",
            )

        m5_approval = load_json(
            SOURCE_PATHS["m5_approval"]
        )
        m5_review = load_json(
            SOURCE_PATHS["m5_review"]
        )
        m5_result = load_json(
            SOURCE_PATHS["m5_result"]
        )
        m5_fix1 = load_json(
            SOURCE_PATHS["m5_fix1_result"]
        )
        cred1_approval = load_json(
            SOURCE_PATHS["cred1_approval"]
        )
        cred1_result = load_json(
            SOURCE_PATHS["cred1_result"]
        )

        verify_self_digest(
            m5_review,
            "human_review_evidence_digest_sha256",
            EXPECTED_DIGESTS["m5_review"],
        )
        verify_self_digest(
            m5_fix1,
            "fix_evidence_digest_sha256",
            EXPECTED_DIGESTS["m5_fix1"],
        )
        verify_self_digest(
            cred1_approval,
            "approval_evidence_digest_sha256",
            EXPECTED_DIGESTS["cred1_approval"],
        )
        verify_self_digest(
            cred1_result,
            "result_digest_sha256",
            EXPECTED_DIGESTS["cred1_result"],
        )

        require(
            m5_result["status"]
            == (
                "PASS_DMM_HISTORICAL_M4_EVIDENCE_"
                "HUMAN_REVIEW_APPROVED_NO_NETWORK_"
                "NO_RECLASSIFICATION"
            ),
            "M5 status mismatch",
        )
        require(
            m5_result["review_verdict"]
            == (
                "APPROVED_HISTORICAL_EVIDENCE_"
                "AS_DMM_PRODUCT_MATCH"
            ),
            "M5 review verdict mismatch",
        )
        require(
            m5_result[
                "verified_product_url_candidate"
            ]
            == EXPECTED_PRODUCT_URL,
            "verified product URL mismatch",
        )
        require(
            m5_result[
                "ready_for_final_affiliate_link_generation_gate"
            ]
            is True,
            "M5 not ready for M6 gate",
        )
        require(
            m5_result[
                "ready_for_final_affiliate_link_generation"
            ]
            is False,
            "M5 already allows generation unexpectedly",
        )
        require(
            m5_result[
                "historical_m4_result_reclassified"
            ]
            is False,
            "historical result reclassified",
        )

        require(
            cred1_result["status"]
            == (
                "PASS_DMM_AFFILIATE_IDENTIFIER_"
                "SECURELY_REGISTERED_NO_SECRET_"
                "OUTPUT_NO_NETWORK"
            ),
            "CRED1 status mismatch",
        )
        require(
            cred1_result[
                "ready_for_m6_authorization_gate_retry"
            ]
            is True,
            "CRED1 not ready for M6 retry",
        )
        require(
            cred1_result[
                "credential_target"
            ]["key_count_after"] == 1,
            "CRED1 key count mismatch",
        )
        require(
            cred1_result[
                "identifier_validation"
            ]["identifier_value_output"] is False,
            "CRED1 secret output boundary changed",
        )
        require(
            cred1_result[
                "identifier_validation"
            ][
                "identifier_value_persisted_in_evidence"
            ]
            is False,
            "CRED1 secret persistence boundary changed",
        )

        historical_bindings = m5_approval[
            "source_bindings"
        ]

        for binding in historical_bindings.values():
            historical_path = ROOT / binding["path"]

            require(
                historical_path.exists(),
                (
                    "M5_BOUND_HISTORICAL_SOURCE_MISSING:"
                    + binding["path"]
                ),
            )
            require(
                file_sha256(historical_path)
                == binding["file_sha256"],
                (
                    "M5_BOUND_HISTORICAL_SOURCE_CHANGED:"
                    + binding["path"]
                ),
            )

        identifier, identifier_metadata = (
            read_registered_identifier()
        )

        verify_cred1_commitment(
            identifier,
            cred1_result,
        )

        source_bindings = {
            label: {
                "path": str(
                    path.relative_to(ROOT)
                ),
                "file_sha256": (
                    source_hashes_before[label]
                )
            }
            for label, path in SOURCE_PATHS.items()
        }

        credential_binding = {
            **identifier_metadata,
            "registration_phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M6-CRED1"
            ),
            "registration_result_path": str(
                SOURCE_PATHS[
                    "cred1_result"
                ].relative_to(ROOT)
            ),
            "registration_result_digest_sha256": (
                EXPECTED_DIGESTS[
                    "cred1_result"
                ]
            ),
            "registration_commitment_algorithm": (
                cred1_result[
                    "identifier_commitment"
                ]["algorithm"]
            ),
            "registration_commitment_iterations": (
                cred1_result[
                    "identifier_commitment"
                ]["iterations"]
            ),
            "registration_commitment_salt_hex": (
                cred1_result[
                    "identifier_commitment"
                ]["salt_hex"]
            ),
            "registration_commitment_hex": (
                cred1_result[
                    "identifier_commitment"
                ]["commitment_hex"]
            ),
            "registration_commitment_revalidated": True,
            "identifier_value_present": False
        }

        approval_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M6"
            ),
            "approval_id": (
                "dmm-final-affiliate-link-generation-"
                "authorization-gate-approval-v1"
            ),
            "approval_label": (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "AUTHORIZATION_GATE_APPROVED"
            ),
            "approved_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "approved_at_utc": utc_now(),
            "approved_product_url": (
                EXPECTED_PRODUCT_URL
            ),
            "approved_final_url_contract": {
                "scheme": "https",
                "host": "al.dmm.com",
                "explicit_port_allowed": False,
                "userinfo_allowed": False,
                "destination_exact_binding_required": True,
                "registered_identifier_exact_binding_required": True,
                "latest_alias_allowed": False,
                "past_article_link_reuse_allowed": False,
                "post185_link_reuse_allowed": False,
                "automatic_fallback_allowed": False
            },
            "approved_identifier_binding": (
                credential_binding
            ),
            "approved_boundaries": {
                "single_use_authorization": True,
                "initially_unconsumed": True,
                "reuse_allowed": False,
                "automatic_retry_allowed": False,
                "actual_link_generation_allowed": False,
                "network_access_allowed": False,
                "dmm_recheck_allowed": False,
                "article_modification_allowed": False,
                "article_url_injection_allowed": False,
                "payload_generation_allowed": False,
                "wordpress_access_allowed": False
            },
            "source_bindings": source_bindings,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        approval = copy.deepcopy(
            approval_without_digest
        )
        approval[
            "approval_evidence_digest_sha256"
        ] = digest(approval_without_digest)

        write_exclusive_json(
            APPROVAL,
            approval,
        )

        authorization_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "ONE_SHOT_AUTHORIZATION"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M6"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_id": (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "approval_label": (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "AUTHORIZATION_GATE_APPROVED"
            ),
            "authorized_operation": (
                "ONE_SHOT_OFFLINE_DMM_FINAL_"
                "AFFILIATE_LINK_GENERATION"
            ),
            "authorized_input": {
                "verified_product_url": (
                    EXPECTED_PRODUCT_URL
                ),
                "verified_product_url_role": (
                    "VERIFIED_DMM_PRODUCT_URL_"
                    "CANDIDATE_ONLY"
                ),
                "work_title": "ダークギャザリング",
                "volume": "第20巻",
                "series_id": "861056",
                "author": "近藤憲一",
                "publisher": "集英社"
            },
            "required_output_contract": {
                "scheme": "https",
                "host": "al.dmm.com",
                "explicit_port_allowed": False,
                "userinfo_allowed": False,
                "destination_exact_binding_required": True,
                "registered_identifier_exact_binding_required": True,
                "latest_alias_allowed": False,
                "direct_product_url_as_final_link_allowed": False,
                "verification_source_url_as_final_link_allowed": False,
                "past_article_link_reuse_allowed": False,
                "post185_link_reuse_allowed": False,
                "automatic_fallback_url_allowed": False,
                "dummy_or_placeholder_url_allowed": False
            },
            "affiliate_identifier_binding": (
                credential_binding
            ),
            "single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "actual_generation_requires_execute_now_approval": True,
            "actual_generation_allowed": False,
            "planned_execution_phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M7"
            ),
            "planned_consumption_path": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "dmm_final_affiliate_link_generation_"
                "consumption.json"
            ),
            "planned_result_path": (
                "exchange/links/new_release/fresh/"
                "new-release-comic-20260703-001."
                "dmm_final_affiliate_link_generation_"
                "result.json"
            ),
            "approval_path": str(
                APPROVAL.relative_to(ROOT)
            ),
            "approval_digest_sha256": (
                approval[
                    "approval_evidence_digest_sha256"
                ]
            ),
            "source_bindings": source_bindings,
            "historical_result_reclassified": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "final_affiliate_link_generated": False,
            "final_affiliate_link_validated": False,
            "article_dmm_slot_activated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "authorized_at_utc": utc_now()
        }

        authorization = copy.deepcopy(
            authorization_without_digest
        )
        authorization[
            "authorization_digest_sha256"
        ] = digest(
            authorization_without_digest
        )

        write_exclusive_json(
            AUTHORIZATION,
            authorization,
        )

        for label, path in SOURCE_PATHS.items():
            require(
                file_sha256(path)
                == source_hashes_before[label],
                f"source artifact modified: {label}",
            )

        verify_cred1_commitment(
            identifier,
            cred1_result,
        )

        result_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M6"
            ),
            "status": (
                "PASS_DMM_FINAL_AFFILIATE_LINK_"
                "GENERATION_ONE_SHOT_AUTHORIZATION_"
                "FIXED_NO_GENERATION_NO_NETWORK"
            ),
            "decision": (
                "DMM_FINAL_LINK_GENERATION_"
                "AUTHORIZATION_RECORDED_AWAITING_"
                "EXPLICIT_EXECUTE_NOW_CONFIRMATION"
            ),
            "approval_label": (
                "DMM_FINAL_AFFILIATE_LINK_GENERATION_"
                "AUTHORIZATION_GATE_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_path": str(
                AUTHORIZATION.relative_to(ROOT)
            ),
            "authorization_file_sha256": (
                file_sha256(AUTHORIZATION)
            ),
            "authorization_digest_sha256": (
                authorization[
                    "authorization_digest_sha256"
                ]
            ),
            "authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "verified_product_url": (
                EXPECTED_PRODUCT_URL
            ),
            "required_final_scheme": "https",
            "required_final_host": "al.dmm.com",
            "affiliate_identifier_source_approved": True,
            "affiliate_identifier_format_validated": True,
            "cred1_commitment_revalidated": True,
            "affiliate_identifier_value_output": False,
            "affiliate_identifier_value_persisted": False,
            "authorization_single_use": True,
            "authorization_consumed": False,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "historical_m4_result_modified": False,
            "historical_m4_result_reclassified": False,
            "historical_m5_review_modified": False,
            "historical_cred1_result_modified": False,
            "credential_value_modified": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "final_affiliate_link_generated": False,
            "final_affiliate_link_validated": False,
            "article_dmm_slot_activated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_FINAL_LINK_GENERATION_"
                "AUTHORIZATION_RECORDED_UNCONSUMED_"
                "AWAITING_EXECUTE_NOW_APPROVAL"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m7": True,
            "ready_for_final_affiliate_link_generation": False,
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "completed_at_utc": utc_now()
        }

        result = copy.deepcopy(
            result_without_digest
        )
        result[
            "result_digest_sha256"
        ] = digest(result_without_digest)

        write_exclusive_json(
            RESULT,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M6

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Verified product URL: `{EXPECTED_PRODUCT_URL}`
- Required final scheme: `https`
- Required final host: `al.dmm.com`
- Identifier source: `{CREDENTIAL_FILE}`
- Identifier key: `{CREDENTIAL_KEY}`
- CRED1 commitment revalidated: `true`
- Identifier value output: `false`
- Identifier value persisted: `false`
- Authorization single use: `true`
- Authorization consumed: `false`
- Authorization reuse allowed: `false`
- Network accessed: `false`
- Final affiliate link generated: `false`
- Article modified: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for M7 execute-now gate: `true`
"""

        write_exclusive_text(
            REPORT,
            report,
        )

        del identifier

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-M6"
                    ),
                    "status": (
                        "BLOCKED_DMM_FINAL_AFFILIATE_LINK_"
                        "GENERATION_AUTHORIZATION_GATE"
                    ),
                    "error": str(exc),
                    "authorization_created": False,
                    "identifier_value_output": False,
                    "network_connection_performed": False,
                    "final_affiliate_link_generated": False,
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
