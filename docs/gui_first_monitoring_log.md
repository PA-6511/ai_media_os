# GUI 初回監視ログ

- 監視日: 2026-03-23

## 監視した機能

- 一覧表示
- 詳細表示
- Dashboard
- Audit Log 参照
- Settings 参照（参照のみ）
- Connect
- Disconnect

## Level1 解放直後の観測項目

- 一覧表示の安定性
	- 何を見れば正常か: 一覧が崩れず、再読込後も同じ行構造で表示される
- 詳細表示の安定性
	- 何を見れば正常か: 選択変更ごとに対象の詳細が遅延なく切り替わる
- Dashboard 数値表示
	- 何を見れば正常か: 一覧データの件数・状態と Dashboard 数値が一致する
- Audit Log 一覧表示
	- 何を見れば正常か: ログ一覧が表示され、表示欠落や順序崩れがない
- Settings 参照表示
	- 何を見れば正常か: 設定参照値が取得され、空欄や初期値固定にならない
- message 表示有無
	- 何を見れば正常か: 成功/失敗時に対応する message が表示される
- プレースホルダー復帰
	- 何を見れば正常か: 詳細取得失敗でプレースホルダー表示へ戻り、再取得成功で復帰する

## Level1 継続観測項目（固定）

- 一覧表示の安定性
	- 何を見れば正常か: 再読込や画面遷移後も一覧表示が崩れない
- 詳細表示の安定性
	- 何を見れば正常か: 一覧選択変更に対して詳細表示が即時反映される
- Dashboard 表示の安定性
	- 何を見れば正常か: 一覧データ件数と Dashboard 数値が一致し続ける
- Audit Log 一覧表示の安定性
	- 何を見れば正常か: ログ一覧の表示欠落・順序崩れが発生しない
- Settings 参照表示の安定性
	- 何を見れば正常か: 設定参照値が空欄化せず安定表示される
- message 表示の有無
	- 何を見れば正常か: 成功/失敗時に対応する message が都度表示される
- プレースホルダー復帰の有無
	- 何を見れば正常か: 詳細取得失敗時にプレースホルダーへ戻り、再取得で通常表示に戻る

## Level2 解放直後の観測項目

- Settings 保存結果
	- 何を見れば正常か: 保存成功後に再読込しても設定値が保持される
- Connect 実行結果
	- 何を見れば正常か: 接続状態が一覧・詳細・管理パネルで一致して反映される
- Disconnect 実行結果
	- 何を見れば正常か: 切断状態が一覧・詳細・管理パネルで一致して反映される
- Audit Log 更新
	- 何を見れば正常か: Settings/Connect/Disconnect の操作記録が追記される
- message 表示内容
	- 何を見れば正常か: 成功/失敗 message が操作結果と一致して表示される
- 再描画整合
	- 何を見れば正常か: 一覧・詳細・Dashboard・Audit Log の再描画が整合する
- 詳細/一覧/管理パネルの状態整合
	- 何を見れば正常か: 同一対象の状態差分が3画面で一致する

### Level1 参照系の巻き込み崩れ確認

- 一覧表示
	- 何を見れば正常か: Level2 操作後も一覧が崩れない
- 詳細表示
	- 何を見れば正常か: Level2 操作後も詳細表示が対象一致を維持する
- Dashboard
	- 何を見れば正常か: Level2 操作後も数値表示が空欄化しない
- Audit Log 参照
	- 何を見れば正常か: Level2 操作後も一覧表示が読める状態を維持する
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

## Level3 解放直後の観測項目

- Freeze 実行結果
	- 何を見れば正常か: 確認チェック後の実行で freezeStatus が `frozen` に反映される
- Unfreeze 実行結果
	- 何を見れば正常か: 確認チェック後の実行で freezeStatus が `active` に反映される
- 警告表示の開閉
	- 何を見れば正常か: Freeze/Unfreeze の警告モーダルが開閉でき、閉じた後も表示が崩れない
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

### Level1 / Level2 解放機能の巻き込み崩れ確認（Level3直後）

