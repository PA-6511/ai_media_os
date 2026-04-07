# 監視・障害対応 参照先マップ

- 作成日: 2026-03-25
- 目的: 引き継ぎ時に、監視・障害対応で最初に参照すべき docs を即時判断できるようにする

---

## 日次確認で見る docs

- `docs/gui_daily_ops_template.md`
  - 日次確認の記録テンプレート
- `docs/gui_stable_operations_settled.md`
  - 日次確認対象欄・全体運用状態の確認
- `docs/gui_handoff_feature_status.md`
  - 機能別の現在状態（本運用/条件付き/保留）確認

---

## 定期レビューで見る docs

- `docs/gui_periodic_review_template.md`
  - 定期レビュー実行テンプレート
- `docs/gui_final_operations_start_log.md`
  - 条件付き運用機能の継続条件・定期レビュー指標
- `docs/gui_go_live_decision.md`
  - 停止・巻き戻し判断条件
- `docs/gui_error_flow_check.md`
  - 再評価条件・再開条件

---

## 異常発生時に見る docs

- `docs/gui_incident_response_template.md`
  - 異常発生時の初動記録テンプレート
- `docs/gui_go_live_decision.md`
  - 全面見直し / 機能単位で巻き戻し / 継続監視 の判定
- `docs/gui_error_flow_check.md`
  - 異常後の再評価条件・再開条件
- `docs/gui_hold_resume_template.md`
  - 機能保留/再開判断を記録

---

## 保留/再開判断で見る docs

- `docs/gui_hold_resume_template.md`
  - 保留理由・代替運用・再開前確認項目
- `docs/gui_known_gaps.md`
  - 保留中機能記録欄・再評価条件チェック欄
- `docs/gui_error_flow_check.md`
  - 機能別の再評価条件（再開可否判定）
- `docs/gui_go_live_decision.md`
  - 危険操作系の厳格判定基準

---

## 本運用/安定運用判断で見る docs

- `docs/gui_final_operations_decision.md`
  - 本運用・安定運用判定結果の履歴
- `docs/gui_stable_operations_decision.md`
  - 安定運用定着・定期レビューの判定履歴
- `docs/gui_stable_operations_settled.md`
  - 定着運用・条件付き運用・テンプレ参照先の最新状態
- `docs/gui_handoff_summary.md`
  - 引き継ぎ概要の短縮版サマリ

---

## まず最初に確認する順番

このマップは `docs/gui_handoff_index.md` の「監視/障害対応を見る docs」セクションから参照されることを前提としています。
引き継ぎ時は、まず索引から入り、その後にこのマップで事象別の一次参照先を確定してください。

- 1. 起点: `docs/gui_handoff_index.md`
- 2. 監視/障害対応の整理: `docs/gui_handoff_monitoring_map.md`
- 3. 事象別の一次参照先を開く:
  - 日次確認: `docs/gui_daily_ops_template.md`
  - 定期レビュー: `docs/gui_periodic_review_template.md`
  - 異常対応: `docs/gui_incident_response_template.md` → `docs/gui_go_live_decision.md`
  - 保留/再開判断: `docs/gui_hold_resume_template.md` → `docs/gui_error_flow_check.md`

---

## 参照優先ルール（重複回避）

- 要約版対応: 1枚要約で参照先を確認する場合は `docs/gui_one_page_summary.md` の「運用・監視・障害対応の参照先（圧縮版）」を起点にする
- 要約版運用: 1枚要約版は各用途 1〜2 docs の最小参照のみ掲載し、詳細確認は本マップで行う

- 日次確認の一次参照: `docs/gui_daily_ops_template.md`（必要時のみ `docs/gui_stable_operations_settled.md` を併用）
- 定期レビューの一次参照: `docs/gui_periodic_review_template.md`（継続条件の確認時のみ `docs/gui_final_operations_start_log.md`、判定時のみ `docs/gui_go_live_decision.md` / `docs/gui_error_flow_check.md` を併用）
- 異常対応の一次参照: `docs/gui_incident_response_template.md`（判定時のみ `docs/gui_go_live_decision.md`、保留判断が必要な場合のみ `docs/gui_hold_resume_template.md` を併用）
- 保留/再開の一次参照: `docs/gui_hold_resume_template.md`（条件確認時のみ `docs/gui_known_gaps.md` / `docs/gui_error_flow_check.md` を併用）
- 引き継ぎ時は `docs/gui_handoff_index.md` を起点にし、同用途の docs を同時に開きすぎない
