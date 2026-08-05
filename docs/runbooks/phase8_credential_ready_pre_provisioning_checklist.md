# Phase 8 Credential Ready Pre-Provisioning Checklist

## 1. Purpose
- Prepare safe prerequisites before real credential provisioning.
- Keep this checklist as planning/verification only.
- This checklist is not execution permission.

## 2. Current Fixed Status Baseline
- Phase 8-SVC-3: REPO_UNIT_READY_INSTALL_BLOCKED_BY_SUDO_AUTH
- Phase 8-SVC-3B: POST_INSTALL_VERIFICATION_PROMPT_READY
- Phase 8-SVC-4: PASS_DESIGN_ONLY_NO_ACTIVATION
- Phase 8-SVC-5: PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK

## 3. Scope Boundary
- This checklist does not create credential.env.
- This checklist does not input any secret.
- This checklist does not run Phase 8-29 to 8-40 rerun commands.
- This checklist does not perform WordPress API call/draft/publish.

## 4. Absolute Prohibitions
- systemctl daemon-reload
- systemctl enable
- systemctl start
- systemctl restart
- echo $WORDPRESS_*
- printenv
- cat /etc/ai-media-os/credential.env

## 5. Pre-Provisioning Readiness Items
- [ ] SVC-3 sudo install is completed by human operator.
- [ ] Installed file existence is confirmed for service and timer.
- [ ] Repo vs installed diff is confirmed as no diff.
- [ ] Installed-file systemd-analyze verify exit code is 0.
- [ ] Activation remains unexecuted (enable/start/restart/daemon-reload all false).
- [ ] SVC-4 status is PASS_DESIGN_ONLY_NO_ACTIVATION.
- [ ] SVC-5 status is PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK.

## 6. Credential Input Readiness Items
- [ ] SERVICE_NAME_HERE is fixed to real unit name.
- [ ] SERVICE_USER_HERE is fixed to deploy.
- [ ] SERVICE_GROUP_HERE is fixed to deploy.
- [ ] Target path /etc/ai-media-os/credential.env ownership policy is confirmed.
- [ ] Secret non-disclosure rules are reviewed by operator.

## 7. Secret Safety Rules
- Do not print secret values.
- Do not print secret lengths.
- Do not print secret prefixes/suffixes.
- Do not hash or mask secret values for output.
- Allowed output remains exists=true/false only.

## 8. Evidence Fields To Keep False In This Phase
- daemon_reload_executed=false
- systemctl_enable_executed=false
- systemctl_start_executed=false
- systemctl_restart_executed=false
- credential_env_created=false
- secret_input_executed=false
- phase8_29_to_8_40_rerun_executed=false
- wordpress_api_call_attempted=false
- wordpress_draft_created=false
- wordpress_publish_executed=false

## 9. Completion Rule
- PASS_CHECKLIST_ONLY when all checklist items are confirmed without prohibited actions.
- FAIL if any required checklist item is not confirmed.
- ABORT if any prohibited command or secret exposure is detected.

## 10. Next Step
- Next operation is SVC-3 post-install verification result confirmation.
- After SVC-3 becomes PASS_UNIT_FILES_PLACED_NO_ACTIVATION, proceed to controlled credential provisioning phase.
