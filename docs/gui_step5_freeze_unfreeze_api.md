

# Step5: freeze / unfreeze API 接続メモ

## Step5 の目的
- freeze / unfreeze を本APIへ接続する
- 警告表示導線を維持して実行フローを安定化する
- 成功時反映と失敗時 fail-safe を固定する

## 対象関数
- `freezeBlock(blockId)`
- `unfreezeBlock(blockId)`
- `executeFreezeDangerAction()`
- `getFreezeDangerMeta(blockId, actionType)`

## 変更対象ファイル
- `ui/services/blockService.js`
- `ui/services/apiClient.js`
- `ui/script.js`
- `docs/gui_api_readiness_checklist.md`

## API 利用想定
- freeze: `POST /api/blocks/{id}/freeze`
- unfreeze: `POST /api/blocks/{id}/unfreeze`
- freeze service 呼び出し: `postJson('/blocks/{blockId}/freeze', {})`
- unfreeze service 呼び出し: `postJson('/blocks/{blockId}/unfreeze', {})`
- UI: レスポンスの `success / message / block` を受けて反映

## fallback 方針
- API成功時はレスポンスの状態値を優先反映
- API失敗時は service fallback を実行
- 戻り値形式は `{ success, message, block }` を維持
- UIは `success` 判定で再描画、失敗時は message 表示のみ

## 確認項目
- [ ] `POST /api/blocks/{id}/freeze` が発行される
- [ ] `POST /api/blocks/{id}/unfreeze` が発行される
- [ ] request body が `{}` で送信される
- [ ] 成功時に `freezeStatus` が正しく反映される
- [ ] 失敗時に fallback 分岐へ入る
- [ ] API例外時も画面を崩さず message のみ表示する
- [ ] 警告確認未チェック時は service 関数を呼ばない
- [ ] 警告表示から execute までの導線を維持する
- [ ] 成功時に一覧・詳細・Dashboard・接続管理・監査ログが再描画される
- [ ] 同一 block/action の二重実行が抑止される

## まだやらないこと
- export / delete の本API接続
- freeze / unfreeze 失敗文言の最終統一
- API失敗時の再試行導線追加
- 認証UI拡張