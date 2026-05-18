# CRON 設定ガイド

ai_media_os の定期実行スケジュール（crontab 設定例）。

## 前提

| 項目 | 値 |
|------|----|
| 実行ユーザー | `deploy` |
| プロジェクトルート | `~/ai_media_os` |
| Python | `/usr/bin/python3` |
| ログ出力先 | `~/ai_media_os/data/logs/` |

## crontab 設定方法

```bash
crontab -e
```

## 現在の本番登録（2026-05-18 時点）

現在の ai_media_os 本線 cron 登録行:

```cron
# AI 投稿キュー処理（毎朝 8:10）
10 8 * * * cd /home/deploy/ai_media_os && WP_DRY_RUN=0 bash scripts/run_ai_post_queue.sh --max-items 1 >> logs/ai_post_queue_cron.log 2>&1

# 公開前下書きチェック（毎日 02:00 / Phase 47-C-2-a / 観測期間: 2026-05-18～）
0 2 * * * cd /home/deploy/ai_media_os && python3 tools/check_wp_draft_prepublish.py report --output reports/draft_check_$(date +\%Y\%m\%d).json >> logs/draft_check.log 2>&1
```

これらの設定は以下の監視条件として固定する：

**AI 投稿キュー**
- 1日1回 / 1件処理上限 / draftのみ運用の監視条件として固定

**公開前下書きチェック**
- 毎日 02:00 実行（report 生成のみ）
- Slack 通知なし（観測期間: 3～5日）
- WARN/FAIL 率、誤検知率を収集

## 初期運用プロファイル（固定）

cron の初期運用は次を固定する。

- 実行時刻: 毎日 08:10
- 処理件数: 1件上限（`--max-items 1`）
- 運用モード: draft 止まり（自動公開なし）
- 通知: Slack 到達を毎回確認

3日連続で次を満たすまでは件数・頻度を増やさない。

- cron log に異常終了がない
- Sheets の対象行が `DRAFTED`
- Phase2 health check が `result: OK`
- `ERROR` 行が増えない

## 42監視中チェック

- 42再カウント開始: 2026-05-02 23:28:48 JST
- 監視完了判定時刻: 2026-05-03 23:28:48 JST 以降
- 監視ログ: logs/ai_post_queue_cron.log
- ベースライン対象: TEST-CRON-001, post_id=102

### 異常時の停止

```bash
cd ~/ai_media_os
crontab -e
pkill -f "scripts/run_ai_post_queue.sh" || true
pkill -f "tools/run_single_row_real.py" || true
rm -f data/locks/*.lock
```

## 参考（将来拡張案）

以下は将来拡張時の参考例。初期運用フェーズでは適用しない。

```cron
# -------------------------------------------------------
# ai_media_os cron jobs
# -------------------------------------------------------
SHELL=/bin/bash
MAILTO=""

# === AI 投稿キュー ===
# 毎朝 6:00 に AI 記事生成・WordPress 投稿を実行
0 6 * * * cd ~/ai_media_os && bash scripts/run_ai_post_queue.sh >> data/logs/cron_post_queue.log 2>&1

# === セール終了チェック ===
# 毎朝 7:00 にセール終了アイテムを検出して Slack 通知
0 7 * * * cd ~/ai_media_os && bash scripts/run_sale_end_check.sh >> data/logs/cron_sale_end_check.log 2>&1

# === 運用サイクル ===
# 毎朝 8:00 に異常検知・KPI スナップショット・ログローテートを実行
0 8 * * * cd ~/ai_media_os && python3 -m ops.run_ops_cycle >> data/logs/cron_ops_cycle.log 2>&1

# === 異常検知 ===
# 毎時 00 分に異常チェック
0 * * * * cd ~/ai_media_os && python3 -m monitoring.run_anomaly_check >> data/logs/cron_anomaly_check.log 2>&1
```

## スケジュール一覧

| ジョブ | スクリプト | 実行タイミング | 外部接続 |
|--------|-----------|--------------|---------|
| AI 投稿キュー | `scripts/run_ai_post_queue.sh` | 毎朝 6:00 | Sheets / OpenAI / WP |
| セール終了チェック | `scripts/run_sale_end_check.sh` | 毎朝 7:00 | Slack のみ |
| 運用サイクル | `ops/run_ops_cycle.py` | 毎朝 8:00 | Slack |
| 異常検知 | `monitoring/run_anomaly_check.py` | 毎時 | Slack |

## 環境変数

cron 環境では `.env` から自動読み込みされる。  
各シェルスクリプト冒頭の `source .env` が機能する。

```
~/ai_media_os/.env に以下を設定
SPREADSHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_JSON=...
OPENAI_API_KEY=...
SLACK_WEBHOOK_URL=...
WP_BASE_URL=...
WP_USER=...
WP_APP_PASSWORD=...
```

## ログ確認

```bash
# 直近 50 行を確認
cd ~/ai_media_os
python tools/check_logs.py --lines 50
python tools/check_logs.py --log sale_end_check --lines 100
python tools/check_logs.py --list
```

## cron 動作確認

設定後、手動でジョブを実行してログを確認する。

```bash
cd ~/ai_media_os

# セール終了チェック（dry-run）
bash scripts/run_sale_end_check.sh --dry-run

# 投稿キュー（必須 .env 設定後）
bash scripts/run_ai_post_queue.sh
```
