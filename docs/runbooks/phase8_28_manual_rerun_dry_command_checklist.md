# Phase 8-28 Manual Rerun Dry Command Checklist

## 1. Purpose
- Fix the dry manual command checklist before any rerun attempt.

## 2. Current Status
- This checklist is not execution permission.
- Current status: DRY_CHECKLIST_ONLY_NO_EXECUTION

## 3. Why Commands Are Not Executed Here
- Commands must not be executed in Phase 8-28.
- This phase only validates manual rerun boundaries.

## 4. Required Prior Evidence
- exchange/logs/phase8_27_credential_ready_reevaluation_sequence.json
- exchange/logs/phase8_26_credential_provisioned_declaration_result.json

## 5. Manual Rerun Command Sequence
- python3 scripts/validate_phase8_6_wordpress_credentials_readiness.py
- python3 scripts/validate_phase8_7_rerun_approval_review.py
- python3 scripts/validate_phase8_8_final_credentialed_live_preflight.py
- python3 scripts/run_phase8_9_first_one_item_wordpress_draft_create_rerun.py
- python3 scripts/generate_phase8_10_post_rerun_closure_report.py

## 6. One-Time Execution Boundary
- HUMAN_APPROVAL_REQUIRED=true
- target_item_count=1
- commands_executed_in_this_phase=false
- Rerun count is limited to one explicit operator-triggered run.

## 7. WordPress API Boundary
- WordPress API must not be called in Phase 8-28.
- WordPress draft creation must not occur in Phase 8-28.

## 8. Secret Safety Rules
- secret_values_written=false
- Do not print WORDPRESS_APP_PASSWORD.
- Do not write secrets into this repository.
- Do not create or edit .env automatically.
- Forbidden command patterns include: curl -X POST, curl -u, requests.post(, wp-json/wp/v2/posts, export WORDPRESS_APP_PASSWORD=, WORDPRESS_APP_PASSWORD=

## 9. Publish/Update/Delete Prohibitions
- publish_allowed=false
- auto_post=false
- auto_update=false
- auto_delete=false
- auto_export=false
- Publish, update, delete, bulk, and export are prohibited.

## 10. Operator Checklist
- Confirm no command execution occurs in this phase.
- Confirm no WordPress API call occurs in this phase.
- Confirm no secret value is logged or written.
- Confirm single-item boundary remains fixed.

## 11. Freeze Conditions
- Freeze if any command is executed in this phase.
- Freeze if any secret-like value is detected.
- Freeze if any WordPress API mutation pattern is found.

## 12. Evidence Requirements
- Save validation output JSON and Markdown under exchange/logs.
- Keep evidence immutable for this phase boundary.

## 13. Final Judgment
- PASS_DRY_COMMAND_CHECKLIST_ONLY is required before Phase 8-29.
