# 全API通し確認結果

## Level別 重点監視項目（段階解放）

### Level1: 参照系

- 一覧/詳細表示整合
  - 重点監視: 一覧選択と詳細表示の対象不一致がない
- Dashboard 更新
  - 重点監視: 一覧データに対して集計値が一致する
- Audit Log 更新
  - 重点監視: 参照後のログ表示が最新化される
- message 表示
  - 重点監視: 取得失敗時に原因が分かる message を表示する

### Level1 一覧/詳細 安定監視ポイント

- 一覧が継続して表示されるか
  - 正常: 再読込・画面遷移後も一覧の行/列が維持される
  - 異常兆候: 一覧が空白化する、行欠落が継続する
- 一覧と詳細の選択整合が取れているか
  - 正常: 一覧の選択対象と詳細表示の対象IDが一致する
  - 異常兆候: 一覧選択と異なる詳細が表示される
- 詳細ボタン押下後に表示が崩れないか
  - 正常: 詳細パネルのレイアウト・項目表示が崩れない
  - 異常兆候: 項目欠落、レイアウト崩れ、表示フリーズ
- 詳細取得失敗時にプレースホルダーへ戻れるか
  - 正常: 失敗時はプレースホルダー表示へ戻り、再取得で通常表示へ復帰する
  - 異常兆候: 失敗後に空白表示のまま復帰しない
- message 表示が過不足ないか
  - 正常: 成功/失敗ごとに1件ずつ適切なmessageが表示される
  - 異常兆候: 無表示、重複表示、結果不一致のmessage表示

### Settings 保存 安定監視ポイント

- 保存後に値が反映されたまま維持されるか
  - 正常: 保存成功後、再読込しても設定値が元のまま保持される
  - 異常兆候: 保存直後は反映されるが、再読込で値が古い値に戻る
- 保存後に message が適切に出るか
  - 正常: 保存成功時に成功 message, 失敗時に失敗 message が表示される
  - 異常兆候: message が出ない、失敗時も成功 message が表示される
- Audit Log が更新されるか
  - 正常: Settings 保存後に Audit Log に操作記録が追記される
  - 異常兆候: 保存後も Audit Log に記録が追加されない
- 画面再描画後に値が戻らないか
  - 正常: 保存後の各種再描画・画面遷移後も値が保持される
  - 異常兆候: 画面遷移や再描画後に保存前の値に初期化される
- Settings 参照表示が崩れないか
  - 正常: 保存後に Settings 参照画面が正常表示される
  - 異常兆候: 保存後に参照値が空欄化、初期値固定、崩れ表示になる

### Level2: 低リスク更新系

- Connect / Disconnect 結果
  - 重点監視: 状態遷移が一覧・詳細・接続管理で一致する
- 一覧/詳細表示整合
  - 重点監視: 更新後に古い表示が残らない
- Audit Log 更新
  - 重点監視: 接続操作ログが順序どおり追加される
- message 表示
  - 重点監視: 成功/失敗が即時に切り替わる

### Level3: 条件付き更新系

- Settings 保存結果
  - 重点監視: 保存成功後の値保持、保存失敗時の値不変
- Freeze / Unfreeze 結果
  - 重点監視: freezeStatus が一覧・詳細・Dashboard で一致する
- Dashboard 更新
  - 重点監視: 凍結/解除の反映で集計値が追従する
- Audit Log 更新
  - 重点監視: settings/freeze/unfreeze の記録欠落がない
- message 表示
  - 重点監視: 保存・凍結系の結果文言が一致する

### Freeze / Unfreeze 安定監視ポイント

- Freeze 後に freezeStatus が維持されるか
  - 正常: Freeze 実行後、freezeStatus が frozen のまま一覧・詳細・管理パネルで維持される
  - 異常兆候: 一度 frozen になっても再描画や再取得後に active へ戻る
- Unfreeze 後に freezeStatus が戻るか
  - 正常: Unfreeze 実行後、freezeStatus が active に戻り一覧・詳細・管理パネルで一致する
  - 異常兆候: active に戻らない、または一部画面だけ frozen のまま残る
- message が適切に出るか
  - 正常: 成功時は成功 message、失敗時は失敗 message が結果どおり表示される
  - 異常兆候: message が出ない、重複する、成功/失敗が逆転して表示される
- Audit Log が更新されるか
  - 正常: Freeze / Unfreeze の action / target / result が操作直後に追記される
  - 異常兆候: 記録が追加されない、内容が実行操作と一致しない
