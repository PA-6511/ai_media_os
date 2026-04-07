# GUI Service 関数マッピング

## blockService 関数一覧と将来API対応先

| 現在の関数 | 責務 | 将来API |
|---|---|---|
| `getBlocks()` | block一覧取得 | GET /blocks |
| `getBlockById(blockId)` | block詳細取得 | GET /blocks/:blockId |
| `getConnectionManagementItems()` | 接続管理一覧取得 | GET /blocks （加工） |
| `getBlockDetailViewModel(blockId)` | 詳細viewmodel生成 | GET /blocks/:blockId （加工） |
| `getBlockDashboardStats()` | ダッシュボード集計 | GET /blocks （集計） |
| `connectBlock(blockId)` | connect操作 | POST /blocks/:blockId/connect |
| `disconnectBlock(blockId)` | disconnect操作 | POST /blocks/:blockId/disconnect |
| `freezeBlock(blockId)` | freeze操作 | POST /blocks/:blockId/freeze |
| `unfreezeBlock(blockId)` | unfreeze操作 | POST /blocks/:blockId/unfreeze |
| `exportBlock(blockId, authInfo)` | export操作（認証付き） | POST /blocks/:blockId/export |
| `deleteBlock(blockId, authInfo)` | delete操作（認証付き） | DELETE /blocks/:blockId |
| `getFreezeDangerMeta(blockId, type)` | freeze警告メタ取得 | GET /blocks/:blockId （加工） |
| `getLockGuardMeta(blockId, type)` | lockguard警告メタ取得 | GET /blocks/:blockId （加工） |
| `getHandshakeStatus(blockId)` | handshake状態取得 | GET /handshake/:blockId |
| `setHandshakeStatus(blockId, status)` | handshake状態更新 | PATCH /handshake/:blockId |

## logService 関数一覧と将来API対応先

| 現在の関数 | 責務 | 将来API |
|---|---|---|
| `getAuditLogs()` | audit log全件取得 | GET /audit-logs |
| `getRecentAuditLogs(limit)` | 新しい順のaudit log取得 | GET /audit-logs?limit={n} |
| `getAuditLogViewItems(filter)` | フィルタ済みlog取得 | GET /audit-logs?action=&result= |
| `getAuditLogCount(filter)` | フィルタ済みlog件数 | GET /audit-logs/count?action=&result= |
| `appendAuditLog(entry)` | audit log追記 | POST /audit-logs |
| `getSecuritySettings()` | settings取得 | GET /settings/security |
| `updateSecuritySettings(next)` | settings更新 | PUT /settings/security |

## script.js 側の主な利用箇所

### services.block.*
- `getBlocks` — `renderBlockRows`, `renderExportDeleteRows`
- `getConnectionManagementItems` — `renderConnectionManagementPanel`
- `getBlockDetailViewModel` — `renderSelectedBlockDetail`
- `getBlockDashboardStats` — `renderDashboardStats`
- `getFreezeDangerMeta` — `renderFreezeDangerWarning`
- `getLockGuardMeta` — `renderLockGuard`
- `connectBlock / disconnectBlock` — click handler (actionHandlers map)
- `freezeBlock / unfreezeBlock` — `executeFreezeDangerAction`
- `exportBlock / deleteBlock` — `executeLockGuardAction`
- `setHandshakeStatus` — connect / disconnect 前後の pending / success / failed 更新

### services.log.*
- `getAuditLogs` — `renderAuditLogRows`, `renderDashboardRecentLogs`
- `getAuditLogViewItems` / `getAuditLogCount` — `renderAuditLogRows`
- `getSecuritySettings` — `renderSecuritySettings`
- `getRecentAuditLogs` — `renderDashboardRecentLogs`（オプション）

## mock → 本API差し替え順番

1. `getBlocks` — 一覧が表示されるため影響範囲が最大。最初に差し替える
2. `getBlockById` / `getBlockDetailViewModel` — 詳細表示の正確性確認
3. `connectBlock` / `disconnectBlock` — 基本操作。handshake 連動あり
4. `getHandshakeStatus` / `setHandshakeStatus` — connect/disconnect と同時に確認
5. `freezeBlock` / `unfreezeBlock` — 警告フロー込みで確認
6. `getSecuritySettings` / `updateSecuritySettings` — 設定画面の動作確認
7. `getAuditLogs` / `appendAuditLog` — ログ永続化。操作ログの記録が正しいか確認
8. `exportBlock` / `deleteBlock` — 認証フロー最終確認。最後に差し替える

## APIエンドポイント設計たたき台（GUI→API）

- GET /blocks
	- 用途: block一覧・接続管理表示・ダッシュボード集計の元データ取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: renderBlockRows, renderExportDeleteRows, renderConnectionManagementPanel, renderDashboardStats

- GET /blocks/{id}
	- 用途: block詳細表示と警告メタ計算用データ取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: renderSelectedBlockDetail, renderFreezeDangerWarning, renderLockGuard

- POST /blocks/{id}/connect
	- 用途: 接続処理実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: actionHandlers の connect 操作

- POST /blocks/{id}/disconnect
	- 用途: 切断処理実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: actionHandlers の disconnect 操作

- POST /blocks/{id}/freeze
	- 用途: 凍結処理実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: executeFreezeDangerAction

- POST /blocks/{id}/unfreeze
	- 用途: 凍結解除処理実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: executeFreezeDangerAction

