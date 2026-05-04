# 電子書籍アフィリエイト UI Flags Phase4.87 実アフィリエイトURL投入前チェック設計

## 目的

本ドキュメントは、実アフィリエイトURLを `campaign_items.json` へ投入する前に、
許可条件・投入手順・PRODUCTION PASSの達成条件を固定する。

本フェーズは設計固定のみを対象とし、URL投入・スクリプト変更・本番反映は行わない。

## フェーズ境界（固定）

対象:
- `ebook-affiliate-ui/PHASE4_REAL_AFFILIATE_URL_PREFLIGHT_DESIGN.md`

非対象:
- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `core/decision_package_reader.py`
- WordPress 本番

## 安全前提

- 自動公開・自動投稿・自動削除は行わない
- 本フェーズで Git commit / push / 本番反映は行わない
- 実URLは本設計書が単独コミット・remote確認済みになるまで投入しない
- 現在の本番反映状態は BLOCKED のまま維持する

## 実URL投入の前提条件

実URL投入を開始する前に、以下が揃っていることを確認する。

- [ ] 各 item の `store` 値が `ALLOWED_DOMAINS_BY_STORE` に登録済みのキーと一致している
- [ ] 投入URLが `https://` で始まる
- [ ] 投入URLのホスト名が当該 store の許可ドメインに含まれている
- [ ] アフィリエイトURL発行元の審査・承認が完了している
- [ ] 短縮URLや redirect URLを使う場合は最終ホスト名が許可ドメインに含まれている

## store別 許可URL仕様（Phase4.81 ALLOWED_DOMAINS_BY_STORE 準拠）

| store キー | 許可ドメイン |
|---|---|
| `kobo` | `books.rakuten.co.jp`, `hb.afl.rakuten.co.jp` |
| `rakuten_kobo` | `books.rakuten.co.jp`, `hb.afl.rakuten.co.jp` |
| `rakuten` | `books.rakuten.co.jp`, `hb.afl.rakuten.co.jp` |
| `kindle` | `www.amazon.co.jp`, `amzn.to` |
| `amazon` | `www.amazon.co.jp`, `amzn.to` |

現在の `campaign_items.json` store値一覧（Phase4.86 時点）:
- `rakuten_kobo`: 3件
- `kindle`: 3件
- `cmoa`: 2件 ← **ALLOWED_DOMAINS_BY_STORE 未登録**
- `dmm_books`: 2件 ← **ALLOWED_DOMAINS_BY_STORE 未登録**

重要:
- `cmoa` / `dmm_books` は現時点で `check_affiliate_links.py` に許可ドメインが未定義
- 実URL投入の前に、cmoa / dmm_books は先に許可ドメイン追加を行う
- 実URL投入前に、これら store の許可ドメインを `check_affiliate_links.py` へ追加する必要がある
- または `cmoa` / `dmm_books` を実URL投入対象から除外する方針を選択する

## PRODUCTION exit 0 達成条件

`LINK_CHECK_MODE=PRODUCTION python3 scripts/check_affiliate_links.py` が exit 0 になるには:

検証キーワード固定:
- json invalid count 0
- html href=# 0

1. `html href=# count` が 0 件（Phase4.74 で達成済み）
2. `json invalid count` が 0 件
   - `affiliate_url` が `https://` で始まる
   - `affiliate_url` のホスト名が許可ドメインに含まれる
   - `campaign_url` が `#` のまま残る場合は empty_or_unset として BLOCK になる

補足:
- `campaign_url` は全件 `#` のため、現状では PRODUCTION で 10 件 invalid 扱いになる
- 本番反映前に `campaign_url` を実URLに置換するか、検証ロジックの扱いを設計書で固定する必要がある

## campaign_url の扱い方針（選択肢）

以下のいずれかを次フェーズで確定する。

**方針 A: campaign_url も実URLに更新する**
- affiliate_url と同じURLを campaign_url にも設定する
- PRODUCTION 検証を affiliate_url / campaign_url の両方 PASS で通過する
- 管理コストが増えるが、フォールバック動作と整合する

**方針 B: campaign_url の検証を警告に留める**
- `check_affiliate_links.py` で `campaign_url` の `#` を「警告のみ」に格下げする
- PRODUCTION PASS 条件を `affiliate_url` 全件適合のみとする
- スクリプト変更が必要になる

**方針 C: campaign_url を affiliate_url で上書き管理する**
- JSON構造上、campaign_url を廃止して affiliate_url 一本化する
- HTML/JS 側も campaign_url フォールバックを削除する変更が必要

現時点の推奨: **方針 A**（campaign_url も実URLに揃える）
理由: 設計変更なし・スクリプト変更なし・HTML変更なし

## 実URL投入手順（設計）

1. 対象 item ごとに実アフィリエイトURLを用意する
2. `campaign_items.json` の `affiliate_url` と `campaign_url` を置換する
3. `LINK_CHECK_MODE=DRY_RUN python3 scripts/check_affiliate_links.py` を実行して変数確認
4. `LINK_CHECK_MODE=PRODUCTION python3 scripts/check_affiliate_links.py` を実行して exit 0 を確認
5. 問題なければ単独コミット → push

## ブラウザ実機確認に進む条件

以下がすべて満たされた時点でブラウザ確認フェーズへ進む。

- [ ] PRODUCTION exit 0 確認済み
- [ ] `html href=# count: 0` 維持確認済み
- [ ] `example.invalid` を含むURLが 0 件
- [ ] スクリプト単独コミット・push・remote確認済み

## cmoa / dmm_books の扱い方針（要決定）

現時点では `cmoa` / `dmm_books` の許可ドメインが未定義のため、
これらのURLを投入しても PRODUCTION で `store_not_allowed` として BLOCK になる。

次フェーズで以下を選択する。

- **選択肢 1**: `check_affiliate_links.py` に cmoa / dmm_books の許可ドメインを追加してから実URL投入
- **選択肢 2**: cmoa / dmm_books は今回の実URL投入対象から除外し、対応を後フェーズに先送り

現時点の推奨: **選択肢 1**（設計書で許可ドメインを固定してから実装）

## 受け入れ条件（設計レビュー観点）

- 実URL投入前提条件が明記されている
- store別許可URL仕様が明記されている
- cmoa / dmm_books が未対応であることが明記されている
- PRODUCTION exit 0 達成条件が明記されている
- campaign_url の扱い方針が明記されている
- ブラウザ実機確認に進む条件が明記されている
- 実URL投入手順が明記されている

## ロールバック方針

実URL投入は `campaign_items.json` の単独コミットで実施するため、
問題発生時は当該コミットのみを単独で revert できる。

ロールバック対象:
- `ebook-affiliate-ui/data/campaign_items.json`

ロールバック対象外:
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- すべての `PHASE4_*.md`

ロールバック条件:
- PRODUCTION 実行で予期せぬ invalid が残る場合
- 許可ドメイン外URLが混入した場合
- ブラウザ実機確認でリンク先が不正な場合

ロールバック後の確認:
- `example.invalid` の DRY_RUN 状態に戻っていること
- 本番反映が未実施であること
- BLOCKED 状態が維持されていること

## 次フェーズ接続

- Phase4.88: 本設計書レビュー
- Phase4.89: 設計書単独コミット
- Phase4.90: push前レビュー
- Phase4.91: push
- Phase4.92: remote再取得確認

その後、cmoa / dmm_books 許可ドメイン追加または除外方針を確定してから実URL投入フェーズへ進む。
