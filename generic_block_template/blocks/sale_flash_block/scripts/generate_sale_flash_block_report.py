#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
LOG_DIR = BLOCK_DIR / "logs"

JSON_REPORT = LOG_DIR / "sale_flash_block_report.json"
MD_REPORT = LOG_DIR / "sale_flash_block_report.md"
QUALITY_GATE_JSON = LOG_DIR / "sale_review_quality_gate.json"
ARTICLE_PAYLOAD_JSON = LOG_DIR / "sale_article_payloads.json"
ARTICLE_PAYLOAD_MD = LOG_DIR / "sale_article_payloads.md"
HUMAN_REVIEW_HANDOFF_JSON = LOG_DIR / "sale_human_review_handoff.json"
HUMAN_REVIEW_HANDOFF_MD = LOG_DIR / "sale_human_review_handoff.md"
WORDPRESS_DRAFT_HANDOFF_JSON = LOG_DIR / "wordpress_draft_handoff.json"
WORDPRESS_DRAFT_HANDOFF_MD = LOG_DIR / "wordpress_draft_handoff.md"
WORDPRESS_DRAFT_VALIDATION_JSON = LOG_DIR / "wordpress_draft_payload_validation.json"
WORDPRESS_DRAFT_VALIDATION_MD = LOG_DIR / "wordpress_draft_payload_validation.md"
FINAL_HUMAN_APPROVAL_JSON = LOG_DIR / "final_human_approval_package.json"
FINAL_HUMAN_APPROVAL_MD = LOG_DIR / "final_human_approval_package.md"
WORDPRESS_DRY_RUN_EVIDENCE_JSON = LOG_DIR / "wordpress_dry_run_execution_evidence.json"
WORDPRESS_DRY_RUN_EVIDENCE_MD = LOG_DIR / "wordpress_dry_run_execution_evidence.md"
DRY_RUN_EXECUTION_BASELINE_LOCK_JSON = LOG_DIR / "sale_flash_block_dry_run_execution_baseline_lock_report.json"
DRY_RUN_EXECUTION_BASELINE_LOCK_MD = LOG_DIR / "sale_flash_block_dry_run_execution_baseline_lock_report.md"
FINAL_SIGNOFF_ARCHIVE_JSON = LOG_DIR / "final_signoff_archive.json"
FINAL_SIGNOFF_ARCHIVE_MD = LOG_DIR / "final_signoff_archive.md"
GOVERNANCE_BOUNDARY_REVIEW_JSON = LOG_DIR / "governance_boundary_review.json"
GOVERNANCE_BOUNDARY_REVIEW_MD = LOG_DIR / "governance_boundary_review.md"
PRE_PRODUCTION_BASELINE_LOCK_JSON = LOG_DIR / "sale_flash_block_v1_pre_production_baseline_lock_report.json"
PRE_PRODUCTION_BASELINE_LOCK_MD = LOG_DIR / "sale_flash_block_v1_pre_production_baseline_lock_report.md"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _overall(statuses: List[str]) -> str:
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "WARN" for s in statuses):
        return "WARN"
    return "PASS"


