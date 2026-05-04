# 電子書籍アフィリエイト UI Flags Phase4.39 実URL投入 DRY_RUN パッケージ設計

## 目的

本ドキュメントは、実アフィリエイトURL投入の前段として、DRY_RUN 用の実装パッケージ手順を固定する。
本フェーズでは本物URLを使用せず、BLOCKED 状態を維持したまま、実装順序と検証方法を明確化する。

## 安全前提

- 本物URLは投入しない
- サンプルURLは `example.invalid` のみ使用する
- Git commit / Git push はこの設計フェーズでは必須ではない
- WordPress本番更新・本番反映は行わない
- 判定は BLOCKED を維持する

## 実装スコープ

- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `ebook-affiliate-ui` 配下のJS（CTAリンク反映ロジック）
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`

## DRY_RUN 手順（全体）

1. データ追加（`campaign_items.json` に `affiliate_url` 追加）
2. HTML/JS 反映（`href="#"` 除去、CTAへURL反映、未設定時無効化）
3. 検証拡張（`check_affiliate_links.py` に許可ドメイン検証追加）
4. DRY_RUN 実行で BLOCK 維持を確認

## 1) campaign_items.json への DRY_RUN データ追加

方針:
- 各 item に `affiliate_url` を追加
- 移行互換のため `campaign_url` は残す
- 値は実URLではなく `https://example.invalid/...` を使用

必須ルール:
- `affiliate_url` が空文字 / null / `#` は禁止
- `item_id` とURLの対応関係を保つ
- `example.invalid` を本番候補データとして扱わない

期待結果:
- リンク候補データは揃うが、許可ドメイン検証で BLOCK のまま

## 2) HTML 側 href="#" 除去の実装手順

方針:
- 静的HTMLに `href="#"` を残さない
- `data-item-id` をキーに、JSでリンク先を注入

実装手順:
1. 対象の `a.book-card`（またはCTA要素）を特定
2. 固定 `href="#"` を削除
3. 初期状態は `data-item-id` のみ保持
4. JS初期化でURL解決後に `href` を設定

期待結果:
- HTML静的断面で `href="#"` 件数を削減可能
- URL解決失敗時は遷移不可制御へフォールバック

## 3) JS で affiliate_url を CTA へ反映する実装手順

URL解決優先順位:
1. `affiliate_url`
2. `campaign_url`
3. どちらも無効なら未設定扱い

CTA反映手順:
1. `item_id` から該当データを取得
2. URLを正規化（trim）
3. 有効URLなら `href` を設定
4. 無効URLなら CTA を disabled 状態にする

無効化ルール:
- `aria-disabled="true"`
- 見た目に disabled クラス
- click 時は `preventDefault()`
- ログ/計測に `url_missing` を記録

## 4) URL未設定時 CTA 無効化の実装手順

未設定条件:
- `affiliate_url` と `campaign_url` の両方が空
- 値が `#`
- 値がURLとして不正

挙動:
- 遷移させない
- 表示文言を「準備中」に統一
- `check_affiliate_links.py` では invalid として集計

## 5) check_affiliate_links.py 許可ドメイン検証拡張

追加仕様:
- `urllib.parse` でURLをparseし hostname を取得
- 許可ドメイン一覧と照合
- 不一致を `json invalid count` に加算

初期許可ドメイン:
- `books.rakuten.co.jp`
- `hb.afl.rakuten.co.jp`
- `www.amazon.co.jp`
- `amzn.to`

DRY_RUN前提:
- `example.invalid` は許可しない
- そのため DRY_RUN 中は意図的に BLOCK 維持となる

## 6) 実装コミット分割方針

コミットは必ず次の3分割で管理する。

1. データ追加コミット
- 対象: `campaign_items.json`
- 内容: `affiliate_url` 追加（example.invalid）

2. JS/HTML 反映コミット
- 対象: HTML + JS
- 内容: `href="#"` 除去、CTA反映、未設定時無効化

3. 検証スクリプト拡張コミット
- 対象: `scripts/check_affiliate_links.py`
- 内容: 許可ドメイン検証の追加

## 7) ロールバック順

障害時は新しいコミットから逆順で戻す。

1. 検証スクリプト拡張コミットをrevert
2. JS/HTML 反映コミットをrevert
3. データ追加コミットをrevert

理由:
- 判定ロジックの変更を先に戻すと、表示側不整合を最小化しやすい
- データは最後に戻すことで検証の比較がしやすい

## 8) DRY_RUN 完了判定

設計実行ラインの PASS:
- 実装手順が3分割コミットで計画されている
- ロールバック順が定義されている
- BLOCK維持前提が明示されている

実装後の期待判定（この時点ではまだ目標）:
- `href="#"` は 0 件
- JSON未設定は 0 件を目標
- ただし `example.invalid` 利用中は許可ドメイン不一致により BLOCK 維持

## 9) 次フェーズ入力

次フェーズでは以下を実行する。

- Phase4.40: 本設計書レビュー
- Phase4.41: 単独コミット
- Phase4.42: push前レビュー
- Phase4.43: push
- Phase4.44: remote再取得確認

その後、実URL投入フェーズへ進む場合は、`example.invalid` から実URLへ置換する前に承認ゲートを入れる。
