#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


class LookupValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LookupValidationError(message)


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise LookupValidationError(
            f"required file missing: {path}"
        )

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LookupValidationError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise LookupValidationError(
            f"JSON root must be an object: {path}"
        )

    return value


def validate_mock_fixture(
    fixture: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> dict[str, Any]:
    fixture_policy = policy["mock_fixture"]
    transport = policy["transport_contract"]

    require(
        fixture.get("phase_id") == "LS-NEW-BATCH-4G-1",
        "mock fixture phase mismatch",
    )
    require(
        fixture.get("source_type")
        == fixture_policy["required_source_type"],
        "mock fixture source_type mismatch",
    )
    require(
        fixture.get("production_usable") is False,
        "mock fixture must not be production usable",
    )
    require(
        fixture.get("payload_injection_allowed") is False,
        "mock fixture payload injection must remain blocked",
    )

    request = fixture.get("request")

    require(
        isinstance(request, dict),
        "mock request must be an object",
    )
    require(
        request.get("method")
        == transport["allowed_http_method"],
        "mock request method mismatch",
    )
    require(
        request.get("rest_path")
        == transport["allowed_rest_path"],
        "mock request endpoint mismatch",
    )
    require(
        request.get("request_body") is None,
        "mock request body must remain null",
    )
    require(
        request.get("authorization_header_present")
        is False,
        "mock authorization header must remain absent",
    )

    response = fixture.get("response")

    require(
        isinstance(response, dict),
        "mock response must be an object",
    )
    require(
        response.get("http_status")
        == fixture_policy["required_http_status"],
        "mock HTTP status mismatch",
    )
    require(
        response.get("content_type")
        == fixture_policy["required_content_type"],
        "mock content type mismatch",
    )

    body = response.get("body")

    require(
        isinstance(body, list),
        "mock response body must be an array",
    )
    require(
        len(body)
        <= policy["response_contract"]["maximum_items"],
        "mock response contains too many items",
    )

    required_fields = set(
        policy["response_contract"]["required_fields"]
    )

    normalized_items: list[dict[str, Any]] = []

    for index, item in enumerate(body, start=1):
        require(
            isinstance(item, dict),
            f"mock response item[{index}] must be an object",
        )
        require(
            required_fields.issubset(item),
            f"mock response item[{index}] missing fields",
        )

        category_id = item.get("id")
        slug = item.get("slug")
        name = item.get("name")
        count = item.get("count")

        require(
            isinstance(category_id, int)
            and not isinstance(category_id, bool)
            and category_id > 0,
            f"mock response item[{index}] invalid category ID",
        )
        require(
            fixture_policy["reserved_category_id_minimum"]
            <= category_id
            <= fixture_policy[
                "reserved_category_id_maximum"
            ],
            f"mock response item[{index}] category ID "
            "outside reserved fixture range",
        )
        require(
            isinstance(slug, str) and slug.strip(),
            f"mock response item[{index}] invalid slug",
        )
        require(
            isinstance(name, str) and name.strip(),
            f"mock response item[{index}] invalid name",
        )
        require(
            isinstance(count, int)
            and not isinstance(count, bool)
            and count >= 0,
            f"mock response item[{index}] invalid count",
        )

        normalized_items.append(
            {
                "id": category_id,
                "slug": slug.strip(),
                "name": name.strip(),
                "count": count,
            }
        )

    return {
        "request": copy.deepcopy(request),
        "response": {
            "http_status": response["http_status"],
            "content_type": response["content_type"],
            "body": normalized_items,
        },
        "mock_response_digest_sha256": canonical_digest(
            normalized_items
        ),
    }


def validate_mock_query_for_target(
    normalized_fixture: dict[str, Any],
    *,
    target: dict[str, str],
) -> None:
    request = normalized_fixture["request"]

    expected_query = {
        "slug": target["category_slug"],
        "per_page": 100,
        "_fields": "id,slug,name,count",
    }

    require(
        request.get("query_parameters") == expected_query,
        "mock query does not match target category",
    )


def match_category(
    response_items: list[dict[str, Any]],
    *,
    target_slug: str,
    target_name: str,
) -> dict[str, Any]:
    slug_matches = [
        item
        for item in response_items
        if item["slug"] == target_slug
    ]

    require(
        len(slug_matches) >= 1,
        f"category not found: {target_slug}",
    )
    require(
        len(slug_matches) == 1,
        f"duplicate category result: {target_slug}",
    )

    matched = slug_matches[0]

    require(
        matched["name"] == target_name,
        f"category name mismatch: {target_slug}",
    )

    category_id = matched["id"]

    require(
        isinstance(category_id, int)
        and not isinstance(category_id, bool)
        and category_id > 0,
        f"invalid category ID: {target_slug}",
    )

    mapping_without_digest = {
        "category_slug": target_slug,
        "category_name": target_name,
        "candidate_fixture_category_id": category_id,
        "fixture_post_count": matched["count"],
        "match_state": "MATCHED_LOCAL_MOCK_ONLY",
        "source_type": "LOCAL_WORDPRESS_API_MOCK",
        "production_usable": False,
        "payload_injection_allowed": False,
        "human_verification_required": True,
    }

    mapping = copy.deepcopy(mapping_without_digest)
    mapping["matched_mapping_digest_sha256"] = (
        canonical_digest(mapping_without_digest)
    )

    return mapping


def execute_local_mock_lookup(
    *,
    fixture: dict[str, Any],
    targets: list[dict[str, str]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    normalized_fixture = validate_mock_fixture(
        fixture,
        policy=policy,
    )

    mappings: list[dict[str, Any]] = []

    for target in targets:
        validate_mock_query_for_target(
            normalized_fixture,
            target=target,
        )

        mappings.append(
            match_category(
                normalized_fixture["response"]["body"],
                target_slug=target["category_slug"],
                target_name=target["category_name"],
            )
        )

    return {
        "transport": "LOCAL_JSON_MOCK",
        "method": "GET",
        "rest_path": "/wp-json/wp/v2/categories",
        "mock_response_digest_sha256": normalized_fixture[
            "mock_response_digest_sha256"
        ],
        "mapping_count": len(mappings),
        "mappings": mappings,
        "credential_file_read": False,
        "credential_values_loaded": False,
        "credential_values_output": False,
        "dns_resolution_performed": False,
        "network_connection_performed": False,
        "tls_connection_performed": False,
        "http_request_performed": False,
        "wordpress_response_read": False,
        "wordpress_write_performed": False,
        "production_category_ids_present": False,
        "fixture_category_ids_present": True,
        "fixture_category_ids_applied_to_payload": False,
    }
