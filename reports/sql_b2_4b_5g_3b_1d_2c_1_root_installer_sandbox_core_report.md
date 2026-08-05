# SQL-B2-4B-5G-3B-1D-2C-1 Root Installer Sandbox Core

## Result

`PASS_UNPRIVILEGED_ROOT_INSTALLER_SANDBOX_CORE_TMP_ONLY_NO_HOST_INSTALL_NO_GO`

## Purpose

This phase implements the filesystem-transaction core of the future
release installer inside caller-supplied `/tmp` sandboxes only.

It does not access the future root release path or perform authorization
consumption.

## Bound release

- Release ID: `slack-worker-5441bd1-1590693d6ae7`
- Source-file count: `16`
- Locked-wheel count: `5`
- Future host release path: `/opt/ai-media-os/slack-worker/releases/slack-worker-5441bd1-1590693d6ae7`
- Future current link: `/opt/ai-media-os/slack-worker/current`

## Prepared bundle validation

The sandbox core validates:

- Exact bundle top-level layout
- Exact release and policy hashes
- Exact source and wheel counts
- Normalized relative paths
- No absolute paths or parent traversal
- No payload symlinks, hard links or special files
- Exact payload tree-to-manifest correspondence
- File size, SHA-256 and mode

## Sandbox transaction

The implementation provides:

- Exclusive installation lock
- Dedicated staging directory
- Descriptor-based source and destination access
- `O_NOFOLLOW` where available
- Exclusive destination-file creation
- Copy-time size and SHA-256 revalidation
- File and directory `fsync`
- Precommit staging rollback
- Atomic staging-to-final rename
- Validation-based idempotent retry
- Rejection of altered existing releases

## Explicit boundary

This phase does not:

- Validate or consume an installation authorization capsule
- Create a durable host consumption record
- Build a virtual environment
- Install wheels
- Access `/opt/ai-media-os/slack-worker/releases/slack-worker-5441bd1-1590693d6ae7`
- Create `/opt/ai-media-os/slack-worker/current`
- Install the future root helper
- Read Slack secrets
- Change systemd
- Write either database

## Current state

- Sandbox transaction core implemented: yes
- Root helper implemented: no
- Root helper installed: no
- Root release installation authorized: no
- Root release installation executed: no
- Authorization capsule issued: no
- Authorization capsule consumed: no
- Host consumption record created: no
- Current link created: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
