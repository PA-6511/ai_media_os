# Step2: 詳細取得系 本API接続メモ

## Step2 の目的

- 詳細ボタン押下で本API詳細取得を行う
- 詳細取得失敗時にUI崩れを防止する
- 選択中 blockId の扱いを追いやすくする

## 対象関数

- renderSelectedBlockDetail(blockId)
- refreshSelectedBlockDetail(blockId)
- serviceQueries.getBlockDetailViewModel(blockId)
- services.block.getBlockById(blockId)

## 変更対象ファイル

- ui/services/blockService.js
- ui/services/apiClient.js
- ui/services/queryService.js
- docs/gui_step2_block_detail_api.md

## API 利用想定

- ベースパス: /api
- 詳細取得: GET /api/blocks/{id}
- 成功時: 詳細パネルへ反映
- 失敗時: message 表示 + 詳細パネルをプレースホルダーへ復帰

## fallback 方針

- getBlockDetailViewModel を優先利用
- 利用不可時は getBlockById を利用
- 取得失敗時は詳細パネルを安全側へ戻す
- 非同期競合時は古い応答を破棄し、最新選択のみ反映

## 確認項目

- [ ] 詳細ボタンで API 詳細取得が走る
- [ ] GET /api/blocks/{id} の {id} に選択中 blockId がそのまま入る
- [ ] getBlockById(blockId) 成功時に API 詳細データが返る
- [ ] 詳細取得成功時に詳細パネルが更新される
- [ ] 詳細取得失敗時にUIが崩れない
- [ ] 詳細取得失敗時にプレースホルダーへ復帰する
- [ ] 詳細取得失敗時に message が表示される
- [ ] API 失敗時に getBlockById(blockId) が一覧 fallback へ進む
- [ ] 404 時に not found 系として安全側表示へ戻る
- [ ] 404 時に getBlockById(blockId) が null を返すか安全な戻り方になる
- [ ] 500 時に server error 系として message 表示になる
- [ ] Network タブで request URL / status / response を確認できる
- [ ] Console に未処理例外が出ない
- [ ] 連続選択時に古い応答で上書きされない
- [ ] getBlockDetailViewModel(blockId) の返り値に id が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に name が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に type が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に status が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に connectionStatus が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に freezeStatus が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に handshakeStatus が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に updatedAt が含まれる
- [ ] getBlockDetailViewModel(blockId) の返り値に deleteRequested が含まれる
- [ ] API返り値の一部項目欠損時もデフォルト値で補完される
- [ ] block が存在しない場合は getBlockDetailViewModel(blockId) が null を返す
- [ ] id 欠損時も blockId ベースで整形される
- [ ] name 欠損時は `-` で補完される
- [ ] type 欠損時は `-` で補完される
- [ ] status 欠損時は `stopped` で補完される
- [ ] connectionStatus 欠損時は `disconnected` で補完される
- [ ] freezeStatus 欠損時は `active` で補完される
- [ ] handshakeStatus 欠損時は `idle` で補完される
- [ ] updatedAt 欠損時も値が入る
- [ ] deleteRequested 欠損時は `false` で補完される

## 実動確認メモ

- Request URL は `GET /api/blocks/{id}` になっているか
- path の `{id}` は選択中 blockId と一致しているか
- API 成功時は `getBlockById(blockId)` が詳細 object を返すか
- API 失敗時は `getBlockById(blockId)` が一覧 fallback または null へ安全に戻るか
- `getBlockDetailViewModel(blockId)` は `id / name / type / status / connectionStatus / freezeStatus / handshakeStatus / updatedAt / deleteRequested` のみ返すか
- API 項目欠損時も `normalizeBlock` のデフォルトで表示に必要な項目が埋まるか
- 404 は not found 系として message 表示 + プレースホルダー復帰で見る
- 500 は server error 系として message 表示 + プレースホルダー復帰で見る
- Network タブで Request URL / Status / Response を確認する
- Console に未処理例外が残っていないことを確認する
- block 不存在時に詳細 UI が壊れずプレースホルダー維持になるか

## 整形キー確認メモ

- `BLOCK_DETAIL_VIEW_MODEL_KEYS` と `Object.keys(getBlockDetailViewModel(blockId))` の一致を確認する
- 期待キー:
	- `id`
	- `name`
	- `type`
	- `status`
	- `connectionStatus`
	- `freezeStatus`
	- `handshakeStatus`
	- `updatedAt`
	- `deleteRequested`
- block 不存在時は `getBlockDetailViewModel(blockId) === null` を確認する

## コンソール確認スニペット

```js
// Step2 実動確認: ブラウザコンソールで整形結果を確認する
import { inspectBlockDetailViewModel, BLOCK_DETAIL_VIEW_MODEL_KEYS } from '/ui/services/blockService.js';

// 整形結果を console.table で表示
await inspectBlockDetailViewModel('block-001');

// 期待キー一覧確認
console.log(BLOCK_DETAIL_VIEW_MODEL_KEYS);
// => ['id','name','type','status','connectionStatus','freezeStatus','handshakeStatus','updatedAt','deleteRequested']

// 返却キーと期待キーの一致確認
const vm = await inspectBlockDetailViewModel('block-001');
console.assert(
  vm !== null && JSON.stringify(Object.keys(vm)) === JSON.stringify([...BLOCK_DETAIL_VIEW_MODEL_KEYS]),
  'getBlockDetailViewModel のキーが期待通りであること'
);

// block 不存在時の null 確認
const vmNull = await inspectBlockDetailViewModel('non-existent-id');
console.assert(vmNull === null, 'block 不在時は null であること');
```

## script.js 詳細描画・失敗時復帰 確認項目

- [ ] 詳細ボタン押下で `renderSelectedBlockDetail(blockId)` が呼ばれる
- [ ] `renderSelectedBlockDetail` 成功時に詳細パネル (`renderBlockManagementDetail`) が更新される
- [ ] `renderSelectedBlockDetail` 失敗時に `clearBlockDetailPanels()` でプレースホルダーへ復帰する
- [ ] `renderSelectedBlockDetail` 失敗時に `msgBlockDetailLoadFailed` の message が表示される
- [ ] `detailResult.ok === false` の分岐でも message が出る（`!detailResult.ok` ブランチ）
- [ ] `detailResult.data` が null/不正時にも message + プレースホルダー復帰になる
- [ ] 連続選択時に `blockDetailRequestSeq` で古い応答が破棄され上書きされない
- [ ] `selectedBlockId` が `setSelectedBlockId` で正しく更新される
- [ ] `null` 渡し時に `clearBlockDetailPanels()` のみ呼ばれ例外が出ない

## まだやらないこと

- connect / disconnect の本API化
- freeze / unfreeze / export / delete の本API化
- settings / audit の本API化
- 認証と再試行戦略の最終化
