# DB-SAFE-TST-5A Slack Worker Release Rebinding Control Plane

## Result

`PASS_DRY_RUN_CANDIDATE_NOT_APPROVED`

The production release manifest, release ID, existing validator, downstream
policies, production source, and production runtime were not changed.  The
candidate was generated only below `/tmp`.

## Current binding and chain

- Current manifest: `config/slack_worker_release_source_manifest.json`
- Current manifest file SHA-256: `ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d`
- Direct mutable policy binders: `9`
  - Eight policies contain the exact manifest file SHA.
  - The release bundle policy binds the derived release ID and release path.
- Direct immutable historical evidence binders: `2`
- Indirect mutable policy binders: `10`
- Total chain artifacts: `21`
- Future candidate policy updates modeled: `19`
- Circular dependency: not detected

The immutable dry-run and host-discovery evidence remain bound to the release
that they historically observed.  They must not be rewritten during a future
rebinding.

## Runtime dependency closure

The closure was built by recursively parsing Python AST imports from both
runtime scripts.  It records direct, lazy, optional, type-check-only, dynamic,
and subprocess import behavior.  The existing runtime-import-smoke policy was
used as a declared-module baseline; no Slack runtime was started.

Entrypoint evidence:

- Source manifest: `src/scripts/run_slack_approval_readiness.py`
- Release policy: `/opt/ai-media-os/slack-worker/current/src/scripts/run_slack_approval_readiness.py`
- Repository systemd unit `ExecStartPre` and `ExecStart`:
  `scripts/run_slack_approval_readiness.py`
- Guarded lazy transition: `run_slack_approval_readiness.py` imports
  `run_slack_approval_socket.py` only after readiness validation

Closure result:

- Required Python source files: `17`
- Required safety files: `app/db/access_guard.py`, `app/db/config.py`,
  `app/db/session.py`
- Optional external runtime import: `slack_bolt`
- Local subprocess calls: none
- Unresolved local or dynamic dependencies: none
- Newly required source absent from the current manifest:
  `app/db/access_guard.py`

## Current source evaluation

All existing bound sources are retained.  No source was excluded merely
because static analysis might not discover it.

| Source | Manifest/current state | Closure | Category | Candidate decision |
|---|---|---|---|---|
| `app/db/base.py` | matched | required runtime | baseline unchanged | retain |
| `app/db/config.py` | modified | required safety | DB safety refactor | retain, review required |
| `app/db/models/__init__.py` | matched | required runtime | baseline unchanged | retain |
| `app/db/models/ebook.py` | matched | required runtime | baseline unchanged | retain |
| `app/db/models/workflow_approval.py` | matched | required runtime | baseline unchanged | retain |
| `app/db/repositories/workflow_approval_repository.py` | matched | required runtime | baseline unchanged | retain |
| `app/db/repositories/workflow_repository.py` | matched | required runtime | baseline unchanged | retain |
| `app/db/repositories/workflow_state_repository.py` | modified | required runtime | WordPress state reconciliation | retain, review required |
| `app/db/session.py` | modified | required safety | DB safety refactor | retain, review required |
| `app/services/slack_approval_message_service.py` | matched | required runtime | baseline unchanged | retain |
| `app/services/slack_approval_socket_service.py` | matched | required runtime | baseline unchanged | retain |
| `app/services/slack_readiness_guard.py` | matched | required runtime | baseline unchanged | retain |
| `app/services/workflow_approval_service.py` | matched | required runtime | baseline unchanged | retain |
| `scripts/__init__.py` | matched | required runtime | baseline unchanged | retain |
| `scripts/run_slack_approval_readiness.py` | matched | required runtime | baseline unchanged | retain |
| `scripts/run_slack_approval_socket.py` | modified | required runtime | Slack runtime lifecycle | retain, review required |
| `app/db/access_guard.py` | not recorded | required safety | DB safety refactor | add, review required |

The four prior bodies are available from design source commit
`5441bd1506bb28d1938865f8818c60182df89058` and were compared with the current
files.  No previous body was fabricated from a SHA.

## Review units

### UNIT_DB_SAFETY — NOT_APPROVED

- Sources: `app/db/config.py`, `app/db/session.py`, `app/db/access_guard.py`
- Purpose: production path centralization, test-only fail-closed target checks,
  URI/symlink/hard-link resolution, lazy engine creation, and import-side-effect
  removal
