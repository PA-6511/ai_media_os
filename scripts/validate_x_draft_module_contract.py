#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/x_draft_module_contract.json"
RESULT_PATH = ROOT / "exchange/logs/x_r1_contract_validation_result.json"
REPORT_PATH = ROOT / "reports/x_r1_contract_validation_report.md"


class ContractValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"required file missing: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractValidationError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(isinstance(data, dict), "contract root must be an object")
    return data


def validate_contract(contract: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    require(
        contract.get("schema_version") == "1.0.0",
        "schema_version must be 1.0.0",
    )
    require(contract.get("phase_id") == "X-R1", "phase_id must be X-R1")
    require(
        contract.get("contract_id") == "X_DRAFT_MODULE_CONTRACT_V1",
        "contract_id mismatch",
    )
    checks.append("identity")

    input_contract = contract.get("input_contract")
    require(isinstance(input_contract, dict), "input_contract is required")

    required_input_fields = {
        "ebook_item_id",
        "title",
        "volume_label",
        "author_name",
        "article_url",
        "wordpress_draft_id",
        "wordpress_status",
    }

    actual_input_fields = set(input_contract.get("required_fields", []))
    require(
        actual_input_fields == required_input_fields,
        "input required_fields mismatch",
    )

    field_rules = input_contract.get("field_rules")
    require(isinstance(field_rules, dict), "field_rules is required")
    require(
        field_rules.get("wordpress_status", {}).get("required_value")
        == "DRAFT",
        "wordpress_status must require DRAFT",
    )
    require(
        field_rules.get("wordpress_draft_id", {}).get("minimum") == 1,
        "wordpress_draft_id minimum must be 1",
    )
    require(
        field_rules.get("article_url", {}).get("required_scheme") == "https",
        "article_url must require https",
    )
    require(
        field_rules.get("article_url", {}).get("placeholder_forbidden")
        is True,
        "article URL placeholders must be forbidden",
    )

    wordpress_sources = input_contract.get("wordpress_success_sources")
    require(
        isinstance(wordpress_sources, list) and len(wordpress_sources) == 2,
        "exactly two WordPress success source contracts are required",
    )

    source_pairs = {
        (
            source.get("id_field"),
            source.get("status_field"),
            source.get("required_status"),
        )
        for source in wordpress_sources
        if isinstance(source, dict)
    }

    require(
        (
            "created_post_id",
            "created_post_status",
            "draft",
        )
        in source_pairs,
        "created_post_id success contract missing",
    )
    require(
        (
            "new_post_id",
            "returned_post_status",
            "draft",
        )
        in source_pairs,
        "new_post_id success contract missing",
    )
    checks.append("input_contract")

    generation = contract.get("generation_contract")
    require(isinstance(generation, dict), "generation_contract is required")
    require(
        generation.get("maximum_character_count") == 280,
        "maximum character count must be 280",
    )
    require(
        generation.get("include_synopsis") is False,
        "synopsis must remain disabled",
    )
    require(
        generation.get("unicode_normalization") == "NFKC",
        "Unicode normalization must be NFKC",
    )

    template_lines = generation.get("template_lines")
    require(
        isinstance(template_lines, list) and template_lines,
        "template_lines must be a non-empty list",
    )

    rendered_template = "\n".join(str(line) for line in template_lines)
    require("#PR" in rendered_template, "template must include #PR")
    require(
        "{article_url}" in rendered_template,
        "template must include article_url",
    )
    require(
        "{title}" in rendered_template,
        "template must include title",
    )
    checks.append("generation_contract")

    output_contract = contract.get("output_contract")
    require(isinstance(output_contract, dict), "output_contract is required")

    fixed_values = output_contract.get("fixed_values")
    require(isinstance(fixed_values, dict), "fixed_values is required")
    require(
        fixed_values.get("record_stage") == "DRAFT_GENERATED",
        "record_stage must be DRAFT_GENERATED",
    )
    require(
        fixed_values.get("x_status") == "DRAFT",
        "x_status must be DRAFT",
    )
    require(
        fixed_values.get("review_status") == "IN_REVIEW",
        "review_status must be IN_REVIEW",
    )

    invariants = output_contract.get("invariants")
    require(isinstance(invariants, dict), "output invariants are required")

    for invariant in (
        "generated_text_required",
        "generated_text_must_be_under_character_limit",
        "pr_disclosure_required",
        "selected_url_must_equal_article_url",
        "selected_url_placeholder_forbidden",
        "feedback_record_initialization_required",
        "silent_overwrite_forbidden",
    ):
        require(
            invariants.get(invariant) is True,
            f"output invariant must be true: {invariant}",
        )

    checks.append("output_contract")

    workflow = contract.get("workflow_mapping")
    require(isinstance(workflow, dict), "workflow_mapping is required")
    require(
        workflow.get("database_x_status_after_generation") == "DRAFT",
        "generation DB x_status must be DRAFT",
    )
    require(
        workflow.get("database_review_status_after_generation")
        == "IN_REVIEW",
        "generation review_status must be IN_REVIEW",
    )
    require(
        workflow.get("x_feedback_stage_after_generation")
        == "DRAFT_GENERATED",
        "X-FB generation stage mismatch",
    )
    require(
        workflow.get("x_feedback_human_reviewed_stage")
        == "HUMAN_REVIEWED",
        "X-FB human review stage mismatch",
    )
    require(
        workflow.get("database_review_status_after_human_approval")
        == "APPROVED",
        "DB human approval status must be APPROVED",
    )
    require(
        workflow.get("database_x_status_after_manual_post") == "POSTED",
        "manual post DB status must be POSTED",
    )
    require(
        workflow.get("failure_x_status") == "ERROR",
        "failure x_status must be ERROR",
    )
    checks.append("workflow_mapping")

    storage = contract.get("storage_contract")
    require(isinstance(storage, dict), "storage_contract is required")
    require(
        storage.get("database_table_addition_required") is False,
        "new database table must not be required",
    )
    require(
        storage.get("workflow_history_required") is True,
        "workflow history must be required",
    )
    checks.append("storage_contract")

    failure = contract.get("failure_policy")
    require(isinstance(failure, dict), "failure_policy is required")
    require(failure.get("fail_closed") is True, "fail_closed must be true")
    require(
        failure.get("partial_state_update_forbidden") is True,
        "partial state updates must be forbidden",
    )
    require(
        failure.get("automatic_retry_allowed") is False,
        "automatic retry must remain disabled",
    )
    require(
        failure.get("wordpress_draft_must_not_be_modified") is True,
        "WordPress draft modification must be forbidden",
    )
    checks.append("failure_policy")

    boundary = contract.get("execution_boundary")
    require(isinstance(boundary, dict), "execution_boundary is required")

    for forbidden_action in (
        "x_api_call_allowed",
        "x_post_allowed",
        "wordpress_write_allowed",
        "external_api_call_allowed",
        "automatic_human_approval_allowed",
        "automatic_posted_transition_allowed",
    ):
        require(
            boundary.get(forbidden_action) is False,
            f"{forbidden_action} must be false",
        )

    require(
        boundary.get("production_status") == "NO_GO",
        "production_status must be NO_GO",
    )
    require(
        boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety_state must be DRY_RUN_ONLY",
    )
    checks.append("execution_boundary")

    next_phase = contract.get("next_phase")
    require(isinstance(next_phase, dict), "next_phase is required")
    require(
        next_phase.get("phase_id") == "X-R2",
        "next phase must be X-R2",
    )
    require(
        next_phase.get("execution_allowed") is False,
        "next phase execution must remain disabled",
    )
    checks.append("next_phase")

    return checks


def write_outputs(
    contract: dict[str, Any],
    checks: list[str],
) -> dict[str, Any]:
    result = {
        "phase_id": "X-R1",
        "status": "PASS_CONTRACT_FIXED_NO_EXECUTION",
        "decision": "X_DRAFT_MODULE_CONTRACT_V1_FIXED",
        "contract_id": contract["contract_id"],
        "verified_checks": checks,
        "verified_check_count": len(checks),
        "database_table_addition_required": False,
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "wordpress_write_allowed": False,
        "external_api_call_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "ready_for_x_r2": True,
        "next_phase_execution_allowed": False,
    }

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    REPORT_PATH.write_text(
        "\n".join(
            [
                "# X-R1 X Draft Module Contract Validation",
                "",
                "## Result",
                "",
                f"- Status: `{result['status']}`",
                f"- Decision: `{result['decision']}`",
                f"- Contract: `{result['contract_id']}`",
                f"- Verified checks: `{result['verified_check_count']}`",
                "",
                "## Workflow Mapping",
                "",
                "- WordPress draft verified → X draft generation",
                "- X-FB stage → `DRAFT_GENERATED`",
                "- Database `x_status` → `DRAFT`",
                "- Database `review_status` → `IN_REVIEW`",
                "- Human approval → database `APPROVED`",
                "- Manual X post → database `POSTED`",
                "",
                "## Safety Boundary",
                "",
                "- X API call allowed: `false`",
                "- X posting allowed: `false`",
                "- WordPress write allowed: `false`",
                "- External API call allowed: `false`",
                "- Production status: `NO_GO`",
                "- Safety state: `DRY_RUN_ONLY`",
                "",
                "## Next Phase",
                "",
                "X-R2で、契約に準拠したX下書き生成サービスを実装する。",
                "このフェーズでは外部投稿、WordPress更新、DB状態更新は行わない。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return result


def main() -> int:
    try:
        contract = load_json(CONTRACT_PATH)
        checks = validate_contract(contract)
        result = write_outputs(contract, checks)
    except ContractValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": "X-R1",
                    "status": "FAIL_CONTRACT_VALIDATION",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
