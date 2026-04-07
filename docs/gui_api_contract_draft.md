# GUI API契約たたき台

## API一覧
- `GET /api/v1/media/list` : メディア一覧取得
- `GET /api/v1/media/{media_id}` : メディア詳細取得
- `POST /api/v1/media/{media_id}/play` : 再生開始
- `POST /api/v1/media/{media_id}/stop` : 再生停止
- `PATCH /api/v1/settings` : 設定更新
- `POST /api/v1/logs/gui-event` : GUIイベントログ送信
- `POST /api/v1/session/refresh` : セッション更新

## 各APIの入力
- `GET /api/v1/media/list`
  - クエリ: `page`(int, 任意), `page_size`(int, 任意), `status`(string, 任意)
- `GET /api/v1/media/{media_id}`
  - パス: `media_id`(string, 必須)
- `POST /api/v1/media/{media_id}/play`
  - パス: `media_id`(string, 必須)
  - Body: `requested_by`(string, 必須), `position_sec`(number, 任意)
- `POST /api/v1/media/{media_id}/stop`
  - パス: `media_id`(string, 必須)
  - Body: `requested_by`(string, 必須), `reason`(string, 任意)
- `PATCH /api/v1/settings`
  - Body: `volume`(int, 任意), `auto_play`(bool, 任意), `locale`(string, 任意)
- `POST /api/v1/logs/gui-event`
  - Body: `event_type`(string, 必須), `screen`(string, 必須), `payload`(object, 任意), `occurred_at`(ISO8601, 必須)
- `POST /api/v1/session/refresh`
  - Body: `refresh_token`(string, 必須)

## 各APIの成功時返り値
- 共通
  - `success`: `true`
  - `request_id`: string
  - `timestamp`: ISO8601
- `GET /api/v1/media/list`
  - `data.items`: メディア配列
  - `data.pagination`: `page`, `page_size`, `total`
- `GET /api/v1/media/{media_id}`
  - `data`: `media_id`, `title`, `status`, `duration_sec`, `thumbnail_url`
- `POST /api/v1/media/{media_id}/play`
  - `data`: `media_id`, `status=playing`, `started_at`
- `POST /api/v1/media/{media_id}/stop`
  - `data`: `media_id`, `status=stopped`, `stopped_at`
- `PATCH /api/v1/settings`
  - `data`: `settings_version`, `applied_settings`
- `POST /api/v1/logs/gui-event`
  - `data`: `accepted=true`
- `POST /api/v1/session/refresh`
  - `data`: `access_token`, `expires_in`, `token_type`

## 各APIの失敗時返り値
- 共通
  - `success`: `false`
  - `error.code`: string
  - `error.message`: string
  - `error.details`: object or null
  - `request_id`: string
  - `timestamp`: ISO8601
- 想定エラーコード
  - `INVALID_REQUEST` : 入力不正
  - `UNAUTHORIZED` : 認証失敗
  - `FORBIDDEN` : 権限不足
  - `NOT_FOUND` : 対象なし
  - `CONFLICT` : 状態競合
  - `RATE_LIMITED` : レート制限
  - `INTERNAL_ERROR` : サーバ内部失敗
  - `UPSTREAM_TIMEOUT` : 上流タイムアウト

## GUI側で使う主な項目
- リスト描画
  - `data.items[].media_id`
  - `data.items[].title`
  - `data.items[].status`
  - `data.items[].thumbnail_url`
- 詳細描画
  - `data.duration_sec`
  - `data.status`
- 操作結果通知
  - `data.status`
  - `error.code`
  - `error.message`
- 追跡用
  - `request_id`

## 認証付き操作の入力項目
- ヘッダ
  - `Authorization: Bearer <access_token>`
  - `X-Request-Id: <uuid>`
  - `X-Client-Version: <gui_version>`
- 本文またはクエリ
  - `requested_by` : 操作主体
  - `csrf_token` : 必要時のみ
  - `refresh_token` : セッション更新時
