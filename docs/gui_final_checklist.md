# GUI 最終確認チェックリスト

## 現行判定の基準（最終確定版）

- 本チェックリスト内の「2026-03-23」「2026-03-24」表記セクションは履歴記録として扱う
- 現行の運用判定は以下を正本として扱う
	- `docs/gui_handoff_feature_status.md`
	- `docs/gui_final_operations_decision.md`
- 現行区分は「本運用 / 条件付き運用 / 保留」で統一する
- 用語は `LockGuard`（Export / Delete）と Freeze warning（Freeze / Unfreeze 警告表示）を使い分ける
- 状態項目名は `connectionStatus` / `freezeStatus` を基準にする

## 段階解放レベル別 解放条件（最終判定用）

### Level1: 参照系

- 対象機能: 一覧表示 / 詳細表示 / Dashboard / Audit Log 参照 / Settings 参照
- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし

## Level1 解放直前チェック欄

- [ ] API_BASE_URL確認: 解放先環境のURLが正しい
- [ ] 一覧表示確認: 初期表示と再取得後の表示が崩れない
- [ ] 詳細表示確認: 選択変更時に詳細表示が追従する
- [ ] Dashboard確認: 一覧データと集計表示が一致する
- [ ] Audit Log 参照確認: ログ一覧が表示され最新化できる
- [ ] Settings 参照確認: 設定値が画面に正しく反映される
- [ ] message表示確認: 取得成功/失敗の表示が結果と一致する
- [ ] プレースホルダー確認: TODO/仮文言/仮リンクが残っていない
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が同時に整合する

## Level1 一覧/詳細 安定監視ポイント

- [ ] 一覧が継続して表示されるか
	- 正常: 再読込後も一覧表示が維持される
	- 異常兆候: 一覧が消える、行欠落が継続する
- [ ] 一覧と詳細の選択整合が取れているか
	- 正常: 一覧選択と詳細表示の対象が一致する
	- 異常兆候: 詳細表示の対象が一覧選択とずれる
- [ ] 詳細ボタン押下後に表示が崩れないか
	- 正常: 詳細表示のレイアウトと項目表示が維持される
	- 異常兆候: 詳細パネルの崩れ、空白化、フリーズ
- [ ] 詳細取得失敗時にプレースホルダーへ戻れるか
	- 正常: 失敗時にプレースホルダーへ戻り、再取得で復帰する
	- 異常兆候: 失敗後に復帰せず空白表示のままになる
- [ ] message 表示が過不足ないか
	- 正常: 成功/失敗に応じたmessageが過不足なく表示される
	- 異常兆候: messageが出ない、重複する、内容が不一致

## Settings 保存 安定監視ポイント

- [ ] 保存後に値が反映されたまま維持されるか
	- 正常: 保存成功後、再読込しても設定値が元のまま保持される
	- 異常兆候: 保存直後は反映されるが、再読込で値が古い値に戻る
- [ ] 保存後に message が適切に出るか
	- 正常: 保存成功時に成功 message、失敗時に失敗 message が表示される
	- 異常兆候: message が出ない、失敗時も成功 message が表示される
- [ ] Audit Log が更新されるか
	- 正常: Settings 保存後に Audit Log に操作記録が追記される
	- 異常兆候: 保存後も Audit Log に記録が追加されない
- [ ] 画面再描画後に値が戻らないか
	- 正常: 保存後の各種再描画・画面遷移後も値が保持される
	- 異常兆候: 画面遷移や再描画後に保存前の値に初期化される
- [ ] Settings 参照表示が崩れないか
	- 正常: 保存後に Settings 参照画面が正常表示される
	- 異常兆候: 保存後に参照値が空欄化、初期値固定、崩れ表示になる

### Level1 対象外（このチェックでは扱わない）

- [ ] 更新系: Settings 保存 / Connect / Disconnect
- [ ] 条件付き更新系: Freeze / Unfreeze
- [ ] 危険操作系: Export / Delete

### Level2: 低リスク更新系

- 対象機能: Connect / Disconnect
- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし
- [ ] connectionStatus の反映一致を確認済み

## Level2 解放直前チェック欄

- [ ] API_BASE_URL確認: Level2 解放先の環境値が正しい
- [ ] Level1 監視で重大異常なし
- [ ] Settings 参照確認: 参照値が安定表示される
- [ ] Settings 保存確認: 保存後の再読込で値保持を確認できる
- [ ] Connect 確認: 実行後に接続状態が反映される
- [ ] Disconnect 確認: 実行後に切断状態が反映される
- [ ] Audit Log 更新確認: Settings/Connect/Disconnect の記録が追記される
- [ ] message表示確認: 成功/失敗 message が結果と一致する
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が整合する
- [ ] fail-safe確認: 異常時に state 不整合なく停止できる

### Level2 対象外（このチェックでは扱わない）

- [ ] Freeze / Unfreeze
- [ ] Export / Delete

## Level2 起動前チェック（実行フェーズ固定）

- [ ] API_BASE_URL確認
- [ ] Level1 監視で重大異常なし
- [ ] Settings 参照確認
- [ ] Settings 保存確認
- [ ] Connect 確認
- [ ] Disconnect 確認
- [ ] Audit Log 更新確認
- [ ] message表示確認
- [ ] 再描画整合確認
- [ ] fail-safe確認

### Level2 対象外（実行フェーズ固定）

- [ ] Freeze / Unfreeze
- [ ] Export / Delete

## Level2 進行前提条件チェック欄（Level1 継続判定）