- 一覧/詳細/管理パネルで表示が揃うか
  - 正常: 同一対象の freezeStatus が3画面で同じ状態を示す
  - 異常兆候: 一覧・詳細・管理パネルのいずれかで状態表示が食い違う
- 参照系が巻き込まれて崩れないか
  - 正常: 一覧表示・詳細表示・Dashboard・Audit Log 参照が Freeze / Unfreeze 後も崩れない
  - 異常兆候: 行欠落、詳細不一致、Dashboard 空欄化、Audit Log 一覧崩れが発生する

### Level4: 危険操作系（厳しめ）

- LockGuard 導線
  - 重点監視: confirmed 未チェック・認証不足時は必ず中断する
- Export / Delete 結果
  - 重点監視: 成功時のみ反映、失敗時は状態不変を維持する
- Audit Log 更新
  - 重点監視: export/delete の成功/失敗が必ず追記される
- 一覧/詳細表示整合
  - 重点監視: delete 反映後の一覧・詳細に不整合がない
- message 表示
  - 重点監視: 認証失敗/実行失敗/成功を誤認なく表示する

## 通し確認日

- 実施日:
- 実施者:
- 対象環境:
- 対象ブランチ/コミット:

## 実施したシナリオ

- [ ] 一覧表示 → 詳細表示 → Connect → Disconnect
- [ ] Freeze → Unfreeze
- [ ] Settings 読み込み → Settings 保存
- [ ] Audit Log 確認（一覧/フィルタ/件数）
- [ ] Export（LockGuard）
- [ ] Delete（LockGuard）

## 成功した項目

- [ ] 一覧表示
- [ ] 詳細表示
- [ ] Connect
- [ ] Disconnect
- [ ] Freeze
- [ ] Unfreeze
- [ ] Settings 読み込み
- [ ] Settings 保存
- [ ] Audit Log 確認
- [ ] Export
- [ ] Delete

## 失敗した項目

- [ ] 一覧表示
- [ ] 詳細表示
- [ ] Connect
- [ ] Disconnect
- [ ] Freeze
- [ ] Unfreeze
- [ ] Settings 読み込み
- [ ] Settings 保存
- [ ] Audit Log 確認
- [ ] Export
- [ ] Delete
- 失敗内容メモ:

## 未確認項目

- [ ] 一覧表示
- [ ] 詳細表示
- [ ] Connect
- [ ] Disconnect
- [ ] Freeze
- [ ] Unfreeze
- [ ] Settings 読み込み
- [ ] Settings 保存
- [ ] Audit Log 確認
- [ ] Export
- [ ] Delete
- 未確認理由メモ:

## 発見した課題

- [ ] なし
- [ ] あり
- 課題一覧:
  - 課題1:
  - 課題2:
  - 課題3:

## 稼働開始前に残る確認事項

- [ ] 危険操作 fail-safe（confirmed 未チェック/認証不足）確認完了
- [ ] API 失敗時の UI 安定性確認完了
- [ ] 再描画整合（一覧/詳細/Dashboard/Audit Log）確認完了
- [ ] `docs/gui_final_checklist.md` の未完了項目を解消
- 補足メモ:

## 異常系確認（一覧取得/詳細取得）

### 一覧取得失敗

- [ ] 一覧取得失敗時に message が表示される
- [ ] 一覧取得失敗時に既存一覧表示が維持される
- [ ] 一覧取得失敗時に画面全体が崩れない

### 詳細取得失敗

- [ ] 詳細取得失敗時に message が表示される
- [ ] 詳細取得失敗時に詳細パネルがプレースホルダーへ復帰する
- [ ] 詳細取得失敗時に他パネル（一覧・接続管理）が崩れない

### プレースホルダー復帰

- [ ] 詳細取得失敗後、Dashboard 側詳細が未選択表示へ戻る
- [ ] 詳細取得失敗後、Block管理側詳細が未選択表示へ戻る
- [ ] 再度詳細取得成功時に通常表示へ戻る

### 既存表示維持

- [ ] 一覧取得失敗後も直前の一覧が維持される
- [ ] 一覧取得失敗後も Export/Delete テーブルの既存表示が維持される
- [ ] 一覧取得失敗後も接続管理パネルの既存表示が維持される

### UI が崩れないか

- [ ] レイアウト崩れ（表ヘッダずれ・ボタン消失）が発生しない
- [ ] 連続失敗時も操作不能状態にならない
- [ ] Console に未処理例外が残らない

---

## 監視付き稼働 対象機能（2026-03-23）

