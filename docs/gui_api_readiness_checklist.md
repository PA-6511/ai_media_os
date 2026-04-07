# 本API接続前レビュー チェックリスト

## 段階解放レベル別 解放条件

### Level1: 参照系（一覧表示 / 詳細表示 / Dashboard / Audit Log参照 / Settings参照）

- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし

## Level1 起動前チェック欄（解放直前）

- [ ] API_BASE_URL確認: 接続先がLevel1解放対象環境になっている
- [ ] 一覧表示確認: `GET /blocks` 応答で表示崩れがない
- [ ] 詳細表示確認: `GET /blocks/{id}` 応答で詳細が更新される
- [ ] Dashboard確認: 集計表示が一覧データと一致する
- [ ] Audit Log 参照確認: `GET /audit-logs` 応答が表示に反映される
- [ ] Settings 参照確認: `GET /settings` 応答が表示に反映される
- [ ] message表示確認: 参照系の成功/失敗 message が正しく表示される
- [ ] プレースホルダー確認: 仮文言・仮リンク・仮表示が残っていない
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log の再描画が一致する

### Level1 対象外（別Levelで確認）

- [ ] 更新系: Settings 保存 / Connect / Disconnect
- [ ] 条件付き更新系: Freeze / Unfreeze
- [ ] 危険操作系: Export / Delete

### Level2: 低リスク更新系（Connect / Disconnect）

- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし
- [ ] connectionStatus 反映が一覧・詳細で一致

## Level2 起動前チェック欄（解放直前）

- [ ] API_BASE_URL確認: Level2 対象環境の接続先が正しい
- [ ] Level1 監視で重大異常なし
- [ ] Settings 参照確認: `GET /settings` 応答が安定表示される
- [ ] Settings 保存確認: 保存後再読込で値保持を確認できる
- [ ] Connect 確認: `POST /blocks/{id}/connect` 実行後に接続状態が反映される
- [ ] Disconnect 確認: `POST /blocks/{id}/disconnect` 実行後に切断状態が反映される
- [ ] Audit Log 更新確認: Settings/Connect/Disconnect の記録が追記される
- [ ] message表示確認: 成功/失敗 message が結果と一致する
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が整合する
- [ ] fail-safe確認: 異常時に state 不整合なく停止する

### Level2 対象外（別Levelで確認）

- [ ] Freeze / Unfreeze
- [ ] Export / Delete

## Level2 起動前チェック（実行フェーズ固定）

- [ ] API_BASE_URL確認
- [ ] Level1 監視で重大異常なし
- [ ] Settings 参照確認
- [ ] Settings 保存確認
- [ ] Connect 確認
- [ ] Disconnect 確認
- [ ] Audit Log 更新確認
- [ ] message表示確認
- [ ] 再描画整合確認
- [ ] fail-safe確認

### Level2 対象外（実行フェーズ固定）

- [ ] Freeze / Unfreeze
- [ ] Export / Delete

## Level3 起動前チェック欄（解放直前）

- [ ] API_BASE_URL確認: Level3 解放先環境の接続先が正しい
- [ ] Level2 監視で重大異常なし
- [ ] Freeze 警告表示確認: `POST /blocks/{id}/freeze` 実行前の警告確認モーダルが表示される
- [ ] Unfreeze 警告表示確認: `POST /blocks/{id}/unfreeze` 実行前の警告確認モーダルが表示される
- [ ] 確認チェック導線確認: confirmed チェック未実施時に execute ボタンが無効化または中断される
- [ ] Freeze 実行確認: `POST /blocks/{id}/freeze` 実行後に freezeStatus が `frozen` へ反映される
- [ ] Unfreeze 実行確認: `POST /blocks/{id}/unfreeze` 実行後に freezeStatus が `active` へ反映される
- [ ] Audit Log 更新確認: Freeze/Unfreeze 操作後に Audit Log へ記録が追記される
- [ ] message表示確認: 成功/失敗 message が操作結果と一致する
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が整合する
- [ ] fail-safe確認: blockId 不在・状態不正・confirmed 未チェック時に service call を中断する

### Level3 対象外（別Levelで確認）

- [ ] Export: 危険操作系のため Level4 まで未解放維持
- [ ] Delete: 危険操作系のため Level4 まで未解放維持

## Level3 起動前チェック（実行フェーズ固定）

- [ ] API_BASE_URL確認
- [ ] Level2 監視で重大異常なし
- [ ] Freeze 警告表示確認
- [ ] Unfreeze 警告表示確認
- [ ] 確認チェック導線確認
- [ ] Freeze 実行確認
- [ ] Unfreeze 実行確認
- [ ] Audit Log 更新確認
- [ ] message表示確認
- [ ] 再描画整合確認
- [ ] fail-safe確認

### Level3 対象外（実行フェーズ固定）

- [ ] Export / Delete

### Level3: 条件付き更新系（Settings保存 / Freeze / Unfreeze）

- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし
- [ ] Settings 保存後の値保持確認済み
- [ ] freezeStatus 反映が一覧・詳細・Dashboardで一致

### Level4: 危険操作系（Export / Delete）

- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし
- [ ] LockGuard 全項目検証確認済み
- [ ] confirmed 未チェック時の実行中断確認済み
- [ ] 認証不足時の実行中断確認済み
- [ ] 失敗時 state 不変確認済み
- [ ] 単独操作確認だけでなく通し確認済み

## Level4 解放直前チェック欄（実行フェーズ固定）

- [ ] API_BASE_URL確認: Level4 解放先環境の接続先が正しい
- [ ] Level3 監視で重大異常なし
- [ ] LockGuard 表示確認: Export / Delete 実行前にLockGuardが正しく表示される
- [ ] password 入力確認: 未入力時は中断し、入力時のみ判定へ進む
- [ ] twoFactorCode 入力確認: 未入力時は中断し、入力時のみ判定へ進む
- [ ] confirmationText 入力確認: 指定文言不一致時は中断する
- [ ] confirmed チェック確認: 未チェック時は実行できない
- [ ] Export 実行確認: 認証通過後のみ `POST /blocks/{id}/export` が実行される
- [ ] Delete 実行確認: 認証通過後のみ `DELETE /blocks/{id}` が実行される
- [ ] Audit Log 更新確認: Export / Delete の action / target / result が追記される
- [ ] message表示確認: 成功 / 失敗 / 認証失敗の表示が結果と一致する
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が操作後に整合する
- [ ] fail-safe確認: 認証不足・確認未完了・入力不備・pending時に中断する

