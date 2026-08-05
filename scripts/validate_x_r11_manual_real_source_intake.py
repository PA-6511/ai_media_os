from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = "X-R11-MANUAL-REAL-SOURCE-INTAKE-PREP"

DEFAULT_POLICY_PATH = (
    REPOSITORY_ROOT
    / "config/x_r11_manual_real_source_intake_policy.json"
)

INTAKE_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$"
)


class XR11ManualIntakeError(RuntimeError):
    """Raised when the manual intake contract is invalid."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11ManualIntakeError(message)


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise XR11ManualIntakeError(
            f"JSON is invalid: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def normalize_row(
    row: dict[str, Any],
    header: list[str],
) -> dict[str, str]:
    return {
        field: str(
            row.get(field) or ""
        ).strip()
        for field in header
    }


def assess_url(
    value: str,
    *,
    placeholder_hosts: set[str],
) -> dict[str, Any]:
    raw_url = value.strip()

    if not raw_url:
        return {
            "url": None,
            "host": None,
            "valid": False,
            "blocker": "URL_MISSING",
        }

    parsed = urlparse(raw_url)
    host = (
        parsed.hostname or ""
    ).lower()

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return {
            "url": raw_url,
            "host": host or None,
            "valid": False,
            "blocker": "URL_SCHEME_INVALID",
        }

    if not host:
        return {
            "url": raw_url,
            "host": None,
            "valid": False,
            "blocker": "URL_HOST_MISSING",
        }

    if host in placeholder_hosts:
        return {
            "url": raw_url,
            "host": host,
            "valid": False,
            "blocker": "PLACEHOLDER_URL",
        }

    return {
        "url": raw_url,
        "host": host,
        "valid": True,
        "blocker": None,
    }


def validate_candidate_row(
    row: dict[str, str],
    *,
    policy: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []

    required_fields = list(
        policy["required_fields"]
    )
    allowed_categories = set(
        policy["allowed_categories"]
    )
    retail_url_fields = list(
        policy["retail_url_fields"]
    )
    placeholder_hosts = {
        str(value).lower()
        for value in policy[
            "placeholder_hosts"
        ]
    }
    synthetic_tokens = tuple(
        str(value).lower()
        for value in policy[
            "synthetic_title_tokens"
        ]
    )

    for field in required_fields:
        if not row.get(field):
            blockers.append(
                f"REQUIRED_FIELD_MISSING:{field}"
            )

    intake_id = row.get(
        "intake_id",
        "",
    )

    if (
        intake_id
        and not INTAKE_ID_PATTERN.fullmatch(
            intake_id
        )
    ):
        blockers.append(
            "INTAKE_ID_FORMAT_INVALID"
        )

    title = row.get(
        "title",
        "",
    )
    normalized_title = title.lower()

    if not title:
        blockers.append(
            "TITLE_MISSING"
        )
    elif any(
        token in normalized_title
        for token in synthetic_tokens
    ):
        blockers.append(
            "SYNTHETIC_TITLE_FORBIDDEN"
        )

    release_date = row.get(
        "release_date",
        "",
    )

    if release_date:
        try:
            date.fromisoformat(
                release_date
            )
        except ValueError:
            blockers.append(
                "RELEASE_DATE_INVALID_ISO_FORMAT"
            )

    category = row.get(
        "category",
        "",
    )

    if (
        category
        and category not in allowed_categories
    ):
        blockers.append(
            "CATEGORY_NOT_ALLOWED"
        )

    if (
        row.get("description_mode")
        and row["description_mode"]
        != policy[
            "required_description_mode"
        ]
    ):
        blockers.append(
            "DESCRIPTION_MODE_MUST_BE_MINIMAL"
        )

    if (
        row.get("human_review_state")
        and row["human_review_state"]
        != policy[
            "required_human_review_state"
        ]
    ):
        blockers.append(
            "HUMAN_REVIEW_STATE_MUST_BE_NOT_REVIEWED"
        )

    discovery_assessment = assess_url(
        row.get(
            "source_discovery_url",
            "",
        ),
        placeholder_hosts=placeholder_hosts,
    )

    if not discovery_assessment["valid"]:
        blockers.append(
            "SOURCE_DISCOVERY_URL_INVALID:"
            + str(
                discovery_assessment[
                    "blocker"
                ]
            )
        )

    publisher_assessment = assess_url(
        row.get(
            "publisher_confirmation_url",
            "",
        ),
        placeholder_hosts=placeholder_hosts,
    )

    if not publisher_assessment["valid"]:
        blockers.append(
            "PUBLISHER_CONFIRMATION_URL_INVALID:"
            + str(
                publisher_assessment[
                    "blocker"
                ]
            )
        )

    retail_assessments: dict[
        str,
        dict[str, Any],
    ] = {}

    valid_retail_url_count = 0

    for field in retail_url_fields:
        value = row.get(
            field,
            "",
        )

        if not value:
            retail_assessments[field] = {
                "url": None,
                "host": None,
                "valid": False,
                "blocker": "URL_NOT_PROVIDED",
            }
            continue

        assessment = assess_url(
            value,
            placeholder_hosts=placeholder_hosts,
        )

        retail_assessments[field] = (
            assessment
        )

        if assessment["valid"]:
            valid_retail_url_count += 1
        else:
            blockers.append(
                f"{field.upper()}_INVALID:"
                + str(
                    assessment["blocker"]
                )
            )

    minimum_retail_count = int(
        policy[
            "minimum_valid_retail_url_count"
        ]
    )

    if (
        valid_retail_url_count
        < minimum_retail_count
    ):
        blockers.append(
            "VALID_RETAIL_URL_COUNT_BELOW_MINIMUM"
        )

    candidate_payload = {
        "intake_id": intake_id,
        "title": title,
        "volume_label": row.get(
            "volume_label"
        ),
        "release_date": release_date,
        "publisher": row.get(
            "publisher"
        ),
        "authors": row.get(
            "authors"
        ),
        "category": category,
        "source_discovery_url": row.get(
            "source_discovery_url"
        ),
        "publisher_confirmation_url": (
            row.get(
                "publisher_confirmation_url"
            )
        ),
        "amazon_url": row.get(
            "amazon_url"
        ),
        "rakuten_kobo_url": row.get(
            "rakuten_kobo_url"
        ),
        "dmm_url": row.get(
            "dmm_url"
        ),
        "description_mode": row.get(
            "description_mode"
        ),
        "human_review_state": row.get(
            "human_review_state"
        ),
    }

    candidate_digest = (
        canonical_digest(
            candidate_payload
        )
        if not blockers
        else None
    )

    return {
        "candidate": candidate_payload,
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "valid": not blockers,
        "valid_retail_url_count": (
            valid_retail_url_count
        ),
        "source_discovery_assessment": (
            discovery_assessment
        ),
        "publisher_confirmation_assessment": (
            publisher_assessment
        ),
        "retail_url_assessments": (
            retail_assessments
        ),
        "blockers": blockers,
    }


def validate_manual_intake(
    *,
    input_csv_path: Path,
    policy_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    input_csv_path = (
        input_csv_path.resolve()
    )
    policy_path = policy_path.resolve()
    output_root = output_root.resolve()

    require(
        input_csv_path.is_file(),
        (
            "manual intake CSV is missing: "
            f"{input_csv_path}"
        ),
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    policy = load_json_object(
        policy_path
    )

    require(
        policy.get("phase") == PHASE,
        "manual intake policy phase is invalid",
    )
    require(
        policy.get("status")
        == "MANUAL_REAL_SOURCE_INTAKE_POLICY_FIXED",
        "manual intake policy status is invalid",
    )

    expected_header = list(
        policy["header"]
    )

    with input_csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        actual_header = (
            list(reader.fieldnames or [])
        )

        require(
            actual_header == expected_header,
            (
                "manual intake CSV header "
                "does not match the fixed contract"
            ),
        )

        rows = [
            normalize_row(
                dict(row),
                expected_header,
            )
            for row in reader
            if any(
                str(value or "").strip()
                for value in row.values()
            )
        ]

    maximum_rows = int(
        policy["maximum_rows"]
    )

    assessments = [
        validate_candidate_row(
            row,
            policy=policy,
        )
        for row in rows
    ]

    valid_rows = [
        assessment
        for assessment in assessments
        if assessment["valid"]
    ]

    if not rows:
        status = (
            "PASS_MANUAL_REAL_SOURCE_INTAKE_"
            "TEMPLATE_READY_NO_EXECUTION"
        )
        intake_state = (
            "EMPTY_TEMPLATE_AWAITING_"
            "ONE_REAL_SOURCE_ROW"
        )
        authorized_next_phase = (
            "MANUAL_REAL_SOURCE_DATA_ENTRY"
        )

    elif len(rows) > maximum_rows:
        status = (
            "BLOCKED_MANUAL_REAL_SOURCE_INTAKE_"
            "ROW_LIMIT_EXCEEDED"
        )
        intake_state = (
            "MULTIPLE_ROWS_FORBIDDEN"
        )
        authorized_next_phase = None

    elif len(valid_rows) == 1:
        status = (
            "PASS_MANUAL_REAL_SOURCE_INTAKE_"
            "ONE_VALID_CANDIDATE_REVIEW_REQUIRED"
        )
        intake_state = (
            "ONE_VALID_REAL_SOURCE_"
            "NOT_APPROVED_FOR_IMPORT"
        )
        authorized_next_phase = (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "MANUAL-INTAKE-HUMAN-REVIEW"
        )

    else:
        status = (
            "BLOCKED_MANUAL_REAL_SOURCE_INTAKE_"
            "INVALID_CANDIDATE"
        )
        intake_state = (
            "MANUAL_SOURCE_VALIDATION_FAILED"
        )
        authorized_next_phase = None

    policy_digest = canonical_digest(
        policy
    )

    report_payload = {
        "phase": PHASE,
        "status": status,
        "intake_state": intake_state,
        "policy_path": str(
            policy_path
        ),
        "policy_digest_sha256": (
            policy_digest
        ),
        "input_csv_path": str(
            input_csv_path
        ),
        "input_row_count": len(rows),
        "maximum_rows": maximum_rows,
        "valid_candidate_count": len(
            valid_rows
        ),
        "candidate_assessments": (
            assessments
        ),
        "candidate_selected": False,
        "human_review_required": (
            len(valid_rows) == 1
        ),
        "automatic_selection_allowed": False,
        "database_import_allowed": False,
        "workflow_update_allowed": False,
        "approval_request_creation_allowed": (
            False
        ),
        "wordpress_draft_creation_allowed": (
            False
        ),
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "MANUAL_REAL_SOURCE_INTAKE_"
            "VALIDATION_ONLY"
        ),
    }

    report_digest = canonical_digest(
        report_payload
    )

    report = {
        **report_payload,
        "manual_intake_report_digest_sha256": (
            report_digest
        ),
    }

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        output_root
        / "x_r11_manual_real_source_intake_result.json"
    )

    atomic_write_json(
        report_path,
        report,
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-csv",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = validate_manual_intake(
            input_csv_path=args.input_csv,
            policy_path=args.policy,
            output_root=args.output_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "candidate_selected": False,
                    "database_import_allowed": False,
                    "wordpress_draft_creation_allowed": (
                        False
                    ),
                    "normal_x_fb_write_allowed": False,
                    "production_execution": False,
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