- 一覧表示
	- 何を見れば正常か: Freeze/Unfreeze 後も行欠落・表示崩れがない
- 詳細表示
	- 何を見れば正常か: Freeze/Unfreeze 後も選択対象と詳細が一致する
- Dashboard
	- 何を見れば正常か: Freeze/Unfreeze 後も集計表示が空欄化せず一覧と整合する
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

### Level3 実行フェーズでの見る順序

- 確認チェック未投入での事前確認
	- 何を見れば正常か: confirmed 未チェックでは Freeze/Unfreeze が実行されない
- 確認チェック投入後の本実行
	- 何を見れば正常か: Freeze/Unfreeze の結果が一覧・詳細・管理パネルへ即時反映される
- 実行直後の表示確認
	- 何を見れば正常か: 警告表示、message、Audit Log が操作結果と矛盾なく更新される
- 再描画完了後の整合確認
	- 何を見れば正常か: 一覧・詳細・Dashboard・Audit Log の再描画後も状態不一致がない
- 既存解放機能の巻き込み確認
	- 何を見れば正常か: Level1 / Level2 で解放済みの参照・更新機能が Freeze/Unfreeze 後も崩れない

## Level3 解放後監視フェーズ 固定観測項目

- Freeze 実行結果
	- 何を見れば正常か: 実行後に freezeStatus が frozen へ更新され、そのまま維持される
- Unfreeze 実行結果
	- 何を見れば正常か: 実行後に freezeStatus が active へ更新され、そのまま維持される
- 警告表示の開閉
	- 何を見れば正常か: 警告表示が開閉でき、閉じた後も操作導線と画面表示が崩れない
- 確認チェック導線
	- 何を見れば正常か: confirmed 未チェックでは実行されず、チェック後だけ実行できる
- Audit Log 更新
	- 何を見れば正常か: Freeze / Unfreeze の action / target / result が欠落なく追記される
- message 表示内容
	- 何を見れば正常か: 成功 / 失敗 message が操作結果と一致し、誤表示がない
- 再描画整合
	- 何を見れば正常か: 一覧・詳細・Dashboard・Audit Log の再描画後に表示不整合がない
- 一覧/詳細/管理パネルの状態整合
	- 何を見れば正常か: 同一対象の freezeStatus が3画面で一致する
- Level1 / Level2 解放機能が巻き込まれて崩れていないか
	- 何を見れば正常か: 一覧表示・詳細表示・Dashboard・Audit Log 参照・Settings 参照・Settings 保存・Connect・Disconnect が Freeze / Unfreeze 後も崩れない

## Level4 解放直後の観測項目

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

### Level1 / Level2 / Level3 解放機能の巻き込み崩れ確認（Level4直後）

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

### Level1 監視対象外（維持）

- Settings 保存
- Connect
- Disconnect
- Freeze
- Unfreeze
- Export
- Delete

## 正常だった項目

- （監視結果を記録する）

## 異常兆候が出た項目

- （監視結果を記録する）

## 継続監視に回した項目

- （監視結果を記録する）

## 停止判断した項目

- （監視結果を記録する。停止なしの場合は「なし」と記録）

## 次回監視で見る項目

- （継続監視・停止判断の内容をもとに記録する）

---

## 小規模稼働 継続判定（初回・2026-03-23）

### 継続してよい機能

- 一覧表示: 参照系で安定観測しやすく、異常時の影響が限定的
- 詳細表示: 一覧連動の表示確認が中心で安全性が高い
- Dashboard: 集計整合が取りやすく、継続監視で品質担保しやすい
- Audit Log 参照: 参照専用で運用監視に必須

### 条件付き継続にする機能

- Settings 参照: API 連続エラーがないことを条件に継続
- Connect: connectionStatus 反映とログ追記が一致する場合のみ継続
- Disconnect: connectionStatus 復帰とログ追記が一致する場合のみ継続
- Settings 保存: 保存値保持と message 表示が一致する場合のみ継続
- Freeze: confirmed fail-safe 正常と状態反映一致を条件に継続
- Unfreeze: confirmed fail-safe 正常と状態復帰一致を条件に継続

