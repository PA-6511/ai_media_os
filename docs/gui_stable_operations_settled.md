# 安定運用定着記録

## 判定日

- 判定日: （記入）
- 判定者: （記入）

---

## 定着運用に入れた機能

- [ ] 一覧表示
- [ ] 詳細表示
- [ ] Dashboard
- [ ] Audit Log 参照
- [ ] Settings 参照
- [ ] Settings 保存

備考: （特記があれば記入）

---

## 条件付き運用継続にした機能

- [ ] Connect（継続条件: 接続後 status が3画面一致）
- [ ] Disconnect（継続条件: 切断後残留なし・status が3画面一致）
- [ ] Freeze（継続条件: confirmed すり抜けなし・status 変更・Audit Log が3画面整合）
- [ ] Unfreeze（継続条件: confirmed すり抜けなし・status 復帰・Audit Log が3画面整合）
- [ ] Export（継続条件: 認証不足通過なし・LockGuard 正常・Audit Log 整合）
- [ ] Delete（継続条件: Export 条件 + 削除後3画面整合）

備考: （特記があれば記入）

---

## 見直し候補として残した機能

- （なければ「なし」と記入）

見直し候補にした理由: （記入）

---

## 定常監視ルール

- 毎回見る（条件付き運用機能の実行ごと）
  - [ ] Freeze / Unfreeze: confirmed 通過・status 整合・Audit Log 欠落なし
  - [ ] Export / Delete: 認証不足通過なし・LockGuard 正常閉鎖・Audit Log・3画面整合
  - [ ] LockGuard / 認証導線: 未チェック・認証不足通過なし、処理後残留なし
  - [ ] message 表示内容: 操作結果と一致、前回残留・逆転表示なし
  - [ ] Audit Log 更新: action / target / result 欠落なく追記
- 変更時に見る（参照系・低リスク更新系の操作ごと）
  - [ ] 一覧/詳細表示整合: 同一対象の status が3画面で一致し続ける
  - [ ] Dashboard 更新: 操作後に件数・状態サマリが即時反映
  - [ ] Settings 保存結果: 保存後の値が保持され再表示でも一致
  - [ ] Connect / Disconnect 結果: status 変更が反映され残留・不整合がない
  - [ ] 再描画整合: 操作後に一覧・詳細・Dashboard・Audit Log が同時整合

---

## 見直し/巻き戻し条件

- **全面見直し**: Export/Delete 認証すり抜け、LockGuard 不備、fail-safe 未発動、confirmed すり抜け、原因不明の多箇所不整合
- **機能単位で巻き戻し**: Freeze/Unfreeze 不整合1件、Audit Log 欠落1件、再描画崩れ、Settings 巻き戻り再発、Connect/Disconnect 不整合
- **継続監視**: message 不整合が単発・軽微、再描画遅延が一時的で自己回復

---

## 次の定期レビュー予定

- 次回レビュー予定日: （記入）
- 次回レビューで確認するもの: 定常監視ルールの累積記録・条件付き運用継続機能の継続条件抵触有無・見直し候補の再安定化状況

---

## 定期レビュー運用フェーズ 定期レビュー対象（固定）

### 毎回レビュー対象

条件付き運用に分類された機能は、実行があった週・月ごとに必ず確認する。

- [ ] Connect — 接続後 status が3画面（一覧/詳細/Dashboard）で一致しているか
- [ ] Disconnect — 切断後に残留データがなく status が3画面で一致しているか
- [ ] Freeze — confirmed すり抜けなし・status が freeze に変わり・Audit Log に正しく記録されているか
- [ ] Unfreeze — confirmed すり抜けなし・status が元に戻り・Audit Log に正しく記録されているか
- [ ] Export — 認証不足で通過なし・LockGuard が正しく閉鎖・Audit Log に整合記録があるか
- [ ] Delete — Export 条件を満たした上で削除後3画面整合・Audit Log に整合記録があるか

### 条件付きで毎回確認する対象

定着運用に分類されているが、変更・更新が入った回は必ず確認する。

- [ ] Settings 保存 — 保存後の値が即時反映し再表示しても一致しているか（設定変更時のみ）
- [ ] Audit Log 参照 — 直近の操作が欠落なく追記されているか（条件付き運用機能の実行後）

### 変化時レビュー対象

定期レビュー時ではなく、対象機能に変更・追加があった際にレビューする。

