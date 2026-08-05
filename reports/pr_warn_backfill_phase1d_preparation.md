# PR WARN Backfill Phase 1D Preparation (DRY_RUN_ONLY)

## Scope
- Phase 1D introduces a dedicated runner for post_id=101 only.
- This phase does not execute LIVE updates.
- Existing Phase 1 runner remains unchanged as a safety-stop path.

## Decision
- Adopt Option B from Phase 1C.
- Keep [scripts/pr_warn_backfill_phase1_runner.py](scripts/pr_warn_backfill_phase1_runner.py) as BLOCKED/safety-only.
- Add a new Phase 1D runner that validates constraints and emits payload preview only.

## Phase 1D Minimal Deliverables
- [scripts/pr_warn_backfill_phase1d_live_single_runner.py](scripts/pr_warn_backfill_phase1d_live_single_runner.py)
- [tests/test_pr_warn_backfill_phase1d_live_single_runner.py](tests/test_pr_warn_backfill_phase1d_live_single_runner.py)
- DRY_RUN log output path: [exchange/logs/pr_warn_backfill_phase1d_101_dry_run.json](exchange/logs/pr_warn_backfill_phase1d_101_dry_run.json)

## Safety Invariants
- post_id must be 101.
- approved must be true.
- wordpress_write_allowed must be true.
- max_live_updates must be 1.
- diff_preview must represent PR notice insertion after h1 only.
- proposed_changed_fields is restricted to content.
- forbidden field changes include title/url/cta/featured_image/status/category/tag.
- wordpress_write_executed remains false.
- live_mode_supported remains false.

## Next Phase Entry Criteria (Phase 1E)
- Phase 1D runner compiles and passes tests.
- Dry-run artifact is generated with PASS_DRY_RUN_ONLY.
- Human review confirms no expansion of write capability.
- Preflight checklist for rollback and post-live verification is approved.
