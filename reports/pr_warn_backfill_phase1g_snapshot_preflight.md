# PR WARN Backfill Phase 1G-PREFLIGHT: Existing Post Fetch / Snapshot Planning (DRY_RUN)

## Scope
- Design and dry-run confirmation only.
- No WordPress update.
- No publish.
- No POST/PUT/PATCH/DELETE.
- Read-only GET is not executed in this phase.

## Inputs Confirmed
- Approval: [exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json](exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json)
- Phase1F DRY_RUN: [exchange/logs/pr_warn_backfill_phase1f_live_route_101_dry_run.json](exchange/logs/pr_warn_backfill_phase1f_live_route_101_dry_run.json)
- Phase0 source: [reports/pr_warn_backfill_phase0_dry_run_20260614.json](reports/pr_warn_backfill_phase0_dry_run_20260614.json)
- Env preflight: [reports/pr_warn_backfill_phase1e_env_preflight.md](reports/pr_warn_backfill_phase1e_env_preflight.md)
- Route freeze: [reports/pr_warn_backfill_phase1f_live_route_fix_state.md](reports/pr_warn_backfill_phase1f_live_route_fix_state.md)

## Read-only GET Design (next phase candidate)
- Candidate client function: [wordpress_publisher/wp_client.py](wordpress_publisher/wp_client.py) `get_post(post_id)`
- Endpoint pattern for read-only snapshot retrieval:
  - /wp-json/wp/v2/posts/{post_id}?context=edit
- Allowed operation for snapshot phase:
  - GET only
- Forbidden operations for snapshot phase:
  - POST, PUT, PATCH, DELETE, publish

## Snapshot Schema (fixed)
- phase
- mode
- status
- target_post_id
- snapshot_required_before_live
- snapshot_allowed_operation = GET_ONLY
- snapshot_forbidden_operations = [POST, PUT, PATCH, DELETE, publish]
- snapshot_fields:
  - post_id
  - title
  - content
  - status
  - link
  - modified
  - slug
  - categories
  - tags
  - featured_media
- content_hash
- title_hash
- snapshot_storage_path proposal:
  - exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json

## Diff/Verification Plan
- Compare payload_preview and snapshot content before any live enable phase.
- Allowed change candidate:
  - PR notice insertion after h1 in content only.
- Immutable checks:
  - title, url, cta, featured_image, status, category, tag unchanged.

## Rollback Basis (snapshot-first)
- rollback_source: snapshot.content
- rollback_required_if:
  - content corruption
  - PR notice inserted at wrong location
  - any non-content change
  - API abnormal response
  - post_id mismatch

## Decision
- Phase 1G-PREFLIGHT: PASS
- DRY_RUN_ONLY: maintained
- next_required_phase: Phase 1G-READONLY-SNAPSHOT
