# GUI 稼働拡大判定結果

- 判定日: 2026-03-23

## 段階解放レベル分け

### Level1: 参照系

- 一覧表示: 読み取り専用で影響が限定的
- 詳細表示: 読み取り専用で状態変更なし
- Dashboard: 集計参照のみで可逆性不要
- Audit Log 参照: 参照のみで監査確認に必要
- Settings 参照: 値確認のみで副作用なし

## Level1 解放機能（今回確定）

- 一覧表示: 参照専用で安全に先行解放できる
- 詳細表示: 参照専用で状態変更を伴わない
- Dashboard: 参照系で影響範囲を限定できる
- Audit Log 参照: 監視基盤として先行解放が必要
- Settings 参照: 設定確認のみで更新リスクがない

## Level1 では解放しない機能（今回）

- Settings 保存: 更新系のため Level1 では解放しない
- Connect: 状態更新系のため Level2 で判定する
- Disconnect: 状態更新系のため Level2 で判定する
- Freeze: 条件付き更新系のため Level3 で判定する
- Unfreeze: 条件付き更新系のため Level3 で判定する
- Export: 危険操作系のため Level4 まで未解放維持
- Delete: 危険操作系のため Level4 まで未解放維持

### Level2: 低リスク更新系

- Connect: 可逆操作で復旧しやすい
- Disconnect: 可逆操作で復旧しやすい

## Level2 解放候補（今回確定）

- Settings 保存: 低リスク更新として反映確認を段階的に実施できる
- Connect: 可逆操作で切り戻ししやすい
- Disconnect: 可逆操作で切り戻ししやすい

## Level2 今回解放する機能（実行フェーズ確定）

- Settings 保存: 低リスク更新として影響を限定しつつ判定できる
- Connect: 可逆操作で参照系を壊さずに動作確認しやすい
- Disconnect: 可逆操作で参照系を壊さずに動作確認しやすい

## Level2 でもまだ解放しない機能（実行フェーズ）

- Freeze: 条件付き更新系で fail-safe 前提のため Level3 まで未解放維持
- Unfreeze: 条件付き更新系で fail-safe 前提のため Level3 まで未解放維持
- Export: 危険操作系で LockGuard 前提のため Level4 まで未解放維持
- Delete: 危険操作系で LockGuard 前提のため Level4 まで未解放維持

## Level2 ではまだ解放しない機能（今回）

- Freeze: 条件付き更新系のため Level3 で判定
- Unfreeze: 条件付き更新系のため Level3 で判定
- Export: 危険操作系のため Level4 まで未解放維持
- Delete: 危険操作系のため Level4 まで未解放維持

### Level1 継続対象との関係

- 一覧表示: Level2 更新結果の反映先として継続監視を維持する
- 詳細表示: Connect/Disconnect 後の表示整合確認の基盤として維持する
- Dashboard: Settings 保存影響の有無確認の基盤として維持する
- Audit Log 参照: 更新操作の記録確認の基盤として維持する
- Settings 参照: Settings 保存後の値整合確認の基盤として維持する

### Level3: 条件付き更新系

- Settings 保存: 永続値更新のため整合監視が必要
- Freeze: 業務影響があり fail-safe 前提
- Unfreeze: 業務影響があり fail-safe 前提

### Level4: 危険操作系

- Export: 取り消し不能要素があり LockGuard 前提
- Delete: 取り消し不能で誤操作影響が大きい

## Level4 今回解放候補（確定）

- Export: 危険操作系として最終段階で判定し、LockGuard・fail-safe・監査ログ整合を満たした場合のみ解放候補にする
- Delete: 危険操作系として最終段階で判定し、LockGuard・fail-safe・誤削除防止確認を満たした場合のみ解放候補にする

### Level1 / Level2 / Level3 継続対象との関係（Level4準備）

- 一覧表示/詳細表示/Dashboard/Audit Log 参照: Export/Delete 後の表示整合確認の土台として継続維持する
- Settings 参照/Settings 保存/Connect/Disconnect/Freeze/Unfreeze: Level4 判定時も巻き込み崩れがないことを前提条件にする

### Level4 の位置づけ

- Level4 は最後に解放する段階であり、Export / Delete は Level3 判定対象外のまま Level4 でのみ判定する

## 拡大する機能

- Settings 保存
- Freeze
- Unfreeze

## まだ段階維持する機能

- Settings 参照
- Connect
- Disconnect

## 未解放維持する機能

- Export
- Delete

## 拡大後の監視項目

- 再描画整合（一覧・詳細・Dashboard・Audit Log）
- message 表示整合（成功/失敗/認証失敗）
- 状態更新整合（connectionStatus / freezeStatus）
- Audit Log 自動追記の成功率
- Settings 保存後の値保持
- 危険操作 fail-safe の中断動作
- LockGuard の誤作動有無

