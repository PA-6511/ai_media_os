# 権限最小化確認：コード分析 + 実画面参考資料

## 目的
権限最小化の実画面確認を行う際に、コードから判明した事実と、実画面で確認すべきポイントを対応させるための参考資料。

---

## 1. WordPress 接続権限の分析

### 1-1. 実装で使用する API エンドポイント

**ファイル:** `wordpress_publisher/wp_client.py`

| エンドポイント | メソッド | 用途 | 必要権限 |
|--------|---------|------|--------|
| `/wp-json/wp/v2/posts` | GET | 既存投稿の検索・確認 | read 権限 |
| `/wp-json/wp/v2/posts` | POST | 新規投稿作成 | edit_posts 権限 |
| `/wp-json/wp/v2/categories` | GET | カテゴリ一覧取得 | read 権限 |
| `/wp-json/wp/v2/categories` | POST | カテゴリ新規作成 | manage_categories 権限 |
| `/wp-json/wp/v2/tags` | GET | タグ一覧取得 | read 権限 |
| `/wp-json/wp/v2/tags` | POST | タグ新規作成 | manage_terms 権限 |

### 1-2. WordPress ロール別権限対応

**WordPress デフォルトロール:**

| ロール | 概要 | edit_posts | manage_categories | manage_terms | 判定 |
|-------|------|-----------|------------------|------------|------|
| Administrator | 全権限 | ✓ | ✓ | ✓ | **過剰** |
| Editor | 全投稿編集・カテゴリ/タグ管理 | ✓ | ✓ | ✓ | ✓ 十分 |
| Author | 自分の投稿・c カテゴリ/タグ管理 | ✓ (自分) | ✓ | ✓ | ✓ 十分 |
| Contributor | 自分の投稿のみ（下書き） | ✓ (下書き) | ✗ | ✗ | ✗ 不足 |
| Subscriber | なし | ✗ | ✗ | ✗ | ✗ 不足 |

**推奨ロール:** Editor または Author（ただし Admin は過剰）

### 1-3. Application Password での権限制限の可能性

WordPress の Application Password では、通常ユーザーの権限が引き継がれます。
- ユーザーが Admin → Application Password も Admin 権限
- ユーザーが Author → Application Password も Author 権限

**確認必要:** 
- ユーザーがどのロール（Admin/Editor/Author）で登録されているか
- Application Password に追加の権限制限があるか（アドオン依存）

---

## 2. GitHub Actions 権限の分析

### 2-1. 実装で使用する GitHub Actions

**ファイル:** `.github/workflows/python-check.yml`

| アクション | 用途 | 必要権限 |
|----------|------|--------|
| `actions/checkout@v4` | リポジトリ取得 | contents: read |
| `actions/setup-python@v5` | Python セットアップ | なし（GitHub Actions固有） |
| `pytest / py_compile` | テスト実行 | (コンテナ内実行のため不要) |

### 2-2. GITHUB_TOKEN デフォルト権限

GitHub Actions の GITHUB_TOKEN はデフォルトで以下のスコープを持ちます。

**デフォルト（write アクティベーション時）：**
- contents: write（リポジトリコンテンツ書き込み）
- packages: write（pacakges 書き込み）
- deployments: write（デプロイメント書き込み）

**必要な権限：**
- contents: read（checkout のみ）

### 2-3. python-check.yml の current permissions 宣言

**実装内容：** `.github/workflows/python-check.yml`  には `permissions` セクションが **なし**

現在のワークフローは以下のアクションのみを実行：
- `checkout@v4` - READ のみ
- `setup-python@v5` - スタンドアローン実行（権限不要）
- `py_compile` / `pytest` - コンテナ内実行（外部権限不要）

**結論:** explicit `permissions` 宣言がなくても、このワークフローの範囲では問題ないと判断される。

### 2-4. 権限最小化の推奨状態

**現在:** `permissions` セクションなし（デフォルト動作）

**推奨:** 以下のいずれか
1. **明示的に制限する（ベストプラクティス）:**
   ```yaml
   permissions:
     contents: read
   ```
   - 理由: read-only に明示化のため、誤った権限拡張を防止

