# AI_MEDIA_OS_GUI 状態遷移確定版

> 作成日: 2026-03-15  
> 参照元: 危険操作モーダル仕様（確定版）

---

## 0. 適用範囲

本書は以下の状態機械を対象とする。

- BlockAI 接続状態
- BlockAI 有効/無効状態
- Freeze/Unfreeze 状態
- Export 処理状態
- Delete 処理状態
- 認証状態（未認証 / パスワード確認済 / 2FA確認済）
- ハンドシェイク状態

前提ルール:
- Connect / Disconnect は相互確認ハンドシェイク必須
- Export / Delete はパスワード再入力 + 2FA必須
- fail-safe優先（不明状態は実行しない）
- 監査ログ記録完了まで成功状態に遷移しない

---

## 1. 状態一覧

### 1.1 ドメイン別状態（業務状態）

| ドメイン | 状態ID | 状態名（日本語） | enum案 |
|---|---|---|---|
| 接続 | C0 | 切断 | `ConnectionState.DISCONNECTED` |
| 接続 | C1 | 接続中 | `ConnectionState.CONNECTED` |
| 接続 | C2 | 接続遷移中 | `ConnectionState.TRANSITIONING` |
| 接続 | C3 | 不明（fail-safe） | `ConnectionState.UNKNOWN` |
| 有効/無効 | E0 | 有効 | `EnableState.ENABLED` |
| 有効/無効 | E1 | 無効 | `EnableState.DISABLED` |
| 有効/無効 | E2 | 切替中 | `EnableState.TRANSITIONING` |
| 有効/無効 | E3 | 不明（fail-safe） | `EnableState.UNKNOWN` |
| 凍結 | F0 | 通常稼働 | `FreezeState.UNFROZEN` |
| 凍結 | F1 | 凍結中 | `FreezeState.FROZEN` |
| 凍結 | F2 | 凍結遷移中 | `FreezeState.TRANSITIONING` |
| 凍結 | F3 | 不明（fail-safe） | `FreezeState.UNKNOWN` |

### 1.2 操作プロセス状態（UI/処理状態）

| 対象 | 状態ID | 状態名（日本語） | enum案 |
|---|---|---|---|
| 共通処理 | P0 | 待機 | `FlowState.IDLE` |
| 共通処理 | P1 | 通常確認中 | `FlowState.CONFIRMING` |
| 共通処理 | P2 | 警告確認中 | `FlowState.WARNING` |
| 共通処理 | P3 | パスワード認証中 | `FlowState.AUTH_PASSWORD` |
| 共通処理 | P4 | 2FA認証中 | `FlowState.AUTH_2FA` |
| 共通処理 | P5 | ハンドシェイク確認中 | `FlowState.HANDSHAKE` |
| 共通処理 | P6 | 最終確認中（対象名再入力） | `FlowState.FINAL_CONFIRM` |
| 共通処理 | P7 | 実行中（API） | `FlowState.EXECUTING` |
| 共通処理 | P8 | 監査ログ記録中 | `FlowState.AUDIT_LOGGING` |
| 共通処理 | P9 | 成功 | `FlowState.SUCCESS` |
| 共通処理 | P10 | 失敗 | `FlowState.FAILED` |
| 共通処理 | PX | 中断 | `FlowState.ABORTED` |

### 1.3 認証状態

| 状態ID | 状態名 | enum案 | 説明 |
|---|---|---|---|
| A0 | 未認証 | `AuthState.UNVERIFIED` | 再認証未実施 |
| A1 | パスワード確認済 | `AuthState.PASSWORD_VERIFIED` | パスワードのみ完了 |
| A2 | 2FA確認済 | `AuthState.TWO_FA_VERIFIED` | パスワード + 2FA完了 |
| A3 | 認証失敗 | `AuthState.FAILED` | fail-safe中断対象 |

### 1.4 ハンドシェイク状態

| 状態ID | 状態名 | enum案 | 説明 |
|---|---|---|---|
| H0 | 未開始 | `HandshakeState.NOT_STARTED` | まだ確認していない |
| H1 | 送信側確認済 | `HandshakeState.SENDER_CONFIRMED` | 送信側チェックON |
| H2 | 受信側確認済 | `HandshakeState.RECEIVER_CONFIRMED` | 受信側チェックON |
| H3 | 相互確認完了 | `HandshakeState.MUTUAL_CONFIRMED` | 実行可能 |
| H4 | タイムアウト | `HandshakeState.TIMEOUT` | fail-safe中断 |
| H5 | 不一致 | `HandshakeState.MISMATCH` | fail-safe中断 |

