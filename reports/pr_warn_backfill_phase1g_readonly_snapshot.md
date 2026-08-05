# PR WARN Backfill Phase 1G-READONLY-SNAPSHOT

## Scope
- Execute read-only GET for post_id=101 only.
- Save pre-live snapshot for rollback basis.
- Do not execute any write operation.

## Allowed and Forbidden Operations
- Allowed:
  - GET /wp-json/wp/v2/posts/101?context=edit
- Forbidden:
  - POST, PUT, PATCH, DELETE, publish

## Safety Requirements
- post_id must be 101.
- mode must be READ_ONLY_GET.
- approval must be true-gated.
- wordpress_write_allowed must be true.
- max_live_updates must be 1.
- Required env keys must be present (values never printed).
- Snapshot must be stored successfully before moving to live-enable consideration.

## Generated Artifacts
- snapshot: [exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json](exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json)
- result log: [exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json](exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json)

## Next Phase Candidate
- Phase 1H or live-enable preflight after snapshot/payload diff confirmation.