- [ ] これを満たしたら Level2 に進める: Level1 監視で重大異常なし
- [ ] これを満たしたら Level2 に進める: 一覧/詳細表示が安定
- [ ] これを満たしたら Level2 に進める: Dashboard が安定
- [ ] これを満たしたら Level2 に進める: Audit Log 参照が安定
- [ ] これを満たしたら Level2 に進める: Settings 参照が安定
- [ ] これを満たしたら Level2 に進める: message 表示が適切
- [ ] これを満たしたら Level2 に進める: プレースホルダー復帰が適切

### Level2 判定対象外（Level1継続判定時）

- [ ] 更新系の本格判定（Settings 保存 / Connect / Disconnect）
- [ ] 条件付き更新系（Freeze / Unfreeze）
- [ ] 危険操作系（Export / Delete）

## Level3 へ進む前提条件チェック欄（Level2 継続判定）

- [ ] これを満たしたら Level3 に進める: Level2 監視で重大異常なし
- [ ] これを満たしたら Level3 に進める: Settings 保存が安定（保存後の再読込で値保持）
- [ ] これを満たしたら Level3 に進める: Connect が安定（接続状態が一覧/詳細/管理パネルで一致）
- [ ] これを満たしたら Level3 に進める: Disconnect が安定（切断状態が一覧/詳細/管理パネルで一致）
- [ ] これを満たしたら Level3 に進める: Audit Log 更新が安定（操作記録の欠落・順序崩れなし）
- [ ] これを満たしたら Level3 に進める: message 表示が適切（成功/失敗の表示不整合なし）
- [ ] これを満たしたら Level3 に進める: 再描画整合が保たれている（一覧/詳細/Dashboard/Audit Log が同期）
- [ ] これを満たしたら Level3 に進める: 参照系が巻き込まれて崩れていない（一覧/詳細/Dashboard/Audit Log 参照/Settings 参照が安定）

### Level3 以降で扱う対象

- [ ] Freeze / Unfreeze（Level3 判定対象）
- [ ] Export / Delete（Level4 判定対象）

## Level4 へ進む前提条件チェック欄（Level3 継続判定）

- [ ] これを満たしたら Level4 に進める: Level3 監視で重大異常なし
- [ ] これを満たしたら Level4 に進める: Freeze が安定（freezeStatus 維持・警告導線正常・再発なし）
- [ ] これを満たしたら Level4 に進める: Unfreeze が安定（freezeStatus 復帰・警告導線正常・再発なし）
- [ ] これを満たしたら Level4 に進める: 警告表示導線が安定（開閉/キャンセル/確認チェック導線の破綻なし）
- [ ] これを満たしたら Level4 に進める: Audit Log 更新が安定（Freeze/Unfreeze 記録の欠落・順序崩れなし）
- [ ] これを満たしたら Level4 に進める: message 表示が適切（成功/失敗の表示不整合なし）
- [ ] これを満たしたら Level4 に進める: 再描画整合が保たれている（一覧・詳細・Dashboard・Audit Log が同期）
- [ ] これを満たしたら Level4 に進める: Level1 / Level2 解放機能が巻き込まれて崩れていない

### Level4 進行条件の対象外（Level3継続判定時）

- [ ] Export / Delete の個別実行可否判定は未実施（Level4 側で判定）

## Level3 解放直前チェック欄

- [ ] API_BASE_URL確認: Level3 解放先環境の値が正しい
- [ ] Level2 監視で重大異常なし
- [ ] Freeze 警告表示確認: 警告モーダルが表示され確認チェック導線が動作する
- [ ] Unfreeze 警告表示確認: 警告モーダルが表示され確認チェック導線が動作する
- [ ] 確認チェック導線確認: confirmed 未チェック時に execute が中断される
- [ ] Freeze 実行確認: 確認チェック後に freezeStatus が `frozen` へ反映される
- [ ] Unfreeze 実行確認: 確認チェック後に freezeStatus が `active` へ反映される
- [ ] Audit Log 更新確認: Freeze/Unfreeze 操作後に Audit Log へ記録が追記される
- [ ] message表示確認: 成功/失敗 message が操作結果と一致する
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が整合する
- [ ] fail-safe確認: blockId 不在・状態不正・confirmed 未チェック時に中断する

### Level3 対象外（このチェックでは扱わない）

- [ ] Export: 危険操作系のため Level4 まで未解放維持
- [ ] Delete: 危険操作系のため Level4 まで未解放維持

### Level3: 条件付き更新系

- 対象機能: Settings 保存 / Freeze / Unfreeze
- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし
- [ ] Settings 保存後の値保持確認済み
- [ ] freezeStatus の反映一致を確認済み

## Freeze / Unfreeze 安定監視ポイント

- [ ] Freeze 後に freezeStatus が維持されるか
	- 正常: Freeze 実行後、freezeStatus が frozen のまま一覧・詳細・管理パネルで維持される
	- 異常兆候: 一度 frozen になっても再描画や再取得後に active へ戻る
- [ ] Unfreeze 後に freezeStatus が戻るか
	- 正常: Unfreeze 実行後、freezeStatus が active に戻り一覧・詳細・管理パネルで一致する
	- 異常兆候: active に戻らない、または一部画面だけ frozen のまま残る
- [ ] message が適切に出るか
	- 正常: 成功時は成功 message、失敗時は失敗 message が結果どおり表示される
	- 異常兆候: message が出ない、重複する、成功/失敗が逆転して表示される
- [ ] Audit Log が更新されるか
	- 正常: Freeze / Unfreeze の action / target / result が操作直後に追記される
	- 異常兆候: 記録が追加されない、内容が実行操作と一致しない
