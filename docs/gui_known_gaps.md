# GUI 既知ギャップ

## mock 実装のままの箇所
- [ ] 一覧データ取得が固定JSON
- [ ] 詳細データ取得がローカルスタブ
- [ ] 更新処理が疑似成功レスポンス

## 本API未接続箇所
- [ ] 一覧検索API未接続（クエリ連携なし）
- [ ] 詳細取得API未接続（ID連携なし）
- [ ] 更新API未接続（PATCH/PUT未呼び出し）
- [ ] 削除API未接続（DELETE未呼び出し）

## 認証の簡易実装箇所
- [ ] ログイン状態をローカル変数のみで管理
- [ ] トークン期限切れ処理が未実装
- [ ] 権限別表示制御が固定値

## 後で強化したい UI
- [ ] ローディング表示の統一
- [ ] エラー表示の文言・導線の統一
- [ ] キーボード操作/フォーカス制御の改善
- [ ] モバイル表示の余白・密度最適化

## テスト未実施観点
- [ ] 主要操作のE2E（作成/更新/削除）
- [ ] API失敗時のリトライ・復帰動作
- [ ] 境界値入力（最大文字数・空文字・記号）
- [ ] 多件数データ時の表示性能
- [ ] ブラウザ差分（Chrome/Firefox/Safari）

## 本API接続前の棚卸し（差し替え対象）

### mock のままの箇所（現時点）
- [ ] block 一覧取得: mockレスポンス利用
- [ ] block 詳細取得: ローカルスタブ利用
- [ ] connect / disconnect: mock service の戻り値を利用
- [ ] freeze / unfreeze: mock service の戻り値を利用
- [ ] export / delete: 疑似成功レスポンスを利用
- [ ] audit log 取得: ローカル配列更新を利用
- [ ] settings 取得 / 更新: ローカル状態のみ更新
- [ ] handshake 状態取得 / 更新: ローカルフラグのみ更新

### 本APIに置換予定の箇所
- [ ] block 一覧取得: GET /blocks へ差し替え
- [ ] block 詳細取得: GET /blocks/:blockId へ差し替え
- [ ] connect / disconnect: POST /blocks/:blockId/connect, POST /blocks/:blockId/disconnect へ差し替え
- [ ] freeze / unfreeze: POST /blocks/:blockId/freeze, POST /blocks/:blockId/unfreeze へ差し替え
- [ ] export / delete: POST /blocks/:blockId/export, DELETE /blocks/:blockId へ差し替え
- [ ] audit log 取得: GET /audit-logs へ差し替え
- [ ] settings 取得 / 更新: GET /settings, PATCH /settings へ差し替え
- [ ] handshake 状態取得 / 更新: GET /handshake, PATCH /handshake へ差し替え

---

## 稼働開始判定 機能区分（2026-03-23）

### 先行稼働
- 一覧表示: 読み取り専用、状態変更なし
- 詳細表示: 読み取り専用、状態変更なし
- Dashboard: 読み取り専用、集計表示のみ
- Audit Log 参照: 読み取り専用、ログ参照のみ

### 条件付き稼働
- Settings 参照: mockデータ表示のため「表示確認専用」と明示した上で稼働可
- Connect: 可逆操作。確認フロー動作確認済みかつ監視付きで稼働可
- Disconnect: 同上

### 保留
- Settings 保存: PATCH /settings 未接続。変更が実際には反映されず誤認を招く
- Freeze: 本API未接続。mock成功を実成功と誤認するリスクあり
- Unfreeze: 同上
- Export: 本API未接続かつLockGuard認証未検証。取り消し不能操作のため本API接続まで厳禁
- Delete: 同上。取り消し不能操作のため本API接続・認証検証完了まで厳禁

---

## 監視付き稼働 機能一覧（2026-03-23）

> 条件付き稼働機能は稼働開始後も下記観点で継続監視し、異常があれば即時保留に戻す。

- Connect / Disconnect
  - 監視: connectionStatus の遷移・一覧整合・Audit Log 更新
  - 開始直後に見る挙動: Connect → `connected` 反映、Disconnect → `disconnected` 反映、失敗時は message のみ
  - 停止判断条件: 表示と状態が乖離する / ログが更新されない / 未処理例外が出る
- Audit Log 更新
  - 監視: 各操作後の自動追記・記録内容の正確性・順序逆転なし
  - 開始直後に見る挙動: 操作直後にログ行が追加され action / target / result が正しい
  - 停止判断条件: 操作後に追記されない / 記録内容が操作と不一致
