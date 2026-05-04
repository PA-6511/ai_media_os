# 電子書籍アフィリエイト UI Flags プロトタイプ v1 リリースノート

## 1. タイトル
電子書籍アフィリエイト UI Flags プロトタイプ v1

## 2. 対象リポジトリ
- PA-6511/ai_media_os
- ブランチ: main

## 3. 対象コミット
- e632e8d2da19644d452fe410fa43f3754c5709ed
- メッセージ: Expand ebook affiliate UI flags sample data

## 4. 到達点（Phase0.5〜Phase1.6）
- UI Flags 基盤を実装し、ローカル検証・GitHub保存・remote再取得確認まで完了
- 3件サンプルから10件データ構造へ拡張
- JSON/HTML連携と安全運用ルールを固定

## 5. 実装済み機能
- AI判断による urgent / blink 付与
- blink 最大3件制限
- manual_override（6h/24h/48h、理由必須、上限管理）
- JSON Lines ログ記録
- UI反映（is-urgent / is-blink / is-ai-push / is-manual-push）
- タブ、並び替え、列数切替の維持
- campaign_type 追加と複数ストア対応

## 6. 検証済み項目
- Python構文チェック PASS
- dry-run PASS
- campaign_items.json 10件 PASS
- HTML data-item-id 10件 PASS
- JSON/HTML ID一致 PASS
- campaign_type 全件存在 PASS
- store / campaign_type 種別一致 PASS
- manual_override 優先 PASS
- 解除後AI復帰 PASS
- remote main 再取得整合 PASS

## 7. 安全条件
- 自動投稿なし
- 自動削除なし
- 自動公開なし
- WordPress本番更新なし
- 本番公開未実行

## 8. 未実施項目
- 本番公開
- WordPress/Cocoon への本番反映
- 運用監視の長期運転

## 9. 次フェーズ候補
- Phase1.8: 本番反映前の最終チェックシート作成
- Phase1.9: WordPress/Cocoon移植手順の確定
- Phase2.0: 限定公開での運用観測
