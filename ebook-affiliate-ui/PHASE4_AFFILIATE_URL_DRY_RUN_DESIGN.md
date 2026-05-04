# 電子書籍アフィリエイト UI Flags Phase4.27 実アフィリエイトURL投入 DRY_RUN 設計

## 目的

本ドキュメントは、実アフィリエイトURL投入前の設計ルールを固定する。
本フェーズは DRY_RUN のみとし、本番反映は行わない。

## 安全前提

- Git commit / Git push はこの設計確定フェーズでは必須ではない
- WordPress 本番更新は実施しない
- 本番反映判定は引き続き BLOCKED を維持する
- `check_affiliate_links.py` は本番反映前に必須実行とする

## 正式キー方針

- 正式キー: `affiliate_url`
- 互換キー: `campaign_url`（移行期間のみ許容）
- 参照優先順位: `affiliate_url` -> `campaign_url`
- 将来方針: 全件 `affiliate_url` へ統一し、`campaign_url` は廃止予定

## URL投入前データ形式

`ebook-affiliate-ui/data/campaign_items.json` の各 item に対し、以下を満たすこと。

- `item_id`: 必須、空文字不可
- `affiliate_url`: 原則必須（移行期間は `campaign_url` でも可）
- URL値は文字列であること（null / 数値 / 配列 / オブジェクトは不可）
- 前後空白は除去して保存すること
- `#`、空文字、null は未設定として扱う

## URL未設定時のBLOCK条件

以下のいずれか 1 件でも検出した場合は BLOCK。

- HTML で `href="#"` が残存
- JSON の `affiliate_url` / `campaign_url` が未設定（空文字、null、`#`）
- URL形式チェック不合格
- 許可ドメイン不一致

## URL形式チェック

- `https://` で始まること（http は不可）
- URL構文として妥当であること
- クエリやパラメータの有無は許可
- 短縮URLは原則不可（遷移先ドメイン判定不能のため）

## ストア別URL許可ドメイン

最低限、以下ドメインのみ許可する。

- Kobo: `books.rakuten.co.jp`
- Rakuten affiliate redirect: `hb.afl.rakuten.co.jp`
- Amazon: `www.amazon.co.jp`
- Amazon associate redirect: `amzn.to`（一時許可。可能なら最終遷移先で再評価）

運用ルール:
- 許可外ドメインは BLOCK
- 新規ドメイン追加時は本ドキュメント更新を必須化

## テスト用ダミーURLの扱い

- `example.com`、`test.local`、`dummy` などのテストURLは本番候補データで禁止
- DRY_RUN 中のみ、一時サンプルを使う場合は明示フラグを付ける
- サンプル混入を検出した時点で BLOCK

## 本番反映前の必須チェック手順

1. `cd /home/deploy/ai_media_os/ebook-affiliate-ui`
2. `python3 scripts/check_affiliate_links.py`
3. 結果確認

PASS 条件:
- `html href=# count : 0`
- `json invalid count: 0`
- 許可ドメイン一致
- 終了コード 0

FAIL/BLOCK 条件:
- 上記 PASS 条件を 1 つでも満たさない
- `RESULT: BLOCK` 出力
- 終了コード 1

## Phase4.27 完了条件（設計フェーズ）

- 正式キー方針を文書化済み
- URL未設定時BLOCK条件を文書化済み
- URL形式チェックと許可ドメインを文書化済み
- ダミーURL禁止ルールを文書化済み
- 本番前必須チェック手順と PASS 基準を文書化済み

## 次フェーズ入力

次フェーズ（実アフィリエイトURL投入 DRY_RUN 実施）では、以下を実施する。

- `campaign_items.json` へ実URLを投入（DRY_RUN）
- `check_affiliate_links.py` 実行
- BLOCK解除条件（href=# 0件 / json invalid 0件 / 許可ドメイン一致）を確認
- ただし本番反映は別フェーズで判断する
