# Phase 8-SVC-6: Daemon-Reload Post-Check Design

Status: DESIGN_ONLY_NO_ACTIVATION

## 1. Purpose
- Define post-check items for the phase immediately after a future daemon-reload.
- Keep this phase design-only and prohibit activation actions.

## 2. Preconditions
- SVC-3 status must be PASS_UNIT_FILES_PLACED_NO_ACTIVATION.
- SVC-5 status must be PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK.
- Unit/timer files are already placed in /etc/systemd/system.

## 3. Scope
- This phase defines checks only.
- It does not execute daemon-reload in this phase.
- It does not enable/start/restart service or timer.

## 4. Absolute Prohibitions
- systemctl daemon-reload
- systemctl enable
- systemctl start
- systemctl restart
- credential.env creation
- secret input
- Phase 8-29 to 8-40 rerun
- WordPress API call / draft creation / publish

## 5. Planned Post-Reload Checks (Future Execution Phase)
- Confirm systemd recognizes service unit file metadata.
- Confirm systemd recognizes timer unit file metadata.
- Confirm unit load state is not not-found.
- Confirm no unintended activation occurred.
- Confirm no secret exposure in logs/output.

## 6. Activation Boundary
- timer enable remains prohibited in SVC-6 design phase.
- service start remains prohibited in SVC-6 design phase.
- restart remains prohibited in SVC-6 design phase.

## 7. Credential Boundary
- credential.env may remain not created in SVC-6 design phase.
- secret values must never be printed/masked/hashed.
- Allowed output style remains boolean/existence only.

## 8. Secret Safety Rules
- printenv is prohibited.
- cat /etc/ai-media-os/credential.env is prohibited.
- echo $WORDPRESS_* is prohibited.
- Environment=WORDPRESS_* inline secret in unit is prohibited.

## 9. Failure / Block Conditions
- Missing SVC-3/SVC-5 preconditions => BLOCKED_PRECONDITION_NOT_SATISFIED.
- Forbidden activation trace => ABORT_ACTIVATION_ACTION_EXECUTED.
- WordPress execution trace => ABORT_WORDPRESS_SIDE_EFFECT_DETECTED.
- Secret exposure trace => ABORT_SECRET_OUTPUT_DETECTED.

## 10. Evidence Requirement
- exchange/logs/phase8_svc_6_daemon_reload_post_check_design_result.json must be generated.
- validator status must be PASS_DESIGN_ONLY_DAEMON_RELOAD_POST_CHECK.

## 11. Final Judgment Rule
- PASS when required sections and policy constraints are satisfied.
- FAIL when required sections/policy fields are missing.
- ABORT when forbidden executable traces are detected.

## 12. Next Step
- Candidate next phase: controlled daemon-reload execution checkpoint (still no enable/start).
