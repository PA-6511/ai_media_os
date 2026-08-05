# PR WARN Backfill Phase 1O-REFRESH：rerun2 snapshot参照更新 / no write / no update

- status: PASS_ACTIVE_APPROVAL_REFRESHED_RERUN2_NO_WRITE
- target_post_id: 101
- approval_state: REFRESHED_NOT_APPROVED
- required_pre_live_snapshot_path: exchange/logs/pr_warn_backfill_phase1n_rerun2_101_pre_live_resnapshot.json
- required_pre_live_snapshot_result_path: exchange/logs/pr_warn_backfill_phase1n_rerun2_101_pre_live_resnapshot_result.json
- pre_live_snapshot_valid_until: 2026-06-20T14:17:29.981489+00:00
- valid_until_checked_at: 2026-06-20T13:52:03.913662+00:00
- pre_live_snapshot_expired_at_refresh: false
- resnapshot_required_before_live: false
- approved: false
- wordpress_live_write_allowed: false
- created_for_execution: false
- max_live_updates: 1
- allowed_changed_fields: ["content"]
- WordPress read: false
- WordPress write: false
- LIVE execution: false
- update_count: 0
- approved_true_created: false
- template_modified: false
- snapshot_modified: false
- snapshot_body_displayed: false
- payload_body_displayed: false
- secrets_displayed: false
- next_required_phase: Phase 1O-REFRESH-FIX

## 固定
- active approval の参照先を rerun2 snapshot/result へ更新
- approved=false 維持
- wordpress_live_write_allowed=false 維持
- created_for_execution=false 維持
- WordPress更新なし
- LIVE実行なし