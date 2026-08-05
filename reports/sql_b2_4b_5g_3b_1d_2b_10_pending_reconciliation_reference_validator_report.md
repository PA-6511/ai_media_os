# SQL-B2-4B-5G-3B-1D-2B-10 Pending Reconciliation Reference Validator

## Result

`PASS_PENDING_RECONCILIATION_AUTHORIZATION_REFERENCE_VALIDATOR_IN_MEMORY_ONLY_NOT_CONSUMED_NO_GO`

## Purpose

This phase implements an in-memory reference validator for the future
pending-reconciliation authorization document.

It does not open the future root-owned authorization path, consume an
authorization, create a human decision record or modify a pending record.

## Validated content

- Exact document keys
- Duplicate JSON-key rejection
- Operation and release ID
- Human root issuer identity
- Allowed reconciliation decision
- Pending filename format
- Pending filename binding to authorization ID, nonce and transaction ID
- Pending SHA-256 format
- Exact safety constraints
- UTC issue and expiry timestamps
- Maximum validity of `900` seconds
- Canonical document SHA-256

## Allowed decisions

- `KEEP_REPLAY_RESERVED`
- `AUTHORIZE_FINALIZE_AS_CONSUMED`
- `BLOCK_AND_ESCALATE`

Document validity alone does not permit execution of any decision.

## Explicitly unverified

- Root ownership and mode
- Symlink and hard-link custody
- Actual pending-file SHA-256
- Existing host replay state
- Authorization consumption
- Human decision-record persistence
- Pending-to-final mutation

## Current state

- Reconciliation authorization issued: no
- Authorization file read from host: no
- Root custody validated: no
- Reconciliation authorization consumed: no
- Human decision record created: no
- Pending record modified: no
- Root installation authorized: no
- Root installation executed: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
