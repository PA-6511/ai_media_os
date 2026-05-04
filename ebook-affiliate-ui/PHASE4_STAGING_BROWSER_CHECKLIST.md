# 電子書籍アフィリエイト UI Flags Phase4 ステージング ブラウザ確認チェックリスト

本ドキュメントは、WordPress 本番反映前のブラウザ確認・リンク確認・ロールバック演習の実施項目と判定基準を定める。
本番 WordPress への更新は、本チェックリストの全項目 PASS 後、人間が明示的に承認した場合のみ実施する。

## ローカルステージング URL

```
http://127.0.0.1:8080/kobo-campaign-list-final-v3.html
```

起動コマンド（ebook-affiliate-ui/ で実行）:
```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

---

## 確認項目

### 1. PC 表示確認
- [ ] ページが正常に読み込まれる（タイムアウト・真っ白なし）
- [ ] タブ切り替え（全件 / 店舗別）が動作する
- [ ] ソート切り替えが動作する
- [ ] カラム切り替えが動作する

### 2. スマホ幅確認
- [ ] 幅 375px 前後でレイアウトが崩れない
- [ ] 横スクロールが発生しない

### 3. Console 致命エラー確認
- [ ] ブラウザ DevTools Console に red error がない
- [ ] campaign_items.json 読込エラーがない（Network タブで 200 を確認）
- [ ] loadUiFlags / applyUiFlagsToCard の実行エラーがない
- [ ] data-item-id 不一致警告がない（id mismatch warning が出ていない）

### 4. JSON 読込確認（ブラウザ側）
- [ ] Network タブで campaign_items.json が 200 で取得されている
- [ ] 10 件すべてのカードに ui_flags が反映されている

### 5. blink / urgent 表示確認
- [ ] blink 対象は kobo-003, kobo-007, kobo-005 の 3 件のみ点滅している
- [ ] blink が 4 件以上点滅していない（max-3 制限が有効）
- [ ] urgent 対象（7 件）が urgent スタイルで表示されている

### 6. manual_override 表示確認
- [ ] kobo-009 の manual_override は期限切れ・無効状態で AI 判断が優先されている
- [ ] override が有効な場合、override ラベルが表示される（該当なし時はスキップ）

### 7. アフィリエイトリンク遷移確認
- [ ] 各カードのリンクが別タブまたは対象 URL へ遷移する
- [ ] リンク先が 404 でない（代表 2 ～ 3 件を目視確認）
- [ ] rel="noopener noreferrer" が付与されている（DevTools Elements で確認）

### 8. PR / 広告表記確認
- [ ] アフィリエイト該当箇所に PR または広告の表記が確認できる

### 9. ロールバック演習
- [ ] campaign_items.json を意図的に壊した場合、ページが graceful に扱う（エラーで止まらない）
- [ ] JSON を元に戻した後、表示が正常に回復する
- [ ] 演習後、campaign_items.json を必ず元の内容に戻す

---

## 判定基準

| 状態 | 条件 |
|---|---|
| PASS | 全項目チェック済み・重大問題なし |
| Conditional Go | 軽微な指摘あり・本番反映前に対応予定として記録 |
| FAIL | Console 致命エラー・リンク 404・blink 超過など重大問題あり |

---

## 安全条件

- 自動投稿なし
- 自動削除なし
- 自動公開なし
- WordPress 本番更新なし
- 本番反映なし
- 本チェックリスト全項目 PASS および人間の明示的承認なしに本番反映は実施しない

---

## 現時点の状態

| 確認項目 | 状態 |
|---|---|
| HTML 配信 | PASS（http.server 確認済み） |
| JSON 配信 | PASS（http.server 確認済み） |
| JSON 件数 | PASS（10 件） |
| JSON/HTML ID 整合 | PASS（10 件一致） |
| blink max-3 | PASS |
| urgent 件数 | PASS（7 件） |
| manual_override | PASS（期限切れ・無効状態） |
| Console 確認 | 未実施 |
| リンク遷移確認 | 未実施 |
| ロールバック演習 | 未実施 |
| 本番反映 | 未実施 |
