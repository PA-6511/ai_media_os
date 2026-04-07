# GUI 小規模稼働開始ログ

- 開始日: 2026-03-23

## Level別 重点監視項目（段階解放）

### Level1: 参照系

- 一覧/詳細表示整合
  - 重点監視: 選択変更後に一覧と詳細が同一対象で一致する
- Dashboard 更新
  - 重点監視: 一覧件数・状態集計との乖離がない
- Audit Log 更新
  - 重点監視: 参照操作後の表示最新化が維持される
- message 表示
  - 重点監視: 取得失敗時に失敗 message が表示される

### Level1 参照系 安定監視ポイント（Dashboard / Audit Log / Settings）

- Dashboard 数値が表示され続けるか
  - 正常: 画面遷移・再読込後も数値表示が維持される
  - 異常兆候: 数値が空欄化する、表示が消える
- Audit Log 一覧が崩れず読めるか
  - 正常: ログ行・列が崩れず、内容を継続して確認できる
  - 異常兆候: 行欠落、列崩れ、順序崩れで読めない
- Settings 参照値が空にならないか
  - 正常: 参照値が取得され、空欄や初期値固定にならない
  - 異常兆候: 値が空欄化する、取得後に消える
- 参照系表示が古いまま固まらないか
  - 正常: 再取得後に最新状態へ更新される
  - 異常兆候: 一覧/詳細/Dashboard/Audit Log/Settings が古い表示のまま固定される
- プレースホルダー復帰が適切か
  - 正常: 取得失敗時にプレースホルダーへ戻り、再取得成功で通常表示に戻る
  - 異常兆候: 失敗後に空白表示のまま復帰しない

### Level2: 低リスク更新系

- Connect / Disconnect 結果
  - 重点監視: connectionStatus が一覧・詳細で一致して遷移する
- 一覧/詳細表示整合
  - 重点監視: 操作直後の再描画で古い状態が残らない
- Audit Log 更新
  - 重点監視: connect/disconnect の action/target/result が追記される
- message 表示
  - 重点監視: 成功/失敗 message が結果と一致する

### Level2 解放直後の監視項目（今回）

- Settings 保存結果
  - 何を見れば正常か: 保存後の再読込で値が保持され、失敗時は値不変
- Connect 実行結果
  - 何を見れば正常か: 実行後に接続状態が一覧・詳細・管理パネルで一致する
- Disconnect 実行結果
  - 何を見れば正常か: 実行後に切断状態が一覧・詳細・管理パネルで一致する
- Audit Log 更新
  - 何を見れば正常か: Settings/Connect/Disconnect の記録が欠落なく追記される
- message 表示内容
  - 何を見れば正常か: 成功/失敗 message が操作結果と一致して過不足なく表示される
- 再描画整合
  - 何を見れば正常か: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する
- 詳細/一覧/管理パネルの状態整合
  - 何を見れば正常か: 同一対象の状態が3画面で不一致なく反映される

### Level1 参照系の巻き込み崩れ監視

- 一覧表示
  - 何を見れば正常か: Level2 操作後も一覧表示の崩れ・欠落がない
- 詳細表示
  - 何を見れば正常か: Level2 操作後も詳細表示が選択対象と一致する
- Dashboard
  - 何を見れば正常か: Level2 操作後も集計表示が継続して読める
- Audit Log 参照
  - 何を見れば正常か: Level2 操作後もログ一覧が崩れず読める
- Settings 参照
  - 何を見れば正常か: Level2 操作後も参照値が空欄化しない

## Level2 解放直後 監視チェック欄（実行フェーズ固定）

- [ ] Settings 保存結果
  - 正常: 保存後の再読込で値保持、失敗時は値不変
- [ ] Connect 実行結果
  - 正常: 実行後に接続状態が詳細/一覧/管理パネルで一致
- [ ] Disconnect 実行結果
  - 正常: 実行後に切断状態が詳細/一覧/管理パネルで一致
- [ ] Audit Log 更新
  - 正常: Settings/Connect/Disconnect の記録が欠落なく追記
- [ ] message 表示内容
  - 正常: 成功/失敗 message が操作結果と一致
- [ ] 再描画整合
  - 正常: 一覧・詳細・Dashboard・Audit Log が同時に整合
