# ebook-affiliate-ui (Phase0.5)

## 概要
楽天Koboキャンペーン一覧に対して、AI判断と manual_override による UI 強調表示を行う最小実装です。

## ディレクトリ構成
- `data/`: キャンペーンデータと UI フラグスキーマ
- `logs/`: manual_override の運用ログ(JSON Lines)
- `scripts/`: AI判定、override、CLI、dry-run 実行スクリプト
- `.vscode/`: VS Code タスク
- `kobo-campaign-list-final-v3.html`: 一覧UI本体
- `ui_flags_snippet.html`: HTMLへ貼り付けるCSS/JSスニペット

## dry-run コマンド
```bash
python3 scripts/run_ai_ui_judge.py
```

## manual_override CLI の使い方
```bash
python3 scripts/cli.py
```
- `1`: 一覧表示
- `2`: 推す（item_id + 6/24/48時間 + 理由必須）
- `3`: 解除（item_id + 理由）
- `0`: 終了

## ブラウザ確認方法
```bash
python3 -m http.server 8080
```
ブラウザで `http://localhost:8080/kobo-campaign-list-final-v3.html` を開いて表示を確認します。

## 安全条件
- 自動投稿なし
- 自動削除なし
- 自動公開なし
- WordPress本番更新なし
- UI表示フラグのみ変更
