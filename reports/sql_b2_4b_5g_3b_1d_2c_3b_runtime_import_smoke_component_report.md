# SQL-B2-4B-5G-3B-1D-2C-3B Guarded Import Smoke Component

## Result

`PASS_GUARDED_IMPORT_SMOKE_ENGINE_CONSTRUCTION_OBSERVED_CONNECTIONS_BLOCKED_REPOSITORY_ONLY_NO_GO`

## Corrected boundary

The source imports require construction of one SQLAlchemy Engine object
from `app.db.session`. Engine construction does not itself establish a
database connection.

The corrected smoke boundary therefore:

- Allows and counts SQLAlchemy Engine construction
- Rejects `Engine.connect()`
- Rejects `Engine.raw_connection()`
- Rejects `Engine.begin()`
- Rejects `sqlite3.connect()`
- Rejects `sqlite3.dbapi2.connect()`
- Rejects network socket creation
- Rejects child-process creation
- Rejects configured secret and database paths
- Does not execute either service entrypoint

## Validation evidence

- Release ID: `slack-worker-5441bd1-1590693d6ae7`
- Source modules imported: `16`
- Engine construction count: `1`
- SQLite connection attempts observed: `0`
- Network operations observed: `0`
- Child processes observed: `0`
- Secret-path accesses observed: `0`
- Entrypoint executions: `0`

## Boundary

No runtime was installed outside `/tmp`. No service was started or
enabled. No Slack secret content was read.


## SQLAlchemy preload correction

SQLAlchemy and its engine modules are loaded before socket and process
guards are installed. This prevents SQLAlchemy's own initialization
from encountering a replaced socket class when SQLAlchemy was not
listed as an explicit external module.

After preload, the runtime guards still reject:

- SQLAlchemy connection methods
- SQLite DB-API connections
- Network socket creation
- Child-process creation
- Forbidden-path access

Final decision: `NO_GO`