- Settings 保存（本API接続後に解放）
  - 監視: PATCH /settings 発行・保存値の永続確認・失敗時の state 不変
  - 開始直後に見る挙動: 保存 → ネットワークタブで PATCH 発行 → リロード後も値が保持
  - 停止判断条件: リロード後に設定値が戻る / 失敗時に値が書き換わる
- Freeze / Unfreeze（本API接続後に解放）
  - 監視: freezeStatus の遷移・Dashboard/Audit Log 整合・confirmed fail-safe
  - 開始直後に見る挙動: Freeze → `frozen` が一覧/詳細/Dashboard すべてに反映、confirmed なしで呼び出しが起きない
  - 停止判断条件: freezeStatus が UI に反映されない / confirmed なしで API 呼び出しが通る
- Export / Delete: 解放保留。本API接続・LockGuard 検証・全確認完了まで監視対象外

---

## 保留機能と解放条件（小規模稼働 2026-03-23）

### 保留機能

- Export: 取り消し不能操作のため、解放条件未達の間は保留継続
- Delete: 取り消し不能操作のため、解放条件未達の間は保留継続

### Export 解放条件

- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 認証 fail-safe確認済み（confirmed 未チェック/認証不足で停止）
- [ ] LockGuard確認済み（全フィールド検証）
- [ ] 監査ログ更新確認済み
- [ ] 通し確認済み（一覧→詳細→Export 含む通しシナリオ）
- 未達なら保留継続

### Delete 解放条件

- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 認証 fail-safe確認済み（confirmed 未チェック/認証不足で停止）
- [ ] LockGuard確認済み（全フィールド検証）
- [ ] 監査ログ更新確認済み
- [ ] 通し確認済み（一覧→詳細→Delete 含む通しシナリオ）
- 未達なら保留継続

---

## 条件付き稼働機能 停止判断（2026-03-23）

| 機能 | 続行条件 | 停止判断条件 | 停止後に確認すること |
|---|---|---|---|
| Settings 保存 | 保存後に値が反映・Audit Log 記録あり | 値未反映・ログ未記録・message なし | API レスポンス・エラーログ・再描画タイミング |
| Freeze | freezeStatus が frozen に変わり各所に反映 | 状態未反映・ログ未記録・confirmed すり抜け | confirmed ガード・API レスポンス・freezeStatus 遷移 |
| Unfreeze | freezeStatus が active に戻り各所に反映 | 状態未反映・ログ未記録・confirmed すり抜け | confirmed ガード・API レスポンス・freezeStatus 遷移 |
| Audit Log 更新 | 各操作後に自動追記・内容正常 | 追記なし・内容空・順序逆転が継続 | API 呼び出しタイミング・レスポンス・レンダリング |
| Export / Delete | 保留前提のため該当なし | 保留中に実行可能になっていた場合は即時停止 | confirmed ガード・LockGuard 認証動作 |

---

## 停止/保留対象の再開条件（2026-03-23）

### Export
- 現在止めている理由: 取り消し不能操作で、LockGuard と fail-safe の本番相当確認が未完了
- 再開条件: LockGuard 全項目検証完了、confirmed fail-safe 完了、異常系確認完了、通し確認完了
- 再開前に再確認する項目: 認証失敗時の中断、message 文言整合、Audit Log 追記、一覧/詳細再描画整合

### Delete
- 現在止めている理由: 取り消し不能操作で、誤削除防止の検証が未完了
- 再開条件: LockGuard 全項目検証完了、confirmed fail-safe 完了、異常系確認完了、通し確認完了
- 再開前に再確認する項目: 認証不足時の停止、削除失敗時の状態不変、Audit Log 記録、一覧からの除去反映

### Freeze / Unfreeze（一時停止ケース）
- 現在止めている理由: 状態未反映・confirmed すり抜け・ログ未記録が発生した場合は一時停止
- 再開条件: freezeStatus 遷移の安定確認、confirmed fail-safe 再確認、異常系確認再実施、通し確認完了
- 再開前に再確認する項目: 一覧/詳細/Dashboard の整合、操作後 message、Audit Log 順序と内容一致

---

## Level1 停止候補/不安定候補の再開条件（2026-03-24）

### 一覧表示
- 現在止めている理由: 一覧消失または行欠落が再発し安定表示できない
- 再開条件: 再読込・再取得後も一覧表示が継続し空白化しない
- 再開前に再確認する項目:
  - [ ] 一覧の行/列表示が崩れない
  - [ ] 空白化が再発しない
  - [ ] message 表示が過不足なく出る

