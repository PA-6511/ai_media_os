from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from app.services.x_draft_generation_service import (
    XDraftGenerationService,
    XDraftInput,
)


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MANAGER_PATH = (
    ROOT / "scripts/manage_x_feedback_record.py"
)

SCHEMA_RELATIVE_PATH = Path(
    "config/x_post_wording_feedback_schema.json"
)
POLICY_RELATIVE_PATH = Path(
    "config/x_fb_manual_operation_policy.json"
)
VALIDATOR_RELATIVE_PATH = Path(
    "scripts/build_x_fb_0.py"
)


class XDraftFeedbackRegistrationError(RuntimeError):
    """Raised when X-FB dry-run registration fails."""


@dataclass(frozen=True)
class XDraftFeedbackDryRunResult:
    status: str
    dry_run: bool
    storage_root: str
    feedback_id: str
    current_record_path: str
    operation_result_path: str
    current_record_existed_before: bool
    current_record_written: bool
    operation_result_written: bool
    generated_text: str
    character_count: int
    contains_pr: bool
    initialize_request: dict[str, Any]
    normalized_record: dict[str, Any]
    record_execution_boundary: dict[str, Any]
    manager_execution_boundary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XDraftFeedbackRegistrationError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"required JSON file missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise XDraftFeedbackRegistrationError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def load_python_module(
    path: Path,
    *,
    prefix: str,
) -> ModuleType:
    require(
        path.is_file(),
        f"required Python module missing: {path}",
    )

    digest = hashlib.sha256(
        str(path.resolve()).encode("utf-8")
    ).hexdigest()[:16]

    module_name = f"{prefix}_{digest}"

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    require(
        spec is not None,
        f"failed to build module spec: {path}",
    )
    require(
        spec.loader is not None,
        f"module loader is missing: {path}",
    )

    module = importlib.util.module_from_spec(spec)

    previous_dont_write_bytecode = (
        sys.dont_write_bytecode
    )
    sys.dont_write_bytecode = True

    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = (
            previous_dont_write_bytecode
        )

    return module


def validate_manager_boundary(
    boundary: dict[str, Any],
) -> None:
    require(
        boundary.get("x_api_call_allowed") is False,
        "x_api_call_allowed must be false",
    )
    require(
        boundary.get("x_post_allowed") is False,
        "x_post_allowed must be false",
    )
    require(
        boundary.get("wordpress_write_allowed") is False,
        "wordpress_write_allowed must be false",
    )
    require(
        boundary.get("external_api_call_allowed") is False,
        "external_api_call_allowed must be false",
    )
    require(
        boundary.get("automatic_rule_update_allowed")
        is False,
        "automatic_rule_update_allowed must be false",
    )
    require(
        boundary.get("production_status") == "NO_GO",
        "production_status must be NO_GO",
    )


