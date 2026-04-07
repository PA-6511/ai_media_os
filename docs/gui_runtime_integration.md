# GUI Runtime Integration

## 目的
- 本番API接続前の段階で、GUIのruntime連携方針を明確化する
- mock実装から本実装へ移行する際の差分を最小化する
- 実装前レビューで確認すべき項目を固定化する

## 現在の接続状況
- UI表示: mockデータ経由で表示
- 一覧取得: service経由で取得
- 危険操作: service関数は存在するがUI未接続
- 実API: 未接続

## 次に接続する対象
- block一覧再取得のトリガー
- connect / disconnect のUI操作
- export / delete のUI操作
- audit log 一覧の更新反映

## 失敗時の挙動
- 認証未完了時: `success: false` とメッセージ表示
- 対象未存在時: `success: false` とメッセージ表示
- service例外時: UIで安全なエラーメッセージを表示
- 失敗時は状態を変更しない

## テスト観点
- 一覧表示: 初期表示でblock一覧が描画される
- 認証分岐: password / twoFactorCode / confirmed の欠落時に失敗
- 成功分岐: export / delete で成功オブジェクトが返る
- 監査ログ: appendAuditLog で配列に追記される
- 非接続確認: 実API呼び出しが含まれていない

## 保留項目
- APIクライアント層の導入タイミング
- エラーコード設計（message文字列以外の形式）
- 再試行方針（手動再実行 / 自動再試行）
- 監査ログの永続化方式

## 本API接続対象の棚卸し（事前レビュー用）

### mockのまま維持する箇所（本接続まで）
- block一覧取得: mock service の固定レスポンスを継続
- block詳細取得: ローカルスタブレスポンスを継続
- connect / disconnect: UIイベントは mock service 呼び出しのまま
- freeze / unfreeze: UIイベントは mock service 呼び出しのまま
- export / delete: 疑似成功レスポンスのまま
- audit log 取得: append型のローカル追記を継続
- settings 取得 / 更新: ローカル状態のみ更新
- handshake 状態取得 / 更新: ローカルフラグ更新のみ

### 本APIに置換予定の箇所
- block一覧取得
	- 置換予定: mock一覧取得 -> 本API GET /blocks
	- 置換単位: service層の一覧取得関数
- block詳細取得
	- 置換予定: mock詳細取得 -> 本API GET /blocks/:blockId
	- 置換単位: service層の詳細取得関数
- connect / disconnect
	- 置換予定: mock操作 -> 本API POST /blocks/:blockId/connect, POST /blocks/:blockId/disconnect
	- 置換単位: 危険操作ハンドラの service 呼び出し
- freeze / unfreeze
	- 置換予定: mock操作 -> 本API POST /blocks/:blockId/freeze, POST /blocks/:blockId/unfreeze
	- 置換単位: 危険操作ハンドラの service 呼び出し
- export / delete
	- 置換予定: mock操作 -> 本API POST /blocks/:blockId/export, DELETE /blocks/:blockId
	- 置換単位: 実行ボタンの service 呼び出し
- audit log 取得
	- 置換予定: ローカルappend -> 本API GET /audit-logs
	- 置換単位: ログ一覧取得/更新処理
- settings 取得 / 更新
	- 置換予定: ローカル状態更新 -> 本API GET /settings, PATCH /settings
	- 置換単位: 設定画面ロード/保存処理
- handshake 状態取得 / 更新
	- 置換予定: ローカルフラグ更新 -> 本API GET /handshake, PATCH /handshake
	- 置換単位: handshake状態表示/更新処理

## 失敗時挙動と fail-safe 導線（本API接続前レビュー）

### 失敗系の整理
- 一覧取得失敗
	- 表示: 一覧は空表示メッセージを出す
	- 挙動: 既存の選択状態を維持し、危険操作は実行しない
- 詳細取得失敗
	- 表示: 詳細プレースホルダー表示
	- 挙動: 詳細依存の実行導線を中断
- connect / disconnect 失敗
	- 表示: 失敗メッセージ表示
	- 挙動: handshake を `failed` へ更新し、後続処理は中断
- freeze / unfreeze 失敗
	- 表示: 失敗メッセージ表示
	- 挙動: 対象状態は変更しない
- export / delete 認証失敗
	- 表示: 認証失敗メッセージ表示
	- 挙動: 実行キュー投入を中断し、対象状態は変更しない
- settings 保存失敗
	- 表示: 設定保存失敗メッセージ表示
	- 挙動: 画面の値は再描画時に既存値へ戻す
- log 更新失敗
	- 表示: ログ領域は空状態メッセージ表示
	- 挙動: 操作本体は継続し、ログ反映のみ中断

### fail-safe で停止/中断する項目
- lockguard 状態が `ready` でない場合は export / delete を停止
- blockId 不在または actionType 不正の場合は危険操作を停止
- 確認チェック未同意の場合は freeze / unfreeze / export / delete を停止
- 同一 blockId + actionType が pending の場合は二重実行を停止
- service 例外発生時は UI 状態変更を中断し、メッセージのみ表示
