# SQL-B2-4B-5G-0 systemd Discovery Report

## Result

`PASS_PRODUCTION_READINESS_DISCOVERY`

## Git

- Branch: `feature/sql-b2-4b-slack-production-readiness`
- Commit: `d76612b`

## Runtime

- systemd 249 (249.11-0ubuntu3.21)
- Python: `3.10.12`
- Runtime path: `/usr/bin/python3.10`

## Credentials

- `/etc/ai-media-os/slack.env`: `600 deploy:deploy`
- `/etc/ai-media-os/credential.env`: `600 deploy:deploy`
- Secret values exposed in evidence: no

## Existing validator unit

- User/group: `deploy:deploy`
- `ProtectSystem=full`
- `ProtectHome=read-only`
- `PrivateTmp=yes`
- `PrivateDevices=no`
- `NoNewPrivileges=yes`
- `Restart=no`
- systemd exposure: `8.4 EXPOSED`

The exposure score applies to the existing credential validator,
not to the new Slack approval worker.

## Database findings

- Production DB mode: `644 deploy:deploy`
- SQLAlchemy engine and `SessionLocal` are created at module import.
- Database environment variables must therefore be finalized and
  validated before importing the worker.
- The initial readiness worker must use a dedicated copy database.
- Direct Slack approval against the production database remains
  prohibited.

## 5G design requirements

- Dedicated pre-import readiness guard
- Unit-level and Python-level `DRY_RUN` enforcement
- Readiness-only copy database
- No Linux capabilities
- Restricted devices, namespaces and kernel interfaces
- Address families restricted to:
  `AF_UNIX`, `AF_INET`, `AF_INET6`
- Network access retained for Slack Socket Mode
- SIGTERM graceful shutdown
- journald audit logging
- Automatic restart with rate limiting

## Governance

- `production_status=NO_GO`
- `safety_state=DISCOVERY_ONLY_NO_UNIT_INSTALLED`
- `production_slack_approval_allowed=false`
