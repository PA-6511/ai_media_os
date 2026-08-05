from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "LOCAL-WORDPRESS-DRAFT-TEMPLATE-CONTRACT-DESIGN"
)

EXPECTED_DISCOVERY_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-TEMPLATE-CANDIDATE-DISCOVERY"
)

EXPECTED_DISCOVERY_STATUS = (
    "PASS_WORDPRESS_TEMPLATE_CANDIDATE_DISCOVERY"
)

EXPECTED_DISCOVERY_STATE = (
    "NO_USABLE_WORDPRESS_TEMPLATE_"
    "LOCAL_TEMPLATE_REQUIRED"
)

EXPECTED_DISCOVERY_DIGEST = (
    "ab2514f46aa19b401628169a679e2f7a"
    "406264edefc500e1e763a351b6493567"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_CONTRACT_ID = (
    "X_R11_LOCAL_WORDPRESS_DRAFT_TEMPLATE_V1"
)

EXPECTED_TEMPLATE_PATH = (
    "templates/wordpress/"
    "x_r11_new_release_draft_v1.html"
)

EXPECTED_CATEGORY = {
    "id": 43,
    "name": "コミック新刊",
    "slug": "comic-new-release",
}

EXPECTED_REQUIRED_MARKERS = (
    "ebook-new-release-article",
    "ebook-pr-disclosure",
    "ebook-cover-image",
    "price-cards",
    "store-buttons",
)

EXPECTED_REQUIRED_PLACEHOLDERS = (
    "title",
    "volume_label",
    "release_date_display",
    "publisher_name",
    "author_name",
    "cover_image_url",
    "cover_image_alt",
    "rakuten_affiliate_url",
)

FORBIDDEN_TAGS = (
    "script",
    "iframe",
    "form",
    "input",
    "button",
    "object",
    "embed",
)


class LocalTemplateContractError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise LocalTemplateContractError(
            message
        )


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise LocalTemplateContractError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def extract_placeholders(
    template_html: str,
) -> set[str]:
    return set(
        re.findall(
            r"\{\{([a-z][a-z0-9_]*)\}\}",
            template_html,
        )
    )


def validate_template_contract(
    contract: dict[str, Any],
    template_html: str,
) -> dict[str, Any]:
    require(
        contract.get("contract_id")
        == EXPECTED_CONTRACT_ID,
        "local template contract ID mismatch",
    )

    require(
        contract.get("contract_version")
        == 1,
        "local template contract version mismatch",
    )

    require(
        contract.get("contract_source")
        == "LOCAL_REPOSITORY",
        "template contract source mismatch",
    )

    require(
        contract.get("template_path")
        == EXPECTED_TEMPLATE_PATH,
        "template path mismatch",
    )

    require(
        contract.get("wordpress_post_type")
        == "posts",
        "WordPress post type must be posts",
    )

    require(
        contract.get("wordpress_post_status")
        == "draft",
        "WordPress status must be draft",
    )

    require(
        contract.get("wordpress_category")
        == EXPECTED_CATEGORY,
        "WordPress category contract mismatch",
    )

    require(
        contract.get(
            "source_wordpress_template_post_id"
        )
        is None,
        (
            "local contract must not depend on "
            "a WordPress template post"
        ),
    )

    require(
        contract.get(
            "invalidated_wordpress_template_post_id"
        )
        == 185,
        "invalidated template ID mismatch",
    )

    invalidated_policy = contract.get(
        "invalidated_template_policy"
    )

    require(
        isinstance(invalidated_policy, dict),
        "invalidated template policy is missing",
    )

    for field in (
        "restoration_allowed",
        "update_allowed",
        "reuse_allowed",
    ):
        require(
            invalidated_policy.get(field)
            is False,
            (
                "invalidated template policy "
                f"must block {field}"
            ),
        )

    required_markers = tuple(
        contract.get(
            "required_markers",
            [],
        )
    )

    require(
        required_markers
        == EXPECTED_REQUIRED_MARKERS,
        "required marker contract mismatch",
    )

    missing_markers = [
        marker
        for marker
        in EXPECTED_REQUIRED_MARKERS
        if marker not in template_html
    ]

    require(
        not missing_markers,
        (
            "local template markers are missing: "
            + ", ".join(missing_markers)
        ),
    )

    contract_placeholders = set(
        contract.get(
            "required_placeholders",
            [],
        )
    )

    expected_placeholders = set(
        EXPECTED_REQUIRED_PLACEHOLDERS
    )

    require(
        contract_placeholders
        == expected_placeholders,
        "required placeholder contract mismatch",
    )

    actual_placeholders = (
        extract_placeholders(
            template_html
        )
    )

    missing_placeholders = sorted(
        expected_placeholders
        - actual_placeholders
    )

    unknown_placeholders = sorted(
        actual_placeholders
        - expected_placeholders
    )

    require(
        not missing_placeholders,
        (
            "local template placeholders "
            "are missing: "
            + ", ".join(
                missing_placeholders
            )
        ),
    )

    require(
        not unknown_placeholders,
        (
            "local template contains "
            "unknown placeholders: "
            + ", ".join(
                unknown_placeholders
            )
        ),
    )

    require(
        (
            'class="ebook-new-release-article"'
            in template_html
        ),
        "article root class is missing",
    )

    require(
        (
            'data-template-contract="'
            + EXPECTED_CONTRACT_ID
            + '"'
        )
        in template_html,
        (
            "template contract data attribute "
            "is missing"
        ),
    )

    require(
        (
            'href="{{rakuten_affiliate_url}}"'
            in template_html
        ),
        "Rakuten affiliate placeholder link is missing",
    )

    require(
        'target="_blank"'
        in template_html,
        "affiliate link target is invalid",
    )

    required_rel_tokens = {
        "sponsored",
        "nofollow",
        "noopener",
        "noreferrer",
    }

    rel_match = re.search(
        r'\brel="([^"]+)"',
        template_html,
    )

    require(
        rel_match is not None,
        "affiliate rel attribute is missing",
    )

    actual_rel_tokens = set(
        rel_match.group(1).split()
    )

    require(
        required_rel_tokens.issubset(
            actual_rel_tokens
        ),
        "affiliate rel tokens are incomplete",
    )

    forbidden_tags_found = [
        tag
        for tag in FORBIDDEN_TAGS
        if re.search(
            rf"<\s*{tag}\b",
            template_html,
            flags=re.IGNORECASE,
        )
    ]

    require(
        not forbidden_tags_found,
        (
            "forbidden HTML tags found: "
            + ", ".join(
                forbidden_tags_found
            )
        ),
    )

    require(
        re.search(
            r"\son[a-z]+\s*=",
            template_html,
            flags=re.IGNORECASE,
        )
        is None,
        "inline event handler is forbidden",
    )

    require(
        re.search(
            r"\sstyle\s*=",
            template_html,
            flags=re.IGNORECASE,
        )
        is None,
        "inline style is forbidden",
    )

    require(
        re.search(
            r"https?://",
            template_html,
            flags=re.IGNORECASE,
        )
        is None,
        (
            "hardcoded external URL "
            "is forbidden"
        ),
    )

    payload_requirements = contract.get(
        "wordpress_payload_requirements"
    )

    require(
        isinstance(
            payload_requirements,
            dict,
        ),
        (
            "WordPress payload requirements "
            "are missing"
        ),
    )

    require(
        payload_requirements.get(
            "status_must_equal"
        )
        == "draft",
        "payload status must be draft",
    )

    require(
        payload_requirements.get(
            "category_ids_must_equal"
        )
        == [43],
        "payload category IDs must equal [43]",
    )

    require(
        payload_requirements.get(
            "maximum_post_create_count"
        )
        == 1,
        "maximum post count must be 1",
    )

    price_policy = contract.get(
        "price_display_policy"
    )

    require(
        isinstance(price_policy, dict),
        "price display policy is missing",
    )

    require(
        price_policy.get("mode")
        == "NO_FIXED_PRICE",
        "fixed price must not be embedded",
    )

    require(
        price_policy.get(
            "live_price_required"
        )
        is False,
        "live price must not block rendering",
    )

    cover_policy = contract.get(
        "cover_image_policy"
    )

    require(
        isinstance(cover_policy, dict),
        "cover image policy is missing",
    )

    require(
        cover_policy.get(
            "missing_image_blocks_render"
        )
        is True,
        "missing cover must block rendering",
    )

    execution_policy = contract.get(
        "execution_policy"
    )

    require(
        isinstance(execution_policy, dict),
        "execution policy is missing",
    )

    for field in (
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
        "database_write_allowed",
        "workflow_write_allowed",
        "x_write_allowed",
    ):
        require(
            execution_policy.get(field)
            is False,
            (
                "contract design must block "
                f"{field}"
            ),
        )

    require(
        execution_policy.get(
            "production_status"
        )
        == "NO_GO",
        "production status must remain NO_GO",
    )

    return {
        "contract_id": (
            EXPECTED_CONTRACT_ID
        ),
        "required_marker_results": {
            marker: True
            for marker
            in EXPECTED_REQUIRED_MARKERS
        },
        "required_placeholders": sorted(
            actual_placeholders
        ),
        "unknown_placeholders": [],
        "missing_placeholders": [],
        "forbidden_tags_found": [],
        "inline_event_handlers_found": False,
        "inline_styles_found": False,
        "hardcoded_external_urls_found": False,
        "affiliate_rel_tokens_verified": True,
        "wordpress_post_type": "posts",
        "wordpress_post_status": "draft",
        "wordpress_category_id": 43,
        "maximum_post_create_count": 1,
        "fixed_price_embedded": False,
        "contract_validation_passed": True,
    }


def build_local_template_contract_pack(
    *,
    discovery_pack_path: Path,
    production_database_path: Path,
    contract_path: Path,
    template_path: Path,
    output_path: Path,
    expected_discovery_digest: str = (
        EXPECTED_DISCOVERY_DIGEST
    ),
    expected_database_sha: str = (
        EXPECTED_DATABASE_SHA
    ),
) -> dict[str, Any]:
    discovery_pack_path = (
        discovery_pack_path.resolve()
    )
    production_database_path = (
        production_database_path.resolve()
    )
    contract_path = contract_path.resolve()
    template_path = template_path.resolve()
    output_path = output_path.resolve()

    require(
        production_database_path.is_file(),
        "production database is missing",
    )

    require(
        sha256_file(
            production_database_path
        )
        == expected_database_sha,
        "production database changed",
    )

    discovery = load_json(
        discovery_pack_path
    )

    recorded_discovery_digest = (
        discovery.get(
            "wordpress_template_candidate_"
            "discovery_digest_sha256"
        )
    )

    require(
        recorded_discovery_digest
        == expected_discovery_digest,
        "template discovery digest mismatch",
    )

    discovery_payload = {
        key: value
        for key, value in discovery.items()
        if key
        != (
            "wordpress_template_candidate_"
            "discovery_digest_sha256"
        )
    }

    require(
        canonical_digest(
            discovery_payload
        )
        == expected_discovery_digest,
        (
            "template discovery digest "
            "verification failed"
        ),
    )

    require(
        discovery.get("phase")
        == EXPECTED_DISCOVERY_PHASE,
        "template discovery phase mismatch",
    )

    require(
        discovery.get("status")
        == EXPECTED_DISCOVERY_STATUS,
        "template discovery status mismatch",
    )

    require(
        discovery.get("discovery_state")
        == EXPECTED_DISCOVERY_STATE,
        "template discovery state mismatch",
    )

    require(
        discovery.get(
            "exact_active_candidate_count"
        )
        == 0,
        "an exact WordPress template now exists",
    )

    require(
        discovery.get(
            "legacy_active_candidate_count"
        )
        == 0,
        "a legacy WordPress template now exists",
    )

    invalidated = discovery.get(
        "invalidated_template_source"
    )

    require(
        isinstance(invalidated, dict),
        "invalidated template evidence is missing",
    )

    require(
        invalidated.get("post_id")
        == 185,
        "invalidated template ID mismatch",
    )

    require(
        invalidated.get("status")
        == "trash",
        "invalidated template status mismatch",
    )

    require(
        invalidated.get(
            "usable_for_x_r11"
        )
        is False,
        "post 185 is unexpectedly usable",
    )

    category = discovery.get(
        "wordpress_category"
    )

    require(
        category
        == {
            "id": 43,
            "name": "コミック新刊",
            "slug": "comic-new-release",
            "verified": True,
        },
        "WordPress category evidence mismatch",
    )

    contract = load_json(
        contract_path
    )

    require(
        template_path.is_file(),
        "local HTML template is missing",
    )

    template_html = template_path.read_text(
        encoding="utf-8"
    )

    validation = validate_template_contract(
        contract,
        template_html,
    )

    contract_digest = canonical_digest(
        contract
    )

    template_sha256 = sha256_text(
        template_html
    )

    unresolved_render_inputs = [
        "cover_image_url",
    ]

    design_payload = {
        "phase": PHASE,
        "status": (
            "PASS_LOCAL_WORDPRESS_DRAFT_"
            "TEMPLATE_CONTRACT_FIXED"
        ),
        "design_state": (
            "LOCAL_TEMPLATE_FIXED_"
            "RENDER_INPUT_DISCOVERY_REQUIRED"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_discovery_pack_path": str(
            discovery_pack_path
        ),
        "source_discovery_digest_sha256": (
            expected_discovery_digest
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_production_database_sha256": (
            expected_database_sha
        ),
        "invalidated_wordpress_template": {
            "post_id": 185,
            "status": "trash",
            "reuse_allowed": False,
            "restoration_allowed": False,
            "update_allowed": False,
        },
        "local_template_contract": {
            "contract_id": (
                EXPECTED_CONTRACT_ID
            ),
            "contract_path": str(
                contract_path
            ),
            "contract_file_sha256": (
                sha256_file(
                    contract_path
                )
            ),
            "contract_digest_sha256": (
                contract_digest
            ),
            "template_path": str(
                template_path
            ),
            "template_sha256": (
                template_sha256
            ),
            "wordpress_post_type": (
                "posts"
            ),
            "wordpress_post_status": (
                "draft"
            ),
            "wordpress_category_id": 43,
            "maximum_post_create_count": 1,
        },
        "template_validation": (
            validation
        ),
        "render_input_requirements": {
            "already_available_from_fixed_inputs": [
                "title",
                "volume_label",
                "release_date_display",
                "publisher_name",
                "author_name",
                "rakuten_affiliate_url"
            ],
            "derived_during_render": [
                "cover_image_alt"
            ],
            "requires_read_only_discovery": (
                unresolved_render_inputs
            ),
            "fixed_price_required": False,
        },
        "unresolved_render_inputs": (
            unresolved_render_inputs
        ),
        "unresolved_render_input_count": (
            len(
                unresolved_render_inputs
            )
        ),
        "template_contract_fixed": True,
        "template_candidate_fixed": True,
        "render_dry_run_allowed": False,
        "draft_creation_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_post_creation": False,
        "wordpress_post_update": False,
        "wordpress_post_restore": False,
        "normal_x_fb_write": False,
        "x_api_call": False,
        "x_post": False,
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-DRAFT-RENDER-"
            "INPUT-DISCOVERY"
        ),
        "next_phase_execution_allowed": True,
        "production_status": "NO_GO",
        "safety_state": (
            "LOCAL_TEMPLATE_CONTRACT_FIXED_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
    }

    design = {
        **design_payload,
        "local_wordpress_draft_template_"
        "contract_design_digest_sha256": (
            canonical_digest(
                design_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        design,
    )

    return design


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--discovery-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--contract",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--template",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        design = (
            build_local_template_contract_pack(
                discovery_pack_path=(
                    args.discovery_pack
                ),
                production_database_path=(
                    args.production_db
                ),
                contract_path=args.contract,
                template_path=args.template,
                output_path=args.output,
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_LOCAL_WORDPRESS_"
                        "DRAFT_TEMPLATE_CONTRACT"
                    ),
                    "error": str(exc),
                    "render_dry_run_allowed": False,
                    "draft_creation_allowed": False,
                    "database_write": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
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
            {
                "phase": design["phase"],
                "status": design["status"],
                "design_state": (
                    design["design_state"]
                ),
                "contract_id": (
                    design[
                        "local_template_contract"
                    ]["contract_id"]
                ),
                "wordpress_category_id": 43,
                "required_marker_results": (
                    design[
                        "template_validation"
                    ][
                        "required_marker_results"
                    ]
                ),
                "required_placeholders": (
                    design[
                        "template_validation"
                    ][
                        "required_placeholders"
                    ]
                ),
                "contract_validation_passed": (
                    True
                ),
                "unresolved_render_inputs": (
                    design[
                        "unresolved_render_inputs"
                    ]
                ),
                "unresolved_render_input_count": (
                    design[
                        "unresolved_render_input_count"
                    ]
                ),
                "template_contract_fixed": True,
                "render_dry_run_allowed": False,
                "draft_creation_allowed": False,
                "database_write": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "design_pack_path": str(
                    args.output.resolve()
                ),
                "design_digest_sha256": (
                    design[
                        "local_wordpress_draft_"
                        "template_contract_design_"
                        "digest_sha256"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