## 停止判断条件

- 再描画崩れ: 即停止
- message 不整合: 条件付き停止
- 状態更新不整合: 即停止
- Audit Log 更新失敗の継続発生: 条件付き停止
- Settings 保存不整合: 即停止
- 危険操作 fail-safe 不備: 即停止
- LockGuard 誤作動: 条件付き停止

## 次の見直しタイミング

- 拡大開始から初回監視サイクル完了時
- 同一異常の再発時
- 本API差し替え完了時
- LockGuard 検証完了時
- Export/Delete 解放判定レビュー時

## 段階解放計画反映済みチェック欄

- [ ] 計画日を記録した
- [ ] Level1 解放計画を反映した
- [ ] Level2 解放計画を反映した
- [ ] Level3 解放計画を反映した
- [ ] Level4 解放計画を反映した
- [ ] Level別の解放条件を反映した
- [ ] Level別の監視項目を反映した
- [ ] Level別の巻き戻し条件を反映した

## Level別解放判定欄

- Level1: 未判定 / 解放可 / 保留
- Level2: 未判定 / 解放可 / 保留
- Level3: 未判定 / 解放可 / 保留
- Level4: 未判定 / 解放可 / 保留

## 巻き戻し条件確認欄

- [ ] Level1 の巻き戻し条件を確認した
- [ ] Level2 の巻き戻し条件を確認した
- [ ] Level3 の巻き戻し条件を確認した
- [ ] Level4 の巻き戻し条件を確認した
- [ ] 一段階戻す時の対象機能を記録した
- [ ] 即停止時の停止対象を記録した

## Level3 解放候補（今回確定）

- Freeze: 条件付き更新系、fail-safe 確認済みを前提に Level2 安定後に解放する
- Unfreeze: 条件付き更新系、fail-safe 確認済みを前提に Level2 安定後に解放する

## Level3 今回解放する機能（実行フェーズ確定）

- Freeze: 警告表示つき更新系として参照系・低リスク更新系を壊さずに動作確認しやすい
- Unfreeze: 警告表示つき更新系として参照系・低リスク更新系を壊さずに動作確認しやすい

## Level3 でもまだ解放しない機能（実行フェーズ）

- Export: 危険操作系で LockGuard 前提のため Level4 まで未解放維持
- Delete: 危険操作系で誤操作影響が大きく LockGuard 前提のため Level4 まで未解放維持

## Level3 ではまだ解放しない機能（今回）

- Export: 危険操作系で LockGuard 前提のため Level4 まで未解放維持
- Delete: 危険操作系で LockGuard 前提のため Level4 まで未解放維持

### Level1 / Level2 継続対象との関係（Level3）

- 一覧表示: Freeze/Unfreeze 後の表示整合確認の基盤として継続維持する
- 詳細表示: Freeze/Unfreeze 後の freezeStatus 確認の基盤として継続維持する
- Dashboard: Freeze/Unfreeze 後の集計値整合確認の基盤として継続維持する
- Audit Log 参照: Freeze/Unfreeze 操作の記録確認の基盤として継続維持する
- Settings 保存: Level3 操作との干渉がないことを継続確認する
- Connect/Disconnect: Freeze/Unfreeze との状態整合を継続確認する

---

## Level4 今回解放する機能（実行フェーズ確定）

- Export: 最終危険操作段階。LockGuard 検証・認証フィールド確認・fail-safe 確認が完了したため解放対象に確定する
- Delete: 最終危険操作段階。LockGuard 検証・認証フィールド確認・fail-safe 確認が完了したため解放対象に確定する

## Level4 でもまだ解放しない機能

- 該当なし（Level4 対象は Export / Delete のみ）

### Level1 / Level2 / Level3 継続対象との関係（Level4）

- 一覧表示: Export/Delete 後の状態整合確認の基盤として継続維持する
- 詳細表示: Export/Delete 後の対象状態確認の基盤として継続維持する
- Dashboard: Export/Delete 後の集計整合確認の基盤として継続維持する
- Audit Log 参照: Export/Delete の証跡確認の基盤として継続維持する
- Settings 保存: Level4 操作との干渉がないことを継続確認する
- Connect/Disconnect: Level4 操作後の状態整合を継続確認する
- Freeze/Unfreeze: Level4 操作後の状態整合を継続確認する

### Level4 の位置づけ

- Level4 は最終解放段階であり、最も厳しく扱う
- confirmed チェック・password・twoFactorCode・confirmationText・Audit Log・再描画・停止条件が全て揃っていることを前提とする
- Level1 / Level2 / Level3 の解放機能を巻き込んで崩さないことが最優先