### 停止候補にする機能

- Settings 保存: 保存後に値が戻る場合は停止候補
- Freeze: 状態未反映または confirmed すり抜け時は停止候補
- Unfreeze: 状態未反映または confirmed すり抜け時は停止候補
- Connect: 実行後の状態未反映が継続する場合は停止候補
- Disconnect: 実行後の状態未反映が継続する場合は停止候補

### 別枠（継続対象外）

- Export: 保留継続（LockGuard 本番相当検証完了まで）
- Delete: 保留継続（LockGuard 本番相当検証完了まで）

---

## Level4 解放後監視フェーズ 固定観測項目

- Export 実行結果
	- 何を見れば正常か: 認証・確認通過時のみ実行され、成功時のみ反映される
- Delete 実行結果
	- 何を見れば正常か: 認証・確認通過時のみ実行され、成功時のみ対象状態が更新される
- LockGuard の開閉
	- 何を見れば正常か: Export/Delete で開閉でき、閉じた後も操作導線と画面表示が崩れない
- confirmed チェック導線
	- 何を見れば正常か: confirmed 未チェックでは実行されず、チェック後のみ実行される
- password / twoFactorCode / confirmationText 入力導線
	- 何を見れば正常か: いずれか不足時は実行中断し、状態変更が発生しない
- Audit Log 更新
	- 何を見れば正常か: Export/Delete の action/target/result が欠落なく追記される
- message 表示内容
	- 何を見れば正常か: 成功/失敗/認証失敗の表示が操作結果と一致する
- 再描画整合
	- 何を見れば正常か: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する
- 一覧/詳細/管理パネルの状態整合
	- 何を見れば正常か: 同一対象の状態が3画面で一致し不整合が残らない
- Level1 / Level2 / Level3 解放機能が巻き込まれて崩れていないか
	- 何を見れば正常か: 一覧表示・詳細表示・Dashboard・Audit Log 参照・Settings 参照・Settings 保存・Connect・Disconnect・Freeze・Unfreeze が Export/Delete 後も崩れない

---

## 最終運用判定フェーズ 本運用後の重点監視項目（固定）

- 一覧/詳細表示整合: 同一対象の状態が一覧・詳細で一致し、操作後も不整合が残らない
- Dashboard 更新: 各操作後に件数・状態表示が即時反映され、古い状態が残らない
- Audit Log 更新: 全操作で action / target / result が欠落なく追記される
- Settings 保存結果: 保存後に反映され、空欄化・巻き戻りが発生しない
- Connect / Disconnect 結果: 実行後に3画面の状態が整合し、message が結果と一致する
- Freeze / Unfreeze 結果: confirmed 通過後のみ実行され、status が正しく更新・整合する
- Export 結果: LockGuard・confirmed・認証通過後のみ実行され、Audit Log に追記される
- Delete 結果: Export と同条件 + 削除後に一覧・詳細・管理パネルが整合する
- LockGuard / 認証導線: confirmed 未チェック・認証不足で実行が通らず、LockGuard が実行後に正常閉鎖する
- message 表示内容: 成功・失敗・認証失敗の表示が操作結果と常に一致する
- 再描画整合: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合し、空白化・崩れが出ない

---

## 最終運用開始フェーズ 本運用開始直後の重点監視項目（固定）

- 一覧/詳細表示整合: 開始直後の操作後も一覧・詳細の同一対象状態が一致する
- Dashboard 更新: 開始直後の各操作反映で件数・状態が即時更新される
- Audit Log 更新: 開始直後の全操作で action / target / result が欠落なく追記される
- Settings 保存結果: 開始直後の保存が反映され、空欄化・巻き戻りが発生しない
- Connect / Disconnect 結果: 開始直後の接続切替後に状態表示と実結果が一致する
- Freeze / Unfreeze 結果: 開始直後も confirmed 通過時のみ実行され、状態整合が維持される
- Export / Delete 結果: 開始直後も実行条件充足時のみ通過し、結果が画面と Audit Log に一致する
- LockGuard / 認証導線: 開始直後も confirmed 未チェック・認証不足で実行が通らず、LockGuard が正常閉鎖する
- message 表示内容: 開始直後の成功/失敗/認証失敗表示が操作結果と一致する
- 再描画整合: 開始直後の操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する