2. **現状維持（実害なし）:**
   - ワークフロー自体の範囲では追加権限を利用していないため

---

## 3. Slack webhook 権限の分析

### 3-1. SLACK_WEBHOOK_URL の用途

**ファイル:** `reports/core_ai_runbook.md` より抽出

用途: 日次リポート / 異常通知の送信

メッセージ種別:
- 日次リポート完了通知
- 異常検知時の Quick Alert
- scheduler ジョブ失敗通知

### 3-2. Webhook の権限スコープ

Slack Incoming Webhook の権限：
- **許可:** メッセージ送信（送信チャンネルのみ）
- **制限:** チャンネル作成・削除、ユーザー管理、ワークスペース設定変更など

**最小権限:** 🟢 Webhook のみでは over-privileged 不可能（設計上最小権限のみ）

### 3-3. 確認すべき項目

| 項目 | チェック内容 | 理想状態 |
|-----|----------|--------|
| 接続先チャンネル | webhook が POST するチャンネル | 用途専用チャンネル（ai_media_os 通知のみ） |
| webhook 共用性 | 複数用途で共用されているか | 用途別に分離（本来は複数 webhook） |
| チャンネル共用性 | 複数用途の通知が混在しているか | 用途別チャンネル分離（理想） |
| Active 状態 | 無制限に active なままか | 使用時のみ active（ベスト） または常時 active（許容） |

### 3-4. 現状評価

**現状：** SLACK_WEBHOOK_URL（1つの Webhook）で全通知を一元送信

**評価：**
- 権限スコープ: 🟢 Webhook レベルでは最小権限（送信のみ）
- ただし、チャンネル専用性が確認できれば「安全」と判定可能

---

## 4. 実画面確認時のチェックリスト（コード分析に基づく）

### GitHub Actions 確認項目

**確認場所:** Repository → Settings → Actions → General

```
チェック場所 1: Default permissions (GITHUB_TOKEN)
- [ ] 現状: Read-only / Read and write / Admin のいずれか
- [ ] 推奨: 明示的に制限する（後述）

チェック場所 2: Workflow permissions
- [ ] 設定あり: 内容を記録
- [ ] 設定なし: デフォルト挙動を確認

確認場所 3: .github/workflows/python-check.yml の permissions
- [ ] permissions: read
  → 理想的（explicit 宣言あり）
- [ ] permissions なし
  → 現状問題なし（checkout のみだから）、但し明示化推奨
```

### WordPress ユーザー確認項目

**確認場所:** WordPress 管理画面 → ユーザー → WP_USERNAME

```
チェック場所 1: ロール
- [ ] Administrator → ⚠ 過剰権限。是正検討
- [ ] Editor → ✓ 十分・適切
- [ ] Author → ✓ 十分・適切
- [ ] その他 → 権限を個別確認

チェック場所 2: Application Password
- [ ] 権限が制限されているか確認
- [ ] REST API スコープ確認
```

### Slack webhook 確認項目

**確認場所:** Slack 管理画面 → Apps & integrations → Incoming Webhooks

```
チェック場所 1: 接続先チャンネル
- [ ] 記録: 接続先 = #________
- [ ] 用途確認: ai_media_os 運用通知のみか、複数用途混在か

チェック場所 2: Webhook 管理
- [ ] 登録済み webhook リスト
- [ ] 本 webhook 以外に関連 webhook が無いか

チェック場所 3: チャンネルメンバー・説明
- [ ] チャンネル用途は専用か（他の通知も混在か）
- [ ] メンバー制限（閲覧権限）
```

---

## 5. コード分析に基づく事前判定

### 5-1. GitHub Actions 権限の事前判定

**コード分析:**
- ✓ 使用アクション: checkout, setup-python, pytest - すべて read-only 相当
- ✓ 外部 API 呼び出しなし（ローカルコンパイル・テストのみ）
- ✓ GITHUB_TOKEN の追加権限不要

**事前判定:** 🟢 **安全**（explicit `permissions: read` 宣言があれば理想的）

**実画面確認後の確定:** [ ] OK  [ ] 要改善

---

