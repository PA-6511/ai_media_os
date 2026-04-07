# 運用テンプレ索引

- 作成日: 2026-03-25
- 対象: AI_MEDIA_OS_GUI 安定運用フェーズ以降

---

## テンプレ一覧

| テンプレ名 | ファイル | 使うタイミング | 命名規則 |
|---|---|---|---|
| 日次運用確認 | `docs/gui_daily_ops_template.md` | 毎日の確認時 | `gui_daily_ops_YYYYMMDD.md` |
| 定期レビュー | `docs/gui_periodic_review_template.md` | 月次・定期レビュー時 | `gui_periodic_review_YYYYMMDD.md` |
| 異常発生時記録 | `docs/gui_incident_response_template.md` | 異常・障害が発生したとき | `gui_incident_YYYYMMDD.md` |
| 機能保留/再開判断 | `docs/gui_hold_resume_template.md` | 機能を保留または再開するとき | `gui_hold_resume_YYYYMMDD.md` |

---

## 各テンプレの使い方

### 日次運用確認テンプレ

- 使うタイミング: 毎日の運用確認時
- 主な記入内容: 一覧/詳細/Dashboard/Audit Log/Settings/各機能の確認結果・異常有無まとめ・対応メモ
- 異常があれば: 「異常発生時記録テンプレ」に切り替えて記録する

### 定期レビューテンプレ

- 使うタイミング: 月次などの定期レビュー時
- 主な記入内容: 毎回レビュー対象の結果・条件付き運用の結果・見直し候補の結果・巻き戻し判断・次回監視強化項目
- 判断基準参照先: `docs/gui_go_live_decision.md`（定期レビュー運用フェーズ 停止・巻き戻し判断条件）

### 異常発生時記録テンプレ

- 使うタイミング: 日次確認または運用中に異常を発見したとき
- 主な記入内容: 発生機能・症状・影響範囲・一時対応・停止/保留/継続監視の判断・再開条件
- 判断基準参照先: `docs/gui_go_live_decision.md`・`docs/gui_error_flow_check.md`

### 機能保留/再開判断テンプレ

- 使うタイミング: 機能を保留にするとき・保留中機能の再開を判断するとき
- 主な記入内容: 保留理由・代替運用・再開条件・再開前確認項目・再開判断
- 再開条件参照先: `docs/gui_error_flow_check.md`（見直し候補機能の再評価条件）

---

## 更新時の注意点

- テンプレートファイル本体（`_template.md`）は変更しない — コピーして使う
- 命名規則（`YYYYMMDD` 形式）を守る
- 保存先は `docs/` 配下に統一する
- テンプレートの項目を増やす場合はこの索引も合わせて更新する

---

## 引き継ぎ監視参照マップ欄

- 監視・障害対応の参照先まとめ: `docs/gui_handoff_monitoring_map.md`
- 参照起点（重複回避）: `docs/gui_handoff_index.md` の「監視/障害対応を見る docs」から `docs/gui_handoff_monitoring_map.md` へ遷移し、事象別の参照先を確定する
- 迷った場合: `docs/gui_handoff_monitoring_map.md` の「参照優先ルール（重複回避）」を確認する

## 最初に見る順番

- 引き継ぎ開始時の起点: `docs/gui_handoff_index.md`
- 監視・障害対応の整理: `docs/gui_handoff_monitoring_map.md`
- 日次運用に入る場合: `docs/gui_daily_ops_template.md`
- 定期レビューに入る場合: `docs/gui_periodic_review_template.md`
- 異常対応に入る場合: `docs/gui_incident_response_template.md`
- 保留/再開判断に入る場合: `docs/gui_hold_resume_template.md`

---

## 最終参照一覧（完成報告フェーズ）

- 重複回避のため、詳細一覧は `docs/gui_handoff_index.md` の「最終参照一覧（完成報告フェーズ）」を正本として参照する

- 日次運用で見る docs
	- `docs/gui_daily_ops_template.md`
	- `docs/gui_stable_operations_settled.md`
	- `docs/gui_handoff_feature_status.md`
- 定期レビューで見る docs
	- `docs/gui_periodic_review_template.md`
	- `docs/gui_go_live_decision.md`
	- `docs/gui_error_flow_check.md`
- 異常対応で見る docs
	- `docs/gui_incident_response_template.md`
	- `docs/gui_go_live_decision.md`
	- `docs/gui_error_flow_check.md`
- 保留/再開判断で見る docs
	- `docs/gui_hold_resume_template.md`
	- `docs/gui_known_gaps.md`
	- `docs/gui_error_flow_check.md`
- 引き継ぎで最初に見る docs
	- `docs/gui_handoff_summary.md`
	- `docs/gui_handoff_index.md`
	- `docs/gui_handoff_feature_status.md`
- 完成報告として最初に見る docs
	- `docs/gui_final_completion_report.md`
	- `docs/gui_final_audit_report.md`
	- `docs/gui_final_operations_decision.md`