---

## 2. イベント一覧

| イベントID | イベント名 | 用途 |
|---|---|---|
| EV_OPEN_MODAL | モーダル開始 | P0 -> P1 |
| EV_CONFIRM_OK | 通常確認OK | 次ステップへ |
| EV_WARNING_OK | 警告確認OK | 次ステップへ |
| EV_PASSWORD_SUBMIT_OK | パスワード認証成功 | A0 -> A1 |
| EV_PASSWORD_SUBMIT_NG | パスワード認証失敗 | A0 -> A3 |
| EV_2FA_SUBMIT_OK | 2FA成功 | A1 -> A2 |
| EV_2FA_SUBMIT_NG | 2FA失敗 | A1 -> A3 |
| EV_HANDSHAKE_SENDER_ON | 送信側確認ON | H0/H2 -> H1/H3 |
| EV_HANDSHAKE_RECEIVER_ON | 受信側確認ON | H0/H1 -> H2/H3 |
| EV_HANDSHAKE_TIMEOUT | ハンドシェイク超過 | H* -> H4 |
| EV_HANDSHAKE_MISMATCH | 相互確認不一致 | H* -> H5 |
| EV_FINAL_TEXT_MATCH | 最終確認一致 | Deleteのみ実行可能 |
| EV_FINAL_TEXT_MISMATCH | 最終確認不一致 | fail-safe中断 |
| EV_PREFLIGHT_OK | 事前検証成功 | P* -> P7 |
| EV_PREFLIGHT_NG | 事前検証失敗 | P* -> P10 |
| EV_API_OK | API実行成功 | P7 -> P8 |
| EV_API_NG | API実行失敗 | P7 -> P10 |
| EV_AUDIT_OK | 監査ログ記録成功 | P8 -> P9 |
| EV_AUDIT_NG | 監査ログ記録失敗 | P8 -> P10 |
| EV_CANCEL | ユーザー中断 | 任意 -> PX |
| EV_SESSION_EXPIRED | セッション失効 | 任意 -> PX |
| EV_ROLE_FORBIDDEN | 権限不足 | 任意 -> P10 |

---

## 3. 状態遷移表（操作別）

### 3.1 Connect

| 現在状態 | イベント | 条件 | 次状態 | 備考 |
|---|---|---|---|---|
| P0 | EV_OPEN_MODAL | 対象選択済 | P1 |  |
| P1 | EV_CONFIRM_OK | 有効状態=E0、接続状態=C0 | P5 |  |
| P5 | EV_HANDSHAKE_SENDER_ON / EV_HANDSHAKE_RECEIVER_ON | 両チェック完了でH3 | P7 | H3になるまで待機 |
| P5 | EV_HANDSHAKE_TIMEOUT/MISMATCH | - | P10 | fail-safe |
| P7 | EV_API_OK | - | P8 |  |
| P7 | EV_API_NG | - | P10 |  |
| P8 | EV_AUDIT_OK | - | P9 | 成功確定 |
| P8 | EV_AUDIT_NG | - | P10 | 成功扱い禁止 |

### 3.2 Disconnect

| 現在状態 | イベント | 条件 | 次状態 | 備考 |
|---|---|---|---|---|
| P0 | EV_OPEN_MODAL | 対象選択済 | P1 |  |
| P1 | EV_CONFIRM_OK | 接続状態=C1 | P5 |  |
| P5 | EV_HANDSHAKE_SENDER_ON / EV_HANDSHAKE_RECEIVER_ON | H3 | P7 |  |
| P5 | EV_HANDSHAKE_TIMEOUT/MISMATCH | - | P10 | fail-safe |
| P7 | EV_API_OK | - | P8 |  |
| P7 | EV_API_NG | - | P10 |  |
| P8 | EV_AUDIT_OK | - | P9 | 成功確定 |
| P8 | EV_AUDIT_NG | - | P10 | 成功扱い禁止 |

### 3.3 Freeze

