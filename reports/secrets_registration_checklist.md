# ai_media_os GitHub Actions Secrets 登録チェックリスト

## 0) 実施情報
- 実施日: 2026-04-12
- 実施者: 運用担当（GitHub Actions Secrets 登録）
- 対象リポジトリ: ai_media_os
- 確認者: 運用レビュー担当

---

## 1) 登録前確認
- [ ] 対象リポジトリ ai_media_os を開いた
- [ ] `Settings → Secrets and variables → Actions` を開いた
- [ ] GitHub Actions 用の Secrets 登録作業であることを確認した
- [ ] 値そのものは表示・共有しない運用で進めることを確認した
- [ ] 今回の登録対象が必須4件であることを確認した
- [ ] 旧名を使わず、新名称へ統一することを確認した

### 対象4件（名称のみ）
- [ ] `WP_BASE_URL`
- [ ] `WP_USERNAME`
- [ ] `WP_APP_PASSWORD`
- [ ] `SLACK_WEBHOOK_URL`

### 旧名（使用禁止）
- [ ] `WORDPRESS_URL` を使わない
- [ ] `WORDPRESS_USER` を使わない
- [ ] `WORDPRESS_APP_PASSWORD` を使わない
- [ ] `WP_URL` を使わない

---

## 2) 登録作業
- [x] `WP_BASE_URL` を Secret として登録した
- [x] `WP_USERNAME` を Secret として登録した
- [x] `WP_APP_PASSWORD` を Secret として登録した
- [x] `SLACK_WEBHOOK_URL` を Secret として登録した
- [x] 登録時に値をチャット・メモ・チケットへ貼っていない

---

## 3) 登録後確認
- [x] Secrets 一覧に必須4件がすべて表示されている
- [x] 名称の綴りが完全一致している
- [x] 旧名での登録が存在しないことを確認した
- [x] 値は共有していない（名称のみで確認した）
- [x] GitHub Actions Secrets 登録に限定した作業であることを再確認した

### 表示確認チェック
- [x] `WP_BASE_URL`
- [x] `WP_USERNAME`
- [x] `WP_APP_PASSWORD`
- [x] `SLACK_WEBHOOK_URL`

## 3.5) 登録後の反映確認
- [x] `reports/preflight_checklist.md` の Secrets / Variables 項目を更新した
- [x] 第10.5弾 実環境確認シートを更新した
- [x] `Conditional Go / Go` 判定への影響を確認した

---

## 4) 登録後報告テンプレート

### 確認した Secrets
- `WP_BASE_URL`: あり
- `WP_USERNAME`: あり
- `WP_APP_PASSWORD`: あり
- `SLACK_WEBHOOK_URL`: あり

### 確認した Variables
- `WP_DRY_RUN`

### 不足していたもの
- なし（今回の必須4件）

### 名称ゆれ・整理候補
- なし
- 検出した旧名（あれば記載）:
  - `WORDPRESS_URL`
  - `WORDPRESS_USER`
  - `WORDPRESS_APP_PASSWORD`
  - `WP_URL`

---

## 5) 注意事項
- 値をチャットやメモに貼らない
- 値の共有はしない（名称のみ扱う）
- 旧名は使わない
- 新名称へ統一する
- 登録後に preflight を更新する

---

## 6) 完了判定
- [x] 必須4件の登録が完了した
- [x] 旧名の混入がない
- [x] preflight / 第10.5弾へ反映済み
- [x] Secrets 登録作業は完了と判断する

### 備考
- 値は扱わず、名称のみで更新。
