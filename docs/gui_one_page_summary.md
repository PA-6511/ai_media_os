# AI_MEDIA_OS_GUI 1枚要約版

- 作成日: 2026-03-25
- 対象: AI_MEDIA_OS_GUI

---

## 現在の完成状態

- docs / UI / services の総点検を完了
- 運用・監視・引き継ぎの参照導線を整理済み
- 本運用 / 条件付き運用 / 保留の分類を確定済み

## この1枚の読む順番（最終）

1. 現在の状態
2. 機能の状態
3. 見るべき docs
4. 注意点
5. 次回見直し

---

## 現在の運用段階

- 安定運用定着フェーズを経て、継続運用中
- 定期レビュー前提で運用継続

## 現在の状態（要約）

- 総点検完了・分類確定済み
- 継続運用中（定期レビュー前提）

---

## 機能の状態（本運用）

- 一覧表示
- 詳細表示
- Dashboard
- Audit Log 参照
- Settings 参照
- Connect
- Disconnect

---

## 機能の状態（条件付き運用）

- Settings 保存
- Freeze
- Unfreeze
- Export
- Delete

---

## 機能別状態（圧縮版）

- 一覧表示: 本運用 / 3画面の表示整合
- 詳細表示: 本運用 / 一覧連動を維持
- Dashboard: 本運用 / 集計反映が安定
- Audit Log 参照: 本運用 / 記録参照が安定
- Settings 参照: 本運用 / 保存値表示が安定
- Settings 保存: 条件付き運用 / 保存後一致を監視
- Connect: 本運用 / 接続状態の反映安定
- Disconnect: 本運用 / 切断状態の反映安定
- Freeze: 条件付き運用 / confirmed と状態変更を監視
- Unfreeze: 条件付き運用 / confirmed と状態復帰を監視
- Export: 条件付き運用 / LockGuard 認証整合を監視
- Delete: 条件付き運用 / 削除後の画面整合を監視

---

## 機能の状態（保留）

- なし（2026-03-25 時点）

---

## 見るべき docs（最初）

- `docs/gui_handoff_index.md`
- `docs/gui_handoff_feature_status.md`
- `docs/gui_handoff_monitoring_map.md`
- `docs/gui_final_completion_report.md`

---

## 見るべき docs（障害時）

- `docs/gui_incident_response_template.md`
- `docs/gui_go_live_decision.md`
- `docs/gui_error_flow_check.md`
- `docs/gui_known_gaps.md`

---

## 運用・監視・障害対応の参照先（圧縮版）

- 日次確認で見る docs
	- `docs/gui_daily_ops_template.md`
	- `docs/gui_handoff_feature_status.md`
- 定期レビューで見る docs
	- `docs/gui_periodic_review_template.md`
	- `docs/gui_go_live_decision.md`
- 異常発生時に見る docs
	- `docs/gui_incident_response_template.md`
	- `docs/gui_go_live_decision.md`
- 保留/再開判断で見る docs
	- `docs/gui_hold_resume_template.md`
	- `docs/gui_error_flow_check.md`
- 引き継ぎ時に見る docs
	- `docs/gui_handoff_index.md`
	- `docs/gui_handoff_summary.md`

- 詳細確認は `docs/gui_handoff_monitoring_map.md` を参照

---

## 注意点（圧縮版）

- 条件付き運用/保留: 保留なし、条件付きは Settings 保存 / Freeze / Unfreeze / Export / Delete
- 運用上の注意点: 条件付き機能で異常が出たら機能単位で即時保留へ戻す
- docs と実装の注意点: 区分語（本運用/条件付き運用/保留）と状態名（connectionStatus/freezeStatus）を固定
- 次回見直しで見る点: 条件付き5機能の継続可否、Audit Log 欠落、一覧/詳細/Dashboard 整合

---

## 次回見直し

- 次回見直し日: （記入）
- 担当者: （記入）
- 見直し時参照: `docs/gui_periodic_review_template.md` / `docs/gui_go_live_decision.md`

---

## 詳細を見に行く docs 一覧

- 参照起点（索引）: `docs/gui_handoff_index.md`
- 完成報告（正本）: `docs/gui_final_completion_report.md`
- 機能状態の詳細: `docs/gui_handoff_feature_status.md`
- 監視観点の詳細: `docs/gui_handoff_monitoring_map.md`
- 既知ギャップの詳細: `docs/gui_known_gaps.md`
- 障害対応の詳細: `docs/gui_incident_response_template.md`
- 判定・見直しの詳細: `docs/gui_go_live_decision.md`

---

## 引き継ぎ時の最短読む順番

1. `docs/gui_one_page_summary.md`
2. `docs/gui_handoff_index.md`
3. `docs/gui_handoff_feature_status.md`
4. `docs/gui_handoff_monitoring_map.md`
5. `docs/gui_known_gaps.md`

---

## 最終メモ

- この1枚は全体判断用。詳細判断は各詳細docsで行う
- 参照導線は「1枚要約版 → 引き継ぎ索引 → 完成報告（正本）」で固定する
- 条件付き運用5機能は継続監視前提で扱う
- 異常時は機能単位で即時保留へ戻し、理由を docs に追記する
