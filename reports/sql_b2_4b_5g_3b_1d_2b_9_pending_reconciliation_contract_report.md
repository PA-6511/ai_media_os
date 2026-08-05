# SQL-B2-4B-5G-3B-1D-2B-9 Pending Reconciliation Contract

## Result

`PASS_PENDING_RECONCILIATION_AUTHORIZATION_AND_DECISION_CONTRACT_DESIGN_ONLY_NO_HOST_STATE_NO_GO`

## Purpose

This phase defines the separate authorization and immutable human
decision record required to reconcile a recovered pending authorization
record.

It does not issue reconciliation authorization or modify a pending
record.

## Separate authorization

- Operation: `RECONCILE_PENDING_AUTHORIZATION_RECORD`
- Future path template: `/etc/ai-media-os-install-authorizations/slack-worker-5441bd1-1590693d6ae7.{transaction_id}.pending-reconciliation.json`
- Owner/group: `root:root`
- Mode: `0600`
- Single use: required
- Maximum lifetime: `900` seconds
- Pending filename and SHA-256 binding: required
- Authorization ID, nonce and transaction-ID binding: required
- Distinct from installation authorization: yes

## Allowed decisions

### `KEEP_REPLAY_RESERVED`

The pending record remains unchanged and continues to reserve its
authorization ID and nonce.

### `AUTHORIZE_FINALIZE_AS_CONSUMED`

A future executor may atomically convert a validated pending record into
its final consumed-record name. It may not delete the record or resume
installation.

### `BLOCK_AND_ESCALATE`

The pending record and global consumption block remain in place for
additional investigation.

All outcomes preserve replay protection. Any future installation requires
a newly issued installation authorization capsule.

## Human decision record

- Future root: `/var/lib/ai-media-os-slack-release/install-authorizations/reconciliation-decisions`
- Path template: `/var/lib/ai-media-os-slack-release/install-authorizations/reconciliation-decisions/{decision_id}.json`
- Owner/group: `root:root`
- Mode: `0600`
- Exclusive creation: required
- Immutable after creation: required
- File and directory `fsync`: required
- Related installation state and rationale: required

The decision record must be committed before any future pending-record
mutation.

## Current state

- Reconciliation authorization issued: no
- Reconciliation authorization consumed: no
- Human decision record created: no
- Reconciliation executor implemented: no
- Reconciliation executor installed: no
- Pending record changed: no
- Authorization consumed on host: no
- Root installation authorized: no
- Root installation executed: no
- Current link changed: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