> 下記機能は稼働開始後も継続的に監視を行い、停止判断条件を満たした場合は即時保留に戻す。

### Connect / Disconnect

- 監視項目
  - connectionStatus が想定どおり connected / disconnected へ遷移するか
  - 操作後に一覧・詳細・接続管理パネルの表示が一致しているか
  - Audit Log に操作記録が追記されるか
- 開始直後に見るべき挙動
  - Connect 実行 → connectionStatus = `connected` かつ一覧に反映
  - Disconnect 実行 → connectionStatus = `disconnected` かつ一覧に反映
  - 失敗時に message のみ表示、状態変化なし
- 停止判断条件
  - 成功/失敗にかかわらず UI 表示が一覧と乖離する
  - 操作後に Audit Log が更新されない
  - Console に未処理例外が発生する

### Audit Log 更新

- 監視項目
  - Connect / Disconnect / Freeze / Unfreeze 等の操作後に自動で追記されるか
  - 失敗時にも失敗記録が残るか
  - 連続操作時にログの順序が逆転しないか
- 開始直後に見るべき挙動
  - 操作直後にログ行が追加され、action / target / result が正しい
  - 手動更新なしで最新化される
- 停止判断条件
  - 操作後にログが更新されない
  - 記録内容（action / target / result）が操作と一致しない
  - ログ表示がフリーズする

### Settings 保存（本API接続後・監視前提で解放）

- 監視項目
  - PATCH /settings のリクエストが正しく発行されるか
  - 保存後にリロードしても値が保持されるか
  - 保存失敗時に message が表示され設定値が変化しないか
- 開始直後に見るべき挙動
  - 保存 → ネットワークタブで PATCH /settings が発行される
  - 保存成功 → 成功 message 表示・フォーム値はそのまま残る
  - 保存失敗 → 失敗 message のみ・設定値は変化しない
- 停止判断条件
  - 保存操作が実際には反映されない（リロード後に元の値に戻る）
  - API 失敗時に設定値が書き換わる
  - Console に未処理例外が発生する

### Freeze / Unfreeze（本API接続後・監視前提で解放）

- 監視項目
  - freezeStatus が想定どおり frozen / active へ遷移するか
  - 操作後に一覧・詳細・Dashboard・Audit Log が整合するか
  - confirmed 未チェック時に実行されないか
- 開始直後に見るべき挙動
  - Freeze 実行 → freezeStatus = `frozen` が一覧・詳細・Dashboard すべてに反映
  - Unfreeze 実行 → freezeStatus = `active` に戻り各パネルが一致
  - fail-safe: confirmed なしで呼び出しが起きない
- 停止判断条件
  - freezeStatus の遷移が UI に反映されない
  - confirmed なしで API 呼び出しが通る
  - 操作後に Dashboard / Audit Log が更新されない

### Export / Delete（解放保留）

- 現時点では監視付き稼働の対象外。以下の条件をすべて満たすまで解放しない
  - 本API（POST /blocks/:blockId/export, DELETE /blocks/:blockId）に差し替え済み
  - LockGuard 全フィールド検証が本API で通ることを確認済み
  - 正常系・異常系・fail-safe を本API で確認済み
  - 取り消し不能の UI 明示を確認済み

---

## 条件付き稼働機能 監視チェック欄（2026-03-23）

### Settings 保存

- [ ] 監視したい項目: PATCH /settings 発行、保存値の永続、失敗時 state 不変
- [ ] 開始直後に見るべき挙動: 保存成功 message 表示、再読込後も値が一致
- [ ] 問題があった場合の停止判断: 保存値不一致/失敗時値書き換え/未処理例外で停止

### Freeze

- [ ] 監視したい項目: freezeStatus 遷移、一覧/詳細/Dashboard/Audit Log 整合、confirmed fail-safe
- [ ] 開始直後に見るべき挙動: freezeStatus が frozen へ反映、Audit Log 追記
- [ ] 問題があった場合の停止判断: 状態未反映/ログ未更新/confirmed 未チェック実行で停止

### Unfreeze

- [ ] 監視したい項目: freezeStatus 復帰、一覧/詳細/Dashboard/Audit Log 整合、confirmed fail-safe
- [ ] 開始直後に見るべき挙動: freezeStatus が active へ反映、Audit Log 追記
- [ ] 問題があった場合の停止判断: 状態未反映/ログ未更新/confirmed 未チェック実行で停止

### Audit Log 更新