| 現在状態 | イベント | 条件 | 次状態 | 備考 |
|---|---|---|---|---|
| P0 | EV_OPEN_MODAL | 対象選択済 | P1 |  |
| P1 | EV_CONFIRM_OK | 凍結状態=F0 | P2 |  |
| P2 | EV_WARNING_OK | 凍結理由入力済 + 影響確認チェックON | P7 |  |
| P7 | EV_API_OK | - | P8 |  |
| P7 | EV_API_NG | - | P10 |  |
| P8 | EV_AUDIT_OK | - | P9 | 成功確定 |
| P8 | EV_AUDIT_NG | - | P10 | 成功扱い禁止 |

### 3.4 Unfreeze

| 現在状態 | イベント | 条件 | 次状態 | 備考 |
|---|---|---|---|---|
| P0 | EV_OPEN_MODAL | 対象選択済 | P1 |  |
| P1 | EV_CONFIRM_OK | 凍結状態=F1 | P2 |  |
| P2 | EV_WARNING_OK | 復帰確認チェックON | P7 |  |
| P7 | EV_API_OK | - | P8 |  |
| P7 | EV_API_NG | - | P10 |  |
| P8 | EV_AUDIT_OK | - | P9 | 成功確定 |
| P8 | EV_AUDIT_NG | - | P10 | 成功扱い禁止 |

### 3.5 Export

| 現在状態 | イベント | 条件 | 次状態 | 備考 |
|---|---|---|---|---|
| P0 | EV_OPEN_MODAL | 対象/範囲選択済 | P1 |  |
| P1 | EV_CONFIRM_OK | - | P2 |  |
| P2 | EV_WARNING_OK | 機密取扱チェックON | P3 |  |
| P3 | EV_PASSWORD_SUBMIT_OK | - | P4 | A0 -> A1 |
| P3 | EV_PASSWORD_SUBMIT_NG | - | P10 | A3 |
| P4 | EV_2FA_SUBMIT_OK | - | P7 | A1 -> A2 |
| P4 | EV_2FA_SUBMIT_NG | - | P10 | A3 |
| P7 | EV_PREFLIGHT_OK | 監査ログ予約可 | P7 | 実行継続 |
| P7 | EV_PREFLIGHT_NG | - | P10 | fail-safe |
| P7 | EV_API_OK | - | P8 |  |
| P7 | EV_API_NG | - | P10 |  |
| P8 | EV_AUDIT_OK | - | P9 | 成功確定 |
| P8 | EV_AUDIT_NG | - | P10 | 成功扱い禁止 |

### 3.6 Delete

| 現在状態 | イベント | 条件 | 次状態 | 備考 |
|---|---|---|---|---|
| P0 | EV_OPEN_MODAL | 対象選択済 | P1 |  |
| P1 | EV_CONFIRM_OK | - | P2 |  |
| P2 | EV_WARNING_OK | 取消不可チェックON + 削除理由入力済 | P3 |  |
| P3 | EV_PASSWORD_SUBMIT_OK | - | P4 | A0 -> A1 |
| P3 | EV_PASSWORD_SUBMIT_NG | - | P10 | A3 |
| P4 | EV_2FA_SUBMIT_OK | - | P6 | A1 -> A2 |
| P4 | EV_2FA_SUBMIT_NG | - | P10 | A3 |
| P6 | EV_FINAL_TEXT_MATCH | 対象名完全一致 | P7 |  |
| P6 | EV_FINAL_TEXT_MISMATCH | - | P10 | fail-safe |
| P7 | EV_PREFLIGHT_OK | 参照整合性OK + 監査ログ予約可 | P7 | 実行継続 |
| P7 | EV_PREFLIGHT_NG | - | P10 | 強制削除なし |
| P7 | EV_API_OK | - | P8 |  |
| P7 | EV_API_NG | - | P10 |  |
| P8 | EV_AUDIT_OK | - | P9 | 成功確定 |
| P8 | EV_AUDIT_NG | - | P10 | 成功扱い禁止 |

---

## 4. 禁止遷移

