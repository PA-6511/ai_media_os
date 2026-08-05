# X-R13 Pre-Post Slack Approval Flow Prep

- Status: `PASS_X_R13_PRE_POST_SLACK_APPROVAL_FLOW_PREP_READY`
- State: `DESIGN_BASELINE_READY_NO_CANDIDATE_BOUND`
- Candidate bound: `false`

## Standard sequence

1. Generate and validate a local canonical X draft.
2. Approve and execute one Slack review delivery.
3. Human replies with exact APPROVE, REVISE, or REJECT token.
4. Register screenshot evidence and exact review token.
5. Issue one manual X posting authorization only after APPROVE.
6. Human posts manually to X.
7. Register the resulting X post URL.
8. Capture 24-hour and 7-day metrics.

## Safety

- No Slack message was sent.
- No Slack credential was read.
- No X API or browser automation was used.
- No database, workflow, or WordPress write occurred.
- Production status remains `NO_GO`.