- Runtime: production engine construction remains available and WAL remains
  enabled outside tests
- Security: database target validation is strengthened
- Permission/network: no expansion and no network change
- Rollback: all three files must be treated as a coordinated unit
- Evidence: production database access guard and runtime import smoke tests

### UNIT_WORKFLOW_STATE — NOT_APPROVED

- Source: `app/db/repositories/workflow_state_repository.py`
- Purpose: WordPress post ID and draft-state reconciliation
- Runtime: imported transitively by the Slack approval workflow service
- Security: database mutation surface changed and requires separate review
- Permission/network: no expansion and no network change
- Rollback: callers of the new reconciliation methods must be checked first
- Evidence: WordPress state reconciliation and history-constraint tests

### UNIT_SLACK_RUNTIME — NOT_APPROVED

- Source: `scripts/run_slack_approval_socket.py`
- Purpose: delayed Slack Bolt import, factory injection, fixed dependency error,
  idempotent close, and SIGTERM/KeyboardInterrupt lifecycle
- Runtime: worker construction and shutdown behavior changed
- Security: secret and network boundaries are unchanged
- Permission: no expansion
- Rollback: eager imports and the prior signal lifecycle form one rollback unit
- Evidence: Slack socket runner and runtime import smoke tests

## Review schema design

No existing general review schema binds all source, closure, manifest, validator,
and downstream-plan digests with expiration, single-use, and supersession rules.
The control policy therefore defines the inactive schema candidate
`SLACK_WORKER_RELEASE_REBINDING_REVIEW`.

Required future bindings include the current and candidate manifest SHA,
dependency closure SHA, each review-unit SHA, every source SHA, downstream plan
SHA, and validator-contract SHA.  A future review must explicitly record a
human decision, expiration, single-use handling, and superseded-source handling.
It cannot authorize deployment or runtime execution implicitly.

## Dry-run candidate

- Directory: `/tmp/db-safe-tst-5a-candidate-final`
- Candidate manifest:
  `/tmp/db-safe-tst-5a-candidate-final/candidate-manifest.json`
- Candidate manifest file SHA-256:
  `50928b898f1e4b398b26a7594173b58b70424dc57a1ecf5f23e957f6ece5c657`
- Candidate ID:
  `slack-worker-CANDIDATE-NOT-APPROVED-bd534a267f64`
- Dependency closure SHA-256:
  `74a333b919f52fd10fd15b3d72e37194cd8501c694752e2e420b3baa921b29c4`
- Downstream plan:
  `/tmp/db-safe-tst-5a-candidate-final/downstream-rebinding-plan.json`
- Downstream plan content SHA-256:
  `1a22657915053e43b6e45a5d7cf6a462a3e8febe899f67073faf4f0c8ced1675`
- Status: `CANDIDATE_NOT_APPROVED`
- Deployment allowed: `false`
- Runtime execution allowed: `false`
- Review-incomplete sources: `5`

The generator recomputes the AST closure and hashes each source through a
single `O_NOFOLLOW` descriptor.  It does not clone the production manifest and
replace selected SHA fields.  Output is restricted below `/tmp`, existing or
symlink output is rejected, and files are created exclusively with mode `0600`.

## Validator hardening handoff for DB-SAFE-TST-5B

The existing validator was not modified.  TST-5B should:

1. Open the manifest with `O_NOFOLLOW | O_CLOEXEC` and require a regular,
   single-link file through `fstat`.
2. Reject absolute paths, backslashes, empty components, and `..` traversal.
3. Require resolved sources to remain under the repository root.
4. Open each source once with `O_NOFOLLOW`, then hash only that descriptor.
5. Compare pre/post `fstat` identity, size, and mtime to detect replacement.
6. Reject output symlinks and symlink ancestry.
7. Keep bundle-copy custody, destination exclusivity, fsync, and copy
   revalidation in the existing downstream adapter rather than duplicating
   those transaction responsibilities in the source-manifest validator.

## Test evidence

- New control-plane tests: `14 passed`
- Review-unit source tests: `45 passed`
- Existing release tests: `2 failed`, expected before formal rebinding
- Existing failure: `SOURCE_SHA_MISMATCH: app/db/config.py`
- Slack communication: not used
- Production database opened as SQLite: no

