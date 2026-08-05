# NEW_RELEASE_MULTISTORE_APP

## アプリの用途
新刊マルチストア入力V2のCSVをローカルで検証し、明示確認後のみBlock AI向けインポート成果物を生成するためのローカルWebアプリです。ZIP展開は使わず、既存リポジトリ上で直接運用します。

## 起動コマンド
```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/new_release_multistore_app.py \
  --repo-root /home/deploy/ai_media_os
```

既定URLは http://127.0.0.1:8765/ です。

## VS Code Remote-SSHで8765番を転送する方法
1. VS CodeでRemote-SSH接続を開いた状態にする。
2. Portsビューで `Forward a Port` を選択する。
3. `8765` を入力して転送する。
4. ローカル側で表示された転送URLをブラウザで開く。

## 収集CSVの使い方
1. 画面で `収集CSV` を選択。
2. `.csv` ファイルを選択。
3. `事前検証ボタン` を押して検証結果を確認。

## 手動調整CSVの使い方
1. 画面で `手動調整CSV` を選択。
2. `.csv` ファイルを選択。
3. `事前検証ボタン` を押して検証結果を確認。

## 事前検証画面の表示項目
事前検証後は次を表示します。

- 検証状態
- CSV構造エラー一覧
- 不足必須列一覧
- 未知列一覧
- 検出したschema_id
- 読み込んだデータ行数
- インポート可能かどうか

構造エラーがある場合は、修正方針の目安を画面上で確認できます。

## 旧LS-NEW-BATCH形式の検出とV2変換プレビュー
- ファイル名に `ls_new_batch_input` が含まれる場合、または旧形式ヘッダ候補を満たす場合は旧形式候補として扱います。
- 旧形式候補の場合、`V2形式へ変換プレビュー` ボタンを表示します。
- 変換プレビューは元CSVを上書きせず、UTF-8 BOM付きCSVを `converted_v2.csv` としてダウンロードできます。
- 変換後CSVは既存エンジン (`import_multistore_csv`) で再検証します。

固定補完値:

- `schema_id = NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2`
- `wordpress_status = draft`
- `record_status = READY_FOR_DRAFT`
- `publish_ready = true`
- `pr_required = true`
- `price_notice_required = true`
- `dmm_match_status = NOT_FOUND`
- `amazon_match_status = NOT_FOUND`
- `edition_type = volume`

`source_row_sha256` が欠落している場合は、元行の正規化文字列からSHA-256を生成します。

必須値を補完できない行は `REQUIRES_REVIEW` として変換プレビューに表示し、正常行には含めません。

## CP932対応
- 手動調整CSVでは `UTF-8` / `UTF-8 BOM` / `CP932` を受け付けます。
- CP932を検出した場合は、元ファイルを変更せずに `/tmp/multistore_app_*` 配下の一時ファイルへUTF-8 BOM形式で変換します。

## テンプレートCSVの使い方
画面の `手動調整用テンプレートCSVの取得` からUTF-8 BOM付きテンプレートCSVをダウンロードできます。

## 事前検証と成果物書き込み
- 事前検証ではリポジトリ成果物を書き込みません。
- `Block AIへインポートボタン` 押下時のみ、明示確認チェック成立を条件にJSON成果物を生成します。
- `ready_count >= 1` かつ正式な `batch_id` を確認できる場合のみインポートを有効化します。

## セキュリティと実行制約
- WordPressへの書き込み・公開は行いません。
- 外部通信は行いません。
- 127.0.0.1にのみバインドし、グローバルIPへ直接公開しません。
- 操作時はトークン検証を行います。
- `git add` / `git commit` / `git push` を自動実行しません。

## 停止方法
ターミナルで `Ctrl+C` を押してください。