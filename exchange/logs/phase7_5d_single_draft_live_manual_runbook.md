# Phase 7-5D 1件限定 WordPress実下書き作成 手動実行ランブック

生成日時: 2026-05-05T06:06:51.386382+00:00

## 状態

- runbook_status: READY_FOR_MANUAL_DECISION
- live_execution_allowed: False
- production_status: NO_GO
- wordpress_draft_creation: NO_GO
- wordpress_write_executed: False

## 手動実行手順（固定10項目）

1. 誰が実行するか: 未入力（実行担当者を人間で記入）
2. 実行時刻: 未入力（ISO8601で記録）
3. 実行前に確認するファイル:
- exchange/logs/phase7_5_freeze_or_live_decision_report.json
- exchange/logs/phase7_5b_live_final_approval_result.json
- exchange/outgoing/wordpress_draft_create_payload.dry_run.json
- scripts/run_phase7_5c_single_draft_create_live_manual.py
4. 実行コマンド: python3 scripts/run_phase7_5c_single_draft_create_live_manual.py --execute-live --wordpress-base-url <WP_BASE_URL> --wp-username <WP_USERNAME> --wp-app-password <WP_APP_PASSWORD>
- 注意: 実行は手動のみ。自動実行・cron・GitHub Actionsは禁止。
5. 実行直後に確認する WordPress 管理画面項目:
- 新規下書きが1件のみ作成されている
- 投稿ステータスが draft のまま
- 公開されていない
- タイトルと本文が payload と一致
6. 下書きIDの保存方法: exchange/logs/phase7_5c_single_draft_create_live_result.json の created_post_id を確認し、運用記録へ転記
7. 失敗時の停止条件:
- HTTP status が 201 以外
- レスポンスに post id がない
- status が draft 以外
- 想定外の複数投稿が確認された
8. 再ロック確認: phase7_5c result の relocked_after_execution が true であること
9. 手動削除手順:
- WordPress管理画面で対象下書きを開く
- 対象IDを再確認
- 手動でゴミ箱へ移動
- 必要なら完全削除
- 実施結果を証跡ログに記録
10. 実行後レポート保存先:
- exchange/logs/phase7_5c_single_draft_create_live_result.json
- exchange/logs/phase7_5d_single_draft_live_manual_runbook_generation_result.json

## まだ禁止される操作

- cron_registration
- github_actions_trigger
- slack_production_notification
- multiple_post_create
- publish_post
- update_existing_post
- delete_post_by_automation
- external_export
- vps_execution
- env_secret_auto_edit

next_step: manual_go_or_freeze_decision