- [ ] 監視したい項目: 自動追記、action/target/result 内容整合、順序整合
- [ ] 開始直後に見るべき挙動: 手動更新なしでログ行追加、直近操作内容と一致
- [ ] 問題があった場合の停止判断: 追記なし/内容不一致/順序逆転継続で停止

### 保留扱い

- [ ] Export / Delete は原則保留（解放条件完了まで監視付き開始の対象外）

---

## 稼働拡大時 重点監視項目（2026-03-23）

### 再描画整合
- 拡大直後に見るべきこと: 操作後に一覧・詳細・Dashboard・Audit Log が同じ状態を示す

### message 表示
- 拡大直後に見るべきこと: 成功/失敗/入力エラーの message が操作結果と一致して出る

### Audit Log 更新
- 拡大直後に見るべきこと: 主要操作ごとに action/target/result が欠落なく追記される

### Settings 保存結果
- 拡大直後に見るべきこと: 保存後に再読込しても値が保持され、失敗時は値が変化しない

### Connect / Disconnect 結果
- 拡大直後に見るべきこと: connectionStatus の遷移が一覧・詳細・ログで一致する

### Freeze / Unfreeze 結果
- 拡大直後に見るべきこと: freezeStatus の遷移が一覧・詳細・Dashboard・ログで一致し、confirmed fail-safe が効く

### 危険操作導線の誤作動有無
- 拡大直後に見るべきこと: 未解放時に Export / Delete 導線が誤って実行可能になっていない

---

## Level4 解放後 Export / Delete 安定監視ポイント（固定）

### Export 後に状態が想定どおり変わるか

- 正常: Export 成功時のみ対象状態が更新され、失敗時は状態不変
- 異常兆候: 失敗時に状態が変化する、成功時でも状態が更新されない

### Delete 後に状態が想定どおり変わるか

- 正常: Delete 成功時のみ対象状態が更新され、失敗時は状態不変
- 異常兆候: 失敗時に状態が変化する、成功時でも状態が更新されない

### message が適切に出るか

- 正常: 成功/失敗/認証失敗の message が操作結果と一致する
- 異常兆候: message が出ない、成功失敗が逆転表示される、前回 message が残る

### Audit Log が更新されるか

- 正常: Export / Delete の action / target / result が欠落なく追記される
- 異常兆候: ログ未追記、内容不一致、順序逆転が発生する

### 一覧/詳細/管理パネルで表示が揃うか

- 正常: 同一対象の状態が一覧・詳細・管理パネルで一致する
- 異常兆候: 3画面で状態が食い違う、再操作後も不整合が残る

### Level1 / Level2 / Level3 解放機能が巻き込まれて崩れないか

- 正常: 一覧表示・詳細表示・Dashboard・Audit Log 参照・Settings 参照・Settings 保存・Connect・Disconnect・Freeze・Unfreeze が Export / Delete 後も崩れない
- 異常兆候: 既存解放機能の表示崩れ、状態不整合、操作不能が発生する

---

## 最終運用初回監視フェーズ 参照系・低リスク更新系 初回監視ポイント（固定）

### 一覧表示
- 正常: 一覧の件数・状態が最新で、操作後も表示崩れがない
- 異常兆候: 件数不一致、古い状態残留、表示崩れが発生する

### 詳細表示
- 正常: 一覧で選択した対象と詳細の状態が一致する
- 異常兆候: 一覧と詳細で状態が食い違う、詳細が空欄化する

### Dashboard
- 正常: 各操作後に件数・状態サマリが即時反映される
- 異常兆候: 反映遅延、件数不一致、古いサマリ表示が残る

### Audit Log 参照
- 正常: 直近操作の action / target / result が欠落なく読める
- 異常兆候: 未追記、内容不一致、順序逆転が発生する

### Settings 参照
- 正常: 参照項目が欠落なく表示される
- 異常兆候: 項目欠落、空欄化、読み込み失敗が発生する

### Settings 保存
- 正常: 保存後に値が反映され、再表示でも保持される
- 異常兆候: 保存失敗、巻き戻り、再表示で値が消える

### Connect
- 正常: 実行後に接続状態が更新され、message と状態表示が一致する
- 異常兆候: 状態未更新、逆転表示、再実行不能が発生する

### Disconnect
- 正常: 実行後に切断状態が更新され、message と状態表示が一致する
- 異常兆候: 状態未更新、逆転表示、再実行不能が発生する

### 一覧/詳細/管理パネルの状態整合
- 正常: 同一対象の状態が一覧・詳細・管理パネルで一致する
- 異常兆候: 3画面で状態が食い違う、再描画後も不整合が残る
