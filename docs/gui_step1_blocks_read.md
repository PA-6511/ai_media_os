# Step1: 一覧取得系 実装メモ

## 目的

- `getBlocks()` / `getBlockById()` を本 API 経由で取得できる形に整備する
- 失敗時は mock フォールバックで既存 UI を維持する

---

## 対象関数

| 関数 | API path | 優先度 |
|---|---|---|
| `getBlocks()` | `GET /blocks` | 先に差し替え |
| `getBlockById(id)` | `GET /blocks/{id}` | 先に差し替え |
| `getConnectionManagementItems()` | `getBlocks()` 経由 | getBlocks 済み後に対応 |
| `getBlockDetailViewModel(id)` | `getBlockById()` 経由 | getBlockById 済み後に対応 |
| `getBlockDashboardStats()` | `getBlocks()` 経由 | getBlocks 済み後に対応 |

---

## 変更対象ファイル

- `ui/services/apiClient.js` — `API_BASE_URL` / `API_PATHS` 定数、`getBlocksJson()`
- `ui/services/blockService.js` — `getBlocks()` / `getBlockById()` の API 呼び出しと mock フォールバック
- `ui/script.js` — 一覧描画の欠損値耐性、`normalizeBlockListForView()`

---

## API 利用想定

- `API_BASE_URL = "/api"` (リバースプロキシ経由を想定)
- `GET /api/blocks` → blocks 配列を返す
- `GET /api/blocks/{id}` → 単一 block オブジェクトを返す
- レスポンス形式は `{ data: { items: [...] } }` / 直配列 どちらも `resolveBlocksListResponse()` で吸収済み

---

## mock フォールバック方針

- `getBlocks()`: API 失敗 → `cloneMockBlocks()` を返す
- `getBlockById()`: API 失敗 → `getBlocks()` → `mockBlocks` の順でフォールバック
- 本 API が無い状態でも動作維持

---

## 疎通確認項目

### 確認前準備

- [ ] `API_BASE_URL` が正しいか確認する (`ui/services/apiClient.js` の `API_BASE_URL`)
- [ ] バックエンドが起動しているか確認する
- [ ] リバースプロキシ設定で `/api` が正しくルーティングされているか確認する

### ブラウザコンソール確認

```js
// コンソールで直接疎通確認 (import 済みの apiClient を使う場合)
// または fetch 直打ち
fetch("/api/blocks").then(r => r.json()).then(console.log)
fetch("/api/blocks/1").then(r => r.json()).then(console.log)
```

- [ ] `fetch("/api/blocks")` が 200 を返す
- [ ] レスポンスが配列 or `{ data: { items: [...] } }` 形式である
- [ ] `fetch("/api/blocks/{id}")` が 200 を返す
- [ ] 存在しない id で 404 になる（mock フォールバックに落ちることを確認）

### Network タブ確認

- [ ] ページロード時に `/api/blocks` リクエストが発生している
- [ ] Status が 200 か 404/5xx か
- [ ] 404/5xx のとき GUI が mock データで表示を維持しているか
- [ ] `/api/blocks/{id}` が詳細パネル選択時に発行されているか
- [ ] レスポンスヘッダーに `Content-Type: application/json` が含まれているか

---

## 確認項目 (実装後)

- [ ] `getBlocks()` が API 成功時に API データを返す
- [ ] `getBlocks()` が API 失敗時に mock データを返す
- [ ] API 成功時に GUI 一覧が API データで表示される
- [ ] API 失敗時に GUI 一覧が mock フォールバックで表示される
- [ ] フォールバック時に message 表示（`Block 一覧の取得に失敗しました。`）が出る
- [ ] `getBlockById()` が API 成功時に正規化済みオブジェクトを返す
- [ ] `getBlockById()` が API 失敗時に `getBlocks()` → mock の順でフォールバックする
- [ ] 詳細ボタン押下で詳細表示される
- [ ] 詳細取得 API 失敗時に fallback（`getBlocks()` → mock）する
- [ ] block 不存在時に表示が崩れない（詳細プレースホルダ表示）
- [ ] `normalizeBlock()` で欠損フィールドがデフォルト値で補完される
- [ ] Dashboard / Block管理ページの一覧が両方更新される
- [ ] 詳細パネル選択が壊れない

### getBlockById() 確認観点（Step1）

- [ ] API 成功時: `GET /api/blocks/{id}` 応答で詳細パネルが更新される
- [ ] API 失敗時: 一覧経由フォールバックで詳細パネルが表示継続する
- [ ] block 不存在時: 例外で落ちず、詳細プレースホルダ表示に戻る

### script.js 描画確認観点（Step1）

- [ ] 初回表示で一覧が表示される
- [ ] 詳細ボタン押下で詳細パネルが更新される
- [ ] 一覧取得失敗時に message（`Block 一覧の取得に失敗しました。`）が表示される
- [ ] 詳細取得失敗時に詳細パネルが壊れない（プレースホルダ表示）

---

## まだやらないこと

- POST / DELETE 系 (connect / disconnect / freeze / export / delete)
- 認証トークンの付与
- エラー詳細のユーザー向け表示改善
- logService / settings の API 差し替え

---

## Step1 実動確認結果

- 実動確認日
	- [ ] YYYY-MM-DD

- 成功した確認項目
	- [ ] `GET /api/blocks` で一覧取得できる
	- [ ] 一覧表示が崩れず描画される
	- [ ] 一覧取得失敗時に mock フォールバック表示を維持する
	- [ ] 詳細パネル選択操作が壊れない

- 未確認項目
	- [ ] `GET /api/blocks/{id}` の本API応答で詳細反映
	- [ ] block 不存在時の詳細プレースホルダ遷移
	- [ ] Dashboard 集計の本APIデータ整合

- 発見した課題
	- [ ]

- 次に見るポイント
	- [ ] 詳細取得成功/失敗時のUI分岐
	- [ ] 欠損フィールド時の `normalizeBlock()` 補完結果
	- [ ] Network エラー時メッセージの表示タイミング

---

## Step2 で見る項目（詳細取得系 本API接続）

- [ ] `/blocks/{id}` の path 利用箇所を確認する
- [ ] id の受け渡し（選択ID → API path）の値を確認する
- [ ] 404 時の扱い（例外 → フォールバック/表示維持）を確認する
- [ ] Network タブで `/api/blocks/{id}` の発行・Status を確認する
- [ ] 詳細取得失敗時のフォールバック動作を確認する
- [ ] 詳細ボタン押下で API 詳細取得が発行されること
- [ ] 詳細取得失敗時に UI が崩れないこと
- [ ] 詳細パネルがプレースホルダー表示へ復帰すること
- [ ] 詳細取得失敗時に message が表示されること

### Step2 追加確認（詳細描画安定化）

- [ ] 詳細ボタンで API 詳細取得が走るか
- [ ] 詳細取得失敗時に UI が崩れないか
- [ ] 詳細取得失敗時に詳細パネルがプレースホルダーへ復帰するか
- [ ] 詳細取得失敗時に message が表示されるか
