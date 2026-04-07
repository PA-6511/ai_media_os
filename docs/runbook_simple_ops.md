# ai_media_os 簡易運用 Runbook

最終更新: 2026-04-07

この Runbook は、日常運用と障害初動で迷わないための最小手順です。詳細調査は別ドキュメントに譲り、ここでは実行優先で記載します。

## 0. 実行入口・主要ファイル・ログ場所

- 実行入口
  - `python3 ./main.py` (単体パイプライン実行)
  - `python3 -m ops.run_ops_cycle` (運用サイクル実行)
- 主要スクリプト
  - `testing/smoke_test_runner.py`
  - `pipelines/show_retry_queue.py`
  - `pipelines/retry_failed_items.py`
  - `ops/run_recovery_check.py`
  - `monitoring/run_anomaly_check.py`
- 主要設定
  - `config/ops_settings.json`
  - `config/core_runtime.json`
- ログ確認場所
  - `data/logs/ops_cycle.log`
  - `data/logs/smoke_test.log`
  - `data/logs/anomaly_check.log`
  - `data/logs/pipeline_failures.log`
  - `data/logs/scheduler.log`

## 1. 事前確認

```bash
cd /home/deploy/ai_media_os
python3 --version
python3 -m json.tool config/ops_settings.json >/dev/null
python3 -m json.tool config/core_runtime.json >/dev/null
```

問題がある場合:
- JSON 構文エラーは起動前に修正する。
- Python 実行不可の場合は運用を開始しない。

## 2. 起動前チェック

fail-safe のため、まず dry-run + 小件数で健全性を確認する。

```bash
cd /home/deploy/ai_media_os
WP_DRY_RUN=1 MAX_ITEMS=1 SAVE_PER_ITEM_FILES=0 python3 ./main.py
python3 -m ops.run_recovery_check
```

OK 判定の目安:
- `main.py` が例外終了しない。
- `python3 -m ops.run_recovery_check` が実行できる。

## 3. テスト実行

最低限の運用前テスト:

```bash
cd /home/deploy/ai_media_os
python3 -m testing.smoke_test_runner
python3 -m pytest -q tests/test_retry_policy.py tests/test_retry_queue_store.py tests/test_retry_failed_items.py tests/test_main_retry_paths.py tests/test_retry_audit_logs.py
```

判定:
- 1つでも FAIL があれば本番起動しない。

## 4. 通常起動手順

### 4-1. 単体パイプライン起動 (手動実行)

```bash
cd /home/deploy/ai_media_os
WP_DRY_RUN=0 python3 ./main.py
```

停止方法 (前景実行):
- `Ctrl + C`

### 4-2. 定常運用サイクル起動

```bash
cd /home/deploy/ai_media_os
python3 -m ops.run_ops_cycle
```

失敗箇所で即停止したい場合:

```bash
cd /home/deploy/ai_media_os
python3 -m ops.run_ops_cycle --stop-on-error
```

## 5. retry queue 確認手順

### 5-1. キュー滞留確認

```bash
cd /home/deploy/ai_media_os
python3 -m pipelines.show_retry_queue
```

確認ポイント:
- `queued` が増え続けていないか。
- `give_up` が発生していないか。

### 5-2. retry 実行 (fail-safe: 先に dry-run)

```bash
cd /home/deploy/ai_media_os
WP_DRY_RUN=1 RETRY_BATCH_LIMIT=5 python3 -m pipelines.retry_failed_items
```

本実行:

```bash
cd /home/deploy/ai_media_os
WP_DRY_RUN=0 RETRY_BATCH_LIMIT=5 python3 -m pipelines.retry_failed_items
```

## 6. freeze / 異常時対応

ここでの freeze は「処理が進まない/ハングする」状態を指す。

### 6-1. 初動 (止血)

```bash
cd /home/deploy/ai_media_os
pgrep -af "python3 -m ops.run_ops_cycle"
pgrep -af "python3 ./main.py"
pkill -TERM -f "python3 -m ops.run_ops_cycle"
pkill -TERM -f "python3 ./main.py"
```

