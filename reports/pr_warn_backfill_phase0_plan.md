# PR WARN Backfill Phase 0 Plan

- Status: DESIGN_AND_DRY_RUN_ONLY
- WordPress write: NOT_EXECUTED
- Human approval required: YES

## Scope
- Target date sample: 2026-06-14
- Target rule: classification=existing_draft_backfill AND wp_content_has_pr=no
- Target count: 6

## Fixed Non-Execution Rules
- Do not execute backfill update to WordPress drafts
- Do not change checker logic
- Do not change generator logic
- Do not move to URL WARN phase in this step

## Procedure (Phase 0)
1. Count targets from reclassification artifact
2. Generate dry-run HTML candidate with PR notice insertion
3. Review diff preview for each target
4. Request human approval
5. Limit first live execution to one post
6. Re-run draft_check and verify PR WARN reduction

## Dry-run Summary
- Dry-run candidates with change: 6
- Dry-run candidates without change: 0
- Artifact JSON: reports/pr_warn_backfill_phase0_dry_run_20260614.json
