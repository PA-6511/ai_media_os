#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "one_shot_recheck_policy.json"
)
REQUEST_PATH = ROOT / (
    "exchange/examples/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_execute_request.example.json"
)
PARSER_RUNNER_PATH = ROOT / (
    "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m2.py"
)
CONSUMPTION_PATH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "consumption.json"
)
RECHECK_RESULT_PATH = ROOT / (
    "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "result.json"
)
PACKAGE_PATH = ROOT / (
    "exchange/examples/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_result_package.example.json"
)
RESULT_PATH = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m4_result.json"
)
REPORT_PATH = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m4_"
    "post_parser_fix_dmm_recheck_report.md"
)

EXPECTED_RUNNER_SHA256 = (
    "f28ec2df1816e102673831ea9e8dfde0"
    "db2df7df668324925f6b7f1441e306aa"
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


def json_bytes(
    value: dict[str, Any],
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_bytes(
        json_bytes(value)
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        value,
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


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

    try:
        with os.fdopen(
            fd,
            "wb",
            closefd=True,
        ) as handle:
            handle.write(
                json_bytes(value)
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise

    directory_fd = os.open(
        path.parent,
        os.O_RDONLY,
    )

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def resolve(value: str) -> Path:
    path = Path(value)

    return (
        path
        if path.is_absolute()
        else ROOT / path
    )


def display(path: Path) -> str:
    return str(
        path.resolve().relative_to(
            ROOT.resolve()
        )
    )


def verify_self_digest(
    value: dict[str, Any],
    field: str,
    expected: str,
    label: str,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        f"{label} digest invalid",
    )
    require(
        stored == expected,
        f"{label} digest mismatch",
    )

    return stored


def canonical_product_url_binds_to_expected_series(
    value: str | None,
    *,
    expected_series_id: str,
) -> bool:
    if not isinstance(value, str) or not value:
        return False

    parsed = urllib.parse.urlparse(value)

    if parsed.scheme != "https":
        return False

    if parsed.hostname != "book.dmm.com":
        return False

    try:
        if parsed.port is not None:
            return False
    except ValueError:
        return False

    if parsed.username or parsed.password:
        return False

    if parsed.query or parsed.fragment:
        return False

    match = re.fullmatch(
        r"/product/([^/]+)/([^/]+)/",
        parsed.path,
    )

    if match is None:
        return False

    series_id = match.group(1)
    product_id = match.group(2)

    if series_id != expected_series_id:
        return False

    if product_id.lower() == "latest":
        return False

    if re.fullmatch(
        r"[A-Za-z0-9_-]+",
        product_id,
    ) is None:
        return False

    return True


def load_parser_module() -> ModuleType:
    require(
        file_sha256(PARSER_RUNNER_PATH)
        == EXPECTED_RUNNER_SHA256,
        "remediated parser runner hash mismatch",
    )

    spec = importlib.util.spec_from_file_location(
        "recovery_m4_bound_parser",
        PARSER_RUNNER_PATH,
    )

    require(
        spec is not None
        and spec.loader is not None,
        "failed to create parser module spec",
    )

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def terminal_state() -> int | None:
    result_exists = (
        RECHECK_RESULT_PATH.exists()
    )
    consumption_exists = (
        CONSUMPTION_PATH.exists()
    )

    if (
        not result_exists
        and not consumption_exists
    ):
        return None

    if (
        result_exists
        and consumption_exists
    ):
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M4"
                    ),
                    "status": (
                        "BLOCKED_POST_FIX_DMM_RECHECK_"
                        "AUTHORIZATION_ALREADY_CONSUMED"
                    ),
                    "recheck_result_exists": True,
                    "consumption_evidence_exists": True,
                    "authorization_reuse_allowed": False,
                    "automatic_retry_allowed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3

    print(
        json.dumps(
            {
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-"
                    "RECOVERY-M4"
                ),
                "status": (
                    "FAIL_CLOSED_PARTIAL_POST_FIX_"
                    "DMM_RECHECK_TERMINAL_STATE"
                ),
                "recheck_result_exists": (
                    result_exists
                ),
                "consumption_evidence_exists": (
                    consumption_exists
                ),
                "automatic_repair_allowed": False,
                "authorization_reuse_allowed": False,
                "production_status": "NO_GO"
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 4


def validate_preflight(
    policy: dict[str, Any],
    request: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M4",
        "policy phase mismatch",
    )
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M4",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "operation mode mismatch",
    )
    require(
        request.get("method") == "GET",
        "method must be GET",
    )
    require(
        request.get("target_url")
        == policy["request_contract"][
            "target_url"
        ],
        "target URL mismatch",
    )

    for field in [
        "one_shot_network_get_requested",
        "new_authorization_consumption_requested",
        "new_consumption_evidence_creation_requested",
        "new_recheck_result_creation_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "automatic_retry_requested",
        "authentication_requested",
        "cookie_send_requested",
        "cookie_persistence_requested",
        "login_requested",
        "credential_file_read_requested",
        "request_body_requested",
        "write_operation_requested",
        "proxy_environment_use_requested",
        "full_response_body_persistence_requested",
        "final_affiliate_link_generation_requested",
        "article_modification_requested",
        "article_url_injection_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_publish_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    bindings = request["source_bindings"]

    json_specs = {
        "m3_authorization": (
            "m3_authorization_path",
            "m3_authorization_file_sha256",
            "authorization_digest_sha256",
            "m3_authorization_artifact_digest_sha256",
        ),
        "m3_approval": (
            "m3_approval_path",
            "m3_approval_file_sha256",
            "approval_evidence_digest_sha256",
            "m3_approval_artifact_digest_sha256",
        ),
        "m2_fix1": (
            "m2_fix1_result_path",
            "m2_fix1_result_file_sha256",
            "fix_evidence_digest_sha256",
            "m2_fix1_artifact_digest_sha256",
        ),
        "old_recheck": (
            "old_m2_recheck_result_path",
            "old_m2_recheck_result_file_sha256",
            "dmm_recheck_result_digest_sha256",
            "old_m2_recheck_result_artifact_digest_sha256",
        ),
        "old_consumption": (
            "old_m2_consumption_path",
            "old_m2_consumption_file_sha256",
            "consumption_evidence_digest_sha256",
            "old_m2_consumption_artifact_digest_sha256",
        ),
        "old_execute_approval": (
            "old_m2_execute_approval_path",
            "old_m2_execute_approval_file_sha256",
            "approval_evidence_digest_sha256",
            "old_m2_execute_approval_artifact_digest_sha256",
        ),
        "old_m1_authorization": (
            "old_m1_authorization_path",
            "old_m1_authorization_file_sha256",
            "authorization_digest_sha256",
            "old_m1_authorization_artifact_digest_sha256",
        ),
        "article": (
            "generated_article_path",
            "generated_article_file_sha256",
            "article_content_digest_sha256",
            "generated_article_artifact_digest_sha256",
        ),
        "plan": (
            "store_link_plan_path",
            "store_link_plan_file_sha256",
            "store_link_finalization_plan_digest_sha256",
            "store_link_plan_artifact_digest_sha256",
        ),
    }

    values: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}

    for label, (
        path_field,
        hash_field,
        digest_field,
        digest_reference_field,
    ) in json_specs.items():
        path = resolve(
            bindings[path_field]
        )

        require(
            file_sha256(path)
            == bindings[hash_field],
            f"{label} file hash mismatch",
        )

        value = load_json(path)

        verify_self_digest(
            value,
            digest_field,
            bindings[
                digest_reference_field
            ],
            label,
        )

        paths[label] = path
        values[label] = value

    for label, (
        path_field,
        hash_field,
    ) in {
        "m3_result": (
            "m3_result_path",
            "m3_result_file_sha256",
        ),
        "old_m2_result": (
            "old_m2_result_path",
            "old_m2_result_file_sha256",
        ),
        "runner": (
            "remediated_runner_path",
            "remediated_runner_file_sha256",
        ),
    }.items():
        path = resolve(
            bindings[path_field]
        )

        require(
            file_sha256(path)
            == bindings[hash_field],
            f"{label} file hash mismatch",
        )

        paths[label] = path

        if label != "runner":
            values[label] = load_json(path)

    require(
        file_sha256(paths["runner"])
        == EXPECTED_RUNNER_SHA256,
        "runner SHA-256 mismatch",
    )
    require(
        values["m3_result"]["status"]
        == (
            "PASS_DMM_RECHECK_POST_REMEDIATION_"
            "ONE_SHOT_AUTHORIZATION_FIXED_NO_NETWORK"
        ),
        "M3 status mismatch",
    )

    authorization = values[
        "m3_authorization"
    ]

    require(
        authorization["authorization_id"]
        == (
            "DMM_LATEST_ALIAS_861056_POST_"
            "PARSER_FIX_ONE_SHOT_READ_ONLY_"
            "RECHECK_AUTHORIZATION_V1"
        ),
        "authorization ID mismatch",
    )
    require(
        authorization[
            "authorization_consumed"
        ]
        is False,
        "new authorization already consumed",
    )
    require(
        authorization[
            "authorization_reuse_allowed"
        ]
        is False,
        "authorization reuse contract mismatch",
    )
    require(
        authorization[
            "parser_binding"
        ]["runner_file_sha256"]
        == EXPECTED_RUNNER_SHA256,
        "authorization parser binding mismatch",
    )
    require(
        authorization[
            "target_request"
        ]["method"]
        == "GET",
        "authorization method mismatch",
    )
    require(
        authorization[
            "target_request"
        ]["url"]
        == request["target_url"],
        "authorization target mismatch",
    )

    require(
        values["old_m2_result"][
            "authorization_consumed"
        ]
        is True,
        "old authorization consumption missing",
    )
    require(
        values["old_consumption"][
            "consumption_is_authoritative"
        ]
        is True,
        "old consumption not authoritative",
    )
    require(
        values["old_recheck"]["network"][
            "response_body_sha256"
        ]
        == bindings[
            "historical_response_body_sha256"
        ],
        "historical response SHA mismatch",
    )

    approval = load_json(
        resolve(
            request[
                "execute_now_approval_path"
            ]
        )
    )

    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        "execute approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "execute_now_approval_document_digest_sha256"
        ],
        "execute approval document digest mismatch",
    )
    require(
        approval["approval_label"]
        == (
            "FRESH_DMM_RECHECK_AFTER_PARSER_"
            "REMEDIATION_EXECUTE_NOW_APPROVED"
        ),
        "execute approval label mismatch",
    )
    require(
        approval["human_explicit_approval"]
        is True,
        "explicit human approval missing",
    )

    return authorization, approval, paths


def build_result(
    *,
    attempt_id: str,
    target_url: str,
    redirect_chain: list[
        dict[str, Any]
    ],
    final_status: int | None,
    final_url: str | None,
    response_headers: dict[str, str],
    response_body_sha256: str | None,
    response_body_bytes: int,
    response_hash_complete: bool,
    extraction: dict[str, Any],
    failure_codes: list[str],
    network_error_type: str | None,
    network_error_message: str | None,
    consumption_digest: str,
) -> dict[str, Any]:
    accepted_status = (
        final_status == 200
    )

    matches = extraction.get(
        "identity_matches",
        {},
    )

    identity_match = bool(
        extraction.get(
            "all_required_identity_fields_match",
            False,
        )
    )

    canonical_binding = bool(
        matches.get(
            "canonical_product_binding_to_expected_series",
            False,
        )
    )

    successful_match = (
        accepted_status
        and response_hash_complete
        and identity_match
        and canonical_binding
        and not failure_codes
    )

    decision = (
        "DMM_POST_REMEDIATION_RECHECK_MATCHED_"
        "CANONICAL_PRODUCT_RESOLVED_READY_FOR_"
        "FINAL_LINK_GENERATION_GATE"
        if successful_match
        else
        "DMM_POST_REMEDIATION_RECHECK_FAILED_"
        "CLOSED_SLOT_UNAVAILABLE_RETURN_TO_"
        "HUMAN_REVIEW"
    )

    without_digest = {
        "schema_version": "1.0.0",
        "document_role": (
            "DMM_POST_PARSER_REMEDIATION_"
            "ONE_SHOT_READ_ONLY_RECHECK_RESULT"
        ),
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M4"
        ),
        "attempt_id": attempt_id,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "dmm_series_id": "861056",
        "request": {
            "method": "GET",
            "target_url": target_url,
            "request_body_used": False,
            "authentication_used": False,
            "login_used": False,
            "cookie_sent": False,
            "cookie_persisted": False,
            "credential_file_read": False,
            "proxy_environment_used": False,
            "automatic_retry_performed": False
        },
        "parser_binding": {
            "runner_path": display(
                PARSER_RUNNER_PATH
            ),
            "runner_file_sha256": (
                EXPECTED_RUNNER_SHA256
            ),
            "null_safe_meta_fallback_bound": True
        },
        "network": {
            "network_attempt_performed": True,
            "http_request_attempted": True,
            "http_response_received": (
                final_status is not None
            ),
            "redirect_chain": redirect_chain,
            "redirect_count": len(
                redirect_chain
            ),
            "http_statuses": (
                [
                    item["status"]
                    for item in redirect_chain
                ]
                + (
                    [final_status]
                    if final_status is not None
                    else []
                )
            ),
            "final_http_status": final_status,
            "final_url": final_url,
            "response_headers_allowlisted": (
                response_headers
            ),
            "response_body_sha256": (
                response_body_sha256
            ),
            "response_body_bytes": (
                response_body_bytes
            ),
            "response_body_sha256_complete": (
                response_hash_complete
            ),
            "full_response_body_persisted": False,
            "network_error_type": (
                network_error_type
            ),
            "network_error_message": (
                network_error_message
            )
        },
        "extracted_identity": extraction,
        "verification": {
            "accepted_http_status": (
                accepted_status
            ),
            "all_required_identity_fields_match": (
                identity_match
            ),
            "canonical_product_url_resolved": (
                bool(
                    extraction.get(
                        "canonical_product_url"
                    )
                )
            ),
            "canonical_product_binding_to_expected_series": (
                canonical_binding
            ),
            "successful_match": (
                successful_match
            ),
            "failure_reason_codes": (
                failure_codes
            )
        },
        "decision": decision,
        "dmm_slot_available": (
            successful_match
        ),
        "dmm_slot_must_be_hidden": (
            not successful_match
        ),
        "human_review_required": (
            not successful_match
        ),
        "automatic_fallback_url_used": False,
        "dummy_url_used": False,
        "authorization_consumed": True,
        "authorization_reuse_allowed": False,
        "consumption_evidence_path": (
            display(CONSUMPTION_PATH)
        ),
        "consumption_evidence_digest_sha256": (
            consumption_digest
        ),
        "final_affiliate_link_generated": False,
        "article_modified": False,
        "article_url_injection_performed": False,
        "fresh_payload_created": False,
        "production_category_id_payload_injected": False,
        "wordpress_access_performed": False,
        "wordpress_write_performed": False,
        "wordpress_published": False,
        "production_status": "NO_GO",
        "completed_at_utc": utc_now()
    }

    result = copy.deepcopy(
        without_digest
    )
    result[
        "post_fix_dmm_recheck_result_digest_sha256"
    ] = digest(without_digest)

    return result


def main() -> int:
    terminal = terminal_state()

    if terminal is not None:
        return terminal

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
    )
    args = parser.parse_args()

    if not args.execute:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M4"
                    ),
                    "status": (
                        "BLOCKED_EXPLICIT_EXECUTE_"
                        "FLAG_REQUIRED"
                    ),
                    "authorization_consumed": False,
                    "network_attempt_performed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    try:
        policy = load_json(
            POLICY_PATH
        )
        request = load_json(
            REQUEST_PATH
        )

        (
            authorization,
            approval,
            source_paths,
        ) = validate_preflight(
            policy,
            request,
        )

        source_hashes_before = {
            label: file_sha256(path)
            for label, path
            in source_paths.items()
        }

        parser_module = load_parser_module()

        attempt_id = str(
            uuid.uuid4()
        )
        attempt_started_at = utc_now()

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_POST_PARSER_REMEDIATION_"
                "RECHECK_AUTHORIZATION_CONSUMPTION_"
                "EVIDENCE"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M4"
            ),
            "attempt_id": attempt_id,
            "authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorized_operation": (
                authorization[
                    "authorized_operation"
                ]
            ),
            "authorization_consumed": True,
            "consumption_is_authoritative": True,
            "consumed_at_network_attempt_start_utc": (
                attempt_started_at
            ),
            "single_use": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "retry_after_success_allowed": False,
            "retry_after_http_failure_allowed": False,
            "retry_after_communication_failure_allowed": False,
            "retry_after_identity_mismatch_allowed": False,
            "retry_after_parser_failure_allowed": False,
            "source_authorization_path": (
                request["source_bindings"][
                    "m3_authorization_path"
                ]
            ),
            "source_authorization_file_sha256": (
                request["source_bindings"][
                    "m3_authorization_file_sha256"
                ]
            ),
            "source_authorization_digest_sha256": (
                request["source_bindings"][
                    "m3_authorization_artifact_digest_sha256"
                ]
            ),
            "source_authorization_modified": False,
            "execute_now_approval_path": (
                request[
                    "execute_now_approval_path"
                ]
            ),
            "execute_now_approval_digest_sha256": (
                approval[
                    "approval_evidence_digest_sha256"
                ]
            ),
            "parser_runner_path": (
                display(PARSER_RUNNER_PATH)
            ),
            "parser_runner_file_sha256": (
                EXPECTED_RUNNER_SHA256
            ),
            "request_method": "GET",
            "target_url": request[
                "target_url"
            ],
            "network_attempt_state": (
                "CONSUMED_IMMEDIATELY_BEFORE_"
                "NETWORK_ATTEMPT"
            ),
            "recheck_result_path": (
                display(
                    RECHECK_RESULT_PATH
                )
            ),
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "fresh_payload_created": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO"
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "post_fix_consumption_evidence_digest_sha256"
        ] = digest(
            consumption_without_digest
        )

        write_exclusive_json(
            CONSUMPTION_PATH,
            consumption,
        )

        consumption_digest = consumption[
            "post_fix_consumption_evidence_digest_sha256"
        ]

        target_url = request[
            "target_url"
        ]
        contract = policy[
            "request_contract"
        ]
        request_headers = policy[
            "allowed_request_headers"
        ]

        redirect_handler = (
            parser_module.StrictRedirectHandler(
                maximum_redirect_count=(
                    contract[
                        "maximum_redirect_count"
                    ]
                ),
                request_headers=(
                    request_headers
                ),
            )
        )

        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler(
                {}
            ),
            redirect_handler,
            urllib.request.HTTPSHandler(
                context=(
                    ssl.create_default_context()
                )
            ),
        )

        request_object = urllib.request.Request(
            target_url,
            headers=request_headers,
            method="GET",
        )

        final_status: int | None = None
        final_url: str | None = None
        allowlisted_headers: dict[
            str,
            str
        ] = {}
        response_body_sha256: str | None = None
        response_body_bytes = 0
        response_hash_complete = False
        extraction: dict[str, Any] = {
            "extracted_work_title": None,
            "extracted_volume": None,
            "extracted_author": None,
            "extracted_publisher": None,
            "extracted_series_id": None,
            "canonical_product_url": None,
            "identity_matches": {
                "work_title_match": False,
                "volume_match": False,
                "author_match": False,
                "publisher_match": False,
                "series_identity_match": False,
                "canonical_product_url_resolved": False,
                "canonical_product_binding_to_expected_series": False
            },
            "all_required_identity_fields_match": False
        }
        failure_codes: list[str] = []
        network_error_type: str | None = None
        network_error_message: str | None = None

        try:
            response: Any

            try:
                response = opener.open(
                    request_object,
                    timeout=contract[
                        "request_timeout_seconds"
                    ],
                )
            except urllib.error.HTTPError as exc:
                response = exc

            try:
                final_status = int(
                    response.getcode()
                )
                final_url = (
                    parser_module
                    .validate_https_book_dmm_url(
                        response.geturl(),
                        allow_latest=True,
                    )
                )

                allowed_header_names = {
                    "content-type",
                    "content-encoding",
                    "location",
                    "last-modified",
                    "etag",
                }

                for key, value in response.headers.items():
                    normalized = key.lower()

                    if (
                        normalized
                        in allowed_header_names
                    ):
                        allowlisted_headers[
                            normalized
                        ] = value

                (
                    raw_body,
                    response_body_sha256,
                    response_body_bytes,
                ) = parser_module.read_limited_body(
                    response,
                    contract[
                        "maximum_raw_response_bytes"
                    ],
                )

                response_hash_complete = True

                decoded_body = (
                    parser_module
                    .decode_response_body(
                        raw_body,
                        response.headers.get(
                            "Content-Encoding",
                            "",
                        ),
                    )
                )

                content_type = (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                )

                charset = "utf-8"

                charset_match = re.search(
                    r"charset\s*=\s*[\"']?"
                    r"([A-Za-z0-9._-]+)",
                    content_type,
                    flags=re.IGNORECASE,
                )

                if charset_match:
                    charset = (
                        charset_match.group(1)
                    )

                if final_status != 200:
                    failure_codes.append(
                        "UNEXPECTED_FINAL_HTTP_STATUS"
                    )

                extraction = (
                    parser_module.extract_identity(
                        decoded_body=decoded_body,
                        charset=charset,
                        target_url=target_url,
                        final_url=final_url,
                    )
                )

                matches = extraction[
                    "identity_matches"
                ]

                canonical_url = extraction.get(
                    "canonical_product_url"
                )

                core_identity_match = all(
                    bool(matches.get(field))
                    for field in [
                        "work_title_match",
                        "volume_match",
                        "author_match",
                        "publisher_match",
                        "series_identity_match",
                        "canonical_product_url_resolved",
                    ]
                )

                canonical_binding = (
                    canonical_product_url_binds_to_expected_series(
                        canonical_url,
                        expected_series_id="861056",
                    )
                )

                matches[
                    "canonical_product_binding_to_expected_series"
                ] = canonical_binding

                extraction[
                    "all_required_identity_fields_match"
                ] = (
                    core_identity_match
                    and canonical_binding
                )

                failure_map = {
                    "work_title_match": (
                        "WORK_TITLE_MISMATCH"
                    ),
                    "volume_match": (
                        "VOLUME_MISMATCH"
                    ),
                    "author_match": (
                        "AUTHOR_MISMATCH"
                    ),
                    "publisher_match": (
                        "PUBLISHER_MISMATCH"
                    ),
                    "series_identity_match": (
                        "SERIES_IDENTITY_MISMATCH"
                    ),
                    "canonical_product_url_resolved": (
                        "CANONICAL_PRODUCT_UNRESOLVED"
                    ),
                    "canonical_product_binding_to_expected_series": (
                        "CANONICAL_PRODUCT_SERIES_BINDING_FAILED"
                    ),
                }

                for field, code in (
                    failure_map.items()
                ):
                    if not matches.get(
                        field,
                        False,
                    ):
                        failure_codes.append(
                            code
                        )

            finally:
                try:
                    response.close()
                except Exception:
                    pass

        except parser_module.RedirectPolicyError as exc:
            failure_codes.append(
                "REDIRECT_POLICY_VIOLATION"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        except parser_module.ResponseLimitError as exc:
            failure_codes.append(
                "RESPONSE_BODY_TOO_LARGE"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        except parser_module.ValidationError as exc:
            failure_codes.append(
                "CONTENT_OR_PARSER_VALIDATION_FAILURE"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        except (
            urllib.error.URLError,
            TimeoutError,
            ssl.SSLError,
            OSError,
        ) as exc:
            failure_codes.append(
                "COMMUNICATION_FAILURE"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        except Exception as exc:
            failure_codes.append(
                "UNEXPECTED_RECHECK_EXCEPTION"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        failure_codes = list(
            dict.fromkeys(
                failure_codes
            )
        )

        recheck_result = build_result(
            attempt_id=attempt_id,
            target_url=target_url,
            redirect_chain=(
                redirect_handler.redirect_chain
            ),
            final_status=final_status,
            final_url=final_url,
            response_headers=(
                allowlisted_headers
            ),
            response_body_sha256=(
                response_body_sha256
            ),
            response_body_bytes=(
                response_body_bytes
            ),
            response_hash_complete=(
                response_hash_complete
            ),
            extraction=extraction,
            failure_codes=failure_codes,
            network_error_type=(
                network_error_type
            ),
            network_error_message=(
                network_error_message
            ),
            consumption_digest=(
                consumption_digest
            ),
        )

        write_exclusive_json(
            RECHECK_RESULT_PATH,
            recheck_result,
        )

        for label, path in source_paths.items():
            require(
                file_sha256(path)
                == source_hashes_before[
                    label
                ],
                f"source artifact modified: {label}",
            )

        success = recheck_result[
            "verification"
        ]["successful_match"]

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M4"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "attempt_id": attempt_id,
            "authorization_consumption_path": (
                display(CONSUMPTION_PATH)
            ),
            "authorization_consumption_file_sha256": (
                file_sha256(
                    CONSUMPTION_PATH
                )
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "recheck_result_path": (
                display(
                    RECHECK_RESULT_PATH
                )
            ),
            "recheck_result_file_sha256": (
                file_sha256(
                    RECHECK_RESULT_PATH
                )
            ),
            "recheck_result_digest_sha256": (
                recheck_result[
                    "post_fix_dmm_recheck_result_digest_sha256"
                ]
            ),
            "successful_match": success,
            "dmm_slot_available": (
                recheck_result[
                    "dmm_slot_available"
                ]
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "network_attempt_performed": True,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "fresh_payload_created": False,
            "wordpress_access_performed": False
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "post_fix_dmm_recheck_package_digest_sha256"
        ] = digest(
            package_without_digest
        )

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M4"
            ),
            "status": (
                "PASS_DMM_POST_REMEDIATION_ONE_SHOT_"
                "RECHECK_EXECUTED_AUTH_CONSUMED_"
                "NO_LINK_GENERATION"
            ),
            "decision": (
                recheck_result[
                    "decision"
                ]
            ),
            "approval_label": (
                "FRESH_DMM_RECHECK_AFTER_PARSER_"
                "REMEDIATION_EXECUTE_NOW_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "attempt_id": attempt_id,
            "authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "target_url": target_url,
            "method": "GET",
            "parser_runner_file_sha256": (
                EXPECTED_RUNNER_SHA256
            ),
            "authorization_consumption_path": (
                package[
                    "authorization_consumption_path"
                ]
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "recheck_result_path": (
                package[
                    "recheck_result_path"
                ]
            ),
            "recheck_result_digest_sha256": (
                package[
                    "recheck_result_digest_sha256"
                ]
            ),
            "post_fix_dmm_recheck_package_digest_sha256": (
                package[
                    "post_fix_dmm_recheck_package_digest_sha256"
                ]
            ),
            "authorization_consumed": True,
            "consumption_evidence_created": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "network_attempt_performed": True,
            "http_request_attempted": True,
            "http_response_received": (
                recheck_result[
                    "network"
                ]["http_response_received"]
            ),
            "redirect_count": (
                recheck_result[
                    "network"
                ]["redirect_count"]
            ),
            "final_http_status": (
                recheck_result[
                    "network"
                ]["final_http_status"]
            ),
            "final_url": (
                recheck_result[
                    "network"
                ]["final_url"]
            ),
            "response_body_sha256": (
                recheck_result[
                    "network"
                ]["response_body_sha256"]
            ),
            "full_response_body_persisted": False,
            "all_required_identity_fields_match": (
                recheck_result[
                    "verification"
                ][
                    "all_required_identity_fields_match"
                ]
            ),
            "canonical_product_url": (
                recheck_result[
                    "extracted_identity"
                ].get(
                    "canonical_product_url"
                )
            ),
            "canonical_product_binding_to_expected_series": (
                recheck_result[
                    "verification"
                ][
                    "canonical_product_binding_to_expected_series"
                ]
            ),
            "successful_match": success,
            "failure_reason_codes": (
                recheck_result[
                    "verification"
                ]["failure_reason_codes"]
            ),
            "dmm_slot_available": (
                recheck_result[
                    "dmm_slot_available"
                ]
            ),
            "dmm_slot_must_be_hidden": (
                recheck_result[
                    "dmm_slot_must_be_hidden"
                ]
            ),
            "human_review_required": (
                recheck_result[
                    "human_review_required"
                ]
            ),
            "automatic_fallback_url_used": False,
            "historical_m2_evidence_preserved": True,
            "historical_response_body_sha256_preserved": True,
            "final_affiliate_link_generated": False,
            "final_affiliate_link_validated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "source_artifacts_modified": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_POST_REMEDIATION_RECHECK_"
                "MATCHED_AWAITING_FINAL_LINK_"
                "GENERATION_GATE"
                if success
                else
                "DMM_POST_REMEDIATION_RECHECK_"
                "FAILED_CLOSED_AWAITING_HUMAN_REVIEW"
            ),
            "ready_for_final_affiliate_link_generation_gate": (
                success
            ),
            "ready_for_dmm_failure_human_review": (
                not success
            ),
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False
        }

        write_json(
            PACKAGE_PATH,
            package,
        )
        write_json(
            RESULT_PATH,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M4

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Authorization consumed: `true`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`

## Parser

- Runner SHA-256: `{result["parser_runner_file_sha256"]}`
- Null-safe remediation bound: `true`

## Network Evidence

- HTTP response received: `{str(result["http_response_received"]).lower()}`
- Redirect count: `{result["redirect_count"]}`
- Final HTTP status: `{result["final_http_status"]}`
- Final URL: `{result["final_url"]}`
- Response body SHA-256: `{result["response_body_sha256"]}`
- Full response body persisted: `false`

## Verification

- All required identity fields match: `{str(result["all_required_identity_fields_match"]).lower()}`
- Canonical product URL: `{result["canonical_product_url"]}`
- Canonical series binding: `{str(result["canonical_product_binding_to_expected_series"]).lower()}`
- Successful match: `{str(result["successful_match"]).lower()}`
- DMM slot available: `{str(result["dmm_slot_available"]).lower()}`
- Human review required: `{str(result["human_review_required"]).lower()}`
- Failure reason codes: `{result["failure_reason_codes"]}`

## Boundary

- Final affiliate link generated: `false`
- Article modified: `false`
- URL injected: `false`
- Payload created: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
"""

        write_text(
            REPORT_PATH,
            report,
        )

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
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M4"
                    ),
                    "status": (
                        "FAIL_PREFLIGHT_VALIDATION_"
                        "NO_NETWORK_ATTEMPT"
                    ),
                    "error": str(exc),
                    "authorization_consumed": False,
                    "network_attempt_performed": False,
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
