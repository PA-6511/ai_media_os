# 機能別運用状態まとめ

- 作成日: 2026-03-25
- 対象: AI_MEDIA_OS_GUI 安定運用フェーズ以降

---

## 機能別運用状態一覧

- 要約版対応: 1枚要約の圧縮一覧は `docs/gui_one_page_summary.md` の「機能別状態（圧縮版）」を参照
- 補足: 日次の一次確認は要約版を先に見て、詳細判定が必要な場合のみ本書の各機能詳細を確認する

- 運用状態の定義
	- 本運用: 通常運用で継続可
	- 条件付き運用: 実行は可能だが、継続条件の監視を前提に運用可
	- 保留: 実行停止中。再評価完了まで本運用・条件付き運用の対象外

- 読み替え注意
	- この文書では「本運用」を、引き継ぎ系 docs で使う「定着運用」と同義で扱う
	- Freeze / Unfreeze / Export / Delete は、現時点では「条件付き運用」であり「保留」ではない

| 機能 | 現在状態 | 主な確認点 | 異常時参照先 |
|---|---|---|---|
| 一覧表示 | 本運用 | 同一対象の status が詳細・Dashboard と一致 | `gui_go_live_decision.md` |
| 詳細表示 | 本運用 | 一覧との status 整合・フィールド欠落なし | `gui_go_live_decision.md` |
| Dashboard | 本運用 | 操作後の件数・状態サマリが即時反映 | `gui_go_live_decision.md` |
| Audit Log 参照 | 本運用 | action/target/result 欠落なく読める | `gui_go_live_decision.md` |
| Settings 参照 | 本運用 | 保存済み値が正しく表示されている | `gui_go_live_decision.md` |
| Settings 保存 | **条件付き運用** | 保存後値一致・再表示でも一致 | `gui_go_live_decision.md` / `gui_error_flow_check.md` |
| Connect | 本運用 | 接続後 status が3画面で一致・残留なし | `gui_go_live_decision.md` |
| Disconnect | 本運用 | 切断後 status が3画面で一致・残留なし | `gui_go_live_decision.md` |
| Freeze | **条件付き運用** | confirmed 通過・status 変更・Audit Log 整合 | `gui_go_live_decision.md` / `gui_error_flow_check.md` |
| Unfreeze | **条件付き運用** | confirmed 通過・status 復帰・Audit Log 整合 | `gui_go_live_decision.md` / `gui_error_flow_check.md` |
| Export | **条件付き運用** | 認証完全・LockGuard 正常閉鎖・Audit Log 整合 | `gui_go_live_decision.md` / `gui_error_flow_check.md` |
| Delete | **条件付き運用** | Export 条件 + 削除後3画面整合・Audit Log 整合 | `gui_go_live_decision.md` / `gui_error_flow_check.md` |

---

## 機能別詳細

### 一覧表示

- 現在状態: 本運用
- 見るべき確認点: 同一対象の status が一覧・詳細・Dashboard の3画面で一致し続けること
- 異常時の参照先: `gui_go_live_decision.md`（一覧/詳細表示崩れの判定テーブル）

### 詳細表示

- 現在状態: 本運用
- 見るべき確認点: 一覧との status 整合・表示フィールドの欠落・崩れがないこと
- 異常時の参照先: `gui_go_live_decision.md`（一覧/詳細表示崩れの判定テーブル）

### Dashboard

- 現在状態: 本運用
- 見るべき確認点: 操作後の件数・状態サマリが即時反映されること・空白化・崩れがないこと
- 異常時の参照先: `gui_go_live_decision.md`（Dashboard 不整合の判定テーブル）

### Audit Log 参照

- 現在状態: 本運用
- 見るべき確認点: 条件付き運用機能の実行後に action/target/result が欠落なく追記されること
- 異常時の参照先: `gui_go_live_decision.md`（Audit Log 更新異常の判定テーブル）

### Settings 参照

- 現在状態: 本運用
- 見るべき確認点: 現在保存されている値が正しく表示されていること
- 異常時の参照先: `gui_go_live_decision.md`（Settings 保存不整合の判定テーブル）

### Settings 保存

