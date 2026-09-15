#!/usr/bin/env bash

set -u
set -o pipefail

ROOT="/home/deploy/ai_media_os"
PUBLIC_JSON="/var/lib/ai-media-os/public/ebook/new_releases.json"
OUT_ROOT="$ROOT/exchange/runtime/daily_new_release_roundup"
GATE_ADAPTER="$ROOT/scripts/check_xnr_roundup_metadata_gate.py"
CONTENT_GENERATOR="$ROOT/scripts/generate_xnr_roundup_content.py"
WP_APPLIER="$ROOT/scripts/apply_xnr_roundup_wordpress.php"
COVER_CATCHUP="$ROOT/scripts/catchup_today_verified_kobo_covers.py"
PUBLIC_EXPORTER="$ROOT/integrations/wordpress/ebook_new_releases/scripts/export_ready_approved_new_releases.py"
TARGET_DATE=""
SCHEMA_MAX_ITEMS=200
X_PREVIEW_ITEMS=3

while [ "$#" -gt 0 ]; do
    case "$1" in
        --date)
            TARGET_DATE="${2:-}"
            shift 2
            ;;
        --max-items)
            SCHEMA_MAX_ITEMS="${2:-200}"
            shift 2
            ;;
        --x-preview-items)
            X_PREVIEW_ITEMS="${2:-3}"
            shift 2
            ;;
        *)
            echo "UNKNOWN_ARGUMENT=$1"
            exit 1
            ;;
    esac
done

if [ -z "$TARGET_DATE" ]; then
    TARGET_DATE="$(TZ=Asia/Tokyo date +%Y-%m-%d)"
fi
if ! [[ "$TARGET_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=INVALID_TARGET_DATE"
    exit 40
fi
if ! [[ "$SCHEMA_MAX_ITEMS" =~ ^[0-9]+$ ]] || [ "$SCHEMA_MAX_ITEMS" -lt 1 ] || [ "$SCHEMA_MAX_ITEMS" -gt 200 ]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=INVALID_MAX_ITEMS"
    exit 40
fi
if ! [[ "$X_PREVIEW_ITEMS" =~ ^[0-9]+$ ]] || [ "$X_PREVIEW_ITEMS" -lt 3 ] || [ "$X_PREVIEW_ITEMS" -gt 5 ]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=INVALID_X_PREVIEW_ITEMS"
    exit 40
fi
if [ ! -f "$PUBLIC_JSON" ]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=PUBLIC_JSON_MISSING"
    exit 40
fi

if [ ! -f "$COVER_CATCHUP" ] || [ ! -f "$PUBLIC_EXPORTER" ]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=COVER_PREPARATION_UNAVAILABLE"
    exit 40
fi

DATE_COMPACT="${TARGET_DATE//-/}"
MONTH_RAW="$(printf '%s' "$TARGET_DATE" | cut -d- -f2)"
DAY_RAW="$(printf '%s' "$TARGET_DATE" | cut -d- -f3)"
DATE_LABEL="$((10#$MONTH_RAW))月$((10#$DAY_RAW))日"
OUTDIR="$OUT_ROOT/$DATE_COMPACT"
X_DRAFT="$OUTDIR/new_release_roundup_${DATE_COMPACT}_x_draft.txt"
RESULT="$OUTDIR/result.json"
AUTHORIZATION="$OUTDIR/metadata_gate_authorization.json"
PLAN="$OUTDIR/roundup_content_plan.json"
SOURCE_SNAPSHOT="$OUTDIR/public_source_authorized.snapshot.json"
mkdir -p "$OUTDIR"

run_gate() {
    python3 "$GATE_ADAPTER" \
        --public-json "$PUBLIC_JSON" \
        --date "$TARGET_DATE" \
        --max-items "$SCHEMA_MAX_ITEMS" \
        --authorization-file "$AUTHORIZATION" \
        "$@"
}

block() {
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED"
    echo "WORDPRESS_WRITE=NO"
    echo "WORDPRESS_PUBLISH=NO"
    echo "X_POST=NO"
    exit "${1:-40}"
}

echo "=== DAILY NEW RELEASE ROUNDUP ==="
echo "TARGET_DATE=$TARGET_DATE"
echo "SCHEMA_MAX_ITEMS=$SCHEMA_MAX_ITEMS"
echo "X_PREVIEW_ITEMS=$X_PREVIEW_ITEMS"

echo "=== 0. VERIFIED COVER PREPARATION ==="

# The roundup must not render empty book-cover frames.  Refresh the approved
# Kobo cover evidence first, then regenerate the public source from that exact
# DB state before taking the WordPress authorization snapshot.
COVER_CATCHUP_RESULT="$(
    PYTHONPATH="$ROOT" \
    "$ROOT/.venv/bin/python" \
    "$COVER_CATCHUP" \
    --execute \
    --release-date "$TARGET_DATE" \
    --max-items "$SCHEMA_MAX_ITEMS"
)"
COVER_CATCHUP_RC=$?
printf '%s\n' "$COVER_CATCHUP_RESULT"
[ "$COVER_CATCHUP_RC" -eq 0 ] || block "$COVER_CATCHUP_RC"

if printf '%s\n' "$COVER_CATCHUP_RESULT" | grep -q '^COVER_CATCHUP=PARTIAL$'; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=COVER_CATCHUP_PARTIAL"
    block 40
fi

PUBLIC_EXPORT_RESULT="$(
    PYTHONPATH="$ROOT" \
    "$ROOT/.venv/bin/python" \
    "$PUBLIC_EXPORTER" \
    --release-date "$TARGET_DATE" \
    --execute
)"
PUBLIC_EXPORT_RC=$?
printf '%s\n' "$PUBLIC_EXPORT_RESULT"
[ "$PUBLIC_EXPORT_RC" -eq 0 ] || block "$PUBLIC_EXPORT_RC"

