# Phase 8-SVC-5: Daemon-Reload Preflight Gate Design

Status: DESIGN_ONLY_NO_EXECUTION

## 1. Purpose
- Define the final gate conditions before allowing daemon-reload in a later phase.
- Keep this phase design-only and do not execute daemon-reload.

## 2. Scope
- Validate design conditions for controlled activation progression only.
- Do not execute any activation command in this phase.

## 3. Preconditions
- SVC-3 must be PASS_UNIT_FILES_PLACED_NO_ACTIVATION.
- SVC-4 must be PASS_DESIGN_ONLY_NO_ACTIVATION.
- Installed files must exist under /etc/systemd/system.
- Repo and installed unit files must have no diff.
- systemd-analyze verify for installed files must pass.

## 4. Absolute Prohibitions in SVC-5
- systemctl daemon-reload
- systemctl enable
- systemctl start
- systemctl restart
- credential.env creation
- secret input
- Phase 8-29 to 8-40 rerun
- WordPress API call / draft creation / publish

## 5. Daemon-Reload Allow Rule (Future SVC-6)
- daemon-reload may be allowed only if all preconditions are satisfied.
- Any diff or verify error blocks daemon-reload.
- In SVC-5, daemon-reload remains prohibited.

## 6. Enable/Start Control Rule
- timer enable is not allowed in SVC-5.
- service start is not allowed in SVC-5.
- restart is not allowed in SVC-5.

## 7. Credential Readiness Coupling Rule
- credential.env may remain absent in SVC-5 design phase.
- Real credential provisioning is a separate controlled phase.
- No secret values are printed, masked, hashed, or logged.

## 8. Secret Safety Rule
- printenv is prohibited for secret checks.
- cat /etc/ai-media-os/credential.env is prohibited.
- echo $WORDPRESS_* is prohibited.
- Environment=WORDPRESS_* direct inline secret in unit file is prohibited.

## 9. Failure / Block Conditions
- Missing installed unit files => BLOCKED_INSTALLED_UNIT_FILES_MISSING.
- Repo/installed diff detected => BLOCKED_REPO_INSTALLED_DIFF_DETECTED.
- verify failure => BLOCKED_SYSTEMD_ANALYZE_VERIFY_FAILED.
- activation action executed => ABORT_ACTIVATION_ACTION_EXECUTED.
- WordPress side effects => ABORT_WORDPRESS_SIDE_EFFECT_DETECTED.
- Secret output detected => ABORT_SECRET_OUTPUT_DETECTED.

## 10. Evidence Requirement
- exchange/logs/phase8_svc_5_daemon_reload_preflight_gate_design_result.json must be generated.
- validator status must be PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK.

## 11. Final Judgment Rule
- PASS when gate design is complete and all prohibitions are preserved.
- FAIL when required sections/policy constraints are missing.
- ABORT when forbidden executable traces are detected.

## 12. Next Step
- Candidate next phase: SVC-6 daemon-reload execution checkpoint (still no enable/start).
