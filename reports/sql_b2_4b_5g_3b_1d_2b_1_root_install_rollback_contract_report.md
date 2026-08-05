# SQL-B2-4B-5G-3B-1D-2B-1 Root Install and Rollback Contract

## Result

`PASS_ROOT_RELEASE_INSTALL_ROLLBACK_CONTRACT_DESIGN_ONLY_NO_HOST_CHANGE_NO_GO`

## Release binding

- Release ID: `slack-worker-5441bd1-1590693d6ae7`
- Final release path: `/opt/ai-media-os/slack-worker/releases/slack-worker-5441bd1-1590693d6ae7`
- Current link: `/opt/ai-media-os/slack-worker/current`
- Source files: `16`
- Locked Wheels: `5`

## Authorization boundary

A root-owned, single-use authorization capsule is required before any
persistent host mutation.

- Candidate capsule: `/etc/ai-media-os-install-authorizations/slack-worker-5441bd1-1590693d6ae7.install.json`
- Owner/group: `root:root`
- Mode: `0600`
- Allowed operation: `INSTALL_RELEASE_ONLY`
- Expiration and nonce: required
- Release and input-hash binding: required
- Reuse after failure: prohibited
- Issued during this phase: no

## Input custody

The repository and temporary Wheelhouse remain deploy-writable and cannot
be used directly as root-trusted runtime inputs.

A future root helper must copy regular files without following symlinks
into root-private staging, revalidate every SHA-256, and build the virtual
environment from the private Wheel copy using offline hash-locked pip.

## Install transaction

- Exclusive lock: `/run/lock/ai-media-os-slack-worker-release-install.lock`
- Staging template: `/opt/ai-media-os/slack-worker/releases/.staging-slack-worker-5441bd1-1590693d6ae7-{transaction_id}`
- Transaction type: `INSTALL_ONLY`
- Commit point: atomic same-filesystem rename
- Current-link change: prohibited
- Secret migration: prohibited
- systemd operation: prohibited

## Idempotency and rollback

- Matching existing release: classify as installed and unactivated
- Mismatching existing release: block and require review
- Unknown-path automatic deletion: prohibited
- Before commit: remove only transaction-bound staging
- After commit: do not automatically delete the published release
- Current link remains unchanged

## Activation boundary

Activation is a separate transaction requiring distinct authorization.
Release verification, previous-target recording, atomic replacement and
atomic restoration are mandatory. Service start and enable remain
prohibited.

## Current status

- Root helper implemented: no
- Authorization capsule issued: no
- Root release installation authorized: no
- Root release installation executed: no
- Root ownership applied: no
- Current link created: no
- Secret migration: no
- Unit change: no
- Daemon reload: no
- Gate creation: no
- Service start: no
- Unit enable: no
- Final decision: `NO_GO`
