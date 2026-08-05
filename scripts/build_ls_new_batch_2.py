#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = ROOT / "config/new_release_verification_policy.json"
DEFAULT_BATCH_PATH = (
    ROOT / "exchange/examples/new_release_batch_normalized.example.json"
)
DEFAULT_VERIFICATION_PATH = (
    ROOT / "exchange/examples/new_release_verification_request.example.json"
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_verification_result.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_2_result.json"
REPORT_PATH = ROOT / "reports/ls_new_batch_2_verification_report.md"


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"required file missing: {path}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")

    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(resolved)


def normalize_text(
    value: Any,
    *,
    field_name: str,
    required: bool,
) -> str | None:
    if value is None:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be a string or null"
        )

    normalized = unicodedata.normalize("NFKC", value).strip()

    if normalized == "":
        if required:
            raise ValidationError(f"{field_name} must not be blank")
        return None

    return normalized


def comparison_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def parse_date(
    value: Any,
    *,
    field_name: str,
    required: bool,
) -> str | None:
    normalized = normalize_text(
        value,
        field_name=field_name,
        required=required,
    )

    if normalized is None:
        return None

    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must use YYYY-MM-DD"
        ) from exc

    return parsed.isoformat()


def parse_datetime(
    value: Any,
    *,
    field_name: str,
    required: bool,
) -> str | None:
    normalized = normalize_text(
        value,
        field_name=field_name,
        required=required,
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


def is_reserved_test_host(
    hostname: str,
    policy: dict[str, Any],
) -> bool:
    reserved = policy["reserved_test_domains"]

    return any(
        hostname == suffix
        or hostname.endswith("." + suffix)
        for suffix in reserved
    )


def parse_url(
    value: Any,
    *,
    field_name: str,
    required: bool,
    example_mode: bool,
    policy: dict[str, Any],
) -> str | None:
    normalized = normalize_text(
        value,
        field_name=field_name,
        required=required,
    )

    if normalized is None:
        return None

    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").lower()

    require(
        parsed.scheme == "https" and bool(hostname),
        f"{field_name} must be a valid HTTPS URL",
    )

    if not example_mode:
        require(
            not is_reserved_test_host(hostname, policy),
            f"{field_name} must not use a reserved test domain",
        )

    return normalized


def parse_price(
    value: Any,
    *,
    field_name: str,
) -> int | None:
    if value is None:
        return None

    require(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0,
        f"{field_name} must be a non-negative integer or null",
    )

    return value


def validate_policy(
    policy: dict[str, Any],
    batch: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        policy.get("phase_id") == "LS-NEW-BATCH-2",
        "policy phase_id mismatch",
    )
    checks.append("policy_phase_id")

    require(
        policy.get("policy_id")
        == "NEW_RELEASE_VERIFICATION_POLICY_V1",
        "policy_id mismatch",
    )
    checks.append("policy_identity")

    require(
        batch.get("schema_id") == policy.get("input_schema_id"),
        "normalized batch schema reference mismatch",
    )
    checks.append("batch_schema_reference")

    require(
        batch.get("template_contract_id")
        == policy.get("template_contract_id"),
        "template contract reference mismatch",
    )
    checks.append("template_contract_reference")

    boundary = policy.get("execution_boundary", {})

    require(
        boundary.get("verification_output_write_allowed") is True,
        "verification output write must be allowed",
    )
    require(
        boundary.get("external_api_call_allowed") is False,
        "external API calls must remain blocked",
    )
    require(
        boundary.get("web_scraping_allowed") is False,
        "web scraping must remain blocked",
    )
    require(
        boundary.get("wordpress_write_allowed") is False,
        "WordPress writes must remain blocked",
    )
    require(
        boundary.get("wordpress_publish_allowed") is False,
        "WordPress publishing must remain blocked",
    )
    require(
        boundary.get("x_post_allowed") is False,
        "X posting must remain blocked",
    )
    require(
        boundary.get("automatic_draft_creation_allowed") is False,
        "automatic draft creation must remain blocked",
    )
    require(
        boundary.get("production_status") == "NO_GO",
        "production status must remain NO_GO",
    )
    require(
        boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety state must remain DRY_RUN_ONLY",
    )
    checks.append("execution_boundary")

    return checks


def normalize_publisher_observation(
    value: Any,
    *,
    item_id: str,
    example_mode: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(value, dict),
        f"{item_id}: publisher_official must be an object",
    )

    status = normalize_text(
        value.get("status"),
        field_name=f"{item_id}.publisher_official.status",
        required=True,
    )
    assert status is not None

    require(
        status in policy["publisher_statuses"],
        f"{item_id}: unsupported publisher status: {status}",
    )

    checked = status == "CHECKED"

    return {
        "status": status,
        "checked_at": parse_datetime(
            value.get("checked_at"),
            field_name=(
                f"{item_id}.publisher_official.checked_at"
            ),
            required=checked,
        ),
        "url": parse_url(
            value.get("url"),
            field_name=f"{item_id}.publisher_official.url",
            required=checked,
            example_mode=example_mode,
            policy=policy,
        ),
        "title": normalize_text(
            value.get("title"),
            field_name=f"{item_id}.publisher_official.title",
            required=checked,
        ),
        "volume_label": normalize_text(
            value.get("volume_label"),
            field_name=(
                f"{item_id}.publisher_official.volume_label"
            ),
            required=checked,
        ),
        "release_date": parse_date(
            value.get("release_date"),
            field_name=(
                f"{item_id}.publisher_official.release_date"
            ),
            required=checked,
        ),
    }


def normalize_store_observation(
    value: Any,
    *,
    item_id: str,
    store_name: str,
    example_mode: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(value, dict),
        f"{item_id}: store observation must be an object: "
        f"{store_name}",
    )

    prefix = f"{item_id}.stores.{store_name}"

    status = normalize_text(
        value.get("status"),
        field_name=f"{prefix}.status",
        required=True,
    )
    assert status is not None

    require(
        status in policy["store_statuses"],
        f"{item_id}: unsupported {store_name} status: {status}",
    )

    checked = status in {"FOUND", "NOT_FOUND"}
    found = status == "FOUND"

    normalized = {
        "status": status,
        "checked_at": parse_datetime(
            value.get("checked_at"),
            field_name=f"{prefix}.checked_at",
            required=checked,
        ),
        "url": parse_url(
            value.get("url"),
            field_name=f"{prefix}.url",
            required=found,
            example_mode=example_mode,
            policy=policy,
        ),
        "title": normalize_text(
            value.get("title"),
            field_name=f"{prefix}.title",
            required=found,
        ),
        "volume_label": normalize_text(
            value.get("volume_label"),
            field_name=f"{prefix}.volume_label",
            required=found,
        ),
        "release_date": parse_date(
            value.get("release_date"),
            field_name=f"{prefix}.release_date",
            required=found,
        ),
        "price_jpy": parse_price(
            value.get("price_jpy"),
            field_name=f"{prefix}.price_jpy",
        ),
        "image_url": parse_url(
            value.get("image_url"),
            field_name=f"{prefix}.image_url",
            required=False,
            example_mode=example_mode,
            policy=policy,
        ),
    }

    if not found:
        require(
            normalized["url"] is None,
            f"{prefix}.url must be null unless status=FOUND",
        )
        require(
            normalized["title"] is None,
            f"{prefix}.title must be null unless status=FOUND",
        )
        require(
            normalized["volume_label"] is None,
            f"{prefix}.volume_label must be null unless status=FOUND",
        )
        require(
            normalized["release_date"] is None,
            f"{prefix}.release_date must be null unless status=FOUND",
        )
        require(
            normalized["price_jpy"] is None,
            f"{prefix}.price_jpy must be null unless status=FOUND",
        )
        require(
            normalized["image_url"] is None,
            f"{prefix}.image_url must be null unless status=FOUND",
        )

    return normalized


def normalize_observation(
    value: Any,
    *,
    expected_item_id: str,
    example_mode: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(value, dict),
        f"{expected_item_id}: observation must be an object",
    )

    item_id = normalize_text(
        value.get("item_id"),
        field_name="observation.item_id",
        required=True,
    )
    assert item_id is not None

    require(
        item_id == expected_item_id,
        f"observation item_id mismatch: "
        f"expected={expected_item_id}, actual={item_id}",
    )

    stores_value = value.get("stores")

    require(
        isinstance(stores_value, dict),
        f"{item_id}: stores must be an object",
    )

    require(
        set(stores_value) == set(policy["store_names"]),
        f"{item_id}: stores must contain exactly "
        f"{policy['store_names']}",
    )

    duplicate = value.get("cross_batch_duplicate_suspected")
    exclusion = value.get("manual_exclusion")

    require(
        isinstance(duplicate, bool),
        f"{item_id}: cross_batch_duplicate_suspected "
        "must be boolean",
    )
    require(
        isinstance(exclusion, bool),
        f"{item_id}: manual_exclusion must be boolean",
    )

    exclusion_reason = normalize_text(
        value.get("manual_exclusion_reason"),
        field_name=f"{item_id}.manual_exclusion_reason",
        required=exclusion,
    )

    if not exclusion:
        require(
            exclusion_reason is None,
            f"{item_id}: non-excluded record must not have "
            "manual_exclusion_reason",
        )

    return {
        "item_id": item_id,
        "publisher_official": normalize_publisher_observation(
            value.get("publisher_official"),
            item_id=item_id,
            example_mode=example_mode,
            policy=policy,
        ),
        "stores": {
            store_name: normalize_store_observation(
                stores_value[store_name],
                item_id=item_id,
                store_name=store_name,
                example_mode=example_mode,
                policy=policy,
            )
            for store_name in policy["store_names"]
        },
        "cross_batch_duplicate_suspected": duplicate,
        "manual_exclusion": exclusion,
        "manual_exclusion_reason": exclusion_reason,
        "notes": normalize_text(
            value.get("notes"),
            field_name=f"{item_id}.notes",
            required=False,
        ),
    }


def compare_source_facts(
    record: dict[str, Any],
    observation: dict[str, Any],
) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []

    expected = {
        "title": record["title"],
        "volume_label": record["volume_label"],
        "release_date": record["release_date"],
    }

    publisher = observation["publisher_official"]

    sources: list[tuple[str, dict[str, Any]]] = []

    if publisher["status"] == "CHECKED":
        sources.append(("publisher_official", publisher))

    for store_name, store in observation["stores"].items():
        if store["status"] == "FOUND":
            sources.append((store_name, store))

    for source_name, source in sources:
        for field in ["title", "volume_label"]:
            if (
                comparison_key(source[field])
                != comparison_key(expected[field])
            ):
                mismatches.append(
                    {
                        "source": source_name,
                        "field": field,
                        "expected": expected[field],
                        "observed": source[field],
                    }
                )

        if source["release_date"] != expected["release_date"]:
            mismatches.append(
                {
                    "source": source_name,
                    "field": "release_date",
                    "expected": expected["release_date"],
                    "observed": source["release_date"],
                }
            )

    return mismatches


def classify_record(
    record: dict[str, Any],
    observation: dict[str, Any],
    mismatches: list[dict[str, str]],
    policy: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if observation["manual_exclusion"]:
        reasons.append("manual_exclusion=true")
        return "EXCLUDED", reasons

    if observation["cross_batch_duplicate_suspected"]:
        reasons.append("cross_batch_duplicate_suspected=true")
        return "DUPLICATE_SUSPECTED", reasons

    publisher = observation["publisher_official"]

    if publisher["status"] != "CHECKED":
        reasons.append("publisher_official_not_checked")
        return "NEEDS_RELEASE_DATE_CONFIRMATION", reasons

    release_date_mismatches = [
        mismatch
        for mismatch in mismatches
        if mismatch["field"] == "release_date"
    ]

    if release_date_mismatches:
        reasons.append("release_date_mismatch_detected")
        return "NEEDS_RELEASE_DATE_CONFIRMATION", reasons

    factual_mismatches = [
        mismatch
        for mismatch in mismatches
        if mismatch["field"] in {"title", "volume_label"}
    ]

    if factual_mismatches:
        reasons.append("title_or_volume_mismatch_detected")
        return "FACT_MISMATCH", reasons

    found_stores = [
        store_name
        for store_name, store in observation["stores"].items()
        if store["status"] == "FOUND"
    ]

    if len(found_stores) == 0:
        reasons.append("no_store_page_found")
        return "STORE_PAGE_NOT_FOUND", reasons

    image_urls = [
        record.get("image", {}).get("url")
    ] + [
        store["image_url"]
        for store in observation["stores"].values()
    ]

    if not any(image_urls):
        reasons.append("no_verified_image_available")
        return "MISSING_IMAGE", reasons

    minimum_store_count = policy[
        "draft_readiness"
    ]["minimum_found_store_count"]

    if len(found_stores) < minimum_store_count:
        reasons.append(
            f"found_store_count={len(found_stores)}"
        )
        reasons.append(
            f"minimum_found_store_count={minimum_store_count}"
        )
        return "PARTIAL_STORE_COVERAGE", reasons

    confirmed_prices = [
        store["price_jpy"]
        for store in observation["stores"].values()
        if store["status"] == "FOUND"
        and store["price_jpy"] is not None
    ]

    minimum_price_count = policy[
        "draft_readiness"
    ]["minimum_confirmed_price_count"]

    if len(confirmed_prices) < minimum_price_count:
        reasons.append(
            f"confirmed_price_count={len(confirmed_prices)}"
        )
        reasons.append(
            f"minimum_confirmed_price_count={minimum_price_count}"
        )
        return "NEEDS_PRICE_CONFIRMATION", reasons

    reasons.append("publisher_official_confirmed")
    reasons.append(
        f"found_store_count={len(found_stores)}"
    )
    reasons.append(
        f"confirmed_price_count={len(confirmed_prices)}"
    )
    reasons.append("verified_image_available")

    return "READY_FOR_DRAFT", reasons


def choose_image(
    record: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    existing_url = record.get("image", {}).get("url")

    if existing_url:
        return {
            "source": record["image"]["source"],
            "url": existing_url,
        }

    priority = [
        "rakuten_kobo",
        "amazon",
        "dmm",
    ]

    for store_name in priority:
        image_url = observation["stores"][store_name][
            "image_url"
        ]

        if image_url:
            return {
                "source": store_name,
                "url": image_url,
            }

    return {
        "source": "none",
        "url": None,
    }


def build_verified_item(
    record: dict[str, Any],
    observation: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    mismatches = compare_source_facts(
        record=record,
        observation=observation,
    )

    classification, reasons = classify_record(
        record=record,
        observation=observation,
        mismatches=mismatches,
        policy=policy,
    )

    resolved_store_links = dict(record["store_links"])
    resolved_prices = dict(record["prices_jpy"])

    for store_name, store in observation["stores"].items():
        if store["status"] == "FOUND":
            resolved_store_links[store_name] = store["url"]
            resolved_prices[store_name] = store["price_jpy"]

    return {
        "item_id": record["item_id"],
        "batch_id": record["batch_id"],
        "title": record["title"],
        "volume_label": record["volume_label"],
        "release_date": record["release_date"],
        "publisher": record["publisher"],
        "authors": record["authors"],
        "category": record["category"],
        "source_record_status": record["item_status"],
        "verification_classification": classification,
        "classification_reasons": reasons,
        "mismatches": mismatches,
        "publisher_official": observation[
            "publisher_official"
        ],
        "stores": observation["stores"],
        "resolved_store_links": resolved_store_links,
        "resolved_prices_jpy": resolved_prices,
        "resolved_image": choose_image(
            record=record,
            observation=observation,
        ),
        "cross_batch_duplicate_suspected": observation[
            "cross_batch_duplicate_suspected"
        ],
        "manual_exclusion": observation["manual_exclusion"],
        "manual_exclusion_reason": observation[
            "manual_exclusion_reason"
        ],
        "notes": observation["notes"],
        "wordpress_status": "draft",
        "wordpress_write_allowed": False,
    }


def build_verification_output(
    batch: dict[str, Any],
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    require(
        request.get("phase_id") == "LS-NEW-BATCH-2",
        "verification request phase_id mismatch",
    )

    require(
        request.get("batch_id") == batch.get("batch_id"),
        "verification request batch_id mismatch",
    )

    request_version = request.get("request_version")

    require(
        isinstance(request_version, int)
        and not isinstance(request_version, bool)
        and request_version >= 1,
        "request_version must be a positive integer",
    )

    example_mode = request.get("example_mode", False)

    require(
        isinstance(example_mode, bool),
        "example_mode must be boolean",
    )

    observations_value = request.get("observations")

    require(
        isinstance(observations_value, list),
        "observations must be a list",
    )

    observation_by_item: dict[str, dict[str, Any]] = {}

    for raw_observation in observations_value:
        require(
            isinstance(raw_observation, dict),
            "each observation must be an object",
        )

        raw_item_id = raw_observation.get("item_id")

        require(
            isinstance(raw_item_id, str),
            "each observation requires string item_id",
        )
        require(
            raw_item_id not in observation_by_item,
            f"duplicate observation item_id: {raw_item_id}",
        )

        observation_by_item[raw_item_id] = raw_observation

    batch_item_ids = {
        record["item_id"]
        for record in batch["records"]
    }

    require(
        set(observation_by_item) == batch_item_ids,
        "observations must contain exactly one entry for every "
        "normalized batch item",
    )

    verified_items: list[dict[str, Any]] = []

    for record in batch["records"]:
        normalized_observation = normalize_observation(
            observation_by_item[record["item_id"]],
            expected_item_id=record["item_id"],
            example_mode=example_mode,
            policy=policy,
        )

        verified_items.append(
            build_verified_item(
                record=record,
                observation=normalized_observation,
                policy=policy,
            )
        )

    counts = dict(
        sorted(
            Counter(
                item["verification_classification"]
                for item in verified_items
            ).items()
        )
    )

    ready_count = counts.get("READY_FOR_DRAFT", 0)

    return {
        "schema_version": "1.0.0",
        "phase_id": "LS-NEW-BATCH-2",
        "policy_id": policy["policy_id"],
        "input_schema_id": batch["schema_id"],
        "template_contract_id": batch[
            "template_contract_id"
        ],
        "batch_id": batch["batch_id"],
        "request_version": request_version,
        "example_mode": example_mode,
        "record_count": len(verified_items),
        "classification_counts": counts,
        "ready_for_draft_count": ready_count,
        "all_records_classified": (
            len(verified_items) == batch["record_count"]
        ),
        "items": verified_items,
        "execution_boundary": {
            "external_api_call_allowed": False,
            "web_scraping_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_post_allowed": False,
            "automatic_draft_creation_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
        },
    }


def build_phase_result(
    *,
    policy_checks: list[str],
    output: dict[str, Any],
    batch_path: Path,
    verification_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    return {
        "phase_id": "LS-NEW-BATCH-2",
        "status": "PASS_VERIFICATION_BASELINE_NO_EXTERNAL_ACCESS",
        "decision": "MULTI_SOURCE_VERIFICATION_AND_CLASSIFICATION_READY",
        "policy_id": output["policy_id"],
        "batch_id": output["batch_id"],
        "batch_input_path": display_path(batch_path),
        "verification_input_path": display_path(
            verification_path
        ),
        "verification_output_path": display_path(output_path),
        "record_count": output["record_count"],
        "classification_counts": output[
            "classification_counts"
        ],
        "ready_for_draft_count": output[
            "ready_for_draft_count"
        ],
        "all_records_classified": output[
            "all_records_classified"
        ],
        "verified_checks": policy_checks
        + [
            "observation_completeness",
            "publisher_official_validation",
            "store_observation_validation",
            "title_volume_release_date_comparison",
            "store_coverage_classification",
            "price_confirmation_classification",
            "image_availability_classification",
            "manual_exclusion_precedence",
            "duplicate_suspicion_precedence",
        ],
        "external_api_call_allowed": False,
        "web_scraping_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "x_post_allowed": False,
        "automatic_draft_creation_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "ready_for_real_verification_input": True,
        "ready_for_ls_new_batch_3": True,
        "next_phase_execution_allowed": False,
    }


def build_report(result: dict[str, Any]) -> str:
    classifications = "\n".join(
        f"- `{status}`: {count}"
        for status, count in result[
            "classification_counts"
        ].items()
    )

    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-2 Verification Report

## Result

- Phase: `LS-NEW-BATCH-2`
- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Policy: `{result["policy_id"]}`
- Batch: `{result["batch_id"]}`
- Record count: `{result["record_count"]}`
- Ready for draft count: `{result["ready_for_draft_count"]}`
- All records classified: `{str(result["all_records_classified"]).lower()}`

## Classification Counts

{classifications}

## Verified Checks

{checks}

## Safety Boundary

- External API call allowed: `false`
- Web scraping allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X posting allowed: `false`
- Automatic draft creation allowed: `false`
- Production status: `NO_GO`
- Safety state: `DRY_RUN_ONLY`

## Next State

出版社公式、Amazon、楽天Kobo、DMMの手動確認結果を入力し、
各作品を記事生成可能、要確認、除外などに分類できます。

`LS-NEW-BATCH-3` へ進行可能ですが、WordPress下書き作成権限は
まだ付与されていません。
"""


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch",
        type=Path,
        default=DEFAULT_BATCH_PATH,
    )
    parser.add_argument(
        "--verification",
        type=Path,
        default=DEFAULT_VERIFICATION_PATH,
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

    batch_path = resolve_path(args.batch)
    verification_path = resolve_path(args.verification)
    output_path = resolve_path(args.output)

    try:
        policy = load_json(POLICY_PATH)
        batch = load_json(batch_path)
        request = load_json(verification_path)

        policy_checks = validate_policy(
            policy=policy,
            batch=batch,
        )

        output = build_verification_output(
            batch=batch,
            request=request,
            policy=policy,
        )

        result = build_phase_result(
            policy_checks=policy_checks,
            output=output,
            batch_path=batch_path,
            verification_path=verification_path,
            output_path=output_path,
        )

        if not args.check_only:
            write_json(output_path, output)
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
                    "phase_id": "LS-NEW-BATCH-2",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "external_api_call_allowed": False,
                    "wordpress_write_allowed": False,
                    "x_post_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
