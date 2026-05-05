# Phase4.112：8件先行投入モード待機・運用保留設計

## 1. 概要

Phase4.111.2A～4.111.8A で実装した **8件先行投入モード** が現在 BLOCKED 状態にあります。  
このドキュメントは、当面の待機方針と cmoa 承認後の再開手順を固定します。

## 2. 現在の状態（Phase4.111.8A 完了時点）

| 項目 | 値 |
|------|-----|
| **最終コミット** | 712b78f |
| **メッセージ** | Add early 8 URL insertion mode for ebook UI |
| **HEAD / origin/main** | 712b78f1faa77d771c7763d9205eba0fa13fe106 |
| **本番反映** | BLOCKED |
| **実URL投入数** | 8件（rakuten_kobo 3, kindle 3, dmm_books 2） |
| **待機中数** | 2件（cmoa：kobo-005, kobo-009） |

## 3. BLOCKED が正常状態である理由

### 3.1 cmoa 2件が申請中

```
cmoa 承認状況:
- kobo-005: affiliate_url = https://example.invalid/dry-run/ebook-affiliate/kobo-005
            campaign_url  = #
- kobo-009: affiliate_url = https://example.invalid/dry-run/ebook-affiliate/kobo-009
            campaign_url  = #
```

両アイテムは placeholder（example.invalid）であり、PRODUCTION モードではこれを拒否します。

### 3.2 check_affiliate_links.py が placeholder 検出時に BLOCK

```python
# DRY_RUN:  example.invalid は許容 → BLOCK（他要因）
# PRODUCTION: example.invalid は拒否 → BLOCK（placeholder_not_allowed_in_production）
```

**PRODUCTION exit 0 は達成不可**（cmoa 2件が未投入の間は意図的）

### 3.3 本番反映禁止理由

```
WordPress本番反映は以下をすべて満たすまで BLOCKED:
1. store_not_allowed = 0
2. domain_not_allowed = 0
3. placeholder_not_allowed_in_production = 0  ← cmoa 2件が違反中
```

現在、cmoa 2件が条件3を違反しているため、本番反映は拒否されます。

## 4. 待機方針

### 4.1 BLOCKED 状態を維持する理由

- ✓ 8件は実URL化済みで検証完了
- ✗ cmoa 2件は承認待ちで未投入
- **結論：不完全なまま本番反映しない**

### 4.2 本番反映を禁止する条件（当面の運用ルール）

```
以下のいずれかに該当する場合は本番反映を実行してはいけない:

1. check_affiliate_links.py が BLOCK を返す
2. campaign_items.json に example.invalid が1件以上存在する
3. check_affiliate_links.py の PRODUCTION モード実行で exit code != 0
```

### 4.3 待機中の再検査頻度

- **DRY_RUN**: 問題なし（example.invalid は許容）
- **PRODUCTION**: 定期的に実行し、exit code != 0 を確認する
- **本番反映**: BLOCK が解除されるまで実行禁止

## 5. cmoa 承認後の再開手順（Phase4.113）

### 5.1 再開条件

```
以下をすべて満たしたら再開可能:

1. cmoa から「kobo-005, kobo-009 の URL承認」を取得
2. real_url_input_template.json に kobo-005, kobo-009 の実URL登録
3. campaign_items.json に kobo-005, kobo-009 の実URL反映
4. check_affiliate_links.py (PRODUCTION) で store_not_allowed=0, domain_not_allowed=0 を確認
```

### 5.2 再開手順（予定フロー）

```
Phase4.113: cmoa 2件追加投入
├─ [113-1] kobo-005, kobo-009 の実URL を取得 from cmoa
├─ [113-2] real_url_input_template.json に登録
├─ [113-3] campaign_items.json に反映
├─ [113-4] check_affiliate_links.py (PRODUCTION) で検証
├─ [113-5] store_not_allowed=0 / domain_not_allowed=0 / placeholder=0 を確認
├─ [113-6] git add / commit
├─ [113-7] git push origin main
└─ [113-8] ブラウザ実機 + スマホ幅確認
                ↓
Phase4.114: PRODUCTION exit 0 達成 → 本番反映
```

## 6. real_url_input_template.json の扱い

### 6.1 現在の状態

```
ebook-affiliate-ui/data/real_url_input_template.json
- 状態：未追跡（.gitignore 対象）
- 用途：8件の実URL テンプレート
- 役割：本コミット前の staging 用
```

### 6.2 当面の運用方針

