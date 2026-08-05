# SQL-B2-4B-5G-3B-1D-2C-2 Real Release Bundle Sandbox Adapter

## Result

`PASS_REAL_RELEASE_INPUT_TO_PREPARED_SANDBOX_BUNDLE_ADAPTER_TMP_ONLY_NO_HOST_INSTALL_NO_GO`

## Purpose

This phase maps the committed Slack worker source manifest and locked
wheelhouse into the exact prepared-bundle format accepted by the Phase
1D-2C-1 sandbox installer core.

## Bound input

- Release ID: `slack-worker-5441bd1-1590693d6ae7`
- Repository source files: `16`
- Locked wheels: `5`
- Total prepared payload files: `21`
- Candidate data files: `0`

## Mapping

Repository sources are mapped as:

`src/<repository-relative-path>`

Locked wheels are mapped as:

`wheelhouse/<wheel-filename>`

All output payload files use mode `0644`. The source-side group-write
mode `0664` is not propagated.

## Excluded legacy content

The existing Phase 1D-2A dry-run tree is not copied because it contains
a complete virtual environment and symbolic-link layout.

The adapter does not copy:

- `current`
- Existing `releases`
- Existing virtual environments
- Cached bytecode
- Installed package metadata
- Any unlisted file

## Transaction behavior

- Output must be below `/tmp`
- Exclusive adapter lock
- Dedicated staging root
- Descriptor-based input and output
- Input size and SHA-256 validation
- Exclusive destination-file creation
- File and directory `fsync`
- Atomic staging-to-output rename
- Precommit staging rollback
- Validation through the Phase 1D-2C-1 sandbox core
- Idempotent acceptance of an existing valid output

## Current state

- Sandbox adapter implemented: yes
- Real-input sandbox validation required: yes
- Root release installation authorized: no
- Root release installation executed: no
- Authorization capsule consumed: no
- Host consumption record created: no
- Root helper implemented: no
- Root helper installed: no
- Current link created: no
- Service started: no
- Unit enabled: no
- Final decision: `NO_GO`
