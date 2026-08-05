# Phase 8-SVC-7: Unit/Timer Removal Rollback Design

Status: DESIGN_ONLY_NO_EXECUTION

## 1. Purpose
- Define safe rollback/removal procedures for placed systemd unit/timer files.
- Keep this phase design-only with no destructive execution.

## 2. Scope
- Cover removal targets and verification steps for service/timer files.
- Define differences between pre-daemon-reload and post-daemon-reload rollback logic.
- Define ABORT handling when activation has been executed unexpectedly.

## 3. Removal Targets
- /etc/systemd/system/ai-media-os-credential-ready-validator.service
- /etc/systemd/system/ai-media-os-credential-ready-validator.timer

## 4. Absolute Prohibitions in SVC-7
- rm /etc/systemd/system/ai-media-os-credential-ready-validator.service
- rm /etc/systemd/system/ai-media-os-credential-ready-validator.timer
- systemctl daemon-reload
- systemctl enable
- systemctl start
- systemctl restart
- credential.env creation
- secret input
- Phase 8-29 to 8-40 rerun
- WordPress API call / draft creation / publish

## 5. Pre-Removal Check Design
- Confirm target files exist before any future removal operation.
- Confirm repo copy and installed copy relation is known.
- Confirm activation state (enabled/active) before selecting rollback path.

## 6. Removal Path A (No Activation Executed)
- Condition: enable/start/restart never executed.
- Planned action (future phase only): remove installed service/timer files.
- Planned verification: installed files absent, no activation state remaining.
- daemon-reload may be required in a later controlled phase only.

## 7. Removal Path B (Activation Executed Unexpectedly)
- Condition: any enable/start/restart detected.
- Immediate status: ABORT_ACTIVATION_ACTION_EXECUTED.
- Freeze and incident documentation required before any removal action.
- Recovery plan must be manually approved by human operator.

## 8. Pre/Post Daemon-Reload Difference Design
- Pre-daemon-reload removal: files removed but runtime cache may still reference old units.
- Post-daemon-reload removal: runtime cache expected to reflect file removal.
- In SVC-7, daemon-reload remains prohibited.

## 9. Secret Safety Rules
- printenv is prohibited.
- cat /etc/ai-media-os/credential.env is prohibited.
- echo $WORDPRESS_* is prohibited.
- No secret values, lengths, masks, or hashes in outputs.

## 10. Evidence Requirement
- exchange/logs/phase8_svc_7_unit_timer_removal_rollback_design_result.json must be generated.
- validator status must be PASS_DESIGN_ONLY_REMOVAL_ROLLBACK_PREPARED.

## 11. Final Judgment Rule
- PASS when sections and policy constraints are complete and no executable forbidden traces exist.
- FAIL when required sections or policy constraints are missing.
- ABORT when executable forbidden traces are detected.

## 12. Next Step
- Candidate next phase: controlled removal execution checkpoint (still no WordPress execution).
