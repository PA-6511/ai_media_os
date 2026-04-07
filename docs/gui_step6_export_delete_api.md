# Step6: export / delete 本API接続実装メモ

## 目的
- `exportBlock()` / `deleteBlock()` を本API優先で動作させる
- API 失敗時はモックへフォールバックし、既存 UI 動作を壊さない
- LockGuard 実行フローで成功時のみ再描画する形に最小整理する

---

## 対象関数

| 関数 | ファイル | 変更内容 |
|------|----------|----------|
| `exportBlock(blockId, authInfo)` | `ui/services/blockService.js` | 本API優先 + 失敗時 mock fallback |
| `executeLockGuardAction()` | `ui/script.js` | 成功時のみ再描画・リセット |

---

## 変更対象ファイル

- `ui/services/blockService.js`
- `ui/services/apiClient.js`（`postJson` 関数そのまま利用）
- `ui/script.js`
- `docs/gui_api_readiness_checklist.md`

---

## API 利用想定

- Export
  - メソッド: `POST`
  - パス: `/blocks/{id}/export`
  - body: `authInfo`（password / twoFactorCode / confirmationText / confirmed）
  - 成功判定: `response.success === true`

- Delete
  - メソッド: `DELETE /blocks/{id}` を第一候補
  - 互換: `POST /blocks/{id}/delete`（サーバー要件による）
  - body: `authInfo`（同上）
  - 成功判定: `response.success === true`

---

## fallback 方針

- `postJson()` が例外を投げた場合 → 既存 mock 処理へ落とす
- `response.success !== true` の場合 → message 表示のみ、再描画なし
- 認証失敗（`hasCompletedAuth` 不通過）→ 即 fail-safe return、API 呼ばない
- deleteBlock は現段階で mock fallback なし（blockService 本体は未変更）

---

## 確認項目

- [ ] `POST /api/blocks/{id}/export` がネットワークタブに記録される
- [ ] `DELETE /api/blocks/{id}` または互換 POST がネットワークタブに記録される
- [ ] confirmed 未チェック時は execute が中断される
- [ ] password / twoFactorCode / confirmationText 不足時は `success=false` で止まる
- [ ] 認証失敗時に block 状態が変化しない
- [ ] API 成功後に block 一覧/詳細/Dashboard/Audit Log が再描画される
- [ ] API 失敗時は message 表示のみ、LockGuard は開いたまま再入力できる
- [ ] 実行後に LockGuard の入力値が残らない

---

## まだやらないこと

- deleteBlock の本API接続（現状は mock のまま）
- export / delete の再試行導線
- Delete 成功後の block 表示除外仕様の確定
- Export 応答 shape の最終確定
- 認証情報の POST body 構成の最終調整（authInfo 全渡し vs 必要項目のみ）
- API 失敗時の自動再試行
---

## 全API通し確認（export / delete 危険操作）

### 通し確認手順

1. Export/Delete 管理ページで対象 block の Export ボタンを押す
2. LockGuard が開く（state = ready）ことを確認する
3. confirmed 未チェックのまま execute → 中断 + message 表示で止まることを確認する
4. 認証情報を不完全に入力して execute → fail-safe で止まることを確認する
5. 正しい認証情報を入力して execute → API が発行されることを確認する
6. 成功後に一覧/詳細/Dashboard/Audit Log が再描画されることを確認する
7. Delete ボタンで同様に手順 1～6 を繰り返す

### 確認項目

#### Export で LockGuard が開くか
- [ ] Export ボタン押下で LockGuard パネルが表示される（state = ready）
- [ ] LockGuard に対象 block 名とアクションタイプ（Export）が表示される
- [ ] cancel で LockGuard がリセットされる

#### Delete で LockGuard が開くか
- [ ] Delete ボタン押下で LockGuard パネルが表示される（state = ready）
- [ ] LockGuard に対象 block 名とアクションタイプ（Delete）が表示される
- [ ] cancel で LockGuard がリセットされる

#### 確認チェック未実施時に実行されないか
- [ ] confirmed 未チェックのまま execute → 中断 + message 表示
- [ ] block 状態が変化しない
- [ ] LockGuard が開いたまま再入力できる

#### 認証不足時に fail-safe で止まるか
- [ ] password 空欄のまま execute → `success=false` message 表示
- [ ] twoFactorCode 空欄のまま execute → `success=false` message 表示
- [ ] confirmationText 不一致のまま execute → `success=false` message 表示
- [ ] 認証失敗時に block の状態（deleteRequested 等）が変化しない

#### 成功時に一覧/詳細/ログが整合するか
- [ ] Export 成功後に一覧テーブルが再描画される
- [ ] Export 成功後に詳細パネルが再描画される
- [ ] Export 成功後に Audit Log に export 記録が追加される
- [ ] Delete 成功後に deleteRequested が一覧/詳細に反映される
- [ ] Delete 成功後に Dashboard の deleteRequestedBlocks カウントが増加する
- [ ] Delete 成功後に Audit Log に delete 記録が追加される
- [ ] 成功後に LockGuard の入力値がクリアされる

---

## 異常系確認（Export / Delete / LockGuard）

### 確認チェック未実施
- [ ] confirmed 未チェックのまま execute すると実行されない
- [ ] confirmed 未チェック時は message が表示される
- [ ] confirmed 未チェック時に block 状態が変化しない

### password 不足 / 不一致
- [ ] password 空欄で execute すると fail-safe で止まる
- [ ] password 不一致で execute すると fail-safe で止まる
- [ ] 失敗後に LockGuard が開いたまま再入力できる

### twoFactorCode 不足 / 不一致
- [ ] twoFactorCode 空欄で execute すると fail-safe で止まる
- [ ] twoFactorCode 不一致で execute すると fail-safe で止まる
- [ ] 失敗後に LockGuard が開いたまま再入力できる

### confirmationText 不一致
- [ ] confirmationText 不一致で execute すると fail-safe で止まる
- [ ] 失敗後に block 状態（deleteRequested 等）が変化しない
- [ ] 失敗後に LockGuard 入力値を修正して再実行できる

### Export 失敗
- [ ] Export API 失敗時に message が表示される
- [ ] Export 失敗時に一覧/詳細/Dashboard/Audit Log が不整合にならない
- [ ] Export 失敗時に再描画は走らず既存表示が維持される

### Delete 失敗
- [ ] Delete API 失敗時に message が表示される
- [ ] Delete 失敗時に deleteRequested が誤って更新されない
- [ ] Delete 失敗時に再描画は走らず既存表示が維持される

### fail-safe で止まるか
- [ ] lockguard state が `ready` 以外のとき service call せず停止する
- [ ] blockId/actionType 不正時に service call せず停止する
- [ ] success=false 応答時に LockGuard を閉じず再入力導線を維持する
- [ ] 例外発生時に UI 崩れなく message 表示のみで停止する

### message が適切か
- [ ] 入力不足時に確認不足/認証失敗を示す message が表示される
- [ ] Export 失敗時に export 失敗を示す message が表示される
- [ ] Delete 失敗時に delete 失敗を示す message が表示される
- [ ] 次操作時に message が適切に上書きされる