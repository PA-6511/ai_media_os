# ai_media_os Core AI Runbook (Minimal)

## 事前確認
- 作業ディレクトリ: /home/deploy/ai_media_os
- Python: 3.10 以上を利用する
- 依存導入:
  - python3 -m pip install -r requirements.txt
- 主要設定ファイル:
  - config/core_runtime.json

## 起動前チェック
1. 依存ファイル確認
   - find . -maxdepth 2 \( -name "requirements.txt" -o -name "pyproject.toml" -o -name "Pipfile" -o -name "poetry.lock" \) | sort
2. 構文チェック
   - python3 -m py_compile $(find . -name "*.py")
3. テスト
   - pytest -q
4. 設定の安全値確認
   - config/core_runtime.json の retry.max_retry_count と logging.level を確認

## 通常起動手順
1. メインパイプライン実行
   - python3 main.py
2. dry run を明示したい場合
   - WP_DRY_RUN=1 python3 main.py

## 停止手順
1. フォアグラウンド実行時
   - Ctrl+C で停止
2. バックグラウンド実行時
   - ps -ef | grep "python3 main.py" で PID を確認し、kill <PID>

## retry queue 確認手順
1. 現在の queue 状態を表示
   - python3 pipelines/show_retry_queue.py
2. queued が増え続ける場合の再試行
   - WP_DRY_RUN=1 python3 pipelines/retry_failed_items.py
   - 問題なければ WP_DRY_RUN=0 python3 pipelines/retry_failed_items.py
3. give_up が出た場合
   - エラー内容を確認し、設定値または入力データを見直してから再実行

## freeze / 異常時対応
1. 症状確認
   - main.py 実行時の標準出力エラー
   - retry queue の give_up 件数
2. 一次切り分け
   - python3 -m py_compile $(find . -name "*.py")
   - pytest -q
   - config/core_runtime.json の変更差分確認
3. 一時回避
   - WP_DRY_RUN=1 で安全実行し、失敗パターンを特定
4. 復旧判断
   - 連続失敗や give_up 増加が続く場合は切り戻しを優先

## ログ確認手順
1. 失敗系ログ
   - tail -n 100 data/logs/pipeline_failures.log
2. 価格変動ログ
   - tail -n 100 data/logs/price_change.log
3. 新刊変動ログ
   - tail -n 100 data/logs/release_change.log
4. 複合シグナルログ
   - tail -n 100 data/logs/combined_signal.log

## 設定変更時の注意
1. config/core_runtime.json 変更前にバックアップ
2. 変更後は必ず py_compile と pytest -q を実行
3. retry 関連値は小さくしすぎない（max_retry_count は 1 以上）
4. logging.level は INFO を基準に、障害解析時のみ DEBUG を短期利用

## 切り戻し手順
1. 変更対象を特定
   - 設定変更のみか、コード変更を含むかを判定
2. 設定変更の切り戻し
   - バックアップした config/core_runtime.json を復元
3. コード変更の切り戻し
   - 直前安定版のコミットに戻す（Git 運用時）
4. 切り戻し後の健全性確認
   - python3 -m py_compile $(find . -name "*.py")
   - pytest -q
   - WP_DRY_RUN=1 python3 main.py

## 復元確認履歴
- 本セクションは、バックアップからの復元確認実施記録を残すために使用する。
- Go / Conditional Go 判定の根拠として扱う。
- 手順確認だけでなく、実復元の実施有無を明確に区別する。

### 記録ルール
各記録には、少なくとも以下を残す。
- 実施日
- 実施者
- 対象バックアップID
- 確認種別（手順確認 / 実復元）
- 所要時間
- 結果（成功 / 失敗）
- 課題 / 是正対応

### 記録テンプレート
- 実施日:
- 実施者:
- 対象バックアップID:
- 確認種別:
- 所要時間:
- 結果:
- 課題 / 是正対応:

### 初回記録
- 実施日: 2026-04-12
- 実施者:
- 対象バックアップID:
- 確認種別: 手順確認
- 所要時間:
- 結果:
- 課題 / 是正対応:
- 備考: 本運用開始後、2026-04-30 までに実復元を1回実施し、その結果を追記する（下記第2回記録で完了）

### 第2回記録（実復元）
- 実施日: 2026-04-12
- 実施者: 芦港
- 対象バックアップID: ops_archive_20260314_195353.zip
- 確認種別: 実復元
- 隔離先: /home/deploy/restore_test_20260412_201536（確認後削除済み）
- 所要時間: 約103秒（展開〜整合性確認〜クリーンアップまで）
- 結果: 成功
  - DB 5件（ai_media_os.db / media.db / price_history.db / publish_history.db / release_history.db）すべて展開・整合性確認（integrity=ok）
  - reports ファイル 46件 展開確認
  - ディレクトリ構成（data/reports / data/logs / data/test_outputs）確認
  - 本番上書きは行わず、隔離先で確認した
- 課題 / 是正対応: なし
- 備考: sqlite3 コマンド未インストールのため、Python sqlite3 モジュールで代替確認。整合性・テーブル存在確認ともに問題なし。

### 注意事項
- 実復元未実施の間は Go 判定にしない
- 記録を省略しない
- 課題が出た場合は、是正完了まで追記する

## 運用前チェック Top3
1. requirements.txt から依存を再インストールし、pytest が入ること
2. py_compile と pytest -q が通ること
3. retry queue 状態と主要ログ 4種を確認し、異常増加がないこと