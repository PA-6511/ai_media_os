# Destination Review Queue Builder

- Source Task ID: ir45_live_trial
- Overall Submission Gate Decision: READY_FOR_REVIEW
- Overall Queue Action: Build review queue entries and hand off to destination reviewers.

## Destination Queue Status
- compliance_archive -> QUEUED_FOR_REVIEW
  - compliance_archive-R1: Verify hash manifest and summary link consistency
  - compliance_archive-R2: Confirm evidence digest and bundle hash correspondence
- internal_review_board -> QUEUED_FOR_REVIEW
  - internal_review_board-R1: Verify hash manifest and summary link consistency
  - internal_review_board-R2: Confirm evidence digest and bundle hash correspondence
- regulatory_audit -> QUEUED_FOR_REVIEW
  - regulatory_audit-R1: Verify hash manifest and summary link consistency
  - regulatory_audit-R2: Confirm evidence digest and bundle hash correspondence