- [ ] 一覧/詳細/管理パネルで表示が揃うか
	- 正常: 同一対象の freezeStatus が3画面で同じ状態を示す
	- 異常兆候: 一覧・詳細・管理パネルのいずれかで状態表示が食い違う
- [ ] 参照系が巻き込まれて崩れないか
	- 正常: 一覧表示・詳細表示・Dashboard・Audit Log 参照が Freeze / Unfreeze 後も崩れない
	- 異常兆候: 行欠落、詳細不一致、Dashboard 空欄化、Audit Log 一覧崩れが発生する

### Level4: 危険操作系（最厳格）

- 対象機能: Export / Delete
- [ ] 正常系確認済み
- [ ] 異常系確認済み
- [ ] 再描画整合確認済み
- [ ] message 表示確認済み
- [ ] Audit Log 更新確認済み
- [ ] fail-safe 確認済み
- [ ] 初回監視で重大異常なし
- [ ] LockGuard 全項目検証確認済み
- [ ] confirmed 未チェック時の中断確認済み
- [ ] 認証不足時の中断確認済み
- [ ] 失敗時 state 不変確認済み
- [ ] 通し確認シナリオで再発なし

## Level4 解放直前チェック欄（実行フェーズ固定）

- [ ] API_BASE_URL確認: Level4 解放先環境の接続先が正しい
- [ ] Level3 監視で重大異常なし
- [ ] LockGuard 表示確認: Export / Delete 実行前にLockGuardが正しく表示される
- [ ] password 入力確認: 未入力時は中断し、入力時のみ判定へ進む
- [ ] twoFactorCode 入力確認: 未入力時は中断し、入力時のみ判定へ進む
- [ ] confirmationText 入力確認: 指定文言不一致時は中断する
- [ ] confirmed チェック確認: 未チェック時は実行できない
- [ ] Export 実行確認: 認証通過後のみ実行され、結果がUIへ反映される
- [ ] Delete 実行確認: 認証通過後のみ実行され、結果がUIへ反映される
- [ ] Audit Log 更新確認: Export / Delete の action / target / result が追記される
- [ ] message表示確認: 成功 / 失敗 / 認証失敗の表示が結果と一致する
- [ ] 再描画整合確認: 一覧・詳細・Dashboard・Audit Log が操作後に整合する
- [ ] fail-safe確認: 認証不足・確認未完了・入力不備・pending時に中断する

### Level4 対象外（実行フェーズ固定）

- [ ] Freeze / Unfreeze の継続判定は対象外（Level3 側で継続監視）

## 画面別チェック
- [ ] 一覧画面: 初期表示、読み込み中、空状態、エラー表示が想定どおり
- [ ] 詳細画面: 必須情報が欠けずに表示される
- [ ] 作成/編集画面: 入力、保存、バリデーション表示が動作する
- [ ] 設定画面: 保存後に再読み込みしても値が保持される
- [ ] 画面遷移: 戻る/進む/直リンクで破綻しない

## 危険操作チェック
- [ ] 削除・上書き・一括更新に確認ダイアログが出る
- [ ] 確認ダイアログに対象名/件数が表示される
- [ ] キャンセル時に状態が変化しない
- [ ] 実行後に取り消し不能である旨を明示している

## 再描画チェック
- [ ] フィルタ/検索/ソートで不要な全体再描画が起きない
- [ ] タブ切替時に状態が意図せず初期化されない
- [ ] モーダル開閉で背景リストが崩れない
- [ ] 同一データ再取得時にちらつきが過剰でない

## メッセージ表示チェック
- [ ] 成功メッセージ: 操作名が明確
- [ ] 失敗メッセージ: 原因と次アクションが分かる
- [ ] 入力エラー: 項目単位で表示される
- [ ] トースト/ダイアログの表示時間・閉じ方が適切

## ログ更新チェック
- [ ] 操作ログに操作種別・対象・時刻が記録される
- [ ] 失敗時ログにエラー種別が記録される
- [ ] 連続操作時に順序が逆転しない
- [ ] ログ表示が最新化される（手動更新不要）

## プレースホルダー確認
- [ ] ダミー文言（TODO/仮/サンプル）が残っていない
- [ ] 仮画像・仮アイコン・仮リンクが残っていない
- [ ] 空状態文言が画面目的に合っている

## Bash確認コマンド欄
```bash
cd ~/ai_media_os
ls -la docs
sed -n '1,240p' docs/gui_final_checklist.md
sed -n '1,240p' docs/gui_known_gaps.md
```

---

## 全API通し確認シナリオ

> Step1〜Step6 完了後に、以下の順で通して実施する。

| # | 操作 | 確認したいこと |
|---|------|----------------|
| 1 | 一覧表示 | `GET /blocks` が発行され、block 一覧が崩れず表示される |
| 2 | 詳細表示 | block 選択で `GET /blocks/{id}` が発行され、詳細パネルが更新される |
| 3 | Connect | `POST /blocks/{id}/connect` が発行され、connectionStatus が `connected` へ反映される |
| 4 | Disconnect | `POST /blocks/{id}/disconnect` が発行され、connectionStatus が `disconnected` へ反映される |
| 5 | Freeze | 警告確認チェック後に `POST /blocks/{id}/freeze` が発行され、freezeStatus が `frozen` へ反映される |
| 6 | Unfreeze | 警告確認チェック後に `POST /blocks/{id}/unfreeze` が発行され、freezeStatus が `active` へ反映される |
| 7 | Settings 読み込み | `GET /settings/security` が発行され、フォームに現在値が反映される |
| 8 | Settings 保存 | `PUT /settings/security` が発行され、成功 message が表示される |
| 9 | Audit Log 確認 | `GET /audit-logs` が発行され、各操作の記録が一覧に表示される |
| 10 | Export | LockGuard 認証通過後に `POST /blocks/{id}/export` が発行され、成功時に再描画される |
| 11 | Delete | LockGuard 認証通過後に `DELETE /blocks/{id}` が発行され、成功時に deleteRequested が反映される |