| フェーズ | 対象 | 扱い |
|---------|------|------|
| **Phase4.111** | 8件 | テンプレート作成・検証用 |
| **Phase4.112** | 待機中 | 2件分の URL 欄を空けたまま保管 |
| **Phase4.113** | cmoa 2件 | URL 取得後に追記し、campaign_items.json 反映前に再検証 |
| **本番反映時** | 10件 | テンプレート削除（機能完全化後は不要） |

**推奨：real_url_input_template.json は local-only で保管し、Git push 対象外に**

## 7. 本番反映の最終ゲート条件

```
本番反映を実行するには以下をすべて満たすこと:

✓ check_affiliate_links.py (PRODUCTION) exit 0
✓ store_not_allowed = 0
✓ domain_not_allowed = 0
✓ placeholder_not_allowed_in_production = 0
✓ TOTAL_ITEMS = 10
✓ campaign_items.json に example.invalid なし
✓ ブラウザ実機確認完了
✓ スマホ幅（375px）目視確認完了
```

現在時点：**3項目失敗（cmoa 2件が未投入）**

## 8. メンテナー向けチェックリスト（Phase4.112 期間中）

### 定期確認（週1回推奨）

- [ ] cmoa 承認状況を確認
  - Contact: [cmoa approval contact]
  - Status URL: [if available]
- [ ] `git log --oneline | head -5` で HEAD が 712b78f であることを確認
- [ ] `python3 scripts/check_affiliate_links.py --mode PRODUCTION` を実行し exit != 0 であることを確認

### cmoa 承認取得時の緊急手順

1. kobo-005, kobo-009 の承認 URL を取得
2. `real_url_input_template.json` に追記
3. 本ドキュメントを参照し Phase4.113 へ進む
4. Phase4.113 実行前に本チェックリストを Phase4.113 向けに更新

## 9. BLOCKED が「エラー」ではなく「意図的」であることの記録

```
重要: BLOCKED は障害ではなく、設計上の正常状態です。

理由:
- 8件の実URL は検証済み・本番対応可能
- cmoa 2件の申請が保留中
- 10件すべてが投入されるまで本番反映を抑制することは意図的

BLOCKED は障害ではない。これは「未完成の機能をリリースしない」という
安全設計の一部です。
```

**誰かが「本番反映が停止している」と報告したら、このセクションを提示してください。**

## 10. Console確認とロールバック方針

### 10.1 Console確認

cmoa承認後にPhase4.113で実URLを追加投入した場合でも、
WordPress本番反映前にブラウザ実機で Console エラーなしを確認する。

確認条件:
- PCブラウザで Console エラーなし
- スマホ幅表示で Console エラーなし
- CTAクリック挙動に JavaScript 例外がない
- affiliate_url / campaign_url 反映後も CTA が意図どおり動作する

Console 確認が完了するまでは、本番反映は BLOCKED を維持する。

### 10.2 ロールバック方針

待機中またはPhase4.113再開後に問題が発生した場合は、以下の方針でロールバックする。

コミット前:
- `git restore ebook-affiliate-ui/data/campaign_items.json`
- `git restore ebook-affiliate-ui/scripts/check_affiliate_links.py`
- 必要に応じて対象設計書の変更を破棄する

コミット後:
- 対象コミットを `git revert` する
- または安全確認済みの直前コミットへ対象ファイルを戻す

ロールバック後:
- DRY_RUNを再実行する
- PRODUCTIONがBLOCKED状態へ戻ることを確認する
- WordPress本番反映が未実行であることを確認する

この方針により、cmoa承認待ち中およびPhase4.113再開後も、安全停止状態を維持できる。

## 11. 今後のマイルストーン（参考）

| フェーズ | タイミング | アクション |
|---------|-----------|-----------|
| **Phase4.112** | 現在 | 待機・運用保留（このドキュメント） |
| **Phase4.113** | cmoa 承認後 | 2件追加投入 |
| **Phase4.114** | Phase4.113 完了後 | 本番反映 |
| **事後フェーズ** | 本番反映後 | ログ記録・次プロジェクト企画 |

## 12. 質問・決定事項

- **Q**: Phase4.112 中に何かできることはあるか？
  - **A**: いいえ。cmoa 承認を待つ必要があります。
  
- **Q**: real_url_input_template.json を削除してもいいか？
  - **A**: いいえ。Phase4.113 で再利用するため、local-only で保管してください。
  
- **Q**: 8件だけで本番反映できないか？
  - **A**: いいえ。設計上、10件すべてが投入されることを前提としています（Phase4_REAL_URL_DATA_INSERTION_POLICY.md 参照）。

---

**文書作成日**: 2026-05-05  
**対象コミット**: 712b78f  
**ステータス**: BLOCKED（意図的）  
**次フェーズ**: Phase4.113（cmoa 承認後）
