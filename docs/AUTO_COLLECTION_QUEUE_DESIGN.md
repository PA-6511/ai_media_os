# AUTO_COLLECTION_QUEUE_DESIGN

## 0. 目的と運用前提

この文書は、セール情報の自動収集と投稿キュー投入を安全に段階導入するための設計仕様である。

運用前提:
- 43の安定運用を最優先する
- 現在の解禁範囲は「手動投入 -> 1件draft生成 -> 人間レビュー」まで
- 自動公開は行わない
- 本設計段階では本線接続を行わない

本設計で扱う範囲:
- 自動収集のデータ仕様
- 候補リスト保存形式
- 投稿キュー投入前の検証仕様
- DRY_RUNシミュレーション仕様
- 段階解禁条件


## 1. 自動収集の対象

対象ストア:
- rakuten_kobo
- dmm_books
- kindle_amazon

収集対象フィールド（候補データ）:
- source_store
- work_title
- campaign_name
- sale_start_date
- sale_end_date
- entry_required
- discount_text
- point_text
- official_url
- rakuten_url
- dmm_url
- amazon_url
- cta_store_priority
- fetched_at
- source_name
- source_url

補足:
- 価格や割引は断定値として扱わず、収集時点の参考情報として保持する
- Kindle/Amazon は規約順守確認済みリンクのみ対象化する


## 2. 収集候補リストの形式

投稿キューへ直接投入しない。まず候補リストに保存する。

推奨保存先:
- data/sale_candidates/

推奨ファイル:
- data/sale_candidates/candidates_YYYYMMDD.json
- data/sale_candidates/candidates_YYYYMMDD.csv

JSON基本スキーマ:
- candidate_id: string
- source_store: string
- work_title: string
- campaign_name: string
- sale_start_date: string (YYYY-MM-DD)
- sale_end_date: string (YYYY-MM-DD)
- entry_required: string (required|optional|none)
- discount_text: string
- point_text: string
- official_url: string
- rakuten_url: string
- dmm_url: string
- amazon_url: string
- cta_store_priority: string
- fetched_at: string (ISO8601)
- source_name: string
- source_url: string
- review_status: string (pending|approved|rejected)
- review_note: string

candidate_id生成ルール:
- 正規化キーをsha1化して先頭12桁
- 正規化キー = source_store + work_title + campaign_name + sale_end_date


## 3. 投稿キュー投入前バリデーション

必須チェック:
- source_store が許可値に含まれる
- article_type は sale_article
- work_title が空でない
- campaign_name が空でない
- sale_end_date が YYYY-MM-DD 形式
- entry_required が required|optional|none のいずれか
- CTA候補URLが少なくとも1つ存在する

ストア別URLチェック:
- rakuten_kobo: rakuten_url または official_url
- dmm_books: dmm_url または official_url
- kindle_amazon: amazon_url または official_url

Kindle/Amazon追加チェック:
- amazon_url はアソシエイトID付き形式のみ許可
- 価格/割引の断定文言を生成しない
- 画像URLを自動収集しない

検証失敗時:
- 投稿キュー未投入
- reason_code を付与して候補を retain


## 4. 重複判定

重複判定は二段階で実施する。

候補リスト内重複:
- candidate_id 一致で重複

投稿キュー重複:
- row_id 一致
- または次の複合キー一致
- source_store + work_title + campaign_name + sale_end_date

重複時の挙動:
- 投入対象から除外
- DRY_RUN結果に skip_duplicate として表示


## 5. sale_end_date期限切れ除外

除外ルール:
- sale_end_date < 実行日(UTC) は期限切れとして除外

運用オプション（将来）:
- grace_days を0固定で開始
- 安定後に1日まで許可するかを別途判断

除外時の扱い:
- 投稿キューへ投入しない
- DRY_RUN結果に skip_expired として表示


## 6. 手動承認フロー

安全なフロー:
- 外部セール情報
- 収集候補リストへ保存
- 人間レビュー（pending -> approved/rejected）
- approved のみ投稿キュー候補へ
- 1件だけ昇格して status=NEW
- run_single_row_real.py で1件draft生成

承認条件:
- store別URL妥当性
- セール期間妥当性
- 文言リスク（誇張・断定）なし
- Kindle/Amazonは規約チェック済み


## 7. DRY_RUN仕様

対象スクリプト（設計名）:
- tools/enqueue_sale_candidates.py

初期モード:
- --dry-run 固定

