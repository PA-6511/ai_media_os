# Phase 8-31 Secret-Safe Credential Provisioning Operator Procedure

## 1. Purpose
- Provide a secret-safe operator-only procedure for manual credential provisioning outside this repository.

## 2. Current Status
- Current status: OPERATOR_HANDOFF_BLOCKED_CREDENTIALS_MISSING

## 3. Secret Handling Boundary
- This procedure is not execution permission.
- Do not print WORDPRESS_APP_PASSWORD.
- Do not print credential lengths.
- Do not print credential prefixes or suffixes.
- Do not hash credentials for logging.
- Do not mask credential values for logging.
- Allowed output is exists=true/false only.

## 4. Repository Boundary
- Do not write secrets into this repository.
- Do not create or edit .env automatically.

## 5. Environment Variable Names
- WORDPRESS_BASE_URL
- WORDPRESS_USERNAME
- WORDPRESS_APP_PASSWORD

## 6. Manual Provisioning Guidance
- DRY_RUN_PLACEHOLDER_ONLY: operator provisions credentials outside this repository; no command is executed here.
- Use organization-approved out-of-repo secure methods only.

## 7. What The Operator Must Not Do
- Do not run any API write operation.
- Do not execute existing rerun command chain in this phase.
- Do not include credential templates that require value pasting.

## 8. Verification Without Revealing Values
- Verify existence only.
- Store only boolean existence outputs in phase evidence.

## 9. No API Execution In This Phase
- WordPress API must not be called in Phase 8-31.
- WordPress draft creation must not occur in Phase 8-31.

## 10. No Phase 8-6 To 8-10 Execution In This Phase
- Phase 8-6 to Phase 8-10 must not be executed in Phase 8-31.

## 11. Freeze Conditions
- If any secret value is detected in logs, freeze immediately.
- If any API mutation command appears, freeze immediately.
- If any rerun execution command appears, freeze immediately.

## 12. Evidence Requirements
- HUMAN_APPROVAL_REQUIRED=true
- target_item_count=1
- publish_allowed=false
- auto_post=false
- auto_update=false
- auto_delete=false
- auto_export=false
- commands_executed_in_this_phase=false
- secret_values_written=false

## 13. Final Judgment
- PASS_PROCEDURE_ONLY is required to move forward.

## 14. Next Step
- Phase 8-32 provisioned declaration overlay package
