# PR WARN Backfill Phase 1Y：valid_until Reaction Handler Policy / design-only

## 作成/更新ファイル
- policy: config/pr_warn_backfill_valid_until_reaction_handler_policy.json
- validator: scripts/validate_pr_warn_backfill_valid_until_reaction_handler_policy.py
- tests: tests/test_validate_pr_warn_backfill_valid_until_reaction_handler_policy.py
- report: reports/pr_warn_backfill_phase1y_valid_until_reaction_handler_policy.md
- result: exchange/logs/pr_warn_backfill_phase1y_valid_until_reaction_handler_policy_result.json

## 目的
valid_until が期限切れ・期限接近した場合に、単純ABORTだけでなく、反応先通知・ビジー時 read-only 再審査・rerun snapshot 作成候補・active approval参照更新候補へ安全に退避する設計を固定する。

## 仕様
- soft_expiry_threshold_minutes: 10
- reaction_timeout_minutes: 2
- busy_fallback_enabled: true
- busy_fallback_action: READ_ONLY_REVALIDATION
- auto_resnapshot_allowed: true
- auto_active_approval_refresh_allowed: true
- wordpress_get_allowed_only_during_revalidation: true
- wordpress_post_put_patch_delete_allowed: false
- wordpress_write_allowed: false
- approved_true_allowed: false
- live_execution_allowed: false

## 安全制約
- approved=true: 禁止
- wordpress_live_write_allowed=true: 禁止
- created_for_execution=true: 禁止
- WordPress write: 禁止
- LIVE実行: 禁止
- POST/PUT/PATCH/DELETE: 禁止
- secret表示: 禁止
- snapshot本文表示: 禁止
- payload本文表示: 禁止

## 状態遷移
- VALID: 残り時間が soft threshold 以上
- SOFT_EXPIRING: 残り時間が threshold 未満
- REACTION_PENDING: 通知済み・応答待ち
- REACTION_BUSY: 応答先ビジー
- HARD_EXPIRED: valid_until 超過
- REVALIDATING: read-only再審査
- RESNAPSHOT_READY: 再審査PASS
- REVALIDATION_ABORT: 再審査NG

## 実行結果
- status: PASS_DESIGN_ONLY_NO_EXECUTION
- WordPress API呼び出し: false
- WordPress read: false
- WordPress write: false
- LIVE実行: false
- approved=true作成: false
- active approval変更: false
- template変更: false
- snapshot変更: false
- payload変更: false
- reaction monitor作成: false
- notification sender作成: false
- auto revalidation runner作成: false

## 次フェーズ
- 通常時: Phase 1S-FINAL-APPROVAL-TRUE-PREP-RERUN3
- 現時点でvalid_until切れの場合: Phase 1N-RERUN