- [ ] 詳細/一覧/管理パネルの状態整合
  - 正常: 同一対象の状態が3画面で不一致なし

## Level3 解放直後の監視項目（今回）

- Freeze 実行結果
  - 何を見れば正常か: 確認チェック後の実行で freezeStatus が `frozen` に反映される
- Unfreeze 実行結果
  - 何を見れば正常か: 確認チェック後の実行で freezeStatus が `active` に反映される
- 警告表示の開閉
  - 何を見れば正常か: Freeze/Unfreeze の警告モーダルが開閉でき、閉じた後に画面が崩れない
- 確認チェック後のみ実行されるか
  - 何を見れば正常か: confirmed 未チェック時は実行されず、チェック後のみ実行される
- Audit Log 更新
  - 何を見れば正常か: Freeze/Unfreeze 操作ごとに action/target/result が追記される
- message 表示内容
  - 何を見れば正常か: 成功/失敗 message が操作結果と一致し、誤表示がない
- 再描画整合
  - 何を見れば正常か: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する
- 一覧/詳細/管理パネルの状態整合
  - 何を見れば正常か: 同一対象の freezeStatus が3画面で一致する

### Level1 / Level2 解放機能の巻き込み崩れ監視（Level3直後）

- 一覧表示
  - 何を見れば正常か: Freeze/Unfreeze 後も行欠落・表示崩れがない
- 詳細表示
  - 何を見れば正常か: Freeze/Unfreeze 後も選択対象と詳細が一致する
- Dashboard
  - 何を見れば正常か: Freeze/Unfreeze 後も集計が空欄化せず一覧と整合する
- Audit Log 参照
  - 何を見れば正常か: Freeze/Unfreeze 後もログ一覧が読める状態を維持する
- Settings 参照/保存
  - 何を見れば正常か: Freeze/Unfreeze 実行後も参照値・保存結果が崩れない
- Connect/Disconnect
  - 何を見れば正常か: Freeze/Unfreeze 実行後も connectionStatus 表示整合が維持される

## Level3 解放直後 監視チェック欄（実行フェーズ固定）

- [ ] Freeze 実行結果
  - 正常: 確認チェック後のみ実行され、freezeStatus が `frozen` に反映
- [ ] Unfreeze 実行結果
  - 正常: 確認チェック後のみ実行され、freezeStatus が `active` に反映
- [ ] 警告表示の開閉
  - 正常: Freeze/Unfreeze の警告モーダルが開閉でき、閉じた後も画面が崩れない
- [ ] 確認チェック後のみ実行されるか
  - 正常: confirmed 未チェック時は中断、チェック後のみ実行
- [ ] Audit Log 更新
  - 正常: Freeze/Unfreeze の記録が欠落なく追記
- [ ] message 表示内容
  - 正常: 成功/失敗 message が操作結果と一致
- [ ] 再描画整合
  - 正常: 一覧・詳細・Dashboard・Audit Log が同時に整合
- [ ] 一覧/詳細/管理パネルの状態整合
  - 正常: 同一対象の状態が3画面で不一致なし

## Level4 解放直後の監視項目（今回）

- Export 実行結果
  - 何を見れば正常か: 認証・確認通過時のみ実行され、成功時のみ反映される
- Delete 実行結果
  - 何を見れば正常か: 認証・確認通過時のみ実行され、成功時のみ対象状態が更新される
- LockGuard の開閉
  - 何を見れば正常か: Export/Delete で LockGuard が開閉でき、閉じた後に画面が崩れない
- confirmed チェック後のみ実行されるか
  - 何を見れば正常か: confirmed 未チェック時は実行されず、チェック後のみ実行される
- password / twoFactorCode / confirmationText 不足時に止まるか
  - 何を見れば正常か: いずれか不足時は実行中断し、状態変更が発生しない
- Audit Log 更新
  - 何を見れば正常か: Export/Delete の action/target/result が欠落なく追記される
- message 表示内容
  - 何を見れば正常か: 成功/失敗/認証失敗 message が操作結果と一致する
- 再描画整合
  - 何を見れば正常か: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する
- 一覧/詳細/管理パネルの状態整合
  - 何を見れば正常か: 同一対象の状態が3画面で一致し不整合が残らない

### Level1 / Level2 / Level3 解放機能の巻き込み崩れ監視（Level4直後）