- 現在状態: **条件付き運用**
- 継続条件: 保存後の値が即時反映し再表示でも一致し続けること
- 見るべき確認点: 保存前後の値比較・再表示後の一致確認・エラー表示有無
- 条件付き運用を外す条件: 3回連続で保存→再表示の一致確認が通り、報告ゼロが続いた場合
- 異常時の参照先: `gui_go_live_decision.md` / `gui_error_flow_check.md`（Settings 保存の再評価条件）

### Connect

- 現在状態: 本運用
- 見るべき確認点: 接続後の status が一覧・詳細・Dashboard の3画面で一致・残留データがないこと
- 異常時の参照先: `gui_go_live_decision.md`（Connect/Disconnect 不整合の判定テーブル）

### Disconnect

- 現在状態: 本運用
- 見るべき確認点: 切断後の status が3画面で一致・残留データがないこと
- 異常時の参照先: `gui_go_live_decision.md`（Connect/Disconnect 不整合の判定テーブル）

### Freeze

- 現在状態: **条件付き運用**
- 継続条件: confirmed すり抜けなし・status が freeze に変わる・Audit Log に正しく記録される
- 見るべき確認点: confirmed 通過フロー・status 変更の3画面整合・Audit Log の action/target/result
- 条件付き運用を外す条件: 5回連続で全条件を通過し、報告ゼロが続いた場合
- 異常時の参照先: `gui_go_live_decision.md` / `gui_error_flow_check.md`（Freeze の再評価条件）

### Unfreeze

- 現在状態: **条件付き運用**
- 継続条件: confirmed すり抜けなし・status が元の値に戻る・Audit Log に正しく記録される
- 見るべき確認点: confirmed 通過フロー・status 復帰の3画面整合・Audit Log の action/target/result
- 条件付き運用を外す条件: Freeze と合わせて5回連続で全条件を通過し、報告ゼロが続いた場合
- 異常時の参照先: `gui_go_live_decision.md` / `gui_error_flow_check.md`（Unfreeze の再評価条件）

### Export

- 現在状態: **条件付き運用**
- 継続条件: 認証不足で通過しない・LockGuard が正常閉鎖・Audit Log に整合記録がある
- 見るべき確認点: 認証チェック通過有無・LockGuard 閉鎖確認・Audit Log と実行結果の整合
- 条件付き運用を外す条件: 5回連続で全条件を通過し、報告ゼロが続いた場合
- 異常時の参照先: `gui_go_live_decision.md` / `gui_error_flow_check.md`（Export の再評価条件）

### Delete

- 現在状態: **条件付き運用**
- 継続条件: Export 条件をすべて満たした上で、削除後に3画面整合・Audit Log に整合記録がある
- 見るべき確認点: Export と同じ指標 + 削除後の一覧・詳細・Dashboard 整合確認
- 条件付き運用を外す条件: Export の条件外し条件を満たした上で、Delete 固有の削除後整合が5回確認できた場合
- 異常時の参照先: `gui_go_live_decision.md` / `gui_error_flow_check.md`（Delete の再評価条件）

---

## 最終完成報告フェーズ 機能別完成状態一覧

| 機能 | 完成状態 | 現在の運用状態 | 参照すべき docs |
|---|---|---|---|
| 一覧表示 | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| 詳細表示 | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| Dashboard | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| Audit Log 参照 | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| Settings 参照 | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| Settings 保存 | 条件付き完了 | 条件付き運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` / `docs/gui_error_flow_check.md` |
| Connect | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| Disconnect | 完了 | 本運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` |
| Freeze | 条件付き完了 | 条件付き運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` / `docs/gui_error_flow_check.md` |
| Unfreeze | 条件付き完了 | 条件付き運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` / `docs/gui_error_flow_check.md` |
| Export | 条件付き完了 | 条件付き運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` / `docs/gui_error_flow_check.md` |
| Delete | 条件付き完了 | 条件付き運用 | `docs/gui_handoff_feature_status.md` / `docs/gui_go_live_decision.md` / `docs/gui_error_flow_check.md` |

- 補足:
	- 現時点の保留機能はなし（保留扱いが発生した場合は `docs/gui_known_gaps.md` を更新）
