# SQL-B2-4B-5G-3B-1D-1C-1 Symlink Contract Correction

## Result

`PASS_RELEASE_BUNDLE_SYMLINK_CONTRACT_CORRECTED_DESIGN_ONLY_NO_HOST_CHANGE_NO_GO`

## Correction

The previous contract rejected every symlink in the release tree while
also requiring a governed `current` activation link and a Python virtual
environment whose interpreter is normally a symlink.

The ambiguous blanket rule has been replaced with explicit boundaries.

## Rejected links

- Symlinks inside the copied source tree
- Symlinks inside the manifest tree
- Unapproved symlinks elsewhere in a release
- Virtualenv links resolving to service-user-writable targets

## Allowed governed links

- `/opt/ai-media-os/slack-worker/current`
- Virtualenv-internal interpreter links resolving to root-managed targets

## Current-link requirements

- Owner: `root`
- Group: `root`
- Target must be a direct child of the release root
- Target must not be writable by the service user
- Atomic replacement remains required
- Separate activation authorization remains required

## Safety

- Root release installation: not executed
- Current link creation: not executed
- Secret migration: not executed
- Unit change: not executed
- Daemon reload: not executed
- Gate creation: not executed
- Service start: prohibited
- Unit enable: prohibited
- Final decision: `NO_GO`
