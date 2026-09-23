from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo


ROOT = Path("/home/deploy/ai_media_os")

AUTOFILL = (
    ROOT
    / "scripts"
    / "run_new_release_autofill_v1.py"
)

STATE = (
    ROOT
    / "exchange"
    / "state"
    / "new_release_autofill_daily_v1.json"
)

JST = ZoneInfo("Asia/Tokyo")


def load_state() -> dict:
    try:
        value = json.loads(
            STATE.read_text(
                encoding="utf-8"
            )
        )

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    except Exception:
        return {}


def save_state(
    *,
    target_date: str,
) -> None:
    STATE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "target_date": target_date,
        "completed_at": datetime.now(
            JST
        ).isoformat(),
        "status": "PASS",
    }

    temporary = STATE.with_suffix(
        ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(STATE)


def main() -> int:
    now = datetime.now(JST)

    target = (
        now.date()
        + timedelta(days=1)
    )

    target_text = target.isoformat()

    print(
        "NEW_RELEASE_AUTOFILL_TARGET_DATE="
        + target_text
    )

    state = load_state()

    if (
        state.get("target_date")
        == target_text
        and state.get("status")
        == "PASS"
    ):
        print(
            "NEW_RELEASE_AUTOFILL_STATUS="
            "SKIP_ALREADY_DONE"
        )
        print(
            "NEW_RELEASE_AUTOFILL_WRITE=NO"
        )
        print(
            "WORDPRESS_WRITE=NO"
        )
        print(
            "X_POST=NO"
        )
        return 0

    env = os.environ.copy()

    credential = Path(
        "/etc/ai-media-os/credential.env"
    )

    # The systemd unit may already supply these.
    # If not, the existing protected env file is
    # loaded by a tiny shell child without printing it.
    command = [
        sys.executable,
        str(AUTOFILL),
        "--target-date",
        target_text,
        "--max-items",
        "200",
        "--execute",
        "--kobo-pacing-seconds",
        "1.0",
        "--dmm-pacing-seconds",
        "1.0",
        "--amazon-request-interval-seconds",
        "1.25",
    ]

    if credential.is_file():
        quoted = " ".join(
            subprocess.list2cmdline(
                [part]
            )
            for part in command
        )

        shell_command = (
            "set -a; "
            ". /etc/ai-media-os/credential.env; "
            "set +a; "
            "exec "
            + quoted
        )

        completed = subprocess.run(
            [
                "/bin/bash",
                "-c",
                shell_command,
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    else:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    if completed.stdout:
        print(
            completed.stdout,
            end=(
                ""
                if completed.stdout.endswith("\n")
                else "\n"
            ),
        )

    if completed.stderr:
        print(
            completed.stderr,
            file=sys.stderr,
            end=(
                ""
                if completed.stderr.endswith("\n")
                else "\n"
            ),
        )

    print(
        "NEW_RELEASE_AUTOFILL_CHILD_RC="
        + str(completed.returncode)
    )

    if completed.returncode != 0:
        print(
            "NEW_RELEASE_AUTOFILL_STATUS=FAILED"
        )
        print(
            "NEW_RELEASE_AUTOFILL_WRITE="
            "UNKNOWN"
        )
        print(
            "WORDPRESS_WRITE=NO"
        )
        print(
            "X_POST=NO"
        )
        return completed.returncode

    save_state(
        target_date=target_text
    )

    print(
        "NEW_RELEASE_AUTOFILL_STATUS=PASS"
    )
    print(
        "NEW_RELEASE_AUTOFILL_WRITE="
        "BOUNDED"
    )
    print(
        "WORDPRESS_WRITE=NO"
    )
    print(
        "X_POST=NO"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