### 通し確認の共通チェック
- [ ] 各操作後に Audit Log に記録が追記される
- [ ] 各操作後に Dashboard 集計が最新値に更新される
- [ ] 各操作後に block 一覧・詳細が最新状態で再描画される
- [ ] いずれかの API が失敗しても他の操作が継続できる
- [ ] message 表示が操作ごとに正しく切り替わる

### 通し確認の fail-safe チェック
- [ ] confirmed 未チェックで freeze / export / delete が中断される
- [ ] 認証情報不足で export / delete が中断され block 状態が変化しない
- [ ] API 失敗後も一覧・詳細の表示状態が変化しない
- [ ] 二重クリックによる二重実行が pending 制御で止まる
- [ ] Console に未処理例外が残らない

### 通し確認の判定基準
| 項目 | 合格 |
|------|------|
| ネットワークタブ | 各 API が期待 method / path で発行される |
| 表示整合 | 操作後の一覧・詳細・Dashboard が一致している |
| Audit Log | 全操作分の記録が残っている |
| 失敗時 | message のみ表示、block 状態は変化しない |
| 二重実行 | 同一操作の pending 中は後続クリックが無視される |

---

## 通し確認済みチェック欄

- [ ] 一覧→詳細→Connect→Disconnect を通して確認済み
- [ ] Freeze→Unfreeze→Settings 読み込み/保存→Audit Log を通して確認済み
- [ ] Export→Delete（LockGuard 認証付き）を通して確認済み
- [ ] 失敗系（API失敗/認証不足/確認未実施）を通して確認済み
- [ ] `docs/gui_full_flow_check.md` に実施結果を記録済み

## 危険操作 fail-safe 確認欄

- [ ] Export: LockGuard `confirmed` 未チェック時に実行されない
- [ ] Delete: LockGuard `confirmed` 未チェック時に実行されない
- [ ] Export: 認証不足時に `success=false` で中断され状態が変化しない
- [ ] Delete: 認証不足時に `success=false` で中断され状態が変化しない
- [ ] 危険操作失敗時に message 表示のみで UI が崩れない

## 再描画整合確認欄

- [ ] Connect/Disconnect 成功後に一覧・詳細・接続管理パネルが整合する
- [ ] Freeze/Unfreeze 成功後に一覧・詳細・Dashboard・Audit Log が整合する
- [ ] Settings 保存成功後に Settings 表示と message が整合する
- [ ] Export/Delete 成功後に一覧・詳細・Audit Log が整合する
- [ ] 失敗系では再描画せず、既存表示を維持する

## 稼働開始判定メモ欄（履歴）

- 判定日: 2026-03-23
- 判定結果: 機能選別により本運用/条件付き運用/保留で管理する
- 保留理由: 危険操作・高影響操作は条件を満たすまで段階的に解放する
- 稼働開始前に残る確認事項: 条件付き運用機能の確認フロー動作検証、危険操作の継続監視

## 稼働開始・保留 機能判定（履歴）

| 機能 | 判定 | 理由 |
|------|------|------|
| 一覧表示 | ✅ 本運用 | 読み取り専用・状態変更なし |
| 詳細表示 | ✅ 本運用 | 読み取り専用・状態変更なし |
| Dashboard | ✅ 本運用 | 読み取り専用・集計表示のみ |
| Audit Log 参照 | ✅ 本運用 | 読み取り専用・ログ参照のみ |
| Settings 参照 | ✅ 本運用 | 読み取り中心。表示値の整合が安定 |
| Connect | ✅ 本運用 | 可逆操作。connectionStatus と Audit Log の整合が安定 |
| Disconnect | ✅ 本運用 | 可逆操作。connectionStatus と Audit Log の整合が安定 |
| Settings 保存 | ⚠️ 条件付き運用 | `PUT /settings/security` の保存反映・再表示一致を継続監視 |
| Freeze | ⚠️ 条件付き運用 | confirmed 導線・freezeStatus 整合・Audit Log 整合を継続監視 |
| Unfreeze | ⚠️ 条件付き運用 | confirmed 導線・freezeStatus 復帰・Audit Log 整合を継続監視 |
| Export | ⚠️ 条件付き運用 | LockGuard 認証・監査記録・実行後整合を継続監視 |
| Delete | ⚠️ 条件付き運用 | LockGuard 認証・監査記録・実行後整合を継続監視 |

---

## 異常系確認済みチェック欄

- [ ] 一覧取得失敗シナリオを確認済み
- [ ] 詳細取得失敗シナリオを確認済み
- [ ] Connect/Disconnect 失敗シナリオを確認済み
- [ ] Freeze/Unfreeze 失敗シナリオを確認済み
- [ ] Export/Delete/LockGuard 失敗シナリオを確認済み
- [ ] `docs/gui_error_flow_check.md` に結果を記録済み

## fail-safe 確認欄

- [ ] 不正状態（対象ID不在/状態不正）で service call せず停止する
- [ ] 確認チェック未実施で危険操作が停止する
- [ ] 認証不足/不一致で危険操作が停止する
- [ ] API 失敗時に state 不整合を起こさず停止する
- [ ] 例外発生時に UI 崩壊なく停止する

