#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
SOURCE_REL="${BASE_REL}/i2f3e-j-root-deployment-execution-packet-r1-r2-r1-nested-source-path-binding-correction-preparation-20260726T070939Z-534096"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
NEW_REL="${BASE_REL}/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-negative-test-mutation-indentation-correction-preparation-${RUN_ID}"
NEW_ROOT="${REPO_ROOT}/${NEW_REL}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$SOURCE_ROOT"

cd "$REPO_ROOT"

printf '\n===== FAILED PARTIAL R1-R2-R1 FIXED IDENTITY REVIEW =====\n'
sha256sum -c <<SHAS
0d712c6e12dc0b98213ca1995e4f22d1e9088ab5ffc31a97a497d60ba769fa53  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/root_deployment_execution_once_r1.py
efdabbe83c61a2618128f5518a726f007062bba0e91959a01eed1f380d4b2d74  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/validate_root_deployment_execution_packet_r1.py
d626c22cab0e11f89323df6a5b81cb8b44a15d614928220e16d5954ac9676f99  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/test_root_deployment_execution_packet_r1_negative.py
d626c22cab0e11f89323df6a5b81cb8b44a15d614928220e16d5954ac9676f99  ${SOURCE_ROOT}/packet-snapshot/r1-r1-validator-target/packet-snapshot/candidate-artifacts/test_root_deployment_execution_packet_r1_negative.py
SHAS

mkdir "$NEW_ROOT"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" "$SOURCE_ROOT" "$NEW_ROOT" "$NEW_REL" <<'PY'

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve(strict=True)
source_root = Path(sys.argv[2]).resolve(strict=True)
new_root = Path(sys.argv[3]).resolve(strict=True)
new_relative = sys.argv[4]

packet_root = new_root / "packet-snapshot"
candidate_root = packet_root / "candidate-artifacts"
source_snapshot = packet_root / "source-r1-r2-r1-partial-evidence-snapshot"
validation_target = packet_root / "r1-r1-validator-target"
log_root = packet_root / "validation-logs"

PHASE = "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-EXECUTION-PACKET-R1-R2-R2"
SOURCE_TREE_SHA = "2cddf82d05ed1aade2fc48eee39ec468f3ea37f9f444516e600776032527eb17"
WRAPPER_SHA = "0d712c6e12dc0b98213ca1995e4f22d1e9088ab5ffc31a97a497d60ba769fa53"
VALIDATOR_SHA = "efdabbe83c61a2618128f5518a726f007062bba0e91959a01eed1f380d4b2d74"
FAILED_NEGATIVE_SHA = "d626c22cab0e11f89323df6a5b81cb8b44a15d614928220e16d5954ac9676f99"
CORRECTED_NEGATIVE_SHA = "6dad37c21c35921587e1839002a2435ebab4f4b88399f6035a9dcd9569156ca7"

