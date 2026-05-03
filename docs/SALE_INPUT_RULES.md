# 44. セール情報入力設計（確定版）

## 1. 目的
- セール案件を安全に手動投入できる入力基盤を定義する。
- 43の安定運用を壊さず、将来の45（半自動投入）・46（自動収集）に備える。
- 入力ゆれによる誤判定、重複投入、期限切れ掲載を防止する。

## 2. 対象範囲
- Google Sheets の投稿キュー入力仕様。
- セール系記事の入力ルールと判定ルール。
- 対象は手動投入のみ（収集自動化は対象外）。

## 3. 必須列定義
- row_id: 一意ID。
- article_type: `sale` 固定。
- work_title: 作品名。
- store: 主ストア（許容値は「7. store 許容値」参照）。
- campaign_name: セール名。
- sale_start_date: 開始日。
- sale_end_date: 終了日。
- category: `sale` 固定。
- status: 初期値 `NEW`。

## 4. 推奨列定義
- official_url
- rakuten_url
- dmm_url
- entry_required
- discount_text
- point_text
- target_keyword
- tags
- notes
- author
- publisher
- series_name
- volume

## 5. バリデーション仕様
- row_id: 空欄不可、重複不可。
- article_type: `sale` 以外は受け付けない。
- category: `sale` 以外は受け付けない。
- sale_start_date / sale_end_date: `YYYY-MM-DD` 形式のみ。
- sale_end_date < sale_start_date はエラー。
- URL列: `http://` または `https://` で始まる文字列のみ。
- status: `NEW` で投入（手動で `DRAFTED` / `FAILED` を直接入力しない）。
- discount_text / point_text: 数値や条件を含む短文を推奨。

## 6. sale_end_date 超過ルール
- 判定基準は JST の当日。
- 今日 > sale_end_date の行は新規投入不可。
- 既存 `NEW` 行が期限超過になった場合は投稿対象外として管理対象へ移す。
- 期限超過は `FAILED` へ直結させない（誤停止防止）。

## 7. store 許容値
表記ゆれ防止のため、入力値は以下の固定値のみ許容する。

- kindle
- rakuten_kobo
- dmm_books
- official
- other

本文表示名は投稿生成側で以下へ変換する。

- kindle -> Kindle
- rakuten_kobo -> 楽天Kobo
- dmm_books -> DMMブックス

## 8. entry_required 表記統一
許容値は以下の3種類のみ。

- required: エントリー必須
- optional: エントリー推奨
- none: エントリー不要

運用ルール:
- 空欄は `none` と同義として扱う。
- ただし、手動投入時は `none` を明示入力する。

## 9. URL優先順位
- 基本掲載優先: official_url
- 代替1: rakuten_url
- 代替2: dmm_url
- 複数URLがある場合も本文主リンクは1本を優先順位で採用する。
- notes に補足リンク採用理由を残せるようにする。

## 10. 重複判定キー
- 第一キー: work_title + store + campaign_name + sale_end_date
- 補助キー: official_url または rakuten_url または dmm_url
- 同一キーで status が `NEW` / `DRAFTED` の行がある場合は新規投入を止める。
- campaign_name の表記ゆれは人間確認する。

## 11. 手動投入サンプル3件

### サンプル1
- row_id: SALE-20260504-001
- article_type: sale
- work_title: サンプル作品A
- store: kindle
- official_url: https://example.com/a
- rakuten_url:
- dmm_url:
- campaign_name: GWポイント還元
- sale_start_date: 2026-05-04
- sale_end_date: 2026-05-10
- entry_required: required
- discount_text: 最大50%OFF
- point_text: 最大20%還元
- target_keyword: 電子書籍 セール
- category: sale
- tags: セール, Kindle
- notes: 初回投入テスト
- status: NEW

### サンプル2
- row_id: SALE-20260504-002
- article_type: sale
- work_title: サンプル作品B
- store: rakuten_kobo
- official_url:
- rakuten_url: https://example.com/b
- dmm_url:
- campaign_name: 週末クーポン
- sale_start_date: 2026-05-05
- sale_end_date: 2026-05-08
- entry_required: optional
- discount_text: 30%OFFクーポン
- point_text: 5倍
- target_keyword: Kobo クーポン
- category: sale
- tags: セール, Kobo
- notes: URLは楽天優先
- status: NEW

### サンプル3
- row_id: SALE-20260504-003
- article_type: sale
- work_title: サンプル作品C
- store: dmm_books
- official_url:
- rakuten_url:
- dmm_url: https://example.com/c
- campaign_name: 初回購入限定
- sale_start_date: 2026-05-06
- sale_end_date: 2026-05-12
- entry_required: none
- discount_text: 初回70%OFF
- point_text:
- target_keyword: DMM 初回割引
- category: sale
- tags: セール, DMM
- notes: 初回条件を本文で明記
- status: NEW

## 12. discount_text の禁止表現
法務・誤認防止のため、以下の断定表現は入力禁止。

- 絶対お得
- 最安確定
- 今すぐ買わないと損
- 必ず還元
- 完全無料

## 13. 43中にやっていいこと / まだやらないこと

### やっていいこと
- 入力仕様の確定。
- 列定義とバリデーション文書化。
- 手動投入テンプレート作成。
- サンプル行レビュー。
- 運用チェックリスト整備。

### まだやらないこと
- 自動クロール導入。
- API連携での大量取得。
- 自動キュー投入。
- MAX_ROWS_PER_RUN の増加。
- cron頻度の増加。
- publish自動化。

## 14. 43固定条件（維持）
- 1日1回。
- 1件。
- draftのみ。
- publishなし。
- 3日連続正常まで拡張しない。
- 7日連続正常まで自動収集しない。