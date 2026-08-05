# PR WARN Backfill Phase 1M: Final Approval and Pre-Live Resnapshot Policy (reports-only)

## Scope
- reports-only policy fixation
- no WordPress API connection
- no WordPress write/update
- no live execution
- no active final approval creation

## Baseline Verified
- Phase 1L status: PASS_LIVE_WRITE_PREPARATION_DRY_RUN_ONLY
- Phase 1L mode: DRY_RUN_WITH_WRITE_BLOCKED
- payload_changed_fields: ["content"]
- final live approval example: example-only, approved=false, wordpress_live_write_allowed=false
- existing snapshot baseline: post_id=101, status=draft, modified/content_hash/content_length present

## Final Live Approval Real-File Specification
- Real final approval file must be distinct from example/template files.
- Real file creation is not performed in Phase 1M.
- Required storage path policy:
  - exchange/human_review/pr_warn_backfill_phase1n_101_final_live_approval.real.json
- Naming policy:
  - include phase candidate, post_id=101, and real marker.
- Required fields:
  - approved=true only at explicit human sign-off phase
  - wordpress_live_write_allowed=true only at explicit human sign-off phase
  - target_post_id=101
  - max_live_updates=1
  - allowed_changed_fields=["content"]
  - forbidden_changed_fields fixed set
  - required_pre_live_snapshot_path
  - required_pre_live_snapshot_result_path
  - required_rollback_snapshot_path
  - required_payload_preview_path
  - require_pre_live_resnapshot=true
  - pre_live_snapshot_valid_minutes=30
  - require_modified_unchanged_or_abort=true
  - require_content_hash_match_or_abort=true
  - require_status_draft_or_abort=true
  - require_payload_content_only_or_abort=true
  - require_human_final_confirmation=true
  - approval_scope=post_id_101_single_update_only
  - approval_expires_after_next_run=true
  - approval_must_not_be_reused=true

## Example and Real Separation Rule
- example/template files are non-executable policy artifacts only.
- example/template files must stay approved=false and wordpress_live_write_allowed=false.
- real approval file must not be replaced by example/template path.

## Pre-Live Resnapshot Operation Policy
- Resnapshot is mandatory before any live-enable attempt.
- Required timing: immediately before live gate execution.
- Validity window: 30 minutes from pre-live snapshot timestamp.
- If validity window expires, execution must abort and resnapshot is required.

## Abort Rules for Drift and Integrity
- Abort if post_id mismatch (expected 101).
- Abort if status is not draft.
- Abort if modified differs between resnapshot and policy-required baseline comparison target.
- Abort if content_hash differs from expected comparison rule at gate time.
- Abort if payload scope is not content-only.
- Abort if forbidden fields are present in payload.
- Abort if final approval is missing/expired/reused.

## Snapshot Handling Policy
- Snapshot body content is sensitive operation data.
- Do not print full snapshot content in routine reports.
- Do not externally share full snapshot content.
- Use hash/length/metadata for verification in reports.

## Ordered Procedure for Phase 1N+
1. Generate pre-live resnapshot and result artifact.
2. Validate resnapshot freshness (<=30 minutes).
3. Validate modified/content_hash/status/post_id gates.
4. Generate real final approval file in designated human review path (not in Phase 1M).
5. Require human final confirmation and one-time approval token semantics.
6. Proceed only after all gate checks pass.

## Result
- Phase 1M policy fixation: PASS
- reports-only: maintained
- no update/no live: maintained
