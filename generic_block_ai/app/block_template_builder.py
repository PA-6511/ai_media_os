"""
block_template_builder.py — IR5-T2

BlockTemplateSpec を受け取り、ブロックAI雛形の全ファイル内容を dict として生成します。
ディスク書き込みは reports/generated_skeleton_{block_id}/ のみ（dry_run）。
外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .block_template_spec import (
    AFFILIATE_ALLOWED_PRODUCT_SOURCES,
    AFFILIATE_REQUIRED_DISCLAIMER,
    BlockTemplateSpec,
    TEMPLATE_SPEC_SCHEMA_VERSION,
)

BUILDER_SCHEMA_VERSION = "builder_v1"

# ─── ファイル内容ジェネレータ ──────────────────────────────────────────────────


def _manifest_content(spec: BlockTemplateSpec) -> str:
    return json.dumps(spec.as_manifest_dict(), ensure_ascii=False, indent=2) + "\n"


def _policy_content(spec: BlockTemplateSpec) -> str:
    policy: dict[str, Any] = {
        "policy_metadata": {
            "version": spec.policy_version,
            "environment": spec.policy_environment,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "change_reason": spec.policy_change_reason,
            "policy_hash": "AUTO_COMPUTED",
        },
        "observe_only": True,
        "forbidden_actions": spec.forbidden_actions,
        "quality_metrics": {
            "quality_score_base": 55,
            "priority_weight": 0.35,
            "accepted_risk_weight": 0.2,
            "rejection_penalty_weight": 30,
            "validation_penalty_fail": 35,
            "validation_penalty_warn": 15,
            "risk_gap_weight": 0.7,
            "risk_rejection_penalty_weight": 20,
            "readiness_min_quality_score": 60,
            "readiness_min_risk_balance": 50,
            "readiness_allowed_validation_results": ["PASS"],
        },
        "review_decision": {
            "block_on_status": ["error", "blocked"],
            "reject_on_validation_results": ["FAIL"],
            "reject_on_readiness": ["not_ready"],
            "approve_on_readiness": ["ready"],
        },
    }
    if spec.category == "affiliate":
        policy["affiliate_guardrails"] = {
            "allow_external_checkout": False,
            "allow_pii_storage": False,
            "allow_direct_purchase": False,
            "required_disclosure_text": AFFILIATE_REQUIRED_DISCLAIMER,
            "allowed_product_sources": list(AFFILIATE_ALLOWED_PRODUCT_SOURCES),
            "max_outbound_links_per_item": 3,
            "require_manual_review_before_publish": True,
        }
    return json.dumps(policy, ensure_ascii=False, indent=2) + "\n"


def _app_init_content(spec: BlockTemplateSpec) -> str:
    return f'"""Auto-generated skeleton for {spec.block_id}."""\n'


def _readme_content(spec: BlockTemplateSpec) -> str:
    cap_lines = "\n".join(
        f"- {k}: {v}" for k, v in spec.capabilities.items()
    )
    forbidden_lines = "\n".join(f"- {a}" for a in spec.forbidden_actions)
    return textwrap.dedent(f"""\
        # {spec.display_name}

        > **Auto-generated skeleton** — IR5-T4 dry-run 生成物。人間によるレビューが必要です。

        block_id: `{spec.block_id}`
        version: `{spec.version}`
        category: `{spec.category}`
        risk_level: `{spec.risk_level}`
        mode: `dry_run`
        operation_mode: `OBSERVE`

        ## 概要

        {spec.description or "(説明なし)"}

        ## Capabilities

        {cap_lines}

        ## Forbidden Actions

        {forbidden_lines}

        ## 安全ゲート

        - dry_run: 維持
        - OBSERVE: 維持
        - requires_human_approval: true
        - auto_execute_allowed: false
        - external_write_executed: false
    """)


def _tests_init_content() -> str:
    return '"""Tests for auto-generated block skeleton."""\n'


def _conftest_content(spec: BlockTemplateSpec) -> str:
    return textwrap.dedent(f"""\
        import json
        from pathlib import Path

        import pytest


        MANIFEST_PATH = Path(__file__).parent.parent / "block_manifest.json"
        POLICY_PATH = Path(__file__).parent.parent / "config" / "policy.json"


        @pytest.fixture()
        def manifest_data():
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


        @pytest.fixture()
        def policy_data():
            return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    """)


def _test_manifest_content(spec: BlockTemplateSpec) -> str:
    capabilities_assertions = "\n            ".join(
        f'assert manifest_data["capabilities"]["{k}"] is {str(v)}'
        for k, v in spec.capabilities.items()
    )
    return textwrap.dedent(f"""\
        \"\"\"Manifest smoke-tests for {spec.block_id}.\"\"\"


        def test_manifest_block_id(manifest_data):
            assert manifest_data["block_id"] == "{spec.block_id}"


        def test_manifest_mode(manifest_data):
            assert manifest_data["mode"] == "dry_run"


        def test_manifest_operation_mode(manifest_data):
            assert manifest_data["operation_mode"] == "OBSERVE"


        def test_manifest_requires_human_approval(manifest_data):
            assert manifest_data["approval_policy"]["requires_human_approval"] is True


        def test_manifest_auto_execute_not_allowed(manifest_data):
            assert manifest_data["approval_policy"]["auto_execute_allowed"] is False


        def test_manifest_capabilities(manifest_data):
            {capabilities_assertions}
    """)


def _runner_content() -> str:
    return textwrap.dedent(
        """\
        \"\"\"Minimal dry-run runner for generated affiliate block skeleton.\"\"\"
        from __future__ import annotations

        from datetime import datetime, timezone
        from typing import Any


        INPUT_SCHEMA_VERSION = "affiliate_input_v1"
        OUTPUT_SCHEMA_VERSION = "affiliate_candidate_v1"
        REQUIRED_INPUT_FIELDS = [
            "source",
            "title",
            "asin",
            "url",
            "campaign_type",
            "risk_flags",
        ]


        def _normalize_records(input_payload: dict[str, Any]) -> list[dict[str, Any]]:
            records = input_payload.get("records")
            if isinstance(records, list):
                return [r for r in records if isinstance(r, dict)]

            # Backward-compatible fallback (IR7)
            task_candidates = input_payload.get("task_candidates")
            if isinstance(task_candidates, list):
                normalized: list[dict[str, Any]] = []
                for i, item in enumerate(task_candidates):
                    if isinstance(item, dict):
                        normalized.append(
                            {
                                "source": str(item.get("source", "generated")),
                                "title": str(item.get("title", f"candidate-{i}")),
                                "asin": str(item.get("asin", f"ASIN{i:04d}")),
                                "url": str(item.get("url", "https://example.invalid/item")),
                                "campaign_type": str(item.get("campaign_type", "standard")),
                                "risk_flags": item.get("risk_flags", []),
                            }
                        )
                return normalized
            return []


        def _validate_record(record: dict[str, Any]) -> tuple[bool, str | None]:
            for field in REQUIRED_INPUT_FIELDS:
                if field not in record:
                    return False, f"missing_field:{field}"
            if not isinstance(record.get("risk_flags"), list):
                return False, "invalid_type:risk_flags"
            if not str(record.get("url", "")).startswith(("http://", "https://")):
                return False, "invalid_url"
            return True, None


        def _build_candidate(record: dict[str, Any]) -> dict[str, Any]:
            risk_flags = record.get("risk_flags", [])
            blocked_reason = None
            if "adult" in risk_flags:
                blocked_reason = "risk_flag_adult"
            review_required = bool(risk_flags) or blocked_reason is not None

            return {
                "article_candidate": {
                    "title": record.get("title"),
                    "summary": f"Affiliate draft for {record.get('title', 'untitled')}",
                    "source": record.get("source"),
                    "asin": record.get("asin"),
                    "url": record.get("url"),
                    "campaign_type": record.get("campaign_type"),
                },
                "review_required": review_required,
                "affiliate_disclosure": "This content may include affiliate links.",
                "blocked_reason": blocked_reason,
                "risk_flags": risk_flags,
            }


        def run_affiliate_block_dryrun(input_payload: dict[str, Any]) -> dict[str, Any]:
            records = _normalize_records(input_payload)
            accepted: list[dict[str, Any]] = []
            rejected: list[dict[str, Any]] = []

            for rec in records:
                ok, reason = _validate_record(rec)
                if ok:
                    accepted.append(rec)
                else:
                    rejected.append({"record": rec, "reason": reason})

            selected = accepted[:3]
            candidate_outputs = [_build_candidate(rec) for rec in selected]

            return {
                "status": "success",
                "decision": "human_review",
                "mode": "dry_run",
                "operation_mode": "OBSERVE",
                "input_schema": {
                    "version": INPUT_SCHEMA_VERSION,
                    "required_fields": list(REQUIRED_INPUT_FIELDS),
                },
                "output_schema": {
                    "version": OUTPUT_SCHEMA_VERSION,
                    "fields": [
                        "article_candidate",
                        "review_required",
                        "affiliate_disclosure",
                        "blocked_reason",
                        "risk_flags",
                    ],
                },
                "summary": (
                    f"dry-run processed records={len(records)}, accepted={len(accepted)}, "
                    f"selected={len(selected)}, rejected={len(rejected)}"
                ),
                "recommended_candidates": selected,
                "affiliate_candidates": candidate_outputs,
                "rejected_records": rejected,
                "safeguards": {
                    "actual_auto_execute": False,
                    "actual_auto_approve": False,
                    "external_write_executed": False,
                    "production_release": False,
                },
                "meta": {
                    "generated_runner": True,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        """
    )


def _test_runner_content() -> str:
    return textwrap.dedent(
        """\
        \"\"\"Runner smoke-tests for generated affiliate block skeleton.\"\"\"

        from app.runner import run_affiliate_block_dryrun


        def test_runner_returns_dry_run_human_review():
            result = run_affiliate_block_dryrun({"task_candidates": [{"id": 1}, {"id": 2}]})
            assert result["status"] == "success"
            assert result["decision"] == "human_review"
            assert result["mode"] == "dry_run"
            assert result["operation_mode"] == "OBSERVE"


        def test_runner_preserves_safeguards_false():
            result = run_affiliate_block_dryrun({})
            assert result["safeguards"]["actual_auto_execute"] is False
            assert result["safeguards"]["actual_auto_approve"] is False
            assert result["safeguards"]["external_write_executed"] is False
            assert result["safeguards"]["production_release"] is False


        def test_runner_supports_practical_records_schema():
            result = run_affiliate_block_dryrun(
                {
                    "records": [
                        {
                            "source": "official_api",
                            "title": "Sample Product",
                            "asin": "B000TEST01",
                            "url": "https://example.com/p/1",
                            "campaign_type": "seasonal",
                            "risk_flags": [],
                        }
                    ]
                }
            )
            assert result["input_schema"]["version"] == "affiliate_input_v1"
            assert result["output_schema"]["version"] == "affiliate_candidate_v1"
            assert len(result["affiliate_candidates"]) == 1
            assert "article_candidate" in result["affiliate_candidates"][0]
        """
    )


def _schemas_content() -> str:
    return textwrap.dedent(
        """\
        \"\"\"Practical input/output schemas for generated affiliate block skeleton.\"\"\"

        AFFILIATE_INPUT_SCHEMA = {
            "version": "affiliate_input_v1",
            "required_fields": [
                "source",
                "title",
                "asin",
                "url",
                "campaign_type",
                "risk_flags",
            ],
        }

        AFFILIATE_OUTPUT_SCHEMA = {
            "version": "affiliate_candidate_v1",
            "fields": [
                "article_candidate",
                "review_required",
                "affiliate_disclosure",
                "blocked_reason",
                "risk_flags",
            ],
        }
        """
    )


def _test_schemas_content() -> str:
    return textwrap.dedent(
        """\
        \"\"\"Schema smoke-tests for generated affiliate block skeleton.\"\"\"

        from app.schemas import AFFILIATE_INPUT_SCHEMA, AFFILIATE_OUTPUT_SCHEMA


        def test_input_schema_required_fields():
            required = {
                "source",
                "title",
                "asin",
                "url",
                "campaign_type",
                "risk_flags",
            }
            assert AFFILIATE_INPUT_SCHEMA["version"] == "affiliate_input_v1"
            assert required.issubset(set(AFFILIATE_INPUT_SCHEMA["required_fields"]))


        def test_output_schema_fields():
            fields = {
                "article_candidate",
                "review_required",
                "affiliate_disclosure",
                "blocked_reason",
                "risk_flags",
            }
            assert AFFILIATE_OUTPUT_SCHEMA["version"] == "affiliate_candidate_v1"
            assert fields.issubset(set(AFFILIATE_OUTPUT_SCHEMA["fields"]))
        """
    )


# ─── メインビルダー ───────────────────────────────────────────────────────────


def build_block_skeleton(spec: BlockTemplateSpec) -> dict[str, Any]:
    """
    BlockTemplateSpec からブロックAI雛形の全ファイル内容を生成して返す。
    ディスクへの書き込みは行わない（dry_run）。
    """
    spec_errors = spec.validate()
    if spec_errors:
        return {
            "_meta": {
                "schema_version": BUILDER_SCHEMA_VERSION,
                "spec_version": TEMPLATE_SPEC_SCHEMA_VERSION,
                "block_id": spec.block_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "ERROR",
                "errors": spec_errors,
            },
            "files": [],
            "safeguards": {
                "external_write_executed": False,
                "actual_auto_execute": False,
                "mode": "dry_run",
            },
        }

    generated_at = datetime.now(timezone.utc).isoformat()

    files = [
        {"path": "block_manifest.json", "content": _manifest_content(spec)},
        {"path": "config/policy.json", "content": _policy_content(spec)},
        {"path": "app/__init__.py", "content": _app_init_content(spec)},
        {"path": "app/schemas.py", "content": _schemas_content()},
        {"path": "app/runner.py", "content": _runner_content()},
        {"path": "README.md", "content": _readme_content(spec)},
        {"path": "tests/__init__.py", "content": _tests_init_content()},
        {"path": "tests/conftest.py", "content": _conftest_content(spec)},
        {"path": "tests/test_manifest.py", "content": _test_manifest_content(spec)},
        {"path": "tests/test_schemas.py", "content": _test_schemas_content()},
        {"path": "tests/test_runner.py", "content": _test_runner_content()},
    ]

    return {
        "_meta": {
            "schema_version": BUILDER_SCHEMA_VERSION,
            "spec_version": TEMPLATE_SPEC_SCHEMA_VERSION,
            "block_id": spec.block_id,
            "display_name": spec.display_name,
            "version": spec.version,
            "category": spec.category,
            "risk_level": spec.risk_level,
            "generated_at": generated_at,
            "status": "OK",
            "errors": [],
        },
        "files": files,
        "safeguards": {
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
        },
    }


def write_block_skeleton_dryrun(
    spec: BlockTemplateSpec,
    *,
    base_path: Path,
) -> dict[str, Any]:
    """
    build_block_skeleton の結果を reports/generated_skeleton_{block_id}/ に保存する。
    外部通信なし。生成先は reports/ 以下のみ。
    """
    skeleton = build_block_skeleton(spec)
    if skeleton["_meta"]["status"] != "OK":
        return skeleton

    output_dir = base_path / "reports" / f"generated_skeleton_{spec.block_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for file_entry in skeleton["files"]:
        dest = output_dir / file_entry["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(file_entry["content"], encoding="utf-8")
        written.append(str(dest))

    # summary JSON
    summary_path = output_dir / "_skeleton_summary.json"
    summary: dict[str, Any] = {
        "_meta": skeleton["_meta"],
        "written_files": written,
        "safeguards": skeleton["safeguards"],
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    skeleton["written_files"] = written
    skeleton["summary_path"] = str(summary_path)
    return skeleton
