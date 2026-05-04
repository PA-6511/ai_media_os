# README_PHASE2

## 目的

Phase2 での変更は、安全ガードを前提に運用する。
本ドキュメントは「何を変更してよいか」「何を必ず記録するか」を固定する。

## 運用原則

- 変更は小さく、1コミット1目的を維持する
- 失敗時は握り潰さず、ログに残す
- Core のガードロジック変更はレビュー必須
- 本番影響がある処理は dry_run で先行検証する

## 必須成果物

- schemas/phase2_runtime_log.schema.json
- tools/validate_phase2_logs.py
- tools/phase2_kpi_report.py

## ランタイムログ必須項目

- timestamp (ISO8601 UTC)
- run_id
- phase
- component
- action
- decision: APPROVE / ESCALATE / DENY
- result: SUCCESS / FAIL / SKIP
- kpi.failsafe_coverage
- kpi.freeze_correctness
- kpi.policy_deny_delta
- kpi.warning_streak

## 自動FREEZE判定ルール

以下のいずれかを満たしたら FREEZE:

- failsafe_coverage < 1.00
- freeze_correctness < 0.90
- policy_deny_delta >= 2.0
- warning_streak >= 2

## 変更管理

- Phase2 中は verification 中核の仕様変更を行わない
- 新規 Block 接続は dummy_block 接続テスト通過後に実施する
- KPI しきい値変更はコミットメッセージで理由を明示する
