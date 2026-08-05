# PR WARN Backfill Phase 1R-VALID-UNTIL-RECHECK：1R着手前 valid_until再判定 / no write / no update

## 位置づけ
- 本Phaseは Phase 1R-FINAL-APPROVAL-HANDOFF 本体ではなく、着手前の期限再判定専用フェーズ
- ローカル証跡の再評価のみ実施
- WordPress read/write/LIVE は実行しない

## 判定結果
- status: ABORT_VALID_UNTIL_EXPIRED_RESNAPSHOT_REQUIRED_NO_WRITE
- target_post_id: 101
- active approval state: REFRESHED_NOT_APPROVED
- approved: false
- wordpress_live_write_allowed: false
- created_for_execution: false
- final_approval_created: false
- final_approval_true_created: false
- pre_live_snapshot_valid_until: 2026-06-20T13:37:13.269677+00:00
- valid_until_checked_at: 2026-06-20T13:40:52.136117+00:00
- valid_until_already_expired_now: true
- valid_until_state: EXPIRED_AT_RECHECK
- final_approval_handoff_allowed_candidate: false
- live_execution_allowed: false
- next_required_phase: Phase 1N-RERUN

## 整合確認
- max_live_updates: 1
- allowed_changed_fields: ["content"]
- modified_matches: true
- content_hash_matches: true
- status_draft: true
- payload_content_only: true

## 安全制約確認
- WordPress read: 未実行
- WordPress write: 未実行
- LIVE実行: 未実行
- update_count: 0
- approved=true化: 未実行
- active approval変更: なし
- template変更: なし
- snapshot変更: なし
- snapshot本文表示: していない
- payload本文表示: していない
- secret値表示: していない

## 状態固定
- Phase 1R-VALID-UNTIL-RECHECK: ABORT_VALID_UNTIL_EXPIRED_RESNAPSHOT_REQUIRED_NO_WRITE
- valid_until判定: 期限切れ
- approved=false: 維持
- final approval: true未作成を維持
- no update: 維持
- 次フェーズ: Phase 1N-RERUN

## 補足
- 今回の pre-live snapshot は有効期限切れのため、Phase 1R-FINAL-APPROVAL-HANDOFF へは進めない。
- 先に Phase 1N-RERUN を再実施し、新しい valid_until を取得したうえで再判定する。