### 詳細表示
- 現在止めている理由: 詳細未表示または一覧選択との対象不整合が発生
- 再開条件: 一覧選択と詳細表示の整合が連続して確認できる
- 再開前に再確認する項目:
  - [ ] 詳細ボタン押下後に崩れない
  - [ ] 対象不整合が再発しない
  - [ ] 失敗時にプレースホルダーへ戻れる

### Dashboard
- 現在止めている理由: 数値空欄化または一覧との乖離が継続
- 再開条件: 一覧件数・状態内訳との一致が監視サイクルで維持される
- 再開前に再確認する項目:
  - [ ] 数値空欄化が再発しない
  - [ ] 集計乖離が再発しない
  - [ ] 再読込後も表示が維持される

### Audit Log 参照
- 現在止めている理由: 一覧崩れや順序崩れでログ読取が困難
- 再開条件: ログ一覧の表示整形と順序整合が連続して維持される
- 再開前に再確認する項目:
  - [ ] 行/列崩れがない
  - [ ] 欠落なく一覧表示できる
  - [ ] 順序崩れが再発しない

### Settings 参照
- 現在止めている理由: 参照値空欄化または初期値固定が発生
- 再開条件: 参照値が安定表示され、再取得後も空欄化しない
- 再開前に再確認する項目:
  - [ ] 空欄化が再発しない
  - [ ] 初期値固定にならない
  - [ ] 参照結果に応じたmessageが表示される

---

## Level2 停止候補/不安定候補の再開条件（2026-03-24）

### Settings 保存
- 現在止めている理由: 保存成功後の値巻き戻り、または保存結果と表示不整合が発生
- 再開条件: 保存後の値保持、message整合、Audit Log追記が連続確認できる
- 再開前に再確認する項目:
  - [ ] 保存直後と再読込後で値が一致する
  - [ ] 成功/失敗messageが操作結果と一致する
  - [ ] 保存操作のAudit Logが欠落なく追記される

### Connect
- 現在止めている理由: 接続操作後に状態遷移が未反映、または画面間で状態不一致が継続
- 再開条件: Connect後の状態が一覧/詳細/管理パネルで一致し、再操作でも崩れない
- 再開前に再確認する項目:
  - [ ] Connect後にconnectionStatusが3画面で一致する
  - [ ] 接続操作のmessageが正しく表示される
  - [ ] Connect操作のAudit Log追記が確認できる

### Disconnect
- 現在止めている理由: 切断操作後に状態遷移が未反映、または画面間で状態不一致が継続
- 再開条件: Disconnect後の状態が一覧/詳細/管理パネルで一致し、再操作でも崩れない
- 再開前に再確認する項目:
  - [ ] Disconnect後にconnectionStatusが3画面で一致する
  - [ ] 切断操作のmessageが正しく表示される
  - [ ] Disconnect操作のAudit Log追記が確認できる

### 一覧表示（巻き込み確認）
- 現在止めている理由: Level2操作後に一覧消失・行欠落・表示崩れが発生
- 再開条件: Level2操作直後の再取得でも一覧表示が安定する
- 再開前に再確認する項目:
  - [ ] 行/列崩れがない
  - [ ] 空白化が再発しない
  - [ ] 操作後更新で表示欠落が出ない

### 詳細表示（巻き込み確認）
- 現在止めている理由: Level2操作後に詳細未表示または対象不整合が発生
- 再開条件: 一覧選択と詳細表示の対象一致が連続確認できる
- 再開前に再確認する項目:
  - [ ] 詳細パネルが安定表示される
  - [ ] 対象ID不一致が再発しない
  - [ ] 失敗時にプレースホルダー復帰できる

### Dashboard（巻き込み確認）
- 現在止めている理由: Level2操作後に数値空欄化または集計不整合が発生
- 再開条件: 一覧件数・状態内訳との一致が監視サイクルで維持される
- 再開前に再確認する項目:
  - [ ] 数値空欄化が再発しない
  - [ ] 集計乖離が再発しない
  - [ ] 再読込後も表示が維持される

### Audit Log 参照（巻き込み確認）
- 現在止めている理由: Level2操作後にログ欠落・順序崩れ・一覧崩れが発生
- 再開条件: 操作記録の追記と一覧表示整合が連続確認できる
- 再開前に再確認する項目:
  - [ ] 行/列崩れがない

