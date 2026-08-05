#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "config/x_post_wording_feedback_schema.json"
DEFAULT_INPUT_PATH = (
    ROOT / "exchange/examples/x_post_wording_feedback_record.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT / "exchange/examples/x_post_wording_feedback_normalized.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/x_fb_0_result.json"
REPORT_PATH = ROOT / "reports/x_fb_0_minimum_feedback_record_report.md"

STAGE_ORDER = {
    "DRAFT_GENERATED": 0,
    "HUMAN_REVIEWED": 1,
    "POSTED": 2,
    "METRICS_RECORDED": 3,
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"required file missing: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"JSON root must be an object: {path}")

    return data


def normalize_text(
    value: Any,
    *,
    required: bool = False,
    field_name: str,
) -> str | None:
    if value is None:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string or null")

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = unicodedata.normalize("NFKC", normalized).strip()

    if normalized == "":
        if required:
            raise ValidationError(f"{field_name} must not be blank")
        return None

    return normalized


def parse_datetime(
    value: Any,
    *,
    required: bool,
    field_name: str,
) -> str | None:
    normalized = normalize_text(
        value,
        required=required,
        field_name=field_name,
    )

    if normalized is None:
        return None

    candidate = (
        normalized[:-1] + "+00:00"
        if normalized.endswith("Z")
        else normalized
    )

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO 8601 datetime"
        ) from exc

    require(
        parsed.tzinfo is not None,
        f"{field_name} must include a timezone offset",
    )

    return normalized


def normalize_labels(
    value: Any,
    *,
    field_name: str,
    allowed: set[str],
) -> list[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list")

    normalized: list[str] = []

    for raw_label in value:
        label = normalize_text(
            raw_label,
            required=True,
            field_name=f"{field_name} item",
        )
        assert label is not None

        if label not in allowed:
            raise ValidationError(
                f"{field_name} contains unsupported label: {label}"
            )

        normalized.append(label)

    if len(normalized) != len(set(normalized)):
        raise ValidationError(
            f"{field_name} contains duplicate labels"
        )

    return normalized


def normalize_nullable_identifier(
    value: Any,
    *,
    field_name: str,
) -> str | int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValidationError(
            f"{field_name} must be a string, integer, or null"
        )

    if isinstance(value, int):
        require(value >= 1, f"{field_name} must be positive")
        return value

    if isinstance(value, str):
        return normalize_text(
            value,
            required=False,
            field_name=field_name,
        )

    raise ValidationError(
        f"{field_name} must be a string, integer, or null"
    )


def validate_schema(schema: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        schema.get("phase_id") == "X-FB-0",
        "schema phase_id mismatch",
    )
    checks.append("schema_phase_id")

    require(
        schema.get("schema_id")
        == "X_POST_WORDING_FEEDBACK_SCHEMA_V1",
        "schema_id mismatch",
    )
    checks.append("schema_identity")

    stages = schema.get("record_stages")
    require(
        stages == list(STAGE_ORDER.keys()),
        "record stage order mismatch",
    )
    checks.append("record_stage_definition")

    label_groups = schema.get("wording_label_groups", {})
    all_wording_labels = [
        label
        for group in label_groups.values()
        for label in group
    ]

    require(
        len(all_wording_labels) == len(set(all_wording_labels)),
        "wording labels contain duplicates",
    )
    checks.append("wording_label_definition")

    boundary = schema.get("execution_boundary", {})

    require(
        boundary.get("normalized_json_write_allowed") is True,
        "normalized JSON write must be allowed",
    )
    require(
        boundary.get("x_api_call_allowed") is False,
        "X API calls must remain blocked",
    )
    require(
        boundary.get("x_post_allowed") is False,
        "X posting must remain blocked",
    )
    require(
        boundary.get("wordpress_write_allowed") is False,
        "WordPress writes must remain blocked",
    )
    require(
        boundary.get("external_api_call_allowed") is False,
        "external API calls must remain blocked",
    )
    require(
        boundary.get("automatic_rule_update_allowed") is False,
        "automatic rule updates must remain blocked",
    )
    require(
        boundary.get("algorithm_research_handoff_allowed") is False,
        "algorithm research handoff must remain blocked",
    )
    require(
        boundary.get("production_status") == "NO_GO",
        "production status must be NO_GO",
    )
    require(
        boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety state must be DRY_RUN_ONLY",
    )
    checks.append("execution_boundary")

    return checks


def normalize_article_context(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValidationError("article_context must be an object")

    return {
        "title": normalize_text(
            value.get("title"),
            required=True,
            field_name="article_context.title",
        ),
        "volume_label": normalize_text(
            value.get("volume_label"),
            required=True,
            field_name="article_context.volume_label",
        ),
        "release_date": normalize_text(
            value.get("release_date"),
            required=True,
            field_name="article_context.release_date",
        ),
        "category": normalize_text(
            value.get("category"),
            required=True,
            field_name="article_context.category",
        ),
    }


def normalize_metrics(
    value: Any,
    metric_fields: list[str],
) -> dict[str, int | None]:
    if not isinstance(value, dict):
        raise ValidationError("metrics must be an object")

    unknown_fields = set(value) - set(metric_fields)

    require(
        not unknown_fields,
        f"metrics contains unknown fields: {sorted(unknown_fields)}",
    )

    normalized: dict[str, int | None] = {}

    for field in metric_fields:
        metric = value.get(field)

        if metric is None:
            normalized[field] = None
            continue

        if isinstance(metric, bool) or not isinstance(metric, int):
            raise ValidationError(
                f"metrics.{field} must be an integer or null"
            )

        if metric < 0:
            raise ValidationError(
                f"metrics.{field} must not be negative"
            )

        normalized[field] = metric

    return normalized


def normalize_record(
    source: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    stage = normalize_text(
        source.get("record_stage"),
        required=True,
        field_name="record_stage",
    )
    assert stage is not None

    require(
        stage in STAGE_ORDER,
        f"unsupported record_stage: {stage}",
    )

    record_version = source.get("record_version")

    require(
        isinstance(record_version, int)
        and not isinstance(record_version, bool)
        and record_version >= 1,
        "record_version must be a positive integer",
    )

    generated_text = normalize_text(
        source.get("generated_text"),
        required=True,
        field_name="generated_text",
    )
    assert generated_text is not None

    human_required = STAGE_ORDER[stage] >= STAGE_ORDER["HUMAN_REVIEWED"]
    posted_required = STAGE_ORDER[stage] >= STAGE_ORDER["POSTED"]
    metrics_required = (
        STAGE_ORDER[stage] >= STAGE_ORDER["METRICS_RECORDED"]
    )

    human_edited_text = normalize_text(
        source.get("human_edited_text"),
        required=human_required,
        field_name="human_edited_text",
    )
    actually_posted_text = normalize_text(
        source.get("actually_posted_text"),
        required=posted_required,
        field_name="actually_posted_text",
    )

    was_edited = source.get("was_edited")

    require(
        isinstance(was_edited, bool),
        "was_edited must be true or false",
    )

    wording_labels_allowed = {
        label
        for group in schema["wording_label_groups"].values()
        for label in group
    }

    edit_reason_labels = normalize_labels(
        source.get("edit_reason_labels"),
        field_name="edit_reason_labels",
        allowed=set(schema["edit_reason_labels"]),
    )
    wording_labels = normalize_labels(
        source.get("wording_labels"),
        field_name="wording_labels",
        allowed=wording_labels_allowed,
    )
    posting_adjustment_labels = normalize_labels(
        source.get("posting_adjustment_labels"),
        field_name="posting_adjustment_labels",
        allowed=set(schema["posting_adjustment_labels"]),
    )

    if human_edited_text is not None:
        actual_edit_detected = generated_text != human_edited_text

        require(
            was_edited == actual_edit_detected,
            "was_edited does not match generated/reviewed text difference",
        )

        if was_edited:
            require(
                len(edit_reason_labels) >= 1,
                "edited record requires at least one edit_reason_label",
            )
        else:
            require(
                len(edit_reason_labels) == 0,
                "unedited record must not have edit_reason_labels",
            )
    else:
        require(
            was_edited is False,
            "DRAFT_GENERATED record must use was_edited=false",
        )
        require(
            len(edit_reason_labels) == 0,
            "DRAFT_GENERATED record must not have edit_reason_labels",
        )

    if actually_posted_text is not None:
        assert human_edited_text is not None

        posting_difference = (
            human_edited_text != actually_posted_text
        )

        if posting_difference:
            require(
                len(posting_adjustment_labels) >= 1,
                "posted text difference requires "
                "posting_adjustment_labels",
            )
        else:
            require(
                len(posting_adjustment_labels) == 0,
                "identical reviewed/posted text must not have "
                "posting_adjustment_labels",
            )
    else:
        require(
            len(posting_adjustment_labels) == 0,
            "unposted record must not have posting_adjustment_labels",
        )

    human_rating = source.get("human_rating")

    if human_rating is not None:
        require(
            isinstance(human_rating, int)
            and not isinstance(human_rating, bool)
            and 1 <= human_rating <= 5,
            "human_rating must be an integer from 1 to 5 or null",
        )

    posted_at = parse_datetime(
        source.get("posted_at"),
        required=posted_required,
        field_name="posted_at",
    )

    metrics = normalize_metrics(
        source.get("metrics"),
        metric_fields=schema["metric_fields"],
    )

    metric_observed_at = parse_datetime(
        source.get("metric_observed_at"),
        required=metrics_required,
        field_name="metric_observed_at",
    )

    non_null_metric_count = sum(
        value is not None
        for value in metrics.values()
    )

    if metrics_required:
        require(
            non_null_metric_count >= 1,
            "METRICS_RECORDED requires at least one metric value",
        )

    review_status = normalize_text(
        source.get("review_status"),
        required=True,
        field_name="review_status",
    )
    assert review_status is not None

    require(
        review_status in schema["review_statuses"],
        f"unsupported review_status: {review_status}",
    )

    if stage == "DRAFT_GENERATED":
        require(
            review_status == "UNREVIEWED",
            "DRAFT_GENERATED must use review_status=UNREVIEWED",
        )

    if stage == "HUMAN_REVIEWED":
        require(
            review_status == "HUMAN_REVIEWED",
            "HUMAN_REVIEWED stage must use matching review_status",
        )

    if stage == "POSTED":
        require(
            review_status == "POSTED_UNMEASURED",
            "POSTED stage must use review_status=POSTED_UNMEASURED",
        )

    if stage == "METRICS_RECORDED":
        require(
            review_status in {
                "METRICS_PARTIAL",
                "METRICS_COMPLETE",
            },
            "METRICS_RECORDED must use a metrics review_status",
        )

    edit_reason_note = normalize_text(
        source.get("edit_reason_note"),
        required=False,
        field_name="edit_reason_note",
    )
    posting_adjustment_note = normalize_text(
        source.get("posting_adjustment_note"),
        required=False,
        field_name="posting_adjustment_note",
    )

    if "OTHER" in edit_reason_labels:
        require(
            edit_reason_note is not None,
            "OTHER edit reason requires edit_reason_note",
        )

    if "OTHER" in posting_adjustment_labels:
        require(
            posting_adjustment_note is not None,
            "OTHER posting adjustment requires "
            "posting_adjustment_note",
        )

    normalized: dict[str, Any] = {
        "schema_version": schema["schema_version"],
        "schema_id": schema["schema_id"],
        "record_version": record_version,
        "feedback_id": normalize_text(
            source.get("feedback_id"),
            required=True,
            field_name="feedback_id",
        ),
        "supersedes_feedback_id": normalize_text(
            source.get("supersedes_feedback_id"),
            required=False,
            field_name="supersedes_feedback_id",
        ),
        "article_item_id": normalize_text(
            source.get("article_item_id"),
            required=True,
            field_name="article_item_id",
        ),
        "wordpress_post_id": normalize_nullable_identifier(
            source.get("wordpress_post_id"),
            field_name="wordpress_post_id",
        ),
        "template_id": normalize_text(
            source.get("template_id"),
            required=True,
            field_name="template_id",
        ),
        "record_stage": stage,
        "article_context": normalize_article_context(
            source.get("article_context")
        ),
        "text_snapshots": {
            "generated_text": generated_text,
            "human_edited_text": human_edited_text,
            "actually_posted_text": actually_posted_text,
        },
        "text_character_counts": {
            "generated_text": len(generated_text),
            "human_edited_text": (
                len(human_edited_text)
                if human_edited_text is not None
                else None
            ),
            "actually_posted_text": (
                len(actually_posted_text)
                if actually_posted_text is not None
                else None
            ),
        },
        "was_edited": was_edited,
        "edit_reason_labels": edit_reason_labels,
        "edit_reason_note": edit_reason_note,
        "wording_labels": wording_labels,
        "posting_adjustment_labels": posting_adjustment_labels,
        "posting_adjustment_note": posting_adjustment_note,
        "human_rating": human_rating,
        "posted_at": posted_at,
        "x_post_id": normalize_nullable_identifier(
            source.get("x_post_id"),
            field_name="x_post_id",
        ),
        "metrics": metrics,
        "metric_observed_at": metric_observed_at,
        "review_status": review_status,
        "derived_flags": {
            "human_edit_detected": (
                human_edited_text is not None
                and generated_text != human_edited_text
            ),
            "posting_adjustment_detected": (
                actually_posted_text is not None
                and human_edited_text is not None
                and human_edited_text != actually_posted_text
            ),
            "metrics_available": non_null_metric_count >= 1,
            "ready_for_future_learning_dataset": (
                stage in {"POSTED", "METRICS_RECORDED"}
                and actually_posted_text is not None
            ),
        },
        "execution_boundary": {
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "wordpress_write_allowed": False,
            "external_api_call_allowed": False,
            "automatic_rule_update_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
        },
    }

    canonical_source = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    normalized["record_digest_sha256"] = hashlib.sha256(
        canonical_source.encode("utf-8")
    ).hexdigest()

    return normalized


def display_path(path: Path) -> str:
    """Return a repository-relative path when possible.

    pytest and manual validation may supply files under /tmp or another
    directory outside the repository. Those paths are preserved as absolute
    paths instead of causing relative_to() to fail.
    """
    resolved_path = path.resolve()
    resolved_root = ROOT.resolve()

    try:
        return str(resolved_path.relative_to(resolved_root))
    except ValueError:
        return str(resolved_path)


def build_result(
    schema_checks: list[str],
    normalized: dict[str, Any],
    input_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    return {
        "phase_id": "X-FB-0",
        "status": "PASS_DESIGN_ONLY_NO_EXECUTION",
        "decision": "MINIMUM_X_WORDING_FEEDBACK_RECORD_BASELINE_READY",
        "schema_id": normalized["schema_id"],
        "input_path": display_path(input_path),
        "normalized_output_path": display_path(output_path),
        "feedback_id": normalized["feedback_id"],
        "record_stage": normalized["record_stage"],
        "source_text_snapshots_preserved": True,
        "generated_text_preserved": True,
        "human_edited_text_preserved": (
            normalized["text_snapshots"]["human_edited_text"]
            is not None
        ),
        "actually_posted_text_preserved": (
            normalized["text_snapshots"]["actually_posted_text"]
            is not None
        ),
        "human_edit_detected": normalized[
            "derived_flags"
        ]["human_edit_detected"],
        "posting_adjustment_detected": normalized[
            "derived_flags"
        ]["posting_adjustment_detected"],
        "verified_checks": schema_checks
        + [
            "three_text_snapshot_model",
            "edit_reason_invariant",
            "wording_label_validation",
            "posting_adjustment_invariant",
            "metric_null_and_non_negative_control",
            "record_stage_invariant",
            "record_digest_generation",
        ],
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "wordpress_write_allowed": False,
        "external_api_call_allowed": False,
        "automatic_rule_update_allowed": False,
        "algorithm_research_handoff_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "ready_for_manual_feedback_recording": True,
        "ready_for_x_fb_1": True,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# X-FB-0 Minimum Feedback Record Report

## Result

- Phase: `X-FB-0`
- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Schema: `{result["schema_id"]}`
- Feedback ID: `{result["feedback_id"]}`
- Record stage: `{result["record_stage"]}`

## Preserved Text Snapshots

- AI generated text: `{str(result["generated_text_preserved"]).lower()}`
- Human edited text: `{str(result["human_edited_text_preserved"]).lower()}`
- Actually posted text: `{str(result["actually_posted_text_preserved"]).lower()}`
- Human edit detected: `{str(result["human_edit_detected"]).lower()}`
- Posting adjustment detected: `{str(result["posting_adjustment_detected"]).lower()}`

## Safety Boundary

- X API call allowed: `false`
- X posting allowed: `false`
- WordPress write allowed: `false`
- External API call allowed: `false`
- Automatic wording-rule update allowed: `false`
- Algorithm research handoff allowed: `false`
- Production status: `NO_GO`
- Safety state: `DRY_RUN_ONLY`

## Verified Checks

{checks}

## Next State

- 手動X投稿ごとのフィードバック記録開始準備は完了
- `X-FB-1` で実記事用の記録作成手順へ進行可能
- 単一修正事例からの自動ルール更新は禁止
- アルゴリズム研究ブロックAIへの自動投入は未許可
"""


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    try:
        schema = load_json(SCHEMA_PATH)
        source = load_json(input_path)

        schema_checks = validate_schema(schema)
        normalized = normalize_record(source, schema)

        result = build_result(
            schema_checks=schema_checks,
            normalized=normalized,
            input_path=input_path,
            output_path=output_path,
        )

        if not args.check_only:
            write_json(output_path, normalized)
            write_json(RESULT_PATH, result)

            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(
                build_report(result),
                encoding="utf-8",
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
                    "phase_id": "X-FB-0",
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