COVER_SOURCE_CHECK="$(
python3 - "$PUBLIC_JSON" "$TARGET_DATE" "$SCHEMA_MAX_ITEMS" <<'PY_XNR_COVER_SOURCE'
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from app.services.xnr_roundup_candidate_projection import (
    build_context_candidate_payload,
)

raw_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
payload = build_context_candidate_payload(raw_payload)
target_date = sys.argv[2]
max_items = int(sys.argv[3])
items = [
    item for item in payload.get("new_releases", [])
    if isinstance(item, dict)
    and str(item.get("release_date") or "") == target_date
]

if not items:
    raise SystemExit("COVER_SOURCE_NO_TARGET_ITEMS")
if len(items) > max_items:
    raise SystemExit("COVER_SOURCE_ITEM_LIMIT_EXCEEDED")

missing_ids: list[str] = []
for item in items:
    image_url = str(item.get("image_url") or "").strip()
    parsed = urlparse(image_url)
    is_placeholder = any(
        marker in image_url.lower()
        for marker in ("noimage", "no-image", "no_image")
    )
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or is_placeholder
    ):
        missing_ids.append(str(item.get("item_id") or "UNKNOWN"))

if missing_ids:
    print("COVER_SOURCE_MISSING_IDS=" + ",".join(missing_ids))
    raise SystemExit("COVER_SOURCE_INCOMPLETE")

print("COVER_SOURCE_STATUS=PASS")
print("COVER_SOURCE_ITEM_COUNT=" + str(len(items)))
PY_XNR_COVER_SOURCE
)"
COVER_SOURCE_RC=$?
printf '%s\n' "$COVER_SOURCE_CHECK"
[ "$COVER_SOURCE_RC" -eq 0 ] || block 40

echo "=== 1. ROUNDUP PUBLIC SOURCE GATE ==="
GATE_RESULT="$(run_gate)"
GATE_RC=$?
printf '%s\n' "$GATE_RESULT"
[ "$GATE_RC" -eq 0 ] || block "$GATE_RC"

# XNR_DIGEST_CONTRACT_SPLIT_V1
#
# Authorization identity and publication identity are separate.
#
# Authorization:
#   candidate_ids + candidate_digests + item_count
#
# Publication:
#   plan.source_digest
#
# Build the plan only from the exact candidate snapshot that passed
# the authorization boundary.
echo "=== 1.5. BIND AUTHORIZED SOURCE SNAPSHOT ==="

SNAPSHOT_RESULT="$(
python3 - \
    "$PUBLIC_JSON" \
    "$AUTHORIZATION" \
    "$SOURCE_SNAPSHOT" \
    "$TARGET_DATE" \
    "$SCHEMA_MAX_ITEMS" \
