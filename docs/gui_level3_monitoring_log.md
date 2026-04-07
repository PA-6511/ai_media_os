# GUI Level3 監視ログ

- 監視日:

## 監視した機能

- [ ] Freeze
- [ ] Unfreeze
- [ ] 一覧表示
- [ ] 詳細表示
- [ ] Dashboard
- [ ] Audit Log 参照
- [ ] Settings 参照
- [ ] Settings 保存
- [ ] Connect
- [ ] Disconnect

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

## Level3 継続判定区分

### 継続してよい

- Freeze: confirmed 導線が維持され、freezeStatus・message・Audit Log・再描画整合が安定している
- Unfreeze: confirmed 導線が維持され、freezeStatus 復帰・message・Audit Log・再描画整合が安定している

### 条件付き継続

- Freeze: 単発の Audit Log 遅延や message 軽微不整合があるため再発監視を条件に継続
- Unfreeze: 単発の Audit Log 遅延や message 軽微不整合があるため再発監視を条件に継続
- 一覧表示/詳細表示/Dashboard/Audit Log 参照: Freeze/Unfreeze 後の巻き込み崩れ再発有無を継続監視
- Settings 参照/Settings 保存/Connect/Disconnect: Freeze/Unfreeze との干渉再発有無を継続監視

### 停止候補

- Freeze: confirmed すり抜け、freezeStatus 未反映、状態不整合、再描画崩れが再発した場合
- Unfreeze: confirmed すり抜け、freezeStatus 未復帰、状態不整合、再描画崩れが再発した場合
- 巻き込み対象（一覧表示/詳細表示/Dashboard/Audit Log 参照/Settings 参照/Settings 保存/Connect/Disconnect）: Freeze/Unfreeze 実行後に表示崩れや状態不整合が継続した場合

### Level3 判定対象外（別枠）

- Export: Level4 判定対象のため Level3 継続判定対象外
- Delete: Level4 判定対象のため Level3 継続判定対象外

## Level3 継続判定済みチェック欄

- [ ] 判定日を記録した
- [ ] 継続する機能を記録した
- [ ] 条件付き継続にする機能を記録した
- [ ] 一旦止める機能を記録した
- [ ] 継続監視項目を記録した
- [ ] 再開条件を記録した
- [ ] 次の判定タイミングを記録した

## 条件付き継続の有無

- 条件付き継続: なし / あり
- 対象機能:
- 条件内容:

## 停止対象の有無

- 停止対象: なし / あり
- 停止対象機能:
- 停止理由:

## 次回判定予定

- 次回判定日:
- 判定トリガー:
- 判定対象:
- 次回重点確認項目: