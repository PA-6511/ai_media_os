# 47-C-1 公開前チェックゲート設計

**作成日**: 2026-05-18  
**ステータス**: DESIGN_PHASE  
**対象フェーズ**: 47-C（自動公開フロー検討段階）

---

## 概要

47-C の第1段階として、WordPress の下書き（draft）記事に対する **公開前品質チェックゲート** を設計する。

本ステップでは以下を確定する：

1. チェック項目の定義と判定ルール
2. チェック結果の出力形式（PASS / WARN / FAIL）
3. 判定ロジックの実装方針

**重要：この段階では公開（publish）や状態変更は行わない。判定のみ。**

---

## チェック項目と判定ルール

### 1. 本文品質チェック

| 項目                | ルール                                      | 結果     |
| ------------------- | ------------------------------------------- | -------- |
| 本文空判定          | `content.strip() == ""` → FAIL              | FAIL     |
| 極端に短い本文      | `len(content) < 100` → WARN                 | WARN     |
| 見出し（h2/h3）不足 | HTML に `<h2>` または `<h3>` がない → WARN | WARN     |

**判定ロジック**

```python
def check_content_quality(content: str) -> tuple[str, list]:
    """
    content: post.content (HTML format)
    returns: (result, details)
      result: 'PASS' | 'WARN' | 'FAIL'
      details: list of messages
    """
    issues = []
    
    # Empty content
    if not content or content.strip() == '':
        return 'FAIL', ['本文が空です']
    
    # Too short
    if len(content) < 100:
        issues.append('本文が極端に短い（100文字未満）')
    
    # Check headings
    if '<h2>' not in content and '<h3>' not in content:
        issues.append('見出し（h2/h3）が見つかりません')
    
    result = 'WARN' if issues else 'PASS'
    return result, issues
```

---

### 2. URL チェック

| 項目            | ルール                                        | 結果 |
| --------------- | --------------------------------------------- | ---- |
| 楽天 URL 存在   | `https://rakuten.co.jp` パターン → PASS     | PASS |
| DMM URL 存在    | `https://dmm.co.jp` パターン → PASS         | PASS |
| 公式リンク      | 上記以外の外部リンク 1件以上 → PASS          | PASS |
| URL なし        | 上記いずれもない → WARN                     | WARN |

**判定ロジック**

```python
def check_urls(content: str) -> tuple[str, list]:
    """
    content: post.content (HTML format)
    returns: (result, details)
    """
    details = []
    has_rakuten = 'rakuten.co.jp' in content
    has_dmm = 'dmm.co.jp' in content
    
    # Extract all hrefs
    import re
    urls = re.findall(r'href=["\']([^"\']+)["\']', content)
    external_urls = [u for u in urls if u.startswith('http')]
    
    if has_rakuten:
        details.append('楽天リンク確認')
    if has_dmm:
        details.append('DMM リンク確認')
    if external_urls and not (has_rakuten or has_dmm):
        details.append(f'外部リンク確認（{len(external_urls)}件）')
    
    # At least one URL source
    if has_rakuten or has_dmm or external_urls:
        result = 'PASS'
    else:
        result = 'WARN'
        details.append('URL が見つかりません')
    
    return result, details
```

---

### 3. CTA（Call-to-Action）チェック

| 項目              | ルール                                    | 結果 |
| ----------------- | ----------------------------------------- | ---- |
| ボタン存在        | `<button>` タグ 1件以上 → PASS           | PASS |
| リンク文言存在    | `<a>` タグ + テキストあり → PASS         | PASS |
| CTA なし          | ボタンもリンク文言もない → WARN          | WARN |

**判定ロジック**

```python
def check_cta(content: str) -> tuple[str, list]:
    """
    content: post.content (HTML format)
    returns: (result, details)
    """
    details = []
    
    has_button = '<button>' in content
    has_link_text = '<a' in content and ('</a>' in content)
    
    if has_button:
        details.append('ボタン CTA 確認')
    if has_link_text:
        details.append('リンク CTA 確認')
    
    if has_button or has_link_text:
        result = 'PASS'
    else:
        result = 'WARN'
        details.append('CTA（ボタン/リンク）が見つかりません')
    
    return result, details
```

---

### 4. PR 表記チェック

| 項目                | ルール                                              | 結果 |
| ------------------- | --------------------------------------------------- | ---- |
| 広告表記あり        | 「広告」「PR」「アフィリエイト」含む → PASS      | PASS |
| 表記なし            | 上記いずれも含まない → WARN                       | WARN |

**判定ロジック**

```python
def check_pr_notice(content: str, excerpt: str = '') -> tuple[str, list]:
    """
    content: post.content (HTML format)
    excerpt: post.excerpt (text)
    returns: (result, details)
    """
    details = []
    combined = (content + excerpt).lower()
    
    keywords = ['広告', 'pr', 'アフィリエイト', 'affiliate', '本サイトは']
    found = [k for k in keywords if k in combined]
    
    if found:
        result = 'PASS'
        details.append(f'PR 表記確認: {", ".join(found)}')
    else:
        result = 'WARN'
        details.append('PR/広告表記が見つかりません')
    
    return result, details
```

