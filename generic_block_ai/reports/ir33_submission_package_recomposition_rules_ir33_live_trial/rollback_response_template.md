# Rollback Response Template

- Release Candidate ID: rc_20260523T155148Z_ir26_live_trial_b940393b490b
- Purpose: Handle submission package return/rework without external transmission.

## Return Reason
- [ ] Missing template field
- [ ] Attachment mismatch
- [ ] Signature section incomplete
- [ ] Reviewer clarification requested

## Recomposition Actions
1. Rebuild templates based on destination rules.
2. Re-run IR30 decision summary and IR31 narrative if needed.
3. Regenerate IR32 template pack and IR33 recomposition outputs.

## Guard Confirmation
- send_allowed remains false
- send_executed remains false
- network_transmission_executed remains false