- 一覧表示
  - 何を見れば正常か: Export/Delete 後も行欠落・表示崩れがない
- 詳細表示
  - 何を見れば正常か: Export/Delete 後も選択対象と詳細表示が一致する
- Dashboard
  - 何を見れば正常か: Export/Delete 後も集計表示が空欄化せず整合する
- Audit Log 参照
  - 何を見れば正常か: Export/Delete 後もログ一覧が読める状態を維持する
- Settings 参照/保存
  - 何を見れば正常か: Export/Delete 実行後も参照値・保存結果が崩れない
- Connect/Disconnect
  - 何を見れば正常か: Export/Delete 実行後も connectionStatus 表示整合が維持される
- Freeze/Unfreeze
  - 何を見れば正常か: Export/Delete 実行後も freezeStatus 表示整合が維持される

### Freeze / Unfreeze 警告表示・確認導線 安定監視ポイント

- 警告表示が正しく開くか
  - 正常: Freeze / Unfreeze 操作時に対象操作に対応した警告表示が開く
  - 異常兆候: 警告表示が開かない、別操作の文言で開く、二重に開く
- キャンセルで正しく閉じるか
  - 正常: キャンセル操作で警告表示が閉じ、freezeStatus や他表示に変化が出ない
  - 異常兆候: 閉じない、閉じても背景操作ができない、状態だけ変わる
- 確認チェック未実施時に実行されないか
  - 正常: confirmed 未チェックでは Freeze / Unfreeze が実行されない
  - 異常兆候: 未チェックでも実行できる、または実行要求が通る
- 実行後に警告表示が残らないか
  - 正常: 実行完了後に警告表示が閉じ、次画面操作へ戻れる
  - 異常兆候: 成功/失敗後も警告表示が残る、再操作不能になる
- message が適切か
  - 正常: 警告表示経由の成功/失敗に応じて message が結果どおり表示される
  - 異常兆候: message が出ない、内容が逆転する、同一結果で重複表示される
- 他画面に誤影響が出ないか
  - 正常: 一覧・詳細・Dashboard・Audit Log・Settings・Connect/Disconnect 表示が崩れない
  - 異常兆候: 警告表示の開閉や実行後に他画面が空白化、崩れ、操作不能になる
- LockGuard と混同されないか
  - 正常: Freeze / Unfreeze の警告導線として扱われ、Export / Delete 用 LockGuard 導線とは別挙動である
  - 異常兆候: Export / Delete 用の認証導線や文言が混在して表示される

### Level3 実行フェーズでの見る順序

- 確認チェック未投入での事前確認
  - 正常: confirmed 未チェックでは Freeze/Unfreeze が実行されない
- 確認チェック投入後の本実行
  - 正常: Freeze/Unfreeze の結果が一覧/詳細/管理パネルへ即時反映される
- 実行直後の表示確認
  - 正常: 警告表示、message、Audit Log が操作結果と矛盾なく更新される
- 再描画完了後の整合確認
  - 正常: 一覧・詳細・Dashboard・Audit Log の再描画後も状態不一致がない
- 既存解放機能の巻き込み確認
  - 正常: Level1 / Level2 で解放済みの参照・更新機能が Freeze/Unfreeze 後も崩れない

### Level1 参照系 巻き込み崩れ確認（固定）

- [ ] 一覧表示
  - 正常: Level2 操作後も行欠落・表示崩れなし
- [ ] 詳細表示
  - 正常: Level2 操作後も選択対象と詳細表示が一致
- [ ] Dashboard
  - 正常: Level2 操作後も数値表示が空欄化しない
- [ ] Audit Log 参照
  - 正常: Level2 操作後もログ一覧が読める
- [ ] Settings 参照
  - 正常: Level2 操作後も参照値が空欄化しない

### Connect / Disconnect 安定監視ポイント

- Connect 後に connectionStatus が整合するか
  - 正常: 接続実行後、一覧・詳細・管理パネルで状態が「connected」に統一される
  - 異常兆候: 一部の画面で接続状態が反映されず、状態が不一致のまま継続する
- Disconnect 後に connectionStatus が整合するか
  - 正常: 切断実行後、一覧・詳細・管理パネルで状態が「disconnected」に統一される
  - 異常兆候: 一部の画面で切断状態が反映されず、接続状態のまま表示が固定される