- [ ] 一覧表示 — 同一対象の status が一覧・詳細・Dashboard で一致しているか（データ追加/変更後）
- [ ] 詳細表示 — 一覧との status 整合・表示フィールドの欠落がないか（対象データ変更後）
- [ ] Dashboard — 件数・状態サマリが操作後に即時反映しているか（条件付き運用機能の実行後）
- [ ] Settings 参照 — 現在の保存値が正しく表示されているか（Settings 保存後）

---

## 定期レビュー運用フェーズ 定期レビュー運用チェック欄（固定）

### 定期レビュー運用開始済みチェック欄

- [ ] 定期レビュー対象を `gui_stable_operations_settled.md` に固定した
- [ ] 条件付き運用機能の定期レビュー条件を `gui_final_operations_start_log.md` に固定した
- [ ] 見直し候補機能の再評価条件を `gui_error_flow_check.md` に固定した
- [ ] 定期レビューでの停止・巻き戻し判断条件を `gui_go_live_decision.md` に固定した
- [ ] 定期レビュー記録テンプレートを `gui_periodic_review_template.md` として作成した

### 定期レビュー記録先欄

- テンプレート: `docs/gui_periodic_review_template.md`（毎回コピーして使用）
- 記録ファイル命名規則: `gui_periodic_review_YYYYMMDD.md`
- 保存先: `docs/` 配下

### 次回定期レビュー予定欄

- 次回レビュー予定日: （記入）
- 次回で重点確認する項目: （記入）
- 判定区分: 全面見直し / 機能単位で巻き戻し / 継続監視

---

## 運用テンプレ整備フェーズ 日次運用テンプレ配置済みチェック欄

- [ ] 日次運用確認テンプレートを `docs/gui_daily_ops_template.md` として作成した
- [ ] テンプレートに全確認項目（一覧/詳細/Dashboard/Audit Log/Settings/Connect/Disconnect/Freeze/Unfreeze/Export/Delete/LockGuard/認証/message/再描画）を含めた
- [ ] 異常有無まとめ・対応メモ欄を含めた

## 日次確認対象欄

- 毎日確認: 一覧/詳細表示・Dashboard・Audit Log・message/再描画
- 操作があった日に追加確認: Connect/Disconnect・Freeze/Unfreeze・Export/Delete・LockGuard/認証・Settings
- テンプレート: `docs/gui_daily_ops_template.md`（毎回コピーして使用）
- 記録ファイル命名規則: `gui_daily_ops_YYYYMMDD.md`

---

## 運用テンプレ整備フェーズ 運用テンプレ索引整備済みチェック欄

- [ ] 運用テンプレ索引を `docs/gui_operations_templates_index.md` として作成した
- [ ] 日次運用・定期レビュー・異常対応・保留再開の4テンプレを索引にまとめた
- [ ] 各テンプレの使うタイミング・命名規則・参照先を記載した
- [ ] 更新時の注意点（テンプレ本体は変更しない・命名規則・保存先）を記載した

## テンプレ参照先欄

| 場面 | 使うテンプレ | ファイル |
|---|---|---|
| 毎日の確認 | 日次運用確認 | `docs/gui_daily_ops_template.md` |
| 定期レビュー実施 | 定期レビュー | `docs/gui_periodic_review_template.md` |
| 異常発生時 | 異常発生時記録 | `docs/gui_incident_response_template.md` |
| 機能保留・再開判断 | 機能保留/再開判断 | `docs/gui_hold_resume_template.md` |
| 索引全体 | 運用テンプレ索引 | `docs/gui_operations_templates_index.md` |

---

## 引き継ぎ用まとめフェーズ 引き継ぎ概要作成済みチェック欄

- [ ] 引き継ぎ概要サマリを `docs/gui_handoff_summary.md` として作成した
- [ ] 本運用中の機能・条件付き運用中の機能・保留中の機能の3区分を記載した
- [ ] まず最初に見る docs（4ファイル）を記載した
- [ ] 障害時に最初に見る docs（優先順付き4ファイル）を記載した
- [ ] 次回レビュー予定欄を設けた

## 引き継ぎ参照先欄

- 引き継ぎ概要サマリ: `docs/gui_handoff_summary.md`
- 運用全体の状態: `docs/gui_stable_operations_settled.md`（本ファイル）
- 運用テンプレ索引: `docs/gui_operations_templates_index.md`
