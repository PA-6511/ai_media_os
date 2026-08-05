# Phase 8-37: 初回1件試験稼働 Runbook 最終版

## 1. 目的

このRunbookは ai_media_os における初回1件試験稼働の手順を固定する。
実際の試験稼働は、別途明示的な人間GOが発行されるまで絶対に実行しない。

## 2. 現在の固定状態

- Phase 8-35: BLOCKED_CREDENTIALS_MISSING
- Phase 8-29〜8-31: CREDENTIALS_NOT_READY
- Phase 8-36: BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION
- production_status: NO_GO
- execution: DRY_RUN
- ready_for_first_trial_execution: false

## 3. 実行前提

以下がすべて満たされた場合のみ、初回1件試験稼働の実行を検討する。

- `/etc/ai-media-os/credential.env` が存在し、必須キーが non-empty であること
- Phase 8-29〜8-31 status が CREDENTIALS_READY に更新されていること
- Phase 8-35 status が READY_FOR_DRY_RUN_HANDOFF に更新されていること
- Phase 8-36 handoff_status が READY であること
- Phase 8-38 preflight status が READY であること
- Phase 8-39 simulation が PASS であること
- 人間の明示的 GO が発行されていること
- one-shot lock が取得済みであること（実行直前に人間が取得）

## 4. 絶対禁止事項

- WordPress API POST / PUT / PATCH / DELETE の呼び出し
- WordPress 実下書き作成
- WordPress 本番投稿・更新・削除
- Slack 実送信
- GitHub push / merge
- systemctl restart / reboot / shutdown
- rollback / freeze の実行（シミュレーション以外）
- secret 値・長さ・マスク・ハッシュの出力
- env / printenv による資格情報の表示
- ログ・例外メッセージへの secret 混入

## 5. Credential Ready 確認

実行前に以下を確認する（値は出力しない）。

```bash
# ファイル存在確認のみ
test -f /etc/ai-media-os/credential.env && echo "EXISTS" || echo "MISSING"

# キー存在確認のみ（値を出力しない）
set -a
. /etc/ai-media-os/credential.env
set +a
python3 -c "
import os
keys = ['WORDPRESS_BASE_URL', 'WORDPRESS_USERNAME', 'WORDPRESS_APP_PASSWORD']
for k in keys:
    v = os.environ.get(k, '')
    print(k, 'present=', bool(v), 'non_empty=', len(v) > 0)
"
```

## 6. Phase 8-36 handoff 確認

```bash
python3 -c "
import json; from pathlib import Path
p = Path('exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_result.json')
if p.exists():
    d = json.loads(p.read_text())
    print('status:', d.get('status'))
    print('handoff_allowed:', d.get('handoff_allowed'))
else:
    print('MISSING')
"
```

## 7. 初回1件対象の選定条件

- target_item_count = 1（固定）
- 対象はセール情報として Sheets に登録済みであること
- duplicate_check が PASS であること
- affiliate_disclosure が存在すること
- pr_label が存在すること
- CTA ポリシーチェックが PASS であること
- カテゴリ・タグポリシーチェックが PASS であること

## 8. 人間承認条件

- 人間が明示的に "GO" を発行すること
- 自動 GO は禁止
- 承認日時・承認者・承認理由を evidence ログに記録すること

## 9. one-shot lock 条件

- lock ファイル: `exchange/locks/one_shot_trial_execution.lock`
- 実行直前に人間が作成する
- 実行後に人間が削除する
- lock が存在しない場合は実行禁止
- lock が存在する状態で二重実行を検知した場合は即 ABORT

## 10. 実行直前 preflight

```bash
python3 scripts/validate_phase8_38_first_one_item_trial_preflight.py
```

status が PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_READY_NO_EXECUTION 以外なら実行禁止。

## 11. 実行中監視項目

- WordPress API レスポンスコード（2xx/4xx は正常、5xx は ABORT）
- 投稿 ID の確認（下書き作成後に ID を記録）
- duplicate 投稿の有無
- one-shot lock の状態
- execution 時間（5分超過で WARN、10分超過で ABORT）

## 12. 実行後 evidence

実行後に以下を出力する。