- 詳細/一覧/管理パネルで表示が揃うか
  - 正常: Connect/Disconnect の操作直後に、3画面の表示が同一の状態を示す
  - 異常兆候: 画面遷移時に状態表示がズレたり、複数の状態が混在して表示される
- message が適切か
  - 正常: Connect/Disconnect の成功/失敗時に、結果に対応した message が即座に表示される
  - 異常兆候: message が出ない、失敗時も成功 message が表示される
- Audit Log が更新されるか
  - 正常: Connect/Disconnect の操作後、Audit Log に action/target/result が追記される
  - 異常兆候: 操作後も Audit Log に記録が追加されない、または記録内容が誤る
- 参照系が巻き込まれて崩れないか
  - 正常: Connect/Disconnect 実行後も、一覧・詳細・Dashboard・Audit Log が崩れず表示される
  - 異常兆候: 状態操作後に参照系の表示が欠落、崩れ、初期化されるなどの影響が出る

### Level3: 条件付き更新系

- Settings 保存結果
  - 重点監視: 保存後再読込で値保持、失敗時は値不変
- Freeze / Unfreeze 結果
  - 重点監視: freezeStatus が一覧・詳細・Dashboard で一致して遷移する
- Audit Log 更新
  - 重点監視: settings/freeze/unfreeze のログ欠落がない
- message 表示
  - 重点監視: 保存・凍結操作の成功/失敗が正しく表示される

### Level4: 危険操作系（厳格監視）

- LockGuard 導線
  - 重点監視: confirmed/認証不足で必ず中断し、誤実行しない
- Export / Delete 結果
  - 重点監視: 成功時のみ反映、失敗時は state 不変
- Audit Log 更新
  - 重点監視: export/delete の成功・失敗が欠落なく記録される
- message 表示
  - 重点監視: 認証失敗・実行失敗・成功の区別が明確

## 開始した機能

- 一覧表示
- 詳細表示
- Dashboard
- Audit Log 参照

## 条件付きで開始した機能

- Settings 参照（表示確認専用として限定運用）
- Connect（監視付き・可逆操作）
- Disconnect（監視付き・可逆操作）

## 保留した機能

- Settings 保存（本API接続前のため保留）
- Freeze（本API接続前のため保留）
- Unfreeze（本API接続前のため保留）
- Export（取り消し不能・LockGuard未検証のため保留）
- Delete（取り消し不能・LockGuard未検証のため保留）

## 開始直後に見る項目

- 一覧表示が崩れずに表示されるか
- 詳細パネルが選択に応じて更新されるか
- Dashboard 集計が一覧データと整合するか
- Audit Log にログ行が正しく表示されるか
- Connect/Disconnect で connectionStatus が一覧に反映されるか
- message が操作結果に応じて表示されるか
- 操作後に再描画整合（一覧・詳細・Dashboard・Audit Log）が取れているか

## Level1 解放直後の監視項目（今回）

- 一覧表示の安定性
  - 正常の見方: リロード・再取得後も一覧の行/列が崩れず表示される
- 詳細表示の安定性
  - 正常の見方: 一覧の選択変更に追従して詳細が即時更新される
- Dashboard 数値表示
  - 正常の見方: 一覧の件数・状態内訳と Dashboard 数値が一致する
- Audit Log 一覧表示
  - 正常の見方: ログ一覧が表示され、最新行まで欠落なく確認できる
- Settings 参照表示
  - 正常の見方: 現在値が空欄化せず画面に反映される
- message 表示有無
  - 正常の見方: 取得成功/失敗に応じた message が1件ずつ正しく表示される
- プレースホルダー復帰
  - 正常の見方: 詳細取得失敗時にプレースホルダーへ戻り、再取得成功で通常表示へ復帰する

## 問題発生時の停止判断

- UI 表示と API 結果が乖離する
- Audit Log が操作後に更新されない
- confirmed 未チェックで危険操作 API が通る
- Console に未処理例外が継続発生する
- message が出ない・誤った内容で表示される
- 上記いずれかが発生した場合は即時該当機能を保留に戻す

## 次の見直し予定

- 本API差し替え完了後: Settings 保存・Freeze/Unfreeze の解放判定を実施
- LockGuard 本番相当検証完了後: Export/Delete の解放判定を実施
- 監視中に停止判断条件を満たした場合: 即時保留とし再発防止後に再判定

