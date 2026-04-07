# GUI 小規模稼働継続判定結果

- 判定日: 2026-03-23

## 継続する機能

- 一覧表示
- 詳細表示
- Dashboard
- Audit Log 参照

## 条件付き継続にする機能

- Settings 参照
- Settings 保存
- Connect
- Disconnect
- Freeze
- Unfreeze

## 一旦止める機能

- Export
- Delete

## 継続監視項目

- 再描画整合（一覧・詳細・Dashboard・Audit Log）
- message 表示整合（成功/失敗/入力エラー）
- Audit Log 自動追記（action/target/result）
- Settings 保存後の値保持
- Connect / Disconnect の状態遷移整合
- Freeze / Unfreeze の状態遷移整合と fail-safe

## 再開条件

- Export: LockGuard 検証完了、fail-safe 確認完了、異常系確認完了、通し確認完了
- Delete: LockGuard 検証完了、fail-safe 確認完了、異常系確認完了、通し確認完了
- Freeze / Unfreeze（一時停止時）: 状態遷移安定、fail-safe 再確認、異常系再確認、通し確認完了

## 次の判定タイミング

- 次回監視サイクル完了後
- 条件付き継続機能で継続中止条件が発生した時
- 保留機能の再開条件がすべて満たされた時

---

## 稼働拡大 区分整理（2026-03-23）

### 拡大してよい

- 一覧表示: 参照系で安定運用を継続できる
- 詳細表示: 一覧連動が安定している
- Dashboard: 集計整合が継続確認できている
- Audit Log 参照: 監視基盤として安定している
- Settings 参照: 参照 API の連続エラーがない
- Connect: 状態遷移とログ追記が連続一致している
- Disconnect: 状態遷移とログ追記が連続一致している

### まだ段階維持

- Settings 保存: 値保持の安定監視を継続中
- Freeze: fail-safe と状態遷移の継続監視が必要
- Unfreeze: fail-safe と状態復帰の継続監視が必要

### 未解放維持

- Export: 取り消し不能操作で LockGuard 検証完了まで未解放
- Delete: 取り消し不能操作で LockGuard 検証完了まで未解放
