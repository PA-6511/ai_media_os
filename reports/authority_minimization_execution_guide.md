# 権限最小化確認：実行ガイド

## 概要
ai_media_os の最終 Go/No-Go 判定に向けて「権限最小化の実画面確認」を実施するためのガイド。

**目的:** GitHub、WordPress、Slack の実際の管理画面を見て、使用している認証情報の権限が最小化されているか確認し、結果を運用文書に反映する。

**合計所要時間:** 約 20分

---

## 準備物

1. **GitHub アカウント**（リポジトリオーナーまたは管理者）
2. **WordPress 管理画面へのアクセス**
3. **Slack ワークスペース管理者アカウント**
4. **提供ドキュメント**
   - `reports/authority_minimization_checklist.md` ← **主ドキュメント**（これに記入）
   - `reports/authority_minimization_analysis.md` ← 参考資料（確認方法の詳細）

---

## 実行フロー

### ステップ 1: チェックリストを開く（1分）

ファイル: `reports/authority_minimization_checklist.md`

- [ ] ファイルを VS Code で開いた
- [ ] 項目 1〜7 の構成を確認した
- [ ] 実画面確認中に記入・更新することを予定した

---

### ステップ 2: GitHub Actions 権限を確認（5分）

**確認場所:** GitHub Repository → Settings → Actions

#### 2-1. Default permissions を確認

1. GitHub のリポジトリページにアクセス
2. **Settings** → **Actions** → **General** を開く
3. **Permissions** セクションで **Default permissions** を確認
4. チェックリストの **1-1. Repository Settings確認** に記入
   - デフォルト権限がなんか記入
   - 権限レベル（Read-only / Read and write / Admin）を選択

#### 2-2. python-check.yml の permissions を確認

1. `.github/workflows/python-check.yml` をテキストエディタで開く
2. ファイルの先頭から `permissions:` で始まるセクションを探す

**確認パターン:**
- Pattern A: 以下のように `permissions: read` が明示されている
  ```yaml
  permissions:
    contents: read
  ```
  → チェックリスト **1-2** で「permissions 宣言あり」を選択

- Pattern B: `permissions:` セクションが存在しない
  → チェックリスト **1-2** で「permissions 宣言なし」を選択

#### 2-3. 結論（GitHub）

チェックリスト **1-4. 過剰権限の疑い / メモ** に記入
- [ ] 過剰権限候補なし（Admin 権限がない、read-only で明示）
- [ ] 過剰権限候補あり（Admin 権限あり、または権限不明）

---

### ステップ 3: WordPress 権限を確認（5分）

**確認場所:** WordPress 管理画面 → ユーザー

#### 3-1. ユーザーロール確認

1. WordPress 管理画面にログインする
2. **ユーザー** → **全ユーザー** を開く
3. **WP_USERNAME** に登録されているユーザー名を探す

   > 例: ユーザー名が `publish_bot` が WP_USERNAME の場合、ユーザー一覧から「publish_bot」を探す

4. ユーザー名をクリック → 詳細画面を開く
5. **ロール** 欄でロールを確認
   - 表示例: **Administrator** / **Editor** / **Author** など

#### 3-2. チェックリストに記入

チェックリスト **2-1. WordPress ユーザー情報確認** に記入
- [ ] WP_USERNAME 確認
- [ ] ロール確認（Admin / Editor / Author など）

#### 3-3. 権限判定

チェックリスト **2-2. 実装で必要な機能と権限の対応確認** を参考に判定
- Author ロール以上 → 十分・適切 ✓
- Administrator ロール → 過剰権限 ⚠

チェックリスト **2-4. 過剰権限の疑い / メモ** に記入

---

### ステップ 4: Slack webhook を確認（5分）

**確認場所:** Slack ワークスペース管理 → Apps → Incoming Webhooks

#### 4-1. Incoming Webhooks ページへアクセス

1. Slack ワークスペースのクイックリンクで **Apps** または**Customize Slack** を開く
2. **Apps & integrations** → **Manage** を選択
3. 左側サイドバーで **Incoming Webhooks** を開く

#### 4-2. SLACK_WEBHOOK_URL の接続先を特定

1. Incoming Webhooks の登録済み一覧から SLACK_WEBHOOK_URL に該当するものを探す
   - 名前: `ai_media_os` など、で検索
   - または、URL の一部が一致するものを探す（前方から数文字・後方から数文字を記憶）

   > 注記: URL 全体は記載しない。名前と用途のみ記録

2. 見つけた webhook をクリック → 詳細ページを開く
3. **Post to Channel** 欄で接続先チャンネルを確認
   - 例: `#ai-media-os-notifications` など

#### 4-3. チェックリストに記入

チェックリスト **3-1. SLACK_WEBHOOK_URL の接続先チャンネルを確認** に記入
- [ ] 接続先チャンネル確認（# を除いた名前のみ）
- [ ] 用途確認（例：「ai_media_os 運用通知専用」）

#### 4-4. チャンネルの専用性確認

1. Slack アプリ内で、接続先チャンネルを開く
2. チャンネル ヘッダー をクリック → **チャンネルの詳細** を表示
3. **説明** 欄で用途を確認
4. チャンネル内の メッセージ履歴を確認
   - ai_media_os 通知のみか
   - 複数用途の通知が混在しているか