## message 表示確認欄

- [ ] 一覧取得失敗時に失敗 message が表示される
- [ ] 詳細取得失敗時に失敗 message が表示される
- [ ] Connect/Disconnect 失敗時に失敗 message が表示される
- [ ] Freeze/Unfreeze 失敗時に失敗 message が表示される
- [ ] Export/Delete/LockGuard 失敗時に失敗 message が表示される
- [ ] 連続操作時に message が最新結果で上書きされる

## 既存表示維持/プレースホルダー復帰確認欄

- [ ] 一覧取得失敗時に既存一覧表示を維持できる
- [ ] 詳細取得失敗時に詳細パネルをプレースホルダーへ復帰できる
- [ ] Connect/Disconnect 失敗時に既存表示が崩れない
- [ ] Freeze/Unfreeze 失敗時に warning 導線と既存表示が維持される
- [ ] Export/Delete 失敗時に LockGuard を維持し既存表示が崩れない

---

## 稼働開始前 最終チェックリスト（履歴: 2026-03-23）

> すべての項目に ✅ が入るまで稼働開始しない。

### 環境・接続確認
- [ ] API_BASE_URL が本番/ステージング環境の正しい値に設定されている
- [ ] CORS / 認証ヘッダーが本番環境で正しく通る
- [ ] mock データへの直接参照が残っていない

### 表示確認
- [ ] 一覧表示: GET /blocks が発行され、block 一覧が崩れず表示される
- [ ] 詳細表示: block 選択で GET /blocks/{id} が発行され、詳細パネルが更新される
- [ ] Dashboard: 集計値が一覧データと整合している
- [ ] Audit Log: GET /audit-logs が発行され、ログ一覧が表示される

### 操作確認
- [ ] Connect: POST /blocks/{id}/connect が発行され connectionStatus が `connected` へ反映される
- [ ] Disconnect: POST /blocks/{id}/disconnect が発行され connectionStatus が `disconnected` へ反映される
- [ ] Settings 読み込み: GET /settings/security が発行されフォームに現在値が反映される
- [ ] Settings 保存: PUT /settings/security が発行されリロード後も値が保持される

### fail-safe 確認
- [ ] confirmed 未チェックで freeze / export / delete が実行されない
- [ ] 認証不足で export / delete が中断され block 状態が変化しない
- [ ] pending 中の同一操作が二重実行されない
- [ ] API 失敗時に state 不整合が起きない

### 異常系確認
- [ ] 一覧取得失敗時に既存表示が維持され message が表示される
- [ ] 詳細取得失敗時にプレースホルダーへ復帰し message が表示される
- [ ] Connect/Disconnect 失敗時に表示が崩れず message が表示される
- [ ] Console に未処理例外が残っていない

### 再描画整合確認
- [ ] 各操作後に一覧・詳細・Dashboard・Audit Log が一致している
- [ ] タブ切替・モーダル開閉で表示が崩れない

### message 表示確認
- [ ] 成功・失敗・入力エラーそれぞれの message が正しく表示される
- [ ] 連続操作時に message が最新結果で上書きされる

### 危険操作解放判定
- [ ] Freeze / Unfreeze: 解放条件（本API接続・正常系/異常系/fail-safe/message/Audit Log）をすべて確認済み
- [ ] Export / Delete: 解放条件（本API接続・LockGuard全検証・取り消し不能明示・全確認）をすべて確認済み
- [ ] 未達条件がある場合は該当操作を保留のまま稼働開始する

---

## 稼働開始判定済みチェック欄（履歴）

- [ ] 判定日を `docs/gui_go_live_decision.md` に記録した
- [ ] 判定結果（本運用/条件付き運用/保留）を記録した
- [ ] 停止判断条件を記録した
- [ ] 次の見直しタイミングを記録した

### 本運用機能チェック欄

- [ ] 一覧表示
- [ ] 詳細表示
- [ ] Dashboard
- [ ] Audit Log 参照

### 条件付き運用チェック欄

- [ ] Settings 参照
- [ ] Connect
- [ ] Disconnect
- [ ] Settings 保存（本API接続後）
- [ ] Freeze（本API接続後）
- [ ] Unfreeze（本API接続後）

### 保留機能チェック欄

- [ ] Export（解放保留）
- [ ] Delete（解放保留）

---

## 小規模稼働対象チェック欄（履歴: 2026-03-23）

### 小規模稼働開始する機能

- [ ] 一覧表示（理由: 読み取り専用で影響範囲が小さい）
- [ ] 詳細表示（理由: 読み取り専用で状態変更がない）
- [ ] Dashboard（理由: 参照系のみで安全に確認できる）
- [ ] Audit Log 参照（理由: 参照系のみで運用監視に有効）

### 条件付きで開始する機能

- [ ] Settings 参照（理由: 表示確認用途として限定運用）
- [ ] Settings 保存（理由: 本API接続後のみ開始）
- [ ] Connect（理由: 可逆操作のため監視付きで限定開始）
- [ ] Disconnect（理由: 可逆操作のため監視付きで限定開始）
- [ ] Freeze（理由: 本API接続 + fail-safe 確認完了が前提）
- [ ] Unfreeze（理由: 本API接続 + fail-safe 確認完了が前提）

### 今回は開始しない機能

- [ ] Export（理由: 取り消し不能 + LockGuard 検証未完了）
- [ ] Delete（理由: 取り消し不能 + LockGuard 検証未完了）