<<'PY_XNR_SOURCE_SNAPSHOT'
from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile

# DIGEST_FIX1R_SHARED_CONTEXT_PROJECTION_V1
from app.services.xnr_roundup_candidate_projection import (
    build_context_candidate_payload,
)
from app.services.xnr_roundup_metadata_gate import (
    select_roundup_candidates,
)


source_path = Path(sys.argv[1])
authorization_path = Path(sys.argv[2])
snapshot_path = Path(sys.argv[3])
target_date = sys.argv[4]
max_items = int(sys.argv[5])


raw_payload = json.loads(
    source_path.read_text(
        encoding="utf-8"
    )
)

payload = build_context_candidate_payload(
    raw_payload
)

authorization = json.loads(
    authorization_path.read_text(
        encoding="utf-8"
    )
)

selection = select_roundup_candidates(
    payload,
    target_date=target_date,
    max_items=max_items,
)


authorized_ids = tuple(
    str(value)
    for value in authorization.get(
        "candidate_ids",
        (),
    )
)

selected_ids = tuple(
    str(value)
    for value in selection.candidate_ids
)

if selected_ids != authorized_ids:
    raise SystemExit(
        "AUTHORIZED_CANDIDATE_IDS_MISMATCH"
    )


authorized_digests = {
    str(key): str(value)
    for key, value in dict(
        authorization.get(
            "candidate_digests",
            {},
        )
    ).items()
}

selected_digests = {
    str(key): str(value)
    for key, value in dict(
        selection.candidate_digests
    ).items()
}

if selected_digests != authorized_digests:
    raise SystemExit(
        "AUTHORIZED_CANDIDATE_DIGESTS_MISMATCH"
    )


if int(
    authorization.get(
        "item_count",
        -1,
    )
) != int(selection.item_count):
    raise SystemExit(
        "AUTHORIZED_ITEM_COUNT_MISMATCH"
    )


if str(
    authorization.get(
        "target_date",
        "",
    )
) != target_date:
    raise SystemExit(
        "AUTHORIZED_TARGET_DATE_MISMATCH"
    )


snapshot_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

fd, temp_name = tempfile.mkstemp(
    prefix=snapshot_path.name + ".",
    suffix=".tmp",
    dir=snapshot_path.parent,
    text=True,
)

try:
    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:

        # AFF2_AUTHORIZATION_PUBLICATION_SPLIT_V1
        # Authorization uses the canonical EbookContext projection.
        # Publication preserves the full safe-published payload.
        json.dump(
            raw_payload,
            handle,
            ensure_ascii=False,
            indent=2,
        )

        handle.write("\n")
        handle.flush()
        os.fsync(
            handle.fileno()
        )

    Path(temp_name).replace(
        snapshot_path
    )

finally:
    Path(temp_name).unlink(
        missing_ok=True
    )


print(
    "AUTHORIZED_SOURCE_SNAPSHOT=PASS"
)

print(
    "AUTHORIZED_CANDIDATE_COUNT="
    + str(selection.item_count)
)
PY_XNR_SOURCE_SNAPSHOT
)"

SNAPSHOT_RC=$?

printf '%s\n' "$SNAPSHOT_RESULT"

[ "$SNAPSHOT_RC" -eq 0 ] || block 40

echo "=== 2. GENERATE FULL WORDPRESS PLAN / SHORT X PREVIEW ==="
GENERATOR_RESULT="$(
    python3 "$CONTENT_GENERATOR" \
        --public-json "$SOURCE_SNAPSHOT" \
        --date "$TARGET_DATE" \
        --date-label "$DATE_LABEL" \
        --x-preview-items "$X_PREVIEW_ITEMS" \
        --plan-file "$PLAN"
)"
GENERATOR_RC=$?
printf '%s\n' "$GENERATOR_RESULT"
[ "$GENERATOR_RC" -eq 0 ] || block "$GENERATOR_RC"

PLAN_CHECK="$(
python3 - "$PLAN" "$AUTHORIZATION" <<'PY'
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
authorization = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

if plan.get("target_date") != authorization.get("target_date"):
    raise SystemExit("PLAN_TARGET_DATE_MISMATCH")

if plan.get("total_item_count") != authorization.get("item_count"):
    raise SystemExit("PLAN_ITEM_COUNT_MISMATCH")