#### 4-5. チェックリストに記入

チェックリスト **3-2 / 3-3. webhook の用途専用性** に記入
- [ ] 用途専用 webhook か / 複数用途共用か
- [ ] 用途専用チャンネル か / 共用チャンネルか

---

### ステップ 5: 結果をまとめる（5分）

#### 5-1. サマリ表を作成

チェックリスト **5-1. 確認した権限一覧** の表を埋める
- GitHub / WordPress / Slack それぞれの権限レベルと判定

#### 5-2. 過剰権限・要改善を整理

チェックリスト **5-2 / 5-3 / 5-4** に
- 過剰権限がないか
- 削除・無効化対象があるか
- その他リスク

#### 5-3. 最終判定

チェックリスト **6. 判定と次アクション** で
- preflight 更新可能か判定
- 要改善仕が あるか記録

---

## チェックリスト記入例

### GitHub (OK の場合)
```
- [x] Default permissions を確認した
  - 実際の設定内容: Read-only
  - 権限レベル: [x] Read-only

- [x] Workflow permissions が設定されているか確認
  - [x] 設定なし（デフォルト）

- [x] workflow に explicit permissions 宣言あり
  - 宣言内容: contents: read
```

### WordPress (過剰権限発見の場合)
```
- [x] ユーザー名を確認した
  - ユーザー名: publish_bot

- [x] ロール（権限）を確認した
  - 設定ロール: [x] Administrator

- [x] WordPress ユーザーが Admin ロールではない
  ... (以下省略)

### 過剰権限の疑い / メモ
- [x] Administrator ロール が設定されている
  - 是正必要: 権限を Author または Editor に変更する
```

### Slack (OK の場合)
```
- [x] webhook の接続先チャンネルを確認した
  - 接続先チャンネル: #ai-media-os-alerts

- [x] webhook の用途を確認した
  - 用途: ai_media_os 日次レポート・アラート通知専用

- [x] 用途専用 webhook である
  - 接続元: ai_media_os 本体

- [x] 用途専用チャンネル である
  - チャンネル用途: ai_media_os 運用通知のみ
```

---

## 承認後の次ステップ

### Case 1: すべて OK（権限が最小化されている）

1. チェックリスト **5-2** で「過剰権限なし」を確認
2. チェックリスト **6-1** で「preflight 更新可」と判定
3. 以下のコマンドで preflight_checklist.md を更新：

```bash
# preflight_checklist.md の対象行を更新
# 検索: 権限が最小化されている
# 置換: [ ] → [x]
# 根拠も追記
```

4. コミット＆プッシュ

```bash
git add reports/authority_minimization_checklist.md
git add reports/preflight_checklist.md
git commit -m "Confirm authority minimization - all systems meet minimum privilege requirements"
git push
```

### Case 2: 改善が必要（WordPress Admin など）

1. 過剰権限を特定
2. 是正を実施
   - 例: WordPress Admin ロール → Author に変更
3. 是正完了後、再度カテゴリ 1-5 を実施
4. コミット＆プッシュ

---

## トラブルシューティング

### Q: WP_USERNAME に該当するユーザーが見つからない
**A:**
- [ ] 別のユーザー名で登録されていないか確認
- [ ] WordPress 管理画面 → ユーザー ですべてのユーザーをリストアップ
- [ ] 対応疑わしいユーザーの ユーザー ID フィールドを確認

### Q: GitHub Settings → Actions が見つからない
**A:**
- [ ] リポジトリのオーナーまたは管理者権限があるか確認
- [ ] Repository → Settings が開けるか確認
- [ ] 新ブラウザタブで `https://github.com/<owner>/<repo>/settings/actions` に直接アクセス

### Q: Slack webhook を見つけられない
**A:**
- [ ] ワークスペース管理者権限があるか確認（必須）
- [ ] Slack App Directory から「Incoming Webhooks」を検索
- [ ] Webhook 名が保存されていれば検索可能

---

## 記録習慣

実施後の記録方法：

1. **ファイル保存**
   ```bash
   git add reports/authority_minimization_checklist.md
   git commit -m "Run authority minimization check - YYYY-MM-DD"
   git push
   ```

2. **preflight_checklist.md への反映**
   - Case 1 (OK)：対象行を [ ] → [x] に更新 + 根拠記載
   - Case 2 (改善)：改善完了後に再実施

3. **final_go_nogo_template.md への連動**
   - 権限最小化が完了 → Go 判定の条件 1/3 達成

---

## クイックチェック（判断用）

実施直後、以下で「OK」を確認：

```
- [ ] GitHub: read-only 権限で、unnecessary な admin 権限がない
- [ ] WordPress: Admin ロール以下（Editor または Author）
- [ ] Slack: 用途専用 webhook・チャンネルで共用なし
- [x] 三者すべて「最小権限」と判定できた
```

**判定:** 🟢 Go 条件 1/3 達成 → preflight 更新可能

---

## 参考ドキュメント

- `reports/authority_minimization_checklist.md` - 詳細チェックリスト
- `reports/authority_minimization_analysis.md` - コード分析・参考資料
- `reports/preflight_checklist.md` - Go/No-Go 判定チェックリスト
- `reports/final_go_nogo_template.md` - 最終判定テンプレート

---

**実施準備ができたら、チェックリストを開いて実行を開始してください。**