| 禁止ID | 禁止遷移 | 理由 |
|---|---|---|
| X01 | P1 -> P7（確認後に即実行） | 警告/認証/ハンドシェイクをバイパスするため禁止 |
| X02 | P3未通過でP4へ遷移 | パスワード未確認の2FAは無効 |
| X03 | A2未満でExport/DeleteのP7へ遷移 | 再認証要件違反 |
| X04 | H3未満でConnect/DisconnectのP7へ遷移 | 相互確認要件違反 |
| X05 | P7 -> P9（監査ログ未記録成功） | 監査ログ完了前は成功不可 |
| X06 | F1状態でFreeze開始 | 二重凍結防止 |
| X07 | F0状態でUnfreeze開始 | 未凍結解除防止 |
| X08 | C1状態でConnect開始 | 二重接続防止 |
| X09 | C0状態でDisconnect開始 | 二重切断防止 |
| X10 | UNKNOWN状態（C3/E3/F3）で実行開始 | fail-safe方針により禁止 |

---

## 5. エラー時の遷移

### 5.1 エラー分類と遷移方針

| エラー種別 | 発生フェーズ | 遷移先 | 戻り先UI | 方針 |
|---|---|---|---|---|
| 入力不備 | P1/P2/P6 | 現在状態維持 + エラー表示 | 同一モーダル | 修正可能エラー |
| 認証失敗 | P3/P4 | P10 | S4（Export/Delete） | 再実行は最初から |
| ハンドシェイク失敗 | P5 | P10 | S3（対象ハイライト） | 再実行は最初から |
| 権限不足 | 任意 | P10 | 現在画面 + 403案内 | 即中断 |
| セッション失効 | 任意 | PX | ログイン画面 | 即中断 |
| API失敗 | P7 | P10 | 操作元画面 | 原因表示 |
| 監査ログ失敗 | P8 | P10 | 操作元画面 | 成功扱い禁止 |
| 不明エラー | 任意 | P10 | 操作元画面 | fail-safe中断 |

### 5.2 元状態への戻し方

- 業務状態（C/E/F）は API 成功前に更新しない
- P10遷移時は業務状態を「直前の確定状態」に維持する
- PX遷移（キャンセル）は状態変更なしで終了する

---

## 6. ボタン活性条件

### 6.1 操作ボタン活性条件（主要）

| ボタン | 活性条件（すべて満たす） | 非活性条件 |
|---|---|---|
| Connect実行 | 対象選択済 + C0 + E0 + F0 + H3 | 対象未選択 / H3未満 / UNKNOWN |
| Disconnect実行 | 対象選択済 + C1 + H3 | C0 / H3未満 / UNKNOWN |
| Freeze実行 | 対象選択済 + F0 + 凍結理由入力済 + 影響確認ON | F1 / 理由未入力 / チェック未ON |
| Unfreeze実行 | 対象選択済 + F1 + 復帰確認ON | F0 / チェック未ON |
| Export実行 | 対象/範囲妥当 + A2 + 警告確認ON + preflight可 | A2未満 / 範囲不正 / UNKNOWN |
| Delete実行 | 対象妥当 + A2 + 取消不可確認ON + 対象名一致 + preflight可 | A2未満 / 名称不一致 / 整合性NG |

### 6.2 モーダル内ボタン活性条件

| フェーズ | 主ボタン | 活性条件 |
|---|---|---|
| P1 | 次へ | 必須チェックON |
| P2 | 次へ | 警告確認ON + 必須入力完了 |
| P3 | 認証して進む | パスワード形式妥当 |
| P4 | 認証して進む | 2FA 6桁妥当 |
| P5 | 実行へ進む | H3（相互確認完了） |
| P6 | 最終確定 | 対象名完全一致 |
| P7 | 再押下禁止 | `isPending=true` の間は常に非活性 |

---

## 7. enum / state machine 化しやすい命名案

### 7.1 TypeScript enum案

