# SFB-12: Real-Data CSV Import Runbook (Rules Lock)

## 1. 目的

このRunbookは、SFBがHOLD固定中でも安全に実施できる「実データCSV運用ルール固定」と「投入手順固定」を定義する。
本Runbookは運用整備専用であり、本番write解放は対象外とする。

## 2. 固定前提

- SFBはHOLD固定済み
- production_status は常に NO_GO を維持する
- WordPress本番write実行は禁止
- approval token の新規消費は禁止
- 実データCSVは validate/import の手順固定までに限定する

## 3. CSV投入前チェック

1. 対象CSVファイルが UTF-8 で保存されている
2. ヘッダー行が1行目にあり、必須列が欠落していない
3. 同一キー重複（例: `item_id`）がない
4. 価格・日付・URLの形式が規約に一致している
5. 入力責任者とレビュー担当者が分離されている
6. バックアップfixtureが作成済み
7. NO_GO維持を再確認している

## 4. CSV列ルール

必須列（最低限）:

- `item_id` (string, non-empty, unique)
- `title` (string, non-empty)
- `source_url` (string, URL形式)
- `price` (integer, 0以上)
- `currency` (string, `JPY`固定)
- `in_stock` (boolean: `true`/`false`)
- `fetched_at_utc` (ISO8601 UTC)
- `campaign_label` (string, non-empty)

任意列:

- `author`
- `publisher`
- `memo`

禁止ルール:

- 未定義列の混入
- 同義語列（例: `itemId` と `item_id` の併用）
- 先頭/末尾空白付き値
- 通貨不整合（JPY以外）

## 5. NGデータ例

- `item_id` が空
- `source_url` が `http://` 以外の不正文字列
- `price` が負数・小数・文字列
- `fetched_at_utc` がローカル時刻形式
- 同一 `item_id` の重複行
- ヘッダー名のタイポ（例: `campain_label`）

## 6. validate実行手順

```bash
python3 scripts/check_real_data_csv_operating_readiness.py --dry-run
```

期待:

- `status` が `SFB12_REAL_DATA_CSV_OPERATING_RULES_LOCKED_READY`
- `production_status` が `NO_GO`
- `execution_allowed` が `false`

## 7. import実行手順（運用固定のみ）

本フェーズでは「手順定義」のみを行い、実本番writeは行わない。

1. バックアップ確認（fixture snapshotの存在確認）
2. dry-run importのコマンド定義確認
3. 差分比較レポート出力先確認
4. rollback手順確認

## 8. backup確認

- import前に現在fixtureをスナップショット保存
- スナップショット識別子を記録（時刻・担当者）
- 保存先の読み取りテストを実施

## 9. SFB-1〜SFB-10B 再実行手順（必要時）

1. SFB-1 事前状態確認
2. SFB-2 CSVスキーマ再検証
3. SFB-3 重複キー検査
4. SFB-4 URL/価格フォーマット検査
5. SFB-5 fixtureバックアップ点検
6. SFB-6 差分レポート事前出力
7. SFB-7 NO_GO維持確認
8. SFB-8 rollback導線確認
9. SFB-9 手動チェックリスト再確認
10. SFB-10A trial gate確認
11. SFB-10B final hold確認

## 10. NO_GO維持確認

以下を常に満たすこと:

- `production_status = NO_GO`
- `execution_allowed = false`
- `wordpress_write_executed = false`
- `approval_token_consumed = false`

## 11. rollback手順

1. 直前バックアップIDを特定
2. 対象fixtureをバックアップ時点へ復元
3. 差分がゼロに戻ることを確認
4. rollback記録をログへ残す
5. NO_GO維持を再確認

## 12. 次へ進めてよい条件

- 全必須列ルールを満たす
- NG例に該当しない
- validateが成功
- 差分レポートがレビュー済み
- rollbackリハーサルが成功
- チェックリストが全項目完了

## 13. 止める条件

- 必須列欠落
- 重複キーあり
- 型不整合
- NO_GO維持条件の逸脱
- rollback不可能
- レビュー未完了

## 14. 最終記録フォーマット

- run_id
- checked_at
- operator
- reviewer
- csv_file
- validation_status
- no_go_status
- next_action (`PROCEED_RULES_LOCK` / `STOP_AND_FIX`)