- POST /blocks/{id}/export
	- 用途: 認証付きエクスポート処理実行
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: executeLockGuardAction

- DELETE /blocks/{id} または POST /blocks/{id}/delete
	- 用途: 認証付き削除処理実行
	- 想定HTTPメソッド: DELETE を第一候補、互換要件時のみ POST /delete
	- GUI側利用箇所: executeLockGuardAction

- GET /audit-logs
	- 用途: 監査ログ取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: renderAuditLogRows, renderDashboardRecentLogs

- GET /settings/security
	- 用途: セキュリティ設定取得
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: renderSecuritySettings

- PUT /settings/security
	- 用途: セキュリティ設定更新
	- 想定HTTPメソッド: PUT
	- GUI側利用箇所: 設定保存ハンドラ（updateSecuritySettings 呼び出し元）

- GET /blocks/{id}/handshake
	- 用途: 接続前後の handshake 状態参照
	- 想定HTTPメソッド: GET
	- GUI側利用箇所: connect/disconnect 前後の状態表示更新

- POST /blocks/{id}/handshake
	- 用途: handshake 状態遷移の反映
	- 想定HTTPメソッド: POST
	- GUI側利用箇所: setHandshakeStatus 相当の API 呼び出し

- 運用メモ
	- 本セクションは mock から本APIへ差し替えるための接続設計たたき台
	- 既存の /settings, /handshake/:blockId 記載は互換確認として残置し、移行先は /settings/security と /blocks/{id}/handshake を優先

## blockService API差し替え設計（関数単位・最小版）

- `getBlocks`
	- 将来API: GET /blocks
	- 備考: 一覧の生データ取得

- `getBlockById`
	- 将来API: GET /blocks/{id}
	- 備考: 詳細表示の生データ取得

- `getConnectionManagementItems`
	- 将来API: GET /blocks
	- 備考: レスポンスを接続管理UI向けに整形

- `getBlockDetailViewModel`
	- 将来API: GET /blocks/{id}
	- 備考: レスポンスを詳細UI向けに整形

- `getBlockDashboardStats`
	- 将来API: GET /blocks
	- 備考: レスポンスをダッシュボード集計へ変換

- `connectBlock`
	- 将来API: POST /blocks/{id}/connect
	- 備考: 接続アクション実行

- `disconnectBlock`
	- 将来API: POST /blocks/{id}/disconnect
	- 備考: 切断アクション実行

- `freezeBlock`
	- 将来API: POST /blocks/{id}/freeze
	- 備考: 凍結アクション実行

- `unfreezeBlock`
	- 将来API: POST /blocks/{id}/unfreeze
	- 備考: 凍結解除アクション実行

- `exportBlock`
	- 将来API: POST /blocks/{id}/export
	- 備考: 認証情報付きエクスポート

- `deleteBlock`
	- 将来API: DELETE /blocks/{id}
	- 代替API: POST /blocks/{id}/delete
	- 備考: 認証情報付き削除

- `getFreezeDangerMeta`
	- 将来API: GET /blocks/{id}
	- 備考: freeze/unfreeze 前の警告メタをGUI側で生成

- `getLockGuardMeta`
	- 将来API: GET /blocks/{id}
	- 備考: export/delete 前の認証警告メタをGUI側で生成

- `getHandshakeStatus`
	- 将来API: GET /blocks/{id}/handshake
	- 備考: block単位の handshake 状態取得

- `setHandshakeStatus`
	- 将来API: POST /blocks/{id}/handshake
	- 備考: block単位の handshake 状態更新

## logService API差し替え設計（関数単位・最小版）

### audit 系

- `getAuditLogs`
	- 将来API: GET /audit-logs
	- 備考: 監査ログ全件取得

- `getRecentAuditLogs`
	- 将来API: GET /audit-logs?limit={n}
	- 備考: 新しい順で先頭 n 件を取得

- `getAuditLogViewItems`
	- 将来API: GET /audit-logs?action={action}&result={result}
	- 備考: 一覧表示向けのフィルタ済みデータ

- `getAuditLogCount`
	- 将来API: GET /audit-logs/count?action={action}&result={result}
	- 備考: フィルタ条件に一致する件数取得

- `appendAuditLog`
	- 将来API: POST /audit-logs
	- 備考: 監査ログ追記

### settings 系

- `getSecuritySettings`
	- 将来API: GET /settings/security
	- 備考: セキュリティ設定取得

- `updateSecuritySettings`
	- 将来API: PUT /settings/security
	- 備考: セキュリティ設定更新

## blockService 差し替えポイント（接続直前レビュー）

### 先に差し替える

- `getBlocks`
- `getBlockById`
- `connectBlock`
- `disconnectBlock`
- `getHandshakeStatus`
- `setHandshakeStatus`

### 後で差し替える

- `freezeBlock`
- `unfreezeBlock`
- `exportBlock`
- `deleteBlock`

- 方針メモ
	- 危険操作（freeze/unfreeze/export/delete）は後段で差し替える
	- 認証付き操作（export/delete）は最後に差し替える

## logService 差し替えポイント（本API接続直前レビュー）

### 先に差し替える

- `getAuditLogs`
- `getRecentAuditLogs`
- `getAuditLogViewItems`
- `getAuditLogCount`
- `getSecuritySettings`
- `updateSecuritySettings`

### 後で差し替える

- `appendAuditLog`

- 方針メモ
	- `appendAuditLog` は本番ではサーバ責務に寄る可能性がある前提で後段判断