### Settings 参照（巻き込み確認）
- 現在止めている理由: Level2操作後に参照値空欄化または初期値固定が発生
- 再開条件: 参照値が安定表示され、再取得後も空欄化しない
- 再開前に再確認する項目:
  - [ ] 空欄化が再発しない
  - [ ] 初期値固定にならない
  - [ ] 参照結果に応じたmessageが表示される

### Level2 再開条件の対象外（別枠）

- Freeze / Unfreeze: Level3 判定対象
- Export / Delete: Level4 判定対象

---

## Level3 停止候補/不安定候補の再開条件（2026-03-24）

### Freeze
- 現在止めている理由: confirmed すり抜け、freezeStatus 未反映、状態不整合、再描画崩れの再発
- 再開条件: confirmed 導線正常、freezeStatus が一覧/詳細/管理パネルで一致、Audit Log・message 整合を連続確認
- 再開前に再確認する項目:
  - [ ] confirmed 未チェックで実行されない
  - [ ] freezeStatus が frozen に遷移して維持される
  - [ ] Audit Log が欠落なく追記される
  - [ ] 成功/失敗 message が結果と一致する

### Unfreeze
- 現在止めている理由: confirmed すり抜け、freezeStatus 未復帰、状態不整合、再描画崩れの再発
- 再開条件: confirmed 導線正常、freezeStatus が active へ復帰、Audit Log・message 整合を連続確認
- 再開前に再確認する項目:
  - [ ] confirmed 未チェックで実行されない
  - [ ] freezeStatus が active に復帰して維持される
  - [ ] Audit Log が欠落なく追記される
  - [ ] 成功/失敗 message が結果と一致する

### 巻き込み確認（一覧表示/詳細表示/Dashboard/Audit Log 参照/Settings 参照/Settings 保存/Connect/Disconnect）
- 現在止めている理由: Freeze/Unfreeze 後に参照系またはLevel2更新系へ表示崩れ・状態不整合が波及
- 再開条件: Freeze/Unfreeze 実行後も各機能が安定表示を維持し、状態不整合が再発しない
- 再開前に再確認する項目:
  - [ ] 一覧表示・詳細表示・Dashboard が崩れない
  - [ ] Audit Log 参照が読める状態を維持する
  - [ ] Settings 参照/保存が空欄化・巻き戻りを起こさない
  - [ ] Connect/Disconnect の表示整合が維持される

### Level3 再開条件の対象外（別枠）

- Export / Delete: Level4 判定対象のため本節の再開条件対象外

---

## Level4 継続判定フェーズ 停止候補の再開条件（固定）

> Level4（Export / Delete）は最終危険操作段階。再開条件を全て満たすまで再開禁止。

### Export 再開条件

- 現在止めている理由: confirmed すり抜け / 認証不足通過 / Audit Log 欠落 / 状態不整合 / LockGuard 誤作動いずれかが発生
- 再開条件: 原因特定・修正完了 + テスト環境での連続確認で再発なし
- 再開前に再確認する項目
  - [ ] confirmed 未チェックで実行されない
  - [ ] password / twoFactorCode / confirmationText 不足で実行が中断される
  - [ ] Audit Log の action / target / result が欠落なく追記される
  - [ ] 実行後の3画面（一覧・詳細・管理パネル）が整合する
  - [ ] LockGuard が実行後に正常に閉じる

### Delete 再開条件

- 現在止めている理由: Export と同条件 + 削除後の3画面が一致しなかった
- 再開条件: Export の再開条件を満たした上で、削除後3画面整合を連続確認
- 再開前に再確認する項目
  - [ ] Export の再開前確認項目を全て満たしている
  - [ ] 削除後に一覧から対象が消える
  - [ ] 削除後に詳細が残留・不整合にならない
  - [ ] 削除後に Dashboard が反映される
  - [ ] 削除後の Audit Log に追記される

### 巻き込み確認対象の再開条件

- 現在止めている理由: Export / Delete 後に一覧/詳細/Dashboard/Audit Log/Settings/Connect/Disconnect/Freeze/Unfreeze のいずれかで崩れ
- 再開条件: 原因特定・修正完了 + Export / Delete 実行後も全機能の安定をテスト環境で連続確認
- 再開前に再確認する項目
  - [ ] 一覧表示・詳細表示・Dashboard が崩れない
  - [ ] Audit Log・Settings 参照/保存が崩れない
  - [ ] Connect / Disconnect / Freeze / Unfreeze が崩れない