def generate_report(
    json_report: Path = JSON_REPORT,
    md_report: Path = MD_REPORT,
) -> Dict[str, Any]:
    intake_policy = _read_json(CONFIG_DIR / "intake_policy.json")
    source_registry = _read_json(CONFIG_DIR / "source_registry.json")
    migration_policy = _read_json(CONFIG_DIR / "migration_policy.json")
    normalized = _read_json(LOG_DIR / "normalized_sale_candidates.json")
    queue = _read_json(LOG_DIR / "sale_review_queue.json")
    readiness = _read_json(LOG_DIR / "sale_intake_readiness.json")
    if not QUALITY_GATE_JSON.exists():
        gate_module = _load_module("apply_sale_review_quality_gate", BLOCK_DIR / "scripts/apply_sale_review_quality_gate.py")
        gate_module.apply_quality_gate()
    quality_gate = _read_json(QUALITY_GATE_JSON)

    article_payload_status = "NOT_GENERATED"
    article_payload_count = 0
    skipped_article_candidate_count = 0
    top_article_payloads: List[Dict[str, Any]] = []
    article_payload_log_exists = ARTICLE_PAYLOAD_JSON.exists()
    article_payload_markdown_exists = ARTICLE_PAYLOAD_MD.exists()
    sfb3_status = "NOT_GENERATED"

    if article_payload_log_exists:
        article_payload = _read_json(ARTICLE_PAYLOAD_JSON)
        article_payload_status = str(article_payload.get("status", "NOT_GENERATED"))
        article_payload_count = int(article_payload.get("article_payload_count", 0))
        skipped_article_candidate_count = int(article_payload.get("skipped_candidate_count", 0))
        sfb3_status = article_payload_status

        for item in article_payload.get("payloads", [])[:3]:
            top_article_payloads.append(
                {
                    "payload_id": item.get("payload_id", ""),
                    "title": item.get("title", ""),
                    "review_bucket": item.get("review_bucket", ""),
                    "priority_score": item.get("priority_score", 0),
                }
            )

    human_review_handoff_status = "NOT_GENERATED"
    human_review_handoff_count = 0
    adopt_candidate_count = 0
    needs_fix_candidate_count = 0
    excluded_candidate_count = 0
    human_review_handoff_log_exists = HUMAN_REVIEW_HANDOFF_JSON.exists()
    human_review_handoff_markdown_exists = HUMAN_REVIEW_HANDOFF_MD.exists()
    sfb4_status = "NOT_GENERATED"
    top_review_targets: List[Dict[str, Any]] = []
    human_approval_consumed = False
    final_publish_decision_allowed = False

    if human_review_handoff_log_exists:
        handoff = _read_json(HUMAN_REVIEW_HANDOFF_JSON)
        human_review_handoff_status = str(handoff.get("status", "NOT_GENERATED"))
        human_review_handoff_count = int(handoff.get("handoff_item_count", 0))
        adopt_candidate_count = int(handoff.get("adopt_candidate_count", 0))
        needs_fix_candidate_count = int(handoff.get("needs_fix_candidate_count", 0))
        excluded_candidate_count = int(handoff.get("excluded_candidate_count", 0))
        top_review_targets = list(handoff.get("top_review_targets", []))
        human_approval_consumed = bool(handoff.get("human_approval_consumed", False))
        final_publish_decision_allowed = bool(handoff.get("final_publish_decision_allowed", False))
        sfb4_status = human_review_handoff_status

    statuses = [
        str(normalized.get("status", "FAIL")),
        str(queue.get("status", "FAIL")),
        str(readiness.get("status", "FAIL")),
        str(quality_gate.get("status", "FAIL")),
    ]
    if article_payload_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(article_payload_status)
    if human_review_handoff_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(human_review_handoff_status)

    wordpress_draft_handoff_status = "NOT_GENERATED"
    wordpress_draft_handoff_count = 0
    wordpress_draft_handoff_log_exists = WORDPRESS_DRAFT_HANDOFF_JSON.exists()
    wordpress_draft_handoff_markdown_exists = WORDPRESS_DRAFT_HANDOFF_MD.exists()
    sfb5_status = "NOT_GENERATED"
    top_wordpress_draft_candidates: List[Dict[str, Any]] = []

    if wordpress_draft_handoff_log_exists:
        wp_handoff = _read_json(WORDPRESS_DRAFT_HANDOFF_JSON)
        wordpress_draft_handoff_status = str(wp_handoff.get("status", "NOT_GENERATED"))
        wordpress_draft_handoff_count = int(wp_handoff.get("draft_payload_count", 0))
        sfb5_status = wordpress_draft_handoff_status

        for item in wp_handoff.get("draft_candidates", [])[:3]:
            top_wordpress_draft_candidates.append(
                {
                    "draft_handoff_id": item.get("draft_handoff_id", ""),
                    "title": item.get("title", ""),
                    "priority_score": item.get("priority_score", 0),
                    "post_title": item.get("wordpress_draft_candidate", {}).get("post_title", ""),
                }
            )

    if wordpress_draft_handoff_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(wordpress_draft_handoff_status)

    wordpress_draft_validation_status = "NOT_GENERATED"
    wordpress_draft_validation_count = 0
    wordpress_draft_validation_log_exists = WORDPRESS_DRAFT_VALIDATION_JSON.exists()
    wordpress_draft_validation_markdown_exists = WORDPRESS_DRAFT_VALIDATION_MD.exists()
    sfb6_status = "NOT_GENERATED"
    final_human_gate_status = "NOT_GENERATED"

    if wordpress_draft_validation_log_exists:
        wp_validation = _read_json(WORDPRESS_DRAFT_VALIDATION_JSON)
        wordpress_draft_validation_status = str(wp_validation.get("status", "NOT_GENERATED"))
        wordpress_draft_validation_count = int(wp_validation.get("validated_item_count", 0))
        sfb6_status = wordpress_draft_validation_status
        final_human_gate_status = str(wp_validation.get("final_human_gate", {}).get("status", "NOT_GENERATED"))

    if wordpress_draft_validation_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(wordpress_draft_validation_status)

    final_human_approval_status = "NOT_GENERATED"
    wordpress_dry_run_execution_gate = "NOT_GENERATED"
    production_write_blocked = True
    final_human_approval_log_exists = FINAL_HUMAN_APPROVAL_JSON.exists()
    final_human_approval_markdown_exists = FINAL_HUMAN_APPROVAL_MD.exists()
    sfb7_status = "NOT_GENERATED"

    if final_human_approval_log_exists:
        sfb7 = _read_json(FINAL_HUMAN_APPROVAL_JSON)
        final_human_approval_status = str(sfb7.get("status", "NOT_GENERATED"))
        wordpress_dry_run_execution_gate = str(sfb7.get("wordpress_dry_run_execution_gate", "NOT_GENERATED"))
        production_write_blocked = bool(sfb7.get("production_write_blocked", True))
        sfb7_status = final_human_approval_status

    if final_human_approval_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(final_human_approval_status)

    wordpress_dry_run_evidence_status = "NOT_GENERATED"
    wordpress_dry_run_evidence_count = 0
    wordpress_dry_run_evidence_log_exists = WORDPRESS_DRY_RUN_EVIDENCE_JSON.exists()
    wordpress_dry_run_evidence_markdown_exists = WORDPRESS_DRY_RUN_EVIDENCE_MD.exists()
    sfb8_status = "NOT_GENERATED"

    if wordpress_dry_run_evidence_log_exists:
        sfb8 = _read_json(WORDPRESS_DRY_RUN_EVIDENCE_JSON)
        wordpress_dry_run_evidence_status = str(sfb8.get("status", "NOT_GENERATED"))
        wordpress_dry_run_evidence_count = int(sfb8.get("simulated_execution_count", 0))
        sfb8_status = wordpress_dry_run_evidence_status

    if wordpress_dry_run_evidence_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(wordpress_dry_run_evidence_status)

    dry_run_execution_baseline_lock_status = "NOT_GENERATED"
    dry_run_execution_baseline_locked = False
    dry_run_execution_baseline_lock_log_exists = DRY_RUN_EXECUTION_BASELINE_LOCK_JSON.exists()
    dry_run_execution_baseline_lock_markdown_exists = DRY_RUN_EXECUTION_BASELINE_LOCK_MD.exists()
    sfb8b_status = "NOT_GENERATED"

    if dry_run_execution_baseline_lock_log_exists:
        sfb8b = _read_json(DRY_RUN_EXECUTION_BASELINE_LOCK_JSON)
        dry_run_execution_baseline_lock_status = str(sfb8b.get("status", "NOT_GENERATED"))
        dry_run_execution_baseline_locked = bool(sfb8b.get("baseline_locked", False))
        sfb8b_status = dry_run_execution_baseline_lock_status

    if dry_run_execution_baseline_lock_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(dry_run_execution_baseline_lock_status)

    final_signoff_archive_status = "NOT_GENERATED"
    final_signoff_archive_log_exists = FINAL_SIGNOFF_ARCHIVE_JSON.exists()
    final_signoff_archive_markdown_exists = FINAL_SIGNOFF_ARCHIVE_MD.exists()
    signoff_ready = False
    sfb9_status = "NOT_GENERATED"

    if final_signoff_archive_log_exists:
        sfb9 = _read_json(FINAL_SIGNOFF_ARCHIVE_JSON)
        final_signoff_archive_status = str(sfb9.get("status", "NOT_GENERATED"))
        signoff_ready = bool(sfb9.get("signoff_ready", False))
        sfb9_status = final_signoff_archive_status

    if final_signoff_archive_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(final_signoff_archive_status)

    governance_boundary_review_status = "NOT_GENERATED"
    governance_boundary_review_log_exists = GOVERNANCE_BOUNDARY_REVIEW_JSON.exists()
    governance_boundary_review_markdown_exists = GOVERNANCE_BOUNDARY_REVIEW_MD.exists()
    governance_boundary_review_ready = False
    sfb10_status = "NOT_GENERATED"

    if governance_boundary_review_log_exists:
        sfb10 = _read_json(GOVERNANCE_BOUNDARY_REVIEW_JSON)
        governance_boundary_review_status = str(sfb10.get("status", "NOT_GENERATED"))
        governance_boundary_review_ready = bool(sfb10.get("governance_boundary_review_ready", False))
        sfb10_status = governance_boundary_review_status

    if governance_boundary_review_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(governance_boundary_review_status)

    pre_production_baseline_lock_status = "NOT_GENERATED"
    pre_production_baseline_locked = False
    pre_production_baseline_lock_log_exists = PRE_PRODUCTION_BASELINE_LOCK_JSON.exists()
    pre_production_baseline_lock_markdown_exists = PRE_PRODUCTION_BASELINE_LOCK_MD.exists()
    sfb10b_status = "NOT_GENERATED"

    if pre_production_baseline_lock_log_exists:
        sfb10b = _read_json(PRE_PRODUCTION_BASELINE_LOCK_JSON)
        pre_production_baseline_lock_status = str(sfb10b.get("status", "NOT_GENERATED"))
        pre_production_baseline_locked = bool(sfb10b.get("baseline_locked", False))
        sfb10b_status = pre_production_baseline_lock_status

    if pre_production_baseline_lock_status in {"PASS", "WARN", "FAIL"}:
        statuses.append(pre_production_baseline_lock_status)

    report: Dict[str, Any] = {
        "status": _overall(statuses),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "block_name": intake_policy.get("block_name", "sale_flash_block"),
        "phase": (
            "SFB-10B"
            if pre_production_baseline_lock_status in {"PASS", "WARN"}
            else (
                "SFB-10"
                if governance_boundary_review_status in {"PASS", "WARN"}
                else (
                    "SFB-9"
                    if final_signoff_archive_status in {"PASS", "WARN"}
                    else (
                        "SFB-8B"
                        if dry_run_execution_baseline_lock_status in {"PASS", "WARN"}
                        else (
                            "SFB-8"
                            if wordpress_dry_run_evidence_status in {"PASS", "WARN"}
                            else (
                                "SFB-7"
                                if final_human_approval_status in {"PASS", "WARN"}
                                else (
                                    "SFB-6"
                                    if wordpress_draft_validation_status in {"PASS", "WARN"}
                                    else (
                                        "SFB-5"
                                        if wordpress_draft_handoff_status in {"PASS", "WARN"}
                                        else ("SFB-4" if human_review_handoff_status in {"PASS", "WARN"} else ("SFB-3" if article_payload_status in {"PASS", "WARN"} else "SFB-2"))
                                    )
                                )
                            )
                        )
                    )
                )
            )
        ),
        "production_status": "NO_GO",
        "intake_mode": intake_policy.get("mode", "DRY_RUN"),
        "normalized_candidate_count": normalized.get("item_count", 0),
        "review_queue_count": queue.get("item_count", 0),
        "asin_candidate_count": queue.get("asin_candidate_count", 0),
        "search_candidate_count": queue.get("search_candidate_count", 0),
        "quality_gate_status": quality_gate.get("status", "FAIL"),
        "quality_gate_item_count": quality_gate.get("item_count", 0),
        "quality_gate_bucket_counts": quality_gate.get("bucket_counts", {}),
        "article_payload_status": article_payload_status,
        "article_payload_count": article_payload_count,
        "skipped_article_candidate_count": skipped_article_candidate_count,
        "article_payload_log_exists": article_payload_log_exists,
        "article_payload_markdown_exists": article_payload_markdown_exists,
        "top_article_payloads": top_article_payloads,
        "sfb3_status": sfb3_status,
        "human_review_handoff_status": human_review_handoff_status,
        "human_review_handoff_count": human_review_handoff_count,
        "adopt_candidate_count": adopt_candidate_count,
        "needs_fix_candidate_count": needs_fix_candidate_count,
        "excluded_candidate_count": excluded_candidate_count,
        "human_review_handoff_log_exists": human_review_handoff_log_exists,
        "human_review_handoff_markdown_exists": human_review_handoff_markdown_exists,
        "top_review_targets": top_review_targets,
        "sfb4_status": sfb4_status,
        "human_approval_consumed": human_approval_consumed,
        "final_publish_decision_allowed": final_publish_decision_allowed,
        "wordpress_draft_handoff_status": wordpress_draft_handoff_status,
        "wordpress_draft_handoff_count": wordpress_draft_handoff_count,
        "wordpress_draft_handoff_log_exists": wordpress_draft_handoff_log_exists,
        "wordpress_draft_handoff_markdown_exists": wordpress_draft_handoff_markdown_exists,
        "top_wordpress_draft_candidates": top_wordpress_draft_candidates,
        "sfb5_status": sfb5_status,
        "wordpress_draft_validation_status": wordpress_draft_validation_status,
        "wordpress_draft_validation_count": wordpress_draft_validation_count,
        "wordpress_draft_validation_log_exists": wordpress_draft_validation_log_exists,
        "wordpress_draft_validation_markdown_exists": wordpress_draft_validation_markdown_exists,
        "sfb6_status": sfb6_status,
        "final_human_gate_status": final_human_gate_status,
        "final_human_approval_status": final_human_approval_status,
        "final_human_approval_log_exists": final_human_approval_log_exists,
        "final_human_approval_markdown_exists": final_human_approval_markdown_exists,
        "wordpress_dry_run_execution_gate": wordpress_dry_run_execution_gate,
        "production_write_blocked": production_write_blocked,
        "sfb7_status": sfb7_status,
        "wordpress_dry_run_evidence_status": wordpress_dry_run_evidence_status,
        "wordpress_dry_run_evidence_count": wordpress_dry_run_evidence_count,
        "wordpress_dry_run_evidence_log_exists": wordpress_dry_run_evidence_log_exists,
        "wordpress_dry_run_evidence_markdown_exists": wordpress_dry_run_evidence_markdown_exists,
        "sfb8_status": sfb8_status,
        "dry_run_execution_baseline_lock_status": dry_run_execution_baseline_lock_status,
        "dry_run_execution_baseline_locked": dry_run_execution_baseline_locked,
        "dry_run_execution_baseline_lock_log_exists": dry_run_execution_baseline_lock_log_exists,
        "dry_run_execution_baseline_lock_markdown_exists": dry_run_execution_baseline_lock_markdown_exists,
        "sfb8b_status": sfb8b_status,
        "final_signoff_archive_status": final_signoff_archive_status,
        "final_signoff_archive_log_exists": final_signoff_archive_log_exists,
        "final_signoff_archive_markdown_exists": final_signoff_archive_markdown_exists,
        "signoff_ready": signoff_ready,
        "sfb9_status": sfb9_status,
        "governance_boundary_review_status": governance_boundary_review_status,
        "governance_boundary_review_log_exists": governance_boundary_review_log_exists,
        "governance_boundary_review_markdown_exists": governance_boundary_review_markdown_exists,
        "governance_boundary_review_ready": governance_boundary_review_ready,
        "sfb10_status": sfb10_status,
        "pre_production_baseline_lock_status": pre_production_baseline_lock_status,
        "pre_production_baseline_locked": pre_production_baseline_locked,
        "pre_production_baseline_lock_log_exists": pre_production_baseline_lock_log_exists,
        "pre_production_baseline_lock_markdown_exists": pre_production_baseline_lock_markdown_exists,
        "sfb10b_status": sfb10b_status,
        "readiness_status": readiness.get("status", "FAIL"),
        "creators_api_migration_allowed": migration_policy.get("creators_api_migration_allowed", False),
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "creators_api_called": False,
        "amazon_scraping_called": False,
        "next_recommended_phase": (
            "HOLD: SFB v1 pre-production baseline locked"
            if pre_production_baseline_lock_status in {"PASS", "WARN"}
            else (
                "STOP_POINT: SFB complete to pre-production, boundary remains closed"
                if governance_boundary_review_status in {"PASS", "WARN"}
                else (
                    "SFB-10: Governance-only production boundary review"
                    if final_signoff_archive_status in {"PASS", "WARN"}
                    else (
                        "SFB-9: Human sign-off archive (still NO_GO)"
                        if dry_run_execution_baseline_lock_status in {"PASS", "WARN"}
                        else (
                            "SFB-8B: DRY_RUN execution baseline lock (still NO_GO)"
                            if wordpress_dry_run_evidence_status in {"PASS", "WARN"}
                            else (
                                "SFB-8: Optional WordPress DRY_RUN execution evidence (still NO_GO)"
                                if final_human_approval_status in {"PASS", "WARN"}
                                else (
                                    "SFB-7: Final human approval package (still NO_GO)"
                                    if wordpress_draft_validation_status in {"PASS", "WARN"}
                                    else (
                                        "SFB-6: WordPress DRY_RUN payload validation / final human gate"
                                        if wordpress_draft_handoff_status in {"PASS", "WARN"}
                                        else (
                                            "SFB-5: Human-reviewed article candidate selection / WordPress DRY_RUN handoff"
                                            if human_review_handoff_status in {"PASS", "WARN"}
                                            else "SFB-4: Article payload quality report / human review handoff"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        ),
        "inputs": {
            "intake_policy": str(CONFIG_DIR / "intake_policy.json"),
            "source_registry": str(CONFIG_DIR / "source_registry.json"),
            "migration_policy": str(CONFIG_DIR / "migration_policy.json"),
            "normalized_sale_candidates": str(LOG_DIR / "normalized_sale_candidates.json"),
            "sale_review_queue": str(LOG_DIR / "sale_review_queue.json"),
            "sale_review_quality_gate": str(QUALITY_GATE_JSON),
            "sale_article_payloads": str(ARTICLE_PAYLOAD_JSON),
            "sale_human_review_handoff": str(HUMAN_REVIEW_HANDOFF_JSON),
            "wordpress_draft_handoff": str(WORDPRESS_DRAFT_HANDOFF_JSON),
            "wordpress_draft_payload_validation": str(WORDPRESS_DRAFT_VALIDATION_JSON),
            "final_human_approval_package": str(FINAL_HUMAN_APPROVAL_JSON),
            "wordpress_dry_run_execution_evidence": str(WORDPRESS_DRY_RUN_EVIDENCE_JSON),
            "dry_run_execution_baseline_lock_report": str(DRY_RUN_EXECUTION_BASELINE_LOCK_JSON),
            "final_signoff_archive": str(FINAL_SIGNOFF_ARCHIVE_JSON),
            "governance_boundary_review": str(GOVERNANCE_BOUNDARY_REVIEW_JSON),
            "pre_production_baseline_lock_report": str(PRE_PRODUCTION_BASELINE_LOCK_JSON),
            "sale_intake_readiness": str(LOG_DIR / "sale_intake_readiness.json"),
        },
    }

    json_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Sale Flash Block Report",
        "",
        "## Summary",
        f"- status: {report['status']}",
        f"- phase: {report['phase']}",
        f"- block_name: {report['block_name']}",
        "- production_status: NO_GO",
        f"- intake_mode: {report['intake_mode']}",
        "",
        "## Intake Policy",
        f"- require_human_review: {intake_policy.get('require_human_review', True)}",
        f"- max_items_per_run: {intake_policy.get('max_items_per_run', 0)}",
        f"- creators_api_allowed: {intake_policy.get('creators_api_allowed', False)}",
        f"- amazon_scraping_allowed: {intake_policy.get('amazon_scraping_allowed', False)}",
        "",
        "## Source Registry",
        f"- manual_csv_enabled: {source_registry.get('adapters', {}).get('manual_csv', {}).get('enabled', False)}",
        f"- creators_api_placeholder_enabled: {source_registry.get('adapters', {}).get('creators_api_placeholder', {}).get('enabled', False)}",
        "",
        "## Review Queue",
        f"- normalized_candidate_count: {report['normalized_candidate_count']}",
        f"- review_queue_count: {report['review_queue_count']}",
        f"- asin_candidate_count: {report['asin_candidate_count']}",
        f"- search_candidate_count: {report['search_candidate_count']}",
        "",
        "## Quality Gate",
        f"- quality_gate_status: {report['quality_gate_status']}",
        f"- quality_gate_item_count: {report['quality_gate_item_count']}",
        f"- ready_high_priority: {report['quality_gate_bucket_counts'].get('ready_high_priority', 0)}",
        f"- needs_asin_confirmation: {report['quality_gate_bucket_counts'].get('needs_asin_confirmation', 0)}",
        f"- needs_metadata_fix: {report['quality_gate_bucket_counts'].get('needs_metadata_fix', 0)}",
        f"- duplicate_review: {report['quality_gate_bucket_counts'].get('duplicate_review', 0)}",
        f"- blocked_or_invalid: {report['quality_gate_bucket_counts'].get('blocked_or_invalid', 0)}",
        "",
        "## Article Payloads",
        f"- article_payload_status: {report['article_payload_status']}",
        f"- article_payload_count: {report['article_payload_count']}",
        f"- skipped_article_candidate_count: {report['skipped_article_candidate_count']}",
        f"- article_payload_log_exists: {report['article_payload_log_exists']}",
        f"- article_payload_markdown_exists: {report['article_payload_markdown_exists']}",
        "",
    ]

    if top_article_payloads:
        md_lines.extend(
            [
                "| payload_id | title | review_bucket | priority_score |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in top_article_payloads:
            md_lines.append(
                "| "
                + f"{item.get('payload_id', '')} | "
                + f"{item.get('title', '')} | "
                + f"{item.get('review_bucket', '')} | "
                + f"{item.get('priority_score', 0)} |"
            )
        md_lines.append("")
    else:
        md_lines.extend(["- top_article_payloads: none", ""])

    md_lines.extend(
        [
            "## Human Review Handoff",
            f"- human_review_handoff_status: {report['human_review_handoff_status']}",
            f"- human_review_handoff_count: {report['human_review_handoff_count']}",
            f"- adopt_candidate_count: {report['adopt_candidate_count']}",
            f"- needs_fix_candidate_count: {report['needs_fix_candidate_count']}",
            f"- excluded_candidate_count: {report['excluded_candidate_count']}",
            f"- human_review_handoff_log_exists: {report['human_review_handoff_log_exists']}",
            f"- human_review_handoff_markdown_exists: {report['human_review_handoff_markdown_exists']}",
            "",
        ]
    )

    if top_review_targets:
        md_lines.extend(
            [
                "| handoff_id | title | handoff_bucket | priority_score |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in top_review_targets[:5]:
            md_lines.append(
                "| "
                + f"{item.get('handoff_id', '')} | "
                + f"{item.get('title', '')} | "
                + f"{item.get('handoff_bucket', '')} | "
                + f"{item.get('priority_score', 0)} |"
            )
        md_lines.append("")
    else:
        md_lines.extend(["- top_review_targets: none", ""])

    md_lines.extend(
        [
            "## WordPress Draft Handoff",
            f"- wordpress_draft_handoff_status: {report['wordpress_draft_handoff_status']}",
            f"- wordpress_draft_handoff_count: {report['wordpress_draft_handoff_count']}",
            f"- wordpress_draft_handoff_log_exists: {report['wordpress_draft_handoff_log_exists']}",
            f"- wordpress_draft_handoff_markdown_exists: {report['wordpress_draft_handoff_markdown_exists']}",
            "",
        ]
    )

    if top_wordpress_draft_candidates:
        md_lines.extend(
            [
                "| draft_handoff_id | title | priority_score | post_title |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in top_wordpress_draft_candidates:
            md_lines.append(
                "| "
                + f"{item.get('draft_handoff_id', '')} | "
                + f"{item.get('title', '')} | "
                + f"{item.get('priority_score', 0)} | "
                + f"{item.get('post_title', '')} |"
            )
        md_lines.append("")
    else:
        md_lines.extend(["- top_wordpress_draft_candidates: none", ""])

    md_lines.extend(
        [
            "## WordPress Draft Payload Validation",
            f"- wordpress_draft_validation_status: {report['wordpress_draft_validation_status']}",
            f"- wordpress_draft_validation_count: {report['wordpress_draft_validation_count']}",
            f"- wordpress_draft_validation_log_exists: {report['wordpress_draft_validation_log_exists']}",
            f"- wordpress_draft_validation_markdown_exists: {report['wordpress_draft_validation_markdown_exists']}",
            f"- final_human_gate_status: {report['final_human_gate_status']}",
            "",
        ]
    )

    md_lines.extend(
        [
            "## Final Human Approval Package",
            f"- final_human_approval_status: {report['final_human_approval_status']}",
            f"- final_human_approval_log_exists: {report['final_human_approval_log_exists']}",
            f"- final_human_approval_markdown_exists: {report['final_human_approval_markdown_exists']}",
            f"- wordpress_dry_run_execution_gate: {report['wordpress_dry_run_execution_gate']}",
            f"- production_write_blocked: {report['production_write_blocked']}",
            "",
        ]
    )

    md_lines.extend(
        [
            "## WordPress DRY_RUN Execution Evidence",
            f"- wordpress_dry_run_evidence_status: {report['wordpress_dry_run_evidence_status']}",
            f"- wordpress_dry_run_evidence_count: {report['wordpress_dry_run_evidence_count']}",
            f"- wordpress_dry_run_evidence_log_exists: {report['wordpress_dry_run_evidence_log_exists']}",
            f"- wordpress_dry_run_evidence_markdown_exists: {report['wordpress_dry_run_evidence_markdown_exists']}",
            "",
        ]
    )

    md_lines.extend(
        [
            "## DRY_RUN Execution Baseline Lock",
            f"- dry_run_execution_baseline_lock_status: {report['dry_run_execution_baseline_lock_status']}",
            f"- dry_run_execution_baseline_locked: {report['dry_run_execution_baseline_locked']}",
            f"- dry_run_execution_baseline_lock_log_exists: {report['dry_run_execution_baseline_lock_log_exists']}",
            f"- dry_run_execution_baseline_lock_markdown_exists: {report['dry_run_execution_baseline_lock_markdown_exists']}",
            "",
        ]
    )

    md_lines.extend(
        [
            "## Final Sign-off Archive",
            f"- final_signoff_archive_status: {report['final_signoff_archive_status']}",
            f"- final_signoff_archive_log_exists: {report['final_signoff_archive_log_exists']}",
            f"- final_signoff_archive_markdown_exists: {report['final_signoff_archive_markdown_exists']}",
            f"- signoff_ready: {report['signoff_ready']}",
            "",
        ]
    )

    md_lines.extend(
        [
            "## Governance Boundary Review",
            f"- governance_boundary_review_status: {report['governance_boundary_review_status']}",
            f"- governance_boundary_review_log_exists: {report['governance_boundary_review_log_exists']}",
            f"- governance_boundary_review_markdown_exists: {report['governance_boundary_review_markdown_exists']}",
            f"- governance_boundary_review_ready: {report['governance_boundary_review_ready']}",
            "",
        ]
    )

    md_lines.extend(
        [
            "## Pre-Production Baseline Lock",
            f"- pre_production_baseline_lock_status: {report['pre_production_baseline_lock_status']}",
            f"- pre_production_baseline_locked: {report['pre_production_baseline_locked']}",
            f"- pre_production_baseline_lock_log_exists: {report['pre_production_baseline_lock_log_exists']}",
            f"- pre_production_baseline_lock_markdown_exists: {report['pre_production_baseline_lock_markdown_exists']}",
            "",
        ]
    )

    md_lines.extend([
        "## Migration Plan",
        f"- current_stage: {migration_policy.get('current_stage', 'unknown')}",
        f"- creators_api_migration_allowed: {report['creators_api_migration_allowed']}",
        "",
        "## Safety Gates",
        f"- readiness_status: {report['readiness_status']}",
        f"- external_api_called: {report['external_api_called']}",
        f"- external_network_called: {report['external_network_called']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- creators_api_called: {report['creators_api_called']}",
        f"- amazon_scraping_called: {report['amazon_scraping_called']}",
        "",
        "## SFB-3 Safety Gates",
        f"- sfb3_status: {report['sfb3_status']}",
        f"- article_payload_status: {report['article_payload_status']}",
        "",
        "## SFB-4 Safety Gates",
        f"- sfb4_status: {report['sfb4_status']}",
        f"- human_approval_consumed: {report['human_approval_consumed']}",
        f"- final_publish_decision_allowed: {report['final_publish_decision_allowed']}",
        "",
        "## SFB-5 Safety Gates",
        f"- sfb5_status: {report['sfb5_status']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- publish_executed: false",
        "",
        "## SFB-6 Safety Gates",
        f"- sfb6_status: {report['sfb6_status']}",
        f"- human_approval_consumed: {report['human_approval_consumed']}",
        f"- final_publish_decision_allowed: {report['final_publish_decision_allowed']}",
        "",
        "## SFB-7 Safety Gates",
        f"- sfb7_status: {report['sfb7_status']}",
        f"- wordpress_dry_run_execution_gate: {report['wordpress_dry_run_execution_gate']}",
        f"- production_write_blocked: {report['production_write_blocked']}",
        "",
        "## SFB-8 Safety Gates",
        f"- sfb8_status: {report['sfb8_status']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- production_status: {report['production_status']}",
        "",
        "## SFB-8B Safety Gates",
        f"- sfb8b_status: {report['sfb8b_status']}",
        f"- dry_run_execution_baseline_locked: {report['dry_run_execution_baseline_locked']}",
        f"- production_status: {report['production_status']}",
        "",
        "## SFB-9 Safety Gates",
        f"- sfb9_status: {report['sfb9_status']}",
        f"- signoff_ready: {report['signoff_ready']}",
        f"- production_status: {report['production_status']}",
        "",
        "## SFB-10 Safety Gates",
        f"- sfb10_status: {report['sfb10_status']}",
        f"- governance_boundary_review_ready: {report['governance_boundary_review_ready']}",
        f"- production_status: {report['production_status']}",
        "",
        "## SFB-10B Safety Gates",
        f"- sfb10b_status: {report['sfb10b_status']}",
        f"- pre_production_baseline_locked: {report['pre_production_baseline_locked']}",
        f"- production_status: {report['production_status']}",
        "",
        "## Next Phase",
        f"- next_recommended_phase: {report['next_recommended_phase']}",
    ])
    md_report.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report


def main() -> int:
    report = generate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
