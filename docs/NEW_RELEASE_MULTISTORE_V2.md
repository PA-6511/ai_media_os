# 新刊マルチストア入力V2

この機能は、楽天Kobo・DMMブックス・Amazon Kindle の新刊CSVを、外部通信なしで電子書籍アフィリエイト Block AI 向けの入力JSONへ変換するためのインポーターです。WordPress への書き込みや公開は行わず、人間確認前提の下書き入力素材だけを生成します。

CSV必須列は次の通りです。batch_id、item_id、title、release_date、category、rakuten_kobo_url、image_url、wordpress_status、schema_id、record_status、publish_ready、pr_required、price_notice_required、dmm_match_status、amazon_match_status、source_row_sha256。UTF-8 と UTF-8 BOM の両方に対応します。

楽天Kobo は必須ストアです。rakuten_kobo_url がない行は拒否され、正式 CTA には常に楽天KoboのURLを採用します。DMMブックスと Amazon Kindle は確定済みリンクだけをCTAへ採用し、未確認リンクは store_navigation にも HTML にも入れません。DMM の /latest/ URL は一覧・最新導線であり作品固有導線ではないため禁止します。DMM の確定状態は AUTO_APPROVED 系または MANUAL_VERIFIED 系です。

Amazon は affiliate URL を優先し、なければ item URL を使います。確定状態は MANUAL_VERIFIED、ASIN_LINK_GENERATED、AUTO_APPROVED、AUTO_APPROVED_MANUAL_LINK、および AUTO_APPROVED 系・MANUAL_VERIFIED 系の派生値です。Amazon URL が未入力でも、楽天Kobo が正常ならその行は通過できます。Amazon の手動確認が必要な場合は amazon_match_status を MANUAL_ASIN_REQUIRED、REVIEW_REQUIRED、NOT_FOUND のいずれかにし、必要なら amazon_asin を英数字10文字で補完してください。

実行コマンドは次です。

```bash
python3 scripts/import_new_release_multistore_v2.py 入力CSV --repo-root 一時ディレクトリ
python3 scripts/import_new_release_multistore_v2.py 入力CSV --repo-root 一時ディレクトリ --strict
```

`--strict` は blocked 行が1件でもある場合に終了コード 3 を返すための運用向けオプションです。終了コードは、正常時 0、CSV構造または入力ファイルエラー時 2、`--strict` 指定かつ blocked 行ありのとき 3 です。

出力先は repo_root 配下の exchange です。正常作品JSONは exchange/inputs/new_release/batches/<batch_id>/items/<item_id>.input.json、manifest は exchange/inputs/new_release/batches/<batch_id>/manifest.json、blocked 行は exchange/reviews/new_release/batches/<batch_id>.multistore_blocked.json、実行証跡は exchange/logs/<batch_id>.multistore_import_result.json に生成されます。blocked 行は blocked JSON を確認してください。

この処理は WordPress 書き込みを行いません。外部通信も行いません。生成物は人間確認後に別ランナーへ引き渡す前提です。この実装手順には git add、git commit、git push を含めません。