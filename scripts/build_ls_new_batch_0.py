#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PATH = ROOT / "config/post185_standard_template_contract.json"
POLICY_PATH = ROOT / "config/new_release_batch_operation_policy.json"
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_0_result.json"
REPORT_PATH = ROOT / "reports/ls_new_batch_0_standard_template_contract_report.md"


class ValidationError(RuntimeError):
    pass


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(
    contract: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    checks: list[str] = []

    require(
        contract.get("phase_id") == "LS-NEW-BATCH-0",
        "contract phase_id mismatch",
    )
    checks.append("contract_phase_id")

    require(
        contract.get("contract_id") == "POST185_STANDARD_TEMPLATE_V1_FIXED",
        "contract_id mismatch",
    )
    checks.append("contract_identity")

    source_post = contract.get("source_post", {})
    require(source_post.get("post_id") == 185, "source post_id must be 185")
    require(
        source_post.get("title") == "月曜日のたわわ 第15巻",
        "source post title mismatch",
    )
    require(
        source_post.get("standardization_completed") is True,
        "source post standardization must be completed",
    )
    checks.append("source_post_185")

    components = contract.get("required_components", {})
    require(
        components.get("store_button_order")
        == ["amazon", "rakuten_kobo", "dmm"],
        "store button order mismatch",
    )
    require(
        components.get("rakuten_cover_image") is True,
        "Rakuten cover image must be required",
    )
    require(
        components.get("price_card") is True,
        "price card must be required",
    )
    require(
        components.get("uncategorized_hidden") is True,
        "uncategorized category must be hidden",
    )
    checks.append("required_components")

    contract_boundary = contract.get("execution_boundary", {})
    require(
        contract_boundary.get("wordpress_write_allowed") is False,
        "WordPress write must remain blocked",
    )
    require(
        contract_boundary.get("wordpress_publish_allowed") is False,
        "WordPress publish must remain blocked",
    )
    require(
        contract_boundary.get("external_api_call_allowed") is False,
        "external API calls must remain blocked",
    )
    checks.append("contract_execution_boundary")

    require(
        policy.get("template_contract_id")
        == contract.get("contract_id"),
        "batch policy contract reference mismatch",
    )
    checks.append("policy_contract_reference")

    initial_operation = policy.get("initial_operation", {})
    require(
        initial_operation.get("minimum_items") == 3,
        "initial minimum batch size must be 3",
    )
    require(
        initial_operation.get("maximum_items") == 5,
        "initial maximum batch size must be 5",
    )
    require(
        initial_operation.get("wordpress_default_status") == "draft",
        "WordPress default status must be draft",
    )
    require(
        initial_operation.get("human_review_required") is True,
        "human review must be required",
    )
    checks.append("initial_batch_policy")

    policy_boundary = policy.get("execution_boundary", {})
    require(
        policy_boundary.get("batch_execution_allowed") is False,
        "batch execution must remain blocked",
    )
    require(
        policy_boundary.get("wordpress_write_allowed") is False,
        "batch WordPress write must remain blocked",
    )
    require(
        policy_boundary.get("production_status") == "NO_GO",
        "production status must be NO_GO",
    )
    require(
        policy_boundary.get("safety_state") == "DRY_RUN_ONLY",
        "safety state must be DRY_RUN_ONLY",
    )
    checks.append("policy_execution_boundary")

    return checks


def build_result(checks: list[str]) -> dict[str, Any]:
    return {
        "phase_id": "LS-NEW-BATCH-0",
        "status": "PASS_DESIGN_ONLY_NO_EXECUTION",
        "decision": "POST185_STANDARD_TEMPLATE_CONTRACT_FIXED",
        "contract_id": "POST185_STANDARD_TEMPLATE_V1_FIXED",
        "source_post_id": 185,
        "verified_checks": checks,
        "verified_check_count": len(checks),
        "template_fixed": True,
        "batch_execution_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "external_api_call_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "ready_for_ls_new_batch_1": True,
        "next_phase_execution_allowed": False
    }


def build_report(result: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{check}`: PASS"
        for check in result["verified_checks"]
    )

    return f"""# LS-NEW-BATCH-0 Standard Template Contract Report

## Result

- Phase: `LS-NEW-BATCH-0`
- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Contract: `{result["contract_id"]}`
- Source WordPress post: `{result["source_post_id"]}`
- Template fixed: `{str(result["template_fixed"]).lower()}`

## Safety Boundary

- Batch execution allowed: `false`
- WordPress write allowed: `false`
- WordPress publish allowed: `false`
- External API call allowed: `false`
- Production status: `NO_GO`
- Safety state: `DRY_RUN_ONLY`

## Verified Checks

{checks}

## Next State

`LS-NEW-BATCH-1` の入力スキーマ設計へ進める状態です。

ただし、次Phaseの実行権限、WordPress書き込み権限、
一括下書き作成権限は付与されていません。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate without writing result or report files.",
    )
    args = parser.parse_args()

    contract = load_json(CONTRACT_PATH)
    policy = load_json(POLICY_PATH)
    checks = validate(contract, policy)
    result = build_result(checks)

    if not args.check_only:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

        RESULT_PATH.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        REPORT_PATH.write_text(
            build_report(result),
            encoding="utf-8",
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