---

## 本運用開始機能 起動前チェック欄（2026-03-23）

> 本運用開始対象を起動する前に、以下をすべて確認する。

- [ ] API_BASE_URL確認: 起動先環境の値が正しい
- [ ] 一覧表示確認: 初期表示で一覧が崩れず表示される
- [ ] 詳細表示確認: block選択で詳細が更新される
- [ ] Dashboard確認: 集計値が一覧データと一致する
- [ ] Audit Log参照確認: ログ一覧が取得・表示される
- [ ] Settings参照確認: 現在値が画面に反映される
- [ ] Connect/Disconnect確認: 状態遷移が一覧/詳細に反映される
- [ ] message表示確認: 成功/失敗の文言が正しく切り替わる
- [ ] 再描画整合確認: 操作後に一覧・詳細・Dashboard・Audit Log が整合する

---

## 本運用開始機能 監視ポイント（2026-03-23）

| 機能 | 正常に見える状態 | 異常兆候 | 止めるべき目安 |
|---|---|---|---|
| 一覧表示 | 行が揃って表示・操作後も崩れない | 空欄行・カラム欠け・古いデータ残存 | 複数回操作後も更新されない |
| 詳細表示 | 選択に連動して即時更新 | 前の内容が残る・id 不一致 | 選択変更に一切反応しない |
| Dashboard | 一覧の集計値と一致 | 数値乖離・操作後に未更新 | 乖離が操作をまたいで継続 |
| Audit Log 参照 | 操作後に自動追記・内容正常 | 追記なし・内容空・順序逆転 | 複数操作してもログ未更新 |
| Settings 参照 | 現在値が正しく表示 | 空欄・デフォルト値のまま | 参照 API が連続エラー |
| Connect | connectionStatus が接続済みに変わる | 状態未反映・一覧詳細で食い違い | 複数回後も未反映またはログ未記録 |
| Disconnect | connectionStatus が切断済みに変わる | 状態未反映・Connect 後も戻らない | 複数回後も未反映またはログ未記録 |

---

## 初回監視 UI 異常兆候（2026-03-23）

- message が出ない → **即停止**
- 古い表示のまま更新されない → **即停止**
- 詳細パネルが空になる → **即停止**
- Dashboard 数値がずれる → 継続監視（繰り返すなら停止）
- Audit Log が増えない → **即停止**
- Settings 保存後に値が戻る → **即停止**
- 警告表示が閉じない → 継続監視（繰り返すなら停止）
- LockGuard が消えない / 誤作動する → **即停止**

---

## 次の稼働拡大条件（2026-03-23）

- [ ] 初回監視で重大異常なし
	- これを満たしたら次へ進める: 即停止相当の異常が発生していない
- [ ] 再描画整合が保たれている
	- これを満たしたら次へ進める: 一覧・詳細・Dashboard・Audit Log の不整合が再発しない
- [ ] message 表示が適切
	- これを満たしたら次へ進める: 成功/失敗/入力エラーの message が操作結果と一致する
- [ ] Audit Log が更新される
	- これを満たしたら次へ進める: 主要操作ごとに action/target/result が欠落なく追記される
- [ ] Settings 保存が安定
	- これを満たしたら次へ進める: 保存後の再読込で値保持が継続する
- [ ] Connect / Disconnect が安定
	- これを満たしたら次へ進める: connectionStatus 反映とログ追記が連続して一致する
- [ ] Freeze / Unfreeze が安定
	- これを満たしたら次へ進める: freezeStatus 遷移と confirmed fail-safe が連続して成立する

---

## Level4 解放直前チェック欄（実行フェーズ固定）

> Level4 は最終危険操作段階。全項目グリーンでなければ解放しない。

### 環境・前提確認
- [ ] API_BASE_URL が本番相当の正しい向き先であることを確認した
- [ ] Level3 監視サイクルで即停止相当の重大異常が発生していないことを確認した
- [ ] Level1 / Level2 / Level3 の解放機能が現時点で正常稼働していることを確認した

### LockGuard 確認
- [ ] Export 操作で LockGuard が正しく表示されることを確認した
- [ ] Delete 操作で LockGuard が正しく表示されることを確認した
- [ ] LockGuard がキャンセルで正しく閉じることを確認した
- [ ] LockGuard が操作完了後に正しく閉じることを確認した

### 認証・fail-safe 確認
- [ ] password フィールドが未入力のとき Export/Delete が実行されないことを確認した
- [ ] twoFactorCode フィールドが未入力のとき Export/Delete が実行されないことを確認した
- [ ] confirmationText フィールドが未入力のとき Export/Delete が実行されないことを確認した
- [ ] confirmed チェックが未投入のとき Export/Delete が実行されないことを確認した
- [ ] 全フィールド入力 + confirmed チェック後のみ実行されることを確認した（fail-safe 正常）

### 実行結果確認
- [ ] Export 実行後に成功/失敗に応じた message が表示されることを確認した
- [ ] Export 実行後に Audit Log に action/target/result が追記されることを確認した
- [ ] Export 実行後に一覧・詳細・管理パネルの状態が整合することを確認した
- [ ] Delete 実行後に成功/失敗に応じた message が表示されることを確認した
- [ ] Delete 実行後に Audit Log に action/target/result が追記されることを確認した
- [ ] Delete 実行後に一覧・詳細・管理パネルの状態が整合することを確認した

### 再描画・整合確認
- [ ] Export/Delete 後に一覧・詳細・Dashboard・Audit Log が同時に整合することを確認した
- [ ] Level1 / Level2 / Level3 解放機能が巻き込まれて崩れていないことを確認した