---

## 初回監視 観測項目（2026-03-23）

- 一覧表示の安定性
  - 何を見るか: ページ遷移・操作後に一覧が崩れず再描画されているか
- 詳細表示の安定性
  - 何を見るか: 一覧の選択変更に連動して詳細パネルが正しく更新されるか
- Dashboard 更新
  - 何を見るか: 操作後の集計値が一覧データと整合しているか
- Audit Log 更新
  - 何を見るか: 各操作後にログ行が自動追記され、action/target/result が正しいか
- Settings 保存結果
  - 何を見るか: 保存後に値が反映されているか（現フェーズは参照のみ、保存は保留）
- message 表示
  - 何を見るか: 操作結果に応じた message が適切なタイミングで表示されるか
- 再描画整合
  - 何を見るか: 操作後に一覧・詳細・Dashboard・Audit Log がすべて一貫した状態になるか

---

## 条件付き稼働機能 停止判断（2026-03-23）

### Settings 保存
- 続行条件: 保存後に値が画面に反映され、Audit Log に記録されている
- 停止判断条件: 値未反映・Audit Log 未記録・message が出ない
- 停止後に確認すること: API レスポンス内容・エラーログ・再描画タイミング

### Freeze
- 続行条件: 実行後に freezeStatus が frozen に変わり一覧・詳細・Audit Log に反映される
- 停止判断条件: 状態未反映・Audit Log 未記録・confirmed 未チェックで実行された
- 停止後に確認すること: confirmed ガード動作・API レスポンス・freezeStatus 遷移

### Unfreeze
- 続行条件: 実行後に freezeStatus が active に戻り一覧・詳細・Audit Log に反映される
- 停止判断条件: 状態未反映・Audit Log 未記録・confirmed 未チェックで実行された
- 停止後に確認すること: confirmed ガード動作・API レスポンス・freezeStatus 遷移

### Audit Log 更新
- 続行条件: 各操作後にログ行が自動追記され action/target/result が正しい
- 停止判断条件: 追記されない・内容が空・順序が逆転する状態が継続する
- 停止後に確認すること: API 呼び出しタイミング・レスポンス内容・表示レンダリング

### Export / Delete（保留前提）
- 続行条件: 該当せず（現フェーズは保留）
- 停止判断条件: 保留中に誤って実行可能になっていた場合は即時停止
- 停止後に確認すること: confirmed ガード・LockGuard 認証の動作確認

---

## 初回監視済みチェック欄（2026-03-23）

- [ ] 一覧表示: 監視済み
- [ ] 詳細表示: 監視済み
- [ ] Dashboard: 監視済み
- [ ] Audit Log 参照: 監視済み
- [ ] Settings 参照: 監視済み
- [ ] Connect: 監視済み
- [ ] Disconnect: 監視済み

## 初回監視での問題有無

- 問題あり / なし: （記録する）
- 内容: （異常兆候・停止判断があれば記録する）

## 次回監視予定

- 次回日程: （記録する）
- 重点確認項目: （継続監視に回した項目を記録する）

---

## 条件付き継続 追加監視条件（2026-03-23）

### Settings 保存
- 継続条件: 保存後に値保持・message 表示・Audit Log 記録が一致する
- 追加で見るべき指標: 保存成功率、保存後再読込一致率、保存失敗時の値不変率
- 監視頻度: 各監視サイクルで最低3回操作確認
- 継続中止条件: 値巻き戻り、message 不整合、Audit Log 未記録が再発する

### Freeze
- 継続条件: freezeStatus が frozen へ反映し、一覧/詳細/Audit Log が一致する
- 追加で見るべき指標: 状態反映遅延、confirmed fail-safe 検知件数、ログ追記成功率
- 監視頻度: 監視サイクルごとに1回以上の実行確認
- 継続中止条件: 状態未反映、confirmed すり抜け、ログ未追記が発生する

### Unfreeze
- 継続条件: freezeStatus が active へ復帰し、一覧/詳細/Audit Log が一致する
- 追加で見るべき指標: 復帰反映遅延、confirmed fail-safe 検知件数、ログ追記成功率
- 監視頻度: 監視サイクルごとに1回以上の実行確認
- 継続中止条件: 状態未復帰、confirmed すり抜け、ログ未追記が発生する