- post_id（WordPress 下書き ID）
- post_status（draft のみ許容）
- created_at
- wordpress_api_response_code
- affiliate_disclosure_present
- pr_label_present
- cta_policy_checked
- category_tag_policy_checked
- one_shot_lock_released_at
- execution_duration_seconds

## 13. WordPress 側確認項目

- 下書き記事が1件のみ存在すること
- status が draft であること
- 本番公開されていないこと
- 重複記事がないこと

## 14. Slack 通知方針

- 実行中はSlack送信禁止（DRY_RUN フェーズ）
- 試験稼働が成功した場合のみ、別途GOが出た後に送信
- 送信内容に secret を含めないこと

## 15. rollback 条件

以下の場合に rollback を実施する（人間の手動操作）。

- 下書き記事に重大な誤りが発見された場合
- affiliate_disclosure が欠落していた場合
- CTA ポリシー違反が発見された場合
- 本番公開が誤って実行された場合

rollback 手順:

1. WordPress 管理画面で当該記事を削除
2. one-shot lock を削除
3. rollback evidence を exchange/logs に記録
4. Phase 8-39 ABORT シナリオに従い報告

## 16. freeze 条件

以下の場合に全処理を freeze する。

- secret 値が出力された場合
- WordPress API が予期しない書き込みを実行した場合
- one-shot lock が不正に操作された場合
- システム異常が検知された場合

freeze 手順:

1. 処理を即停止
2. evidence を保存
3. freeze report を exchange/logs に記録
4. 人間に報告

## 17. ABORT 条件

以下のいずれかが発生した場合は即 ABORT。

- wordpress_write_executed = true
- secret_values_output = true
- execution_allowed = true（意図せず）
- 5xx エラーが連続3回以上
- duplicate 投稿が検知された場合
- one-shot lock が存在しない状態で実行が開始された場合

## 18. PASS 条件

- 下書き1件が正常に作成された
- post_status = draft
- affiliate_disclosure_present = true
- pr_label_present = true
- cta_policy_checked = true
- category_tag_policy_checked = true
- duplicate_check_passed = true
- secret_output_safe = true
- one_shot_lock_released = true

## 19. WARN 条件

- WordPress API レスポンスが 4xx（認証除く）
- execution_duration_seconds > 300
- ログに想定外のキーが含まれる

## 20. FAIL 条件

- WordPress API が 5xx を返した
- post_status が draft 以外
- duplicate 投稿が検知された
- affiliate_disclosure_present = false
- pr_label_present = false

## 21. 再実行禁止条件

以下の場合は再実行禁止。

- PASS 後（同一対象への二重実行防止）
- ABORT が発生した場合（原因究明・人間承認後に限り再実行可）
- one-shot lock が削除されていない場合

## 22. secret 非露出ルール

- 資格情報の値を一切出力しない
- 資格情報の長さを出力しない
- 資格情報のマスク表現を出力しない
- 資格情報のハッシュを出力しない
- ログに secret キーワードを含む値を書かない
- 例外メッセージに認証情報を含めない
- env / printenv 実行後は直ちに変数を unset する

## 23. 最終報告フォーマット

```json
{
  "phase": "8-36_to_8_40_first_trial",
  "production_status": "NO_GO",
  "execution": "DRY_RUN",
  "trial_status": "PASS | FAIL | ABORT | WARN",
  "post_id": null,
  "post_status": "draft",
  "wordpress_write_executed": false,
  "wordpress_draft_created": false,
  "wordpress_api_call_attempted": false,
  "affiliate_disclosure_present": true,
  "pr_label_present": true,
  "cta_policy_checked": true,
  "category_tag_policy_checked": true,
  "duplicate_check_passed": true,
  "one_shot_lock_acquired": true,
  "one_shot_lock_released": true,
  "secret_output_safe": true,
  "executed_external_changes": 0,
  "rollback_executed": false,
  "freeze_executed": false,
  "execution_duration_seconds": null,
  "blocked_reasons": [],
  "warn_list": [],
  "fail_list": [],
  "next_step": "NEXT_STEP_REQUEST_EXPLICIT_HUMAN_GO_FOR_FIRST_ONE_ITEM_TRIAL"
}
```
