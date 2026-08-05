#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(
    os.environ.get("AI_MEDIA_OS_ROOT", str(DEFAULT_ROOT))
).resolve()

SCHEMA_PATH = ROOT / "config/x_post_wording_feedback_schema.json"
POLICY_PATH = ROOT / "config/x_fb_manual_operation_policy.json"
VALIDATOR_PATH = ROOT / "scripts/build_x_fb_0.py"

FEEDBACK_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class OperationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise OperationError(message)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise OperationError(f"required file missing: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OperationError(f"invalid JSON: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise OperationError(f"JSON root must be an object: {path}")

    return data


def load_validator() -> Any:
    if not VALIDATOR_PATH.exists():
        raise OperationError(
            f"X-FB-0 validator missing: {VALIDATOR_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "x_fb_0_validator",
        VALIDATOR_PATH,
    )

    if spec is None or spec.loader is None:
        raise OperationError("failed to load X-FB-0 validator")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_feedback_id(feedback_id: str) -> str:
    require(
        bool(FEEDBACK_ID_PATTERN.fullmatch(feedback_id)),
        "feedback_id may contain only letters, numbers, dot, "
        "underscore, and hyphen",
    )
    return feedback_id


def current_path(feedback_id: str) -> Path:
    return (
        ROOT
        / "exchange/input/x_post_feedback"
        / feedback_id
        / "current.json"
    )


def archive_path(
    feedback_id: str,
    record_version: int,
) -> Path:
    return (
        ROOT
        / "exchange/archive/x_post_feedback"
        / feedback_id
        / f"v{record_version:03d}.json"
    )


def result_path(
    feedback_id: str,
    record_version: int,
) -> Path:
    return (
        ROOT
        / "exchange/logs"
        / f"x_fb_1_{feedback_id}_v{record_version:03d}_result.json"
    )


def atomic_write_json(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def source_from_normalized(
    normalized: dict[str, Any],
) -> dict[str, Any]:
    snapshots = normalized["text_snapshots"]

    return {
        "record_version": normalized["record_version"],
        "feedback_id": normalized["feedback_id"],
        "supersedes_feedback_id": normalized.get(
            "supersedes_feedback_id"
        ),
        "article_item_id": normalized["article_item_id"],
        "wordpress_post_id": normalized.get("wordpress_post_id"),
        "template_id": normalized["template_id"],
        "record_stage": normalized["record_stage"],
        "article_context": normalized["article_context"],
        "generated_text": snapshots["generated_text"],
        "human_edited_text": snapshots["human_edited_text"],
        "actually_posted_text": snapshots["actually_posted_text"],
        "was_edited": normalized["was_edited"],
        "edit_reason_labels": normalized["edit_reason_labels"],
        "edit_reason_note": normalized["edit_reason_note"],
        "wording_labels": normalized["wording_labels"],
        "posting_adjustment_labels": normalized[
            "posting_adjustment_labels"
        ],
        "posting_adjustment_note": normalized[
            "posting_adjustment_note"
        ],
        "human_rating": normalized["human_rating"],
        "posted_at": normalized["posted_at"],
        "x_post_id": normalized["x_post_id"],
        "metrics": normalized["metrics"],
        "metric_observed_at": normalized["metric_observed_at"],
        "review_status": normalized["review_status"],
    }


def initialize_source(
    request: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    return {
        "record_version": 1,
        "feedback_id": request.get("feedback_id"),
        "supersedes_feedback_id": None,
        "article_item_id": request.get("article_item_id"),
        "wordpress_post_id": request.get("wordpress_post_id"),
        "template_id": request.get("template_id"),
        "record_stage": "DRAFT_GENERATED",
        "article_context": request.get("article_context"),
        "generated_text": request.get("generated_text"),
        "human_edited_text": None,
        "actually_posted_text": None,
        "was_edited": False,
        "edit_reason_labels": [],
        "edit_reason_note": None,
        "wording_labels": request.get("wording_labels", []),
        "posting_adjustment_labels": [],
        "posting_adjustment_note": None,
        "human_rating": None,
        "posted_at": None,
        "x_post_id": None,
        "metrics": {
            field: None
            for field in schema["metric_fields"]
        },
        "metric_observed_at": None,
        "review_status": "UNREVIEWED",
    }


def apply_request(
    current: dict[str, Any] | None,
    request: dict[str, Any],
    schema: dict[str, Any],
    validator: Any,
) -> dict[str, Any]:
    action = request.get("action")

    require(
        action in {"INITIALIZE", "REVIEW", "POST", "METRICS"},
        f"unsupported action: {action}",
    )

    request_feedback_id = request.get("feedback_id")

    require(
        isinstance(request_feedback_id, str),
        "feedback_id must be a string",
    )
    validate_feedback_id(request_feedback_id)

    if action == "INITIALIZE":
        require(
            current is None,
            "INITIALIZE is forbidden because current record exists",
        )

        source = initialize_source(request, schema)
        return validator.normalize_record(source, schema)

    require(
        current is not None,
        f"{action} requires an existing current record",
    )
    require(
        current["feedback_id"] == request_feedback_id,
        "request feedback_id does not match current record",
    )

    source = source_from_normalized(current)
    source["record_version"] = current["record_version"] + 1
    source["supersedes_feedback_id"] = current["feedback_id"]

    if action == "REVIEW":
        require(
            current["record_stage"] == "DRAFT_GENERATED",
            "REVIEW requires record_stage=DRAFT_GENERATED",
        )

        reviewed_text = validator.normalize_text(
            request.get("human_edited_text"),
            required=True,
            field_name="human_edited_text",
        )

        generated_text = current[
            "text_snapshots"
        ]["generated_text"]

        source["record_stage"] = "HUMAN_REVIEWED"
        source["human_edited_text"] = reviewed_text
        source["was_edited"] = generated_text != reviewed_text
        source["edit_reason_labels"] = request.get(
            "edit_reason_labels",
            [],
        )
        source["edit_reason_note"] = request.get(
            "edit_reason_note"
        )
        source["wording_labels"] = request.get(
            "wording_labels",
            current["wording_labels"],
        )
        source["human_rating"] = request.get("human_rating")
        source["review_status"] = "HUMAN_REVIEWED"

    elif action == "POST":
        require(
            current["record_stage"] == "HUMAN_REVIEWED",
            "POST requires record_stage=HUMAN_REVIEWED",
        )

        source["record_stage"] = "POSTED"
        source["actually_posted_text"] = request.get(
            "actually_posted_text"
        )
        source["posting_adjustment_labels"] = request.get(
            "posting_adjustment_labels",
            [],
        )
        source["posting_adjustment_note"] = request.get(
            "posting_adjustment_note"
        )
        source["posted_at"] = request.get("posted_at")
        source["x_post_id"] = request.get("x_post_id")
        source["review_status"] = "POSTED_UNMEASURED"

    elif action == "METRICS":
        require(
            current["record_stage"]
            in {"POSTED", "METRICS_RECORDED"},
            "METRICS requires a posted record",
        )

        incoming_metrics = request.get("metrics")

        require(
            isinstance(incoming_metrics, dict),
            "metrics must be an object",
        )

        merged_metrics = dict(current["metrics"])

        for field, value in incoming_metrics.items():
            require(
                field in schema["metric_fields"],
                f"unsupported metric field: {field}",
            )
            merged_metrics[field] = value

        source["record_stage"] = "METRICS_RECORDED"
        source["metrics"] = merged_metrics
        source["metric_observed_at"] = request.get(
            "metric_observed_at"
        )
        source["review_status"] = request.get("review_status")

    return validator.normalize_record(source, schema)


def build_operation_result(
    *,
    action: str,
    previous: dict[str, Any] | None,
    normalized: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "phase_id": "X-FB-1",
        "status": (
            "PASS_DRY_RUN_NO_WRITE"
            if dry_run
            else "PASS_MANUAL_RECORD_OPERATION"
        ),
        "action": action,
        "feedback_id": normalized["feedback_id"],
        "previous_record_version": (
            previous["record_version"]
            if previous is not None
            else None
        ),
        "record_version": normalized["record_version"],
        "previous_record_stage": (
            previous["record_stage"]
            if previous is not None
            else None
        ),
        "record_stage": normalized["record_stage"],
        "record_digest_sha256": normalized[
            "record_digest_sha256"
        ],
        "human_edit_detected": normalized[
            "derived_flags"
        ]["human_edit_detected"],
        "posting_adjustment_detected": normalized[
            "derived_flags"
        ]["posting_adjustment_detected"],
        "metrics_available": normalized[
            "derived_flags"
        ]["metrics_available"],
        "previous_version_archived": (
            previous is not None and not dry_run
        ),
        "current_record_written": not dry_run,
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "wordpress_write_allowed": False,
        "external_api_call_allowed": False,
        "automatic_rule_update_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "MANUAL_RECORDING_ONLY",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--request",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        schema = load_json(SCHEMA_PATH)
        policy = load_json(POLICY_PATH)
        request = load_json(args.request.resolve())
        validator = load_validator()

        require(
            policy.get("phase_id") == "X-FB-1",
            "manual operation policy phase mismatch",
        )
        require(
            schema.get("schema_id")
            == policy.get("feedback_schema_id"),
            "feedback schema reference mismatch",
        )

        feedback_id_raw = request.get("feedback_id")

        require(
            isinstance(feedback_id_raw, str),
            "feedback_id must be a string",
        )

        feedback_id = validate_feedback_id(feedback_id_raw)
        path = current_path(feedback_id)

        current = load_json(path) if path.exists() else None

        normalized = apply_request(
            current=current,
            request=request,
            schema=schema,
            validator=validator,
        )

        result = build_operation_result(
            action=request["action"],
            previous=current,
            normalized=normalized,
            dry_run=args.dry_run,
        )

        if not args.dry_run:
            if current is not None:
                old_archive_path = archive_path(
                    feedback_id,
                    current["record_version"],
                )

                if old_archive_path.exists():
                    archived = load_json(old_archive_path)

                    require(
                        archived == current,
                        "archive path already exists with "
                        "different content",
                    )
                else:
                    atomic_write_json(old_archive_path, current)

            atomic_write_json(path, normalized)

            operation_result_path = result_path(
                feedback_id,
                normalized["record_version"],
            )

            require(
                not operation_result_path.exists(),
                "operation result already exists for this version",
            )

            atomic_write_json(operation_result_path, result)

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except (
        OperationError,
        validator.ValidationError
        if "validator" in locals()
        else OperationError,
    ) as exc:
        print(
            json.dumps(
                {
                    "phase_id": "X-FB-1",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "x_api_call_allowed": False,
                    "x_post_allowed": False,
                    "wordpress_write_allowed": False,
                    "external_api_call_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