---

## 最終運用初回監視フェーズ 継続観測項目（固定）

- 一覧/詳細表示整合: 同一対象の状態が一覧・詳細で一致し、操作後も不整合が残らない
- Dashboard 更新: 各操作後に件数・状態表示が即時反映され、古い表示が残らない
- Audit Log 更新: 全操作で action / target / result が欠落なく追記される
- Settings 参照/保存: 参照可能で、保存後に反映され巻き戻りが発生しない
- Connect / Disconnect: 実行結果と状態表示が一致し、表示不整合が残らない
- Freeze / Unfreeze: confirmed 通過時のみ実行され、状態更新と表示整合が一致する
- Export / Delete: 実行条件充足時のみ通過し、結果が画面と Audit Log に一致する
- LockGuard / 認証導線: confirmed 未チェック・認証不足で実行が通らず、処理後に LockGuard が正常閉鎖する
- message 表示内容: 成功/失敗/認証失敗の表示が操作結果と一致する
- 再描画整合: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する

---

## 安定運用移行フェーズ 定常監視項目（固定）

- 一覧/詳細表示整合: 定常監視で何を見れば正常か: 同一対象の状態が一覧・詳細で一致し不整合が残らない
- Dashboard 更新: 定常監視で何を見れば正常か: 操作後に件数・状態サマリが即時反映される
- Audit Log 更新: 定常監視で何を見れば正常か: action / target / result が欠落なく追記される
- Settings 保存結果: 定常監視で何を見れば正常か: 保存後に反映され再表示でも値が保持される
- Connect / Disconnect 結果: 定常監視で何を見れば正常か: 実行結果と状態表示が一致し再実行不能がない
- Freeze / Unfreeze 結果: 定常監視で何を見れば正常か: confirmed 通過時のみ実行されstatus 整合が維持される
- Export / Delete 結果: 定常監視で何を見れば正常か: 認証・LockGuard 条件下のみ実行され結果整合が維持される
- LockGuard / 認証導線: 定常監視で何を見れば正常か: 未チェック・認証不足で実行が通らず処理後に正常閉鎖する
- message 表示内容: 定常監視で何を見れば正常か: 成功/失敗/認証失敗の表示が操作結果と一致する
- 再描画整合: 定常監視で何を見れば正常か: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する

---

## 安定運用定着フェーズ 定常監視ルール（固定）

- 毎回見る（条件付き運用機能の実行ごと）
  - Freeze / Unfreeze: confirmed 通過・status 整合・Audit Log 欠落なし
  - Export / Delete: 認証不足通過なし・LockGuard 正常閉鎖・Audit Log・3画面整合
  - LockGuard / 認証導線: 未チェック・認証不足通過なし、処理後残留なし
  - message 表示内容: 操作結果と一致、前回残留・逆転表示なし
  - Audit Log 更新: action / target / result 欠落なく追記
- 変更時に見る（参照系・低リスク更新系の操作ごと）
  - 一覧/詳細表示整合: 同一対象の status が3画面で一致し続ける
  - Dashboard 更新: 操作後に件数・状態サマリが即時反映される
  - Settings 保存結果: 保存後の値が保持され再表示でも一致する
  - Connect / Disconnect 結果: status 変更が反映され残留・不整合がない
  - 再描画整合: 操作後に一覧・詳細・Dashboard・Audit Log が同時整合する
- 異常時に見る（停止条件に抵触した疑いが生じたとき）
  - 全項目を対象に再確認し「全面停止」「機能保留へ戻す」「継続監視」の3段階で判定する
