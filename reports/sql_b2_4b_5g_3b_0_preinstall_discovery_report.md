# SQL-B2-4B-5G-3B-0 Preinstall Discovery Report

## Result

`PASS_PREINSTALL_DISCOVERY_FAIL_CLOSED_NO_GO`

## Git

- Branch: `feature/sql-b2-4b-slack-production-readiness`
- Source commit: `538e2a2`

## Repository Unit

- ExecCondition present: yes
- systemd verification: PASS
- SHA-256: `ea27ffcff758a32020102f35a4df025aba8358501a6798d33f0ba069162005fc`
- Ready for controlled installation: yes

## Installed Unit

- Updated: no
- Contains new ExecCondition: no
- Differs from repository Unit: yes
- SHA-256: `94b6aaac4f43605996eec4e3e79ee50eb7523e5efe50bf447069dc9489b4681e`

## Approval gate

- Owner contract: `root`
- Group contract: `root`
- Mode contract: `0644`
- Gate present: no
- Approval: `NOT_APPROVED`

## Fail-closed check

- Readiness health: `PASS`
- Autostart command exit code: `3`
- Final decision: `NO_GO`

## Database safety

- Production database unchanged: yes
- Readiness quick check: `ok`
- Readiness approval requests: `0`

## systemd state

- Active state: `inactive`
- Substate: `dead`
- Unit enabled: no
- Service running: no
- Main PID: `0`

## Governance

- `production_status=NO_GO`
- `safety_state=PREINSTALL_DISCOVERY_COMPLETE_INSTALL_NOT_EXECUTED`
- `installed_unit_change_allowed=false`
- `automatic_start_allowed=false`
- `production_slack_approval_allowed=false`