if plan.get("wordpress_item_count") != plan.get("total_item_count"):
    raise SystemExit("WORDPRESS_ITEM_COUNT_MISMATCH")

publication_digest = str(
    plan.get("source_digest")
    or ""
)

if (
    len(publication_digest) != 64
    or any(
        character not in "0123456789abcdef"
        for character in publication_digest
    )
):
    raise SystemExit(
        "PLAN_PUBLICATION_DIGEST_INVALID"
    )

print("PLAN_AUTHORIZATION_BINDING=PASS")
print("PUBLICATION_DIGEST=" + publication_digest)
print("ITEM_COUNT=" + str(plan["total_item_count"]))
PY
)"
PLAN_CHECK_RC=$?
printf '%s\n' "$PLAN_CHECK"
[ "$PLAN_CHECK_RC" -eq 0 ] || block 40
ITEM_COUNT="$(printf '%s\n' "$PLAN_CHECK" | sed -n 's/^ITEM_COUNT=//p')"

# AFF4_PUBLICATION_AFFILIATE_CONTRACT_V1
echo "=== 2.5. PUBLICATION AFFILIATE CONTRACT ==="

if ! PUBLICATION_CONTRACT_RESULT="$(
PYTHONPATH="$ROOT" \
"$ROOT/.venv/bin/python" - \
    "$SOURCE_SNAPSHOT" \
    "$PLAN" \
<<'PY_XNR_PUBLICATION_AFFILIATE_CONTRACT'
from __future__ import annotations

import json
import sys
from pathlib import Path

from app.services.xnr_roundup_publication_contract import (
    XnrRoundupPublicationContractError,
    validate_xnr_roundup_publication_contract,
)


source_path = Path(
    sys.argv[1]
)

plan_path = Path(
    sys.argv[2]
)

source_payload = json.loads(
    source_path.read_text(
        encoding="utf-8"
    )
)

plan = json.loads(
    plan_path.read_text(
        encoding="utf-8"
    )
)

try:
    result = (
        validate_xnr_roundup_publication_contract(
            source_payload=source_payload,
            plan=plan,
        )
    )
except XnrRoundupPublicationContractError as exc:
    print(
        "XNR_PUBLICATION_AFFILIATE_CONTRACT=BLOCKED"
    )
    print(
        "XNR_PUBLICATION_AFFILIATE_ERROR="
        + exc.code
    )

    if exc.detail:
        print(
            "XNR_PUBLICATION_AFFILIATE_DETAIL="
            + exc.detail
        )

    raise SystemExit(40)

print(
    "XNR_PUBLICATION_AFFILIATE_CONTRACT=PASS"
)

print(
    "AFFILIATE_EXPECTED_TOTAL="
    + str(
        result.expected_total
    )
)

print(
    "AFFILIATE_RENDERED_TOTAL="
    + str(
        result.rendered_total
    )
)

for store_key in (
    "kindle",
    "rakuten",
    "dmm",
):
    print(
        "AFFILIATE_"
        + store_key.upper()
        + "_EXPECTED="
        + str(
            result.expected_by_store[
                store_key
            ]
        )
    )

    print(
        "AFFILIATE_"
        + store_key.upper()
        + "_RENDERED="
        + str(
            result.rendered_by_store[
                store_key
            ]
        )
    )
PY_XNR_PUBLICATION_AFFILIATE_CONTRACT
)"; then
    printf '%s\n' \
      "$PUBLICATION_CONTRACT_RESULT"

    echo \
      "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=PUBLICATION_AFFILIATE_CONTRACT"

    block 40
fi

printf '%s\n' \
  "$PUBLICATION_CONTRACT_RESULT"

echo "=== 3. PRE-WORDPRESS SOURCE/DIGEST REVALIDATION ==="
REVALIDATE_RESULT="$(run_gate --revalidate)"
REVALIDATE_RC=$?
printf '%s\n' "$REVALIDATE_RESULT"
[ "$REVALIDATE_RC" -eq 0 ] || block "$REVALIDATE_RC"

echo "=== 3.5. DAILY NEW RELEASE OGP GENERATION ==="
OGP_IMAGE="$ROOT/exchange/runtime/ogp_daily_new_release/${TARGET_DATE}.png"
OGP_GENERATE_RESULT="$(
    "$ROOT/.venv/bin/python" \
    "$ROOT/scripts/generate_daily_new_release_ogp.py" \
    --date "$TARGET_DATE" \
    --plan-file "$PLAN"
)"
OGP_GENERATE_RC=$?
printf '%s\n' "$OGP_GENERATE_RESULT"
[ "$OGP_GENERATE_RC" -eq 0 ] || block "$OGP_GENERATE_RC"
[ -f "$OGP_IMAGE" ] || block 40

echo "=== 4. CREATE OR REPAIR WORDPRESS DRAFT ==="
WP_RESULT="$(
    env \
        XNR_PLAN_FILE="$PLAN" \
        TARGET_DATE="$TARGET_DATE" \
        php "$WP_APPLIER"
)"
WP_RC=$?
printf '%s\n' "$WP_RESULT"
[ "$WP_RC" -eq 0 ] || block "$WP_RC"
POST_ID="$(printf '%s\n' "$WP_RESULT" | sed -n 's/^POST_ID=//p')"
WP_ACTION="$(printf '%s\n' "$WP_RESULT" | sed -n 's/^WORDPRESS_ACTION=//p')"
[ -n "$POST_ID" ] || block 40


echo
echo "=== 4.5. DAILY NEW RELEASE OGP ATTACHMENT ==="
echo "OGP_TARGET_DATE=$TARGET_DATE"
echo "OGP_POST_ID=$POST_ID"
echo "OGP_IMAGE=$OGP_IMAGE"

# attach_daily_new_release_ogp.py verifies the uploaded media ID and the
# post's featured_media value.  A failure is blocking: a draft without its
# social thumbnail must never be reported as a successful roundup.
OGP_ATTACH_RESULT="$(
    "$ROOT/.venv/bin/python" \
    "$ROOT/scripts/attach_daily_new_release_ogp.py" \
    --post-id "$POST_ID" \
    --date "$TARGET_DATE" \
    --image "$OGP_IMAGE"
)"
OGP_ATTACH_RC=$?
printf '%s\n' "$OGP_ATTACH_RESULT"
[ "$OGP_ATTACH_RC" -eq 0 ] || block "$OGP_ATTACH_RC"
if printf '%s\n' "$OGP_ATTACH_RESULT" | grep -q '^OGP_ATTACH=ALREADY_PRESENT$'; then
    OGP_STATUS="ALREADY_ATTACHED"
else
    OGP_STATUS="ATTACHED"
fi
echo "OGP_STATUS=$OGP_STATUS"


python3 - "$PLAN" "$RESULT" "$TARGET_DATE" "$ITEM_COUNT" "$POST_ID" "$WP_ACTION" "$X_DRAFT" <<'PY'
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
path = Path(sys.argv[2])
payload = {
    "schema_version": "1.0",
    "runner": "X_NR_AUTO_1",
    "release_date": sys.argv[3],
    "item_count": int(sys.argv[4]),
    "wordpress_post_id": int(sys.argv[5]),
    "wordpress_action": sys.argv[6],
    "wordpress_status": "draft",
    "wordpress_publish_executed": False,
    "x_draft_file": sys.argv[7],
    "x_post_status": "DRAFT_ONLY",
    "x_post_executed": False,
    "article_url_state": "PLACEHOLDER",
    "human_review_required": True,
    "generated_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
}

def atomic_write(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        Path(name).replace(destination)
    finally:
        Path(name).unlink(missing_ok=True)

atomic_write(Path(sys.argv[7]), str(plan["x_draft_text"]))
atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
RESULT_RC=$?
[ "$RESULT_RC" -eq 0 ] || block 40

# XNR_ARTICLE_URL_FINALIZATION_V1
#
# The WordPress helper already performed its own readback.
# Consume that verified result; do not issue another WP write.
XNR_WP_STATUS="$(
    printf '%s\n' "${WP_RESULT}" \
    | awk -F= '/^POST_STATUS=/ { print $2; exit }'
)"

XNR_ARTICLE_URL="$(
    printf '%s\n' "${WP_RESULT}" \
    | awk -F= '
        /^PERMALINK=/ {
            value=substr($0,index($0,"=")+1)
        }
        END {
            print value
        }
    '
)"

if [[ -z "$XNR_WP_STATUS" ]]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=WORDPRESS_STATUS_READBACK_MISSING"
    block 40
fi

set +e

python3 - \
    "$RESULT" \
    "$X_DRAFT" \
    "$XNR_WP_STATUS" \
    "$XNR_ARTICLE_URL" \
<<'PY_XNR_URL_FINALIZER'
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import os
import sys
import tempfile


result_path = Path(sys.argv[1])
draft_path = Path(sys.argv[2])
wordpress_status = str(
    sys.argv[3] or ""
).strip().lower()
article_url = str(
    sys.argv[4] or ""
).strip()


def atomic_write(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

        Path(name).replace(path)

    finally:
        Path(name).unlink(
            missing_ok=True
        )


def valid_public_url(
    value: str,
) -> bool:
    if not value:
        return False

    if "{ARTICLE_URL}" in value:
        return False

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    if parsed.scheme.lower() != "https":
        return False

    if not parsed.netloc:
        return False

    if "/wp-admin/" in parsed.path.lower():
        return False

    return True


result = json.loads(
    result_path.read_text(
        encoding="utf-8",
    )
)

draft = draft_path.read_text(
    encoding="utf-8",
)

result["wordpress_status"] = (
    wordpress_status
)

# XNR_SCHEDULED_PERMALINK_FINALIZATION_V1
#
# WordPress has an authoritative pretty permalink for
# scheduled posts too. Do not force the post live early.
if wordpress_status in {"publish", "future"}:

    if not valid_public_url(
        article_url
    ):
        raise SystemExit(
            "INVALID_PUBLIC_ARTICLE_URL"
        )

    placeholder_count = draft.count(
        "{ARTICLE_URL}"
    )

    if placeholder_count == 1:
        draft = draft.replace(
            "{ARTICLE_URL}",
            article_url,
            1,
        )

    elif placeholder_count == 0:
        if article_url not in draft:
            raise SystemExit(
                "ARTICLE_URL_TOKEN_MISSING"
            )

    else:
        raise SystemExit(
            "MULTIPLE_ARTICLE_URL_PLACEHOLDERS"
        )

    if "{ARTICLE_URL}" in draft:
        raise SystemExit(
            "ARTICLE_URL_PLACEHOLDER_REMAINS"
        )

    result["article_url"] = article_url
    result[
        "article_url_state"
    ] = "WORDPRESS_PERMALINK"

else:
    # A date-based pretty permalink may change between
    # draft creation and publication. Do not guess it.
    result["article_url"] = ""
    result[
        "article_url_state"
    ] = "AWAITING_WORDPRESS_PUBLISH"


draft_digest = hashlib.sha256(
    draft.encode("utf-8")
).hexdigest()

result["x_draft_sha256"] = (
    draft_digest
)

atomic_write(
    draft_path,
    draft,
)

atomic_write(
    result_path,
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
)

print(
    "XNR_WORDPRESS_STATUS="
    + wordpress_status
)

print(
    "XNR_ARTICLE_URL_STATE="
    + str(
        result["article_url_state"]
    )
)

print(
    "XNR_ARTICLE_URL="
    + str(
        result["article_url"]
    )
)

print(
    "XNR_X_DRAFT_SHA256="
    + draft_digest
)
PY_XNR_URL_FINALIZER

XNR_URL_FINALIZER_RC=$?

set -e

if [[ "$XNR_URL_FINALIZER_RC" -ne 0 ]]; then
    echo "DAILY_NEW_RELEASE_ROUNDUP=BLOCKED CODE=ARTICLE_URL_FINALIZATION_FAILED"
    block 40
fi

echo "=== RESULT ==="
echo "DAILY_NEW_RELEASE_ROUNDUP=PASS"
echo "RELEASE_DATE=$TARGET_DATE"
echo "ITEM_COUNT=$ITEM_COUNT"
echo "WORDPRESS_POST_ID=$POST_ID"
echo "WORDPRESS_ACTION=$WP_ACTION"
echo "WORDPRESS_STATUS=${XNR_WP_STATUS^^}"
echo "X_DRAFT=$X_DRAFT"
echo "RESULT_FILE=$RESULT"
echo "WORDPRESS_PUBLISH=NO"
echo "X_POST=NO"
echo "NEXT=HUMAN_REVIEW"
