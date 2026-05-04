# 電子書籍アフィリエイト UI Flags Phase4.57 HTML/JS CTA反映設計

## 目的

本ドキュメントは、CTAリンク反映に関する実装方針を先に固定し、
次フェーズの実装を HTML/JS のみに分離するための設計基準を定義する。

## 安全条件（固定）

- 自動投稿・自動削除・自動公開は行わない
- WordPress本番更新・本番反映は行わない
- Git commit / Git push は本フェーズでは行わない
- `campaign_items.json` は変更しない
- `check_affiliate_links.py` は変更しない
- BLOCKED 状態を維持する

## スコープ

設計対象:
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `ebook-affiliate-ui` 配下のJS（CTAリンク反映ロジック）

対象外:
- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- 本番環境の公開設定・配信設定

## 設計方針 1: HTML の href="#" 除去

方針:
- 静的HTML内の CTA アンカーに固定 `href="#"` を残さない
- 代わりに `data-item-id` を必須キーとして保持する

実装設計:
1. 既存 CTA 要素を特定する
2. 固定 `href="#"` を削除する
3. 初期状態は遷移先未設定として扱う
4. JS 初期化後に有効URLのみ `href` を設定する

期待効果:
- 静的断面で `href="#"` 依存を解消できる
- URL未解決時の制御をJS側へ集約できる

## 設計方針 2: JS で affiliate_url を CTA へ反映

URL解決優先順位:
1. `affiliate_url`
2. `campaign_url`
3. 両方無効なら未設定扱い

反映フロー:
1. `data-item-id` で対象 item を特定
2. URLを trim して正規化
3. 有効URLなら CTA の `href` へ反映
4. 無効URLなら CTA を無効化

有効URL判定:
- `https://` で始まる
- `#` ではない
- 空文字ではない

## 設計方針 3: affiliate_url 未設定時 CTA 無効化

無効化条件:
- `affiliate_url` と `campaign_url` の両方が空
- 値が `#`
- URL形式が不正

無効化仕様:
- `aria-disabled="true"` を付与
- disabled用クラスを付与
- click 時に `preventDefault()`
- 表示文言は「準備中」に統一

## BLOCKED維持方針

- DRY_RUN 値 `example.invalid` は本番投入不可
- `check_affiliate_links.py` は本フェーズで未変更のため判定強化は次段階
- 本フェーズ完了時点では本番反映判定を BLOCKED のまま維持する

## 非変更保証（このフェーズ）

- `campaign_items.json` は変更しない
- `check_affiliate_links.py` は変更しない
- 本物URLは投入しない
- WordPress本番反映は行わない

## ロールバック方針

本フェーズのHTML/JS CTA反映は、データ追加とは別コミットで実施する。
そのため、問題発生時は HTML/JS反映コミットのみを単独で revert する。

ロールバック対象:
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `ebook-affiliate-ui` 配下のJS（CTA反映ロジック）

ロールバック対象外:
- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- すべての `PHASE4_*.md`

ロールバック条件:
- CTAリンク反映後に表示崩れが発生した場合
- affiliate_url 未設定時の無効化表示が崩れた場合
- `example.invalid` のまま外部遷移が許可される場合
- Consoleエラーが発生した場合
- 本番反映前チェックで BLOCK 条件を正しく維持できない場合

ロールバック後の確認:
- HTML/JSのCTAが安全な状態に戻っていること
- 本番反映が未実施であること
- BLOCKED 状態が維持されていること
- `campaign_items.json` の DRY_RUN affiliate_url が維持されていること
- `check_affiliate_links.py` が未変更のままであること

本番反映前のため、ロールバックは Git revert または対象ファイル復元で実施可能とする。

## 受け入れ条件（設計レビュー観点）

- `href="#"` 除去方針が明記されている
- JS反映の優先順位が明記されている
- 未設定時無効化仕様が明記されている
- `example.invalid` と BLOCKED維持方針が明記されている
- 非変更対象（JSON/検証スクリプト）が明記されている

## 次フェーズ接続

- Phase4.58: 本設計書レビュー
- Phase4.59: 設計書単独コミット
- Phase4.60: push前レビュー
- Phase4.61: push
- Phase4.62: remote再取得確認

その後、HTML/JS 実装フェーズを分離して実施する。
