# ai_media_os 最終 Go / No-Go 判定テンプレート

## 0. 目的と前提
- 目的: 残項目を集約し、最終 Go / No-Go 判定の基準を1枚で固定する。
- 対象: 判定文書化のみ（実装本体は変更しない）。
- 方針: fail-safe 優先。未確認項目は未完了として明記する。
- 更新日: 2026-04-12

## 1. 完了済み項目
### 1-1. 既に反映済みドキュメント
- [x] reports/preflight_checklist.md 更新済み
- [x] reports/core_ai_runbook.md 更新済み
- [x] reports/secrets_registration_checklist.md 追加済み
- [x] 各ドキュメントは commit / push 済み

### 1-2. 主要な完了内容
- [x] Git / GitHub 連携完了（main と origin/main の同期状態を確認済み）
- [x] GitHub Actions の最新 python-check 成功を確認済み
- [x] `.gitignore` 強化済み（`.env` / `*.db` / `*.zip` / `data/logs/` / `data/archives/`）
- [x] DB / ZIP / logs の Git 非追跡化を確認済み
- [x] 判定は 3 段階（Go / Conditional Go / No-Go）で運用する方針を確定
- [x] 必須 Secrets 4件と Variables（`WP_DRY_RUN`）の確認内容を反映済み
- [x] 初回運用体制の主要ルール（連絡フロー / 一次判断 / 停止基準）を確定済み
- [x] バックアップ方針を確定（保持期間: Daily 7日 / Weekly 4週 / Monthly 3か月、頻度: 毎日1回）
- [x] 復元手順の文書化と、復元確認履歴セクション追加を完了
- [x] Secrets 必須4件（WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD / SLACK_WEBHOOK_URL）の登録確認を反映
- [x] rollback 条件、当日ログ確認項目、retry queue 確認方針を反映

## 2. 残項目
### 2-1. Go 判定に直結する残項目（必須）
- [ ] 権限最小化の実画面確認
  - GitHub Actions permissions 未明示部分の確認
  - WordPress 接続ユーザー権限（実ロール）確認
  - Slack webhook が用途専用であることの確認
- [ ] 本運用後の実復元確認の実施と証跡記録
  - 手順確認は実施済み（2026-04-12）
  - 実復元は未完了（期限: 2026-04-30）
- [ ] 機密情報の最終監査（コード / リポジトリへの直書き有無の最終確認）
  - preflight 上で未確認のまま
  - Go 判定前に監査結果の記録が必要

### 2-2. 運用上の残項目（初回運用日チェック）
- [ ] 当日 py_compile 実行結果の記録
- [ ] 当日 pytest -q 実行結果の記録
- [ ] retry queue / 主要ログ確認結果の記録
- [ ] rollback 手順と連絡フロー再確認の記録
- [ ] 当日最終確認（運用開始直前レビュー）の実施結果記録
- [ ] 連絡フロー以外の運用体制で微調整があれば文書へ反映

## 3. Go / Conditional Go / No-Go 判定ルール
### 3-1. Go
次の条件をすべて満たした場合に Go とする。
- 必須残項目がすべて完了している
- 初回運用日チェックの必須ログが記録されている
- 重大な未確認事項が残っていない

### 3-2. Conditional Go
次の条件に該当する場合に Conditional Go とする。
- 安全運用に必要な主要手順は整っている
- ただし、Go の必須条件の一部が未完了
- 未完了項目に期限・担当・証跡方針が設定済み

### 3-3. No-Go
次のいずれかに該当する場合に No-Go とする。
- fail-safe を満たせない重大未確認項目がある
- 重大リスクの回避策または停止基準が不明確
- 実施必須の確認作業に失敗し、是正見込みが立っていない

## 4. 現時点の暫定判定
- 暫定判定: Conditional Go
- 判定日: 2026-04-12
- 理由:
  - 運用・監視・切り戻し・バックアップ・Secrets 登録確認の文書化は完了
  - ただし、Go 必須の未確認事項（権限最小化の実画面確認、実復元記録、機密情報最終監査）が残っている
  - 初回運用日チェックの当日実行結果（py_compile / pytest / queue / logs / rollback再確認）が未記録

## 5. Go に上げるための最終条件
次の 1 から 5 をすべて満たした時点で Go に引き上げる。
1. 権限最小化の実画面確認が完了し、確認結果を文書化する
2. 本運用後の実復元確認を 1 回以上実施し、結果と証跡を runbook に記録する
3. 機密情報の最終監査を完了し、直書きなし（または是正完了）を記録する
4. 初回運用日チェック項目（py_compile / pytest / queue / logs / rollback再確認）を記録する
5. 判定者が当日最終確認を実施し、判定欄と判定メモを確定する

## 6. 判定メモ（現時点）
- 判定: [ ] Go  [x] Conditional Go  [ ] No-Go
- 判定日: 2026-04-12
- 判定者:
- 判定理由（要約）: 主要文書と運用ルールは整備済みだが、Go 必須の実環境確認と当日記録が未完了。
- 未完了項目:
  - 権限最小化の実画面確認
  - 本運用後の実復元確認と証跡記録
  - 機密情報最終監査
  - 初回運用日チェック結果記録
- 期限:
  - 実復元確認: 2026-04-30 まで
  - それ以外の必須確認: 初回運用日まで
- 担当:
- 証跡の保存先: reports/core_ai_runbook.md, reports/preflight_checklist.md
- 優先順位:
  1. 権限最小化の実画面確認
  2. 実復元確認と証跡記録
  3. 機密情報最終監査
  4. 当日チェック結果記録
- fail-safe 原則:
  - 重大未確認項目が 1 つでも残る場合は Go に上げない
  - 迷った場合は停止側（Conditional Go 維持または No-Go）を選択する
- 条件未達時の扱い（継続停止条件）: 未達項目がある間は運用拡大せず、限定運用または停止を維持する
- 次回判定予定日:

## 7. Conditional Go 維持理由（現時点固定文）
- 権限最小化の最終確認が管理画面ベースで未完了
- 本運用後の実復元確認と証跡記録が未完了
- 上記 2 点は Go 判定の必須条件であり、未充足のため Go へ引き上げない

## 8. 参照元
- reports/preflight_checklist.md
- reports/core_ai_runbook.md
- reports/secrets_registration_checklist.md
