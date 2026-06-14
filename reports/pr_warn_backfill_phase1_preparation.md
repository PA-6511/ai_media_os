# PR WARN Backfill Phase 1 Preparation

## Status
- Phase: PREPARATION_ONLY
- WordPress write: NOT_EXECUTED
- Human approval gate: REQUIRED
- Batch update: FORBIDDEN

## Goal
- Prepare a safe single-item backfill path after Phase 0.
- Keep execution default to DRY_RUN.
- Block live update unless approval file passes strict checks.

## Added Artifacts
- `scripts/pr_warn_backfill_phase1_runner.py`
- `exchange/examples/pr_warn_backfill_phase1_human_approval.example.json`

## Runner Safety Rules
1. Default mode is `DRY_RUN`.
2. Target must exist in `reports/pr_warn_backfill_phase0_dry_run_20260614.json`.
3. Target must satisfy `classification=existing_draft_backfill` and `dry_run_would_change=true`.
4. `LIVE` mode requires approval file.
5. Approval checks:
- `approved=true`
- `approval_token=APPROVED_PR_WARN_BACKFILL_PHASE1`
- `approved_post_id` must match `--post-id`
- `max_live_updates=1`
- `wordpress_write_allowed=true`
6. This preparation runner intentionally does not execute WordPress write even in `LIVE` mode.

## Dry-run Command Example
```bash
cd /home/deploy/ai_media_os
python3 scripts/pr_warn_backfill_phase1_runner.py --post-id 101 --mode DRY_RUN
```

## Live-precheck Command Example (still blocked)
```bash
cd /home/deploy/ai_media_os
python3 scripts/pr_warn_backfill_phase1_runner.py \
  --post-id 101 \
  --mode LIVE \
  --approval exchange/human_review/pr_warn_backfill_phase1_approval.json
```

## Out of Scope (Not Executed)
- WordPress draft update
- Multi-item backfill
- Checker logic changes
- Generator logic changes
- URL WARN phase migration
- Semi-automatic publish
