# 電子書籍アフィリエイト UI Flags Phase4.63 HTML/JS CTA反映 実装手順書

## 目的

本ドキュメントは、次フェーズで実施する CTA反映実装を安全に行うため、
変更対象・実装手順・検証手順・停止条件を事前に固定する。

## 安全条件（固定）

- 自動投稿・自動削除・自動公開は行わない
- WordPress本番更新・本番反映は行わない
- Git commit / Git push は本フェーズでは行わない
- BLOCKED 状態を維持する
- 本物URLは投入しない

## 実装対象（固定）

- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html` のみ

## 非対象（変更禁止）

- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- すべての `PHASE4_*.md`
- `core/decision_package_reader.py`

## 実装ゴール

- HTML内の固定 `href="#"` を除去する
- `data-item-id` をキーに CTAリンクを反映する処理を HTML内JSで実装する
- URL未設定時に CTA を安全に無効化する
- `example.invalid` 利用中は BLOCKED を維持する

## 事前確認手順

1. `git status --short` で開始状態を確認する
2. `href="#"` の現在件数を確認する
3. 対象外ファイルが未変更であることを確認する

## 実装手順（次フェーズ実行用）

1. `kobo-campaign-list-final-v3.html` の CTA要素を特定する
2. 固定 `href="#"` を削除し、`data-item-id` を付与・維持する
3. HTML内JSで itemごとに URL解決処理を実装する
4. URL解決優先順位を適用する
   - `affiliate_url` 優先
   - 次に `campaign_url`
   - どちらも無効なら未設定
5. 有効URL時のみ `href` を設定する
6. 未設定時は CTA を無効化する
   - `aria-disabled="true"`
   - disabledクラス付与
   - click時 `preventDefault()`
   - 文言「準備中」

## URL判定ルール

- 有効: `https://` で始まり、`#` ではなく、空文字でない
- 無効: 空文字 / `#` / URL形式不正
- DRY_RUN中は `example.invalid` を許容し、本番反映は行わない

## 検証手順（次フェーズ実行用）

1. `git diff -- ebook-affiliate-ui/kobo-campaign-list-final-v3.html` で差分確認
2. 変更対象がHTML 1ファイルのみであることを確認
3. `href="#"` 残件数を再計測
4. Consoleエラーが増えていないことを確認（ローカル確認）
5. CTA未設定時に遷移しないことを確認
6. BLOCKED 状態維持前提を確認

## 受け入れ条件

- 変更ファイルが `kobo-campaign-list-final-v3.html` のみ
- `href="#"` が対象CTAで除去されている
- `affiliate_url` / `campaign_url` の優先順位処理が実装されている
- 未設定CTAの無効化が実装されている
- 非対象ファイルが未変更
- commit / push / 本番反映が未実行

## ロールバック方針

- 問題発生時は HTML/JS反映コミットのみを単独で revert する
- `campaign_items.json` はロールバック対象外とする
- `check_affiliate_links.py` はロールバック対象外とする
- 本番反映前のため Git revert または対象ファイル復元で戻せる
- ロールバック後も BLOCKED 維持を確認する

## 次フェーズ接続

- Phase4.64: 本手順書レビュー
- Phase4.65: 手順書単独コミット
- Phase4.66: push前レビュー
- Phase4.67: push
- Phase4.68: remote再取得確認

その後、HTML/JS実装フェーズを単独コミットで実施する。
