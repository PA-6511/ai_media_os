# PR WARN Backfill Phase 1O-REFRESH：active approval draft の snapshot参照更新 / rerun valid_until反映 / approved=false維持 / no write

## 実施範囲
- active approval draft の snapshot/result 参照を Phase 1N-RERUN 証跡へ更新
- rerun valid_until を active approval draft に反映
- approved=false / wordpress_live_write_allowed=false / created_for_execution=false を維持
- WordPress read/write/LIVE は実行しない

## 更新対象
- active approval: exchange/human_review/pr_warn_backfill_phase1o_101_final_live_approval.active.json
- refresh result: exchange/logs/pr_warn_backfill_phase1o_refresh_101_active_approval_result.json

## 確認結果
- target_post_id: 101
- required_pre_live_snapshot_path: exchange/logs/pr_warn_backfill_phase1n_rerun_101_pre_live_resnapshot.json
- required_pre_live_snapshot_result_path: exchange/logs/pr_warn_backfill_phase1n_rerun_101_pre_live_resnapshot_result.json
- pre_live_snapshot_valid_until: 2026-06-20T13:37:13.269677+00:00
- pre_live_snapshot_expired_at_refresh: false
- resnapshot_required_before_live: false
- approval_state: REFRESHED_NOT_APPROVED
- approved: false
- wordpress_live_write_allowed: false
- created_for_execution: false
- max_live_updates: 1
- allowed_changed_fields: ["content"]
- modified_matches: true
- content_hash_matches: true
- status_draft: true
- payload_content_only: true
- WordPress read: 未実行
- WordPress write: 未実行
- LIVE実行: 未実行
- update_count: 0
- approved=true化: 未実行
- template変更: なし
- snapshot本文表示: していない
- payload本文表示: していない
- secret値表示: していない

## 状態固定
- Phase 1O-REFRESH: PASS_ACTIVE_APPROVAL_REFRESHED_NO_WRITE
- active approval: rerun snapshot/result 参照へ更新済み
- approved=false: 維持
- no update: 維持
- valid_until期限内/期限切れ: 期限内
- 次フェーズ: Phase 1O-REFRESH-FIX

## 境界条件
- active approval draft は更新したが、実行許可にはしていない。
- approved=false / wordpress_live_write_allowed=false / created_for_execution=false のため、LIVE更新材料ではない。
- 次フェーズでは refresh 結果の固定のみを行い、approved=true 化はまだ行わない。

## 判定
- Phase 1O-REFRESH: PASS
- active approval refresh: 完了
- 安全停止: no write / no update で完了
- 次へ進めるか: Phase 1O-REFRESH-FIX へ進行可
- 次に必要な人間判断: Phase 1O-REFRESH-FIX で refresh 後状態を正式固定するかの判断