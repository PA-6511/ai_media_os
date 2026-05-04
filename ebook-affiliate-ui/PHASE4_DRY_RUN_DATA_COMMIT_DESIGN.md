# 電子書籍アフィリエイト UI Flags Phase4.45 DRY_RUNデータ追加コミット設計

## 目的

本ドキュメントは、Phase4.46で実施する `campaign_items.json` のみの変更を安全に行うため、
変更対象・手順・検証観点・停止条件を固定する。

## 安全条件（固定）

- 自動投稿・自動削除・自動公開は行わない
- WordPress本番更新・本番反映は行わない
- Git commit / Git push は本フェーズでは行わない
- 本物URLは投入しない
- BLOCKED 状態を維持する

## スコープ

対象ファイル:
- `ebook-affiliate-ui/data/campaign_items.json` のみ

対象外（このフェーズで変更しない）:
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `ebook-affiliate-ui` 配下のJS
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`

## 変更方針

- 各アイテムに `affiliate_url` キーを追加する
- 値は DRY_RUN 用の `https://example.invalid/...` を使用する
- 既存互換のため `campaign_url` は維持する
- `affiliate_url` に本番URL・実運用URLは入れない

## データ形式ルール

- `affiliate_url` は文字列型で保持する
- 空文字、`#`、null は使用しない
- `item_id` とURLの対応関係を崩さない
- URLは一意である必要はないが、意図しない重複は避ける

## DRY_RUN用URL規約

- 許可形式: `https://example.invalid/<slug>`
- `<slug>` は半角英数字・ハイフンのみを推奨
- クエリ文字列は不要
- 本物ドメイン（rakuten/amazon等）は使用禁止

## 実施手順（設計）

1. `campaign_items.json` の全itemを確認する
2. `affiliate_url` 未設定itemに `https://example.invalid/<slug>` を追加する
3. 既存キー順・インデントを崩さない
4. JSON構文エラーがないことを確認する
5. 変更ファイルが `campaign_items.json` のみであることを確認する

## 受け入れ条件（Phase4.46着手前）

- 変更対象が `campaign_items.json` のみ
- すべての対象itemに `affiliate_url` が存在
- `affiliate_url` は全件 `example.invalid` ドメイン
- 本番URLは 0 件
- commit/push/本番反映が 0 件

## BLOCKED維持の確認観点

- `example.invalid` は許可ドメイン対象外のため、最終判定は BLOCKED 維持
- 本フェーズでは `href="#"` 件数の改善を行わない
- 本フェーズでは検証スクリプト拡張を行わない

## ロールバック方針

- Phase4.46以降で問題が出た場合は、データ追加コミット単位でrevertできる構成を維持する
- UI変更・スクリプト変更と同一コミットに混在させない

## 次フェーズ接続

- Phase4.46: `campaign_items.json` 変更（実作業）
- Phase4.47: データ差分レビュー
- Phase4.48: データ単独コミット
- Phase4.49: push前レビュー
- Phase4.50: push
- Phase4.51: remote再取得確認
