# ENQUEUE_47C_DESIGN

## 0. 目的と前提

本文書は 47-C「手動承認付き・最大1件 NEW 投入」の設計仕様である。

前提:
- 47-B（DRY_RUNプレビュー）が 3日連続正常終了していること
- Sheets への書き込み権限が有効であること
- 実行は毎回 人間がターミナルで手動起動 する
- cron・自動公開・複数件投入は本フェーズでは禁止

本フェーズで許可すること:
- preview_sale_candidates.py 相当の判定（読み取り）
- review_status = approved の候補を最大1件だけ投稿キューへ NEW として書き込む
- 書き込み前に標準入力で YES 確認を要求する

本フェーズで禁止すること:
- 2件以上の同時投入
- review_status = pending のまま投入
- --yes フラグ等による確認スキップ
- WordPress draft 生成（投入後は別途 run_single_row_real.py で行う）
- cron 連携
- 自動公開


## 1. 対象スクリプト（設計名）

```
tools/enqueue_sale_candidates.py
```

47-B 時点では未実装。47-C で新規実装する。


## 2. 実行フロー

```
python3 tools/enqueue_sale_candidates.py [--input <path>]
```

1. 入力JSONを読み込む（デフォルト: samples/auto_collection/sale_candidates.sample.json）
2. preview_sale_candidates.py と同じバリデーション・期限切れ・重複判定を実施
3. valid かつ review_status = approved の候補を抽出
4. 抽出件数が 0 件なら終了（EXIT 0）
5. 抽出件数が 1 件以上なら、最初の 1 件だけを「投入予定候補」として表示
6. 確認プロンプト（大文字YESのみ受け付ける）を表示
7. YES 以外の入力はキャンセル（EXIT 0）
8. YES 入力後、Sheets の投稿キューへ 1件だけ status=NEW として書き込む
9. 書き込み結果（row番号・candidate_id）を標準出力に表示して終了


## 3. 候補選択ルール（1件だけ選ぶ基準）

優先順位（上から順に評価）:
1. sale_end_date が近い順（今日から最も近い期限切れ前のもの）
2. review_status = approved のみ対象
3. source_store の優先順は設定しない（将来検討）

同点の場合:
- JSON 内での出現順（先頭）を採用


## 4. Sheets 書き込み仕様

書き込み先:
- 既存の投稿キューシート（src/sheets で利用中のスプレッドシート）
- 書き込みは append のみ（既存行の上書き禁止）

書き込みフィールド（最小セット）:
- row_id: 自動採番（既存最大 row_id + 1）
- status: NEW
- article_type: sale_article
- source_store: candidate の source_store
- work_title: candidate の work_title
- campaign_name: candidate の campaign_name
- sale_start_date: candidate の sale_start_date
- sale_end_date: candidate の sale_end_date
- entry_required: candidate の entry_required
- discount_text: candidate の discount_text
- point_text: candidate の point_text
- rakuten_url: candidate の rakuten_url
- dmm_url: candidate の dmm_url
- amazon_url: candidate の amazon_url
- official_url: candidate の official_url
- cta_store_priority: candidate の cta_store_priority
- enqueued_at: 実行時刻（ISO8601 UTC）
- candidate_id: candidate の candidate_id

書き込み禁止フィールド:
- wordpress_post_id（draft 生成前は空欄のまま）
- published_at（自動公開禁止）


## 5. 確認プロンプト仕様

表示フォーマット（概念）:
```
============================================================
  [投入予定 1件]
  candidate_id : a1b2c3d4e5f6
  work_title   : 楽天Kobo サンプル作品
  campaign     : 楽天Kobo テストキャンペーン
  store        : rakuten_kobo
  sale_end     : 2026-05-10
  status       : approved
============================================================
  !! Sheets の投稿キューに 1件 NEW として書き込みます。
  !! この操作は取り消せません。
  !! 続行するには YES と入力してください（それ以外でキャンセル）:
```

受付:
- 入力が `"YES"` と完全一致する場合のみ書き込み実行
- `"yes"` / `"y"` / `"Y"` はすべてキャンセル扱い

キャンセル時:
- `[CANCELLED] 書き込みを中止しました。Sheets は変更されていません。` と表示して EXIT 0


## 6. エラーハンドリング

| 状況 | 挙動 |
|---|---|
| 入力JSONが見つからない | エラーメッセージ表示 → EXIT 1 |
| JSON パースエラー | エラーメッセージ表示 → EXIT 1 |
| approved 候補が 0件 | `[INFO] 投入対象の approved 候補がありません。` → EXIT 0 |
| Sheets 書き込み失敗 | エラーメッセージ・スタックトレース表示 → EXIT 1（Sheetsは変更なし） |
| 書き込み後の行番号取得失敗 | 警告表示（EXIT 0、書き込み自体は成功） |


## 7. 実行後の確認手順（運用）

1. `enqueued_at` が正しい日時か確認
2. Sheets で該当行の status = NEW を目視確認
3. 問題なければ `run_single_row_real.py` で 1件 draft 生成
4. WordPress 管理画面で下書きを確認・編集
5. 問題があれば Sheets の該当行を手動で status = HOLD に変更

NOTE: draft 生成・投稿は `enqueue_sale_candidates.py` の外で行う。
本スクリプトは「Sheetsに1行書く」だけで完結する。


## 8. 受け入れ条件（47-C完了判定）

- [ ] tools/enqueue_sale_candidates.py が実装されている
- [ ] approved 候補 0件 のとき何も書かずに正常終了する
- [ ] YES 以外の入力でキャンセルされ Sheets が変更されない
- [ ] YES 入力後に Sheets へ 1件だけ NEW 書き込みが行われる
- [ ] 書き込まれた行の status = NEW で row_id が採番されている
- [ ] 2件目が書き込まれないことをサンプルで確認
- [ ] DRY_RUN モード（--dry-run フラグ）でも動作する（Sheets 未書き込み）
- [ ] 47-B の preview と同じバリデーション・skip判定が通る

## 9. 解禁条件

47-C の実装を開始するには以下が満たされていること:
- 47-B の DRY_RUN 正常動作が 3日連続確認済み
- Sheets 読み書き疎通確認済み（src/sheets.py が正常動作）
- 本設計書（本ファイル）がレビュー済み