### Level4 対象外（実行フェーズ固定）

- [ ] Freeze / Unfreeze の継続判定は対象外（Level3 側で継続監視）

## 接続対象API一覧
- [ ] GET /blocks — block一覧取得
- [ ] GET /blocks/:blockId — block詳細取得
- [ ] POST /blocks/:blockId/connect — connect操作
- [ ] POST /blocks/:blockId/disconnect — disconnect操作
- [ ] POST /blocks/:blockId/freeze — freeze操作
- [ ] POST /blocks/:blockId/unfreeze — unfreeze操作
- [ ] POST /blocks/:blockId/export — export操作（認証必須）
- [ ] DELETE /blocks/:blockId — delete操作（認証必須）
- [ ] GET /audit-logs — audit log一覧取得
- [ ] GET /settings — settings取得
- [ ] PATCH /settings — settings更新
- [ ] GET /handshake — handshake状態取得
- [ ] PATCH /handshake — handshake状態更新

## 各操作の前提条件
- connect / disconnect: blockId が存在すること
- freeze / unfreeze: blockId が存在し、警告確認チェックが完了していること
- export / delete: blockId 存在・password・twoFactorCode・confirmationText・confirmed がすべて揃っていること
- settings 更新: 各フィールドの型が正しいこと（Boolean / Number）
- audit log 取得: フィルタ条件が文字列形式であること

## 失敗時の止め方
- [ ] lockguard 状態が `ready` でない場合は export / delete を中断
- [ ] blockId 不在または actionType 不正の場合は危険操作を中断
- [ ] 確認チェック未同意の場合は freeze / unfreeze / export / delete を中断
- [ ] 同一 blockId + actionType が pending の場合は二重実行を中断
- [ ] service 例外発生時は UI 状態変更を中断してメッセージのみ表示

## UI再描画確認
- [ ] 操作成功後に block一覧・詳細・ダッシュボード集計が再描画される
- [ ] 操作成功後に audit log が再描画される
- [ ] 操作成功後に connection management パネルが再描画される
- [ ] 操作失敗後に UI 状態が変化しない

## 認証確認
- [ ] export / delete の実行前に password / twoFactorCode / confirmationText / confirmed の全検証が通る
- [ ] 認証失敗時に失敗メッセージが表示され、対象が変更されない
- [ ] 認証情報は送信後にフォームからクリアされる

## ログ更新確認
- [ ] 操作ごとに audit log に action / target / result / operator が記録される
- [ ] 失敗時にも audit log に失敗記録が残る
- [ ] ログ表示領域が操作後に最新化される

## テスト前チェック
- [ ] services マップの各関数が API 版に差し替わっている
- [ ] mock データへの直接参照が script.js に残っていない
- [ ] fetch / API エラー時のフォールバックが設定されている
- [ ] 本番環境の CORS / 認証ヘッダーが正しく設定されている

## API接続設計たたき台（GUI利用観点）

- GET /blocks
	- 用途: block一覧の取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: 一覧テーブル、接続管理パネル、ダッシュボード集計の初期表示

- GET /blocks/{id}
	- 用途: block詳細の取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: 選択中block詳細、freeze/lockguard警告表示の元データ取得

- POST /blocks/{id}/connect
	- 用途: block接続操作の実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: 接続管理パネルの connect アクション

- POST /blocks/{id}/disconnect
	- 用途: block切断操作の実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: 接続管理パネルの disconnect アクション

- POST /blocks/{id}/freeze
	- 用途: block凍結操作の実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: 危険操作フロー（freeze確認ダイアログ）

- POST /blocks/{id}/unfreeze
	- 用途: block凍結解除操作の実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: 危険操作フロー（unfreeze確認ダイアログ）

- POST /blocks/{id}/export
	- 用途: blockエクスポート操作の実行（認証付き）
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: lockguard付き export 実行フロー

- DELETE /blocks/{id} または POST /blocks/{id}/delete
	- 用途: block削除操作の実行（認証付き）
	- 想定HTTPメソッド: DELETE を第一候補、互換要件がある場合のみ POST /delete を許容
	- GUI側利用箇所: lockguard付き delete 実行フロー

- GET /audit-logs
	- 用途: 監査ログ一覧の取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: 監査ログテーブル、ダッシュボード最近ログ表示

---

## Step5 実装後の確認 (freeze / unfreeze 本API接続)

### 実装後の確認項目
- [ ] `POST /api/blocks/{id}/freeze` がネットワークタブに記録される
- [ ] `POST /api/blocks/{id}/unfreeze` がネットワークタブに記録される
- [ ] request body が `{}` で送信される
- [ ] レスポンスの `block.freezeStatus` が画面に即時反映される
- [ ] API成功時は一覧・詳細・Dashboard・接続管理・監査ログが再描画される
- [ ] API失敗時は fallback 分岐に入り、UI状態が変化しない
- [ ] API例外時は `message` のみ表示され画面を崩さない

### freeze / unfreeze 系の残課題
- [ ] 失敗メッセージ文言の最終統一（未対応）
- [ ] API失敗時の再試行導線追加（未対応）
- [ ] freeze 中 block への操作がUIレベルで抑止されているか確認
- [ ] unfreeze 後の状態遷移が正しく画面へ伝播するか確認

### 警告表示導線の確認
- [ ] 警告確認チェックが未完了の場合、service 関数を呼ばない
- [ ] 警告ダイアログ表示 → execute までの導線が維持されている
- [ ] 警告ダイアログの cancel が正しく機能し、状態が元に戻る
- [ ] freeze / unfreeze 両方で警告モーダルの表示トリガーが動作する

### fail-safe 確認
- [ ] blockId 不在時は freeze / unfreeze を中断する
- [ ] 同一 blockId + actionType が pending の場合は二重実行を中断する
- [ ] service 例外発生時は UI 状態変更を中断し message のみ表示する
- [ ] API失敗後も一覧・詳細の表示状態が変化しない

- GET /settings/security
	- 用途: セキュリティ設定の取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: Security Settings 画面の初期表示

- PUT /settings/security
	- 用途: セキュリティ設定の更新
	- 想定HTTPメソッド: PUT
	- GUI側利用箇所: Security Settings 保存アクション

