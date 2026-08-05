# PR WARN Backfill Phase 1N-RERUN2：pre-live snapshot 再取得 / read-only GET / no write / no update

- status: PASS_PRE_LIVE_RESNAPSHOT_RERUN2
- target_post_id: 101
- fetched_post_id: 101
- status_from_wp: draft
- modified_matches_rollback_snapshot: true
- content_hash_matches_rollback_snapshot: true
- content_length: 1177
- valid_minutes: 30
- fetched_at: 2026-06-20T13:47:29.981489+00:00
- valid_until: 2026-06-20T14:17:29.981489+00:00
- wordpress_read_executed: true (GET)
- wordpress_write_executed: false
- post_put_patch_delete_executed: false
- live_execution_executed: false
- update_count: 0
- active_approval_modified: false
- approved_true_created: false
- template_modified: false
- snapshot_body_displayed: false
- payload_body_displayed: false
- secrets_displayed: false
- next_required_phase: Phase 1O-REFRESH

## 固定
- read-only GET のみ実施
- active approval は未変更
- template は未変更
- snapshot本文contentは表示していない
- payload本文は表示していない
- secret値は表示していない
