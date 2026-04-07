# Mock Server 確認手順

generated_at: `2026-03-15T12:08:23.703772+00:00`

このドキュメントは AI Media OS GUI mock server の
**正しい起動・確認・停止手順**をまとめたものです。

「起動後に Ctrl+C で止めてから curl してしまう」運用ミスを防ぐため、
foreground / background それぞれの手順を明記しています。

## ⛔ よくある誤操作（やってはいけないこと）

> **⚠️ 注意:** foreground 起動したターミナルで **Ctrl+C を押してから** 同じターミナルで `curl` を打っても、サーバーはすでに停止しているため `Connection refused` になります。

```
# ❌ 誤った操作の流れ
$ python3 -m gui.run_mock_server   # 同じターミナルで起動
^C                                 # ← Ctrl+C で停止してしまう
$ curl http://127.0.0.1:8766/health  # ← Connection refused
```

**正しい操作は「サーバーを起動したまま」別ターミナルから `curl` することです。**

## 方法 1: Foreground 起動（開発時推奨）

ログをリアルタイムで目視したい開発時に使います。
**ターミナルを 2 つ用意してください。**

### ターミナル 1 ── サーバー起動

> **💡 ポイント:** Ctrl+C は確認が終わるまで押さないでください。

```bash
cd ~/ai_media_os
python3 -m gui.run_mock_server
```

起動成功時の出力例:

```
============================================================
  MOCK SERVER READY
  final_port  : 8766
  server_url  : http://127.0.0.1:8766/
  pid         : 12345
  stop        : Ctrl+C or SIGTERM
============================================================
```

`final_port` の値（例: `8766`）を控えてください。
この値を以降の確認コマンドで使います。

### ターミナル 2 ── 確認コマンド（サーバーを止めずに実行）

> **⚠️ 注意:** ターミナル 1 の Ctrl+C は **確認がすべて終わるまで押さない**でください。

```bash
cd ~/ai_media_os

# 確定ポートの確認
cat data/reports/mock_server_runtime_latest.json

# ポートが LISTEN しているか確認
ss -ltnp | grep 8766

# 案内エンドポイント
curl http://127.0.0.1:8766/
curl http://127.0.0.1:8766/docs

# ヘルスチェック
curl http://127.0.0.1:8766/health

# JSON endpoint index
curl http://127.0.0.1:8766/api/index

# データ API
curl http://127.0.0.1:8766/api/home
curl http://127.0.0.1:8766/api/bootstrap
```

### ターミナル 1 ── 確認後の停止

確認がすべて終わったら、ターミナル 1 で:

```bash
# Ctrl+C を押す
```

## 方法 2: Background 起動（CI・長時間運用推奨）

ターミナルを 1 つで完結させたい場合や、
停止せず並行作業したい場合に使います。

### 起動

```bash
cd ~/ai_media_os
bash gui/run_mock_server_bg.sh
```

起動成功時の出力例:

```
============================================================
  MOCK SERVER BACKGROUND
  pid         : 12345
  final_port  : 8766
  server_url  : http://127.0.0.1:8766/
  log         : data/logs/mock_server.out
  pid_file    : data/run/mock_server.pid
  confirm:  curl http://127.0.0.1:8766/health
  stop:     bash gui/stop_mock_server.sh
============================================================
```

### 確認

```bash
cd ~/ai_media_os

# 確定ポートを runtime JSON から確認
cat data/reports/mock_server_runtime_latest.json

# ポートが LISTEN しているか確認
PORT=$(python3 -c "import json; print(json.load(open('data/reports/mock_server_runtime_latest.json'))['final_port'])")
ss -ltnp | grep $PORT

# ヘルスチェック
curl http://127.0.0.1:$PORT/health

# endpoint index
curl http://127.0.0.1:$PORT/api/index

# ログ確認
tail -20 data/logs/mock_server.out
```

### 停止

```bash
cd ~/ai_media_os
bash gui/stop_mock_server.sh
```

### PID 手動確認・手動停止

```bash
# PID の確認
cat data/run/mock_server.pid

# プロセスが生きているか確認
kill -0 $(cat data/run/mock_server.pid) && echo running || echo stopped

# 手動 SIGTERM（stop スクリプトと同等）
kill -TERM $(cat data/run/mock_server.pid)
```

## 確認観点チェックリスト

| 確認項目 | コマンド | 期待値 |
|---|---|---|
| ポート LISTEN | `ss -ltnp \| grep 8766` | `LISTEN 127.0.0.1:8766` が出る |
| runtime JSON 存在 | `cat data/reports/mock_server_runtime_latest.json` | `final_port` / `server_url` が入っている |
| ヘルスチェック | `curl .../health` | `{"ok": true}` |
| endpoint index | `curl .../api/index` | `endpoint_count` が 9 以上 |
| 案内ページ | `curl .../` | `available_endpoints` 一覧が返る |
| docs | `curl .../docs` | plain text で endpoint 一覧が返る |
| データ API | `curl .../api/home` | `ok: true` の JSON が返る |


## ポート競合が起きた場合

起動スクリプトは `8766` から順に `8775` まで自動的に空きポートを探します。
採用されたポートは必ず起動ログと `mock_server_runtime_latest.json` に記録されます。

```bash
# 実際に採用されたポートを確認
python3 -c "import json; d=json.load(open('data/reports/mock_server_runtime_latest.json')); print(d['server_url'])"

# スキップされたポートも確認可能
python3 -c "import json; d=json.load(open('data/reports/mock_server_runtime_latest.json')); print('skipped:', d['skipped_ports'])"
```

## トラブルシュート

### Connection refused が出る

1. サーバーがまだ起動していない → 起動ログで `MOCK SERVER READY` を確認
2. **Ctrl+C でサーバーを止めてから curl している** → サーバーを再起動してから別ターミナルで curl
3. ポートがずれている → `cat data/reports/mock_server_runtime_latest.json` で `final_port` を確認
4. プロセスが異常終了している → `cat data/logs/mock_server.out` でエラーを確認

### Ctrl+C を押してしまった後の復旧

```bash
# foreground の場合: そのまま再起動
python3 -m gui.run_mock_server

# background の場合
bash gui/stop_mock_server.sh  # 念のりにクリーンアップ
bash gui/run_mock_server_bg.sh
```

### サーバープロセスが残留している場合

```bash
# mock server プロセスをすべて確認
ps aux | grep run_mock_server | grep -v grep

# PID を指定して停止
kill -TERM <PID>
```

## 関連ファイル

| ファイル | 説明 |
|---|---|
| `gui/mock_server.py` | HTTP ハンドラ・エンドポイント定義 |
| `gui/run_mock_server.py` | foreground 起動エントリポイント |
| `gui/run_mock_server_bg.sh` | background 起動スクリプト |
| `gui/stop_mock_server.sh` | 停止スクリプト |
| `data/run/mock_server.pid` | 稼働中 PID（停止後は削除） |
| `data/logs/mock_server.out` | サーバーログ |
| `data/reports/mock_server_runtime_latest.json` | 確定ポート・URL（停止後は削除） |


*generated_at: 2026-03-15T12:08:23.703772+00:00*