- GET /blocks/{id}/handshake
	- 用途: block単位の handshake 状態取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: connect/disconnect 実行前後の状態表示

- POST /blocks/{id}/handshake
	- 用途: block単位の handshake 状態遷移更新
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: connect/disconnect 実行時の pending/success/failed 更新

- 設計メモ
	- 本セクションは接続設計フェーズのたたき台であり、本API実装の着手前提資料として扱う
	- 既存の /settings, /handshake 系記載は互換検討用として残し、最終仕様は /settings/security と /blocks/{id}/handshake に寄せる

## API失敗時のGUI挙動（script.js 最小方針）

- 一覧取得失敗
	- メッセージ表示: `Block 一覧の取得に失敗しました。`
	- 既存データ維持: 直前に描画済みの一覧DOMを維持
	- 再描画停止: 当該一覧セクションの再描画を中断

- 詳細取得失敗
	- メッセージ表示: `Block 詳細の取得に失敗しました。`
	- 既存データ維持: 直前の詳細表示を維持
	- 再描画停止: 詳細パネル更新を中断

- 危険操作失敗（freeze/unfreeze/export/delete）
	- メッセージ表示: service の `message` を優先、未設定時は失敗文言を表示
	- 既存データ維持: 対象 block の表示値は失敗時に変更しない
	- 再描画停止: 失敗系レスポンスでは状態更新を行わず、安全側で処理終了

- 認証失敗（export/delete）
	- メッセージ表示: service の `success=false` + `message` を表示
	- 既存データ維持: deleteRequested 等の状態は変更しない
	- 再描画停止: 認証失敗時は危険操作の結果反映を中断

- settings 保存失敗
	- メッセージ表示: settings 更新失敗メッセージを表示
	- 既存データ維持: 直前の設定表示値を維持
	- 再描画停止: settings セクションの反映更新を中断

- audit log 取得失敗
	- メッセージ表示: `audit log の取得に失敗しました。`
	- 既存データ維持: ダッシュボード最近ログ・監査ログ一覧は直前表示を維持
	- 再描画停止: log テーブル/件数の更新を中断

## 接続直前レビュー観点（差分追加）

- mock 関数の差し替え順序（どの mock 関数から先に差し替えるか）
	- [ ] `getBlocks`（一覧取得）
	- [ ] `getBlockDetail`（詳細取得）
	- [ ] `getAuditLogs`（ログ取得）
	- [ ] `getSettings` / `saveSettings`（settings）
	- [ ] `connect` / `disconnect`（通常操作）
	- [ ] `freeze` / `unfreeze`（準危険操作）
	- [ ] `export` / `delete`（危険操作・認証付き、最後）

- 危険操作は後回しにする順序
	- [ ] 後回し1: `export`
	- [ ] 後回し2: `delete`
	- [ ] 後回し3: `freeze` / `unfreeze`
	- [ ] `connect` / `disconnect` の安定確認後に着手

- 認証付き操作の確認事項
	- [ ] `Authorization` ヘッダー付与有無
	- [ ] `X-Request-Id` の採番と送信
	- [ ] 認証エラー時に状態反映しないこと
	- [ ] 認証情報の再入力導線とクリア動作

- 一覧取得失敗時の扱い
	- [ ] 既存一覧を保持
	- [ ] 失敗メッセージを表示
	- [ ] 一覧セクションのみ再描画停止

- ログ取得失敗時の扱い
	- [ ] 既存ログ表示を保持
	- [ ] 失敗メッセージを表示
	- [ ] ログ件数更新を停止

- settings 保存失敗時の扱い
	- [ ] 未反映ステータスを表示
	- [ ] 直前値へのロールバック導線を表示
	- [ ] 自動再試行は1回まで

- fail-safe で止める条件
	- [ ] 同一主要APIの連続失敗が3回
	- [ ] 認証付きAPIで `UNAUTHORIZED` が連続発生
	- [ ] 危険操作で状態不整合を検知
	- [ ] `INTERNAL_ERROR` / `UPSTREAM_TIMEOUT` が継続

## 実装着手順

### Step1: 一覧取得系
- 着手条件
	- [ ] `GET /blocks` のレスポンス項目が確定している
	- [ ] 一覧系の描画項目と API 項目の対応が取れている
- 確認項目
	- [ ] block 一覧が崩れず描画される
	- [ ] dashboard 集計と connection management の元データ取得が成立する
	- [ ] 一覧取得失敗時に既存表示を維持できる
- まだやらないこと
	- [ ] 危険操作の接続
	- [ ] 認証付き API の接続

#### Step1 実動確認済みチェック欄
- [ ] 実動確認日を記録した
- [ ] `GET /blocks` 応答で一覧表示を確認した
- [ ] 一覧取得失敗時のフォールバック表示を確認した
- [ ] message 表示（一覧取得失敗）を確認した

#### 一覧取得系の残課題
- [ ] レスポンス項目の最終固定（型・必須/任意）
- [ ] dashboard 集計値の算出元フィールド整合
- [ ] 取得失敗時の再試行導線（手動/自動）の方針決定

#### 詳細取得系の残課題
- [ ] `GET /blocks/:blockId` 正常系の描画差分確認
- [ ] 404/不正ID時のプレースホルダ遷移確認
- [ ] 一覧フォールバック利用時の詳細整合ルール確定

## Step6 実装後の確認 (export / delete 本API接続)

### 実装後の確認項目
- [ ] Export API 実行: `POST /api/blocks/{id}/export` が実行される
- [ ] Delete API 実行: `DELETE /api/blocks/{id}` または互換 `POST /api/blocks/{id}/delete` が実行される
- [ ] 確認チェック未実施時に実行しないこと（LockGuard confirmed 未チェック時は service call しない）
- [ ] 認証入力不足時の fail-safe（`success=false` を message 表示し、再描画しない）
- [ ] 成功時再描画（block 一覧/詳細、Dashboard、接続管理、Audit Log、message）
- [ ] 失敗時 UI 安定性（message 表示のみで画面崩壊・不要再描画なし）

### LockGuard 導線の確認
- [ ] Export ボタン押下 → LockGuard 表示（state=ready）
- [ ] Delete ボタン押下 → LockGuard 表示（state=ready）
- [ ] LockGuard 表示中に blockId / actionType が正しく保持されている
- [ ] confirmed 未チェック → execute 時に中断されメッセージ表示
- [ ] cancel ボタンで LockGuard がリセットされる
- [ ] 実行後に LockGuard がリセットされ入力値が残らない

