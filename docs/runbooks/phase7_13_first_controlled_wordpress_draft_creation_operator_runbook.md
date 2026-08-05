# Phase 7-13 First Controlled WordPress Draft Creation Operator Runbook

## 1. Purpose
- Prepare the operator process for a future single controlled WordPress draft creation.
- Current phase is documentation and validation only.

## 2. Current Status
- Production status: NO_GO
- Current phase does not execute WordPress write.
- APPROVE_DRAFT_CREATE_ONLY is not active in Phase 7-13.

## 3. Absolute NO-GO Until Explicit Approval
- Do not publish.
- Do not update existing posts.
- Do not delete posts.
- Do not run bulk execution.

## 4. Required Preconditions
- HUMAN_APPROVAL_REQUIRED=true
- target_item_count=1
- phase7_14 final status must be reviewed before any future unlock request.

## 5. Human Approval Requirements
- Human approval file must be explicitly prepared in a future phase.
- Approval must remain review-only until final preflight completes.

## 6. Allowed Scope After Future Approval
- Scope is only one item draft creation candidate after explicit human approval.
- No publish or update permissions are included.

## 7. Blocked Operations
- AUTO_POST=false
- AUTO_UPDATE=false
- AUTO_DELETE=false
- AUTO_EXPORT=false
- publish_allowed=false
- wordpress_write_executed=false
- wordpress_api_call_allowed=false
- WordPress REST API POST is not allowed in Phase 7-13.

## 8. Single Item Execution Checklist
- Verify candidate_id is fixed to one reviewed item.
- Verify all safety flags remain NO_GO/false.
- Verify acknowledgement records are complete.

## 9. Pre-execution Verification
- Re-check policy and evidence consistency.
- If any mismatch is detected, immediately freeze and stop.

## 10. Execution Command Placeholder
- DRY_RUN_PLACEHOLDER_ONLY: future command must be reviewed in Phase 8 before execution.

## 11. Evidence Checklist
- Keep decision logs, validation logs, and runbook validation logs.
- Preserve all evidence files under exchange/logs.

## 12. Freeze Conditions
- Any status mismatch in prerequisite evidence.
- Any unexpected flag change from false/NO_GO.

## 13. Rollback / Manual Cleanup
- Since this phase does not execute writes, rollback is evidence correction and freeze confirmation only.

## 14. Post-run Review
- Confirm no write execution occurred.
- Confirm all blocked operations remained blocked.

## 15. Final Judgment
- This runbook is preparation only and is not execution permission.

## 16. Next Step
- Phase 7-14 pre-live unlock final freeze/go report.
