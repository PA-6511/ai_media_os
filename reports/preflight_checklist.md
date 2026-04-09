# ai_media_os Preflight Checklist

## 概要
- 本チェックリストは、ai_media_os を運用開始する前の最終確認に使用する。
- 実装状態だけでなく、運用・保全・切り戻し・確認手順まで含めて確認する。
- 判定は Go / Conditional Go / No-Go の3段階とする。
- 運用ルール:
	- 確認できた事実だけ [x]
	- 未確認は [ ]
	- 推測では埋めない
	- 各項目に根拠を必ず残す

## Git状態
- [ ] 作業ツリーが clean である
	- 根拠: 現時点で preflight_checklist.md 自体の更新差分があるため、clean は未達扱い
	- 確認コマンド: `git status --short`

- [x] main ブランチで作業している
	- 根拠: `git branch --show-current` で main を確認
	- 確認コマンド: `git branch --show-current`

- [x] main と origin/main が一致している
	- 根拠: `git rev-list --left-right --count origin/main...HEAD` で差分なし確認済み
	- 確認コマンド: `git rev-list --left-right --count origin/main...HEAD`

- [x] 不要な一時ブランチが残っていない
	- 根拠: ブランチ一覧確認時に main のみ
	- 確認コマンド: `git branch`

- [x] 直近コミット内容が把握できている
	- 根拠: 直近コミット確認済み（例: generated local artifacts 除外関連）
	- 確認コマンド: `git log --oneline -n 5`

## 生成物の追跡除外
- [x] DB ファイルが Git 追跡対象に含まれていない
	- 根拠: `git ls-files` 確認で data/*.db の追跡なし
	- 確認コマンド: `git ls-files 'data/*.db' 'data/**/*.db' '*.db'`