### 認証 fail-safe 確認
- [ ] password 空欄のまま execute → `success=false` が返りメッセージ表示
- [ ] twoFactorCode 空欄のまま execute → `success=false` が返りメッセージ表示
- [ ] confirmationText 不一致のまま execute → `success=false` が返りメッセージ表示
- [ ] 認証失敗時に block の状態（deleteRequested 等）が変化しない
- [ ] 認証失敗後に LockGuard が開いたまま再入力できる状態を維持する

### export / delete 系の残課題
- [ ] Delete 成功後の block 表示除外または deleteRequested 反映の最終仕様確認
- [ ] Export 成功応答の shape 確定（block オブジェクト有無）
- [ ] 認証情報の POST body への含め方の最終確認（authInfo 全渡し vs 必要フィールドのみ）
- [ ] API 失敗時の再試行導線追加（未対応）
- [ ] 同一 blockId への連続 export / delete の制御強化（未対応）

### Step2: 詳細取得系
- 着手条件
	- [ ] `GET /blocks/:blockId` の詳細項目が確定している
	- [ ] 詳細表示で必要な handshake / freeze / deleteRequested の扱いが決まっている
- 確認項目
	- [ ] block 選択時に詳細が更新される
	- [ ] 詳細取得失敗時に直前表示を維持できる
	- [ ] warning / lockguard 用の元データとして再利用できる
- まだやらないこと
	- [ ] freeze / unfreeze 実行
	- [ ] export / delete 実行

### Step2 実装後の確認項目
- [ ] 詳細ボタン押下で GET /api/blocks/{id} が発行される
- [ ] GET /api/blocks/{id} の path parameter に選択中 blockId が入る
- [ ] 詳細取得成功時に Dashboard 側と Block管理側が同じ内容で更新される
- [ ] 詳細取得失敗時に UI が崩れない
- [ ] 詳細取得失敗時に詳細パネルがプレースホルダー表示へ戻る
- [ ] 詳細取得失敗時に message が表示される
- [ ] 404 / 500 / timeout を Network タブで切り分け確認できる
- [ ] 詳細取得失敗時に Console に未処理例外が残らない
- [ ] 一覧・Dashboard・接続/切断管理・危険操作導線に回帰影響がない

### 詳細取得系の残課題
- [ ] 404 / 5xx / timeout の表示文言と扱いを最終固定する
- [ ] 詳細レスポンス項目の必須/任意を最終固定する
- [ ] 詳細取得失敗時の再試行導線を決める
- [ ] 一覧フォールバック時の詳細整合ルールを最終化する
- [ ] 詳細取得成功直後の再選択時に race condition を起こさない条件を固定する

## Step5 実装後チェック（freeze / unfreeze）

### Step5 実装後の確認項目
- [ ] `POST /api/blocks/{id}/freeze` が期待どおり発行される
- [ ] `POST /api/blocks/{id}/unfreeze` が期待どおり発行される
- [ ] 成功時に `freezeStatus` が `frozen/active` へ正しく反映される
- [ ] 成功時に一覧・詳細・Dashboard・接続管理・監査ログが再描画される
- [ ] 失敗時に状態を変更せず message のみ更新される

### freeze / unfreeze 系の残課題
- [ ] 失敗時メッセージ文言の最終統一
- [ ] fallback 継続条件の明文化（HTTP種別・エラー種別）
- [ ] 二重実行抑止の閾値と解除条件の固定
- [ ] API timeout 時の再試行方針（手動/自動）を最終化

### 警告表示導線の確認欄
- [ ] freeze 選択時に warning 表示が有効になる
- [ ] unfreeze 選択時に warning 表示が有効になる
- [ ] 確認チェック未同意では execute を無効化する
- [ ] blockId/actionType 欠如時は実行せずメッセージ表示で停止する

### fail-safe 確認欄
- [ ] API失敗時に再描画を停止し、既存表示を維持する
- [ ] service例外時に未処理例外を残さずメッセージ表示へ退避する
- [ ] `response.success !== true` で安全側の fallback 分岐に入る
- [ ] 連続失敗時に危険操作を中断できる

### 選択中 block の保持に関する注意点
- 選択値は null / 空文字を同一扱いで正規化する
- 最新選択のみ描画反映し、古い非同期応答は破棄する
- 詳細取得失敗時は選択状態と表示状態を切り分けて扱う
- 一覧再描画後も選択中 blockId の再解決可否を先に判定する
- 画面再描画後も選択中 blockId の一致確認を行う

### Step3: 接続/切断系
- 着手条件
	- [ ] `POST /blocks/:blockId/connect` と `POST /blocks/:blockId/disconnect` の契約が確定している
	- [ ] handshake 状態更新 API の扱いが決まっている
- 確認項目
	- [ ] pending / success / failed の表示更新が崩れない
	- [ ] 二重実行防止が維持される
	- [ ] 実行後に一覧・詳細・dashboard が再描画される
- まだやらないこと
	- [ ] settings 更新
	- [ ] 危険操作フロー

### Step3 実装後の確認項目
- [ ] 接続ボタン押下で `POST /api/blocks/{id}/connect` が発行される
- [ ] 切断ボタン押下で `POST /api/blocks/{id}/disconnect` が発行される
- [ ] 成功時に一覧・詳細・Dashboard・接続/切断管理・Audit Log・message が再描画される
- [ ] 失敗時に UI が崩れず message のみ表示される
- [ ] 失敗時に Console に未処理例外が残らない
- [ ] 二重実行防止が維持される
- [ ] `getBlocks()` / `getBlockById()` / `disconnectBlock()` に回帰影響がない

### Step3 実動確認済みチェック欄
- [ ] 実動確認日を記録した
- [ ] connect の成功系を確認した
- [ ] disconnect の成功系を確認した
- [ ] connect の失敗系を確認した
- [ ] disconnect の失敗系を確認した
- [ ] message 表示を確認した

### 接続/切断系の残課題
- [ ] `POST /blocks/:blockId/connect` レスポンス項目の最終固定（型・必須/任意）
- [ ] `POST /blocks/:blockId/disconnect` レスポンス項目の最終固定
- [ ] API 失敗時のリトライ導線（手動/自動）の方針決定
- [ ] fallback（mock 更新）を廃止する条件と時期の確定

### 接続/切断系の残課題（実動確認観点）
- [ ] success=false 応答時の表示方針を固定する
- [ ] fallback 時の audit log 記録内容を確認する
- [ ] API 応答 block と再描画結果の差分を確認する
- [ ] message 文言の統一を確認する

### handshake 状態整合の確認欄
- [ ] 接続成功後に handshakeStatus が `success` に更新される
- [ ] 切断成功後に handshakeStatus が適切な状態に更新される
- [ ] API 失敗後に handshakeStatus が不整合状態にならない
- [ ] pending 中に再実行しても handshakeStatus が二重更新されない
- [ ] `POST /blocks/{id}/handshake` の本格接続前後で表示整合を確認する

### 再描画確認欄
- [ ] 接続成功時に Block 一覧が更新される
- [ ] 接続成功時に Block 詳細が更新される
- [ ] 接続成功時に Dashboard が更新される
- [ ] 接続成功時に 接続/切断管理 が更新される

### Step4 実装後の確認項目
- [ ] Audit Log 一覧取得成功時に Dashboard 最新ログと Audit 一覧が更新される
- [ ] Audit Log 件数取得成功時に件数表示が更新される
- [ ] Settings 取得成功時に settings パネルの各値が反映される
- [ ] Settings 保存成功時に settings パネル再取得と Audit Log 再描画が行われる
- [ ] Step1〜Step3 の一覧・詳細・接続/切断・危険操作導線に回帰影響がない

### audit / settings 系の残課題
- [ ] `/audit-logs` 応答 shape の最終固定（items/logs/data の統一）
- [ ] `/audit-logs/count` 応答 shape の最終固定（count の型とキー）
- [ ] `/settings/security` 応答 shape の最終固定（Boolean/Number の必須・任意）
- [ ] フィルタ条件（action/result）の大小文字・部分一致ルールを固定
- [ ] fallback（mock/既存表示維持）を解除する時期を確定

### settings 保存 fail-safe の確認欄
- [ ] 保存API失敗時にフォーム表示が崩れない
- [ ] 保存API失敗時に値の不整合（意図しない上書き）が起きない
- [ ] 保存API失敗時に message 表示のみで処理停止する
- [ ] 保存API連打時に二重送信防止（ボタン disable）が維持される
- [ ] 保存成功後に save ボタンが再度有効化される

### Step4: Audit / Settings 実動確認チェック欄
- [ ] Audit Log 一覧取得成功時に一覧と件数が更新される
- [ ] Audit Log 一覧取得失敗時に既存表示維持またはプレースホルダー表示 + message になる
- [ ] Settings 取得成功時にフォームへ値が反映される
- [ ] Settings 取得失敗時に既存表示維持またはプレースホルダー表示 + message になる
- [ ] Settings 保存成功時に message 表示後、フォーム表示と Audit Log 表示が再同期される
- [ ] Settings 保存失敗時に UI が崩れず message 表示のみで fail-safe 停止する
- [ ] 接続成功時に Audit Log が更新される
- [ ] 接続成功時に message が更新される
- [ ] 切断成功時に Block 一覧が更新される
- [ ] 切断成功時に Block 詳細が更新される
- [ ] 切断成功時に Dashboard が更新される
- [ ] 切断成功時に 接続/切断管理 が更新される
- [ ] 切断成功時に Audit Log が更新される
- [ ] 切断成功時に message が更新される
- [ ] 失敗時に UI が崩れない

### Step4: audit / settings 系
- 着手条件
	- [ ] `GET /audit-logs` 系と `GET/PUT /settings/security` の契約が確定している
	- [ ] filter / count / recent log の返却形式が決まっている
- 確認項目
	- [ ] audit 一覧・件数・recent log が更新される
	- [ ] settings 初期表示が崩れない
	- [ ] 取得失敗時に既存表示維持とメッセージ表示ができる
- まだやらないこと
	- [ ] appendAuditLog の本番責務整理
	- [ ] 危険操作の監査記録最適化

### Step5: freeze / unfreeze 系
- 着手条件
	- [ ] `POST /blocks/:blockId/freeze` と `POST /blocks/:blockId/unfreeze` の契約が確定している
	- [ ] 実行前警告で必要な確認項目が確定している
- 確認項目
	- [ ] warning 表示から execute まで既存フローが壊れない
	- [ ] confirmed 未実施時に fail-safe で停止する
	- [ ] success 時のみ一覧・詳細・Dashboard・接続/切断管理・Audit Log・message の再描画が走る
	- [ ] 実行後に一覧・詳細・audit 表示が更新される
- まだやらないこと
	- [ ] export / delete 接続
	- [ ] 認証方式の最終確定

### Step5 実動確認済みチェック欄
- [ ] Freeze API 実行
        - [ ] freeze ボタン押下で `POST /api/blocks/{id}/freeze` が発行される
        - [ ] 成功時に一覧・詳細・Dashboard・接続/切断管理・Audit Log・message が再描画される
        - [ ] 失敗時に UI が崩れず message のみ表示される
- [ ] Unfreeze API 実行
        - [ ] unfreeze ボタン押下で `POST /api/blocks/{id}/unfreeze` が発行される
        - [ ] 成功時に一覧・詳細・Dashboard・接続/切断管理・Audit Log・message が再描画される
        - [ ] 失敗時に UI が崩れず message のみ表示される
- [ ] 成功時再描画
        - [ ] block 一覧の freezeStatus が更新される
        - [ ] block 詳細の freezeStatus が更新される
        - [ ] Dashboard 集計が変更反映される
        - [ ] 接続/切断管理パネルが更新される
        - [ ] Audit Log に freeze/unfreeze アクションが記録される
- [ ] 警告表示導線の確認欄
	- [ ] freeze-warning が対象 block と actionType を保持する
	- [ ] warning 表示から execute まで既存導線が壊れない
	- [ ] confirm の再操作で execute 可否が追える
- [ ] 失敗時 UI 安定性
        - [ ] API 失敗後に blockId が二重実行されない
        - [ ] 失敗時に freezeStatus の状態が不整合にならない
        - [ ] 失敗時に Console に未処理例外が残らない
        - [ ] freeze / unfreeze 後の再選択が正常に動作する
- [ ] fail-safe 確認欄
	- [ ] blockId または actionType 不正時に service call せず停止する
	- [ ] confirm 未実施時に service call せず message 表示へ寄る
	- [ ] success=false 応答時に再描画せず message 表示へ寄る
