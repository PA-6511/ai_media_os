# Sale Flash Block Report

## Summary
- status: PASS
- phase: SFB-10B
- block_name: sale_flash_block
- production_status: NO_GO
- intake_mode: DRY_RUN

## Intake Policy
- require_human_review: True
- max_items_per_run: 50
- creators_api_allowed: False
- amazon_scraping_allowed: False

## Source Registry
- manual_csv_enabled: True
- creators_api_placeholder_enabled: False

## Review Queue
- normalized_candidate_count: 2
- review_queue_count: 2
- asin_candidate_count: 1
- search_candidate_count: 1

## Quality Gate
- quality_gate_status: PASS
- quality_gate_item_count: 2
- ready_high_priority: 1
- needs_asin_confirmation: 1
- needs_metadata_fix: 0
- duplicate_review: 0
- blocked_or_invalid: 0

## Article Payloads
- article_payload_status: PASS
- article_payload_count: 2
- skipped_article_candidate_count: 0
- article_payload_log_exists: True
- article_payload_markdown_exists: True

| payload_id | title | review_bucket | priority_score |
| --- | --- | --- | --- |
| sfb3-payload-001 | Crimson Library | ready_high_priority | 94 |
| sfb3-payload-002 | Glass Moon | needs_asin_confirmation | 59 |

## Human Review Handoff
- human_review_handoff_status: PASS
- human_review_handoff_count: 2
- adopt_candidate_count: 1
- needs_fix_candidate_count: 1
- excluded_candidate_count: 0
- human_review_handoff_log_exists: True
- human_review_handoff_markdown_exists: True

| handoff_id | title | handoff_bucket | priority_score |
| --- | --- | --- | --- |
| sfb4-handoff-001 | Crimson Library | adopt_candidate | 94 |
| sfb4-handoff-002 | Glass Moon | needs_fix_candidate | 59 |

## WordPress Draft Handoff
- wordpress_draft_handoff_status: PASS
- wordpress_draft_handoff_count: 1
- wordpress_draft_handoff_log_exists: True
- wordpress_draft_handoff_markdown_exists: True

| draft_handoff_id | title | priority_score | post_title |
| --- | --- | --- | --- |
| sfb5-draft-001 | Crimson Library | 94 | 【SUMMER_FLASH】Crimson Library をチェック |

## WordPress Draft Payload Validation
- wordpress_draft_validation_status: PASS
- wordpress_draft_validation_count: 1
- wordpress_draft_validation_log_exists: True
- wordpress_draft_validation_markdown_exists: True
- final_human_gate_status: READY_FOR_FINAL_HUMAN_GATE

## Final Human Approval Package
- final_human_approval_status: PASS
- final_human_approval_log_exists: True
- final_human_approval_markdown_exists: True
- wordpress_dry_run_execution_gate: READY_FOR_DRY_RUN_ONLY
- production_write_blocked: True

## WordPress DRY_RUN Execution Evidence
- wordpress_dry_run_evidence_status: PASS
- wordpress_dry_run_evidence_count: 1
- wordpress_dry_run_evidence_log_exists: True
- wordpress_dry_run_evidence_markdown_exists: True

## DRY_RUN Execution Baseline Lock
- dry_run_execution_baseline_lock_status: PASS
- dry_run_execution_baseline_locked: True
- dry_run_execution_baseline_lock_log_exists: True
- dry_run_execution_baseline_lock_markdown_exists: True

## Final Sign-off Archive
- final_signoff_archive_status: PASS
- final_signoff_archive_log_exists: True
- final_signoff_archive_markdown_exists: True
- signoff_ready: True

## Governance Boundary Review
- governance_boundary_review_status: PASS
- governance_boundary_review_log_exists: True
- governance_boundary_review_markdown_exists: True
- governance_boundary_review_ready: True

## Pre-Production Baseline Lock
- pre_production_baseline_lock_status: PASS
- pre_production_baseline_locked: True
- pre_production_baseline_lock_log_exists: True
- pre_production_baseline_lock_markdown_exists: True

## Migration Plan
- current_stage: API_NOT_ELIGIBLE_MANUAL_INTAKE
- creators_api_migration_allowed: False

## Safety Gates
- readiness_status: PASS
- external_api_called: False
- external_network_called: False
- wordpress_write_executed: False
- creators_api_called: False
- amazon_scraping_called: False

## SFB-3 Safety Gates
- sfb3_status: PASS
- article_payload_status: PASS

## SFB-4 Safety Gates
- sfb4_status: PASS
- human_approval_consumed: False
- final_publish_decision_allowed: False

## SFB-5 Safety Gates
- sfb5_status: PASS
- wordpress_write_executed: False
- publish_executed: false

## SFB-6 Safety Gates
- sfb6_status: PASS
- human_approval_consumed: False
- final_publish_decision_allowed: False

## SFB-7 Safety Gates
- sfb7_status: PASS
- wordpress_dry_run_execution_gate: READY_FOR_DRY_RUN_ONLY
- production_write_blocked: True

## SFB-8 Safety Gates
- sfb8_status: PASS
- wordpress_write_executed: False
- production_status: NO_GO

## SFB-8B Safety Gates
- sfb8b_status: PASS
- dry_run_execution_baseline_locked: True
- production_status: NO_GO

## SFB-9 Safety Gates
- sfb9_status: PASS
- signoff_ready: True
- production_status: NO_GO

## SFB-10 Safety Gates
- sfb10_status: PASS
- governance_boundary_review_ready: True
- production_status: NO_GO

## SFB-10B Safety Gates
- sfb10b_status: PASS
- pre_production_baseline_locked: True
- production_status: NO_GO

## Next Phase
- next_recommended_phase: HOLD: SFB v1 pre-production baseline locked
