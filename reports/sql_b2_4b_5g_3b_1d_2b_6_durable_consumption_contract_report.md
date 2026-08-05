# SQL-B2-4B-5G-3B-1D-2B-6 Durable Authorization Consumption Contract

## Result

`PASS_DURABLE_AUTHORIZATION_CONSUMPTION_STATE_CONTRACT_DESIGN_ONLY_NO_HOST_STATE_NO_GO`

## Purpose

This phase defines the crash-resistant durable state contract for
single-use installation authorization consumption.

It does not create the state root, lock file, pending record or final
record.

## State custody

- State root: `/var/lib/ai-media-os-slack-release/install-authorizations`
- Records directory: `/var/lib/ai-media-os-slack-release/install-authorizations/records`
- Lock file: `/var/lib/ai-media-os-slack-release/install-authorizations/consume.lock`
- Directory owner/group: `root:root`
- Directory mode: `0700`
- Lock owner/group: `root:root`
- Lock mode: `0600`
- Service-user writes: prohibited

## Single-record strategy

Authorization-ID and nonce uniqueness are not split between independent
index files.

One record contains both values. A global exclusive lock covers the
complete scan, duplicate check, pending-record publication and final
rename.

Both pending and final records participate in future replay detection.

## Pending record

The pending filename contains:

- Authorization ID
- Nonce
- Transaction ID

After the complete pending document and records directory have been
`fsync`ed, the authorization is durably consumed.

A crash after that point leaves a pending record that reserves both the
authorization ID and nonce. It must be treated as consumed and reconciled,
not deleted for retry.

## Publication

The pending file is renamed to the final authorization-ID record using a
same-directory atomic rename, followed by a directory `fsync`.

Unknown, malformed or untrusted entries block all new consumption and
require human review.

## Current state

- Durable writer implemented: no
- Durable writer installed: no
- State root created: no
- Lock file created: no
- Pending record created: no
- Final record created: no
- Authorization consumed on host: no
- Root installation authorized: no
- Root installation executed: no
- Current link changed: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
