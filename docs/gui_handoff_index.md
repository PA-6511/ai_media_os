# 引き継ぎ索引

- 作成日: 2026-03-25
- 目的: 引き継ぎ時に必要な docs を最短で参照できるようにする

---

## 概要を見る docs

- docs/gui_handoff_summary.md
- docs/gui_stable_operations_settled.md

---

## 1枚要約版参照欄

- docs/gui_one_page_summary.md
- 用途: 引き継ぎ開始時の全体把握（保留事項・注意点・次回見直しを先に確認）
- 次の参照先: docs/gui_handoff_index.md（本索引）→ docs/gui_final_completion_report.md（完成報告正本）

---

## 最初に読む推奨 docs 欄

1. docs/gui_one_page_summary.md
2. docs/gui_handoff_index.md
3. docs/gui_handoff_summary.md
4. docs/gui_handoff_feature_status.md
5. docs/gui_final_completion_report.md

---

## 機能別状態を見る docs

- docs/gui_handoff_feature_status.md
- docs/gui_final_operations_decision.md
- docs/gui_stable_operations_decision.md

---

## 監視/障害対応を見る docs

- docs/gui_handoff_monitoring_map.md
- docs/gui_go_live_decision.md
- docs/gui_error_flow_check.md
- docs/gui_incident_response_template.md

---

## 保留/再開を見る docs

- docs/gui_handoff_hold_resume.md
- docs/gui_known_gaps.md
- docs/gui_hold_resume_template.md

---

## テンプレ類を見る docs

- docs/gui_operations_templates_index.md
- docs/gui_daily_ops_template.md
- docs/gui_periodic_review_template.md
- docs/gui_incident_response_template.md
- docs/gui_hold_resume_template.md

---

## まず最初に読む順番

1. docs/gui_handoff_summary.md
2. docs/gui_handoff_feature_status.md
3. docs/gui_handoff_monitoring_map.md
4. docs/gui_handoff_hold_resume.md
5. docs/gui_operations_templates_index.md

---

## 更新時の注意点

- 各カテゴリに追加した docs は本索引にも必ず追記する
- 参照先のファイル名変更時は本索引を同時更新する
- テンプレートの追加・削除時は「テンプレ類を見る docs」を更新する
- まず最初に読む順番は運用段階の変更に合わせて見直す

---

## 総点検済みチェック欄

- [x] docs と実装の対応関係を総点検した（2026-03-25）
- [x] UI / services の命名・導線整合を総点検した（2026-03-25）
- [x] 監視・運用・引き継ぎ docs の参照整合を総点検した（2026-03-25）
- [x] 保留/条件付き/本運用の分類ズレを総点検した（2026-03-25）
- [x] 総点検結果を docs に記録した（2026-03-25）
- [x] 総点検レポートの参照先と引き継ぎ起点を更新した（2026-03-25）

---

## 総点検レポート参照欄

- 総点検レポート: `docs/gui_final_audit_report.md`
- 点検日: 2026-03-25
- 点検対象: UI 命名・導線 / 監視・運用・引き継ぎ docs / 本運用・条件付き運用・保留の分類
- 修正済み: `ui/script.js` / `ui/services/blockService.js` / 主要引き継ぎ docs
- 要注意項目: `docs/gui_final_audit_report.md` の「要注意として残した項目」を参照
- 次に見るべき docs: `docs/gui_handoff_feature_status.md` / `docs/gui_handoff_monitoring_map.md`

---

## 最終参照一覧（完成報告フェーズ）

- 本一覧を運用・監視・引き継ぎ参照先の正本とする（テンプレ運用側の簡易一覧より優先）
- 並び順は「日次運用 → 定期レビュー → 異常対応 → 保留/再開判断 → 引き継ぎ → 完成報告」で固定する

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

---

## 最終完成報告確認済みチェック欄

- 確認日: （記入）
- 確認者: （記入）
- [x] 最終完成報告（`docs/gui_final_completion_report.md`）を作成・確認した
- [x] 完成報告の要約・運用範囲・保留事項を確認した
- [x] 運用開始後に見る docs を確認した
- [x] 引き継ぎ時に渡す docs を確認した

---

## 完成報告参照先欄

- 完成報告本体: `docs/gui_final_completion_report.md`
- 総点検レポート: `docs/gui_final_audit_report.md`
- 機能別運用状態: `docs/gui_handoff_feature_status.md`
- 引き継ぎ概要: `docs/gui_handoff_summary.md`
- 最終参照起点: `docs/gui_final_completion_report.md` を完成報告の正本として扱う
