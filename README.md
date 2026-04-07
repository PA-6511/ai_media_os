# AI Media OS (Minimal Pipeline)

このリポジトリの最小ラインは以下です。

1. 作品DB/記事DBのセットアップ
2. キーワード生成
3. 検索意図解析
4. (任意) WordPress下書き投稿テスト

## ディレクトリ構成

- `core/database/db_setup.py`: DBテーブル作成とサンプル投入
- `core/database/db_utils.py`: data配下のパス管理とDB接続
- `core/keyword/keyword_generator.py`: worksからキーワード生成
- `core/intent/search_intent_analyzer.py`: キーワードの意図/記事タイプ判定
- `core/publisher/wordpress_publisher_test.py`: WP下書き投稿テスト
- `data/`: `media.db`, `keywords.json`, `intent_analysis.json` の保存先
- `main.py`: 1->2->3 を順番に実行

## 実行方法

```bash
cd /home/deploy/ai_media_os
python3 main.py
```

WordPress投稿テストは個別実行です。

```bash
export WP_URL="https://your-site.example.com"
export WP_USERNAME="your_user"
export WP_APP_PASSWORD="your_app_password"
python3 core/publisher/wordpress_publisher_test.py
```

## PowerShell 実行例

```powershell
cd C:\path\to\ai_media_os
python .\main.py

$env:WP_URL = "https://your-site.example.com"
$env:WP_USERNAME = "your_user"
$env:WP_APP_PASSWORD = "your_app_password"
python .\core\publisher\wordpress_publisher_test.py
```