- [ ] 確認チェック未実施時に実行しないこと
        - [ ] freeze-warning-confirm チェック未実施時に実行ボタンが disable される
        - [ ] 確認チェック未実施で execute ボタン押下時に警告メッセージが表示される
	- [ ] 確認チェック未実施時は freeze / unfreeze API が発行されない
        - [ ] 警告表示の導線が壊れない

### Step5: freeze / unfreeze 系の残課題
- [ ] freezeStatus 更新時の getFreezeDangerMeta() との整合ルール確定
- [ ] freeze / unfreeze 失敗時の message 文言統一
- [ ] API 失敗時の再試行導線方針決定
	- [ ] 警告表示導線の文言と状態管理の最終統一
	- [ ] fail-safe 時の message 優先順位を固定
	- [ ] 認証 UI の拡張

### Step4 実動確認済みチェック欄
- [ ] 実動確認日を記録した
- [ ] Audit Log 一覧更新（成功系）を確認した
- [ ] Audit Log 件数更新（成功系）を確認した
- [ ] Settings 描画更新（取得成功系）を確認した
- [ ] Settings 保存後 message 表示（成功系）を確認した
- [ ] 失敗系で UI が崩れないことを確認した

### audit / settings 系の残課題（実動確認後）
- [ ] Audit Log API 失敗時の message 文言統一
- [ ] Audit Log fallback 時の件数整合ルール固定
- [ ] Settings 取得失敗時のプレースホルダー文言統一
- [ ] Settings 保存失敗時の再試行導線方針決定

### settings 保存 fail-safe 確認欄
- [ ] 保存失敗時にフォームが壊れない
- [ ] 保存失敗時に直前表示を維持できる
- [ ] 保存失敗時に message 表示のみで停止する
- [ ] 保存ボタン disable/enable が復帰する

### Audit Log fallback 確認欄
- [ ] 一覧取得失敗時に既存表示を維持できる
- [ ] 一覧取得失敗時にプレースホルダー復帰できる
- [ ] fallback 時でも件数表示が崩れない
- [ ] result/action フィルタ適用時も UI が崩れない

---

## 全API通し確認シナリオ

> 一覧→詳細→接続→凍結→設定→監査→危険操作の順で実施する。

| # | 操作 | 確認したいこと |
|---|------|----------------|
| 1 | 一覧表示 | `GET /blocks` が発行され、block 一覧が崩れず表示される |
| 2 | 詳細表示 | block 選択で `GET /blocks/{id}` が発行され、詳細パネルが更新される |
| 3 | Connect | `POST /blocks/{id}/connect` が発行され、connectionStatus が `connected` へ反映される |
| 4 | Disconnect | `POST /blocks/{id}/disconnect` が発行され、connectionStatus が `disconnected` へ反映される |
| 5 | Freeze | 警告確認チェック後に `POST /blocks/{id}/freeze` が発行され、freezeStatus が `frozen` へ反映される |
| 6 | Unfreeze | 警告確認チェック後に `POST /blocks/{id}/unfreeze` が発行され、freezeStatus が `active` へ反映される |
| 7 | Settings 読み込み | `GET /settings/security` が発行され、フィールドに現在値が反映される |
| 8 | Settings 保存 | `PUT /settings/security` が発行され、成功 message が表示される |
| 9 | Audit Log 確認 | `GET /audit-logs` が発行され、各操作の記録が一覧に表示される |
| 10 | Export | LockGuard 認証通過後に `POST /blocks/{id}/export` が発行され、成功時に再描画される |
| 11 | Delete | LockGuard 認証通過後に `DELETE /blocks/{id}` が発行され、成功時に deleteRequested が反映される |

### 通し確認の共通チェック
- [ ] 各操作後に Audit Log に記録が追記される
- [ ] 各操作後に Dashboard 集計が最新値に更新される
- [ ] 各操作後に block 一覧・詳細が最新状態で再描画される
- [ ] いずれかの API が失敗しても他の操作が継続できる
- [ ] message 表示が操作ごとに正しく切り替わる

### 通し確認の fail-safe チェック
- [ ] confirmed 未チェックで freeze / export / delete が中断される
- [ ] 認証情報不足で export / delete が中断され block 状態が変化しない
- [ ] API 失敗後も一覧・詳細の表示状態が変化しない
- [ ] 二重クリックによる二重実行が pending 制御で止まる

---

## 危険操作 解放条件（2026-03-23）

> **未達条件が1つでも残る場合は解放しない。**

### Freeze
- [ ] 本API（POST /blocks/:blockId/freeze）に差し替え済み
- [ ] 正常系: 成功レスポンス後に freezeStatus が `frozen` へ反映される
- [ ] 異常系: success=false 時に状態変化なし・message のみ表示
- [ ] fail-safe: confirmed 未チェックで実行されない
- [ ] fail-safe: 対象 blockId 不在・状態不正で service call されない
- [ ] message: 成功・失敗それぞれの文言が画面に出る
- [ ] 監査ログ: 操作後に Audit Log へ記録が追記される

### Unfreeze
- [ ] 本API（POST /blocks/:blockId/unfreeze）に差し替え済み
- [ ] 正常系: 成功レスポンス後に freezeStatus が `active` へ反映される
- [ ] 異常系: success=false 時に状態変化なし・message のみ表示
- [ ] fail-safe: confirmed 未チェックで実行されない
- [ ] fail-safe: 対象 blockId 不在・状態不正で service call されない
- [ ] message: 成功・失敗それぞれの文言が画面に出る
- [ ] 監査ログ: 操作後に Audit Log へ記録が追記される

### Export
- [ ] 本API（POST /blocks/:blockId/export）に差し替え済み
- [ ] LockGuard: password / twoFactorCode / confirmationText / confirmed の全検証が通る
- [ ] LockGuard: 認証失敗時に実行されず認証フォームが維持される
- [ ] 正常系: 成功レスポンス後に一覧・詳細・Audit Log が再描画される
- [ ] 異常系: success=false 時に状態変化なし・message のみ表示
- [ ] fail-safe: confirmed 未チェック・認証不足で実行されない
- [ ] fail-safe: 取り消し不能であることを UI 上で明示している
- [ ] message: 成功・失敗・認証失敗それぞれの文言が画面に出る
- [ ] 監査ログ: 操作後に Audit Log へ記録が追記される

