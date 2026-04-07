# Step3: 接続/切断系 本API接続実装メモ

## 目的

- `connectBlock()` / `disconnectBlock()` を本API前提で安定動作させる
- mock 依存を残しつつ、API 成功時は API 応答で動かす
- 失敗時は既存 mock 更新へフォールバックし、UI 崩れを防ぐ

---

## 対象関数

| 関数 | ファイル |
|------|---------|
| `connectBlock(blockId)` | `ui/services/blockService.js` |
| `disconnectBlock(blockId)` | `ui/services/blockService.js` |
| `postJson(path)` | `ui/services/apiClient.js` |

---

## 変更対象ファイル

- `ui/services/blockService.js` — `connectBlock()` を API try/catch + fallback 形式に書き換え
- `ui/services/apiClient.js` — `postJson()` が未定義の場合は追加

---

## API 利用想定

```
POST /blocks/{blockId}/connect
POST /blocks/{blockId}/disconnect
```

- リクエストボディ: なし（blockId は path parameter）
- 成功レスポンス想定: `{ success: true, block: { ... } }`
- 失敗レスポンス想定: `{ success: false, message: "..." }`

Step3 実装では `postJson(path, body = {})` を使うため、body 未指定時も `{}` が JSON で送信される。

### Step3 確認用メモ

- connect 送信先: `POST /blocks/{id}/connect`
- disconnect 送信先: `POST /blocks/{id}/disconnect`
- request body: 未指定でも `{}` が送信される
- Network タブ: Request URL / Method / Payload / Response を確認
- Console: `POST /blocks/{id}/connect failed:` / `POST /blocks/{id}/disconnect failed:` の有無を確認

---

## fallback 方針

- API 呼び出し成功（`success: true`）: API 応答の block を使って返却
- API 呼び出し失敗 / 例外発生: mock 配列を直接更新してフォールバック返却
- 失敗時に message へ表示し、UI 状態変更は行わない方針と整合させる

```
try {
  // postJson → APIレスポンス取得
  // success: true → API応答のblockを返却
  // success: false → fallback
} catch {
  // 例外 → fallback (mock更新)
}
```

---

## 確認項目

### POST 疎通確認

#### 1. POST /blocks/{id}/connect

**Network タブ確認**
- [ ] ブラウザ DevTools → Network タブを開く
- [ ] 接続ボタン押下
- [ ] Request header に `POST /api/blocks/{id}/connect` が表示される（実際の id 値に置換）
- [ ] Request Payload が `{}`（body 未指定時）または指定 body になっている
- [ ] `Content-Type: application/json` を確認

**Console 確認**
- [ ] エラーが表示されないか確認
- [ ] `POST /blocks/{id}/connect failed:` が出ていない

**レスポンス確認（Network タブ）**
- [ ] Response ペインで `{ "success": true, "block": { ... } }` または `{ "success": false, "message": "..." }` を確認

#### 2. POST /blocks/{id}/disconnect

**Network タブ確認**
- [ ] ブラウザ DevTools → Network タブを開く
- [ ] 切断ボタン押下
- [ ] Request header に `POST /api/blocks/{id}/disconnect` が表示される（実際の id 値に置換）
- [ ] Request Payload が `{}`（body 未指定時）または指定 body になっている
- [ ] `Content-Type: application/json` を確認

**Console 確認**
- [ ] エラーが表示されないか確認
- [ ] `POST /blocks/{id}/disconnect failed:` が出ていない

**レスポンス確認（Network タブ）**
- [ ] Response ペインで `{ "success": true, "block": { ... } }` または `{ "success": false, "message": "..." }` を確認

### UI 反映確認

- [ ] `connectBlock(blockId)` の返り値で `source: "api"` または `source: "fallback"` を確認できる
- [ ] 接続成功時に `block.connectionStatus` が `connected` へ更新される
- [ ] 接続成功時に `block.handshakeStatus` が API 応答または既存状態と整合している
- [ ] API 失敗時でも fallback で `block.connectionStatus` が更新され、`apiSuccess: false` が確認できる
- [ ] `message` が返り、成功時と fallback 時の判別材料になる
- [ ] `disconnectBlock(blockId)` の返り値で `source: "api"` または `source: "fallback"` を確認できる
- [ ] 切断成功時に `block.connectionStatus` が `disconnected` へ更新される
- [ ] 切断成功時に `block.handshakeStatus` が API 応答または既存状態と整合している
- [ ] API 失敗時でも fallback で `block.connectionStatus` が更新され、`apiSuccess: false` が確認できる
- [ ] 切断時も `message` が返り、成功時と fallback 時の判別材料になる
- [ ] 接続成功時に Block 一覧 / Block 詳細 / Dashboard / 接続/切断管理 / Audit Log / message が再描画される
- [ ] 切断成功時に Block 一覧 / Block 詳細 / Dashboard / 接続/切断管理 / Audit Log / message が再描画される
- [ ] 接続/切断失敗時でも UI が崩れず、既存表示を維持したまま message が確認できる
- [ ] message が接続/切断結果に応じて適切に表示される
- [ ] API 成功時に一覧・詳細・Dashboard・接続/切断管理・Audit Log・message が再描画される
- [ ] API 失敗時に UI が崩れず、message のみ表示される
- [ ] handshake 状態表示が接続/切断後に更新される
- [ ] 二重実行防止が維持される
- [ ] `getBlocks()` / `getBlockById()` / `disconnectBlock()` に回帰影響がない