---

### 5. アイキャッチ チェック

| 項目              | ルール                    | 結果 |
| ----------------- | ------------------------- | ---- |
| アイキャッチあり  | featured_media ID > 0     | PASS |
| アイキャッチなし  | featured_media ID = 0     | WARN |

**判定ロジック**

```python
def check_featured_image(post_id: int, wp_rest) -> tuple[str, list]:
    """
    post_id: WordPress post ID
    wp_rest: WordPress REST API client
    returns: (result, details)
    """
    details = []
    
    post = wp_rest.get_post(post_id)
    featured_media_id = post.get('featured_media', 0)
    
    if featured_media_id > 0:
        result = 'PASS'
        details.append(f'アイキャッチ設定済み（ID: {featured_media_id}）')
    else:
        result = 'WARN'
        details.append('アイキャッチが未設定です')
    
    return result, details
```

---

## 最終判定ロジック

### 判定の組み合わせルール

各チェックの結果を組み合わせ、最終判定を決定する。

```python
def aggregate_check_results(checks: dict) -> str:
    """
    checks: {
        'content_quality': 'PASS'|'WARN'|'FAIL',
        'urls': 'PASS'|'WARN',
        'cta': 'PASS'|'WARN',
        'pr_notice': 'PASS'|'WARN',
        'featured_image': 'PASS'|'WARN',
    }
    returns: 'PASS_ALL' | 'PASS_WITH_WARNS' | 'FAIL'
    """
    has_fail = any(v == 'FAIL' for v in checks.values())
    has_warn = any(v == 'WARN' for v in checks.values())
    
    if has_fail:
        return 'FAIL'
    elif has_warn:
        return 'PASS_WITH_WARNS'
    else:
        return 'PASS_ALL'
```

| 最終判定          | 条件                              | 備考                           |
| ----------------- | --------------------------------- | ------------------------------ |
| `PASS_ALL`        | すべて PASS                       | 理想的な状態                   |
| `PASS_WITH_WARNS` | PASS が多く、WARN が 1～4件     | 軽微な問題あり（推奨: 修正）   |
| `FAIL`            | 1件以上の FAIL                   | 公開不可                       |

---

## 出力フォーマット

### JSON 出力例

チェック結果は JSON で記録する。

```json
{
  "post_id": 12345,
  "post_title": "セール情報：〇〇",
  "check_timestamp": "2026-05-18T14:30:00Z",
  "checks": {
    "content_quality": {
      "result": "PASS",
      "details": []
    },
    "urls": {
      "result": "PASS",
      "details": ["楽天リンク確認", "外部リンク確認（3件）"]
    },
    "cta": {
      "result": "PASS",
      "details": ["ボタン CTA 確認"]
    },
    "pr_notice": {
      "result": "WARN",
      "details": ["PR/広告表記が見つかりません"]
    },
    "featured_image": {
      "result": "PASS",
      "details": ["アイキャッチ設定済み（ID: 9876）"]
    }
  },
  "final_result": "PASS_WITH_WARNS",
  "recommendation": "修正推奨（PR表記の追加）"
}
```

---

## 実装方針

### 47-C-2 Dry-Run 実装の入力

上記ロジックを基に、`tools/check_wp_draft_prepublish.py` を実装する。

```python
# tools/check_wp_draft_prepublish.py
"""
公開前下書きチェック（dry-run / 自動公開なし）

実行モード:
  - list: 未公開 draft を一覧
  - check: 指定 post_id のチェック実行
  - report: JSON 出力

実行例:
  python tools/check_wp_draft_prepublish.py list
  python tools/check_wp_draft_prepublish.py check --post-id 12345
  python tools/check_wp_draft_prepublish.py report --output report.json
"""
```

### テスト計画（47-C-2）

- 本文空のdraft をチェック（FAIL 期待）
- 100文字未満のdraft をチェック（WARN 期待）
- 見出しなしのdraft をチェック（WARN 期待）
- URL なしのdraft をチェック（WARN 期待）
- すべての条件を満たす draft をチェック（PASS_ALL 期待）

---

## 重要な制限事項

**47-C-1 の範囲外（絶対に実装しない）**

- ❌ `publish` への状態変更
- ❌ WordPress 記事の編集・更新
- ❌ 自動投稿・自動公開
- ❌ Sheets への書き込み
- ❌ Slack への通知（チェック結果のみ可）

---

## 次の段階へ

### 47-C-2 で実装するもの

1. `check_wp_draft_prepublish.py` 実装
2. dry-run テスト（3～5日連続実行）
3. チェック結果ログの収集と分析

### 47-C-3 で実装するもの

1. 人間確認フロー（Slack 通知 + 人手による LGTM）
2. 承認後の draft → publish フロー（ここで初めて publish）

---

## 参考資料

- Phase 47-B dry-run 継続観測中
- AUTO_COLLECTION_QUEUE_DESIGN.md（自動キュー登録の設計）
- ENQUEUE_47C_DESIGN.md（キュー管理スクリプトの設計）

---

**次のマイルストーン**: 47-C-2 dry-run 実装開始（5月20日目安）
