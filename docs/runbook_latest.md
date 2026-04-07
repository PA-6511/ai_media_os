# AI Media OS Runbook

- generated_at: 2026-03-14T00:26:04.429295+00:00
- target: AI Media OS ops/recovery/reporting command set

この Runbook は、障害時と定常点検で『まず何を打つか』を素早く判断するための最小手順書です。

## 日常点検

目的: 毎日の状態確認を短時間で実施する

1. 復旧一次確認サマリー

```bash
cd ~/ai_media_os
python3 -m ops.run_recovery_check
```

補足: 最新成果物・retry queue・anomaly・health score をまとめて確認

2. 成果物インデックス確認 (JSON)

```bash
cd ~/ai_media_os
python3 -m reporting.run_artifact_index --format json
```

補足: latest daily/monthly/dashboard/archive と件数を確認

3. 成果物インデックス確認 (HTML)

```bash
cd ~/ai_media_os
python3 -m reporting.run_artifact_index_html
```

補足: ブラウザ確認用 artifact_index_latest.html を再生成

## 運用サイクル実行

目的: 定常運用フローを一括実行する

1. ops cycle 実行

```bash
cd ~/ai_media_os
python3 -m ops.run_ops_cycle
```

補足: scheduler/smoke/anomaly/report/dashboard/archive/log_rotate を順次実行

2. 失敗時即停止で実行

```bash
cd ~/ai_media_os
python3 -m ops.run_ops_cycle --stop-on-error
```

補足: 障害調査時に失敗ステップで停止したい場合に使用

## 異常検知確認

目的: anomaly の状態を詳細確認する

1. anomaly check 実行

```bash
cd ~/ai_media_os
python3 -m monitoring.run_anomaly_check
```

補足: OK/WARNING/CRITICAL と alert 内容を確認

## retry queue 確認

目的: 未解決リトライの滞留を把握する

1. retry queue 一覧

```bash
cd ~/ai_media_os
python3 -m pipelines.show_retry_queue
```

補足: queued/retrying/resolved/give_up の件数を確認

## 日次レポート確認

目的: 日次の処理統計と成果物を確認する

1. 日次レポート表示

```bash
cd ~/ai_media_os
python3 -m reporting.show_daily_report
```

補足: 直近日次のサマリーを表示

2. 日次レポート生成

```bash
cd ~/ai_media_os
python3 -m reporting.run_daily_report
```

補足: 前日分をデフォルト生成

## 月次レポート確認

目的: 月次の統計レポートを確認・再生成する

1. 月次レポート生成 (対象月指定)

```bash
cd ~/ai_media_os
python3 -m reporting.run_monthly_report --month YYYYMM
```

補足: 対象月の monthly_report_YYYYMM.* を生成

## アーカイブ確認

目的: バックアップ生成状態と世代を確認する

1. アーカイブ作成

```bash
cd ~/ai_media_os
python3 -m ops.run_archive_backup
```

補足: data 配下の成果物バックアップを作成

2. アーカイブ検査

```bash
cd ~/ai_media_os
python3 -m ops.run_archive_inspect
```

補足: 最新 zip の中身と生成時刻を確認

## 復旧一次確認

目的: 障害時の初動確認を最短で行う

1. 復旧サマリー表示

```bash
cd ~/ai_media_os
python3 -m ops.run_recovery_check
```

補足: latest artifacts / retry / anomaly / health score を総覧

2. 復旧サマリー JSON 出力

```bash
cd ~/ai_media_os
python3 -m ops.run_recovery_check --format json
```

補足: Slack 連携や機械処理向け

## 運用メモ

- 失敗調査は run_recovery_check -> run_anomaly_check -> show_retry_queue の順で確認すると切り分けが速い。
- バックアップ未作成時は run_archive_backup 実行後に run_archive_inspect で検証する。
