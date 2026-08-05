# SQL-B2-4B-5G-3B-1D-2B-7 Durable Writer Sandbox

## Result

`PASS_DURABLE_WRITER_SANDBOX_REFERENCE_IMPLEMENTATION_TMP_ONLY_NO_HOST_AUTHORIZATION_NO_GO`

## Purpose

This phase implements the durable-consumption writer protocol only inside
a caller-supplied `/tmp` test sandbox.

It does not use the future root-managed state path and does not issue,
consume or authorize a host installation.

## Implemented sandbox behavior

- Caller-supplied path must be below `/tmp`
- State and records directories use mode `0700`
- Lock and record files use mode `0600`
- Exclusive process lock covers scan and publication
- Existing final records reject authorization-ID and nonce replay
- Existing pending records block consumption fail-closed
- Unknown and malformed entries block consumption
- Pending files use `O_CREAT | O_EXCL`
- `O_NOFOLLOW` is used where available
- Pending file is `fsync`ed
- Records directory is `fsync`ed before rename
- Pending file is atomically renamed to the final record
- Records directory is `fsync`ed after rename

## Explicit boundary

The generated record state is:

`SANDBOX_DURABLE_CONSUMED_REFERENCE_ONLY`

It is not a host authorization-consumption record and cannot authorize
root release installation.

## Unverified production properties

- Root ownership and custody
- Future capsule-file descriptor custody
- Future host replay state
- Adversarial writers bypassing the cooperative lock
- Real power-loss behavior
- Root helper integration
- Root installation authority

## Current state

- Sandbox writer implemented: yes
- Durable host writer implemented: no
- Durable host writer installed: no
- Host state root created: no
- Authorization capsule issued: no
- Authorization consumed on host: no
- Host consumption record created: no
- Root installation authorized: no
- Root installation executed: no
- Current link changed: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
