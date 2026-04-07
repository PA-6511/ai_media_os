# Step4: Audit / Settings 本API接続メモ

## Step4 の目的
- Audit Log / Security Settings を本API前提で安定動作させる
- API成功時を優先し、失敗時もUIを壊さない
- 既存の一覧・詳細・接続/切断・危険操作導線に影響を出さない

## 対象関数
- `getAuditLogs()`
- `getRecentAuditLogs()`
- `getAuditLogViewItems()`
- `getAuditLogCount()`
- `getSecuritySettings()`
- `updateSecuritySettings(nextSettings)`

## 変更対象ファイル
- `ui/services/apiClient.js`
- `ui/services/logService.js`
- `ui/script.js`

## API 利用想定
- Audit Log 一覧取得: `GET /audit-logs`
- Audit Log 条件取得: `GET /audit-logs?action={action}&result={result}`
- Audit Log 件数取得: `GET /audit-logs/count?action={action}&result={result}`
- Security Settings 取得: `GET /settings/security`
- Security Settings 保存: `PUT /settings/security`
- 将来方針:
  - `getAuditLogs()` は `getJson('/audit-logs')` 前提を維持
  - `getSecuritySettings()` は `getJson('/settings/security')` 前提を維持
  - `updateSecuritySettings()` は `putJson('/settings/security', nextSettings)` 前提を維持

## fallback 方針
- API成功時:
  - APIレスポンスを正規化してUIへ反映
- API失敗時:
  - Audit Log は mock / 既存表示 / プレースホルダーにフォールバック
  - Settings は mock / 既存表示にフォールバック
  - 保存失敗時は fail-safe で再描画破壊を避け、message表示のみ実施

## 確認項目
- Audit Log
  - 一覧取得成功時にダッシュボード最新ログと一覧が更新される
  - 一覧取得失敗時に既存表示維持またはプレースホルダー表示になる
  - 件数取得成功時に件数表示が更新される
  - 件数取得失敗時にUIが崩れず message 表示される
- Settings
  - 取得成功時にフォームへ値が反映される
  - 取得失敗時に既存表示維持またはプレースホルダー表示になる
  - 保存成功時に設定表示とAudit Log表示が再同期される
  - 保存失敗時にUIが崩れず message 表示のみで停止する

## Step4 実動確認: API疎通チェック
- GET /audit-logs
  - [ ] Network タブで `GET /api/audit-logs` が発行される
  - [ ] response body の shape（array / items / logs / data.items / data.logs）を確認する
  - [ ] Console に `GET /audit-logs failed` が不要に出ていないことを確認する
- GET /settings/security
  - [ ] Network タブで `GET /api/settings/security` が発行される
  - [ ] response body の shape（settings object）を確認する
  - [ ] Console に `GET /settings/security failed` が不要に出ていないことを確認する
- PUT /settings/security
  - [ ] Network タブで `PUT /api/settings/security` が発行される
  - [ ] request body に settings の5項目が入っていることを確認する
  - [ ] response body の shape（updated settings object）を確認する
  - [ ] Console に `PUT /settings/security failed` が不要に出ていないことを確認する

## Step4 実動確認: Audit Log 取得系（成功/失敗）
- [ ] Audit Log API成功時に一覧（`getAuditLogs()` / `getAuditLogViewItems()`）が返る
- [ ] Audit Log API失敗時に fallback（mock）へ切り替わる
- [ ] 件数表示（`getAuditLogCount()`）が崩れない
- [ ] `result` / `action` フィルタ適用時に一覧描画が崩れない
- [ ] `getRecentAuditLogs()` で最新N件の表示が崩れない

## Step4 実動確認: Settings 取得/保存系（成功/失敗）
- [ ] Settings API取得成功時に値（`getSecuritySettings()`）が返る
- [ ] Settings API取得失敗時に既存表示維持または fallback する
- [ ] Settings API保存成功時に message が表示される
- [ ] Settings API保存失敗時に fail-safe で UI が壊れない