---

## 本運用継続判定フェーズ 保留へ戻す候補の再開条件（固定）

### Settings 保存
- 現在保留へ戻す理由: 保存後の巻き戻り・空欄化・保存結果不一致
- 再開条件: 保存反映と再表示保持が連続一致し再発なし
- 再開前に再確認する項目
  - [ ] 保存後の値保持
  - [ ] message 一致
  - [ ] Audit Log 記録整合

### Freeze
- 現在保留へ戻す理由: confirmed すり抜け / status 不整合 / Audit Log 欠落
- 再開条件: confirmed 通過時のみ実行 + status / 監査記録の連続整合
- 再開前に再確認する項目
  - [ ] confirmed 未チェックで実行されない
  - [ ] status が3画面一致
  - [ ] Audit Log 欠落なし

### Unfreeze
- 現在保留へ戻す理由: confirmed すり抜け / status 復帰失敗 / Audit Log 欠落
- 再開条件: confirmed 通過時のみ実行 + 復帰状態 / 監査記録の連続整合
- 再開前に再確認する項目
  - [ ] confirmed 未チェックで実行されない
  - [ ] status 復帰が3画面一致
  - [ ] Audit Log 欠落なし

### Export
- 現在保留へ戻す理由: 認証不足通過 / LockGuard 誤作動 / 結果不一致 / Audit Log 欠落
- 再開条件: LockGuard / 認証 / fail-safe 正常 + 結果整合の連続確認
- 再開前に再確認する項目
  - [ ] 認証不足で実行されない
  - [ ] LockGuard 正常開閉
  - [ ] message・Audit Log・3画面整合

### Delete
- 現在保留へ戻す理由: 認証不足通過 / LockGuard 誤作動 / 削除後不整合 / Audit Log 欠落
- 再開条件: Export 条件達成 + 削除後整合の連続確認
- 再開前に再確認する項目
  - [ ] 認証不足で実行されない
  - [ ] 削除後3画面整合
  - [ ] message・Audit Log 一致

### 巻き込み確認（一覧/詳細/監査ログ/再描画整合）
- 現在保留へ戻す理由: 条件付き機能実行後に参照系・監査表示へ波及異常
- 再開条件: 実行後も一覧表示・詳細表示・Audit Log 参照・再描画整合が安定
- 再開前に再確認する項目
  - [ ] 一覧表示・詳細表示が崩れない
  - [ ] Audit Log 参照が欠落なく読める
  - [ ] 再描画後に不整合が残らない

---

## 安定運用初回レビュー フェーズ 見直し候補の再安定化条件（固定）

- Settings 保存
  - 見直し候補にした理由: 保存後の巻き戻り・空欄化・再表示不一致が発生
  - 再安定化条件: 保存反映・値保持・再表示一致が連続確認でき再発なし
  - 再レビュー前に再確認する項目
    - [ ] 値が巻き戻らない
    - [ ] 再表示で保持される
    - [ ] message・Audit Log 整合

- Freeze
  - 見直し候補にした理由: confirmed すり抜け・status 不整合・Audit Log 欠落が発生
  - 再安定化条件: confirmed 通過時のみ実行 + status 変更・Audit Log 整合が連続確認できる
  - 再レビュー前に再確認する項目
    - [ ] confirmed 未チェックで実行されない
    - [ ] status 変更が3画面一致
    - [ ] Audit Log 欠落なし

- Unfreeze
  - 見直し候補にした理由: confirmed すり抜け・status 復帰失敗・Audit Log 欠落が発生
  - 再安定化条件: confirmed 通過時のみ実行 + status 復帰・Audit Log 整合が連続確認できる
  - 再レビュー前に再確認する項目
    - [ ] confirmed 未チェックで実行されない
    - [ ] status 復帰が3画面一致
    - [ ] Audit Log 欠落なし

- Export
  - 見直し候補にした理由: 認証不足通過・LockGuard 誤作動・結果不一致・Audit Log 欠落が発生
  - 再安定化条件: 認証 / LockGuard / fail-safe 正常 + 結果整合が連続確認できる
  - 再レビュー前に再確認する項目
    - [ ] 認証不足で実行されない
    - [ ] LockGuard 正常開閉・残留なし
    - [ ] message・Audit Log・3画面整合

