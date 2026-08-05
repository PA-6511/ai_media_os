# Phase 8-SVC-4: Activation Preflight Design / No Activation

Status: DESIGN_ONLY_NO_EXECUTION

## 1. Purpose
- Define preflight gates before any future daemon-reload/enable/start operations.
- Keep this phase design-only with no activation and no external execution.

## 2. Scope
- Design the decision criteria for activation readiness only.
- Do not create credential files and do not input secrets in this phase.
- Do not execute Phase 8-29 to 8-40 reruns in this phase.

## 3. Absolute Prohibitions in SVC-4
- systemctl daemon-reload
- systemctl enable
- systemctl start
- systemctl restart
- credential.env creation
- secret input
- WordPress API call / draft creation / publish

## 4. Preflight Gate Checklist (Future SVC-5+)
- SVC-3 status must be PASS_UNIT_FILES_PLACED_NO_ACTIVATION.
- service and timer files must exist under /etc/systemd/system.
- repo and installed unit files must have no diff.
- systemd-analyze verify for installed files must return exit code 0.
- forbidden-operation scan must show no activation/write code paths.
- activation commands must remain unexecuted in preflight phase.

## 5. Daemon-Reload Permission Rule
- daemon-reload is allowed only after all checklist items pass.
- In SVC-4, daemon-reload remains prohibited.

## 6. Timer Enable Permission Rule
- timer enable is allowed only after daemon-reload is completed in the next phase.
- In SVC-4, timer enable remains prohibited.

## 7. Service Start Permission Rule
- service start remains prohibited until credential readiness is confirmed.
- If credential.env is missing or incomplete, service start is blocked.

## 8. Credential Handling Rule
- credential.env must not be created in SVC-4.
- secret values must not be printed, masked, hashed, or logged.
- only existence booleans are allowed in later verification outputs.

## 9. Secret Output Safety Rule
- printenv is prohibited for secret verification.
- cat /etc/ai-media-os/credential.env is prohibited.
- echo $WORDPRESS_* is prohibited.

## 10. Rollback / Removal Design
- If installed unit files are wrong, remove only the installed files manually.
- rollback scope for SVC-4 is file placement correction only.
- no service activation rollback is needed because activation is prohibited.

## 11. Evidence Requirement
- exchange/logs/phase8_svc_4_activation_preflight_design_result.json must be generated.
- validator output status must be PASS_DESIGN_ONLY_NO_ACTIVATION.

## 12. Final Judgment Rule
- PASS when design checklist is complete and all prohibitions are preserved.
- FAIL when required sections or policy requirements are missing.
- ABORT when forbidden activation/wordpress/secret execution traces are present.

## 13. Next Step
- Next phase candidate: SVC-5 activation preflight execution (still no WordPress execution).
- Credential Ready real provisioning starts only after explicit human approval.
