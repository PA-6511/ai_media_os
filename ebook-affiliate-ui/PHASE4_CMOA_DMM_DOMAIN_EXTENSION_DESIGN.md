# 電子書籍アフィリエイト UI Flags Phase4.93 cmoa / dmm_books 許可ドメイン追加設計

## 目的

本ドキュメントは、`check_affiliate_links.py` の `ALLOWED_DOMAINS_BY_STORE` に
`cmoa` と `dmm_books` の許可ドメインを追加する前提条件と実装方針を固定する。

本フェーズは設計固定のみを対象とし、実装変更・データ変更・本番反映は行わない。

## フェーズ境界（固定）

対象:
- `ebook-affiliate-ui/PHASE4_CMOA_DMM_DOMAIN_EXTENSION_DESIGN.md`

非対象:
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `ebook-affiliate-ui/PHASE4_REAL_AFFILIATE_URL_PREFLIGHT_DESIGN.md`
- `core/decision_package_reader.py`
- WordPress 本番

## 現状整理（Phase4.92時点）

- `campaign_items.json` の store 分布:
  - `rakuten_kobo`: 3件
  - `kindle`: 3件
  - `cmoa`: 2件
  - `dmm_books`: 2件
- `check_affiliate_links.py` の `ALLOWED_DOMAINS_BY_STORE` には `cmoa` / `dmm_books` が未登録
- このため、`cmoa` / `dmm_books` の実URL投入後は `store_not_allowed` で BLOCK になる

## 安全前提

- 自動公開・自動投稿・自動削除は行わない
- 本フェーズで Git add / commit / push は行わない
- 実URL投入は行わない
- 本番反映は行わない
- 本番反映状態は BLOCKED のまま維持する

## 追加対象（設計値）

`ALLOWED_DOMAINS_BY_STORE` へ以下を追加する。

- `cmoa`:
  - `www.cmoa.jp`
- `dmm_books`:
  - `book.dmm.com`
  - `al.dmm.com`

補足:
- 実際のアフィリエイトリンク発行結果によっては許可ドメインの追加調整が必要
- ワイルドカード許可は行わない
- `https://` のみ許可する既存方針を維持する

## 検証ルール（維持）

- `LINK_CHECK_MODE=DRY_RUN`:
  - `example.invalid` は許容（警告）
  - ただし本番反映可否は `BLOCKED` 維持
- `LINK_CHECK_MODE=PRODUCTION`:
  - `example.invalid` は不許可
  - 許可ドメイン外は `domain_not_allowed`
  - store未登録は `store_not_allowed`
- `affiliate_url` / `campaign_url` の両方を検証対象とする

## PRODUCTION exit 0 達成に対する影響

`cmoa` / `dmm_books` を許可ドメイン登録することで、以下が改善される。

- `store_not_allowed` 起因の BLOCK を解消可能

ただし、以下は別途対応が必要。

- `campaign_url` が `#` のままの場合は `empty_or_unset` で BLOCK
- 実URL未投入状態では PRODUCTION exit 0 は達成不可

固定キーワード:
- PRODUCTION exit 0
- json invalid count 0
- html href=# 0

## 実装フェーズへの受け渡し仕様

実装フェーズ（次段）では以下のみを実施する。

1. `check_affiliate_links.py` の `ALLOWED_DOMAINS_BY_STORE` に `cmoa` / `dmm_books` を追加
2. `python3 -m py_compile` で構文検証
3. DRY_RUN 実行で既存の `example.invalid` 警告挙動を維持確認
4. PRODUCTION 実行で `store_not_allowed` が消えることを確認

## 期待される検証結果（実装後）

- DRY_RUN:
  - `example.invalid count: 10`
  - `RESULT: BLOCK`（維持）
- PRODUCTION:
  - `store_not_allowed` は 0 件になる想定
  - ただし `example.invalid` / `campaign_url=#` により `RESULT: BLOCK` 維持

## ロールバック方針

実装フェーズは `check_affiliate_links.py` の単独コミットで行う。
問題発生時は当該コミットのみを単独で revert する。

ロールバック対象:
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`

ロールバック対象外:
- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- すべての `PHASE4_*.md`

ロールバック条件:
- cmoa / dmm_books 以外の store 判定に副作用が出る
- DRY_RUN の `example.invalid` 許容挙動が壊れる
- PRODUCTION の `https://` 判定が壊れる

## 受け入れ条件（設計レビュー観点）

- `cmoa` / `dmm_books` の追加対象が明記されている
- 許可ドメイン候補が明記されている
- DRY_RUN / PRODUCTION の既存方針維持が明記されている
- PRODUCTION exit 0 への影響範囲が明記されている
- ロールバック方針が明記されている

## 次フェーズ接続

- Phase4.94: 本設計書レビュー
- Phase4.95: 設計書単独コミット
- Phase4.96: push前レビュー
- Phase4.97: push
- Phase4.98: remote再取得確認

その後、`check_affiliate_links.py` の実装フェーズへ進む。
