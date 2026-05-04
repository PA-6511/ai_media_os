# SALE_WATCHLIST_48A_DESIGN

## 0. 目的と前提

本文書は 48-A「セール待ち商品保存ページ」の設計仕様である。

目的:
- セールになったら紹介したい作品を事前に保存しておく
- 47-C（手動承認付き1件投入）と将来接続し、保存済み作品を投稿キューへ昇格させる
- 運営者が手動でデータを登録・管理する（自動収集はしない）

前提:
- 本フェーズは設計のみ。実装は 47-C 完了後に判断する
- 一般ユーザー公開はしない（運営者専用管理ページ）
- 自動クロール・自動投入・自動公開は禁止


## 1. データスキーマ（wait_item）

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| wait_id | string | ○ | sha1先頭12桁（store + work_title + product_url） |
| work_title | string | ○ | 作品名 |
| store | string | ○ | rakuten_kobo / dmm_books / kindle_amazon |
| product_url | string | ○ | 商品ページURL |
| desired_discount | string | − | 希望割引条件（例: 30%OFF以上） |
| desired_point | string | − | 希望還元条件（例: ポイント20%以上） |
| priority | string | − | high / normal / low（デフォルト: normal） |
| memo | string | − | 自由記述メモ |
| status | string | ○ | waiting / candidate / approved / drafted / ignored |
| created_at | string | ○ | ISO8601 UTC |
| updated_at | string | ○ | ISO8601 UTC |

wait_id 生成ルール:
- 正規化キー = store + work_title + product_url
- sha1(正規化キー).hexdigest()[:12]

status 遷移:
```
waiting   → candidate（セール候補になった）
candidate → approved（人間が手動承認）
approved  → drafted（run_single_row_real.py で draft 生成済み）
waiting   → ignored（登録取り消し）
candidate → ignored（見送り）
```


## 2. 保存形式

推奨保存先:
- data/sale_watchlist/

推奨ファイル:
- data/sale_watchlist/watchlist.json（全件・1ファイル管理）

JSON構造:
```json
[
  {
    "wait_id": "a1b2c3d4e5f6",
    "work_title": "サンプル作品タイトル",
    "store": "rakuten_kobo",
    "product_url": "https://www.kobo.com/jp/ja/ebook/XXXXX",
    "desired_discount": "30%OFF以上",
    "desired_point": "",
    "priority": "high",
    "memo": "人気シリーズ。セール時に即紹介したい",
    "status": "waiting",
    "created_at": "2026-05-04T00:00:00+00:00",
    "updated_at": "2026-05-04T00:00:00+00:00"
  }
]
```


## 3. 重複防止ルール

- wait_id 一致で重複と判定
- 同一 store + work_title + product_url の組み合わせは1件のみ登録可
- ignored 状態のものも重複カウントする（再登録は手動で status を戻す）


## 4. 47-C との連携設計（将来）

連携フロー（48-D 以降で実装）:
```
watchlist.json の status=candidate 一覧
↓
人間がレビュー → status=approved に変更
↓
enqueue_sale_candidates.py の入力として渡す
↓
Sheets 投稿キューに status=NEW で1件書き込み
↓
run_single_row_real.py で draft 生成
↓
status=drafted に更新
```

candidate_id との対応:
- wait_id と candidate_id は別物（生成キーが異なる）
- 連携時は work_title + store + sale_end_date で突合する


## 5. フェーズ構成

| フェーズ | 内容 | 実装タイミング |
|---|---|---|
| 48-A | 設計（本文書） | 完了 |
| 48-B | 静的プレビューHTML作成 | 43安定確認後 |
| 48-C | 管理用保存スクリプト実装 | 47-C完了後 |
| 48-D | 投稿キュー連携実装 | 48-C安定後 |
| 48-E | セール自動検知・通知 | さらに後段 |


## 6. 禁止事項（48-A時点）

- 自動クロール・自動収集
- 自動での candidate 昇格
- 自動での approved 設定
- 自動投稿キュー投入
- 複数件まとめ処理
- 自動公開
- 一般ユーザー向け公開ページ化
- cron連携


## 7. 受け入れ条件（48-A完了判定）

- [x] データスキーマが定義されている
- [x] status 遷移が定義されている
- [x] 重複防止ルールが定義されている
- [x] 保存形式が定義されている
- [x] 47-C との連携フローが設計されている
- [x] フェーズ構成と禁止事項が明記されている
