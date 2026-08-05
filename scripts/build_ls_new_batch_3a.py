#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/"
    "new_release_ready_preview_integration_policy.json"
)
ARTICLE_POLICY_PATH = (
    ROOT / "config/"
    "new_release_article_batch_dry_run_policy.json"
)
X_SCHEMA_PATH = (
    ROOT / "config/x_post_wording_feedback_schema.json"
)
VERIFICATION_PATH = (
    ROOT / "exchange/examples/"
    "new_release_verification_ready.example.json"
)
REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "new_release_article_batch_dry_run_request.example.json"
)

ARTICLE_BUILDER_PATH = (
    ROOT / "scripts/build_ls_new_batch_3.py"
)
X_MANAGER_PATH = (
    ROOT / "scripts/manage_x_feedback_record.py"
)
X_VALIDATOR_PATH = (
    ROOT / "scripts/build_x_fb_0.py"
)

OUTPUT_PATH = (
    ROOT / "exchange/examples/"
    "new_release_article_ready_preview_result.example.json"
)
X_REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "x_fb_ready_preview_initialize_request.example.json"
)
X_NORMALIZED_PATH = (
    ROOT / "exchange/examples/"
    "x_fb_ready_preview_normalized.example.json"
)
PREVIEW_ROOT = (
    ROOT / "exchange/output/new_release_article_previews"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_3a_result.json"
)
REPORT_PATH = (
    ROOT / "reports/"
    "ls_new_batch_3a_ready_preview_integration_report.md"
)


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
        raise ValidationError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise ValidationError(
            f"JSON root must be object: {path}"
        )

    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise ValidationError(
            f"failed to load module: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def display_path(path: Path) -> str:
    resolved = path.resolve()

    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(resolved)


def validate_policy(policy: dict[str, Any]) -> list[str]:
    require(
        policy.get("phase_id") == "LS-NEW-BATCH-3A",
        "integration policy phase mismatch",
    )
    require(
        policy.get("policy_id")
        == "NEW_RELEASE_READY_PREVIEW_INTEGRATION_POLICY_V1",
        "integration policy identity mismatch",
    )

    boundary = policy.get("execution_boundary", {})

    for field in [
        "external_api_call_allowed",
        "web_scraping_allowed",
        "wordpress_write_allowed",
        "wordpress_publish_allowed",
        "x_api_call_allowed",
        "x_post_allowed",
        "automatic_rule_update_allowed",
    ]:
        require(
            boundary.get(field) is False,
            f"{field} must remain false",
        )

    require(
        boundary.get("production_status") == "NO_GO",
        "production status must remain NO_GO",
    )
    require(
        boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety state must remain DRY_RUN_ONLY",
    )

    return [
        "integration_policy_identity",
        "integration_execution_boundary",
    ]


def main() -> int:
    try:
        policy = load_json(POLICY_PATH)
        article_policy = load_json(ARTICLE_POLICY_PATH)
        x_schema = load_json(X_SCHEMA_PATH)
        verification = load_json(VERIFICATION_PATH)
        request = load_json(REQUEST_PATH)

        checks = validate_policy(policy)

        article_builder = load_module(
            ARTICLE_BUILDER_PATH,
            "ls_new_batch_3_for_3a",
        )
        x_manager = load_module(
            X_MANAGER_PATH,
            "x_feedback_manager_for_3a",
        )
        x_validator = load_module(
            X_VALIDATOR_PATH,
            "x_feedback_validator_for_3a",
        )

        article_builder.validate_policy(article_policy)

        output = article_builder.build_output(
            verification=verification,
            request=request,
            policy=article_policy,
        )

        repeated_output = article_builder.build_output(
            verification=verification,
            request=request,
            policy=article_policy,
        )

        expected = policy["expected_result"]

        require(
            output["source_record_count"]
            == expected["source_record_count"],
            "source record count mismatch",
        )
        require(
            output["generated_item_count"]
            == expected["generated_item_count"],
            "expected exactly one generated item",
        )
        require(
            output["skipped_item_count"]
            == expected["skipped_item_count"],
            "ready fixture must not be skipped",
        )

        generated = output["generated_items"][0]
        repeated = repeated_output["generated_items"][0]
        payload = generated["article_payload"]
        x_candidate = generated["x_candidate"]
        x_request = generated[
            "x_feedback_initialize_request"
        ]

        require(
            generated["source_classification"]
            == expected["source_classification"],
            "source classification mismatch",
        )
        require(
            payload["post_status"]
            == expected["wordpress_status"],
            "WordPress status must remain draft",
        )
        require(
            payload["uncategorized_assigned"] is False,
            "uncategorized must not be assigned",
        )
        require(
            generated["wordpress_write_allowed"] is False,
            "WordPress write must remain blocked",
        )
        require(
            generated["x_post_allowed"] is False,
            "X posting must remain blocked",
        )
        require(
            generated["preview_digest_sha256"]
            == repeated["preview_digest_sha256"],
            "preview digest is not deterministic",
        )

        html_content = payload["content_html"]

        for element in policy["required_html_elements"]:
            require(
                element in html_content,
                f"required HTML element missing: {element}",
            )

        require(
            html_content.index("Amazon Kindle")
            < html_content.index("楽天Kobo"),
            "store display order mismatch",
        )
        require(
            "<script" not in html_content.lower(),
            "script element must not exist",
        )

        require(
            x_candidate["requires_manual_review"] is True,
            "X candidate must require manual review",
        )
        require(
            x_candidate["automatic_post_allowed"] is False,
            "automatic X posting must remain blocked",
        )
        require(
            "#" not in x_candidate[
                "candidate_text_without_url"
            ],
            "X candidate must not contain hashtags",
        )

        x_normalized = x_manager.apply_request(
            current=None,
            request=x_request,
            schema=x_schema,
            validator=x_validator,
        )

        require(
            x_normalized["record_stage"]
            == "DRAFT_GENERATED",
            "X-FB stage mismatch",
        )
        require(
            x_normalized["record_version"] == 1,
            "X-FB initial version mismatch",
        )
        require(
            x_normalized["execution_boundary"][
                "x_post_allowed"
            ]
            is False,
            "X-FB must not allow posting",
        )

        preview_path = (
            PREVIEW_ROOT
            / article_builder.safe_slug(output["batch_id"])
            / f"{payload['post_name']}.html"
        )

        write_json(OUTPUT_PATH, output)
        write_json(X_REQUEST_PATH, x_request)
        write_json(X_NORMALIZED_PATH, x_normalized)
        write_text(preview_path, html_content)

        checks.extend(
            [
                "ready_classification_input",
                "one_item_article_generation",
                "post185_html_preview_generation",
                "price_card_generation",
                "fixed_store_display_order",
                "uncategorized_exclusion",
                "x_candidate_generation",
                "x_feedback_initialize_validation",
                "deterministic_preview_digest",
            ]
        )

        result = {
            "phase_id": "LS-NEW-BATCH-3A",
            "status": (
                "PASS_READY_ITEM_INTEGRATION_"
                "PREVIEW_NO_LIVE_WRITE"
            ),
            "decision": (
                "READY_ITEM_HTML_X_FEEDBACK_"
                "INTEGRATION_VERIFIED"
            ),
            "policy_id": policy["policy_id"],
            "template_contract_id": policy[
                "template_contract_id"
            ],
            "batch_id": output["batch_id"],
            "item_id": generated["item_id"],
            "source_record_count": output[
                "source_record_count"
            ],
            "generated_item_count": output[
                "generated_item_count"
            ],
            "skipped_item_count": output[
                "skipped_item_count"
            ],
            "article_output_path": display_path(
                OUTPUT_PATH
            ),
            "html_preview_path": display_path(
                preview_path
            ),
            "x_feedback_initialize_request_path": (
                display_path(X_REQUEST_PATH)
            ),
            "x_feedback_normalized_path": display_path(
                X_NORMALIZED_PATH
            ),
            "preview_digest_sha256": generated[
                "preview_digest_sha256"
            ],
            "x_feedback_dry_run_status": (
                "PASS_DRY_RUN_NO_WRITE"
            ),
            "x_feedback_record_stage": (
                x_normalized["record_stage"]
            ),
            "verified_checks": checks,
            "external_api_call_allowed": False,
            "web_scraping_allowed": False,
            "wordpress_write_allowed": False,
            "wordpress_publish_allowed": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "automatic_rule_update_allowed": False,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
            "ready_for_real_batch_preview": True,
            "ready_for_ls_new_batch_4": True,
            "next_phase_execution_allowed": False,
        }

        write_json(RESULT_PATH, result)

        check_lines = "\n".join(
            f"- `{check}`: PASS"
            for check in checks
        )

        write_text(
            REPORT_PATH,
            f"""# LS-NEW-BATCH-3A Ready Preview Integration Report

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Batch: `{result["batch_id"]}`
- Item: `{result["item_id"]}`
- Generated items: `{result["generated_item_count"]}`
- Skipped items: `{result["skipped_item_count"]}`
- Preview digest: `{result["preview_digest_sha256"]}`

## Generated Artifacts

- Article output: `{result["article_output_path"]}`
- HTML preview: `{result["html_preview_path"]}`
- X-FB request: `{result["x_feedback_initialize_request_path"]}`
- X-FB normalized: `{result["x_feedback_normalized_path"]}`

## Verified Checks

{check_lines}

## Safety Boundary

- External API call allowed: `false`
- Web scraping allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- X API call allowed: `false`
- X posting allowed: `false`
- Automatic wording-rule update allowed: `false`
- Production status: `NO_GO`
- Safety state: `DRY_RUN_ONLY`

## Next State

READY_FOR_DRAFT作品1件について、post_id=185準拠HTML、
価格カード、ストアボタン、X候補文およびX-FB初期化処理の
ローカル統合確認が完了しました。

WordPressおよびXへの書き込みは実行していません。
""",
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except (
        ValidationError,
        x_validator.ValidationError
        if "x_validator" in locals()
        else ValidationError,
    ) as exc:
        print(
            json.dumps(
                {
                    "phase_id": "LS-NEW-BATCH-3A",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "wordpress_write_allowed": False,
                    "x_post_allowed": False,
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
