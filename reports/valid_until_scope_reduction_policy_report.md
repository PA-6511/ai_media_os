# VALID_UNTIL_SCOPE_REDUCTION_POLICY

## 目的
valid_until 運用を見直し、DESIGN_ONLY / DRY_RUN_ONLY / reports-only / no-execution 系の判定で、時間失効による再判定ループを起こさないようにする。

## 問題点
- valid_until が DESIGN_ONLY / DRY_RUN_ONLY でも失効し、再判定トークンを消費していた。

## 新方針
- 非実行判定は時間失効しない。
- 入力・ポリシー・承認ラベル・credential 状態・実行権限の変化でのみ失効する。
- 標準 freshness_policy は `STATIC_UNTIL_INPUT_CHANGE` とする。
- `valid_until_required` は非実行判定では `false`、実行権限ゲートでは `true` とする。

## valid_until を残す対象
- credential.env 作成
- 外部API実行
- WordPress 書き込み
- 本番公開
- systemd timer start/enable
- rollback
- 緊急復旧・隔離解除

## valid_until を原則使わない対象
- DESIGN_ONLY
- DRY_RUN_ONLY
- reports-only
- no-execution
- evidence-only
- handoff-only

## 安全境界
- no production write
- no WordPress API call
- no external API call
- no credential read/output
- no systemd operation

## 結果
- status: PASS_DESIGN_ONLY_NO_EXECUTION
- production_status: NO_GO

## 補足
- evidence index updated safely