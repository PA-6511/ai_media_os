# 電子書籍アフィリエイト UI Flags Phase4.75 リンク検証スクリプト許可ドメイン拡張設計

## 目的

本ドキュメントは、`check_affiliate_links.py` の許可ドメイン検証拡張に向けて、
実装前に判定ルールと終了コード仕様を固定する。

本フェーズは設計固定のみを対象とし、実装変更は行わない。

## フェーズ境界（固定）

対象:
- `ebook-affiliate-ui/PHASE4_LINK_CHECKER_DOMAIN_EXTENSION_DESIGN.md`

非対象:
- `ebook-affiliate-ui/scripts/check_affiliate_links.py`
- `ebook-affiliate-ui/data/campaign_items.json`
- `ebook-affiliate-ui/kobo-campaign-list-final-v3.html`
- `core/decision_package_reader.py`
- WordPress 本番

## 安全前提

- 自動公開・自動投稿・自動削除は行わない
- 本フェーズで Git commit / push / 本番反映は行わない
- DRY_RUN と PRODUCTION の判定軸を明確に分離する
- 現在の本番反映状態は BLOCKED のまま維持する

## 設計方針

### 1) URL検証対象

- 各 item の `affiliate_url` と `campaign_url` の両方を検証対象にする
- URL優先順位は既存仕様を維持し、判定では両キーの妥当性を記録する
- 片方が有効でも、もう片方に不正値がある場合は警告対象として残す

### 2) store種別ごとの許可ドメイン

`store` ごとに許可ドメインを定義し、`hostname` 単位で判定する。

初期定義（Phase4.75 設計値）:
- `kobo`: `books.rakuten.co.jp`, `hb.afl.rakuten.co.jp`
- `rakuten`: `books.rakuten.co.jp`, `hb.afl.rakuten.co.jp`
- `amazon`: `www.amazon.co.jp`, `amzn.to`

拡張ルール:
- サブドメイン許容は明示登録のみ（ワイルドカード不使用）
- `store` 未定義または許可ドメイン未定義は BLOCK 扱い
- `http://` は不許可、`https://` のみ許可

### 3) DRY_RUN 専用プレースホルダ判定

- `example.invalid` は DRY_RUN 専用 URL として識別する
- DRY_RUN モードでは `example.invalid` を「許容（警告）」として扱う
- PRODUCTION モードでは `example.invalid` を「不許可（エラー）」として扱う
- DRY_RUN で許容した場合でも、本番反映可否フラグは `BLOCKED` を維持する

### 4) BLOCK条件

以下はモードに関わらず BLOCK 条件とする。

- 空文字、null、キー未設定
- `#`、`javascript:` など遷移先として無効な値
- URL parse 失敗
- 許可ドメイン外の `hostname`
- `https://` 以外

追加条件（PRODUCTION のみ）:
- `example.invalid` を含む URL

## モード別判定仕様

### DRY_RUN モード

- 許可: `example.invalid`（警告付き）
- 不許可: 空・未設定・不正URL・未許可ドメイン
- 期待状態: 検証実行自体は可能だが、本番反映可否は `BLOCKED`

### PRODUCTION モード

- 許可: 許可ドメインかつ `https://` のみ
- 不許可: DRY_RUN プレースホルダを含む全NG条件
- 期待状態: 全件適合時のみ本番反映可否を `PASS` にできる

## 終了コード仕様（固定）

`check_affiliate_links.py` 実装時は以下を採用する。

- `0`: 検証処理成功、かつ選択モードの必須条件を満たす
- `1`: 検証処理成功、ただしポリシー違反あり（BLOCK）
- `2`: 入力ファイル欠落、JSON破損、実行時例外などのシステムエラー

補足:
- DRY_RUN で `example.invalid` のみを検出したケースは「警告」を出力する
- ただし本番反映可否フラグは `BLOCKED` 固定で報告する

## 出力項目仕様（実装時に必須化）

最低限、次をログ/標準出力で出せるようにする。

- 実行モード（`DRY_RUN` / `PRODUCTION`）
- 総件数
- `affiliate_url` 検証件数
- `campaign_url` 検証件数
- invalid 件数（空・不正・未許可ドメイン）
- `example.invalid` 検出件数
- 本番反映可否（`PASS` / `BLOCKED`）
- 終了コード

## 受け入れ条件（設計レビュー観点）

- `example.invalid` の DRY_RUN 専用扱いが明記されている
- DRY_RUN と PRODUCTION の差分ルールが明記されている
- `store` 種別ごとの許可ドメインが定義されている
- `affiliate_url` と `campaign_url` の両方を検証対象としている
- 空・未設定・不正URL・未許可ドメインが BLOCK 条件として固定されている
- 終了コード `0/1/2` が固定されている

## 次フェーズ接続（実装分離）

- Phase4.76: `check_affiliate_links.py` 実装
- Phase4.77: 検証スクリプト単独コミット
- Phase4.78: push 前レビュー
- Phase4.79: push
- Phase4.80: remote 再取得確認

この分離により、問題発生時は検証スクリプト変更のみ単独で revert できる。