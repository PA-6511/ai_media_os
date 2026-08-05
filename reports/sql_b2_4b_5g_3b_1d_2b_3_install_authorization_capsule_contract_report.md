# SQL-B2-4B-5G-3B-1D-2B-3 Install Authorization Capsule Contract

## Result

`PASS_INSTALL_AUTHORIZATION_CAPSULE_CONTRACT_DESIGN_ONLY_NOT_ISSUED_NO_GO`

## Purpose

This phase defines the future single-use authorization capsule required
before a root-managed Slack Worker release may be installed.

The contract does not issue an authorization capsule and does not
authorize or execute an installation.

## Root custody

- Exact future path: `/etc/ai-media-os-install-authorizations/slack-worker-5441bd1-1590693d6ae7.install.json`
- Required owner/group: `root:root`
- Required mode: `0600`
- Regular file required: yes
- Symlinks rejected: yes
- Hard-link count: exactly one
- `O_NOFOLLOW` and descriptor-based reading required
- Maximum capsule size: `16384` bytes

## Document identity

- Operation: `INSTALL_RELEASE_ONLY`
- Release ID: `slack-worker-5441bd1-1590693d6ae7`
- Issuer kind: `HUMAN_ROOT_OPERATOR`
- Issuer UID: `0`
- Authorization ID: required and unique
- Nonce: required and unique
- Unknown keys: rejected
- Duplicate JSON keys: rejected

## Bound inputs

- Root-install policy SHA-256: `e8e6806151bacb307e64586a97f7d460c6bac17281559b2b989f32483f49f74e`
- Root-helper interface policy SHA-256: `587df47b5c8f5527677b6750fe862c50639116b887309c3d132d654a1fd6c879`
- Source manifest SHA-256: `ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d`
- Requirements lock SHA-256: `404f695387cb0fa1939275647c73ed0f62ee81c358645a1fbbe69acedd805bc0`
- Wheel hash-set SHA-256: `92e45be55ecfd50fb250809e4416cebe10c427e50bc88f21fe7646ef4622b57f`
- Final release path: `/opt/ai-media-os/slack-worker/releases/slack-worker-5441bd1-1590693d6ae7`

## Time boundary

- UTC RFC3339 timestamps required
- Maximum validity: `900` seconds
- Expired or not-yet-valid capsules: rejected
- Time rechecked immediately before consumption

## Single-use consumption

The authorization ID and nonce must be atomically recorded under:

`/var/lib/ai-media-os-slack-release/install-authorizations`

The consumption record is a control-plane mutation and must precede all
release-tree, current-link, secret, Unit and database mutations.

After successful consumption, any installation failure requires a newly
issued authorization capsule. Consumption records may not be deleted to
permit retry.

## Prohibited operations

The capsule permits only installation of the bound release.

It does not permit:

- `current` link changes
- Secret migration
- Unit changes
- daemon reload
- Gate creation
- Service start
- Unit enable
- Production database writes

## Current state

- Capsule issued: no
- Capsule file created: no
- Authorization consumed: no
- Issuer tool implemented: no
- Root helper implemented: no
- Root helper installed: no
- Root installation authorized: no
- Root installation executed: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
