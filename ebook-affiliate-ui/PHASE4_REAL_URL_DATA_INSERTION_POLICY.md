# Phase4.105 実URL投入データ方針 設計

## 1. 目的

本設計書は、電子書籍アフィリエイトUIの `campaign_items.json` に対して、
DRY_RUN用 `example.invalid` URL から実アフィリエイトURLへ切り替える前の
データ投入方針・検証条件・ロールバック方針を固定する。

本フェーズでは設計書のみを作成し、コード・JSONデータ・HTML・本番環境は変更しない。

## 2. 対象

対象:
- ebook-affiliate-ui/data/campaign_items.json

ただし Phase4.105 ではデータ変更しない。
実URL投入は後続フェーズで実施する。

非対象:
- ebook-affiliate-ui/scripts/check_affiliate_links.py
- ebook-affiliate-ui/kobo-campaign-list-final-v3.html
- ebook-affiliate-ui/logs/manual_override.log
- core/decision_package_reader.py
- WordPress本番環境

## 3. フィールド方針

### affiliate_url

`affiliate_url` は正式キーとして扱う。

方針:
- 実アフィリエイトURLを設定する
- HTML/JS CTA が優先参照する
- 全10件に必須設定する
- 空文字、null、`#`、`example.invalid` は本番不可

### campaign_url

`campaign_url` は互換fallback兼検証対象として扱う。

今回方針:
- `campaign_url` には `affiliate_url` と同じ実URLを設定する
- 理由は、現行 `check_affiliate_links.py` が `affiliate_url` と `campaign_url` の両方を検証対象にしているため
- `campaign_url` を空または `#` のままにすると PRODUCTION で `empty_or_unset` BLOCK になる

## 4. store別 実URL許可ドメイン

| store | 件数 | 許可ドメイン |
|---|---:|---|
| rakuten_kobo | 3 | `hb.afl.rakuten.co.jp`, `books.rakuten.co.jp` |
| kindle | 3 | `www.amazon.co.jp`, `amzn.to` |
| cmoa | 2 | `www.cmoa.jp` |
| dmm_books | 2 | `book.dmm.com`, `al.dmm.com` |

全URLは `https://` 必須。
`http://` は `non_https` として BLOCK。

## 5. example.invalid 置換方針

- 全10件を一括で置換する
- 部分投入は禁止
- `affiliate_url` と `campaign_url` を同時に実URL化する
- 実URLが10件分揃うまでデータ変更フェーズへ進まない
- `example.invalid` が1件でも残る場合、PRODUCTIONはBLOCK

## 6. PRODUCTION exit 0 条件

実URL投入後、以下をすべて満たす必要がある。

- JSON構文OK
- 全10件に `affiliate_url` あり
- 全10件に `campaign_url` あり
- `example.invalid` 0件
- `empty_or_unset` 0件
- `invalid_url` 0件
- `non_https` 0件
- `store_not_allowed` 0件
- `domain_not_allowed` 0件
- HTML内 `href="#"` 0件
- `LINK_CHECK_MODE=PRODUCTION python3 scripts/check_affiliate_links.py` が exit 0

## 7. ブラウザ確認へ進む条件

以下を満たすまでブラウザ確認へ進まない。

1. DRY_RUN 実行で重大BLOCKなし
2. PRODUCTION 実行で exit 0
3. HTML内 `href="#"` 0件維持
4. 実URLが全件許可ドメイン内
5. `affiliate_url` と `campaign_url` が全件同値

## 8. 本番反映条件

WordPress本番反映は以下をすべて満たすまで BLOCKED。

- 実URL投入コミットがGitHub保存済み
- remote再取得確認済み
- PRODUCTION exit 0
- ブラウザ Console エラーなし
- スマホ幅目視確認OK
- 人間承認あり

## 9. ロールバック方針

コミット前:
- `git restore ebook-affiliate-ui/data/campaign_items.json`

コミット後:
- 対象コミットを `git revert` する
- または `campaign_items.json` を直前の安全コミットから復元する

ロールバック後:
- DRY_RUN再実行
- PRODUCTIONがBLOCKへ戻ることを確認
- 本番反映BLOCKED維持を確認

## 10. 後続フェーズ

- Phase4.106: 本設計書レビュー
- Phase4.107: 本設計書単独コミット
- Phase4.108: push前レビュー
- Phase4.109: push
- Phase4.110: remote再取得確認
- Phase4.111以降: 実URL投入データ作成・検証

## 11. Phase4.111.2A 一時運用（追記）

Phase4.111.2A では、cmoa審査待ちのため一時的に8件先行投入モードを適用する。

- 先行対象: rakuten_kobo 3件 / kindle 3件 / dmm_books 2件
- 保留対象: cmoa 2件
- PRODUCTION exit 0 は一時的に必須から除外
- 本番反映は BLOCKED 維持

詳細は PHASE4_111_2A_EARLY_8_MODE_DESIGN.md を正とする。
