# Phase 8-11 WordPress Credentials Manual Provisioning Runbook

## 1. Purpose

This runbook explains how to manually and safely provision WordPress credentials
for re-executing Phase 8-6 to Phase 8-10 after they stopped with
`RERUN_NOT_EXECUTED_CONFIRMED` due to missing credentials.

This runbook does NOT contain secret values.
This runbook does NOT create or edit .env automatically.
This runbook does NOT call the WordPress API.
This runbook is NOT execution permission.

## 2. Current Status

- Phase 8-6 = CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT
- Phase 8-7 = PASS_RERUN_REVIEW_ONLY
- Phase 8-8 = NOT_READY_CREDENTIALS_MISSING
- Phase 8-9 = NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY
- Phase 8-10 = RERUN_NOT_EXECUTED_CONFIRMED
- WordPress API must not be called in Phase 8-11.
- wordpress_write_executed = false
- secret_values_written = false

## 3. Why This Runbook Exists

The ai_media_os controlled draft creation flow requires three environment
variables to be set before the WordPress draft creation step can proceed.
Phase 8-9 detected that these variables were not present in the execution
environment, and stopped safely without making any API call.

This runbook guides the operator to provision those variables through the
organisation's existing secret management process — not through this repository.

## 4. Absolute Prohibitions

The following actions are strictly prohibited when following this runbook:

- This runbook must not contain secret values.
- Do not write secrets into this repository.
- Do NOT write secrets into this repository.
- Do NOT create or edit .env automatically.
- Do not create or edit .env automatically.
- Do NOT print WORDPRESS_APP_PASSWORD.
- Do NOT print credential lengths.
- Do NOT print credential prefixes or suffixes.
- Do NOT hash credentials for logging.
- Do NOT store credential values in JSON or Markdown logs.
- Do NOT use `export VARIABLE=value` commands that would leave secrets in shell history.
- Do NOT commit credentials to version control.
- Do NOT send credentials over unencrypted channels.
- HUMAN_APPROVAL_REQUIRED = true
- publish_allowed = false
- auto_post = false
- auto_update = false
- auto_delete = false
- auto_export = false
- target_item_count = 1

## 5. Required Environment Variables

The following three environment variables must be set in the execution
environment before re-running Phase 8-6 to Phase 8-10:

- `WORDPRESS_BASE_URL`
- `WORDPRESS_USERNAME`
- `WORDPRESS_APP_PASSWORD`

Allowed output is exists=true/false only.
Values, lengths, prefixes, suffixes, and hashes must never be output.

## 6. Safe Manual Provisioning Guidance

Provision the required variables using the organisation's existing safe secret
management approach.

DRY_RUN_PLACEHOLDER_ONLY: credentials must be provisioned manually outside this repository.

Do not place actual credentials in this document, in any script, or in any log
file. The variables must be available only in the secure runtime environment
where Phase 8-6 to Phase 8-9 scripts are executed.

Guidance:
- Use your organisation's secret manager or CI secrets store.
- Set variables in the shell session where the scripts will run.
- Do not echo the values to verify them; use Phase 8-13 which outputs only
  exists=true/false.
- If any secret value is detected in logs, freeze immediately.

## 7. No-Secret-Leak Rules

- Allowed output is exists=true/false only.
- Do not print WORDPRESS_APP_PASSWORD.
- Do not print credential lengths.
- Do not print credential prefixes or suffixes.
- Do not hash credentials for logging.
- Do not write credentials to any log file.
- Do not write credentials to any JSON artifact.
- secret_values_written = false must remain true in all Phase logs.
- If any secret value is detected in logs, freeze immediately.

## 8. Operator Checklist

Before re-running Phase 8-6 to Phase 8-10, confirm the following:

- [ ] WORDPRESS_BASE_URL has been set in the execution environment using the
      organisation's secure process (no value recorded here).
- [ ] WORDPRESS_USERNAME has been set in the execution environment using the
      organisation's secure process (no value recorded here).
- [ ] WORDPRESS_APP_PASSWORD has been set in the execution environment using the
      organisation's secure process (no value recorded here).
- [ ] No credential values have been written to any file in this repository.
- [ ] No credential values have been printed to any log.
- [ ] Phase 8-12 no-secret-leak audit has been reviewed.
- [ ] Phase 8-13 post-credential readiness recheck shows exists=true for all variables.
- [ ] Phase 8-14 rerun authorization renewal has been acknowledged.
- [ ] Phase 8-15 rerun handoff report has been reviewed.
- [ ] Human operator confirms re-execution is intentional.

## 9. Verification Without Revealing Values

To verify that credentials are present without exposing values, run:

```
python3 scripts/validate_phase8_13_post_credential_readiness_recheck.py
```

This script outputs only `"exists": true` or `"exists": false` for each variable.
It does not print values, lengths, prefixes, suffixes, or hashes.

The expected result when all credentials are present:
```
"credentials": {
  "WORDPRESS_BASE_URL": {"exists": true},
  "WORDPRESS_USERNAME": {"exists": true},
  "WORDPRESS_APP_PASSWORD": {"exists": true}
}
```

## 10. What Not To Do

The following examples show actions that are prohibited:

- Do not run commands that print credential values to the terminal.
- Do not store credential values in Python variables that are later logged.
- Do not pass credentials as command-line arguments.
- Do not write credentials in `config/*.json` files.
- Do not write credentials in `docs/` files.
- Do not write credentials in `exchange/logs/` files.
- Do not include `Authorization: Basic` headers in log output.
- Do not use `print(os.environ[...])` style debugging.
- Do not create .env files containing actual credentials in this repository.
- Do not create or modify secrets store entries automatically from scripts.

## 11. Expected Next Step

After this runbook validation passes (`PASS_RUNBOOK_ONLY`), proceed to:

1. Phase 8-12: no-secret-leak credential handling audit
2. Phase 8-13: post-credential readiness recheck gate (outputs exists=true/false only)
3. Phase 8-14: explicit rerun authorization renewal after credentials ready
4. Phase 8-15: rerun handoff report for Phase 8-6 to Phase 8-10 re-execution
5. If Phase 8-15 = READY_TO_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED, the human
   operator may manually re-run Phase 8-6 to Phase 8-10 scripts with explicit
   confirmation.

## 12. Freeze Conditions

Stop immediately and do not proceed if any of the following occur:

- A credential value appears in any log file.
- `secret_values_written = true` appears in any Phase log.
- `publish_allowed = true` appears in any Phase log.
- The WordPress API is called unexpectedly.
- A WordPress draft is created without explicit operator intent.
- Any error suggests credentials are being exposed.
- If any secret value is detected in logs, freeze immediately.

## 13. Evidence Requirements

This runbook validation reads the following evidence:

- `exchange/logs/phase8_10_post_rerun_closure_report.json` — must show
  `RERUN_NOT_EXECUTED_CONFIRMED`

Required validation passing conditions:
- All required sections present in this runbook.
- All required fixed statements present.
- No dangerous patterns (secret values, API call templates) detected.

## 14. Final Judgment

When all sections are present and no dangerous patterns are found:
- Status: `PASS_RUNBOOK_ONLY`

This status means the runbook is structurally valid. It is NOT execution
permission. The human operator must still follow the checklist in Section 8 and
confirm all subsequent phases before any API call is made.

HUMAN_APPROVAL_REQUIRED = true
target_item_count = 1
publish_allowed = false
auto_post = false
auto_update = false
auto_delete = false
auto_export = false