- Delete
  - 見直し候補にした理由: Export 条件への抵触または削除後3画面不整合が発生
  - 再安定化条件: Export 再安定化条件すべて + 削除後3画面整合が連続確認できる
  - 再レビュー前に再確認する項目
    - [ ] Export 再安定化条件すべて満たす
    - [ ] 削除後3画面一致
    - [ ] message・Audit Log 整合

- 巻き込み確認（一覧/詳細/監査ログ/再描画整合）
  - 見直し候補にした理由: 条件付き運用機能実行後に参照系・監査表示へ波及異常が発生
  - 再安定化条件: 実行後も一覧・詳細・Audit Log 参照・再描画整合が安定
  - 再レビュー前に再確認する項目
    - [ ] 一覧・詳細が崩れない
    - [ ] Audit Log 欠落なく読める
    - [ ] 再描画後に不整合が残らない

---

## 定期レビュー運用フェーズ 見直し候補機能の再評価条件チェック欄（固定）

- [ ] Settings 保存の再評価条件を `gui_error_flow_check.md` に固定した
- [ ] Freeze の再評価条件を `gui_error_flow_check.md` に固定した
- [ ] Unfreeze の再評価条件を `gui_error_flow_check.md` に固定した
- [ ] Export の再評価条件を `gui_error_flow_check.md` に固定した
- [ ] Delete の再評価条件（Export 条件前提）を `gui_error_flow_check.md` に固定した
- [ ] 巻き込み確認（一覧/詳細/監査ログ/再描画整合）の再評価条件を追記した
- [ ] 各項目に「見直し候補に残している理由」「再評価条件」「再評価前の再確認項目」の3点を記載した

---

## 運用テンプレ整備フェーズ 保留/再開判断テンプレ確認欄

- [ ] 機能保留/再開判断テンプレートを `docs/gui_hold_resume_template.md` として作成した
- [ ] テンプレートに判定日・対象機能・保留理由・影響範囲・代替運用・再開条件・再開前確認・再開判断・次回見直しの全項目を含めた
- [ ] 再開条件の参照先として `gui_error_flow_check.md` を記載した
- [ ] 停止・巻き戻し判断基準として `gui_go_live_decision.md` を記載した

## 保留中機能記録欄

- 現在保留中の機能: （なければ「なし」）
- 保留開始日: （記入）
- 保留理由の概要: （記入）
- 再開予定日: （記入）
- 参照テンプレート: `docs/gui_hold_resume_template.md`（コピーして使用）
- 記録ファイル命名規則: `gui_hold_resume_YYYYMMDD.md`

---

## 引き継ぎ用保留まとめ参照欄

- 保留機能・再開条件の引き継ぎまとめ: docs/gui_handoff_hold_resume.md
- 保留中機能の最新記録: docs/gui_known_gaps.md（保留中機能記録欄）
- 再開条件の判定参照先: docs/gui_error_flow_check.md
- 停止・巻き戻し判断基準: docs/gui_go_live_decision.md
- 記録テンプレート: docs/gui_hold_resume_template.md

---

## 最終完成報告フェーズ 残課題・見直しポイント（2026-03-26）

- まだ保留している機能または条件付き運用の機能
  - 保留: なし
  - 条件付き運用: Settings 保存 / Freeze / Unfreeze / Export / Delete
- docs と実装で今後も注意すべき点
  - 区分語は「本運用 / 条件付き運用 / 保留」で固定する
  - 状態名は connectionStatus / freezeStatus を基準に統一する
  - API 差し替え時は UI / service / docs を同一更新単位で見直す
- 定期レビューで確認すべき点
  - 条件付き運用5機能の継続条件が維持されているか
  - 一覧 / 詳細 / Dashboard / 管理パネルの状態整合が維持されているか
  - Audit Log の action / target / result 欠落と順序崩れがないか
- 将来の改善余地
  - 本API接続後の判定表更新と過去メモ整理
  - 失敗系 / 再開系の確認テンプレート拡充
  - 監視項目の自動集計による手動記録依存の低減
- 引き継ぎ時に注意すべき点
  - 参照起点は docs/gui_handoff_index.md を固定する
  - 変更時は docs/gui_known_gaps.md / docs/gui_handoff_feature_status.md / docs/gui_final_audit_report.md を同時更新する
  - 条件付き運用機能で異常が出た場合は機能単位の保留戻しを優先する

## 1枚要約版との対応（2026-03-26）

- 対応先: docs/gui_one_page_summary.md の「注意点（圧縮版）」
- 上記の残課題・見直しポイントを要約版に同期する