- 対象API
  - `POST /api/v1/media/{media_id}/play`
  - `POST /api/v1/media/{media_id}/stop`
  - `PATCH /api/v1/settings`
  - `POST /api/v1/session/refresh`

## 実装着手順

### Step1: 一覧取得系
- 着手条件
  - block 一覧系 API のエンドポイントを `GET /blocks` に寄せる
  - 一覧レスポンスの最小項目を確定する
- Step1 で使う想定 API / path
  - `API_BASE_URL`: `/api`
  - `buildApiUrl("/blocks")` → `/api/blocks`
  - `getJson("/blocks")`
  - 必要に応じて `getJson("/audit-logs")` を一覧系 read only 取得へ流用
- 確認項目
  - 一覧用レスポンスに `id` `name` `type` `status` `connectionStatus` `freezeStatus` `updatedAt` を含める
  - dashboard 集計と connection management の再利用可否を確認する
  - 失敗時レスポンスで `success` `error.message` `request_id` を返せる
- まだやらないこと
  - 危険操作 API の接続
  - 認証ヘッダ必須化

### Step2: 詳細取得系
- 着手条件
  - `GET /blocks/:blockId` の詳細項目を確定する
  - 詳細 API と warning 用データの責務分担を決める
- 確認項目
  - 詳細レスポンスに `handshakeStatus` `deleteRequested` を含める
  - not found 時の失敗契約を確定する
  - GUI が追加加工なしで主要項目を描画できる
- まだやらないこと
  - freeze / unfreeze 実行契約の最終化
  - export / delete 認証契約の最終化

### Step3: 接続/切断系
- 着手条件
  - `POST /blocks/:blockId/connect` と `POST /blocks/:blockId/disconnect` の成功/失敗契約を確定する
  - handshake 状態遷移 API の扱いを決める
- Step3 で使う想定 API / path
  - `POST /blocks/{id}/connect`
  - `POST /blocks/{id}/disconnect`
- 確認項目
  - 成功時に GUI が状態更新へ使える `status` を返せる
  - 競合時に `CONFLICT` を返せる
  - pending / success / failed の表示更新に必要な値が取れる
- まだやらないこと
  - audit 保存方式の最終化
  - 認証付き危険操作の接続

### Step4: audit / settings 系
- 着手条件
  - `GET /audit-logs` 系と `GET/PUT /settings/security` のレスポンス形式を確定する
  - filter / count / recent の扱いを決める
- Step4 で使う想定 API / path
  - `GET /audit-logs`
  - `GET /settings/security`
  - `PUT /settings/security`
- 確認項目
  - audit 一覧に `timestamp` `operator` `target` `action` `result` を返せる
  - count 系の返り値キーを確定する
  - settings 更新で GUI がそのまま反映できる形を返せる
- まだやらないこと
  - `appendAuditLog` の本番責務確定
  - settings 更新時の副次ログ最適化

### Step5: freeze / unfreeze 系
- 着手条件
  - `POST /blocks/:blockId/freeze` と `POST /blocks/:blockId/unfreeze` の入力/出力契約を確定する
  - warning 表示に必要な事前条件を確定する
- Step5 で使う想定 API / path
  - `POST /blocks/{id}/freeze`
  - `POST /blocks/{id}/unfreeze`
- 確認項目
  - GUI が fail-safe のまま実行可否を判定できる
  - 成功/失敗の message を返せる
  - 実行後に一覧・詳細再取得で整合が取れる
- まだやらないこと
  - export / delete の認証項目送信
  - 自動再試行

### Step6: export / delete 系
- 着手条件
  - `POST /blocks/:blockId/export` と `DELETE /blocks/:blockId` の認証契約を確定する
  - lockguard 入力項目と API 入力項目の対応を確定する
- 確認項目
  - 認証失敗時に `UNAUTHORIZED` または `FORBIDDEN` を返せる
  - 確認文言不一致時の失敗契約を決める
  - 成功時に GUI が再描画へ使える最小情報を返せる
- まだやらないこと
  - 認証 UI の拡張仕様
  - バックグラウンド再実行制御