# PR WARN Backfill Phase 1N-RERUN：pre-live再snapshot 再取得 / read-only GET / no write / no update

## スコープ
- pre-live snapshot 再取得フェーズ
- WordPress REST API GET のみ実行
- post_id=101 のみ対象
- active approval draft は更新しない
- approved=true 化しない
- wordpress_live_write_allowed=true 化しない
- no write / no update / no live で停止

## 確認対象
- runner: scripts/pr_warn_backfill_phase1n_pre_live_resnapshot.py
- active approval draft: exchange/human_review/pr_warn_backfill_phase1o_101_final_live_approval.active.json
- rerun snapshot: exchange/logs/pr_warn_backfill_phase1n_rerun_101_pre_live_resnapshot.json
- rerun result: exchange/logs/pr_warn_backfill_phase1n_rerun_101_pre_live_resnapshot_result.json
- rollback snapshot: exchange/logs/pr_warn_backfill_phase1g_101_pre_live_snapshot.json
- rollback snapshot result: exchange/logs/pr_warn_backfill_phase1g_101_readonly_snapshot_result.json
- payload preview: exchange/logs/pr_warn_backfill_phase1l_101_live_write_preparation_dry_run.json

## 実行結果
- py_compile: PASS
- pytest: PASS
- READ_ONLY_GET: 実行済み
- rerun snapshot保存: 完了
- rerun result保存: 完了

## 確認結果
- target_post_id: 101
- fetched_post_id: 101
- status: draft
- modified: 2026-05-01T14:14:24
- rollback_modified: 2026-05-01T14:14:24
- modified_matches: true
- content_length: 1177
- content_hash: 記録済み
- rollback_content_hash: 一致
- content_hash_matches: true
- valid_minutes: 30
- valid_until: 2026-06-20T13:37:13.269677+00:00
- valid_until_already_expired: false
- WordPress read: 実行済み（GETのみ）
- WordPress write: 未実行
- LIVE実行: 未実行
- update_count: 0
- active approval approved: false
- active approval wordpress_live_write_allowed: false
- snapshot本文表示: していない
- payload本文表示: していない
- secret値表示: していない

## 判定整理
- runner の result status は PASS_PRE_LIVE_RESNAPSHOT のまま出力されている。
- 本フェーズではこの結果を Phase 1N-RERUN の再取得成功として扱う。
- modified / content_hash / status=draft の全条件は維持されている。
- 新しい valid_until は作成時点で未失効のため、次フェーズは Phase 1O-REFRESH に進行可能。

## 安全確認
- GET: 実行
- POST: 未実行
- PUT: 未実行
- PATCH: 未実行
- DELETE: 未実行
- WordPress更新: 未実行
- LIVE実行: 未実行
- active approval更新: 未実行
- approved=true化: 未実行
- template変更: 未実行

## 境界条件
- active approval draft は旧 valid_until を参照したままであり、このPhaseでは更新していない。
- 次の Phase 1O-REFRESH で rerun snapshot / rerun result を参照するように整理する。
- その後も approved=false / wordpress_live_write_allowed=false を維持したまま状態固定する。

## 判定
- Phase 1N-RERUN: PASS
- pre-live再snapshot再取得: PASS
- read-only GET: PASS
- no write: PASS
- 安全停止: PASS
- Phase 1O-REFRESHへ進めるか: 可
- 次に必要な人間判断: Phase 1O-REFRESH で active approval draft の参照先と valid_until を新 rerun 証跡へ更新するかの判断