### Audit Log 更新
- 継続条件: 全操作で action/target/result が正しい順序で自動追記される
- 追加で見るべき指標: ログ追記欠落率、内容不一致件数、順序逆転件数
- 監視頻度: 主要操作後に毎回確認
- 継続中止条件: 追記欠落・内容不一致・順序逆転が連続して発生する

---

## 継続判定済みチェック欄（2026-03-23）

- [ ] 判定日を記録した
- [ ] 継続する機能を記録した
- [ ] 条件付き継続にする機能を記録した
- [ ] 一旦止める機能を記録した
- [ ] 継続監視項目を記録した
- [ ] 再開条件を記録した

## 条件付き継続の有無

- あり / なし: （記録する）
- 対象機能: （記録する）

## 停止対象の有無

- あり / なし: （記録する）
- 対象機能: （記録する）

## 次回判定予定

- 判定予定日: （記録する）
- 判定トリガー: （監視サイクル完了 / 中止条件発生 / 再開条件充足 など）

---

## 稼働拡大時 重点監視項目（2026-03-23）

- 再描画整合
  - 拡大直後に見るべきこと: 一覧・詳細・Dashboard・Audit Log の表示が同時に整合する
- message 表示
  - 拡大直後に見るべきこと: 成功/失敗/入力エラーの message が操作結果に一致する
- Audit Log 更新
  - 拡大直後に見るべきこと: 主要操作の action/target/result が欠落なく追記される
- Settings 保存結果
  - 拡大直後に見るべきこと: 保存後に再読込しても値が保持される
- Connect / Disconnect 結果
  - 拡大直後に見るべきこと: connectionStatus 反映が一覧・詳細・ログで一致する
- Freeze / Unfreeze 結果
  - 拡大直後に見るべきこと: freezeStatus 遷移と confirmed fail-safe が一致して動作する
- 危険操作導線の誤作動有無
  - 拡大直後に見るべきこと: Export / Delete が未解放時に実行可能化されていない

---

## Level4 LockGuard・認証導線 安定監視ポイント（固定）

> Freeze / Unfreeze の警告表示導線とは別系統として確認する。

- LockGuard が正しく開くか
  - 正常: Export / Delete 開始時に対象操作用 LockGuard が1回だけ表示される
  - 異常兆候: 開かない、別操作向け文言が出る、二重表示される
- キャンセルで正しく閉じるか
  - 正常: キャンセルで LockGuard が閉じ、状態変更が発生しない
  - 異常兆候: 閉じない、閉じた後も状態が変化する、背景操作が不能になる
- confirmed チェック未実施時に実行されないか
  - 正常: confirmed 未チェックでは実行要求が通らない
  - 異常兆候: 未チェックで API 呼び出しまたは実行完了が発生する
- password 不足で止まるか
  - 正常: password 未入力時は実行中断し、状態変更が起きない
  - 異常兆候: password 未入力でも実行される
- twoFactorCode 不足で止まるか
  - 正常: twoFactorCode 未入力時は実行中断し、状態変更が起きない
  - 異常兆候: twoFactorCode 未入力でも実行される
- confirmationText 不一致で止まるか
  - 正常: confirmationText 不一致時は実行中断し、状態変更が起きない
  - 異常兆候: 不一致でも実行される、誤った対象に適用される
- 実行後に LockGuard が残らないか
  - 正常: 成功/失敗いずれでも処理後に LockGuard が閉じる
  - 異常兆候: 処理後も残留する、再実行不可になる
- 他画面に誤影響が出ないか
  - 正常: 一覧・詳細・Dashboard・Audit Log・Settings・Connect/Disconnect・Freeze/Unfreeze が崩れない
  - 異常兆候: 表示崩れ、状態食い違い、操作不能が発生する

---

## 最終運用判定フェーズ 本運用後の重点監視項目（固定）

- 一覧/詳細表示整合
  - 何を見れば正常か: 同一対象の状態が一覧・詳細で一致し、操作後も不整合が残らない
- Dashboard 更新
  - 何を見れば正常か: 各操作後に件数・状態表示が即時反映され、古い状態が残らない
- Audit Log 更新
  - 何を見れば正常か: 全操作で action / target / result が欠落なく追記される
