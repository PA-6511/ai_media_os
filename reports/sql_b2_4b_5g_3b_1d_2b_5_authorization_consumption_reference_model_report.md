# SQL-B2-4B-5G-3B-1D-2B-5 Authorization Consumption Reference Model

## Result

`PASS_AUTHORIZATION_CONSUMPTION_STATE_MACHINE_REFERENCE_MODEL_IN_MEMORY_ONLY_NO_HOST_STATE_NO_GO`

## Purpose

This phase implements an in-memory reference model for single-use
authorization consumption.

It models authorization-ID and nonce replay rejection without creating a
host consumption record or authorizing installation.

## Reference state machine

- Initial state: `UNSEEN`
- Valid and unique document: `CONSUMED_IN_MEMORY_REFERENCE_ONLY`
- Invalid document: `REJECTED_NO_LEDGER_CHANGE`
- Duplicate authorization ID: `REPLAY_REJECTED`
- Duplicate nonce: `REPLAY_REJECTED`
- Host-consumed state: unreachable
- Install-authorized state: unreachable

## Ledger behavior

The model receives a caller-provided in-memory ledger and returns a new
ledger using copy-on-write behavior.

The input ledger is not modified. Invalid, expired or replayed documents
produce no replacement ledger and therefore cannot create a partial
authorization-ID-only or nonce-only update.

## Future durable state

The future root helper is expected to record durable consumption under:

`/var/lib/ai-media-os-slack-release/install-authorizations`

This reference model does not create, inspect or modify that path.

## Explicit limitations

The model does not validate:

- Root ownership or mode
- Symlink or hard-link custody
- Exclusive file creation
- Filesystem atomicity
- `fsync` or directory `fsync`
- Process-crash recovery
- Multi-process locking
- Existing host replay state

## Current state

- Capsule issued: no
- Host capsule file read: no
- In-memory reference consumption executed during tests only
- Host authorization consumed: no
- Host consumption record created: no
- Root file custody validated: no
- Root installation authorized: no
- Root installation executed: no
- Host mutation: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
