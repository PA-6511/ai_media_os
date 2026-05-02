# 運用マニュアル (OPERATION.md)

ai_media_os の日常運用・障害対応手順。

---

## 0. 42監視再カウントメモ（固定記録）

- 再カウント開始時刻（JST）: 2026-05-02 23:28:48
- 再カウント開始時刻（UTC）: 2026-05-02T14:28:48.117330+00:00
- 確認対象 row_id: TEST-CRON-001
- 確認済み post_id: 102
- 確認済み draft URL: https://hoshido.jp/?p=102
- 本線条件: 1日1回 / max-items=1 / draftのみ / publishなし
- Slack確認: 未確認 / 次回cron後に再確認（端末からは送信経路まで確認済み）

### 0-1. 42監視中に変更しない項目

- cron時刻
- MAX_ROWS_PER_RUN
- DRY_RUN / WP_DRY_RUN の運用方針
- publish関連ロジック
- 依存パッケージ更新

### 0-2. 異常時の停止手順

```bash
cd ~/ai_media_os

# 1) cron を一時停止（行頭に # を付与）
crontab -e

# 2) 走行中の本線プロセス停止
pkill -f "scripts/run_ai_post_queue.sh" || true
pkill -f "tools/run_single_row_real.py" || true

# 3) ロックファイルを除去
rm -f data/locks/*.lock
```

---

## 1. システム概要

| 項目 | 内容 |
|------|------|
| 役割 | マンガ・ライトノベルのセール情報記事を自動生成・WordPress 投稿 |
| 主要スクリプト | `scripts/run_ai_post_queue.sh`, `scripts/run_sale_end_check.sh` |
| 通知先 | Slack `#ai-media-os-alert` |
| ログ格納先 | `data/logs/` |

---

## 2. 日常確認手順

### 2-1. ログ確認

```bash
cd ~/ai_media_os

# 直近 50 行（デフォルト: pipeline_failures.log）
python tools/check_logs.py --lines 50

# ログ一覧確認
python tools/check_logs.py --list

# 特定ログ確認
python tools/check_logs.py --log sale_end_check --lines 100
python tools/check_logs.py --log ops_cycle --lines 100
```

### 2-2. セール終了チェック（手動実行）

```bash
cd ~/ai_media_os
# dry-run（Slack 通知なし）
bash scripts/run_sale_end_check.sh --dry-run

# 通常実行（Slack 通知あり）
bash scripts/run_sale_end_check.sh
```

**終了コード:**

| 終了コード | 意味 |
|-----------|------|
| `0` | セール終了アイテムなし（正常） |
| `1` | セール終了アイテムあり（要対応） |

### 2-3. 投稿キュー実行（手動）

> **前提:** `.env` に必須変数が設定済みであること。  
> 未設定の場合は起動時にエラーで停止する。

```bash
cd ~/ai_media_os
bash scripts/run_ai_post_queue.sh
```

---

## 3. 必須 .env 設定チェックリスト

DRY_RUN 検証・本番実行の前に以下を埋める。

| 変数名 | DRY_RUN で必要 | 説明 |
|--------|--------------|------|
| `SPREADSHEET_ID` | 必須 | 投稿キュー Google Spreadsheet ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 必須 | Sheets 認証サービスアカウント JSON |
| `OPENAI_API_KEY` | 必須 | AI 記事生成 API キー |
| `SLACK_WEBHOOK_URL` | 推奨 | Slack 通知 Webhook URL |
| `WP_BASE_URL` | 後でも可 | WordPress サイト URL |
| `WP_USER` | 後でも可 | WordPress ユーザー名 |
| `WP_APP_PASSWORD` | 後でも可 | WordPress アプリパスワード |

```bash
# 設定例
cat ~/ai_media_os/.env
```

---

## 4. 再起動・復旧手順

### 4-1. ロックファイルが残っている場合

```bash
ls ~/ai_media_os/data/locks/
rm ~/ai_media_os/data/locks/*.lock
```

### 4-2. ログローテート手動実行

```bash
cd ~/ai_media_os
python3 -m ops.run_log_rotate
```

### 4-3. 異常検知手動実行

```bash
cd ~/ai_media_os
python3 -m monitoring.run_anomaly_check
```

---

## 5. DRY_RUN → 本番の移行手順

1. `.env` の必須変数を実値に更新
2. `python3 scripts/diagnose_sheets.py` でシート接続確認
3. `python3 scripts/test_prompt_output.py` でプロンプト出力確認
4. `python3 scripts/run_single_row.py TEST-001` で 1 行 DRY_RUN 実行
5. WordPress 下書きが作成されていることを確認
6. 問題なければ cron 登録（[CRON.md](CRON.md) 参照）

---

## 6. ファイル構成

```
ai_media_os/
├── scripts/
│   ├── run_ai_post_queue.sh   # 投稿キュー実行スクリプト
│   ├── run_sale_end_check.sh  # セール終了チェックスクリプト
│   └── sale_end_check.py      # セール終了チェックロジック
├── tools/
│   └── check_logs.py          # ログ確認ツール
├── tests/
│   └── test_sale_end_check.py # sale_end_check テスト
├── docs/
│   ├── CRON.md                # cron 設定ガイド
│   ├── ENVIRONMENT.md         # 環境変数リファレンス
│   └── OPERATION.md           # 本ファイル
└── data/
    └── logs/                  # 各種ログファイル
```

---

## 7. Slack アラート対応フロー

| アラート内容 | 対応 |
|------------|------|
| `sale_ended` | `sale_end_check.py` のログで対象 work_id を確認 → 記事更新またはセール情報削除 |
| `pipeline_failure` | `check_logs.py --log pipeline_failures` でエラー内容確認 |
| `anomaly CRITICAL` | `check_logs.py --log anomaly_check` で原因特定 |

---

## 8. 関連ドキュメント

- [CRON.md](CRON.md) — cron ジョブ設定
- [ENVIRONMENT.md](ENVIRONMENT.md) — 環境変数詳細