`TERM` で停止しない場合のみ:

```bash
cd /home/deploy/ai_media_os
pkill -KILL -f "python3 -m ops.run_ops_cycle"
pkill -KILL -f "python3 ./main.py"
```

### 6-2. 影響確認

```bash
cd /home/deploy/ai_media_os
python3 -m ops.run_recovery_check
python3 -m monitoring.run_anomaly_check
python3 -m pipelines.show_retry_queue
```

### 6-3. 再開前 fail-safe

```bash
cd /home/deploy/ai_media_os
WP_DRY_RUN=1 MAX_ITEMS=1 SAVE_PER_ITEM_FILES=0 python3 ./main.py
```

これが成功してから本実行へ戻す。

## 7. ログ確認手順

直近ログの確認:

```bash
cd /home/deploy/ai_media_os
tail -n 120 data/logs/ops_cycle.log
tail -n 120 data/logs/smoke_test.log
tail -n 120 data/logs/anomaly_check.log
tail -n 120 data/logs/pipeline_failures.log
tail -n 120 data/logs/scheduler.log
```

エラー行の横断確認:

```bash
cd /home/deploy/ai_media_os
grep -Rin "CRITICAL\|ERROR\|Traceback\|FAIL" data/logs
```

## 8. 設定変更時の注意

変更対象:
- `config/ops_settings.json`
- `config/core_runtime.json`

変更前に必ずバックアップ:

```bash
cd /home/deploy/ai_media_os
TS=$(date +%Y%m%d_%H%M%S)
cp config/ops_settings.json "config/ops_settings.json.bak.${TS}"
cp config/core_runtime.json "config/core_runtime.json.bak.${TS}"
```

変更後の確認:

```bash
cd /home/deploy/ai_media_os
python3 -m json.tool config/ops_settings.json >/dev/null
python3 -m json.tool config/core_runtime.json >/dev/null
WP_DRY_RUN=1 MAX_ITEMS=1 SAVE_PER_ITEM_FILES=0 python3 ./main.py
python3 -m testing.smoke_test_runner
```

## 9. 切り戻し手順

症状: 設定変更後に異常増加、retry 滞留急増、主要テスト失敗。

### 9-1. 即時停止

```bash
cd /home/deploy/ai_media_os
pkill -TERM -f "python3 -m ops.run_ops_cycle"
pkill -TERM -f "python3 ./main.py"
```

### 9-2. 設定ファイル切り戻し

```bash
cd /home/deploy/ai_media_os
ls -1t config/ops_settings.json.bak.* | head -n 1
ls -1t config/core_runtime.json.bak.* | head -n 1
cp "$(ls -1t config/ops_settings.json.bak.* | head -n 1)" config/ops_settings.json
cp "$(ls -1t config/core_runtime.json.bak.* | head -n 1)" config/core_runtime.json
```

### 9-3. 切り戻し後の健全性確認

```bash
cd /home/deploy/ai_media_os
python3 -m json.tool config/ops_settings.json >/dev/null
python3 -m json.tool config/core_runtime.json >/dev/null
WP_DRY_RUN=1 MAX_ITEMS=1 SAVE_PER_ITEM_FILES=0 python3 ./main.py
python3 -m ops.run_recovery_check
python3 -m pipelines.show_retry_queue
```

### 9-4. 再開

```bash
cd /home/deploy/ai_media_os
python3 -m ops.run_ops_cycle --stop-on-error
```

## 10. 運用開始前チェック項目 (短縮版)

- [ ] 設定 JSON 2ファイルの構文チェック済み
- [ ] dry-run (`WP_DRY_RUN=1 MAX_ITEMS=1`) 成功
- [ ] smoke test 成功
- [ ] retry queue に `give_up` がない (または原因把握済み)
- [ ] 直近ログに `CRITICAL` / `Traceback` の未解決エラーがない
- [ ] 切り戻し用バックアップ (bak) を作成済み