---

## まだやらないこと

- freeze / unfreeze の本API接続
- export / delete の本API接続（認証付き）
- audit log / settings の本API接続
- handshake API (`POST /blocks/{id}/handshake`) の本格接続
- postJson のリトライ・タイムアウト制御

---

## Step3 実動確認結果

### 実動確認日

- [ ] yyyy-mm-dd

### 成功した確認項目

- [ ] `POST /blocks/{id}/connect` の送信を確認
- [ ] `POST /blocks/{id}/disconnect` の送信を確認
- [ ] request body が `{}` または想定どおりの JSON であることを確認
- [ ] 接続成功時に `connectionStatus` が更新されることを確認
- [ ] 切断成功時に `connectionStatus` が更新されることを確認
- [ ] 接続成功時に一覧 / 詳細 / Dashboard / 接続管理 / Audit Log / message の再描画を確認
- [ ] 切断成功時に一覧 / 詳細 / Dashboard / 接続管理 / Audit Log / message の再描画を確認

### 未確認項目

- [ ] 接続失敗時の fallback 動作
- [ ] 切断失敗時の fallback 動作
- [ ] handshakeStatus の整合確認
- [ ] Console に未処理例外が残らないこと

### 発見した課題

- [ ] API success=false 時の message 文言
- [ ] fallback 継続条件の明確化
- [ ] handshake 更新タイミングの最終確認
- [ ] 再描画後の表示整合差分の確認

### 次に見るポイント

- [ ] `source: "api" / "fallback"` の確認結果整理
- [ ] `apiSuccess` / `apiMessage` の実測確認
- [ ] handshakeStatus の `pending / success / failed` 遷移確認
- [ ] 失敗時の message と UI 維持の整合確認

---

## 全API通し確認（一覧→詳細→接続/切断）

### 通し確認手順

1. ページを開き、`GET /blocks` が発行されて一覧が表示される
2. block 行の「詳細」ボタンを押し、`GET /blocks/{id}` が発行されて詳細パネルが更新される
3. block 行または接続/切断管理パネルの Connect ボタンを押す
4. Connect 後に一覧・詳細・接続管理パネル・Dashboard・Audit Log が整合して再描画される
5. 同じ block で Disconnect ボタンを押す
6. Disconnect 後に同様に整合して再描画される

### 確認項目

#### 一覧表示後に詳細へ遷移できるか
- [ ] 一覧テーブルの「詳細」ボタンで詳細パネルが開く
- [ ] 別の block を選択すると詳細が切り替わる
- [ ] 詳細パネルに connectionStatus / freezeStatus / handshakeStatus が表示される

#### Connect 後に整合するか
- [ ] 一覧の connectionStatus chip が `connected` に更新される
- [ ] 詳細パネルの connectionStatus が `connected` に更新される
- [ ] 接続/切断管理パネルの connectionStatus が `connected` に更新される
- [ ] Dashboard の connectedBlocks カウントが増加する
- [ ] Audit Log に connect 記録が追加される
- [ ] message に接続結果が表示される

#### Disconnect 後に整合するか
- [ ] 一覧の connectionStatus chip が `disconnected` に更新される
- [ ] 詳細パネルの connectionStatus が `disconnected` に更新される
- [ ] 接続/切断管理パネルの connectionStatus が `disconnected` に更新される
- [ ] Dashboard の disconnectedBlocks カウントが増加する
- [ ] Audit Log に disconnect 記録が追加される
- [ ] message に切断結果が表示される

#### message が適切に更新されるか
- [ ] Connect 成功時に成功 message が表示される
- [ ] Connect 失敗時（API 失敗 / fallback）に操作結果 message が表示される
- [ ] Disconnect 成功時に成功 message が表示される
- [ ] 別操作を実行すると message が上書きされる

#### 接続/切断管理パネルの Connect/Disconnect ボタンが機能するか
- [ ] 接続管理パネルの Connect ボタンで `connect-management` アクションが発火する
- [ ] 接続管理パネルの Disconnect ボタンで `disconnect-management` アクションが発火する
- [ ] 管理パネルのボタンからの操作後も一覧・詳細が再描画される