### 解放判断
- [ ] 上記全項目グリーンであることを最終確認した
- [ ] 解放判断者の承認を得た

## Level4 対象外（実行フェーズ固定）

- Level4 解放対象は Export / Delete のみ
- Level1〜3 の解放済み機能は継続監視に移行

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

## Level4 全面継続・最終運用移行 前提条件（固定）

> 以下を全て満たした場合のみ移行可。1項目でも満たさない場合は移行不可。

- Level4 監視で重大異常なし（即停止事象ゼロ、条件付き停止事象が収束）
- Export が安定（confirmed・認証・LockGuard・Audit Log・状態整合が全回正常、複数回再発なし）
- Delete が安定（Export と同条件 + 削除後3画面整合が全回取れている）
- LockGuard 導線が安定（実行・キャンセル・失敗後いずれも正常閉鎖、残留・誤作動なし）
- Audit Log 更新が安定（欠落・順序逆転・内容不一致が1件もない）
- message 表示が適切（成功・失敗・認証失敗の表示が操作結果と常に一致し、不整合再発なし）
- 再描画整合が保たれている（操作後の一覧・詳細・Dashboard・Audit Log が全回整合、崩れ再発なし）
- Level1〜3 解放機能が巻き込まれて崩れていない（一覧/詳細/Dashboard/Audit Log/Settings/Connect/Disconnect/Freeze/Unfreeze が全回正常）

---

## Level4 全面継続・最終運用移行 前提チェック欄

- [ ] Level4 監視で重大異常なしを確認した
- [ ] Export の安定を複数回確認した
- [ ] Delete の安定を複数回確認した
- [ ] LockGuard 導線の安定を確認した
- [ ] Audit Log 更新の安定を確認した
- [ ] message 表示の適切さを確認した
- [ ] 再描画整合が保たれていることを確認した
- [ ] Level1〜3 解放機能の巻き込み崩れがないことを確認した
- [ ] 全項目を満たしたと判断し、移行を決定した

---

## 最終運用判定フェーズ 本運用に進める条件（固定）

> 以下を全て満たした場合のみ本運用に進めてよい。1項目でも満たさない場合は本運用移行を保留する。

- [ ] Level1〜Level4 監視で重大異常（即停止事象）が1件もない
- [ ] 再描画整合が保たれている（操作後の一覧・詳細・Dashboard・Audit Log が全回整合、崩れ再発なし）
- [ ] message 表示が適切（成功・失敗・認証失敗の表示が操作結果と常に一致し、不整合再発なし）
- [ ] Audit Log 更新が安定（全操作で action / target / result が欠落なく追記され、欠落・不整合が1件もない）
- [ ] Settings 保存が安定（保存後に反映され、空欄化・巻き戻りが発生しない）
- [ ] Connect / Disconnect が安定（実行後の状態表示と3画面整合が全回正常）
- [ ] Freeze / Unfreeze が安定（confirmed 導線・Audit Log・再描画整合の安定を複数回確認済み）
- [ ] Export が安定（LockGuard・confirmed・認証・Audit Log・状態整合が全回正常、複数回再発なし）
- [ ] Delete が安定（Export 条件を満たし、削除後の3画面整合が全回取れている）
- [ ] LockGuard / 認証 / fail-safe が安定（confirmed 未チェック・認証不足で実行が通ったことが1件もない）
- [ ] 全項目を満たしたと判断し、本運用移行を決定した

---

## 最終運用開始フェーズ 本運用開始直前チェック欄（固定）

- [ ] API_BASE_URL確認: 本番向け接続先が想定値と一致している
- [ ] Level1〜Level4 判定完了確認: 各段階の判定ログと承認が完了している
- [ ] 一覧/詳細表示確認: 同一対象の表示が一致し、崩れがない
- [ ] Dashboard確認: 件数・状態表示が最新状態と一致している
- [ ] Audit Log確認: 直近操作の action / target / result が欠落なく読める
- [ ] Settings 参照/保存確認: 参照可能で、保存後に反映され巻き戻りがない
- [ ] Connect/Disconnect確認: 実行結果と状態表示が一致している
- [ ] Freeze/Unfreeze確認: confirmed 導線通過後のみ実行され、状態整合が取れている
- [ ] Export/Delete確認: 実行条件を満たした時のみ実行され、結果整合が取れている
- [ ] LockGuard確認: 開閉が正常で、実行後に残留しない
- [ ] message表示確認: 成功/失敗/認証失敗の表示が操作結果と一致している
- [ ] 再描画整合確認: 操作後に一覧・詳細・Dashboard・Audit Log が同時に整合する
- [ ] fail-safe確認: confirmed 未チェック・認証不足では実行が通らない
- [ ] 上記全項目を満たしたため本運用開始可と判断した

---

## 最終運用初回監視フェーズ 参照系・低リスク更新系 初回監視ポイント（固定）

- 一覧表示
  - 正常: 件数・状態が最新で表示崩れがない
  - 異常兆候: 件数不一致、古い状態残留、表示崩れ
- 詳細表示
  - 正常: 一覧選択対象と詳細状態が一致する
  - 異常兆候: 一覧と詳細の状態不一致、空欄化
- Dashboard
  - 正常: 操作後に件数・状態サマリが即時反映される
  - 異常兆候: 反映遅延、件数不一致、古い表示残留
- Audit Log 参照
  - 正常: action / target / result が欠落なく読める
  - 異常兆候: 未追記、内容不一致、順序逆転