corrected_negative = base64.b64decode(
    "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCgppbXBvcnQgYXN0CmltcG9ydCBoYXNobGliCmltcG9ydCBpbXBvcnRsaWIudXRpbAppbXBvcnQganNvbgppbXBvcnQgc2h1dGlsCmltcG9ydCB0ZW1wZmlsZQppbXBvcnQgdW5pdHRlc3QKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCgpIRVJFID0gUGF0aChfX2ZpbGVfXykucmVzb2x2ZSgpLnBhcmVudApFVklERU5DRV9ST09UID0gSEVSRS5wYXJlbnQucGFyZW50ClZBTElEQVRPUiA9IEhFUkUgLyAidmFsaWRhdGVfcm9vdF9kZXBsb3ltZW50X2V4ZWN1dGlvbl9wYWNrZXRfcjEucHkiClNQRUMgPSBpbXBvcnRsaWIudXRpbC5zcGVjX2Zyb21fZmlsZV9sb2NhdGlvbigicjFyMV92YWxpZGF0b3IiLCBWQUxJREFUT1IpCmFzc2VydCBTUEVDIGlzIG5vdCBOb25lIGFuZCBTUEVDLmxvYWRlciBpcyBub3QgTm9uZQpNT0RVTEUgPSBpbXBvcnRsaWIudXRpbC5tb2R1bGVfZnJvbV9zcGVjKFNQRUMpClNQRUMubG9hZGVyLmV4ZWNfbW9kdWxlKE1PRFVMRSkKCgpkZWYgc2hhMjU2KHBhdGg6IFBhdGgpIC0+IHN0cjoKICAgIHJldHVybiBoYXNobGliLnNoYTI1NihwYXRoLnJlYWRfYnl0ZXMoKSkuaGV4ZGlnZXN0KCkKCgpjbGFzcyBSMVIxTmVnYXRpdmVUZXN0cyh1bml0dGVzdC5UZXN0Q2FzZSk6CiAgICBkZWYgc2V0VXAoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLnRlbXAgPSB0ZW1wZmlsZS5UZW1wb3JhcnlEaXJlY3RvcnkocHJlZml4PSIzZS1qLXIxLXIxLW5lZ2F0aXZlLSIpCiAgICAgICAgc2VsZi5yb290ID0gUGF0aChzZWxmLnRlbXAubmFtZSkgLyAiZXZpZGVuY2UiCiAgICAgICAgc2h1dGlsLmNvcHl0cmVlKEVWSURFTkNFX1JPT1QsIHNlbGYucm9vdCkKCiAgICBkZWYgdGVhckRvd24oc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLnRlbXAuY2xlYW51cCgpCgogICAgZGVmIHZhbGlkYXRlKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgTU9EVUxFLnZhbGlkYXRlKHNlbGYucm9vdCkKCiAgICBkZWYgbG9hZF9qc29uKHNlbGYsIHJlbGF0aXZlOiBzdHIpOgogICAgICAgIHBhdGggPSBzZWxmLnJvb3QgLyByZWxhdGl2ZQogICAgICAgIHJldHVybiBwYXRoLCBqc29uLmxvYWRzKHBhdGgucmVhZF90ZXh0KGVuY29kaW5nPSJ1dGYtOCIpKQoKICAgIGRlZiB3cml0ZV9qc29uKHNlbGYsIHBhdGg6IFBhdGgsIHZhbHVlKSAtPiBOb25lOgogICAgICAgIHBhdGgud3JpdGVfdGV4dChqc29uLmR1bXBzKHZhbHVlLCBzb3J0X2tleXM9VHJ1ZSwgaW5kZW50PTIpICsgIlxuIiwgZW5jb2Rpbmc9InV0Zi04IikKCiAgICBkZWYgbXV0YXRlX2pzb24oc2VsZiwgcmVsYXRpdmU6IHN0ciwgbXV0YXRlKSAtPiBOb25lOgogICAgICAgIHBhdGgsIHZhbHVlID0gc2VsZi5sb2FkX2pzb24ocmVsYXRpdmUpCiAgICAgICAgbXV0YXRlKHZhbHVlKQogICAgICAgIHNlbGYud3JpdGVfanNvbihwYXRoLCB2YWx1ZSkKICAgICAgICBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCkKCiAgICBkZWYgd3JhcHBlcl9wYXRoKHNlbGYpIC0+IFBhdGg6CiAgICAgICAgcmV0dXJuIHNlbGYucm9vdCAvICJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9yb290X2RlcGxveW1lbnRfZXhlY3V0aW9uX29uY2VfcjEucHkiCgogICAgZGVmIG11dGF0ZV93cmFwcGVyKHNlbGYsIG9sZDogc3RyLCBuZXc6IHN0ciwgKiwgY291bnQ6IGludCA9IDEpIC0+IE5vbmU6CiAgICAgICAgcGF0aCA9IHNlbGYud3JhcHBlcl9wYXRoKCkKICAgICAgICB0ZXh0ID0gcGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICBzZWxmLmFzc2VydEdyZWF0ZXJFcXVhbCh0ZXh0LmNvdW50KG9sZCksIGNvdW50KQogICAgICAgIHBhdGgud3JpdGVfdGV4dCh0ZXh0LnJlcGxhY2Uob2xkLCBuZXcsIGNvdW50KSwgZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCkKCiAgICBkZWYgbXV0YXRlX3ByZWZsaWdodF9jYWxsKAogICAgICAgIHNlbGYsCiAgICAgICAgZnVuY3Rpb25fbmFtZTogc3RyLAogICAgICAgIHJlcGxhY2VtZW50X3NvdXJjZTogc3RyLAogICAgICAgICosCiAgICAgICAgZXhwZWN0ZWRfYXJnX25hbWVzOiB0dXBsZVtzdHIsIC4uLl0sCiAgICApIC0+IE5vbmU6CiAgICAgICAgcGF0aCA9IHNlbGYud3JhcHBlcl9wYXRoKCkKICAgICAgICB0ZXh0ID0gcGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICB0cmVlID0gYXN0LnBhcnNlKHRleHQpCiAgICAgICAgcHJlZmxpZ2h0X25vZGVzID0gWwogICAgICAgICAgICBub2RlCiAgICAgICAgICAgIGZvciBub2RlIGluIHRyZWUuYm9keQogICAgICAgICAgICBpZiBpc2luc3RhbmNlKG5vZGUsIGFzdC5GdW5jdGlvbkRlZikgYW5kIG5vZGUubmFtZSA9PSAicHJlZmxpZ2h0IgogICAgICAgIF0KICAgICAgICBzZWxmLmFzc2VydEVxdWFsKGxlbihwcmVmbGlnaHRfbm9kZXMpLCAxKQogICAgICAgIGNhbGxfc3RhdGVtZW50czogbGlzdFthc3QuRXhwcl0gPSBbXQogICAgICAgIGZvciBub2RlIGluIGFzdC53YWxrKHByZWZsaWdodF9ub2Rlc1swXSk6CiAgICAgICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKG5vZGUsIGFzdC5FeHByKToKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIHZhbHVlID0gbm9kZS52YWx1ZQogICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZSh2YWx1ZSwgYXN0LkNhbGwpOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UodmFsdWUuZnVuYywgYXN0Lk5hbWUpOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgaWYgdmFsdWUuZnVuYy5pZCA9PSBmdW5jdGlvbl9uYW1lOgogICAgICAgICAgICAgICAgY2FsbF9zdGF0ZW1lbnRzLmFwcGVuZChub2RlKQogICAgICAgIHNlbGYuYXNzZXJ0RXF1YWwobGVuKGNhbGxfc3RhdGVtZW50cyksIDEpCiAgICAgICAgc3RhdGVtZW50ID0gY2FsbF9zdGF0ZW1lbnRzWzBdCiAgICAgICAgY2FsbCA9IHN0YXRlbWVudC52YWx1ZQogICAgICAgIGFzc2VydCBpc2luc3RhbmNlKGNhbGwsIGFzdC5DYWxsKQogICAgICAgIGFjdHVhbF9hcmdfbmFtZXMgPSB0dXBsZSgKICAgICAgICAgICAgYXJndW1lbnQuaWQgaWYgaXNpbnN0YW5jZShhcmd1bWVudCwgYXN0Lk5hbWUpIGVsc2UgIjxOT05fTkFNRT4iCiAgICAgICAgICAgIGZvciBhcmd1bWVudCBpbiBjYWxsLmFyZ3MKICAgICAgICApCiAgICAgICAgc2VsZi5hc3NlcnRFcXVhbChhY3R1YWxfYXJnX25hbWVzLCBleHBlY3RlZF9hcmdfbmFtZXMpCiAgICAgICAgc2VsZi5hc3NlcnRFcXVhbChjYWxsLmtleXdvcmRzLCBbXSkKICAgICAgICBzZWxmLmFzc2VydElzTm90Tm9uZShzdGF0ZW1lbnQuZW5kX2xpbmVubykKICAgICAgICBzZWxmLmFzc2VydElzTm90Tm9uZShzdGF0ZW1lbnQuZW5kX2NvbF9vZmZzZXQpCiAgICAgICAgbGluZXMgPSB0ZXh0LnNwbGl0bGluZXMoa2VlcGVuZHM9VHJ1ZSkKCiAgICAgICAgZGVmIG9mZnNldChsaW5lbm86IGludCwgY29sdW1uOiBpbnQpIC0+IGludDoKICAgICAgICAgICAgcmV0dXJuIHN1bShsZW4obGluZSkgZm9yIGxpbmUgaW4gbGluZXNbOiBsaW5lbm8gLSAxXSkgKyBjb2x1bW4KCiAgICAgICAgc3RhcnQgPSBvZmZzZXQoc3RhdGVtZW50LmxpbmVubywgc3RhdGVtZW50LmNvbF9vZmZzZXQpCiAgICAgICAgZW5kID0gb2Zmc2V0KHN0YXRlbWVudC5lbmRfbGluZW5vLCBzdGF0ZW1lbnQuZW5kX2NvbF9vZmZzZXQpCiAgICAgICAgcmVwbGFjZW1lbnQgPSByZXBsYWNlbWVudF9zb3VyY2UKICAgICAgICBtdXRhdGVkID0gdGV4dFs6c3RhcnRdICsgcmVwbGFjZW1lbnQgKyB0ZXh0W2VuZDpdCiAgICAgICAgY29tcGlsZShtdXRhdGVkLCBzdHIocGF0aCksICJleGVjIikKICAgICAgICBwYXRoLndyaXRlX3RleHQobXV0YXRlZCwgZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCkKCiAgICBkZWYgcmVmcmVzaF9tYW5pZmVzdHMoc2VsZikgLT4gTm9uZToKICAgICAgICBjYW5kaWRhdGUgPSBzZWxmLnJvb3QgLyAicGFja2V0LXNuYXBzaG90L2NhbmRpZGF0ZS1hcnRpZmFjdHMiCiAgICAgICAgY2FuZGlkYXRlX21hbmlmZXN0X3BhdGggPSBjYW5kaWRhdGUgLyAiY2FuZGlkYXRlLW1hbmlmZXN0Lmpzb24iCiAgICAgICAgY2FuZGlkYXRlX21hbmlmZXN0ID0ganNvbi5sb2FkcyhjYW5kaWRhdGVfbWFuaWZlc3RfcGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikpCiAgICAgICAgY2FuZGlkYXRlX21hbmlmZXN0WyJmaWxlcyJdID0gW10KICAgICAgICBmb3IgcGF0aCBpbiBzb3J0ZWQoY2FuZGlkYXRlLml0ZXJkaXIoKSk6CiAgICAgICAgICAgIGlmIHBhdGguaXNfZmlsZSgpIGFuZCBwYXRoLm5hbWUgIT0gImNhbmRpZGF0ZS1tYW5pZmVzdC5qc29uIjoKICAgICAgICAgICAgICAgIGNhbmRpZGF0ZV9tYW5pZmVzdFsiZmlsZXMiXS5hcHBlbmQoeyJuYW1lIjogcGF0aC5uYW1lLCAic2hhMjU2Ijogc2hhMjU2KHBhdGgpLCAic2l6ZV9ieXRlcyI6IHBhdGguc3RhdCgpLnN0X3NpemV9KQogICAgICAgIHNlbGYud3JpdGVfanNvbihjYW5kaWRhdGVfbWFuaWZlc3RfcGF0aCwgY2FuZGlkYXRlX21hbmlmZXN0KQoKICAgICAgICBwYWNrZXQgPSBzZWxmLnJvb3QgLyAicGFja2V0LXNuYXBzaG90IgogICAgICAgIHBhY2tldF9tYW5pZmVzdF9wYXRoID0gcGFja2V0IC8gInBhY2tldC1tYW5pZmVzdC5qc29uIgogICAgICAgIHBhY2tldF9tYW5pZmVzdCA9IGpzb24ubG9hZHMocGFja2V0X21hbmlmZXN0X3BhdGgucmVhZF90ZXh0KGVuY29kaW5nPSJ1dGYtOCIpKQogICAgICAgIHBhY2tldF9tYW5pZmVzdFsicGFja2V0X2ZpbGVzIl0gPSBbXQogICAgICAgIGZvciBwYXRoIGluIHNvcnRlZChwYWNrZXQucmdsb2IoIioiKSk6CiAgICAgICAgICAgIGlmIHBhdGguaXNfZmlsZSgpOgogICAgICAgICAgICAgICAgcmVsYXRpdmUgPSBwYXRoLnJlbGF0aXZlX3RvKHBhY2tldCkuYXNfcG9zaXgoKQogICAgICAgICAgICAgICAgaWYgcmVsYXRpdmUgIT0gInBhY2tldC1tYW5pZmVzdC5qc29uIjoKICAgICAgICAgICAgICAgICAgICBwYWNrZXRfbWFuaWZlc3RbInBhY2tldF9maWxlcyJdLmFwcGVuZCh7Im5hbWUiOiByZWxhdGl2ZSwgInNoYTI1NiI6IHNoYTI1NihwYXRoKSwgInNpemVfYnl0ZXMiOiBwYXRoLnN0YXQoKS5zdF9zaXplfSkKICAgICAgICBwYWNrZXRfbWFuaWZlc3RbInBhY2tldF9maWxlX2NvdW50X2V4Y2x1ZGluZ19tYW5pZmVzdCJdID0gbGVuKHBhY2tldF9tYW5pZmVzdFsicGFja2V0X2ZpbGVzIl0pCiAgICAgICAgc2VsZi53cml0ZV9qc29uKHBhY2tldF9tYW5pZmVzdF9wYXRoLCBwYWNrZXRfbWFuaWZlc3QpCgogICAgICAgIGV2aWRlbmNlX21hbmlmZXN0ID0gc2VsZi5yb290IC8gImV2aWRlbmNlLW1hbmlmZXN0LnR4dCIKICAgICAgICBsaW5lcyA9IFtdCiAgICAgICAgZm9yIHBhdGggaW4gc29ydGVkKHNlbGYucm9vdC5yZ2xvYigiKiIpKToKICAgICAgICAgICAgaWYgcGF0aC5pc19maWxlKCk6CiAgICAgICAgICAgICAgICByZWxhdGl2ZSA9IHBhdGgucmVsYXRpdmVfdG8oc2VsZi5yb290KS5hc19wb3NpeCgpCiAgICAgICAgICAgICAgICBpZiByZWxhdGl2ZSAhPSAiZXZpZGVuY2UtbWFuaWZlc3QudHh0IjoKICAgICAgICAgICAgICAgICAgICBsaW5lcy5hcHBlbmQoZiJ7c2hhMjU2KHBhdGgpfSAge3JlbGF0aXZlfSIpCiAgICAgICAgZXZpZGVuY2VfbWFuaWZlc3Qud3JpdGVfdGV4dCgiXG4iLmpvaW4obGluZXMpICsgIlxuIiwgZW5jb2Rpbmc9InV0Zi04IikKCiAgICBkZWYgYXNzZXJ0X3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgd2l0aCBzZWxmLmFzc2VydFJhaXNlcyhBc3NlcnRpb25FcnJvcik6CiAgICAgICAgICAgIHNlbGYudmFsaWRhdGUoKQoKICAgIGRlZiB0ZXN0XzAxX3ZhbGlkX3BhY2tldF9wYXNzZXMoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLnZhbGlkYXRlKCkKCiAgICBkZWYgdGVzdF8wMl9leHRyYV9jYW5kaWRhdGVfZmlsZV9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIChzZWxmLnJvb3QgLyAicGFja2V0LXNuYXBzaG90L2NhbmRpZGF0ZS1hcnRpZmFjdHMvZXh0cmEucHljIikud3JpdGVfYnl0ZXMoYiJ4IikKICAgICAgICBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8wM19taXNzaW5nX3NvdXJjZV9zbmFwc2hvdF9maWxlX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgKHNlbGYucm9vdCAvICJwYWNrZXQtc25hcHNob3Qvc291cmNlLXBhcnRpYWwtZXZpZGVuY2Utc25hcHNob3QvcGFja2V0LXNuYXBzaG90L3ZhbGlkYXRpb24tbG9ncy92aXN1ZG8ubG9nIikudW5saW5rKCkKICAgICAgICBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8wNF9wb2xpY3lfZXhlY3V0aW9uX3RydWVfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9qc29uKCJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9yMS1yMS1jb3JyZWN0aW9uLXBvbGljeS5qc29uIiwgbGFtYmRhIHY6IHYuX19zZXRpdGVtX18oInJvb3RfZGVwbG95bWVudF9leGVjdXRpb25fYWxsb3dlZCIsIFRydWUpKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzA1X3BvbGljeV9zdWRvZXJzX3RydWVfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9qc29uKCJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9yMS1yMS1jb3JyZWN0aW9uLXBvbGljeS5qc29uIiwgbGFtYmRhIHY6IHYuX19zZXRpdGVtX18oInN1ZG9lcnNfaW5zdGFsbGF0aW9uX2FsbG93ZWQiLCBUcnVlKSk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8wNl9wb2xpY3lfcmVsZWFzZV9nb19yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX2pzb24oInBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzL3IxLXIxLWNvcnJlY3Rpb24tcG9saWN5Lmpzb24iLCBsYW1iZGEgdjogdi5fX3NldGl0ZW1fXygicHJvZHVjdGlvbl9yZWxlYXNlX2RlY2lzaW9uIiwgIkdPIikpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMDdfaW52ZW50b3J5X2ZpbGVfY291bnRfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9qc29uKCJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9wYXJ0aWFsLXNvdXJjZS1pbnZlbnRvcnkuanNvbiIsIGxhbWJkYSB2OiB2Ll9fc2V0aXRlbV9fKCJzb3VyY2VfZmlsZV9jb3VudCIsIDM4KSk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8wOF9pbnZlbnRvcnlfc2hhX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfanNvbigicGFja2V0LXNuYXBzaG90L2NhbmRpZGF0ZS1hcnRpZmFjdHMvcGFydGlhbC1zb3VyY2UtaW52ZW50b3J5Lmpzb24iLCBsYW1iZGEgdjogdlsiZmlsZXMiXVswXS5fX3NldGl0ZW1fXygic2hhMjU2IiwgIjAiICogNjQpKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzA5X3JlcG9ydF93cmFwcGVyX3NoYV9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX2pzb24oInBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzL3ZhbGlkYXRvci1uZWdhdGl2ZS1jb3JyZWN0aW9uLXJlcG9ydC5qc29uIiwgbGFtYmRhIHY6IHYuX19zZXRpdGVtX18oIndyYXBwZXJfc2hhMjU2IiwgIjAiICogNjQpKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzEwX3JlcG9ydF9mYWlsZWRfdmFsaWRhdG9yX3NoYV9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX2pzb24oInBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzL3ZhbGlkYXRvci1uZWdhdGl2ZS1jb3JyZWN0aW9uLXJlcG9ydC5qc29uIiwgbGFtYmRhIHY6IHYuX19zZXRpdGVtX18oImZhaWxlZF92YWxpZGF0b3Jfc2hhMjU2IiwgIjAiICogNjQpKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzExX3JlcG9ydF9mYWlsZWRfbmVnYXRpdmVfc2hhX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfanNvbigicGFja2V0LXNuYXBzaG90L2NhbmRpZGF0ZS1hcnRpZmFjdHMvdmFsaWRhdG9yLW5lZ2F0aXZlLWNvcnJlY3Rpb24tcmVwb3J0Lmpzb24iLCBsYW1iZGEgdjogdi5fX3NldGl0ZW1fXygiZmFpbGVkX25lZ2F0aXZlX3Rlc3Rfc2hhMjU2IiwgIjAiICogNjQpKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzEyX3NvdXJjZV9maW5hbGl6YXRpb25fZmxhZ19yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX2pzb24oInBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzL3BhcnRpYWwtc291cmNlLWludmVudG9yeS5qc29uIiwgbGFtYmRhIHY6IHZbImZpbmFsaXphdGlvbl9maWxlc19wcmVzZW50Il0uX19zZXRpdGVtX18oInJlc3VsdC5qc29uIiwgVHJ1ZSkpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMTNfc291cmNlX3NuYXBzaG90X3BheWxvYWRfY2hhbmdlX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgcGF0aCA9IHNlbGYucm9vdCAvICJwYWNrZXQtc25hcHNob3Qvc291cmNlLXBhcnRpYWwtZXZpZGVuY2Utc25hcHNob3QvcGFja2V0LXNuYXBzaG90L2h1bWFuLWFwcHJvdmFsLXZlcmJhdGltLnR4dCIKICAgICAgICBwYXRoLndyaXRlX3RleHQocGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikgKyAieCIsIGVuY29kaW5nPSJ1dGYtOCIpCiAgICAgICAgc2VsZi5yZWZyZXNoX21hbmlmZXN0cygpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMTRfc291cmNlX3NuYXBzaG90X3N5bWxpbmtfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICB0YXJnZXQgPSBzZWxmLnJvb3QgLyAicGFja2V0LXNuYXBzaG90L3NvdXJjZS1wYXJ0aWFsLWV2aWRlbmNlLXNuYXBzaG90L3VuZXhwZWN0ZWQtbGluayIKICAgICAgICB0YXJnZXQuc3ltbGlua190bygibWlzc2luZy10YXJnZXQiKQogICAgICAgIHNlbGYucmVmcmVzaF9tYW5pZmVzdHMoKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzE1X3dyYXBwZXJfYnl0ZXNfY2hhbmdlX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfd3JhcHBlcigiTUFYX0VYRUNVVElPTl9BVFRFTVBUUyA9IDEiLCAiTUFYX0VYRUNVVElPTl9BVFRFTVBUUyA9IDIiKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzE2X3dyYXBwZXJfZXhlY3V0aW9uX3RydWVfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9qc29uKCJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9yMS1yMS1jb3JyZWN0aW9uLXBvbGljeS5qc29uIiwgbGFtYmRhIHY6IHYuX19zZXRpdGVtX18oImNvcnJlY3RlZF93cmFwcGVyX2V4ZWN1dGlvbl9hbGxvd2VkIiwgVHJ1ZSkpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMTdfd3JhcHBlcl9jaGFuZ2VfdHJ1ZV9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX2pzb24oInBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzL3IxLXIxLWNvcnJlY3Rpb24tcG9saWN5Lmpzb24iLCBsYW1iZGEgdjogdi5fX3NldGl0ZW1fXygiY29ycmVjdGVkX3dyYXBwZXJfY2hhbmdlX2FsbG93ZWQiLCBUcnVlKSk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8xOF90ZXN0X2lkc19jaGFuZ2VfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9qc29uKCJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9yMS1yMS1jb3JyZWN0aW9uLXBvbGljeS5qc29uIiwgbGFtYmRhIHY6IHYuX19zZXRpdGVtX18oImNvcnJlY3RlZF90ZXN0X2lkcyIsIFsyNiwgMjcsIDMwXSkpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMTlfc3Vkb2Vyc193aWxkY2FyZF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHBhdGggPSBzZWxmLnJvb3QgLyAicGFja2V0LXNuYXBzaG90L2NhbmRpZGF0ZS1hcnRpZmFjdHMvYWktbWVkaWEtb3MtM2Utai1yb290LWhlbHBlci5zdWRvZXJzIgogICAgICAgIHBhdGgud3JpdGVfdGV4dCgiKlxuIiwgZW5jb2Rpbmc9InV0Zi04Iik7IHNlbGYucmVmcmVzaF9tYW5pZmVzdHMoKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzIwX3dyYXBwZXJfbWFuaWZlc3RfcGFyc2VyX3JlbW92ZWRfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV93cmFwcGVyKCJkZWYgcGFyc2VfZXZpZGVuY2VfbWFuaWZlc3QoIiwgImRlZiByZW1vdmVkX3BhcnNlX2V2aWRlbmNlX21hbmlmZXN0KCIpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMjFfd3JhcHBlcl9ldmlkZW5jZV9jYWxsX3JlbW92ZWRfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9wcmVmbGlnaHRfY2FsbCgKICAgICAgICAgICAgInZhbGlkYXRlX2V2aWRlbmNlX2ludGVncml0eSIsCiAgICAgICAgICAgICJyZXF1aXJlKFRydWUsICdSRU1PVkVEX0VWSURFTkNFX1ZBTElEQVRJT04nKSIsCiAgICAgICAgICAgIGV4cGVjdGVkX2FyZ19uYW1lcz0oImV2aWRlbmNlX3Jvb3QiLCAiYmluZGluZyIpLAogICAgICAgICkKICAgICAgICBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMjJfd3JhcHBlcl9wYXJlbnRfZGV2aWNlX21hcmtlcl9yZW1vdmVkX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfd3JhcHBlcignIlJPTExCQUNLX1BBUkVOVF9ERVZJQ0UiJywgJyJSRU1PVkVEX1BBUkVOVF9ERVZJQ0UiJyk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8yM193cmFwcGVyX3BhcmVudF9pbm9kZV9tYXJrZXJfcmVtb3ZlZF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX3dyYXBwZXIoJyJST0xMQkFDS19QQVJFTlRfSU5PREUiJywgJyJSRU1PVkVEX1BBUkVOVF9JTk9ERSInKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzI0X3dyYXBwZXJfbGV4aXN0c19yZW1vdmVkX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfd3JhcHBlcigib3MucGF0aC5sZXhpc3RzIiwgIm9zLnBhdGguZXhpc3RzIik7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8yNV93cmFwcGVyX3BhdGhfYWJzZW5jZV9mdW5jdGlvbl9yZW1vdmVkX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfd3JhcHBlcigiZGVmIHJlcXVpcmVfcGF0aF9lbnRyeV9hYnNlbnQoIiwgImRlZiByZW1vdmVkX3JlcXVpcmVfcGF0aF9lbnRyeV9hYnNlbnQoIik7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8yNl93cmFwcGVyX3Byb3RlY3RlZF92YWxpZGF0aW9uX2NhbGxfcmVtb3ZlZF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX3ByZWZsaWdodF9jYWxsKAogICAgICAgICAgICAidmFsaWRhdGVfcHJvdGVjdGVkX3NoYSIsCiAgICAgICAgICAgICJyZXF1aXJlKFRydWUsICdSRU1PVkVEX1BST1RFQ1RFRF9WQUxJREFUSU9OJykiLAogICAgICAgICAgICBleHBlY3RlZF9hcmdfbmFtZXM9KCksCiAgICAgICAgKQogICAgICAgIHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8yN193cmFwcGVyX3Byb3RlY3RlZF90YWJsZV9leGFjdF9hc3NpZ25tZW50X3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfd3JhcHBlcigiUFJPVEVDVEVEX1NIQSA9IHsiLCAiUkVNT1ZFRF9QUk9URUNURURfU0hBID0geyIpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMjhfd3JhcHBlcl9wYXJlbnRfcm9sbGJhY2tfaWRlbnRpdHlfZmFsc2VfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBzZWxmLm11dGF0ZV9qc29uKCJwYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cy9yb290LWRlcGxveW1lbnQtdHJhbnNhY3Rpb24tY29udHJhY3QuanNvbiIsIGxhbWJkYSB2OiB2WyJyb2xsYmFjayJdLl9fc2V0aXRlbV9fKCJjcmVhdGVkX3BhcmVudF9yZW1vdmFsX3JlcXVpcmVzX2lub2RlX2RldmljZV9tYXRjaCIsIEZhbHNlKSk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8yOV93cmFwcGVyX3JlbmFtZV9mYWxsYmFja19jb250cmFjdF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX2pzb24oInBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzL3Jvb3QtZGVwbG95bWVudC10cmFuc2FjdGlvbi1jb250cmFjdC5qc29uIiwgbGFtYmRhIHY6IHZbInByZWZsaWdodCJdLl9fc2V0aXRlbV9fKCJyZW5hbWVfZmFsbGJhY2tfYWxsb3dlZCIsIFRydWUpKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzMwX3dyYXBwZXJfYm90aF9yZW5hbWVhdDJfcmVmZXJlbmNlc19yZW1vdmVkX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgcGF0aCA9IHNlbGYud3JhcHBlcl9wYXRoKCk7IHRleHQgPSBwYXRoLnJlYWRfdGV4dChlbmNvZGluZz0idXRmLTgiKQogICAgICAgIHNlbGYuYXNzZXJ0RXF1YWwodGV4dC5jb3VudCgicmVuYW1lYXQyID0gbGliYy5yZW5hbWVhdDIiKSwgMikKICAgICAgICBwYXRoLndyaXRlX3RleHQodGV4dC5yZXBsYWNlKCJyZW5hbWVhdDIgPSBsaWJjLnJlbmFtZWF0MiIsICJyZW5hbWVhdDIgPSBsaWJjLnJlbW92ZWRfcmVuYW1lYXQyIiksIGVuY29kaW5nPSJ1dGYtOCIpCiAgICAgICAgc2VsZi5yZWZyZXNoX21hbmlmZXN0cygpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMzFfd3JhcHBlcl9yZW5hbWVfbm9yZXBsYWNlX2V4YWN0X2NvbnN0YW50X3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfd3JhcHBlcigiUkVOQU1FX05PUkVQTEFDRSA9IDFcbiIsICJSRU5BTUVfTk9SRVBMQUNFID0gMlxuIik7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8zMl93cmFwcGVyX3JlbmFtZWF0Ml9maWZ0aF9hcmd1bWVudF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYubXV0YXRlX3dyYXBwZXIoIiAgICAgICAgUkVOQU1FX05PUkVQTEFDRSxcbiIsICIgICAgICAgIDAsXG4iKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzMzX3dyYXBwZXJfb3NfcmVuYW1lX2ZhbGxiYWNrX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgcGF0aCA9IHNlbGYud3JhcHBlcl9wYXRoKCk7IHBhdGgud3JpdGVfdGV4dChwYXRoLnJlYWRfdGV4dChlbmNvZGluZz0idXRmLTgiKSArICJcbiMgb3MucmVuYW1lKHN0YWdlLCB0YXJnZXQpXG4iLCBlbmNvZGluZz0idXRmLTgiKQogICAgICAgIHNlbGYucmVmcmVzaF9tYW5pZmVzdHMoKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzM0X3dyYXBwZXJfc2hlbGxfdHJ1ZV9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHBhdGggPSBzZWxmLndyYXBwZXJfcGF0aCgpOyBwYXRoLndyaXRlX3RleHQocGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikgKyAiXG4jIHNoZWxsPVRydWVcbiIsIGVuY29kaW5nPSJ1dGYtOCIpCiAgICAgICAgc2VsZi5yZWZyZXNoX21hbmlmZXN0cygpOyBzZWxmLmFzc2VydF9yZWplY3RlZCgpCgogICAgZGVmIHRlc3RfMzVfd3JhcHBlcl9ldmlkZW5jZV9hZnRlcl9ndWFyZF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHBhdGggPSBzZWxmLndyYXBwZXJfcGF0aCgpOyB0ZXh0ID0gcGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICB0ZXh0ID0gdGV4dC5yZXBsYWNlKCIgICAgICAgIHZhbGlkYXRlX2V2aWRlbmNlX2ludGVncml0eShldmlkZW5jZV9yb290LCBiaW5kaW5nKVxuIiwgIiAgICAgICAgcmVxdWlyZShUcnVlLCAnREVGRVJSRURfRVZJREVOQ0UnKVxuIiwgMSkKICAgICAgICB0ZXh0ID0gdGV4dC5yZXBsYWNlKCIgICAgICAgIGNyZWF0ZV9vbmVfc2hvdF9ndWFyZChndWFyZF9wYXlsb2FkKVxuIiwgIiAgICAgICAgY3JlYXRlX29uZV9zaG90X2d1YXJkKGd1YXJkX3BheWxvYWQpXG4gICAgICAgIHZhbGlkYXRlX2V2aWRlbmNlX2ludGVncml0eShldmlkZW5jZV9yb290LCB7fSlcbiIsIDEpCiAgICAgICAgcGF0aC53cml0ZV90ZXh0KHRleHQsIGVuY29kaW5nPSJ1dGYtOCIpOyBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8zNl93cmFwcGVyX3Byb3RlY3RlZF9hZnRlcl9ndWFyZF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHBhdGggPSBzZWxmLndyYXBwZXJfcGF0aCgpOyB0ZXh0ID0gcGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICB0ZXh0ID0gdGV4dC5yZXBsYWNlKCIgICAgICAgIHZhbGlkYXRlX3Byb3RlY3RlZF9zaGEoKVxuIiwgIiAgICAgICAgcmVxdWlyZShUcnVlLCAnREVGRVJSRURfUFJPVEVDVEVEJylcbiIsIDEpCiAgICAgICAgdGV4dCA9IHRleHQucmVwbGFjZSgiICAgICAgICBjcmVhdGVfb25lX3Nob3RfZ3VhcmQoZ3VhcmRfcGF5bG9hZClcbiIsICIgICAgICAgIGNyZWF0ZV9vbmVfc2hvdF9ndWFyZChndWFyZF9wYXlsb2FkKVxuICAgICAgICB2YWxpZGF0ZV9wcm90ZWN0ZWRfc2hhKClcbiIsIDEpCiAgICAgICAgcGF0aC53cml0ZV90ZXh0KHRleHQsIGVuY29kaW5nPSJ1dGYtOCIpOyBzZWxmLnJlZnJlc2hfbWFuaWZlc3RzKCk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF8zN193cmFwcGVyX3JlbmFtZV9hdmFpbGFiaWxpdHlfYWZ0ZXJfZ3VhcmRfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBwYXRoID0gc2VsZi53cmFwcGVyX3BhdGgoKTsgdGV4dCA9IHBhdGgucmVhZF90ZXh0KGVuY29kaW5nPSJ1dGYtOCIpCiAgICAgICAgdGV4dCA9IHRleHQucmVwbGFjZSgiICAgICAgICByZXF1aXJlX3JlbmFtZV9ub3JlcGxhY2VfYXZhaWxhYmxlKClcbiIsICIgICAgICAgIHJlcXVpcmUoVHJ1ZSwgJ0RFRkVSUkVEX1JFTkFNRV9BVkFJTEFCSUxJVFknKVxuIiwgMSkKICAgICAgICB0ZXh0ID0gdGV4dC5yZXBsYWNlKCIgICAgICAgIGNyZWF0ZV9vbmVfc2hvdF9ndWFyZChndWFyZF9wYXlsb2FkKVxuIiwgIiAgICAgICAgY3JlYXRlX29uZV9zaG90X2d1YXJkKGd1YXJkX3BheWxvYWQpXG4gICAgICAgIHJlcXVpcmVfcmVuYW1lX25vcmVwbGFjZV9hdmFpbGFibGUoKVxuIiwgMSkKICAgICAgICBwYXRoLndyaXRlX3RleHQodGV4dCwgZW5jb2Rpbmc9InV0Zi04Iik7IHNlbGYucmVmcmVzaF9tYW5pZmVzdHMoKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzM4X3BhY2tldF9tYW5pZmVzdF9jb3VudF9yZWplY3RlZChzZWxmKSAtPiBOb25lOgogICAgICAgIHBhdGgsIHZhbHVlID0gc2VsZi5sb2FkX2pzb24oInBhY2tldC1zbmFwc2hvdC9wYWNrZXQtbWFuaWZlc3QuanNvbiIpOyB2YWx1ZVsicGFja2V0X2ZpbGVfY291bnRfZXhjbHVkaW5nX21hbmlmZXN0Il0gPSA2MTsgc2VsZi53cml0ZV9qc29uKHBhdGgsIHZhbHVlKTsgc2VsZi5hc3NlcnRfcmVqZWN0ZWQoKQoKICAgIGRlZiB0ZXN0XzM5X2V2aWRlbmNlX21hbmlmZXN0X2VudHJ5X3JlbW92ZWRfcmVqZWN0ZWQoc2VsZikgLT4gTm9uZToKICAgICAgICBwYXRoID0gc2VsZi5yb290IC8gImV2aWRlbmNlLW1hbmlmZXN0LnR4dCI7IGxpbmVzID0gcGF0aC5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04Iikuc3BsaXRsaW5lcygpOyBwYXRoLndyaXRlX3RleHQoIlxuIi5qb2luKGxpbmVzWzotMV0pICsgIlxuIiwgZW5jb2Rpbmc9InV0Zi04Iik7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCiAgICBkZWYgdGVzdF80MF9yZXN1bHRfd3JhcHBlcl9leGVjdXRlZF90cnVlX3JlamVjdGVkKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5tdXRhdGVfanNvbigicmVzdWx0Lmpzb24iLCBsYW1iZGEgdjogdi5fX3NldGl0ZW1fXygiY29ycmVjdGVkX3dyYXBwZXJfZXhlY3V0ZWQiLCBUcnVlKSk7IHNlbGYuYXNzZXJ0X3JlamVjdGVkKCkKCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgdW5pdHRlc3QubWFpbih2ZXJib3NpdHk9MikK",
    validate=True,
)
approval_text = base64.b64decode("QVBQUk9WRV8zRV9KX1JPT1RfREVQTE9ZTUVOVF9FWEVDVVRJT05fUEFDS0VUX1IxX1IyX1IyX05FR0FUSVZFX1RFU1RfTVVUQVRJT05fSU5ERU5UQVRJT05fQ09SUkVDVElPTl9QUkVQQVJBVElPTl9OT19FWEVDVVRJT04KCkZBSUxFRF9SMV9SMl9SMV9FVklERU5DRV9SRUFET05MWV9JTlZFTlRPUlk9UEFTUwpGQUlMRURfUjFfUjJfUjFfRVZJREVOQ0VfTVVUQVRJT049ZmFsc2UKUkVBRE9OTFlfSU5WRU5UT1JZX0VYSVRfQ09ERT0wCgpSMV9SMl9SMV9QQUNLRVRfUFJFUEFSQVRJT049RkFJTF9ORUdBVElWRV9URVNUX01VVEFUSU9OX0lOREVOVEFUSU9OCkZBSUxVUkVfU1RBR0U9VEVNUE9SQVJZX1ZBTElEQVRPUl9UQVJHRVRfTkVHQVRJVkVfVEVTVFMKRkFJTEVEX1RFU1RfQ09VTlQ9MApFUlJPUl9URVNUX0NPVU5UPTIKQ09SUkVDVEVEX1RFU1RfSURTPTIxLDI2CgpTT1VSQ0VfRklMRV9DT1VOVD0xNTAKU09VUkNFX0RJUkVDVE9SWV9DT1VOVF9FWENMVURJTkdfUk9PVD0yOQpTT1VSQ0VfVFJFRV9JREVOVElUWV9TSEEyNTY9MmNkZGY4MmQwNWVkMWFhZGUyZmM0OGVlZTM5ZWM0NjhmM2VhMzdmOWY0NDQ1MTZlNjAwNzc2MDMyNTI3ZWIxNwoKQ09SUkVDVEVEX1dSQVBQRVJfU0hBPTBkNzEyYzZlMTJkYzBiOTgyMTNjYTE5OTVlNGYyMmQxZTkwODhhYjVmZmMzMWE5N2E0OTdkNjBiYTc2OWZhNTMKUjFfUjFfVkFMSURBVE9SX1NIQT1lZmRhYmJlODNjNjFhMjYxODEyOGY1NTE4YTcyNmYwMDcwNjJiYmEwZTkxOTU5YTAxZWVkMWYzODBkNGIyZDc0CkZBSUxFRF9SMV9SMl9SMV9ORUdBVElWRV9URVNUX1NIQT1kNjI2YzIyY2FiMGUxMWY4OTMyM2RmNmE1YjgxY2I4YjQ0YTE1ZDYxNDkyODIyMGUxNmQ1OTU0YWM5Njc2Zjk5CgpSMV9SMl9SMl9DT1JSRUNUSU9OX1BBQ0tFVF9QUkVQQVJBVElPTl9PTkxZPXRydWUKTkVHQVRJVkVfVEVTVF9NVVRBVElPTl9JTkRFTlRBVElPTl9DT1JSRUNUSU9OX09OTFk9dHJ1ZQpDT1JSRUNURURfV1JBUFBFUl9DSEFOR0VfQUxMT1dFRD1mYWxzZQpDT1JSRUNURURfV1JBUFBFUl9FWEVDVVRJT05fQUxMT1dFRD1mYWxzZQpSMV9SMV9WQUxJREFUT1JfQ0hBTkdFX0FMTE9XRUQ9ZmFsc2UKQ09SUkVDVEVEX1RFU1RfSURTPTIxLDI2CgpST09UX0RFUExPWU1FTlRfRVhFQ1VUSU9OX0FMTE9XRUQ9ZmFsc2UKU1VET0VSU19JTlNUQUxMQVRJT05fQUxMT1dFRD1mYWxzZQpQUk9EVUNUSU9OX0ZJTEVfQ1JFQVRJT05fQUxMT1dFRD1mYWxzZQpQUk9EVUNUSU9OX0RJUkVDVE9SWV9DUkVBVElPTl9BTExPV0VEPWZhbHNlClJPT1RfSEVMUEVSX0VYRUNVVElPTl9BTExPV0VEPWZhbHNlClJVTk5FUl9FWEVDVVRJT05fQUxMT1dFRD1mYWxzZQpPTkVfU0hPVF9ERVBMT1lNRU5UX0dVQVJEX0NSRUFURUQ9ZmFsc2UKQVBQUk9WQUxfQklORElOR19DUkVBVEVEPWZhbHNlClJPT1RfUkVBRE9OTFlfVkVSSUZJQ0FUSU9OX1JFRVhFQ1VUSU9OX0FMTE9XRUQ9ZmFsc2UKT05FX1NIT1RfR1VBUkRfQ0hBTkdFX0FMTE9XRUQ9ZmFsc2UKU1VET0VSU19DSEFOR0VEPWZhbHNlCkFVVE9NQVRJQ19ERVBMT1lNRU5UX1BFUkZPUk1FRD1mYWxzZQpDQU5ESURBVEVfREVQTE9ZRURfVE9fUFJPRFVDVElPTj1mYWxzZQpSVU5ORVJfU1RBVFVTPUJMT0NLRURfVU5USUxfRVhQTElDSVRfRklOQUxfRVhFQ1VUSU9OX0FQUFJPVkFMCldSSVRFUl9GUkVFWkVfRVhFQ1VUSU9OPUhPTEQKUFJPRFVDVElPTl9SRUxFQVNFX0RFQ0lTSU9OPUhPTEQKUkVMRUFTRV9TVEFUVVM9Q0FORElEQVRFX05PVF9BUFBST1ZFRAo=", validate=True)
manual_text = base64.b64decode("IyAzRS1KIFIxLVIyLVIyIE11dGF0aW9uIEluZGVudGF0aW9uIENvcnJlY3Rpb24KClRoaXMgUGFja2V0IGNvcnJlY3RzIG9uZSBsaW5lIGluIHRoZSBuZWdhdGl2ZS10ZXN0IGhlbHBlciBvbmx5OgoKYGBgcHl0aG9uCnJlcGxhY2VtZW50ID0gcmVwbGFjZW1lbnRfc291cmNlCmBgYAoKVGhlIHNvdXJjZSBzbGljZSBhbHJlYWR5IHByZXNlcnZlcyB0aGUgb3JpZ2luYWwgaW5kZW50YXRpb24gYmVmb3JlIHRoZSBBU1QKZXhwcmVzc2lvbiBzdGFydC4gQWRkaW5nIGBzdGF0ZW1lbnQuY29sX29mZnNldGAgYWdhaW4gY2F1c2VkIHRoZSBwcmlvcgpgSW5kZW50YXRpb25FcnJvcmAuCgpUaGUgcm9vdC1kZXBsb3ltZW50IHdyYXBwZXIgcmVtYWlucyBieXRlLWZvci1ieXRlIGZpeGVkLiBUaGUgUjEtUjEgdmFsaWRhdG9yCmFsc28gcmVtYWlucyBieXRlLWZvci1ieXRlIGZpeGVkLiBUZXN0cyAyMSBhbmQgMjYgcmV0YWluIHRoZSBBU1QtYmFzZWQKYHByZWZsaWdodGAgZGlyZWN0LWNhbGwgc2VsZWN0b3IsIGV4YWN0LW9uZSByZXF1aXJlbWVudCwgc2lnbmF0dXJlIGNoZWNrcywKYW5kIHNvdXJjZS1yYW5nZSByZXBsYWNlbWVudCB1c2luZyBgbGluZW5vYCwgYGNvbF9vZmZzZXRgLCBgZW5kX2xpbmVub2AsIGFuZApgZW5kX2NvbF9vZmZzZXRgLgoKTm8gZGVwbG95bWVudCB3cmFwcGVyLCBibG9ja2VkIGVudHJ5cG9pbnQsIHJvb3QgaGVscGVyLCBydW5uZXIsIGFwcHJvdmFsCmJpbmRpbmcsIG9uZS1zaG90IGd1YXJkLCBgL29wdGAgcGF0aCwgb3IgYC9ldGMvc3Vkb2Vycy5kYCB0YXJnZXQgaXMgZXhlY3V0ZWQKb3IgbW9kaWZpZWQuIFByb2R1Y3Rpb24gcmVsZWFzZSByZW1haW5zIEhPTEQuCg==", validate=True)
contract_bytes = base64.b64decode("ewogICJjaGFuZ2VkX2xpbmVfY291bnQiOiAxLAogICJjaGFuZ2VkX3Rlc3RfaWRzIjogWwogICAgMjEsCiAgICAyNgogIF0sCiAgImNvcnJlY3RlZF9uZWdhdGl2ZV90ZXN0X3NoYTI1NiI6ICI2ZGFkMzdjMjFjMzU5MjE1ODdlMTgzOTAwMmEyNDM1ZWJhYjRmNGI4ODM5OWY2MDM1YTlkY2Q5NTY5MTU2Y2E3IiwKICAiY29ycmVjdGVkX3dyYXBwZXJfc2hhMjU2IjogIjBkNzEyYzZlMTJkYzBiOTgyMTNjYTE5OTVlNGYyMmQxZTkwODhhYjVmZmMzMWE5N2E0OTdkNjBiYTc2OWZhNTMiLAogICJjb3JyZWN0aW9uX3Njb3BlIjogIk5FR0FUSVZFX1RFU1RfTVVUQVRJT05fSU5ERU5UQVRJT05fT05MWSIsCiAgImZhaWxlZF9uZWdhdGl2ZV90ZXN0X3NoYTI1NiI6ICJkNjI2YzIyY2FiMGUxMWY4OTMyM2RmNmE1YjgxY2I4YjQ0YTE1ZDYxNDkyODIyMGUxNmQ1OTU0YWM5Njc2Zjk5IiwKICAicGhhc2UiOiAiVFNULTVELVcyQi1JMkYtM0UtSi1ST09ULURFUExPWU1FTlQtRVhFQ1VUSU9OLVBBQ0tFVC1SMS1SMi1SMiIsCiAgInByb2R1Y3Rpb25fcmVsZWFzZV9kZWNpc2lvbiI6ICJIT0xEIiwKICAicm9vdF9kZXBsb3ltZW50X2V4ZWN1dGlvbl9hbGxvd2VkIjogZmFsc2UsCiAgInNjaGVtYV92ZXJzaW9uIjogIjEuMCIsCiAgInNvdXJjZV9kaXJlY3RvcnlfY291bnRfZXhjbHVkaW5nX3Jvb3QiOiAyOSwKICAic291cmNlX2ZpbGVfY291bnQiOiAxNTAsCiAgInNvdXJjZV90cmVlX2lkZW50aXR5X3NoYTI1NiI6ICIyY2RkZjgyZDA1ZWQxYWFkZTJmYzQ4ZWVlMzllYzQ2OGYzZWEzN2Y5ZjQ0NDUxNmU2MDA3NzYwMzI1MjdlYjE3IiwKICAidmFsaWRhdG9yX2NoYW5nZWQiOiBmYWxzZSwKICAidmFsaWRhdG9yX3NoYTI1NiI6ICJlZmRhYmJlODNjNjFhMjYxODEyOGY1NTE4YTcyNmYwMDcwNjJiYmEwZTkxOTU5YTAxZWVkMWYzODBkNGIyZDc0IiwKICAid3JhcHBlcl9jaGFuZ2VkIjogZmFsc2UsCiAgIndyYXBwZXJfZXhlY3V0ZWQiOiBmYWxzZQp9Cg==", validate=True)

