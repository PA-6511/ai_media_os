# PR WARN Backfill Phase 1O：final approval 実ファイル作成 / approved=false / no write / no update

## 実施範囲
- final live approval の実ファイルを active approval draft として作成
- approved=false を維持
- wordpress_live_write_allowed=false を維持
- reports-only / no write / no update で停止

## 参照確認
- template: exchange/examples/pr_warn_backfill_phase1m_final_live_approval.template.json
- pre-live snapshot: exchange/logs/pr_warn_backfill_phase1n_101_pre_live_resnapshot.json
- pre-live result: exchange/logs/pr_warn_backfill_phase1n_101_pre_live_resnapshot_result.json
- rollback snapshot: exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json
- payload preview: exchange/logs/pr_warn_backfill_phase1l_101_live_write_preparation_dry_run.json
- Phase 1N-FIX report: reports/pr_warn_backfill_phase1n_fix_pre_live_resnapshot_state.md

## 作成物
- active approval draft: exchange/human_review/pr_warn_backfill_phase1o_101_final_live_approval.active.json
- result log: exchange/logs/pr_warn_backfill_phase1o_101_final_approval_draft_result.json

## 確認結果
- target_post_id: 101
- title: 呪術廻戦は何巻まで出てる？最新巻・関連情報まとめ
- approved: false
- wordpress_live_write_allowed: false
- created_for_execution: false
- approval_state: CREATED_NOT_APPROVED
- max_live_updates: 1
- allowed_changed_fields: ["content"]
- modified/content_hash一致: 維持
- pre_live_snapshot_valid_minutes: 30
- pre_live_snapshot_valid_until: 2026-06-20T05:02:18.605125+00:00
- pre_live_snapshot_expired_at_creation: true
- require_resnapshot_if_expired: true
- resnapshot_required_before_live: true
- WordPress read: 未実行
- WordPress write: 未実行
- LIVE実行: 未実行
- update_count: 0
- approved=true実承認ファイル: 未作成
- template変更: なし
- snapshot本文表示: なし
- payload本文表示: なし

## active approval draft と template/example の違い
- template/example は雛形であり、実行対象の個別案件を拘束しない。
- 今回の active approval draft は post_id=101 専用で、参照すべき snapshot / rollback / payload preview のパスを固定している。
- ただし active であっても approved=false のため、実行許可ではない。
- wordpress_live_write_allowed=false のため、LIVE更新には使用できない。

## 期限切れ境界条件
- valid_until は作成時点で超過している。
- このため、LIVE前に Phase 1N-RERUN を必須とする。
- Phase 1N-RERUN 完了までは、この承認ドラフトを approved=true 化してはならない。
- 再取得後も modified/content_hash/status/payload_changed_fields の条件を再確認し、不一致なら abort とする。

## 状態固定
- Phase 1O は approval draft 作成のみでPASS。
- active approval draft は後続承認の土台だが、まだ実承認ではない。
- no write / no update / no live を維持。
- 次フェーズは Phase 1N-RERUN、その後に Phase 1O-FIX を想定する。

## 禁止事項の継続
- WordPress API の GET/POST/PUT/PATCH/DELETE は実行しない。
- 下書き更新、publish、本文変更送信、approved=true化、template true化、commit、push は行わない。