class XDraftFeedbackRegistrationService:
    """
    Integrates X draft generation with X-FB normalization.

    This service intentionally exposes dry-run registration only.
    It never writes current.json, archives, operation results,
    databases, WordPress records, or X posts.
    """

    def __init__(
        self,
        *,
        generation_service: (
            XDraftGenerationService | None
        ) = None,
        manager_path: Path = DEFAULT_MANAGER_PATH,
    ) -> None:
        self.generation_service = (
            generation_service
            or XDraftGenerationService()
        )
        self.manager_path = manager_path.resolve()

    def dry_run_register(
        self,
        draft_input: XDraftInput,
        *,
        storage_root: Path = ROOT,
    ) -> XDraftFeedbackDryRunResult:
        resolved_root = storage_root.resolve()

        schema_path = (
            resolved_root / SCHEMA_RELATIVE_PATH
        )
        policy_path = (
            resolved_root / POLICY_RELATIVE_PATH
        )
        validator_path = (
            resolved_root / VALIDATOR_RELATIVE_PATH
        )

        schema = load_json_object(schema_path)
        policy = load_json_object(policy_path)

        require(
            schema.get("schema_id")
            == "X_POST_WORDING_FEEDBACK_SCHEMA_V1",
            "unsupported X-FB schema",
        )
        require(
            policy.get("phase_id") == "X-FB-1",
            "unsupported X-FB operation policy",
        )
        require(
            policy.get("feedback_schema_id")
            == schema.get("schema_id"),
            "X-FB policy/schema mismatch",
        )

        manager_boundary = policy.get(
            "execution_boundary"
        )

        require(
            isinstance(manager_boundary, dict),
            "manager execution_boundary must be an object",
        )
        validate_manager_boundary(manager_boundary)

        draft_result = (
            self.generation_service.generate(
                draft_input
            )
        )

        feedback_id = draft_result.feedback_id

        current_record_path = (
            resolved_root
            / "exchange/input/x_post_feedback"
            / feedback_id
            / "current.json"
        )
        operation_result_path = (
            resolved_root
            / "exchange/logs"
            / (
                f"x_fb_1_{feedback_id}"
                "_v001_result.json"
            )
        )

        current_existed_before = (
            current_record_path.exists()
        )

        current_record = (
            load_json_object(current_record_path)
            if current_existed_before
            else None
        )

        manager = load_python_module(
            self.manager_path,
            prefix="x_feedback_manager",
        )
        validator = load_python_module(
            validator_path,
            prefix="x_feedback_validator",
        )

        require(
            callable(
                getattr(
                    manager,
                    "apply_request",
                    None,
                )
            ),
            "manager apply_request() is missing",
        )
        require(
            callable(
                getattr(
                    validator,
                    "normalize_record",
                    None,
                )
            ),
            "validator normalize_record() is missing",
        )

        try:
            normalized = manager.apply_request(
                current=current_record,
                request=(
                    draft_result.initialize_request
                ),
                schema=schema,
                validator=validator,
            )
        except Exception as exc:
            raise XDraftFeedbackRegistrationError(
                "X-FB dry-run registration failed: "
                f"{exc}"
            ) from exc

        require(
            isinstance(normalized, dict),
            "normalized record must be an object",
        )
        require(
            normalized.get("feedback_id")
            == feedback_id,
            "normalized feedback_id mismatch",
        )
        require(
            normalized.get("record_version") == 1,
            "INITIALIZE must produce record_version=1",
        )
        require(
            normalized.get("record_stage")
            == "DRAFT_GENERATED",
            (
                "INITIALIZE must produce "
                "record_stage=DRAFT_GENERATED"
            ),
        )
        require(
            normalized.get("review_status")
            == "UNREVIEWED",
            (
                "INITIALIZE must produce "
                "review_status=UNREVIEWED"
            ),
        )

        snapshots = normalized.get(
            "text_snapshots"
        )

        require(
            isinstance(snapshots, dict),
            "text_snapshots must be an object",
        )
        require(
            snapshots.get("generated_text")
            == draft_result.generated_text,
            "generated_text was not preserved",
        )

        record_boundary = normalized.get(
            "execution_boundary"
        )

        require(
            isinstance(record_boundary, dict),
            "record execution_boundary must be an object",
        )
        validate_manager_boundary(record_boundary)

        require(
            not current_record_path.exists(),
            (
                "dry-run registration must not create "
                "current.json"
            ),
        )
        require(
            not operation_result_path.exists(),
            (
                "dry-run registration must not create "
                "operation result JSON"
            ),
        )

        return XDraftFeedbackDryRunResult(
            status="PASS_DRY_RUN_NO_WRITE",
            dry_run=True,
            storage_root=str(resolved_root),
            feedback_id=feedback_id,
            current_record_path=str(
                current_record_path
            ),
            operation_result_path=str(
                operation_result_path
            ),
            current_record_existed_before=(
                current_existed_before
            ),
            current_record_written=False,
            operation_result_written=False,
            generated_text=(
                draft_result.generated_text
            ),
            character_count=(
                draft_result.character_count
            ),
            contains_pr=(
                draft_result.contains_pr
            ),
            initialize_request=(
                draft_result.initialize_request
            ),
            normalized_record=normalized,
            record_execution_boundary=(
                record_boundary
            ),
            manager_execution_boundary=(
                manager_boundary
            ),
        )