### 5-2. WordPress 権限の事前判定

**コード分析:**
- ✓ 使用 API: カテゴリ・タグ作成、投稿読み取り・作成
- ✓ 必要な最小権限: Author または Editor ロール

**現状推定:**
- ⚠ Administrator ロール の場合 → **過剰権限**
- ✓ Editor / Author の場合 → **適切**
- ✗ Contributor 以下の場合 → **権限不足**

**実画面確認後の確定:** [ ] OK  [ ] 要改善

---

### 5-3. Slack Web hook 権限の事前判定

**コード分析:**
- ✓ Webhook の機能: メッセージ送信のみ
- ✓ スコープ: 接続先チャンネルに限定

**要確認事項:**
- チャンネルが ai_media_os 通知専用か（複数用途混在なし）
- webhook が複数用途で共用されていないか

**事前判定:** 🟡 **要確認**

**実画面確認後の確定:** [ ] OK  [ ] 要改善

---

## 6. 実画面確認フロー（推奨順序）

### Phase 1: GitHub（5分）
1. Repository Settings → Actions → General を開く
2. Default permissions を確認し、チェックリストに記入
3. python-check.yml を表示して permissions セクションを確認

### Phase 2: WordPress（5分）
1. WordPress 管理画面 → ユーザー を開く
2. WP_USERNAME に該当するユーザーを開く
3. ロール欄で権限を確認
4. Application Password の詳細（あれば）を確認

### Phase 3: Slack（5分）
1. Slack 管理画面 → Apps &integrations を開く
2. Incoming Webhooks で SLACK_WEBHOOK_URL を検索
3. 接続先チャンネル＆用途を確認
4. チャンネル自体が専用か共用か確認

### Phase 4: 結果整理（5分）
1. 3次資料に結果を記入
2. 過剰権限の有無を判定
3. preflight_checklist.md への反映を決定

**合計時間: 約 20分**

---

## 7. 最終判定への引き継ぎ

### 事前判定結果

| サービス | 分析判定 | 実画面確認 | 最終判定 |
|----------|--------|---------|--------|
| GitHub Actions | 🟢 安全 | [ ] 確認待ち | [ ] 確定待ち |
| WordPress | 🟡 要確認 | [ ] 確認待ち | [ ] 確定待ち |
| Slack Webhook | 🟡 要確認 | [ ] 確認待ち | [ ] 確定待ち |

### preflight_checklist.md への反映条件

**対象項目:**
```
- [ ] 権限が最小化されている
```

**更新条件（すべて満たす場合）:**
1. [ ] GitHub Actions: explicit permissions あり または write 権限を利用していない
2. [ ] WordPress: Admin ロール以下（Editor または Author）
3. [ ] Slack: 用途専用 webhook・チャンネルで共用なし
4. [ ] 未使用認証情報: なし

**更新内容:**
```
- [x] 権限が最小化されている
  - 根拠: GitHub Actions は checkout のみで read-only、WordPress は Editor ロール、
          Slack webhook は用途専用チャンネル で確認済み
  - 確認日: YYYY-MM-DD
  - 確認者: [名前]
```

### 過剰権限発見時の対応

**WordPress Administrator の場合:**
- [ ] 権限ロールを Editor / Author に変更
- [ ] 変更実施日: ________
- [ ] 変更完了後に preflight 更新

**Slack webhook の共用発見の場合:**
- [ ] 用途別に webhook を分離（新規作成）
- [ ] 変更実施日: ________
- [ ] 変更完了後に preflight 更新

---

## 参考資料

### WordPress ロール・権限の公式ドキュメント
- [Roles and Capabilities - WordPress.org](https://wordpress.org/support/article/roles-and-capabilities/)
- Author / Editor / Admin の権限差分

### GitHub Actions 権限スコープ
- [Authentication in a workflow - GitHub Docs](https://docs.github.com/en/actions/security-guides/automatic-token-authentication)
- GITHUB_TOKEN のスコープと制限方法

### Slack Webhook セキュリティ
- [Incoming Webhooks - Slack API Docs](https://api.slack.com/messaging/webhooks)
- 権限スコープ・レート制限