- Settings 参照
  - 正常: 参照項目が欠落なく表示される
  - 異常兆候: 項目欠落、空欄化、読み込み失敗
- Settings 保存
  - 正常: 保存後に反映され再表示でも保持される
  - 異常兆候: 保存失敗、巻き戻り、再表示で値消失
- Connect
  - 正常: 接続状態更新と message が一致する
  - 異常兆候: 状態未更新、逆転表示、再実行不能
- Disconnect
  - 正常: 切断状態更新と message が一致する
  - 異常兆候: 状態未更新、逆転表示、再実行不能
- 一覧/詳細/管理パネルの状態整合
  - 正常: 同一対象の状態が3画面で一致する
  - 異常兆候: 3画面不一致、再描画後も不整合残留

---

## 本運用継続判定フェーズ 安定運用継続に進める条件（固定）

> これを満たしたら安定運用継続に進める。1項目でも未達なら継続判定は保留。

- [ ] 本運用初回監視で重大異常なし（即停止相当が1件もない）
- [ ] 一覧/詳細表示が安定（表示一致・崩れ再発なし）
- [ ] Dashboard が安定（件数・状態サマリが即時反映）
- [ ] Audit Log 更新が安定（action / target / result 欠落なし）
- [ ] Settings 保存が安定（保存反映・再表示保持・巻き戻りなし）
- [ ] Connect / Disconnect が安定（結果と状態表示一致、再実行不能なし）
- [ ] Freeze / Unfreeze が安定（confirmed 通過時のみ実行、freezeStatus 3画面一致）
- [ ] Export / Delete が安定（認証・LockGuard 条件下のみ実行、結果整合維持）
- [ ] LockGuard / 認証 / fail-safe が安定（未チェック・認証不足通過が1件もない）
- [ ] 再描画整合が保たれている（一覧・詳細・Dashboard・Audit Log が同時整合）
- [ ] 全項目を満たしたため安定運用継続へ進めると判定した

---

## 安定運用移行フェーズ 安定運用へ移行できる条件（固定）

> これを満たしたら安定運用へ移行できる。1項目でも未達なら移行判定は保留。

- [ ] 本運用初回監視で重大異常なし（即停止相当が1件もない）
- [ ] 一覧/詳細表示が安定（表示一致・崩れ再発なし）
- [ ] Dashboard が安定（件数・状態サマリが即時反映）
- [ ] Audit Log 更新が安定（action / target / result 欠落なし）
- [ ] Settings 保存が安定（保存反映・再表示保持・巻き戻りなし）
- [ ] Connect / Disconnect が安定（結果と状態表示一致、再実行不能なし）
- [ ] Freeze / Unfreeze が安定（confirmed 通過時のみ実行、freezeStatus 3画面一致）
- [ ] Export / Delete が安定（認証・LockGuard 条件下のみ実行、結果整合維持）
- [ ] LockGuard / 認証 / fail-safe が安定（未チェック・認証不足通過が1件もない）
- [ ] 再描画整合が保たれている（一覧・詳細・Dashboard・Audit Log が同時整合）
- [ ] 全項目を満たしたため安定運用へ移行できると判定した

---

## 安定運用初回レビュー フェーズ 次回レビューまでの定常監視条件（固定）

- [ ] 一覧/詳細表示整合: 同一対象の connectionStatus / freezeStatus が3画面で一致し続けるか
- [ ] Dashboard 更新: 操作後に件数・状態サマリが即時反映されるか
- [ ] Audit Log 更新: action / target / result が欠落なく追記されているか
- [ ] Settings 保存結果: 保存後の値が保持され、再表示でも一致するか
- [ ] Connect / Disconnect 結果: 実行後 connectionStatus 変更が反映され、残留・不整合がないか
- [ ] Freeze / Unfreeze 結果: confirmed 通過時のみ実行、freezeStatus 変更・復帰が3画面一致するか
- [ ] Export / Delete 結果: 認証・LockGuard 条件下のみ実行、結果と Audit Log・3画面が一致するか
- [ ] LockGuard / 認証 / fail-safe: 認証不足通過なし、LockGuard 残留なし
- [ ] message 表示内容: 操作結果と一致し、残留・逆転表示がないか
- [ ] 再描画整合: 操作後に一覧・詳細・Dashboard・Audit Log が同時整合するか
- [ ] 次回レビュー予定日を記録した

---

## 安定運用定着フェーズ 定着運用へ移行できる条件（固定）

> これを満たしたら定着運用へ移行できる。1項目でも未達なら移行判定は保留。

- [ ] 安定運用初回レビューで重大異常なし（全面停止相当が1件もない）
- [ ] 一覧/詳細表示が安定（表示一致・崩れ再発なし）
- [ ] Dashboard が安定（件数・状態サマリが即時反映）
- [ ] Audit Log 更新が安定（action / target / result 欠落なし）
- [ ] Settings 保存が安定（保存反映・再表示保持・巻き戻りなし）
- [ ] Connect / Disconnect が安定（結果と状態表示一致、残留・不整合なし）
- [ ] Freeze / Unfreeze が安定（confirmed 通過時のみ実行、freezeStatus 整合維持）
- [ ] Export / Delete が安定（認証・LockGuard 条件下のみ実行、結果整合維持）
- [ ] LockGuard / 認証 / fail-safe が安定（未チェック・認証不足通過が1件もない）
- [ ] 再描画整合が保たれている（操作後の一覧・詳細・Dashboard・Audit Log 同時整合）
- [ ] 全項目を満たしたため定着運用へ移行できると判定した
