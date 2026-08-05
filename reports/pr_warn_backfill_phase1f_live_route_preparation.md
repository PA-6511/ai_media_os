# PR WARN Backfill Phase 1F-LIVE-ROUTE Preparation (DRY_RUN_FIRST)

## Purpose
- Address the Phase 1F stop reason: ABORT_LIVE_ROUTE_NOT_AVAILABLE.
- Build the execution-route scaffold for post_id=101 while keeping write capability disabled.
- Keep this phase as DRY_RUN_FIRST only.

## Scope
- Target is fixed to post_id=101 only.
- max_live_updates is fixed to 1.
- Approval file must be true-gated.
- Phase0 diff must match PR insertion-only pattern.
- WordPress API write is disabled in this phase.

## Deliverables
- [scripts/pr_warn_backfill_phase1f_live_route_runner.py](scripts/pr_warn_backfill_phase1f_live_route_runner.py)
- [tests/test_pr_warn_backfill_phase1f_live_route_runner.py](tests/test_pr_warn_backfill_phase1f_live_route_runner.py)
- DRY_RUN log path: [exchange/logs/pr_warn_backfill_phase1f_live_route_101_dry_run.json](exchange/logs/pr_warn_backfill_phase1f_live_route_101_dry_run.json)
- LIVE request in this phase aborts to: [exchange/logs/pr_warn_backfill_phase1f_live_route_101_live_abort.json](exchange/logs/pr_warn_backfill_phase1f_live_route_101_live_abort.json)

## Safety Constraints
- Allowed changed field: content only.
- Forbidden changed fields: title, url, cta, featured_image, status, category, tag, publish.
- Single-item only, no bulk path.
- update_count is always 0 in this phase.
- wordpress_write_executed is always false in this phase.

## Plans Captured In DRY_RUN
- snapshot_plan
- rollback_plan
- post_live_verification_plan

## Next Phase Requirement
- Live enablement must be handled in a separate phase with explicit human approval.
- No direct migration from this phase to immediate write without the live-enable gate.
