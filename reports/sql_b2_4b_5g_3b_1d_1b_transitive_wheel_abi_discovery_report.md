# SQL-B2-4B-5G-3B-1D-1B Transitive Wheel and ABI Discovery

## Result

`PASS_TRANSITIVE_DEPENDENCY_WHEEL_HASH_ABI_OFFLINE_INSTALL_VALIDATED_NO_PERSISTENT_HOST_CHANGE_NO_GO`

## Transitive dependency closure

- Distribution count: `5`
- Dependency edge count: `3`
- Unresolved dependency: none
- Dynamic dependency gap identified: none

| Distribution | Version | Wheel SHA-256 |
|---|---:|---|
| `greenlet` | `3.5.3` | `9bcd2d72ccd70a1ec68ba6ef93e7fbb4420ef9997dabc7010d893bd4015e0bec` |
| `slack_bolt` | `1.29.0` | `1835b66b778158f3af0da77603aa18d7dfd82fd9b9a985e25c752f95050ab826` |
| `slack_sdk` | `3.43.0` | `4b6557c65577fc172f685af218b811f9f3b4909e24cddd839ada09565f10c585` |
| `SQLAlchemy` | `2.0.51` | `2e54ff2dd657f2e3e0fbf2b097db1182f7bfea263eca4353f00065bae2a67c3d` |
| `typing_extensions` | `4.16.0` | `481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8` |

## Hash lock

- Repository path: `config/slack_worker_release_requirements_hash_locked.txt`
- SHA-256: `404f695387cb0fa1939275647c73ed0f62ee81c358645a1fbbe69acedd805bc0`
- Exact wheel set validated: yes
- Wheel CRC validated: yes
- Wheel/installed-version binding validated: yes
- Host compatibility tags validated: yes

## Offline rebuild

- Installation from local Wheelhouse only: passed
- `--require-hashes`: enforced
- Network used during installation: no
- Runtime import test: passed
- `pip check`: passed
- Version source: `importlib.metadata`

## Native ABI

- Native extension files: `8`
- Native distributions: `greenlet`, `SQLAlchemy`
- Architecture: `x86_64`
- Host glibc: `2.35`
- Maximum observed required glibc: `2.14`
- Shared-library resolution: passed
- glibc compatibility: passed
- `ldd` executed: no

## Safety

- Slack secret content read: no
- Slack secret content hashed: no
- Slack secret content output: no
- Production database unchanged: yes
- Readiness database quick check: `ok`
- Approval requests: `0`
- Unit enabled: no
- Service running: no
- Autostart gate present: no

## Decision

- Root-managed release-bundle installation: not executed
- Secret-boundary migration: not executed
- Persistent host change: `HOLD`
- Unit change: `HOLD`
- Gate creation: `HOLD`
- Service start: prohibited
- Unit enable: prohibited
- Autostart approval: `NOT_APPROVED`
- Final decision: `NO_GO`