```ts
export enum ConnectionState {
  DISCONNECTED = "DISCONNECTED",
  CONNECTED = "CONNECTED",
  TRANSITIONING = "TRANSITIONING",
  UNKNOWN = "UNKNOWN",
}

export enum EnableState {
  ENABLED = "ENABLED",
  DISABLED = "DISABLED",
  TRANSITIONING = "TRANSITIONING",
  UNKNOWN = "UNKNOWN",
}

export enum FreezeState {
  UNFROZEN = "UNFROZEN",
  FROZEN = "FROZEN",
  TRANSITIONING = "TRANSITIONING",
  UNKNOWN = "UNKNOWN",
}

export enum AuthState {
  UNVERIFIED = "UNVERIFIED",
  PASSWORD_VERIFIED = "PASSWORD_VERIFIED",
  TWO_FA_VERIFIED = "TWO_FA_VERIFIED",
  FAILED = "FAILED",
}

export enum HandshakeState {
  NOT_STARTED = "NOT_STARTED",
  SENDER_CONFIRMED = "SENDER_CONFIRMED",
  RECEIVER_CONFIRMED = "RECEIVER_CONFIRMED",
  MUTUAL_CONFIRMED = "MUTUAL_CONFIRMED",
  TIMEOUT = "TIMEOUT",
  MISMATCH = "MISMATCH",
}

export enum FlowState {
  IDLE = "IDLE",
  CONFIRMING = "CONFIRMING",
  WARNING = "WARNING",
  AUTH_PASSWORD = "AUTH_PASSWORD",
  AUTH_2FA = "AUTH_2FA",
  HANDSHAKE = "HANDSHAKE",
  FINAL_CONFIRM = "FINAL_CONFIRM",
  EXECUTING = "EXECUTING",
  AUDIT_LOGGING = "AUDIT_LOGGING",
  SUCCESS = "SUCCESS",
  FAILED = "FAILED",
  ABORTED = "ABORTED",
}
```

### 7.2 イベント定数案

```ts
export enum FlowEvent {
  OPEN_MODAL = "OPEN_MODAL",
  CONFIRM_OK = "CONFIRM_OK",
  WARNING_OK = "WARNING_OK",
  PASSWORD_OK = "PASSWORD_OK",
  PASSWORD_NG = "PASSWORD_NG",
  TWO_FA_OK = "TWO_FA_OK",
  TWO_FA_NG = "TWO_FA_NG",
  HANDSHAKE_SENDER_ON = "HANDSHAKE_SENDER_ON",
  HANDSHAKE_RECEIVER_ON = "HANDSHAKE_RECEIVER_ON",
  HANDSHAKE_TIMEOUT = "HANDSHAKE_TIMEOUT",
  HANDSHAKE_MISMATCH = "HANDSHAKE_MISMATCH",
  FINAL_TEXT_MATCH = "FINAL_TEXT_MATCH",
  FINAL_TEXT_MISMATCH = "FINAL_TEXT_MISMATCH",
  PREFLIGHT_OK = "PREFLIGHT_OK",
  PREFLIGHT_NG = "PREFLIGHT_NG",
  API_OK = "API_OK",
  API_NG = "API_NG",
  AUDIT_OK = "AUDIT_OK",
  AUDIT_NG = "AUDIT_NG",
  CANCEL = "CANCEL",
  SESSION_EXPIRED = "SESSION_EXPIRED",
  ROLE_FORBIDDEN = "ROLE_FORBIDDEN",
}
```

---

## 8. State machine 安全設計の注意点

- 単一責務化: 認証状態（AuthState）と業務状態（Connection/Freeze等）を同一enumに混在させない
- 成功確定のゲート: `FlowState.SUCCESS` は `AUDIT_OK` のみで到達可能にする
- fail-safeデフォルト: 未知イベント受信時は `FAILED` へ遷移し処理停止
- 冪等性: Connect/Disconnect/Freeze/Unfreeze は現状態と同じ要求を拒否する
- 監査一貫性: `request_id` 単位で UI/API/監査ログを相関できるようにする
- 二重送信防止: `EXECUTING` と `AUDIT_LOGGING` では全実行系ボタンを非活性
- 再試行規則: `FAILED` からの再試行は必ず `IDLE` へ戻して最初から開始

---

## 9. 実装チェック観点（受け入れ確認用）

- Connect の開始前条件: `C0 && E0 && F0 && H3`
- Disconnect の禁止条件: `C0` または `H3未満`
- Delete 前の認証完了条件: `AuthState.TWO_FA_VERIFIED` かつ `FINAL_TEXT_MATCH`
- エラー時の戻り先: S3またはS4へ明示的に固定
- ボタン活性条件: 各フェーズで定義済み条件を満たさない限り非活性

この仕様を満たせば、ダミーUIでも安全に状態制御を反映できる。