PROTECTED_SHA = {
    "data/database/ebook_affiliate.db":
        "1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9",
    "config/slack_worker_release_source_manifest.json":
        "ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d",
    "app/db/repositories/workflow_state_repository.py":
        "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "migrations/versions/00241611109d_add_unique_wordpress_post_id.py":
        "e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a",
    "scripts/run_slack_approval_socket.py":
        "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6",
    "tests/test_slack_approval_socket_hold_remediation_offline.py":
        "86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_exclusive(path: Path, data: bytes, mode: int = 0o640) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
    )
    with os.fdopen(descriptor, "wb", closefd=True) as stream:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            count = stream.write(view[offset:])
            require(count is not None and count > 0, f"WRITE_ZERO:{path}")
            offset += count
        stream.flush()
        os.fsync(stream.fileno())


def mkdir_exclusive(path: Path, mode: int = 0o750) -> None:
    os.mkdir(path, mode)


def scan(root: Path):
    files: set[str] = set()
    dirs: set[str] = set()
    links = 0
    other = 0
    for path in sorted(root.rglob("*")):
        item = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(item.st_mode):
            links += 1
        elif stat.S_ISREG(item.st_mode):
            files.add(relative)
        elif stat.S_ISDIR(item.st_mode):
            dirs.add(relative)
        else:
            other += 1
    return files, dirs, links, other


