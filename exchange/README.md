# Exchange Interface for Local Self-Builder and Ebook Affiliate Block AI

## Purpose

This directory defines the limited connection interface between:

- local_self_builder
- core_consensus_ai
- ebook_affiliate_block
- human_review

This interface is for CONNECTION_TEST and DRY_RUN only.

---

## Connection Flow

```
[local_self_builder]
  Receives improvement request from human / Core AI / ebook_affiliate_block
  Generates: patch_proposal, test_report, decision_package
          ↓
[core_consensus_ai / consensus_ai]
  Judges: safety, policy risk, priority
  Output: PASS / WARN / FAIL / ABORT
          ↓
[human_review]
  Human approval gate (mandatory)
  Options: APPROVE_DRY_RUN_ONLY / REQUEST_FIX / REJECT / ABORT
          ↓
[ebook_affiliate_block]
  Receives approved candidates only
  Does NOT auto-execute: drafts, data updates, CTA changes, rankings
          ↓
[GitHub Actions / WordPress / Slack]
  Scheduled execution / draft post / notification
  (Triggered only after APPROVE + human_review)
```

---

## Fixed Safety Parameters

| Parameter | Value |
|-----------|-------|
| MODE | CONNECTION_TEST |
| EXECUTION | DRY_RUN |
| HUMAN_APPROVAL_REQUIRED | true |
| AUTO_POST | false |
| AUTO_UPDATE | false |
| AUTO_DELETE | false |
| AUTO_EXPORT | false |

---

## Allowed Operations

- observe
- analyze
- propose
- draft
- test
- report
- send_to_human_review

## Forbidden Operations

- WordPress production post
- WordPress production update
- article deletion
- external export
- cron modification
- .env modification
- secrets or credentials access
- affiliate link mass replacement
- write outside allowed exchange directory

---

## Required Files

| File | Role |
|------|------|
| exchange/incoming/decision_package.example.json | AI間接続の判定パッケージ |
| exchange/incoming/patch_proposal.example.json | 修正・改善提案 |
| exchange/incoming/test_report.example.json | テスト・検証結果 |
| exchange/human_review/review_required.example.json | 人間承認リクエスト |
| exchange/logs/connection_test_result.example.json | 接続試験ログ |

---

## Decision Status

| Status | Meaning |
|--------|---------|
| PASS | 問題なし、次ステップへ進める |
| WARN | 要確認、human_review 必須 |
| FAIL | 修正が必要、再試験まで進めない |
| ABORT | 即停止。次ステップへは進まない |

---

## Immediate ABORT Conditions

Abort immediately if any of the following is detected:

- auto_post=true
- auto_update=true
- auto_delete=true
- auto_export=true
- human_approval_required=false
- execution=LIVE
- access to .env / secrets / credentials
- WordPress production write request
- article deletion request
- external export request
- write outside allowed directories
- missing test_report
- missing decision_package

---

## Current Phase

- 限定接続インターフェース作成: GO
- 本番反映: NO-GO
- 次ステップ: 受信バリデータ作成
