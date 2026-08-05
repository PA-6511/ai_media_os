# PR WARN Backfill Phase 1I: LIVE Enable Design / DRY_RUN_WITH_WRITE_DISABLED

## Scope
- Design and gate definition only.
- No WordPress API write.
- No LIVE send.
- No content update.
- No runner behavior change in existing scripts.

## Fixed Inputs
- approved file: exchange/human_review/pr_warn_backfill_phase1_101_human_approval.approved.json
- snapshot: exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json
- snapshot result: exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json
- phase1f dry-run: exchange/logs/pr_warn_backfill_phase1f_live_route_101_dry_run.json
- phase1h report: reports/pr_warn_backfill_phase1h_live_enable_preflight.md

## Design Decisions (Phase 1I Fixed)
1. Keep existing safety-stop runners unchanged:
   - scripts/pr_warn_backfill_phase1_runner.py
   - scripts/pr_warn_backfill_phase1d_live_single_runner.py
   - scripts/pr_warn_backfill_phase1f_live_route_runner.py
2. Introduce live write in a separate dedicated runner in next phase only.
3. Update payload scope remains content-only.
4. Forbidden fields remain unchanged:
   - title
   - status
   - slug
   - link
   - categories
   - tags
   - featured_media
   - publish
   - excerpt
   - author
   - date

## Pre-LIVE Re-snapshot Policy (Required)
- A fresh read-only snapshot is mandatory immediately before any live write attempt.
- Abort if fetched_post_id is not 101.
- Abort if current modified differs from baseline snapshot policy target.
- Abort if content_hash validation fails against designated baseline rule.
- Abort if snapshot result is not PASS_READONLY_SNAPSHOT.

## Snapshot Expiry and Drift Policy
- Final live approval expires after next run.
- Pre-live resnapshot is required every live attempt.
- Any modified drift or hash drift triggers abort and forces re-approval.

## Final Live Approval Format
- Defined as example file:
  exchange/examples/pr_warn_backfill_phase1i_final_live_approval.example.json
- This file is template/example only in Phase 1I.
- Actual live approval file must be separately created and signed off by human in next phase.

## Rollback Preconditions
- Rollback snapshot path must exist and be readable.
- Snapshot must correspond to post_id=101 and draft status baseline.
- Rollback plan must be present before any live write activation.
- If rollback source integrity cannot be proven, abort live.

## Post-LIVE Verification Plan (for next phase execution)
- updated_post_id must be 101.
- update_count must be exactly 1.
- status remains draft.
- title/link/slug/categories/tags/featured_media remain unchanged.
- PR marker exists in content and is placed immediately after h1.
- draft check is re-run.
- PR WARN resolution for target post is verified.
- Any anomaly routes to rollback decision path.

## Phase 1I Outcome
- PASS_LIVE_ENABLE_DESIGN_DRY_RUN_ONLY
- No WordPress read/write execution performed by this phase output generation.
- Ready for next phase decision (Phase 1J or Phase 1I-FIX).