## Step4 実動確認: script.js 描画更新（Audit / Settings）
- [ ] Audit Log 一覧更新が反映される（ダッシュボード / Audit ページ）
- [ ] Audit Log 件数更新が反映される
- [ ] Settings 描画更新が反映される（取得成功時）
- [ ] Settings 保存後に message が表示される
- [ ] 取得/保存失敗時に UI 安定性（既存表示維持またはプレースホルダー復帰）が維持される

## まだやらないこと
- 危険操作系 (`export` / `delete` / `freeze` / `unfreeze`) の本API強化
- 認証ヘッダー付与やリクエスト署名の本番最適化
- retry / circuit breaker など高度な失敗制御
- fallback（mock依存）の完全撤去

## Step4 実動確認結果
- 実動確認日
  - [ ] yyyy-mm-dd
- 成功した確認項目
  - [ ] GET /audit-logs: 一覧更新OK
  - [ ] GET /audit-logs(count/filter): 件数・フィルタ更新OK
  - [ ] GET /settings/security: settings 描画更新OK
  - [ ] PUT /settings/security: 保存後 message 表示OK
- 未確認項目
  - [ ] 失敗系レスポンス（audit）
  - [ ] 失敗系レスポンス（settings 取得）
  - [ ] 失敗系レスポンス（settings 保存）
- 発見した課題
  - [ ] なし
  - [ ] あり（内容を記載）
- 次に見るポイント
  - [ ] settings 保存失敗時の fail-safe（再描画破壊なし）
  - [ ] audit fallback 時の件数表示整合
  - [ ] フィルタ入力時の一覧更新遅延/ちらつき

---

## 全API通し確認（freeze/unfreeze → settings → audit）

### 通し確認手順

1. block の Freeze ボタンを押し、警告確認チェックを入れて実行する
2. Freeze 後に一覧・詳細・Dashboard の freezeStatus / 集計値・Audit Log が整合して更新される
3. 同じ block で Unfreeze を実行し、同様に再描画が整合するか確認する
4. Settings ページで任意のフィールドを変更して保存する
5. 保存後に Settings フォームの表示が最新値に更新され、Audit Log に記録が残ることを確認する
6. Audit Log ページでフィルタを切り替えて絞り込みが正しく機能するか確認する

### 確認項目

#### Freeze 後に状態が更新されるか
- [ ] 一覧の freezeStatus chip が `frozen` に変わる
- [ ] 詳細パネルの freezeStatus が `frozen` に変わる
- [ ] Dashboard の frozenBlocks カウントが増加する
- [ ] Dashboard の activeBlocks カウントが減少する
- [ ] Audit Log に freeze 記録が追加される
- [ ] message に freeze 成功結果が表示される

#### Unfreeze 後に状態が戻るか
- [ ] 一覧の freezeStatus chip が `active` に戻る
- [ ] 詳細パネルの freezeStatus が `active` に戻る
- [ ] Dashboard の frozenBlocks カウントが減少する
- [ ] Dashboard の activeBlocks カウントが増加する
- [ ] Audit Log に unfreeze 記録が追加される
- [ ] message に unfreeze 成功結果が表示される

#### Settings 保存後に message と表示が整合するか
- [ ] `PUT /settings/security` が発行される
- [ ] 保存成功後に Settings フォームの表示が最新値に更新される
- [ ] 保存成功 message が表示される
- [ ] Audit Log に settings 保存記録が追加される
- [ ] 保存失敗時に message のみ表示され、フォームの状態が変化しない

#### Audit Log に操作履歴が反映されるか
- [ ] Freeze 操作が Audit Log に action=`freeze`、result=`success` で記録される
- [ ] Unfreeze 操作が Audit Log に action=`unfreeze`、result=`success` で記録される
- [ ] Settings 保存が Audit Log に記録される
- [ ] action フィルタで freeze のみ絞り込みができる
- [ ] result フィルタで success のみ絞り込みができる
- [ ] Dashboard の最近ログに最新操作が表示される