DRY_RUNで実施すること:
- 入力JSON読込
- スキーマ検証
- 重複判定
- 期限切れ除外
- ストア別URL妥当性確認
- 投入予定件数の算出

DRY_RUNで実施しないこと:
- 投稿キューへの書き込み
- status変更
- WordPress投稿処理

標準出力例（概念）:
- total_candidates
- valid_candidates
- skipped_duplicate
- skipped_expired
- skipped_validation_error
- would_enqueue_ids


## 7-B. preview_sale_candidates.py（47-B 実装済み）

実装ファイル:
- tools/preview_sale_candidates.py

位置づけ:
- セクション7のDRY_RUN仕様を読み取り専用で先行実装したスクリプト
- Sheets書き込み・WordPress接続・cron連携は一切行わない

使い方:
```
# デフォルト（samples/auto_collection/sale_candidates.sample.json を読む）
python3 tools/preview_sale_candidates.py

# 任意のJSONを指定
python3 tools/preview_sale_candidates.py --input path/to/candidates.json
```

実行結果の見方:
- would_enqueue: Sheetsに投入される予定件数（DRY_RUNなので実際には書かない）
- skip_expired: sale_end_date < 実行日(UTC) で除外された件数
- skip_duplicate: candidate_id 重複で除外された件数
- skip_validation_err: バリデーション失敗で除外された件数

サンプルJSON:
- samples/auto_collection/sale_candidates.sample.json
- 楽天Kobo・DMM・Kindle 各1件
- 期限切れ検証用 1件（sale_end_date が過去日）
- 重複検証用 1件（candidate_id を同一に設定）

注意事項:
- このスクリプトはSheetsへの接続を行わない（SPREADSHEET_ID 不要）
- 重複判定は候補リスト内のcandidate_id一致のみ（投稿キューとの照合は未実装）
- review_status によるフィルタリングは行わない（pending/approved いずれも表示）


## 8. 複数件処理の解禁条件

現時点:
- 常に1件固定

将来解禁の段階:
- 47-B: DRY_RUNのみ（3日連続正常）
- 47-C: 手動承認付き1件投入（7日連続正常）
- 47-D: 複数件2〜3件（連続正常後）

複数件解禁時の制約:
- 1回あたり最大2〜3件から開始
- 同一ストア上限を設定
- 同一キャンペーン上限を設定
- sale_end_dateが近い順を優先
- エラー時は基本継続、結果を個別記録


## 9. 禁止事項

本番接続前は以下を禁止する:
- 自動収集の本稼働
- 自動キュー投入
- 複数件まとめ処理
- cron頻度変更
- MAX_ROWS_PER_RUN増加
- 自動公開
- .env / secrets の安易な変更
- 外部APIの無制限追加


## 10. フェーズ定義

47-A（完了）: 設計のみ
- 本文書の作成
- サンプルJSON仕様の確定
- バリデーション仕様の確定

47-B（完了）: DRY_RUN実装
- tools/preview_sale_candidates.py 実装済み（読み取り・判定のみ）
- 全スキップ判定の動作確認済み（skip_expired / skip_duplicate）
- 詳細仕様: セクション7-B 参照

47-C（設計完了・実装待ち）: 手動承認付き1件投入
- YES入力必須（大文字完全一致）
- approved 候補を最大1件のみ status=NEW で Sheets に書き込む
- 解禁条件: 47-B が 3日連続正常 かつ Sheets 疎通確認済み
- 詳細仕様: docs/ENQUEUE_47C_DESIGN.md 参照

47-D（後段）: 複数件拡張
- 2〜3件から開始
- 連続正常時のみ段階拡張


## 11. 受け入れ条件（各フェーズ完了判定）

47-A（完了）:
- [x] 収集候補データ形式が定義されている
- [x] 投稿キュー投入前バリデーションが定義されている
- [x] 重複判定と期限切れ除外ルールが定義されている
- [x] 手動承認フローが定義されている
- [x] DRY_RUN専用方針が明記されている
- [x] 複数件解禁条件と禁止事項が明記されている

47-B（完了）:
- [x] preview_sale_candidates.py が実装されている
- [x] skip_expired 判定が動作する
- [x] skip_duplicate 判定が動作する
- [x] バリデーションエラーが正しく表示される
- [x] Sheets・WordPress への書き込みが一切行われない
- [x] docs に使い方が記載されている

47-C（実装待ち）:
- 詳細は docs/ENQUEUE_47C_DESIGN.md セクション8 参照