### Delete
- [ ] 本API（DELETE /blocks/:blockId）に差し替え済み
- [ ] LockGuard: password / twoFactorCode / confirmationText / confirmed の全検証が通る
- [ ] LockGuard: 認証失敗時に実行されず認証フォームが維持される
- [ ] 正常系: 成功レスポンス後に対象 block が一覧から除去・Audit Log に記録
- [ ] 異常系: success=false 時に状態変化なし・message のみ表示
- [ ] fail-safe: confirmed 未チェック・認証不足で実行されない
- [ ] fail-safe: 取り消し不能であることを UI 上で明示している
- [ ] message: 成功・失敗・認証失敗それぞれの文言が画面に出る
- [ ] 監査ログ: 操作後に Audit Log へ記録が追記される

---

## 異常系確認シナリオ（connect / disconnect / freeze / unfreeze）

### Connect 失敗
- [ ] connect API 失敗時に message が表示される
- [ ] connect API 失敗時に handshake が failed へ遷移する
- [ ] connect API 失敗時に一覧/詳細/接続管理パネルの表示が壊れない

### Disconnect 失敗
- [ ] disconnect API 失敗時に message が表示される
- [ ] disconnect API 失敗時に handshake が failed へ遷移する
- [ ] disconnect API 失敗時に一覧/詳細/接続管理パネルの表示が壊れない

### Freeze 失敗
- [ ] Freeze 実行で success=false 応答時に message が表示される
- [ ] Freeze 実行失敗時に警告表示導線（warning UI）が維持される
- [ ] Freeze 実行失敗時に一覧/詳細/Dashboard の状態が変化しない

### Unfreeze 失敗
- [ ] Unfreeze 実行で success=false 応答時に message が表示される
- [ ] Unfreeze 実行失敗時に警告表示導線（warning UI）が維持される
- [ ] Unfreeze 実行失敗時に一覧/詳細/Dashboard の状態が変化しない

### 状態が壊れないか
- [ ] connect/disconnect 失敗後も block 一覧を再操作できる
- [ ] freeze/unfreeze 失敗後も warning 確認チェック導線を再操作できる
- [ ] 失敗直後に別 block を選択しても詳細表示が崩れない
- [ ] 連続失敗時も UI 全体が操作不能にならない

### message が適切か
- [ ] connect 失敗時に接続失敗を示す message が表示される
- [ ] disconnect 失敗時に切断失敗を示す message が表示される
- [ ] freeze/unfreeze 失敗時に危険操作失敗を示す message が表示される
- [ ] 失敗後に次操作を行うと message が適切に上書きされる

---

## 稼働開始前 最終チェックリスト（2026-03-23）

> すべての項目に ✅ が入るまで稼働開始しない。

### 環境・接続
- [ ] API_BASE_URL が正しい環境値に設定されている
- [ ] services マップの各関数が API 版に差し替わっている
- [ ] mock データへの直接参照が script.js に残っていない
- [ ] fetch / API エラー時のフォールバックが設定されている
- [ ] 本番環境の CORS / 認証ヘッダーが正しく設定されている

### 表示確認
- [ ] 一覧表示: GET /blocks が発行され一覧が崩れず表示される
- [ ] 詳細表示: GET /blocks/{id} が発行され詳細パネルが更新される
- [ ] Dashboard: 集計値が一覧データと整合している
- [ ] Audit Log: GET /audit-logs が発行されログ一覧が表示される
- [ ] Settings 読み込み: GET /settings が発行されフォームに現在値が反映される

### 操作確認
- [ ] Connect / Disconnect: API 発行・connectionStatus 反映・一覧整合を確認済み
- [ ] Settings 保存: PATCH /settings 発行・リロード後の値保持を確認済み（本API接続後）
- [ ] Audit Log 更新: 各操作後に自動追記されることを確認済み

### fail-safe 確認
- [ ] confirmed 未チェックで freeze / export / delete が実行されない
- [ ] 認証不足で export / delete が中断される
- [ ] pending 中の二重実行が防止される
- [ ] API 失敗時に state 不整合が起きない

### 異常系確認
- [ ] 各 API 失敗時に message のみ表示され UI 状態が変化しない
- [ ] Console に未処理例外が残っていない

### 再描画整合確認
- [ ] 操作後に一覧・詳細・Dashboard・Audit Log が一致している
- [ ] 失敗後に既存表示が維持される

### message 表示確認
- [ ] 成功・失敗・認証失敗それぞれの message が正しく表示される
- [ ] 連続操作時に message が最新結果で上書きされる

### 危険操作解放判定
- [ ] Freeze / Unfreeze: 解放条件をすべて確認済み（本API・正常系・異常系・fail-safe・message・Audit Log）
- [ ] Export / Delete: 解放条件をすべて確認済み（本API・LockGuard全検証・取り消し不能明示・全確認）
- [ ] 未達条件がある場合は該当操作を保留のまま稼働開始する

---

## 先行稼働機能 起動前チェック（2026-03-23）

> 先行稼働対象の起動前に必須確認。未達があれば起動しない。

- [ ] API_BASE_URL確認: 環境値（本番/ステージング）が正しい
- [ ] 一覧表示確認: GET /blocks で一覧が崩れず表示される
- [ ] 詳細表示確認: GET /blocks/{id} で詳細が更新される
- [ ] Dashboard確認: 表示集計が一覧データと一致する
- [ ] Audit Log参照確認: GET /audit-logs でログ表示が更新される
- [ ] Settings参照確認: GET /settings で現在値が反映される
- [ ] Connect/Disconnect確認: API発行後の接続状態が一覧/詳細に反映される
- [ ] message表示確認: 成功/失敗の message が正しく表示される
- [ ] 再描画整合確認: 操作後に一覧・詳細・Dashboard・Audit Log が一致する

---

## 危険操作 解放可否 再判定（稼働拡大・2026-03-23）

### Freeze
- 正常系確認済み: 済
- 異常系確認済み: 済
- fail-safe確認済み: 済
- LockGuard確認済み: 対象外（Freeze は LockGuard 非対象）
- 監査ログ更新確認済み: 済
- 通し確認済み: 一部済（追加監視で最終確認）
- 小規模稼働で重大異常なし: はい
- 判定結果: まだ条件付き

