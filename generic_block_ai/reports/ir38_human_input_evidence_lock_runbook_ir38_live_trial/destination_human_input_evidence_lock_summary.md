# Human Input & Evidence Lock Runbook

- Source Task ID: ir38_live_trial
- Overall Approval Decision: APPROVE_DRY_RUN
- Overall Runbook Action: Collect approver records and lock evidence for dry-run approval path.

## Destination Human Input & Lock Steps
- regulatory_audit -> APPROVE_DRY_RUN
  - Freeze destination decision record and approver input snapshot.
  - Store immutable digest for runbook payload and destination manifest refs.
  - Persist lock timestamp and operator metadata in audit trail.
- internal_review_board -> APPROVE_DRY_RUN
  - Freeze destination decision record and approver input snapshot.
  - Store immutable digest for runbook payload and destination manifest refs.
  - Persist lock timestamp and operator metadata in audit trail.
- compliance_archive -> APPROVE_DRY_RUN
  - Freeze destination decision record and approver input snapshot.
  - Store immutable digest for runbook payload and destination manifest refs.
  - Persist lock timestamp and operator metadata in audit trail.