def identity(root: Path):
    files, dirs, links, other = scan(root)
    require(links == 0 and other == 0, f"SPECIAL_PATH:{root}")
    value: dict[str, tuple[object, ...]] = {}
    for relative in sorted(dirs):
        item = (root / relative).lstat()
        value[relative + "/"] = (
            "DIR",
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        value[relative] = (
            sha256(path),
            item.st_size,
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    return value


def inventory(root: Path):
    files, dirs, links, other = scan(root)
    require(links == 0 and other == 0, "SOURCE_SPECIAL")
    entries: list[dict[str, object]] = []
    lines: list[str] = []
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        digest = sha256(path)
        lines.append(
            f"{digest}  {item.st_size}  "
            f"{stat.S_IMODE(item.st_mode):04o}  "
            f"{item.st_uid}  {item.st_gid}  {relative}"
        )
        entries.append(
            {
                "relative_path": relative,
                "size_bytes": item.st_size,
                "mode": f"{stat.S_IMODE(item.st_mode):04o}",
                "uid": item.st_uid,
                "gid": item.st_gid,
                "sha256": digest,
            }
        )
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    return files, dirs, digest, entries


def create_tree(root: Path, dirs: set[str]) -> None:
    mkdir_exclusive(root)
    for relative in sorted(dirs, key=lambda item: (item.count("/"), item)):
        mkdir_exclusive(root / relative)


def copy_file(source: Path, destination: Path) -> None:
    item = source.lstat()
    require(stat.S_ISREG(item.st_mode), f"SOURCE_NOT_REGULAR:{source}")
    require(not stat.S_ISLNK(item.st_mode), f"SOURCE_SYMLINK:{source}")
    write_exclusive(destination, source.read_bytes())


def regenerate_candidate_manifest(
    candidate: Path,
    source_manifest: Path,
) -> bytes:
    value = json.loads(source_manifest.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "CANDIDATE_MANIFEST_OBJECT")
    entries = []
    for path in sorted(candidate.iterdir()):
        if path.is_file() and path.name != "candidate-manifest.json":
            entries.append(
                {
                    "name": path.name,
                    "sha256": sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    require(len(entries) == 17, f"CANDIDATE_ENTRY_COUNT:{len(entries)}")
    value["total_file_count"] = 18
    value["file_count_excluding_manifest"] = 17
    value["files"] = entries
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def finalize_target(root: Path, relative_label: str) -> None:
    packet = root / "packet-snapshot"
    entries = []
    for path in sorted(packet.rglob("*")):
        if path.is_file():
            relative = path.relative_to(packet).as_posix()
            if relative != "packet-manifest.json":
                entries.append(
                    {
                        "name": relative,
                        "sha256": sha256(path),
                        "size_bytes": path.stat().st_size,
                    }
                )
    require(len(entries) == 62, f"TARGET_PACKET_ENTRY_COUNT:{len(entries)}")
    packet_value = {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-EXECUTION-PACKET-R1-R1",
        "status":
            "R1_R1_NEGATIVE_TEST_AND_STATIC_VALIDATOR_CORRECTION_"
            "PACKET_PREPARED_NO_EXECUTION",
        "packet_file_count_excluding_manifest": 62,
        "packet_files": entries,
        "candidate_artifact_count": 18,
        "source_partial_snapshot_file_count": 39,
        "validation_log_count": 4,
        "negative_test_count": 40,
        "corrected_wrapper_changed": False,
        "corrected_wrapper_executed": False,
        "root_deployment_execution_allowed": False,
        "sudoers_installation_allowed": False,
        "production_release_decision": "HOLD",
    }
    write_exclusive(
        packet / "packet-manifest.json",
        (json.dumps(packet_value, sort_keys=True, indent=2) + "\n").encode(),
    )
    result = {
        "schema_version": "1.0",
        "phase": "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-EXECUTION-PACKET-R1-R1",
        "result":
            "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_R1_R1_"
            "NEGATIVE_TEST_AND_STATIC_VALIDATOR_CORRECTION_PREPARED_NO_EXECUTION",
        "evidence_root": relative_label,
        "source_failed_partial_evidence_file_count": 39,
        "source_failed_partial_evidence_directory_count": 8,
        "source_failed_partial_evidence_finalized": False,
        "source_failed_partial_evidence_unchanged": True,
        "evidence_file_count": 65,
        "evidence_directory_count_excluding_root": 12,
        "packet_file_count": 63,
        "packet_directory_count": 11,
        "packet_manifest_entry_count": 62,
        "evidence_manifest_entry_count": 64,
        "candidate_artifact_count": 18,
        "source_partial_snapshot_file_count": 39,
        "validation_log_count": 4,
        "negative_test_count": 40,
        "corrected_test_ids": [26, 27, 30, 31],
        "validator": "PASS",
        "negative_tests": "PASS",
        "visudo_static_validation": "PASS",
        "corrected_wrapper_sha256": WRAPPER_SHA,
        "corrected_wrapper_changed": False,
        "corrected_wrapper_executed": False,
        "packet_preparation_only": True,
        "root_deployment_execution_allowed": False,
        "sudoers_installation_allowed": False,
        "production_file_creation_allowed": False,
        "production_directory_creation_allowed": False,
        "root_helper_execution_allowed": False,
        "runner_execution_allowed": False,
        "one_shot_deployment_guard_created": False,
        "approval_binding_created": False,
        "sudoers_changed": False,
        "automatic_deployment_performed": False,
        "candidate_deployed_to_production": False,
        "protected_sha_unchanged": True,
        "runner_status": "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
        "writer_freeze_execution": "HOLD",
        "production_release_decision": "HOLD",
        "release_status": "CANDIDATE_NOT_APPROVED",
        "next_gate":
            "HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
            "R1_R1_CORRECTION_READONLY",
    }
    write_exclusive(
        root / "result.json",
        (json.dumps(result, sort_keys=True, indent=2) + "\n").encode(),
    )
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative != "evidence-manifest.txt":
                lines.append(f"{sha256(path)}  {relative}")
    require(len(lines) == 64, f"TARGET_EVIDENCE_ENTRY_COUNT:{len(lines)}")
    write_exclusive(
        root / "evidence-manifest.txt",
        ("\n".join(lines) + "\n").encode(),
    )


def run_python(path: Path, args: list[str]) -> str:
    run = subprocess.run(
        [str(repo_root / ".venv/bin/python"), "-B", str(path), *args],
        cwd=path.parent,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
    )
    require(run.returncode == 0, f"PROGRAM_NONZERO:{path.name}\n{run.stdout}")
    return run.stdout


source_files, source_dirs, source_tree_sha, source_inventory = inventory(source_root)
require(len(source_files) == 150, f"SOURCE_FILE_COUNT:{len(source_files)}")
require(len(source_dirs) == 29, f"SOURCE_DIR_COUNT:{len(source_dirs)}")
require(source_tree_sha == SOURCE_TREE_SHA, "SOURCE_TREE_SHA")
for relative in (
    "result.json",
    "evidence-manifest.txt",
    "packet-snapshot/packet-manifest.json",
):
    require(not (source_root / relative).is_file(), f"SOURCE_FINALIZED:{relative}")

source_candidate = source_root / "packet-snapshot/candidate-artifacts"
source_target = source_root / "packet-snapshot/r1-r1-validator-target"
require(sha256(source_candidate / "root_deployment_execution_once_r1.py") == WRAPPER_SHA, "WRAPPER_SHA")
require(sha256(source_candidate / "validate_root_deployment_execution_packet_r1.py") == VALIDATOR_SHA, "VALIDATOR_SHA")
require(sha256(source_candidate / "test_root_deployment_execution_packet_r1_negative.py") == FAILED_NEGATIVE_SHA, "FAILED_NEGATIVE_SHA")
require(
    sha256(
        source_target
        / "packet-snapshot/candidate-artifacts/"
        "test_root_deployment_execution_packet_r1_negative.py"
    )
    == FAILED_NEGATIVE_SHA,
    "TARGET_FAILED_NEGATIVE_SHA",
)
require(hashlib.sha256(corrected_negative).hexdigest() == CORRECTED_NEGATIVE_SHA, "CORRECTED_NEGATIVE_SHA")
compile(corrected_negative.decode("utf-8"), "corrected_negative.py", "exec")

for relative, expected in PROTECTED_SHA.items():
    require(sha256(repo_root / relative) == expected, f"PROTECTED_SHA:{relative}")

source_identity_before = identity(source_root)

mkdir_exclusive(packet_root)
mkdir_exclusive(candidate_root)
create_tree(source_snapshot, source_dirs)
mkdir_exclusive(log_root)

for relative in sorted(source_files):
    copy_file(source_root / relative, source_snapshot / relative)

target_files, target_dirs, target_links, target_other = scan(source_target)
require(len(target_files) == 65, f"SOURCE_TARGET_FILE_COUNT:{len(target_files)}")
require(len(target_dirs) == 12, f"SOURCE_TARGET_DIR_COUNT:{len(target_dirs)}")
require(target_links == 0 and target_other == 0, "SOURCE_TARGET_SPECIAL")
create_tree(validation_target, target_dirs)

negative_relative = (
    "packet-snapshot/candidate-artifacts/"
    "test_root_deployment_execution_packet_r1_negative.py"
)
candidate_manifest_relative = (
    "packet-snapshot/candidate-artifacts/candidate-manifest.json"
)
target_regenerated = {
    negative_relative,
    candidate_manifest_relative,
    "packet-snapshot/packet-manifest.json",
    "result.json",
    "evidence-manifest.txt",
}
for relative in sorted(target_files):
    if relative in target_regenerated:
        continue
    copy_file(source_target / relative, validation_target / relative)

write_exclusive(validation_target / negative_relative, corrected_negative)
target_candidate = validation_target / "packet-snapshot/candidate-artifacts"
write_exclusive(
    validation_target / candidate_manifest_relative,
    regenerate_candidate_manifest(
        target_candidate,
        source_target / candidate_manifest_relative,
    ),
)
finalize_target(
    validation_target,
    new_relative + "/packet-snapshot/r1-r1-validator-target",
)

source_candidate_files, source_candidate_dirs, candidate_links, candidate_other = scan(source_candidate)
require(len(source_candidate_files) == 18, "SOURCE_CANDIDATE_FILE_COUNT")
require(not source_candidate_dirs, "SOURCE_CANDIDATE_DIR_COUNT")
require(candidate_links == 0 and candidate_other == 0, "SOURCE_CANDIDATE_SPECIAL")
for name in sorted(source_candidate_files):
    if name in {
        "candidate-manifest.json",
        "test_root_deployment_execution_packet_r1_negative.py",
    }:
        continue
    copy_file(source_candidate / name, candidate_root / name)

write_exclusive(
    candidate_root / "test_root_deployment_execution_packet_r1_negative.py",
    corrected_negative,
)
write_exclusive(
    candidate_root / "candidate-manifest.json",
    regenerate_candidate_manifest(
        candidate_root,
        source_candidate / "candidate-manifest.json",
    ),
)

require(
    sha256(candidate_root / "root_deployment_execution_once_r1.py")
    == WRAPPER_SHA,
    "CANDIDATE_WRAPPER_CHANGED",
)
require(
    sha256(candidate_root / "validate_root_deployment_execution_packet_r1.py")
    == VALIDATOR_SHA,
    "CANDIDATE_VALIDATOR_CHANGED",
)
require(
    sha256(candidate_root / "test_root_deployment_execution_packet_r1_negative.py")
    == CORRECTED_NEGATIVE_SHA,
    "CANDIDATE_NEGATIVE_SHA",
)

inventory_value = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_root": source_root.relative_to(repo_root).as_posix(),
    "source_file_count": 150,
    "source_directory_count_excluding_root": 29,
    "source_symlink_count": 0,
    "source_nonregular_count": 0,
    "source_tree_identity_entry_count": 150,
    "source_tree_identity_sha256": SOURCE_TREE_SHA,
    "source_finalization_files_present": {
        "result.json": False,
        "evidence-manifest.txt": False,
        "packet-snapshot/packet-manifest.json": False,
    },
    "files": source_inventory,
}
write_exclusive(
    packet_root / "source-r1-r2-r1-partial-inventory.json",
    (json.dumps(inventory_value, sort_keys=True, indent=2) + "\n").encode(),
)

correction_report = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_failure":
        "FAIL_NEGATIVE_TEST_MUTATION_INDENTATION",
    "source_failure_stage":
        "TEMPORARY_VALIDATOR_TARGET_NEGATIVE_TESTS",
    "source_failed_test_count": 0,
    "source_error_test_count": 2,
    "corrected_test_ids": [21, 26],
    "correction_scope":
        "NEGATIVE_TEST_MUTATION_INDENTATION_ONLY",
    "failed_helper_line":
        'replacement = (" " * statement.col_offset) + replacement_source',
    "corrected_helper_line":
        "replacement = replacement_source",
    "changed_line_count": 1,
    "ast_selector_preserved": True,
    "exact_one_selector_preserved": True,
    "call_signature_validation_preserved": True,
    "source_range_coordinates_preserved": [
        "lineno",
        "col_offset",
        "end_lineno",
        "end_col_offset",
    ],
    "mutation_compile_required": True,
    "validator_rejection_required": True,
    "failed_negative_test_sha256": FAILED_NEGATIVE_SHA,
    "corrected_negative_test_sha256": CORRECTED_NEGATIVE_SHA,
    "corrected_wrapper_sha256": WRAPPER_SHA,
    "corrected_wrapper_changed": False,
    "corrected_wrapper_executed": False,
    "validator_sha256": VALIDATOR_SHA,
    "validator_changed": False,
    "root_deployment_execution_allowed": False,
    "production_release_decision": "HOLD",
}
write_exclusive(
    packet_root / "mutation-indentation-correction-report.json",
    (json.dumps(correction_report, sort_keys=True, indent=2) + "\n").encode(),
)
write_exclusive(packet_root / "human-approval-verbatim.txt", approval_text)
write_exclusive(packet_root / "operation-manual.md", manual_text)
write_exclusive(packet_root / "correction-contract.json", contract_bytes)

compile_lines = []
for name in (
    "root_deployment_execution_once_r1.py",
    "blocked_root_deployment_execution_r1_entrypoint.py",
    "validate_root_deployment_execution_packet_r1.py",
    "test_root_deployment_execution_packet_r1_negative.py",
):
    path = candidate_root / name
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
    compile_lines.append(f"PYTHON_COMPILE_PASS={name}")
write_exclusive(
    log_root / "python-compile.log",
    ("\n".join(compile_lines) + "\n").encode(),
)

validator_path = (
    validation_target
    / "packet-snapshot/candidate-artifacts/"
    "validate_root_deployment_execution_packet_r1.py"
)
negative_path = (
    validation_target
    / "packet-snapshot/candidate-artifacts/"
    "test_root_deployment_execution_packet_r1_negative.py"
)
validator_output = run_python(validator_path, [str(validation_target)])
require("VALIDATION=PASS" in validator_output, "VALIDATOR_MARKER")
write_exclusive(log_root / "validator.log", validator_output.encode())

negative_output = run_python(negative_path, [])
require("Ran 40 tests" in negative_output, "NEGATIVE_COUNT")
require(
    [line.strip() for line in negative_output.splitlines()].count("OK") == 1,
    "NEGATIVE_OK",
)
write_exclusive(log_root / "negative-tests.log", negative_output.encode())

visudo = Path("/usr/sbin/visudo")
require(visudo.is_file(), "VISUDO_MISSING")
visudo_run = subprocess.run(
    [
        str(visudo),
        "-cf",
        str(candidate_root / "ai-media-os-3e-j-root-helper.sudoers"),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
    text=True,
)
require(visudo_run.returncode == 0, "VISUDO_NONZERO\n" + visudo_run.stdout)
write_exclusive(
    log_root / "visudo.log",
    ("VISUDO_VALIDATION=PASS\n" + visudo_run.stdout).encode(),
)

packet_entries = []
for path in sorted(packet_root.rglob("*")):
    if path.is_file():
        relative = path.relative_to(packet_root).as_posix()
        if relative != "packet-manifest.json":
            packet_entries.append(
                {
                    "name": relative,
                    "sha256": sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )

packet_manifest = {
    "schema_version": "1.0",
    "phase": PHASE,
    "status":
        "R1_R2_R2_NEGATIVE_TEST_MUTATION_INDENTATION_"
        "CORRECTION_PACKET_PREPARED_NO_EXECUTION",
    "packet_file_count_excluding_manifest": len(packet_entries),
    "packet_files": packet_entries,
    "candidate_artifact_count": 18,
    "source_partial_snapshot_file_count": 150,
    "validator_target_file_count": 65,
    "validation_log_count": 4,
    "negative_test_count": 40,
    "corrected_test_ids": [21, 26],
    "changed_line_count": 1,
    "corrected_wrapper_changed": False,
    "corrected_wrapper_executed": False,
    "validator_changed": False,
    "root_deployment_execution_allowed": False,
    "sudoers_installation_allowed": False,
    "production_release_decision": "HOLD",
}
write_exclusive(
    packet_root / "packet-manifest.json",
    (json.dumps(packet_manifest, sort_keys=True, indent=2) + "\n").encode(),
)

packet_files, packet_dirs, packet_links, packet_other = scan(packet_root)
require(packet_links == 0 and packet_other == 0, "PACKET_SPECIAL")

result = {
    "schema_version": "1.0",
    "phase": PHASE,
    "result":
        "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
        "R1_R2_R2_NEGATIVE_TEST_MUTATION_INDENTATION_"
        "CORRECTION_PREPARED_NO_EXECUTION",
    "evidence_root": new_relative,
    "source_failed_r1_r2_r1_file_count": 150,
    "source_failed_r1_r2_r1_directory_count_excluding_root": 29,
    "source_failed_r1_r2_r1_tree_identity_sha256": SOURCE_TREE_SHA,
    "source_failed_r1_r2_r1_unchanged": True,
    "source_failure":
        "FAIL_NEGATIVE_TEST_MUTATION_INDENTATION",
    "source_failure_stage":
        "TEMPORARY_VALIDATOR_TARGET_NEGATIVE_TESTS",
    "source_failed_test_count": 0,
    "source_error_test_count": 2,
    "source_partial_snapshot_file_count": 150,
    "validator_target_file_count": 65,
    "packet_file_count": len(packet_files),
    "packet_directory_count": len(packet_dirs),
    "packet_manifest_entry_count": len(packet_entries),
    "candidate_artifact_count": 18,
    "validation_log_count": 4,
    "negative_test_count": 40,
    "negative_tests": "PASS",
    "validator": "PASS",
    "visudo_static_validation": "PASS",
    "corrected_test_ids": [21, 26],
    "correction_scope":
        "NEGATIVE_TEST_MUTATION_INDENTATION_ONLY",
    "changed_line_count": 1,
    "negative_test_selector_strategy":
        "AST_PREFLIGHT_DIRECT_CALL_EXACT_ONE_SOURCE_RANGE",
    "failed_negative_test_sha256": FAILED_NEGATIVE_SHA,
    "corrected_negative_test_sha256": CORRECTED_NEGATIVE_SHA,
    "corrected_wrapper_sha256": WRAPPER_SHA,
    "corrected_wrapper_changed": False,
    "corrected_wrapper_executed": False,
    "validator_sha256": VALIDATOR_SHA,
    "validator_changed": False,
    "packet_preparation_only": True,
    "root_deployment_execution_allowed": False,
    "sudoers_installation_allowed": False,
    "production_file_creation_allowed": False,
    "production_directory_creation_allowed": False,
    "root_helper_execution_allowed": False,
    "runner_execution_allowed": False,
    "one_shot_deployment_guard_created": False,
    "approval_binding_created": False,
    "sudoers_changed": False,
    "automatic_deployment_performed": False,
    "candidate_deployed_to_production": False,
    "protected_sha_unchanged": True,
    "runner_status": "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate":
        "HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
        "R1_R2_R2_CORRECTION_READONLY",
}
write_exclusive(
    new_root / "result.json",
    (json.dumps(result, sort_keys=True, indent=2) + "\n").encode(),
)

evidence_lines = []
for path in sorted(new_root.rglob("*")):
    if path.is_file():
        relative = path.relative_to(new_root).as_posix()
        if relative != "evidence-manifest.txt":
            evidence_lines.append(f"{sha256(path)}  {relative}")
write_exclusive(
    new_root / "evidence-manifest.txt",
    ("\n".join(evidence_lines) + "\n").encode(),
)

outer_files, outer_dirs, outer_links, outer_other = scan(new_root)
require(outer_links == 0 and outer_other == 0, "OUTER_SPECIAL")
require(
    len(evidence_lines) == len(outer_files) - 1,
    "EVIDENCE_MANIFEST_ENTRY_COUNT",
)
require(not list(new_root.rglob("*.pyc")), "BYTECODE_SIDE_EFFECT")
require(identity(source_root) == source_identity_before, "SOURCE_CHANGED")

for relative, expected in PROTECTED_SHA.items():
    require(sha256(repo_root / relative) == expected, f"PROTECTED_CHANGED:{relative}")

# Persisted target revalidation after outer finalization.
validator_output_final = run_python(validator_path, [str(validation_target)])
require("VALIDATION=PASS" in validator_output_final, "FINAL_VALIDATOR")
negative_output_final = run_python(negative_path, [])
require("Ran 40 tests" in negative_output_final, "FINAL_NEGATIVE_COUNT")
require(
    [line.strip() for line in negative_output_final.splitlines()].count("OK")
    == 1,
    "FINAL_NEGATIVE_OK",
)

print(
    "RESULT=PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
    "R1_R2_R2_NEGATIVE_TEST_MUTATION_INDENTATION_"
    "CORRECTION_PREPARED_NO_EXECUTION"
)
print(f"EVIDENCE_ROOT={new_relative}")
print("SOURCE_FAILED_R1_R2_R1_FILE_COUNT=150")
print("SOURCE_FAILED_R1_R2_R1_DIRECTORY_COUNT_EXCLUDING_ROOT=29")
print(f"SOURCE_FAILED_R1_R2_R1_TREE_IDENTITY_SHA256={SOURCE_TREE_SHA}")
print("SOURCE_FAILED_R1_R2_R1_UNCHANGED=true")
print("SOURCE_PARTIAL_SNAPSHOT_FILE_COUNT=150")
print("VALIDATOR_TARGET_FILE_COUNT=65")
print(f"EVIDENCE_FILE_COUNT={len(outer_files)}")
print(f"EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT={len(outer_dirs)}")
print(f"PACKET_FILE_COUNT={len(packet_files)}")
print(f"PACKET_DIRECTORY_COUNT={len(packet_dirs)}")
print(f"PACKET_MANIFEST_ENTRY_COUNT={len(packet_entries)}")
print(f"EVIDENCE_MANIFEST_ENTRY_COUNT={len(evidence_lines)}")
print("CANDIDATE_ARTIFACT_COUNT=18")
print("VALIDATION_LOG_COUNT=4")
print("NEGATIVE_TEST_COUNT=40")
print("NEGATIVE_TESTS=PASS")
print("VALIDATOR=PASS")
print("VISUDO_STATIC_VALIDATION=PASS")
print("CORRECTED_TEST_IDS=21,26")
print("NEGATIVE_TEST_MUTATION_INDENTATION_CORRECTION_ONLY=true")
print("CHANGED_LINE_COUNT=1")
print(f"FAILED_NEGATIVE_TEST_SHA={FAILED_NEGATIVE_SHA}")
print(f"CORRECTED_NEGATIVE_TEST_SHA={CORRECTED_NEGATIVE_SHA}")
print("CORRECTED_WRAPPER_SHA_REVIEW=PASS")
print("CORRECTED_WRAPPER_CHANGED=false")
print("CORRECTED_WRAPPER_EXECUTED=false")
print("R1_R1_VALIDATOR_SHA_REVIEW=PASS")
print("R1_R1_VALIDATOR_CHANGED=false")
print("BYTECODE_SIDE_EFFECT=false")
print("R1_R2_R2_CORRECTION_PACKET_PREPARATION_ONLY=true")
print("ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false")
print("SUDOERS_INSTALLATION_ALLOWED=false")
print("PRODUCTION_FILE_CREATION_ALLOWED=false")
print("PRODUCTION_DIRECTORY_CREATION_ALLOWED=false")
print("ROOT_HELPER_EXECUTION_ALLOWED=false")
print("RUNNER_EXECUTION_ALLOWED=false")
print("ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ROOT_READONLY_VERIFICATION_REEXECUTION_ALLOWED=false")
print("ONE_SHOT_GUARD_CHANGE_ALLOWED=false")
print("SUDOERS_CHANGED=false")
print("AUTOMATIC_DEPLOYMENT_PERFORMED=false")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("PROTECTED_SHA_UNCHANGED=true")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE=HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
    "R1_R2_R2_CORRECTION_READONLY"
)
print(f"RESULT_SHA={sha256(new_root / 'result.json')}")
print(f"PACKET_MANIFEST_SHA={sha256(packet_root / 'packet-manifest.json')}")
print(f"CANDIDATE_MANIFEST_SHA={sha256(candidate_root / 'candidate-manifest.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(new_root / 'evidence-manifest.txt')}")

PY

echo "SCRIPT_EXIT_CODE=0"