- Settings 保存結果
  - 何を見れば正常か: 保存後に反映され、空欄化・巻き戻りが発生しない
- Connect / Disconnect 結果
  - 何を見れば正常か: 実行後に3画面の状態が整合し、message が結果と一致する
- Freeze / Unfreeze 結果
  - 何を見れば正常か: confirmed 通過後のみ実行され、status が正しく更新・整合する
- Export 結果
  - 何を見れば正常か: LockGuard・confirmed・認証通過後のみ実行され、Audit Log に追記される
- Delete 結果
  - 何を見れば正常か: Export と同条件 + 削除後に一覧・詳細・管理パネルが整合する
- LockGuard / 認証導線
  - 何を見れば正常か: confirmed 未チェック・認証不足で実行が通らず、LockGuard が実行後に正常閉鎖する
- message 表示内容
  - 何を見れば正常か: 成功・失敗・認証失敗の表示が操作結果と常に一致する
- 再描画整合
  - 何を見れば正常か: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合し、空白化・崩れが出ない

---

## 最終運用開始フェーズ 本運用開始直後の重点監視項目（固定）

- 一覧/詳細表示整合
  - 何を見れば正常か: 開始直後の操作後も一覧・詳細の同一対象状態が一致する
- Dashboard 更新
  - 何を見れば正常か: 開始直後の各操作反映で件数・状態が即時更新される
- Audit Log 更新
  - 何を見れば正常か: 開始直後の全操作で action / target / result が欠落なく追記される
- Settings 保存結果
  - 何を見れば正常か: 開始直後の保存が反映され、空欄化・巻き戻りが発生しない
- Connect / Disconnect 結果
  - 何を見れば正常か: 開始直後の接続切替後に状態表示と実結果が一致する
- Freeze / Unfreeze 結果
  - 何を見れば正常か: 開始直後も confirmed 通過時のみ実行され、状態整合が維持される
- Export / Delete 結果
  - 何を見れば正常か: 開始直後も実行条件充足時のみ通過し、結果が画面と Audit Log に一致する
- LockGuard / 認証導線
  - 何を見れば正常か: 開始直後も confirmed 未チェック・認証不足で実行が通らず、LockGuard が正常閉鎖する
- message 表示内容
  - 何を見れば正常か: 開始直後の成功/失敗/認証失敗表示が操作結果と一致する
- 再描画整合
  - 何を見れば正常か: 開始直後の操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する

---

## 最終運用初回監視フェーズ Freeze/Unfreeze・Export/Delete 初回監視ポイント（固定）

### Freeze
- 正常: confirmed 通過後のみ実行され、status 変更が一覧・詳細・管理パネルで一致する
- 異常兆候: confirmed 未チェックで実行される、status が3画面で不一致になる

### Unfreeze
- 正常: confirmed 通過後のみ実行され、status 復帰が一覧・詳細・管理パネルで一致する
- 異常兆候: confirmed 未チェックで実行される、復帰後も状態不整合が残る

### Export
- 正常: LockGuard・認証通過後のみ実行され、結果が画面表示と一致する
- 異常兆候: 認証不足で実行される、成功/失敗結果と表示が食い違う

### Delete
- 正常: LockGuard・認証通過後のみ実行され、削除後状態が一覧・詳細・管理パネルで一致する
- 異常兆候: 認証不足で実行される、削除後に3画面不整合が残る

### LockGuard / 認証導線
- 正常: confirmed 未チェック・認証不足で実行が通らず、処理後に LockGuard が閉じる
- 異常兆候: 実行すり抜け、LockGuard 残留、誤開閉が発生する

### Audit Log 更新
- 正常: Freeze/Unfreeze/Export/Delete の action / target / result が欠落なく追記される
- 異常兆候: 未追記、内容不一致、順序逆転が発生する

### message 表示内容
- 正常: 成功/失敗/認証失敗の表示が操作結果と一致する
- 異常兆候: message 未表示、逆転表示、前回表示残留が発生する

### 再描画整合
- 正常: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する
- 異常兆候: 再描画遅延、空白化、再描画後も不整合が残る

### 状態整合（一覧/詳細/管理パネル）
- 正常: 同一対象の状態が3画面で一致し続ける
- 異常兆候: いずれか1画面だけ更新され、食い違いが継続する
