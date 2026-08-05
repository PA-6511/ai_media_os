from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    FINAL_APPROVAL_LABEL,
    FINAL_APPROVAL_STATE,
    FINAL_GATE_STATE,
    canonical_json_digest,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
    json_storage_snapshot,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    TOKEN_STATE,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    sha256_file,
)
from scripts.run_x_r8_isolated_x_fb_write import (
    load_json_object,
)


ROOT = REPOSITORY_ROOT

EXPECTED_DESIGN_STATUS = (
    "FINAL_GATE_DESIGN_READY_NO_EXECUTION"
)
EXPECTED_RESULT_STATUS = (
    "PASS_FINAL_GATE_DESIGN_READY_NO_EXECUTION"
)
EXPECTED_TOKEN_STATUS = (
    "APPROVAL_TOKEN_ISSUED_NO_EXECUTION"
)

CERTIFICATE_STATE = (
    "ISSUED_NOT_CONSUMED"
)
AUTHORIZED_NEXT_PHASE = (
    "X-R11-NORMAL-X-FB-ONE-SHOT-"
    "WRITE-RUNNER-PREP"
)


class XR11FinalApprovalError(RuntimeError):
    """Raised when final approval certificate issuance fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR11FinalApprovalError(message)


def normalize_nonempty_text(
    value: str,
    field_name: str,
) -> str:
    require(
        isinstance(value, str),
        f"{field_name} must be a string",
    )

    normalized = unicodedata.normalize(
        "NFKC",
        value,
    ).strip()

    require(
        bool(normalized),
        f"{field_name} must not be empty",
    )

    return normalized


def normalize_approved_at(value: str) -> str:
    normalized = normalize_nonempty_text(
        value,
        "approved_at",
    )

    parse_value = normalized

    if parse_value.endswith("Z"):
        parse_value = (
            parse_value[:-1] + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            parse_value
        )
    except ValueError as exc:
        raise XR11FinalApprovalError(
            "approved_at must be ISO-8601"
        ) from exc

    require(
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None,
        "approved_at must include timezone",
    )

    return parsed.isoformat()


def is_within(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.resolve().relative_to(
            parent.resolve()
        )
    except ValueError:
        return False

    return True


def assert_diagnostic_path(
    path: Path,
    normal_x_fb_root: Path,
    field_name: str,
) -> None:
    forbidden_roots = (
        normal_x_fb_root
        / "exchange/input/x_post_feedback",
        normal_x_fb_root
        / "exchange/archive/x_post_feedback",
        normal_x_fb_root
        / "exchange/logs",
    )

    for forbidden_root in forbidden_roots:
        require(
            not is_within(
                path,
                forbidden_root,
            ),
            (
                f"{field_name} must not be inside "
                "normal X-FB storage"
            ),
        )


def create_exclusive_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise XR11FinalApprovalError(
            "final approval certificate "
            f"already exists: {path}"
        ) from exc

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())

        directory_descriptor = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    except Exception:
        path.unlink(missing_ok=True)
        raise


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_final_gate_result(
    result: dict[str, Any],
    *,
    design_path: Path,
) -> str:
    require(
        result.get("status")
        == EXPECTED_RESULT_STATUS,
        "final-gate result status is invalid",
    )
    require(
        result.get("gate_state")
        == FINAL_GATE_STATE,
        "final-gate result state is invalid",
    )
    require(
        Path(
            str(
                result.get(
                    "final_gate_design_path",
                    "",
                )
            )
        ).resolve()
        == design_path,
        (
            "final-gate result design path "
            "does not match supplied design"
        ),
    )
    require(
        result.get("candidate_revalidated")
        is True,
        "candidate was not revalidated",
    )
    require(
        result.get("approval_pack_verified")
        is True,
        "approval pack was not verified",
    )
    require(
        result.get("preflight_lock_verified")
        is True,
        "preflight lock was not verified",
    )
    require(
        result.get("approval_token_verified")
        is True,
        "approval token was not verified",
    )
    require(
        result.get(
            "initialize_request_verified"
        )
        is True,
        "initialize request was not verified",
    )
    require(
        result.get("target_paths_fixed")
        is True,
        "target paths are not fixed",
    )
    require(
        result.get(
            "final_approval_label_consumed"
        )
        is False,
        (
            "final approval label must be "
            "unconsumed"
        ),
    )
    require(
        result.get("execution_token_consumed")
        is False,
        (
            "execution token must remain "
            "unconsumed"
        ),
    )
    require(
        result.get("preflight_lock_consumed")
        is False,
        (
            "preflight lock must remain "
            "unconsumed"
        ),
    )
    require(
        result.get("execution_allowed")
        is False,
        (
            "final-gate result execution_allowed "
            "must be false"
        ),
    )
    require(
        result.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "final-gate result normal X-FB "
            "write must be false"
        ),
    )
    require(
        result.get("current_record_written")
        is False,
        (
            "final-gate result reports an "
            "existing current write"
        ),
    )
    require(
        result.get(
            "operation_result_written"
        )
        is False,
        (
            "final-gate result reports an "
            "existing operation result write"
        ),
    )
    require(
        result.get(
            "normal_x_fb_storage_modified"
        )
        is False,
        (
            "final-gate result reports modified "
            "normal X-FB storage"
        ),
    )
    require(
        result.get("production_status")
        == "NO_GO",
        (
            "final-gate production_status "
            "must be NO_GO"
        ),
    )

    design_digest = result.get(
        "final_gate_design_digest_sha256"
    )

    require(
        isinstance(design_digest, str)
        and len(design_digest) == 64,
        "final-gate design digest is invalid",
    )

    return design_digest


def validate_final_gate_design(
    design: dict[str, Any],
    *,
    expected_digest: str,
) -> None:
    require(
        design.get("status")
        == EXPECTED_DESIGN_STATUS,
        "final-gate design status is invalid",
    )
    require(
        design.get("gate_state")
        == FINAL_GATE_STATE,
        "final-gate design state is invalid",
    )
    require(
        design.get(
            "required_final_approval_label"
        )
        == FINAL_APPROVAL_LABEL,
        (
            "final-gate required approval "
            "label is invalid"
        ),
    )
    require(
        design.get("final_approval_state")
        == FINAL_APPROVAL_STATE,
        (
            "final-gate approval state "
            "is invalid"
        ),
    )
    require(
        design.get(
            "final_approval_label_consumed"
        )
        is False,
        (
            "final approval label must remain "
            "unconsumed"
        ),
    )
    require(
        design.get("execution_token_consumed")
        is False,
        (
            "execution token must remain "
            "unconsumed"
        ),
    )
    require(
        design.get("preflight_lock_consumed")
        is False,
        (
            "preflight lock must remain "
            "unconsumed"
        ),
    )
    require(
        design.get("execution_allowed")
        is False,
        (
            "final-gate execution_allowed "
            "must be false"
        ),
    )
    require(
        design.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "final-gate normal X-FB write "
            "must be false"
        ),
    )
    require(
        design.get("candidate_revalidated")
        is True,
        "candidate revalidation is missing",
    )
    require(
        design.get(
            "regenerated_draft_matches_approval"
        )
        is True,
        (
            "regenerated draft does not match "
            "approval"
        ),
    )

    target_paths = design.get(
        "target_paths"
    )

    require(
        isinstance(target_paths, dict),
        "target_paths must be an object",
    )
    require(
        target_paths.get("paths_fixed")
        is True,
        "target paths must be fixed",
    )
    require(
        target_paths.get(
            "path_substitution_allowed"
        )
        is False,
        (
            "target path substitution "
            "must be forbidden"
        ),
    )

    execution_contract = design.get(
        "execution_contract"
    )

    require(
        isinstance(
            execution_contract,
            dict,
        ),
        (
            "execution_contract must be "
            "an object"
        ),
    )
    require(
        execution_contract.get(
            "maximum_record_count"
        )
        == 1,
        "maximum record count must be 1",
    )
    require(
        execution_contract.get("operation")
        == "INITIALIZE",
        "operation must be INITIALIZE",
    )
    require(
        execution_contract.get(
            "second_execution_forbidden"
        )
        is True,
        (
            "second execution must be "
            "forbidden"
        ),
    )
    require(
        execution_contract.get(
            "x_api_call_allowed"
        )
        is False,
        "X API calls must be forbidden",
    )
    require(
        execution_contract.get(
            "x_post_allowed"
        )
        is False,
        "X posting must be forbidden",
    )

    failure_policy = design.get(
        "failure_policy"
    )

    require(
        isinstance(failure_policy, dict),
        "failure_policy must be an object",
    )
    require(
        failure_policy.get("fail_closed")
        is True,
        "failure policy must fail closed",
    )
    require(
        failure_policy.get(
            "automatic_retry_allowed"
        )
        is False,
        (
            "automatic retry must be "
            "forbidden"
        ),
    )
    require(
        failure_policy.get(
            "rollback_after_normal_current_write"
        )
        == "NO_AUTOMATIC_DELETE",
        (
            "post-write automatic deletion "
            "must be forbidden"
        ),
    )

    safety = design.get("safety")

    require(
        isinstance(safety, dict),
        "safety must be an object",
    )

    for field_name in (
        "database_write",
        "workflow_write",
        "wordpress_write",
        "x_api_call",
        "x_post",
        "external_api_call",
        "normal_x_fb_storage_modified",
    ):
        require(
            safety.get(field_name) is False,
            (
                "final-gate safety flag must "
                f"be false: {field_name}"
            ),
        )

    require(
        safety.get("production_status")
        == "NO_GO",
        "production_status must be NO_GO",
    )
    require(
        safety.get("safety_state")
        == "DESIGN_ONLY_NO_EXECUTION",
        "final-gate safety_state is invalid",
    )

    stored_digest = design.get(
        "final_gate_design_digest_sha256"
    )

    require(
        stored_digest == expected_digest,
        (
            "final-gate result and design "
            "digest mismatch"
        ),
    )

    payload = {
        key: value
        for key, value in design.items()
        if key
        != "final_gate_design_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == stored_digest,
        (
            "final-gate design tampering "
            "detected: digest mismatch"
        ),
    )


def validate_approval_bundle(
    design: dict[str, Any],
) -> dict[str, Any]:
    approval_pack_path = Path(
        str(design["approval_pack_path"])
    ).resolve()
    preflight_lock_path = Path(
        str(design["preflight_lock_path"])
    ).resolve()
    approval_token_path = Path(
        str(design["approval_token_path"])
    ).resolve()
    initialize_request_path = Path(
        str(design["initialize_request_path"])
    ).resolve()

    approval_pack = load_json_object(
        approval_pack_path
    )
    preflight_lock = load_json_object(
        preflight_lock_path
    )
    approval_token = load_json_object(
        approval_token_path
    )
    initialize_request = load_json_object(
        initialize_request_path
    )

    pack_digest = approval_pack.get(
        "approval_pack_digest_sha256"
    )

    require(
        pack_digest
        == design.get(
            "approval_pack_digest_sha256"
        ),
        (
            "approval pack digest does not "
            "match final-gate design"
        ),
    )

    pack_payload = {
        key: value
        for key, value in approval_pack.items()
        if key
        != "approval_pack_digest_sha256"
    }

    require(
        canonical_digest(pack_payload)
        == pack_digest,
        "approval pack tampering detected",
    )

    token_digest = approval_token.get(
        "execution_token_digest_sha256"
    )

    require(
        token_digest
        == design.get(
            "approval_token_digest_sha256"
        ),
        (
            "approval token digest does not "
            "match final-gate design"
        ),
    )

    token_payload = {
        key: value
        for key, value in approval_token.items()
        if key
        != "execution_token_digest_sha256"
    }

    require(
        canonical_digest(token_payload)
        == token_digest,
        "approval token tampering detected",
    )
    require(
        approval_token.get("status")
        == EXPECTED_TOKEN_STATUS,
        "approval token status is invalid",
    )
    require(
        approval_token.get("token_state")
        == TOKEN_STATE,
        (
            "approval token state must be "
            "ISSUED_NOT_CONSUMED"
        ),
    )
    require(
        approval_token.get(
            "execution_token_consumed"
        )
        is False,
        (
            "approval token must remain "
            "unconsumed"
        ),
    )
    require(
        approval_token.get(
            "preflight_lock_consumed"
        )
        is False,
        (
            "preflight lock must remain "
            "unconsumed"
        ),
    )
    require(
        approval_token.get(
            "execution_allowed"
        )
        is False,
        (
            "approval token execution_allowed "
            "must be false"
        ),
    )
    require(
        approval_token.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "approval token normal X-FB "
            "write must be false"
        ),
    )

    require(
        approval_token.get(
            "approval_pack_file_sha256"
        )
        == sha256_file(
            approval_pack_path
        ),
        (
            "approval pack file hash does not "
            "match approval token"
        ),
    )
    require(
        approval_token.get(
            "one_shot_lock_file_sha256"
        )
        == sha256_file(
            preflight_lock_path
        ),
        (
            "preflight lock file hash does not "
            "match approval token"
        ),
    )

    require(
        preflight_lock.get("consumed", False)
        is False,
        (
            "preflight lock must remain "
            "unconsumed"
        ),
    )
    require(
        preflight_lock.get(
            "execution_allowed"
        )
        is False,
        (
            "preflight lock execution_allowed "
            "must be false"
        ),
    )
    require(
        preflight_lock.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "preflight lock normal X-FB "
            "write must be false"
        ),
    )

    request_digest = canonical_json_digest(
        initialize_request
    )

    require(
        request_digest
        == design.get(
            "initialize_request_digest_sha256"
        ),
        (
            "initialize request digest does not "
            "match final-gate design"
        ),
    )
    require(
        request_digest
        == design.get(
            "regenerated_request_digest_sha256"
        ),
        (
            "initialize request does not match "
            "regenerated request"
        ),
    )

    return {
        "approval_pack_path": approval_pack_path,
        "preflight_lock_path": preflight_lock_path,
        "approval_token_path": approval_token_path,
        "initialize_request_path": (
            initialize_request_path
        ),
        "approval_pack_digest": pack_digest,
        "approval_token_digest": token_digest,
        "initialize_request_digest": (
            request_digest
        ),
        "execution_token_id": (
            approval_token["token_id"]
        ),
    }


def run_x_r11_final_approval_protocol(
    *,
    final_gate_result_path: Path,
    final_gate_design_path: Path,
    final_approval_label: str,
    approved_by: str,
    approved_at: str,
    output_root: Path,
    certificate_root: Path,
    normal_x_fb_root: Path = ROOT,
) -> dict[str, Any]:
    final_gate_result_path = (
        final_gate_result_path.resolve()
    )
    final_gate_design_path = (
        final_gate_design_path.resolve()
    )
    output_root = output_root.resolve()
    certificate_root = (
        certificate_root.resolve()
    )
    normal_x_fb_root = (
        normal_x_fb_root.resolve()
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    assert_diagnostic_path(
        output_root,
        normal_x_fb_root,
        "output_root",
    )
    assert_diagnostic_path(
        certificate_root,
        normal_x_fb_root,
        "certificate_root",
    )

    normalized_label = (
        normalize_nonempty_text(
            final_approval_label,
            "final_approval_label",
        )
    )
    normalized_approver = (
        normalize_nonempty_text(
            approved_by,
            "approved_by",
        )
    )
    normalized_approved_at = (
        normalize_approved_at(
            approved_at
        )
    )

    require(
        normalized_label
        == FINAL_APPROVAL_LABEL,
        (
            "final approval label must exactly "
            f"match {FINAL_APPROVAL_LABEL}"
        ),
    )

    source_paths = {
        "final_gate_result": (
            final_gate_result_path
        ),
        "final_gate_design": (
            final_gate_design_path
        ),
    }

    for path in source_paths.values():
        require(
            path.is_file(),
            f"required artifact is missing: {path}",
        )

    source_hashes_before = {
        name: sha256_file(path)
        for name, path in source_paths.items()
    }

    normal_snapshot_before = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    result = load_json_object(
        final_gate_result_path
    )
    design = load_json_object(
        final_gate_design_path
    )

    design_digest = (
        validate_final_gate_result(
            result,
            design_path=(
                final_gate_design_path
            ),
        )
    )

    validate_final_gate_design(
        design,
        expected_digest=design_digest,
    )

    bundle = validate_approval_bundle(
        design
    )

    for name, path in (
        (
            "approval_pack",
            bundle["approval_pack_path"],
        ),
        (
            "preflight_lock",
            bundle["preflight_lock_path"],
        ),
        (
            "approval_token",
            bundle["approval_token_path"],
        ),
        (
            "initialize_request",
            bundle["initialize_request_path"],
        ),
    ):
        source_paths[name] = path
        source_hashes_before[name] = (
            sha256_file(path)
        )

    source_database_path = Path(
        str(design["source_database_path"])
    ).resolve()

    require(
        source_database_path.is_file(),
        (
            "final-gate source database "
            "is missing"
        ),
    )

    source_paths["source_database"] = (
        source_database_path
    )
    source_hashes_before[
        "source_database"
    ] = sha256_file(
        source_database_path
    )

    expected_database_sha = result.get(
        "source_database_sha256_after"
    )

    require(
        source_hashes_before[
            "source_database"
        ]
        == expected_database_sha,
        (
            "source database changed after "
            "final-gate design"
        ),
    )

    target_paths = design[
        "target_paths"
    ]

    current_record_path = Path(
        str(
            target_paths[
                "current_record_path"
            ]
        )
    ).resolve()
    operation_result_path = Path(
        str(
            target_paths[
                "operation_result_path"
            ]
        )
    ).resolve()

    require(
        is_within(
            current_record_path,
            (
                normal_x_fb_root
                / "exchange/input/x_post_feedback"
            ),
        ),
        (
            "fixed current record path is "
            "outside normal X-FB input root"
        ),
    )
    require(
        is_within(
            operation_result_path,
            (
                normal_x_fb_root
                / "exchange/logs"
            ),
        ),
        (
            "fixed operation result path is "
            "outside normal X-FB log root"
        ),
    )
    require(
        not current_record_path.exists(),
        (
            "normal X-FB current.json "
            "already exists"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "normal X-FB operation result "
            "already exists"
        ),
    )

    feedback_id = str(
        design["feedback_id"]
    )
    approval_request_id = str(
        design["approval_request_id"]
    )
    database_scope = str(
        design["database_scope"]
    )

    certificate_scope = (
        "PRODUCTION_APPROVAL_NO_EXECUTION"
        if database_scope
        == "PRODUCTION_READ_ONLY"
        else "ISOLATED_PROTOCOL_VALIDATION_ONLY"
    )

    certificate_id_source = "|".join(
        (
            feedback_id,
            design_digest,
            normalized_approver,
            normalized_approved_at,
        )
    )

    certificate_id = (
        "xr11-final-"
        + hashlib.sha256(
            certificate_id_source.encode(
                "utf-8"
            )
        ).hexdigest()[:24]
    )

    certificate_path = (
        certificate_root
        / f"{feedback_id}.certificate.json"
    )

    issued_at = datetime.now(
        timezone.utc
    ).isoformat()

    certificate_payload = {
        "phase": (
            "X-R11-FINAL-APPROVAL-PROTOCOL"
        ),
        "status": (
            "FINAL_APPROVAL_CERTIFICATE_"
            "ISSUED_NO_EXECUTION"
        ),
        "certificate_id": certificate_id,
        "certificate_state": (
            CERTIFICATE_STATE
        ),
        "certificate_scope": (
            certificate_scope
        ),
        "database_scope": database_scope,
        "feedback_id": feedback_id,
        "approval_request_id": (
            approval_request_id
        ),
        "execution_token_id": (
            bundle["execution_token_id"]
        ),
        "final_gate_result_path": str(
            final_gate_result_path
        ),
        "final_gate_design_path": str(
            final_gate_design_path
        ),
        "final_gate_design_digest_sha256": (
            design_digest
        ),
        "approval_pack_digest_sha256": (
            bundle["approval_pack_digest"]
        ),
        "approval_token_digest_sha256": (
            bundle["approval_token_digest"]
        ),
        "initialize_request_digest_sha256": (
            bundle[
                "initialize_request_digest"
            ]
        ),
        "source_database_sha256": (
            expected_database_sha
        ),
        "final_approval_label": (
            normalized_label
        ),
        "approved_by": (
            normalized_approver
        ),
        "approved_at": (
            normalized_approved_at
        ),
        "issued_at": issued_at,
        "final_approval_label_consumed": True,
        "certificate_consumed": False,
        "execution_token_consumed": False,
        "preflight_lock_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            AUTHORIZED_NEXT_PHASE
        ),
        "final_execution_still_requires_explicit_command": (
            True
        ),
        "consumption_contract": {
            "certificate_must_be_consumed_once": (
                True
            ),
            "execution_token_must_be_consumed_once": (
                True
            ),
            "preflight_lock_must_be_consumed_once": (
                True
            ),
            "all_consumption_must_share_transaction_id": (
                True
            ),
            "second_execution_forbidden": True,
            "automatic_retry_allowed": False,
            "normal_x_fb_write_in_this_phase": (
                False
            ),
            "x_api_call_allowed": False,
            "x_post_allowed": False,
        },
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "FINAL_APPROVAL_CERTIFICATE_"
            "ONLY_NO_EXECUTION"
        ),
    }

    certificate_digest = canonical_digest(
        certificate_payload
    )

    certificate = {
        **certificate_payload,
        "final_approval_certificate_digest_sha256": (
            certificate_digest
        ),
    }

    certificate_created = False

    try:
        create_exclusive_json(
            certificate_path,
            certificate,
        )
        certificate_created = True

        source_hashes_after = {
            name: sha256_file(path)
            for name, path in source_paths.items()
        }

        require(
            source_hashes_before
            == source_hashes_after,
            (
                "source approval artifacts "
                "changed during certificate "
                "issuance"
            ),
        )

        normal_snapshot_after = (
            json_storage_snapshot(
                normal_x_fb_root
            )
        )

        require(
            normal_snapshot_before
            == normal_snapshot_after,
            (
                "normal X-FB storage changed "
                "during final approval"
            ),
        )

        protocol_result = {
            "phase": (
                "X-R11-FINAL-APPROVAL-PROTOCOL"
            ),
            "status": (
                "PASS_FINAL_APPROVAL_"
                "CERTIFICATE_ISSUED_NO_EXECUTION"
            ),
            "certificate_id": (
                certificate_id
            ),
            "certificate_state": (
                CERTIFICATE_STATE
            ),
            "certificate_scope": (
                certificate_scope
            ),
            "database_scope": (
                database_scope
            ),
            "feedback_id": feedback_id,
            "approval_request_id": (
                approval_request_id
            ),
            "final_approval_certificate_path": str(
                certificate_path
            ),
            "final_approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "final_gate_design_digest_sha256": (
                design_digest
            ),
            "final_approval_label": (
                normalized_label
            ),
            "approved_by": (
                normalized_approver
            ),
            "approved_at": (
                normalized_approved_at
            ),
            "final_approval_label_consumed": True,
            "certificate_consumed": False,
            "execution_token_consumed": False,
            "preflight_lock_consumed": False,
            "execution_allowed": False,
            "normal_x_fb_write_allowed": False,
            "source_artifacts_unchanged": True,
            "source_database_unchanged": True,
            "current_record_written": False,
            "operation_result_written": False,
            "normal_x_fb_storage_modified": False,
            "database_read": True,
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
            "external_api_call": False,
            "production_execution": False,
            "authorized_next_phase": (
                AUTHORIZED_NEXT_PHASE
            ),
            "production_status": "NO_GO",
            "safety_state": (
                "FINAL_APPROVAL_CERTIFICATE_"
                "ONLY_NO_EXECUTION"
            ),
        }

        output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        atomic_write_json(
            output_root
            / "x_r11_final_approval_result.json",
            protocol_result,
        )

        return protocol_result

    except Exception:
        if certificate_created:
            certificate_path.unlink(
                missing_ok=True
            )
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--final-gate-result",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--final-gate-design",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--final-approval-label",
        required=True,
    )
    parser.add_argument(
        "--approved-by",
        required=True,
    )
    parser.add_argument(
        "--approved-at",
        required=True,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--certificate-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--normal-x-fb-root",
        type=Path,
        default=ROOT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = (
            run_x_r11_final_approval_protocol(
                final_gate_result_path=(
                    args.final_gate_result
                ),
                final_gate_design_path=(
                    args.final_gate_design
                ),
                final_approval_label=(
                    args.final_approval_label
                ),
                approved_by=(
                    args.approved_by
                ),
                approved_at=(
                    args.approved_at
                ),
                output_root=(
                    args.output_root
                ),
                certificate_root=(
                    args.certificate_root
                ),
                normal_x_fb_root=(
                    args.normal_x_fb_root
                ),
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": (
                        "X-R11-FINAL-"
                        "APPROVAL-PROTOCOL"
                    ),
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "final_approval_label_consumed": (
                        False
                    ),
                    "certificate_consumed": False,
                    "execution_token_consumed": False,
                    "preflight_lock_consumed": False,
                    "execution_allowed": False,
                    "normal_x_fb_write_allowed": False,
                    "database_write": False,
                    "workflow_write": False,
                    "wordpress_write": False,
                    "x_api_call": False,
                    "x_post": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
