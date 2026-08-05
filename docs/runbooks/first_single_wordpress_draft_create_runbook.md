# Phase 6-8 初回1件限定 WordPress実下書き作成ランブック

## 1. Purpose
This runbook defines pre-release hardening checks for a future controlled single-item WordPress draft creation process.

## 2. Current Status
Production status: NO_GO
Current phase does not allow WordPress write execution.
AUTO_POST=false
AUTO_UPDATE=false
AUTO_DELETE=false
AUTO_EXPORT=false
HUMAN_APPROVAL_REQUIRED=true
execution=DRY_RUN
publish_allowed=false
wordpress_write_executed=false
max_items=1
APPROVE_DRAFT_CREATE_ONLY is reserved for future controlled unlock only.

## 3. Absolute NO-GO
If any mismatch is detected, immediately freeze and stop.
No publish, no update, no delete, no export, and no automated escalation are allowed.

## 4. Required Preconditions
- Phase 6-5 execution spec PASS
- Phase 6-6 quality gate PASS or acceptable WARN reviewed by human
- Phase 6-7 Slack approval DRY_RUN PASS
- Phase 6-9 preflight gate PASS
- Target item count equals 1
- Duplicate check passed
- PR notice exists
- CTA URL exists
- affiliate link uses https
- rollback/freeze path exists
- human approval evidence exists

## 5. GO Conditions
All required preconditions are satisfied and documented.
All safety flags remain NO_GO and all forbidden operations remain disabled.

## 6. NO-GO Conditions
Any missing evidence, safety mismatch, or dangerous flag change causes immediate NO-GO.
Any request for publish/update/delete/export causes immediate NO-GO.

## 7. Execution Scope
- Only one item
- Draft creation only in future unlock
- No publish
- No update
- No delete
- No export
- No bulk run
- No retry storm
- No automatic escalation

## 8. Operator Checklist
- Confirm phase logs for 6-5, 6-6, 6-7, and 6-9.
- Confirm target item count is exactly one.
- Confirm PR notice and CTA/affiliate URLs are valid https links.
- Confirm freeze and rollback path are ready before any future unlock.

## 9. Evidence Checklist
- Validation outputs for all required phases are present.
- Human approval record is present and verifiable.
- Candidate payload is immutable and traceable.

## 10. Freeze / Rollback
- freeze flag を立てる
- Slack通知はDRY_RUNまたは手動
- 証跡JSONを保存
- 該当候補を再実行不可にする
- 人間レビューまで停止

## 11. Post-run Review
Review outcomes, mismatches, and operational notes.
Re-verify that production safety flags remain unchanged.

## 12. Next Step
Proceed only to Phase 7 design and controlled preparation work.