- [x] ZIP archives が Git 追跡対象に含まれていない
	- 根拠: `git ls-files` 確認で data/archives/*.zip の追跡なし
	- 確認コマンド: `git ls-files 'data/archives/*.zip' '*.zip'`

- [x] logs が Git 追跡対象に含まれていない
	- 根拠: `git ls-files` 確認で data/logs/* と *.log の追跡なし
	- 確認コマンド: `git ls-files 'data/logs/*' '*.log'`

- [x] .gitignore が最新状態で反映されている
	- 根拠: `.gitignore` に `.env`, `*.db`, `*.zip`, `data/logs/`, `data/archives/` 等のルールあり
	- 確認コマンド: `sed -n '1,200p' .gitignore`

- [x] ローカル実ファイルが誤って削除されていない
	- 根拠: 代表ファイル存在確認済み（DB / ZIP / logs）
	- 確認コマンド: `ls -la data && ls -la data/archives && ls -la data/logs`

## CI/CD
- [x] GitHub Actions の最新 run が成功している
	- 根拠: Actions 画面で python-check 成功を確認済み
	- 確認方法: GitHub Actions 画面

- [x] python-check workflow が有効である
	- 根拠: `.github/workflows/python-check.yml` が存在し、Git 管理対象
	- 確認コマンド: `sed -n '1,240p' .github/workflows/python-check.yml`

- [x] Install dependencies が成功している
	- 根拠: GitHub Actions 成功画面で確認済み
	- 確認方法: GitHub Actions 画面

- [x] Python compile check が成功している
	- 根拠: GitHub Actions 成功画面で確認済み
	- 確認方法: GitHub Actions 画面

- [x] Run tests が成功している
	- 根拠: GitHub Actions 成功画面で確認済み
	- 確認方法: GitHub Actions 画面

- [x] py_compile の手動実行手順が確立している
	- 根拠: reports/core_ai_runbook.md に手順記載あり
	- 確認コマンド: `grep -n "py_compile" reports/core_ai_runbook.md`

- [x] pytest -q の手動実行手順が確立している
	- 根拠: reports/core_ai_runbook.md に手順記載あり
	- 確認コマンド: `grep -n "pytest -q" reports/core_ai_runbook.md`

## 設定と機密情報
- [ ] 本番用 Secrets / Variables が登録済みである
	- 根拠: 実環境側の最終確認未実施
	- 確認方法: GitHub / 実行環境の設定画面

- [x] ローカル用 .env は Git 非追跡である
	- 根拠: `git ls-files '.env' '.env.*'` で追跡なし
	- 確認コマンド: `git ls-files '.env' '.env.*'`

- [ ] 機密情報がコードやリポジトリに直書きされていない
	- 根拠: 最終監査未実施
	- 確認方法: 目視レビュー / 監査

- [x] 設定変更時の確認手順がある
	- 根拠: reports/core_ai_runbook.md に設定変更時の注意あり
	- 確認コマンド: `grep -n "設定変更時の注意" reports/core_ai_runbook.md`

- [ ] 権限が最小化されている
	- 根拠: Secrets / Token / deploy 権限の最終確認未実施
	- 確認方法: Secrets / Token / deploy 権限確認

## データ保全
- [x] DB バックアップ手順がある
	- 根拠: Runbook / docs 上で手順あり
	- 確認方法: Runbook / docs

- [x] バックアップ保存先が決まっている
	- 根拠: 文書上で確認可能
	- 確認方法: Runbook / docs

- [ ] 保持期間が決まっている
	- 根拠: 明文化未確認
	- 確認方法: Runbook / docs / 運用ルール

- [x] 復元手順がある
	- 根拠: Runbook / docs 上で確認可能
	- 確認方法: Runbook / docs

- [ ] 少なくとも1回は復元確認または手順確認を実施した
	- 根拠: 実施記録未確認
	- 確認方法: 実施記録 / 作業ログ

## 監視と運用
- [x] retry queue の確認手順がある
	- 根拠: reports/core_ai_runbook.md に記載あり
	- 確認コマンド: `grep -n "retry queue" reports/core_ai_runbook.md`

- [x] freeze 時の対応手順がある
	- 根拠: reports/core_ai_runbook.md に freeze / 異常時対応あり
	- 確認コマンド: `grep -n "freeze" reports/core_ai_runbook.md`

- [x] ログ確認手順がある
	- 根拠: reports/core_ai_runbook.md にログ確認手順あり
	- 確認コマンド: `grep -n "ログ確認" reports/core_ai_runbook.md`

- [x] ログ肥大化対策がある
	- 根拠: logs のローテーション済みファイル存在と運用文書確認
	- 確認方法: Runbook / ログ運用方針

- [x] 障害時の一次切り分け手順がある
	- 根拠: Runbook に一次切り分け手順あり
	- 確認方法: Runbook

- [x] 定期ジョブの稼働確認方法がある
	- 根拠: Runbook / 運用手順上で確認可能
	- 確認方法: Runbook / 運用手順

## リリース運用
- [x] Go / No-Go 判定基準がある
	- 根拠: preflight checklist 自体に判定欄あり
	- 確認方法: reports/preflight_checklist.md

- [x] rollback 手順がある
	- 根拠: reports/core_ai_runbook.md に切り戻し手順あり
	- 確認コマンド: `grep -n "切り戻し手順" reports/core_ai_runbook.md`

- [ ] 初回運用日の担当者が決まっている
	- 根拠: 未確認
	- 確認方法: 運用計画

- [ ] 連絡フローが決まっている
	- 根拠: 未確認
	- 確認方法: 運用計画

- [x] 初回運用時の監視ポイントが明確である
	- 根拠: Runbook / preflight に確認項目あり
	- 確認方法: Runbook / preflight

## Go / No-Go 判定
- 判定: [ ] Go  [x] Conditional Go  [ ] No-Go
- 判定日: 2026-04-09
- 判定者:
- 備考:
	- Go にするための残条件:
		- Secrets / Variables の最終確認
		- 権限最小化の確認
		- バックアップ保持期間の明文化
		- 復元確認の実施記録
		- 初回運用日の担当者・連絡フロー確定
	- 未確認の重要項目:
		- 本番用 Secrets / Variables
		- 権限
		- 運用体制
	- 初回運用日までに埋める項目:
		- 当日 py_compile / pytest 実行結果
		- retry queue / 主要ログ確認
		- rollback / 連絡フロー再確認
	- 第10弾反映（2026-04-09）:
		- 文書上で確認可能な項目のみ更新（復元手順文書化、rollback 条件、当日ログ/queue 確認項目）。
		- Secrets/Variables、権限、担当者/連絡フロー、保持期間、復元実施記録は未確認のため [ ] 維持。

## 初回運用日の確認項目
- [ ] 運用開始前に `python3 -m py_compile $(find . -name "*.py")` を実行した
	- 根拠:

- [ ] 運用開始前に `pytest -q` を実行した
	- 根拠:

- [ ] retry queue の状態を確認した
	- 根拠:

- [ ] 主要ログを確認した
	- 根拠:

- [ ] rollback 手順を再確認した
	- 根拠:

- [ ] 連絡フローを再確認した
	- 根拠:

## 第10弾：未確認項目を埋めるための実環境確認リスト

### 目的
- reports/preflight_checklist.md で [ ] のまま残っている項目を、実環境で順に確認して埋める。
- 特に重要な4領域に絞って確認する。
	- Secrets / Variables
	- 権限最小化
	- データ保全
	- 初回運用体制

### 1. Secrets / Variables 確認

確認したいこと:
- 本番運用に必要な Secrets / Variables が揃っているか
- 未使用の古い値が残っていないか
- 値の用途が分かるか

チェック項目:
- [ ] GitHub Actions / 実行環境で必要な Secrets が登録済み
- [ ] Variables が登録済み
- [ ] 名前だけで用途が分かる
- [ ] 不要な古い値が残っていない
- [ ] 本番値とテスト値が混ざっていない

確認結果メモ:
- GitHub Settings 画面での最終確認は未実施（この作業環境では CLI 連携未設定）。

見る場所:
- GitHub Repository -> Settings -> Secrets and variables -> Actions
- サーバ側 .env や運用メモがあるならそこも確認

埋めるメモ例:
- Secrets:
	- WORDPRESS_URL
	- WORDPRESS_USER
	- WORDPRESS_APP_PASSWORD
	- SLACK_WEBHOOK_URL
	- RAKUTEN_APP_ID
	- AMAZON_PAAPI_KEY
- Variables:
	- WP_DRY_RUN
	- LOG_LEVEL

### 2. 権限最小化の確認

確認したいこと:
- 使っている token や接続先が、必要以上の権限を持っていないか
- 使っていない接続が生きていないか

チェック項目:
- [ ] GitHub token / Actions 権限が必要最小限
- [ ] WordPress 接続権限が必要最小限
- [ ] Slack webhook が用途限定
- [ ] API キーが読み書き不要な範囲で絞られている
- [ ] 使っていない token / key が削除済み

確認結果メモ:
- Secrets / token / webhook の実環境権限確認は未実施（管理画面での確認が必要）。

確認の観点:
- 書き込み権限が本当に必要か
- 管理者権限が過剰でないか
- 失効・再発行しやすい形になっているか

### 3. データ保全の確認

確認したいこと:
- バックアップ手順があるだけでなく、保管先・保持期間・復元確認が決まっているか

チェック項目:
- [ ] DB バックアップ保存先が決まっている
- [ ] 保持期間が決まっている
- [ ] バックアップ頻度が決まっている
- [x] 復元手順が文書化されている
- [ ] 少なくとも1回は復元確認または手順確認をした

確認結果メモ:
- `reports/core_ai_runbook.md` の「切り戻し手順」に復元手順の記載あり。
- 保持期間・頻度・復元実施記録は未確認。

埋めるメモ例:
- 保存先:
	- VPS local: /home/deploy/backups/
	- Secondary: NAS / external storage
- 保持期間:
	- Daily: 7日
	- Weekly: 4週
	- Monthly: 3か月

### 4. 初回運用体制の確認

確認したいこと:
- 初回運用日に誰が見るか
- 異常時に誰へ連絡するか
- 何をもって Go / Stop を決めるか

チェック項目:
- [ ] 初回運用日の担当者が決まっている
- [ ] 連絡フローが決まっている
- [ ] 異常時の一次判断者が決まっている
- [x] rollback 判断条件が明確
- [x] 当日確認するログと queue が決まっている

確認結果メモ:
- `reports/core_ai_runbook.md` の「freeze / 異常時対応」に復旧判断条件あり。
- `reports/core_ai_runbook.md` の「retry queue 確認手順」「ログ確認手順」「運用前チェック Top3」に当日確認項目あり。
- 担当者・連絡フロー・一次判断者は未確認。

埋めるメモ例:
- 担当者:
	- 初回監視: 自分
	- 異常時判断: 自分
	- 連絡先: Slack / メモ
- 当日見るもの:
	- pytest -q
	- py_compile
	- retry queue
	- pipeline_failures.log
	- combined_signal.log

### 5. 判定更新ルール

Conditional Go -> Go に上げる条件:
- [ ] Secrets / Variables 確認完了
- [ ] 権限最小化確認完了
- [ ] 保持期間と復元確認が完了
- [ ] 初回運用日の担当者・連絡フロー確定

これが埋まれば、かなり自然に Go へ上げられます。

今回の更新結果:
- Conditional Go のまま（Go 条件は未充足）。

### 6. そのまま使える短い確認フォーマット

#### 第10弾 実環境確認

Secrets / Variables:
- [ ] 登録済み
- [ ] 用途明確
- [ ] 不要値なし

権限最小化:
- [ ] GitHub 権限確認
- [ ] WordPress 権限確認
- [ ] Slack / API キー権限確認

データ保全:
- [ ] 保存先確認
- [ ] 保持期間確認
- [ ] 復元確認

初回運用体制:
- [ ] 担当者決定
- [ ] 連絡フロー決定
- [ ] rollback 条件確認

判定:
- [ ] Go
- [x] Conditional Go
- [ ] No-Go

### 今のおすすめ順

この順で埋めるのが早いです。

- Secrets / Variables
- 初回運用体制
- 権限最小化
- データ保全

理由:
- 最初の2つが埋まると実運用判断がかなりしやすくなるため。

## 第10.5弾：実環境確認チェックリスト

### 目的
- reports/preflight_checklist.md で最後まで [ ] のまま残りやすい、実環境依存の項目を埋めるための確認表。
- 今回は特に以下の4つに集中する。
	- Secrets / Variables
	- 権限最小化
	- 初回運用体制
	- データ保全の残項目

### 1. Secrets / Variables

確認したいこと:
- 本番に必要な値が揃っているか
- テスト用と本番用が混ざっていないか
- 名前と用途が明確か

チェックリスト:
#### Secrets / Variables
- [ ] GitHub Actions Secrets が必要分そろっている
- [ ] GitHub Actions Variables が必要分そろっている
- [ ] 各値の用途が分かる
- [ ] 不要な古い値が残っていない
- [ ] テスト用と本番用が混在していない
- [ ] preflight 本体の「本番用 Secrets / Variables が登録済みである」を [x] に更新した

見る場所:
- GitHub -> Repository Settings -> Secrets and variables -> Actions
- VPS 側 .env や運用メモ

記録メモ欄:
- 確認した Secrets:
- 確認した Variables:
- 不足していたもの:
- 備考:

### 2. 権限最小化

確認したいこと:
- 接続先が必要以上の権限を持っていないか
- 使っていない認証情報が残っていないか

チェックリスト:
#### 権限最小化
- [ ] GitHub Actions / Token 権限が必要最小限
- [ ] WordPress 接続権限が必要最小限
- [ ] Slack webhook が用途限定である
- [ ] 外部 API キーが必要最小限の用途に限定されている
- [ ] 使っていない token / key が残っていない
- [ ] preflight 本体の「権限が最小化されている」を [x] に更新した

記録メモ欄:
- 確認した権限:
- 過剰権限の疑い:
- 削除/無効化対象:
- 備考:

### 3. 初回運用体制

確認したいこと:
- 初回運用日に誰が見るか
- 何を見て異常と判断するか
- どこへ連絡するか

チェックリスト:
#### 初回運用体制
- [ ] 初回運用日の担当者が決まっている
- [ ] 連絡フローが決まっている
- [ ] 異常時の一次判断者が決まっている
- [ ] rollback 判断条件が共有されている
- [ ] 当日見るログと retry queue が決まっている
- [ ] preflight 本体の「初回運用日の担当者」「連絡フロー」を [x] に更新した

記録メモ欄:
- 担当者:
- 異常時判断者:
- 連絡フロー:
- 当日確認対象:
- 備考:

### 4. データ保全の残項目

確認したいこと:
- 保存先と手順だけでなく、保持期間と復元確認の証跡があるか

チェックリスト:
#### データ保全（残項目）
- [ ] バックアップ保持期間が決まっている
- [ ] バックアップ頻度が決まっている
- [ ] 少なくとも1回は復元確認または手順確認を実施した
- [ ] 実施記録が残っている
- [ ] preflight 本体の「保持期間」「復元確認または手順確認を実施した」を [x] に更新した

記録メモ欄:
- 保持期間:
- バックアップ頻度:
- 復元確認日:
- 記録場所:
- 備考:

### 5. 判定更新ルール

Conditional Go -> Go に上げる条件:
#### 判定更新条件
- [ ] Secrets / Variables 確認完了
- [ ] 権限最小化確認完了
- [ ] 初回運用体制確認完了
- [ ] 保持期間と復元確認記録が埋まった
- [ ] preflight 本体の対応項目が [x] に更新済み

### 6. そのまま使える短い記録フォーマット

#### 第10.5弾 実環境確認

Secrets / Variables:
- [ ] 確認完了
- [ ] preflight 反映済み
- メモ:

権限最小化:
- [ ] 確認完了
- [ ] preflight 反映済み
- メモ:

初回運用体制:
- [ ] 確認完了
- [ ] preflight 反映済み
- メモ:

データ保全:
- [ ] 確認完了
- [ ] preflight 反映済み
- メモ:

判定:
- [ ] Go
- [ ] Conditional Go
- [ ] No-Go
- 備考:

### 今のおすすめ順（第10.5弾）

最短で進めるならこの順。

- Secrets / Variables
- 初回運用体制
- 権限最小化
- データ保全（保持期間・復元記録）

理由:
- 最初の2つが埋まると Go 判定の現実味が一気に上がるため。

## 第10.5弾 実環境確認シート（現状反映版）

### 1) Secrets / Variables
- [ ] GitHub Actions Secrets が必要分そろっている
- [ ] GitHub Actions Variables が必要分そろっている
- [ ] 各値の用途が分かる
- [ ] 不要な古い値が残っていない
- [ ] テスト用と本番用が混在していない
- [ ] preflight 本体の「本番用 Secrets / Variables が登録済みである」を [x] に更新した

記録:
- 確認した Secrets: 未確認
- 確認した Variables: 未確認
- 不足していたもの: 未確認
- 備考: GitHub / 実行環境の設定画面での実確認が必要

### 2) 初回運用体制
- [ ] 初回運用日の担当者が決まっている
- [ ] 連絡フローが決まっている
- [ ] 異常時の一次判断者が決まっている
- [x] rollback 判断条件が共有されている
- [x] 当日見るログと retry queue が決まっている
- [ ] preflight 本体の「初回運用日の担当者」「連絡フロー」を [x] に更新した

記録:
- 担当者: 未確認
- 異常時判断者: 未確認
- 連絡フロー: 未確認
- 当日確認対象: retry queue / pipeline_failures.log / combined_signal.log / py_compile / pytest -q
- 備考: rollback 手順と監視対象は Runbook / preflight に記載済み。担当者と連絡フローのみ未確定

### 3) 権限最小化
- [ ] GitHub Actions / Token 権限が必要最小限
- [ ] WordPress 接続権限が必要最小限
- [ ] Slack webhook が用途限定である
- [ ] 外部 API キーが必要最小限の用途に限定されている
- [ ] 使っていない token / key が残っていない
- [ ] preflight 本体の「権限が最小化されている」を [x] に更新した

記録:
- 確認した権限: 未確認
- 過剰権限の疑い: 未確認
- 削除/無効化対象: 未確認
- 備考: Secrets / Token / webhook / API キーの実環境確認が必要

### 4) データ保全（残項目）
- [ ] バックアップ保持期間が決まっている
- [ ] バックアップ頻度が決まっている
- [ ] 少なくとも1回は復元確認または手順確認を実施した
- [ ] 実施記録が残っている
- [ ] preflight 本体の「保持期間」「復元確認または手順確認を実施した」を [x] に更新した

記録:
- 保持期間: 未確認
- バックアップ頻度: 未確認
- 復元確認日: 未確認
- 記録場所: 未確認
- 備考: バックアップ/復元の手順文書はあるが、保持期間と実施記録は未確認

---

## 判定更新条件（Conditional Go → Go）
- [ ] Secrets / Variables 確認完了
- [ ] 権限最小化確認完了
- [ ] 初回運用体制確認完了
- [ ] 保持期間と復元確認記録が埋まった
- [ ] preflight 本体の対応項目が [x] に更新済み

---

## 最終判定
- [ ] Go
- [x] Conditional Go
- [ ] No-Go
- 備考:
	- Git / GitHub / Actions / .gitignore / 追跡除外 / Runbook / Preflight は整備済み
	- GitHub Actions の python-check は成功確認済み
	- DB / ZIP / logs は Git 非追跡化済み
	- Secrets / Variables、権限最小化、保持期間、復元確認記録、担当者・連絡フローは未確認
	- 上記が埋まれば Go 判定へ移行可能
