# SFB v1 Trial Operation Checklist (SFB-1 to SFB-10B)

## 1. 基本情報

- run_id:
- operator:
- reviewer:
- target_csv:
- checked_at_utc:

## 2. SFB-1〜SFB-10B

- [ ] SFB-1 事前状態確認（HOLD固定 / NO_GO）
- [ ] SFB-2 CSV必須列確認
- [ ] SFB-3 重複キー確認
- [ ] SFB-4 URL・価格・日付フォーマット確認
- [ ] SFB-5 fixtureバックアップ確認
- [ ] SFB-6 差分比較レポート事前確認
- [ ] SFB-7 validate手順確認
- [ ] SFB-8 import手順（運用固定）確認
- [ ] SFB-9 rollback手順確認
- [ ] SFB-10A 次工程進行条件確認
- [ ] SFB-10B 停止条件・NO_GO維持確認

## 3. CSV投入前チェック

- [ ] ヘッダー誤記なし
- [ ] 必須列欠落なし
- [ ] 空値チェック完了
- [ ] 禁止列なし
- [ ] 文字コードUTF-8

## 4. NGデータ確認

- [ ] 空 `item_id` なし
- [ ] 不正URLなし
- [ ] 負数価格なし
- [ ] 重複 `item_id` なし
- [ ] 不正日時なし

## 5. NO_GO維持

- [ ] `production_status = NO_GO`
- [ ] `execution_allowed = false`
- [ ] `wordpress_write_executed = false`
- [ ] `approval_token_consumed = false`

## 6. 進行判定

- [ ] 次へ進めてよい条件を全て満たす
- [ ] 止める条件に該当しない

最終判定:

- [ ] PROCEED_RULES_LOCK
- [ ] STOP_AND_FIX

備考:
