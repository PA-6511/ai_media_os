# 月次新刊コミック同期 V1 — 運用・復旧

## 処理内容

楽天ブックスのコミック発売日カレンダーを母集団にし、各公開商品ページから著者、出版社、レーベル、シリーズ、ISBN、発売日を補完する。既存の `CsvImportService` で SQLite に差分投入し、楽天Kobo、DMM、Kindle、書影の既存サービスをこの順で実行する。

公開商品ページの詳細は対象月ごとに7日間キャッシュする。日次実行では新しいカレンダー候補を取得しつつ、直近確認済みの詳細を再利用するため、同じ全件を毎日取り直さない。

- 同一の `source_name` / `source_item_id` は再作成しない。
- ISBN またはタイトル・巻数が他ソースと一致する候補は `REVIEW_REQUIRED` とし、作成・更新しない。
- 本文の書影カラムは既存の公式ストア書影ポリシーだけで更新する。楽天商品ページの `og:image` は監査用の候補 URL として保存し、転載・公開には使用しない。
- Kindle は既存のタイトル検索 API がないため、Amazon をスクレイピングせず、確認用検索 URL を証跡に残す。

## 手動運用

すべてリポジトリ直下で実行する。

Kobo/DMM等の認証情報は `/etc/ai-media-os/credential.env` から読み込む。手動の `--execute` 前には、値を表示せず次を実行して同じ環境を引き継ぐ。

```bash
set -a; . /etc/ai-media-os/credential.env; set +a
```

```bash
# 読取専用: 全候補、重複・差分、canonical CSV を確認する
.venv/bin/python scripts/run_monthly_comic_release_sync.py --month 2026-09 --phase plan

# 読取専用: 最初の100件を既存CSV取込ロジックで検証する
.venv/bin/python scripts/run_monthly_comic_release_sync.py --month 2026-09 --phase apply --sample-size 100 --detail-limit 100

# 初回100件: DBだけに確定投入する。ストア探索は実行しない。
/usr/bin/flock -n data/locks/monthly-comic-release-sync.lock \
  .venv/bin/python scripts/run_monthly_comic_release_sync.py --execute --month 2026-09 --phase apply --sample-size 100 --detail-limit 100

# 残りを含む全件: SQLite投入、Kobo/DMM/Kindle、書影確認を実行する。
/usr/bin/flock -n data/locks/monthly-comic-release-sync.lock \
  .venv/bin/python scripts/run_monthly_comic_release_sync.py --execute --month 2026-09 --phase all --detail-limit 1000 --detail-workers 3 --kobo-limit 1000 --dmm-limit 1000 --kindle-limit 1000 --cover-limit 1000

# DB投入済みの月について、外部ストア・書影だけを再開する。
# Kobo公式API未設定時はそのストアをSKIPPED_NOT_CONFIGUREDとして継続する。
/usr/bin/flock -n data/locks/monthly-comic-release-sync.lock \
  .venv/bin/python scripts/run_monthly_comic_release_sync.py --execute --month 2026-09 --phase enrich --detail-limit 0 --kobo-limit 1000 --dmm-limit 1000 --kindle-limit 1000 --cover-limit 1000
```

各runの `plan.json`、`result.json`、`canonical_import.csv` は `exchange/runtime/monthly_comic_release_sync/YYYY-MM/<run_id>/` に残る。確定投入前のSQLiteバックアップは `backups/monthly_comic_release_sync_<run_id>/ebook_affiliate_before.db` に残る。

## 自動実行

`ai-media-os-monthly-comic-release-sync.timer` は毎月1日 02:10（日本時間）に全同期を実行する。`ai-media-os-daily-comic-release-reconcile.timer` は毎朝8:00（日本時間）に同じ同期を実行し、月途中の新規、発売日、タイトル、巻数、出版社、レーベルの変更を差分適用する。Amazon Creators API の認証情報がある環境では Kindle も探索し、未設定時は要確認状態を記録して他ストアの処理を継続する。

配置後の有効化手順:

```bash
sudo install -m 0644 systemd/ai-media-os-monthly-comic-release-sync.service /etc/systemd/system/
sudo install -m 0644 systemd/ai-media-os-monthly-comic-release-sync.timer /etc/systemd/system/
sudo install -m 0644 systemd/ai-media-os-daily-comic-release-reconcile.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-media-os-monthly-comic-release-sync.timer ai-media-os-daily-comic-release-reconcile.timer
systemctl list-timers 'ai-media-os-*comic-release*'
```

## 障害時の復旧

1. `sudo systemctl stop ai-media-os-monthly-comic-release-sync.timer ai-media-os-daily-comic-release-reconcile.timer` で新規runを止める。
2. 対象runのバックアップを `sqlite3 <backup> 'PRAGMA integrity_check;'` で確認する。`ok` 以外なら復元しない。
3. DBを使用するプロセスを停止したうえで、バックアップを `data/database/ebook_affiliate.db` へ復元する。
4. 復元したバックアップが証跡migrationより前なら `.venv/bin/alembic upgrade f7b2c8d9e1a3` を実行する。
5. `--phase plan` で差分を確認してから、必要な範囲だけ再実行する。問題がなければtimerを再開する。

SQLiteファイルを直接置き換える復元は、必ずサービス停止とバックアップ整合性確認の後に行う。通常の再実行は source identity と差分判定により安全であり、DBファイルを復元する必要はない。
