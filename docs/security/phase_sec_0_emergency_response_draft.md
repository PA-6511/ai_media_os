# Phase-Sec 0: Security Emergency Response Baseline Draft

## 1. Phase Status

- Phase ID: PHASE_SEC_0
- Phase Name: Security Emergency Response Baseline Draft
- Status: DESIGN_ONLY
- Execution: DRY_RUN
- Production: NO_GO
- Human Approval: REQUIRED
- Scope: Core AI / Block AI / Self Builder AI / WordPress / VPS / Backup / Evidence

## 2. Purpose

Phase-Sec 0 defines the initial emergency security response baseline for the AI operating system.

This phase is not an implementation phase.  
It is a design-only security baseline that prepares future countermeasures against compromise, takeover, ransomware, credential leakage, malicious automation, and unauthorized external writes.

## 3. Core Principle

If compromise is suspected, safety takes priority over revenue, automation, posting, updating, exporting, and convenience.

The system must prefer:

1. Stop
2. Isolate
3. Preserve evidence
4. Rotate secrets
5. Restore from trusted backups
6. Resume only after human approval

## 4. Applicability

This baseline applies to:

- Core AI
- Generic Block AI
- Affiliate Block AI
- Self Builder AI
- Algorithm Research Block AI
- WordPress integration
- GitHub integration
- Slack integration
- VPS runtime
- NAS backup
- Cloud backup
- Evidence and report storage
- Future GUI control layer

## 5. Assumed Threats

The following threats are explicitly assumed:

- VPS compromise
- SSH key leakage
- GitHub token leakage
- WordPress credential leakage
- WordPress plugin vulnerability exploitation
- API key leakage
- Slack webhook leakage
- Malicious dependency or supply-chain attack
- Unauthorized code modification
- Unauthorized AI prompt or policy modification
- Block AI takeover
- Core AI behavior modification
- Ransomware encryption of logs, evidence, prompts, configs, or backups
- Unauthorized WordPress posting
- Unauthorized WordPress update
- Unauthorized WordPress deletion
- Unauthorized export
- Unauthorized external API execution
- Unauthorized self-update
- Unauthorized connector switching
- Unauthorized VPS migration
- Human approval spoofing

## 6. Emergency Freeze

Emergency Freeze is the highest priority safety state.

When Emergency Freeze is active, the system must conceptually stop:

- Block AI execution
- External writes
- WordPress posting
- WordPress updating
- WordPress deletion
- GitHub push
- External export
- Connector switching
- VPS migration
- Self-update
- Auto-repair
- Auto-deployment
- Auto-scaling
- Scheduled production jobs

Phase-Sec 0 does not implement Emergency Freeze.  
It only defines Emergency Freeze as a required future safety capability.

## 7. Block Isolation

If a Block AI is suspected to be compromised, the Core AI must be able to isolate that Block AI.

Isolation means:

- Disconnect from Core AI
- Stop task intake
- Stop external output
- Preserve logs
- Preserve last decision package
- Preserve last evidence
- Require human review before reconnection

Future GUI should expose Block isolation as a protected operation.

## 8. External Write Stop

If compromise is suspected, all external write operations must be stopped.

External write operations include:

- WordPress post creation
- WordPress post update
- WordPress post deletion
- GitHub push
- GitHub release
- GitHub Actions dispatch
- Slack production notification
- Paid API execution
- Public web publishing
- File export
- Remote deployment
- DNS or Cloudflare setting changes

Phase-Sec 0 defines this as a required design rule only.

## 9. Secret Rotation Plan

If compromise is suspected, the following secrets must be considered contaminated:

- SSH private keys
- GitHub tokens
- WordPress application passwords
- WordPress administrator passwords
- Slack webhooks
- OpenAI API keys
- Amazon PA-API keys
- Rakuten API keys
- DMM API keys
- Database passwords
- VPS user passwords
- Backup storage credentials
- Cloud storage credentials

Required future response:

1. Freeze system
2. Revoke exposed secrets
3. Generate new secrets
4. Update runtime secrets manually
5. Verify no old secret remains active
6. Preserve rotation evidence
7. Resume only after human approval

## 10. Backup Protection

Backups must not rely only on always-connected storage.

Future backup layers should include:

- Online backup
- Cloud backup
- NAS backup
- Offline backup
- Immutable or append-only backup
- Periodic restore test
- Backup integrity verification

Ransomware response must assume that online storage may also be affected.

## 11. Recovery Core Draft

A future Recovery Core may be introduced.

Its role would be:

- Read-only incident review
- Evidence verification
- Backup integrity check
- Safe rollback recommendation
- Secret rotation checklist generation
- Block AI reconnection recommendation
- Core AI recovery recommendation

Phase-Sec 0 does not create Recovery Core.  
It only reserves the concept.

## 12. Evidence Lock

Security evidence must be preserved in a tamper-resistant manner.

Future evidence should include:

- Incident timestamp
- Trigger reason
- Affected component
- Freeze status
- Isolation status
- External write status
- Secret rotation status
- Backup verification status
- Human reviewer
- Final decision
- Resume approval evidence

Evidence must not be silently overwritten.

## 13. ABORT Conditions

The following conditions must cause ABORT in future security gates:

- production_status is not NO_GO during design-only security phase
- execution is not DRY_RUN during design-only security phase
- human_approval_required is false
- emergency freeze is disabled
- external write stop is disabled
- block isolation is disabled
- secret rotation plan is absent
- backup protection plan is absent
- evidence preservation is absent
- automatic production write is enabled
- automatic deletion is enabled
- automatic export is enabled
- automatic connector switching is enabled
- unknown security decision is received
- compromised component requests reconnection without human approval

## 14. Prohibited Actions in Phase-Sec 0

The following actions are prohibited:

- WordPress write
- WordPress update
- WordPress delete
- GitHub push
- GitHub Actions dispatch
- external API execution
- production deployment
- automatic secret rotation
- automatic recovery execution
- automatic rollback execution
- automatic connector switching
- VPS migration
- modifying .env
- modifying secrets
- enabling production mode

## 15. Allowed Actions in Phase-Sec 0

The following actions are allowed:

- create design document
- create security baseline JSON
- validate JSON
- create validator
- create tests
- generate design-only evidence
- review future security requirements

## 16. Future Phase Candidates

Possible future phases:

- Phase-Sec 1: Emergency Freeze Flag Design
- Phase-Sec 2: Block Isolation Gate Design
- Phase-Sec 3: External Write Stop Gate Design
- Phase-Sec 4: Secret Rotation Checklist Design
- Phase-Sec 5: Backup Integrity Evidence Design
- Phase-Sec 6: Recovery Core Design
- Phase-Sec 7: Security Incident Report Generator
- Phase-Sec 8: Controlled Resume Gate
- Phase-Sec 9: GUI Protected Security Operations

## 17. Final Position

Phase-Sec 0 is a cross-cutting safety baseline.

Current conclusion:

- Security baseline: REQUIRED
- Implementation: NOT YET
- Production operation: NO_GO
- External write: NO_GO
- Automatic recovery: NO_GO
- Human approval: REQUIRED