### Unfreeze
- 正常系確認済み: 済
- 異常系確認済み: 済
- fail-safe確認済み: 済
- LockGuard確認済み: 対象外（Unfreeze は LockGuard 非対象）
- 監査ログ更新確認済み: 済
- 通し確認済み: 一部済（追加監視で最終確認）
- 小規模稼働で重大異常なし: はい
- 判定結果: まだ条件付き

### Export
- 正常系確認済み: 未
- 異常系確認済み: 未
- fail-safe確認済み: 未
- LockGuard確認済み: 未
- 監査ログ更新確認済み: 未
- 通し確認済み: 未
- 小規模稼働で重大異常なし: 判定対象外（未解放）
- 判定結果: 未解放維持

### Delete
- 正常系確認済み: 未
- 異常系確認済み: 未
- fail-safe確認済み: 未
- LockGuard確認済み: 未
- 監査ログ更新確認済み: 未
- 通し確認済み: 未
- 小規模稼働で重大異常なし: 判定対象外（未解放）
- 判定結果: 未解放維持

---

## Level4 解放直前チェック欄（実行フェーズ固定）

> Level4 は最終危険操作段階。全項目グリーンでなければ解放しない。

### 環境・前提確認
- [ ] API_BASE_URL が本番相当の正しい向き先であることを確認した
- [ ] Level3 監視サイクルで即停止相当の重大異常が発生していないことを確認した
- [ ] Level1 / Level2 / Level3 の API が現時点で正常応答していることを確認した

### LockGuard 確認
- [ ] POST /blocks/{id}/export で LockGuard が正しく表示されることを確認した
- [ ] DELETE /blocks/{id} で LockGuard が正しく表示されることを確認した
- [ ] LockGuard がキャンセルで正しく閉じることを確認した
- [ ] LockGuard が操作完了後に正しく閉じることを確認した

### 認証・fail-safe 確認
- [ ] password 未入力時に POST /blocks/{id}/export が実行されないことを確認した
- [ ] twoFactorCode 未入力時に POST /blocks/{id}/export が実行されないことを確認した
- [ ] confirmationText 未入力時に DELETE /blocks/{id} が実行されないことを確認した
- [ ] confirmed 未チェック時に Export / Delete の API が呼ばれないことを確認した
- [ ] 全フィールド入力 + confirmed チェック後のみ API が呼ばれることを確認した（fail-safe 正常）

### API 実行結果確認
- [ ] POST /blocks/{id}/export 成功時に一覧・詳細・管理パネルの状態が整合することを確認した
- [ ] POST /blocks/{id}/export 後に Audit Log へ action/target/result が追記されることを確認した
- [ ] POST /blocks/{id}/export 後に message が結果に一致して表示されることを確認した
- [ ] DELETE /blocks/{id} 成功時に一覧・詳細・管理パネルの状態が整合することを確認した
- [ ] DELETE /blocks/{id} 後に Audit Log へ action/target/result が追記されることを確認した
- [ ] DELETE /blocks/{id} 後に message が結果に一致して表示されることを確認した

### 再描画・整合確認
- [ ] Export/Delete 後に一覧・詳細・Dashboard・Audit Log が同時に整合することを確認した
- [ ] Level1 / Level2 / Level3 の API が巻き込まれて異常応答していないことを確認した

### 解放判断
- [ ] 上記全項目グリーンであることを最終確認した
- [ ] 解放判断者の承認を得た

## Level4 対象外（実行フェーズ固定）

- Level4 解放対象 API は POST /blocks/{id}/export と DELETE /blocks/{id} のみ
- Level1〜3 の API は継続監視に移行

---

## 最終運用判定フェーズ 本運用に進める条件（固定）

> 以下を全て満たした場合のみ本運用に進めてよい。1項目でも満たさない場合は本運用移行を保留する。

- [ ] Level1〜Level4 監視で重大異常（即停止事象）が1件もない
- [ ] 再描画整合が保たれている（全 API 実行後の画面整合が全回正常）
- [ ] message 表示が適切（全 API の成功・失敗・認証失敗の応答が表示と常に一致）
- [ ] Audit Log 更新が安定（全操作 API で action / target / result が欠落なく追記され、欠落・不整合が1件もない）
- [ ] Settings 保存 API が安定（PATCH 後に反映され、空欄化・巻き戻りが発生しない）
- [ ] Connect / Disconnect API が安定（POST /connect・POST /disconnect 後の状態整合が全回正常）
- [ ] Freeze / Unfreeze API が安定（POST /freeze・POST /unfreeze で confirmed 導線・Audit Log・状態整合が全回正常）
- [ ] Export API が安定（POST /blocks/{id}/export で LockGuard・confirmed・認証・Audit Log・状態整合が全回正常）
- [ ] Delete API が安定（DELETE /blocks/{id} で Export 条件を満たし、削除後の3画面整合が全回取れている）
- [ ] LockGuard / 認証 / fail-safe が安定（confirmed 未チェック・認証不足で API 呼び出しが通ったことが1件もない）
- [ ] 全項目を満たしたと判断し、本運用移行を決定した

---

## 最終運用開始フェーズ 本運用開始直前チェック欄（固定）

- [ ] API_BASE_URL確認: 本番向け API_BASE_URL が想定値で固定されている
- [ ] Level1〜Level4 判定完了確認: 各レベルの判定記録・承認記録が完了している
- [ ] 一覧/詳細表示確認: 参照 API 応答が一致し、表示崩れがない
- [ ] Dashboard確認: 集計 API 応答と表示値が一致している
- [ ] Audit Log確認: 参照 API で action / target / result が欠落なく取得できる
- [ ] Settings 参照/保存確認: 参照 API と保存 API（PATCH）が正常応答し反映される
- [ ] Connect/Disconnect確認: 接続系 API 実行後に状態 API 応答と表示が一致する
- [ ] Freeze/Unfreeze確認: 実行 API が confirmed 条件でのみ通過し、状態 API と整合する
- [ ] Export/Delete確認: POST /blocks/{id}/export と DELETE /blocks/{id} が条件充足時のみ通過する
- [ ] LockGuard確認: LockGuard 導線の前提条件が API 実行条件と一致している
- [ ] message表示確認: API 応答結果と UI message が一致している
- [ ] 再描画整合確認: API 実行後に一覧・詳細・Dashboard・Audit Log の再取得結果が整合する
- [ ] fail-safe確認: confirmed 未チェック・認証不足で API 呼び出しが拒否される
- [ ] 上記全項目を満たしたため本運用開始可と判断した
