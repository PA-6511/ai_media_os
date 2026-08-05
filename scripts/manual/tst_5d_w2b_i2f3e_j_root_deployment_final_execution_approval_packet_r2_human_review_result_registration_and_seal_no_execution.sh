#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SOURCE_R2_REL="${BASE_REL}/i2f3e-j-root-deployment-final-execution-approval-packet-r2-runner-source-binding-correction-preparation-and-seal-20260726T122216Z-539539"
SOURCE_R2_ROOT="${REPO_ROOT}/${SOURCE_R2_REL}"

CANDIDATE_SOURCE_REL="${BASE_REL}/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-negative-test-mutation-indentation-correction-preparation-20260726T072647Z-534604"
CANDIDATE_SOURCE_ROOT="${REPO_ROOT}/${CANDIDATE_SOURCE_REL}"

FAILED_STAGING_1_REL="${BASE_REL}/.i2f3e-j-root-deployment-final-execution-approval-packet-preparation-and-seal-staging-20260726T102320Z-537656"
FAILED_STAGING_1_ROOT="${REPO_ROOT}/${FAILED_STAGING_1_REL}"

FAILED_STAGING_2_REL="${BASE_REL}/.i2f3e-j-root-deployment-final-execution-approval-packet-r1-staging-lifecycle-correction-preparation-and-seal-staging-20260726T110354Z-538346"
FAILED_STAGING_2_ROOT="${REPO_ROOT}/${FAILED_STAGING_2_REL}"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
FINAL_PREFIX="i2f3e-j-root-deployment-final-execution-approval-packet-r2-human-review-result-registration-and-seal"
FINAL_REL="${BASE_REL}/${FINAL_PREFIX}-${RUN_ID}"
FINAL_ROOT="${REPO_ROOT}/${FINAL_REL}"
STAGING_ROOT="${REPO_ROOT}/${BASE_REL}/.${FINAL_PREFIX}-staging-${RUN_ID}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ROOT_EXECUTION_FORBIDDEN=true" >&2
  exit 1
fi

if [[ "$#" -ne 0 ]]; then
  echo "ARBITRARY_ARGUMENT_ALLOWED=false" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$SOURCE_R2_ROOT"
test ! -L "$SOURCE_R2_ROOT"
test -d "$CANDIDATE_SOURCE_ROOT"
test ! -L "$CANDIDATE_SOURCE_ROOT"
test -d "$FAILED_STAGING_1_ROOT"
test ! -L "$FAILED_STAGING_1_ROOT"
test -d "$FAILED_STAGING_2_ROOT"
test ! -L "$FAILED_STAGING_2_ROOT"
test ! -e "$FINAL_ROOT"
test ! -L "$FINAL_ROOT"
test ! -e "$STAGING_ROOT"
test ! -L "$STAGING_ROOT"

cd "$REPO_ROOT"

printf '\n===== R2 SOURCE FIXED SHA REVIEW =====\n'
sha256sum -c <<SHAS
a93e5231ce39800f663623515fa2a190ced326915fceecbf7fb7383e6f566367  ${SOURCE_R2_ROOT}/result.json
80e49a7afdf390ee821b1515eee39c09a7ece246f218b6f4adb33841f2ea56cc  ${SOURCE_R2_ROOT}/packet-snapshot/packet-manifest.json
ede979a98e5171b4571c7a17a4a95e273c799deffb0f1d3774cbc72152702fae  ${SOURCE_R2_ROOT}/packet-snapshot/execution-candidate-binding.json
e0a0e0f1fade49f310dcc92586dc2bf627c7ebf434ce30570d293683da068294  ${SOURCE_R2_ROOT}/packet-snapshot/exact-command-contract.json
50d0327e6c034ce43ff0df3cf643e6e8b8e9f69f550e67cdf050c74e42bc775d  ${SOURCE_R2_ROOT}/packet-snapshot/final-execution-approval-token-template.json
ae8df7a3ed4dd74cdab2913067d17f15fa237c698b01810dde379bf01f91d214  ${SOURCE_R2_ROOT}/packet-snapshot/target-layout.json
f8acc73d809de4530b3bcb8712b75b7fb15a45db72b6cbba8cbc17808dccdf6d  ${SOURCE_R2_ROOT}/evidence-manifest.txt
SHAS

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$SOURCE_R2_ROOT" \
  "$CANDIDATE_SOURCE_ROOT" \
  "$FAILED_STAGING_1_ROOT" \
  "$FAILED_STAGING_2_ROOT" \
  "$STAGING_ROOT" \
  "$FINAL_ROOT" \
  "$FINAL_REL" <<'PY'
from __future__ import annotations

import base64
import ctypes
import errno
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

REPO = Path(sys.argv[1]).resolve(strict=True)
SOURCE_R2 = Path(sys.argv[2]).resolve(strict=True)
CANDIDATE_SOURCE = Path(sys.argv[3]).resolve(strict=True)
FAILED_STAGING_1 = Path(sys.argv[4]).resolve(strict=True)
FAILED_STAGING_2 = Path(sys.argv[5]).resolve(strict=True)
FAILED_STAGINGS = (FAILED_STAGING_1, FAILED_STAGING_2)
STAGING_ARGUMENT = Path(sys.argv[6])
FINAL_ARGUMENT = Path(sys.argv[7])
FINAL_REL = sys.argv[8]

PHASE = (
    "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-FINAL-EXECUTION-"
    "APPROVAL-PACKET-R2-HUMAN-REVIEW-RESULT-SEAL"
)

APPROVAL_TEXT = base64.b64decode("QVBQUk9WRV8zRV9KX1JPT1RfREVQTE9ZTUVOVF9GSU5BTF9FWEVDVVRJT05fQVBQUk9WQUxfUEFDS0VUX1IyX0hVTUFOX1JFVklFV19SRVNVTFRfUkVHSVNUUkFUSU9OX0FORF9TRUFMX05PX0VYRUNVVElPTgoK5a++6LGhUjIgRXZpZGVuY2XvvJoKCmV4Y2hhbmdlL3Jldmlld19ldmlkZW5jZS9zbGFja193b3JrZXJfcmVsZWFzZV9yZWJpbmRpbmcvCnNsYWNrLXdvcmtlci1DQU5ESURBVEUtTk9ULUFQUFJPVkVELTAxYmE4ODA5ZjEzMy8KdHN0LTVkLXcyYi1pMmUtYmFzZWxpbmUtYWJzb3JwdGlvbi1yZXJldmlldy0yMDI2MDcyNVQxNDE2MzIvCmkyZjNlLWotcm9vdC1kZXBsb3ltZW50LWZpbmFsLWV4ZWN1dGlvbi1hcHByb3ZhbC1wYWNrZXQtCnIyLXJ1bm5lci1zb3VyY2UtYmluZGluZy1jb3JyZWN0aW9uLXByZXBhcmF0aW9uLWFuZC1zZWFsLQoyMDI2MDcyNlQxMjIyMTZaLTUzOTUzOQoK5a++6LGh5Zu65a6aSWRlbnRpdHnvvJoKClJFU1VMVF9TSEE9CmE5M2U1MjMxY2UzOTgwMGY2NjM2MjM1MTVmYTJhMTkwY2VkMzI2OTE1ZmNlZWNiZjdmYjczODNlNmY1NjYzNjcKClBBQ0tFVF9NQU5JRkVTVF9TSEE9CjgwZTQ5YTdhZmRmMzkwZWU4MjFiMTUxNWVlZTM5YzA5YTdlY2UyNDZmMjE4YjZmNGFkYjMzODQxZjJlYTU2Y2MKCkNBTkRJREFURV9CSU5ESU5HX1NIQT0KZWRlOTc5YTk4ZTUxNzFiNDU3MWM3YTE3YTRhOTVlMjczYzc5OWRlZmZiMGYxZDM3NzRjYmM3MjE1MjcwMmZhZQoKRVhBQ1RfQ09NTUFORF9DT05UUkFDVF9TSEE9CmUwYTBlMGYxZmFkZTQ5ZjMxMGRjYzkyNTg2ZGMyYmY2MjdjN2ViZjQzNGNlMzA1NzBkMjkzNjgzZGEwNjgyOTQKClRPS0VOX1RFTVBMQVRFX1NIQT0KNTBkMDMyN2U2YzAzNGNlNDNmZjBkZjNjZjY0M2U2ZThiOGU5ZjY5ZjU1MGU2N2NkZjA1MGM3NGU0MmJjNzc1ZAoKRVZJREVOQ0VfTUFOSUZFU1RfU0hBPQpmOGFjYzczZDgwOWRlNDUzMGIzYmNiODcxMmI3NWI3ZmIxNWE0NWRiNzJiNmNiYmE4Y2JjMTc4MDhkY2NkZjZkCgpUQVJHRVRfTEFZT1VUX1NIQT0KYWU4ZGY3YTNlZDRkZDc0Y2RhYjI5MTMwNjdkMTdmMTVmYTIzN2M2OThiMDE4MTBkZGUzNzliZjAxZjkxZDIxNAoKSHVtYW4gUmV2aWV357WQ5p6c77yaCgpST09UX0RFUExPWU1FTlRfRklOQUxfRVhFQ1VUSU9OX0FQUFJPVkFMX1BBQ0tFVF8KUjJfU0VBTF9SRUFET05MWV9SRVZJRVdfQ09NQklORUQ9UEFTUwoKU0VBTF9SRVZJRVdfUkVBRE9OTFlfT05MWT10cnVlCgpQUklPUl9SMl9TRUFMX1JFVklFV19TRUNUSU9OUz0KUEFTU19CRUZPUkVfVEFSR0VUX0xBWU9VVF9BU1NFUlRJT04KClJFVklFV0VSX1RBUkdFVF9MQVlPVVRfU0NIRU1BX0FTU1VNUFRJT05fQ09ORklSTUVEPXRydWUKSU5JVElBTF9UQVJHRVRfTEFZT1VUX0FTU0VSVElPTl9XQVNfUEFDS0VUX0RFRkVDVD1mYWxzZQpUQVJHRVRfTEFZT1VUX1NDSEVNQV9DT1JSRUNUSU9OX1JFQURPTkxZPVBBU1MKClRBUkdFVF9MQVlPVVRfRVhBQ1RfVE9QX0xFVkVMX1NDSEVNQT1QQVNTClRBUkdFVF9MQVlPVVRfRVhBQ1RfRElSRUNUT1JZX1NFVD1QQVNTClRBUkdFVF9MQVlPVVRfRVhBQ1RfRklMRV9TRVQ9UEFTUwpUQVJHRVRfTEFZT1VUX0VYQUNUX1NVRE9FUlNfVEFSR0VUPVBBU1MKClRBUkdFVF9MQVlPVVRfUEFDS0VUX01BTklGRVNUX0JJTkRJTkc9UEFTUwpUQVJHRVRfTEFZT1VUX0VWSURFTkNFX01BTklGRVNUX0JJTkRJTkc9UEFTUwpUQVJHRVRfTEFZT1VUX0ZJWEVEX1NIQV9SRVZBTElEQVRJT049UEFTUwoKVEFSR0VUX0xBWU9VVF9PV05TX0xBWU9VVF9PTkxZPXRydWUKUkVTVUxUX09XTlNfUFJFUEFSQVRJT05fSU5TUEVDVElPTl9SRVNVTFQ9dHJ1ZQpQUkVGTElHSFRfQ09OVFJBQ1RfT1dOU19GVVRVUkVfU1RBVEVfVkVSSUZJQ0FUSU9OPXRydWUKClRBUkdFVF9TVEFURV9JTlNQRUNURURfRFVSSU5HX1BSRVBBUkFUSU9OPWZhbHNlClRBUkdFVF9TVEFURV9WRVJJRklDQVRJT05fREVGRVJSRUQ9dHJ1ZQoKRVZJREVOQ0VfTVVUQVRJT049ZmFsc2UKU0VBTEVEX1NPVVJDRV9NVVRBVElPTj1mYWxzZQpDQU5ESURBVEVfU09VUkNFX01VVEFUSU9OPWZhbHNlCkZBSUxFRF9TVEFHSU5HX01VVEFUSU9OPWZhbHNlCkJZVEVDT0RFX1NJREVfRUZGRUNUPWZhbHNlCgpIVU1BTl9SRVZJRVdfUkVTVUxUX1JFR0lTVFJBVElPTl9BTkRfU0VBTF9PTkxZPXRydWUKUk9PVF9ERVBMT1lNRU5UX0VYRUNVVElPTl9BTExPV0VEPWZhbHNlClNVRE9FUlNfSU5TVEFMTEFUSU9OX0FMTE9XRUQ9ZmFsc2UKQ09SUkVDVEVEX1dSQVBQRVJfRVhFQ1VUSU9OX0FMTE9XRUQ9ZmFsc2UKQVBQUk9WQUxfQklORElOR19DUkVBVEVEPWZhbHNlCk9ORV9TSE9UX0RFUExPWU1FTlRfR1VBUkRfQ1JFQVRFRD1mYWxzZQpGSU5BTF9FWEVDVVRJT05fQVBQUk9WQUxfSVNTVUVEPWZhbHNlCkZJTkFMX0VYRUNVVElPTl9UT0tFTl9DT05TVU1FRD1mYWxzZQpXUklURVJfRlJFRVpFX0VYRUNVVElPTj1IT0xEClBST0RVQ1RJT05fUkVMRUFTRV9ERUNJU0lPTj1IT0xEClJFTEVBU0VfU1RBVFVTPUNBTkRJREFURV9OT1RfQVBQUk9WRUQK", validate=True)
REVIEW_RESULT_TEXT = base64.b64decode(
    "Uk9PVF9ERVBMT1lNRU5UX0ZJTkFMX0VYRUNVVElPTl9BUFBST1ZBTF9QQUNLRVRfUjJfU0VBTF9SRUFET05MWV9SRVZJRVdfQ09NQklORUQ9UEFTUwpTRUFMX1JFVklFV19SRUFET05MWV9PTkxZPXRydWUKUFJJT1JfUjJfU0VBTF9SRVZJRVdfU0VDVElPTlM9UEFTU19CRUZPUkVfVEFSR0VUX0xBWU9VVF9BU1NFUlRJT04KUkVWSUVXRVJfVEFSR0VUX0xBWU9VVF9TQ0hFTUFfQVNTVU1QVElPTl9DT05GSVJNRUQ9dHJ1ZQpJTklUSUFMX1RBUkdFVF9MQVlPVVRfQVNTRVJUSU9OX1dBU19QQUNLRVRfREVGRUNUPWZhbHNlClRBUkdFVF9MQVlPVVRfU0NIRU1BX0NPUlJFQ1RJT05fUkVBRE9OTFk9UEFTUwpUQVJHRVRfTEFZT1VUX0VYQUNUX1RPUF9MRVZFTF9TQ0hFTUE9UEFTUwpUQVJHRVRfTEFZT1VUX0VYQUNUX0RJUkVDVE9SWV9TRVQ9UEFTUwpUQVJHRVRfTEFZT1VUX0VYQUNUX0ZJTEVfU0VUPVBBU1MKVEFSR0VUX0xBWU9VVF9FWEFDVF9TVURPRVJTX1RBUkdFVD1QQVNTClRBUkdFVF9MQVlPVVRfUEFDS0VUX01BTklGRVNUX0JJTkRJTkc9UEFTUwpUQVJHRVRfTEFZT1VUX0VWSURFTkNFX01BTklGRVNUX0JJTkRJTkc9UEFTUwpUQVJHRVRfTEFZT1VUX0ZJWEVEX1NIQV9SRVZBTElEQVRJT049UEFTUwpUQVJHRVRfTEFZT1VUX09XTlNfTEFZT1VUX09OTFk9dHJ1ZQpSRVNVTFRfT1dOU19QUkVQQVJBVElPTl9JTlNQRUNUSU9OX1JFU1VMVD10cnVlClBSRUZMSUdIVF9DT05UUkFDVF9PV05TX0ZVVFVSRV9TVEFURV9WRVJJRklDQVRJT049dHJ1ZQpUQVJHRVRfU1RBVEVfSU5TUEVDVEVEX0RVUklOR19QUkVQQVJBVElPTj1mYWxzZQpUQVJHRVRfU1RBVEVfVkVSSUZJQ0FUSU9OX0RFRkVSUkVEPXRydWUKRVZJREVOQ0VfTVVUQVRJT049ZmFsc2UKU0VBTEVEX1NPVVJDRV9NVVRBVElPTj1mYWxzZQpDQU5ESURBVEVfU09VUkNFX01VVEFUSU9OPWZhbHNlCkZBSUxFRF9TVEFHSU5HX01VVEFUSU9OPWZhbHNlCkJZVEVDT0RFX1NJREVfRUZGRUNUPWZhbHNlClIyX1NFQUxfUkVBRE9OTFlfUkVWSUVXX0NPUlJFQ1RJT05fRVhJVF9DT0RFPTAK",
    validate=True,
)
MANUAL_TEXT = base64.b64decode("IyAzRS1KIFIyIEZpbmFsIEV4ZWN1dGlvbiBBcHByb3ZhbCBQYWNrZXQgSHVtYW4gUmV2aWV3IFJlc3VsdAoKVGhpcyBvcGVyYXRpb24gb25seSByZWdpc3RlcnMgYW5kIHNlYWxzIHRoZSBjb21iaW5lZCByZWFkLW9ubHkgSHVtYW4gUmV2aWV3CnJlc3VsdCBmb3IgdGhlIGFscmVhZHkgc2VhbGVkIFIyIEZpbmFsIEV4ZWN1dGlvbiBBcHByb3ZhbCBQYWNrZXQuCgpUaGUgb3BlcmF0aW9uIHJldmFsaWRhdGVzOgoKLSB0aGUgZXhhY3QgMjAtZmlsZSBSMiBFdmlkZW5jZSBzZXQ7Ci0gdGhlIDE3LWVudHJ5IFBhY2tldCBtYW5pZmVzdCBhbmQgMTktZW50cnkgRXZpZGVuY2UgbWFuaWZlc3Q7Ci0gYWxsIGZpeGVkIFIyIEV2aWRlbmNlIFNIQS0yNTYgaWRlbnRpdGllczsKLSB0aGUgZXhhY3QgVGFyZ2V0IExheW91dCBzY2hlbWEgYW5kIGl0cyBtYW5pZmVzdCBiaW5kaW5nczsKLSB0aGUgMjQ1LWZpbGUgQ2FuZGlkYXRlIFNvdXJjZSB0cmVlIGlkZW50aXR5OwotIHRoZSBDYW5vbmljYWwgUnVubmVyIHNvdXJjZSBhbmQgdGhyZWUtbGV2ZWwgbWFuaWZlc3QgYmluZGluZzsKLSBib3RoIGltbXV0YWJsZSBlbXB0eSBmYWlsZWQgU3RhZ2luZyBkaXJlY3RvcmllczsKLSB0aGUgc2l4IHByb3RlY3RlZCBwcm9kdWN0aW9uIFNIQS0yNTYgaWRlbnRpdGllcy4KClRoZSBpbml0aWFsIHJlYWQtb25seSByZXZpZXcgc3RvcHBlZCBiZWNhdXNlIGl0IHJlcXVpcmVkIGEgVGFyZ2V0IExheW91dCBrZXkKdGhhdCB0aGUgYWN0dWFsIHNjaGVtYSBkb2VzIG5vdCBvd24uIFRoZSBjb3JyZWN0ZWQgcmVhZC1vbmx5IHJldmlldyBlc3RhYmxpc2hlZAp0aGF0IFRhcmdldCBMYXlvdXQgb3ducyBvbmx5IHRoZSBwbGFubmVkIGxheW91dCwgcmVzdWx0Lmpzb24gb3ducyB0aGUKcHJlcGFyYXRpb24gaW5zcGVjdGlvbiByZXN1bHQsIGFuZCBwcmVmbGlnaHQtcGF0aC1zdGF0ZS1jb250cmFjdC5qc29uIG93bnMgdGhlCmZ1dHVyZSB0YXJnZXQtc3RhdGUgdmVyaWZpY2F0aW9uIHJlcXVpcmVtZW50LgoKQSBuZXcgdW5pcXVlIHN0YWdpbmcgRXZpZGVuY2UgaXMgY3JlYXRlZCBieSBQeXRob24gb25seS4gVGhlIGNvbXBsZXRlZCBFdmlkZW5jZQppcyBzZWFsZWQgdG8gZmlsZSBtb2RlIDA0NDQgYW5kIGRpcmVjdG9yeSBtb2RlIDA1NTUsIHRoZW4gcHJvbW90ZWQgd2l0aCBMaW51eApyZW5hbWVhdDIgUkVOQU1FX05PUkVQTEFDRS4KClRoaXMgb3BlcmF0aW9uIGRvZXMgbm90IGluc3BlY3QgL29wdCB0YXJnZXRzLCByZWFkIG9yIG1vZGlmeSB0aGUgcmVhbCBzdWRvZXJzCnRhcmdldCwgY3JlYXRlIGFuIGFwcHJvdmFsIGJpbmRpbmcsIGNyZWF0ZSB0aGUgb25lLXNob3QgZ3VhcmQsIGV4ZWN1dGUgdGhlCmNvcnJlY3RlZCB3cmFwcGVyLCBleGVjdXRlIHRoZSBibG9ja2VkIGVudHJ5cG9pbnQsIGNvbm5lY3QgdG8gdGhlIGRhdGFiYXNlLApwZXJmb3JtIFNRTCwgYmFja3VwLCByZXN0b3JlLCBtaWdyYXRpb24sIEdpdC9HaXRIdWIgd3JpdGVzLCBleHRlcm5hbApjb21tdW5pY2F0aW9uLCBSb290IERlcGxveW1lbnQsIHByb2R1Y3Rpb24gYXBwcm92YWwsIG9yIHByb2R1Y3Rpb24gcmVsZWFzZS4KClByb2R1Y3Rpb24gcmVsZWFzZSByZW1haW5zIEhPTEQuCg==", validate=True)
REVIEW_CONTRACT_BYTES = base64.b64decode(
    "ewogICJhcHByb3ZhbF9iaW5kaW5nX2NyZWF0ZWQiOiBmYWxzZSwKICAiY2FuZGlkYXRlX3NvdXJjZV9kaXJlY3RvcnlfY291bnRfZXhjbHVkaW5nX3Jvb3QiOiA0NiwKICAiY2FuZGlkYXRlX3NvdXJjZV9maWxlX2NvdW50IjogMjQ1LAogICJjYW5kaWRhdGVfc291cmNlX211dGF0aW9uX2FsbG93ZWQiOiBmYWxzZSwKICAiY29ycmVjdGVkX3dyYXBwZXJfZXhlY3V0aW9uX2FsbG93ZWQiOiBmYWxzZSwKICAiZmFpbGVkX3N0YWdpbmdfY291bnQiOiAyLAogICJmYWlsZWRfc3RhZ2luZ19tdXRhdGlvbl9hbGxvd2VkIjogZmFsc2UsCiAgImZpbmFsX2V4ZWN1dGlvbl9hcHByb3ZhbF9pc3N1ZWQiOiBmYWxzZSwKICAiZmluYWxfZXhlY3V0aW9uX3Rva2VuX2NvbnN1bWVkIjogZmFsc2UsCiAgImZpbmFsX3Byb21vdGlvbiI6ICJyZW5hbWVhdDIoUkVOQU1FX05PUkVQTEFDRSkiLAogICJodW1hbl9yZXZpZXdfcmVzdWx0IjogIlBBU1MiLAogICJpbml0aWFsX3RhcmdldF9sYXlvdXRfYXNzZXJ0aW9uX3dhc19wYWNrZXRfZGVmZWN0IjogZmFsc2UsCiAgIm9uZV9zaG90X2RlcGxveW1lbnRfZ3VhcmRfY3JlYXRlZCI6IGZhbHNlLAogICJvcGVyYXRpb24iOiAiSFVNQU5fUkVWSUVXX1JFU1VMVF9SRUdJU1RSQVRJT05fQU5EX1NFQUxfT05MWSIsCiAgInBoYXNlIjogIlRTVC01RC1XMkItSTJGLTNFLUotUk9PVC1ERVBMT1lNRU5ULUZJTkFMLUVYRUNVVElPTi1BUFBST1ZBTC1QQUNLRVQtUjItSFVNQU4tUkVWSUVXLVJFU1VMVC1TRUFMIiwKICAicHJvZHVjdGlvbl9yZWxlYXNlX2RlY2lzaW9uIjogIkhPTEQiLAogICJwcm90ZWN0ZWRfc2hhX2NvdW50IjogNiwKICAicmVsZWFzZV9zdGF0dXMiOiAiQ0FORElEQVRFX05PVF9BUFBST1ZFRCIsCiAgInJldmlld2VyX3RhcmdldF9sYXlvdXRfc2NoZW1hX2Fzc3VtcHRpb25fY29uZmlybWVkIjogdHJ1ZSwKICAicm9vdF9kZXBsb3ltZW50X2V4ZWN1dGlvbl9hbGxvd2VkIjogZmFsc2UsCiAgInNjaGVtYV92ZXJzaW9uIjogIjEuMCIsCiAgInNlYWxfZGlyZWN0b3J5X21vZGUiOiAiMDU1NSIsCiAgInNlYWxfZmlsZV9tb2RlIjogIjA0NDQiLAogICJzb3VyY2VfbXV0YXRpb25fYWxsb3dlZCI6IGZhbHNlLAogICJzb3VyY2VfcjJfZXZpZGVuY2VfZGlyZWN0b3J5X2NvdW50X2V4Y2x1ZGluZ19yb290IjogMSwKICAic291cmNlX3IyX2V2aWRlbmNlX2ZpbGVfY291bnQiOiAyMCwKICAic291cmNlX3IyX2V2aWRlbmNlX21hbmlmZXN0X2VudHJ5X2NvdW50IjogMTksCiAgInNvdXJjZV9yMl9wYWNrZXRfbWFuaWZlc3RfZW50cnlfY291bnQiOiAxNywKICAic3Vkb2Vyc19pbnN0YWxsYXRpb25fYWxsb3dlZCI6IGZhbHNlLAogICJ0YXJnZXRfc3RhdGVfaW5zcGVjdGVkX2R1cmluZ19wcmVwYXJhdGlvbiI6IGZhbHNlLAogICJ0YXJnZXRfc3RhdGVfdmVyaWZpY2F0aW9uX2RlZmVycmVkIjogdHJ1ZSwKICAid3JpdGVyX2ZyZWV6ZV9leGVjdXRpb24iOiAiSE9MRCIKfQo=",
    validate=True,
)

EXPECTED_R2_FIXED_SHA = {
    "result.json":
        "a93e5231ce39800f663623515fa2a190ced326915fceecbf7fb7383e6f566367",
    "packet-snapshot/packet-manifest.json":
        "80e49a7afdf390ee821b1515eee39c09a7ece246f218b6f4adb33841f2ea56cc",
    "packet-snapshot/execution-candidate-binding.json":
        "ede979a98e5171b4571c7a17a4a95e273c799deffb0f1d3774cbc72152702fae",
    "packet-snapshot/exact-command-contract.json":
        "e0a0e0f1fade49f310dcc92586dc2bf627c7ebf434ce30570d293683da068294",
    "packet-snapshot/final-execution-approval-token-template.json":
        "50d0327e6c034ce43ff0df3cf643e6e8b8e9f69f550e67cdf050c74e42bc775d",
    "packet-snapshot/target-layout.json":
        "ae8df7a3ed4dd74cdab2913067d17f15fa237c698b01810dde379bf01f91d214",
    "evidence-manifest.txt":
        "f8acc73d809de4530b3bcb8712b75b7fb15a45db72b6cbba8cbc17808dccdf6d",
}

EXPECTED_R2_FILES = {
    "result.json",
    "evidence-manifest.txt",
    "packet-snapshot/approval-binding-required-values.json",
    "packet-snapshot/exact-command-contract.json",
    "packet-snapshot/execution-candidate-binding.json",
    "packet-snapshot/failed-staging-inventory.json",
    "packet-snapshot/final-execution-approval-token-template.json",
    "packet-snapshot/human-approval-verbatim.txt",
    "packet-snapshot/operation-manual.md",
    "packet-snapshot/operator-checklist.md",
    "packet-snapshot/packet-contract.json",
    "packet-snapshot/packet-manifest.json",
    "packet-snapshot/preflight-path-state-contract.json",
    "packet-snapshot/protected-sha-contract.json",
    "packet-snapshot/reviewer-assumption-corrections.json",
    "packet-snapshot/rollback-stop-contract.json",
    "packet-snapshot/runner-source-binding-correction.json",
    "packet-snapshot/seal-contract.json",
    "packet-snapshot/sealed-source-verification.json",
    "packet-snapshot/target-layout.json",
}
EXPECTED_R2_DIRECTORIES = {"packet-snapshot"}

EXPECTED_PACKET_PAYLOAD_FILES = {
    "approval-binding-required-values.json",
    "exact-command-contract.json",
    "execution-candidate-binding.json",
    "failed-staging-inventory.json",
    "final-execution-approval-token-template.json",
    "human-approval-verbatim.txt",
    "operation-manual.md",
    "operator-checklist.md",
    "packet-contract.json",
    "preflight-path-state-contract.json",
    "protected-sha-contract.json",
    "reviewer-assumption-corrections.json",
    "rollback-stop-contract.json",
    "runner-source-binding-correction.json",
    "seal-contract.json",
    "sealed-source-verification.json",
    "target-layout.json",
}

EXPECTED_CANDIDATE_TREE_SHA = (
    "f55823bdffd9198e05e1b727b78f47ed"
    "8a395b37f6f9ee7ee557d0c35cac666e"
)

EXPECTED_CANDIDATE_FIXED_SHA = {
    "result.json":
        "8db446727c08e063661fb7272d390b20bcb31280f08a945fd464f148c38b370d",
    "packet-snapshot/packet-manifest.json":
        "e3d74993dbafac43853e09391c35f3c591dd7dbb36f1b66b72921baa25dd9e57",
    "packet-snapshot/candidate-artifacts/candidate-manifest.json":
        "fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577",
    "evidence-manifest.txt":
        "78aa0778009d37ad1a6ec75c0ff62c2e07b42bf0dc80e32e8ce78f15e3b126f7",
}

RUNNER_CANDIDATE_MANIFEST_SHA = (
    "0677a9a9479e209a6e1ee30fdcd07996"
    "b671737850b17e79b97987578a73ec7f"
)

RUNNER_PAYLOAD_SHA = {
    "one_shot_writer_freeze_backup_restart_runner.py":
        "1ccdabcbf59d130c1010643f6444f71f3dd8ea9a1ccaa4b8bad111e098b3b052",
    "root_fd_metadata_helper.py":
        "e989fb528110a4b7c482404fc5b024e2d4a8371a6d6cf901c2a940b8f4f83888",
    "runner-policy.json":
        "261941dab03f577b0882836f000f9a0f06b255a6dbf85b78ad8b5e4a3b7682dd",
    "validate_3e_j_runner_packet.py":
        "eaf5f28f3a924da93a4dc0dc6a15669c5546c784b4207074629282954c48e65f",
    "test_3e_j_runner_negative.py":
        "3e46a59517699e7e4845f9e716bd7ca021ddf9a23714453afb784960d223238e",
    "3e_j_operation_manual.md":
        "2ff4a42b574c4fb89699cf92beb555b7c83772a381847facca1ae289a765c773",
}

CANONICAL_RUNNER_REL = (
    "packet-snapshot/r1-r1-validator-target/"
    "packet-snapshot/source-partial-evidence-snapshot/"
    "packet-snapshot/deployment-input-snapshot/runner-candidate"
)
EXECUTION_EVIDENCE_REL = "packet-snapshot/r1-r1-validator-target"

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

EXPECTED_TARGET_TOP_LEVEL = {
    "schema_version",
    "phase",
    "deployment_parent",
    "deployment_root",
    "directories",
    "files",
    "sudoers_target",
    "preparation_phase_target_write_allowed",
}

EXPECTED_TARGET_DIRECTORIES = [
    {"path": "/opt/ai-media-os/3e-j", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/bin", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/libexec", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/review", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/docs", "owner": "root", "group": "root", "mode": "0755"},
]

EXPECTED_FAILED = (
    {
        "mode": 0o750,
        "uid": 1001,
        "gid": 1001,
        "mtime_ns": 1785061400585610693,
    },
    {
        "mode": 0o750,
        "uid": 1001,
        "gid": 1001,
        "mtime_ns": 1785063834302475917,
    },
)


def require(condition: bool, marker: str) -> None:
    if not condition:
        raise AssertionError(marker)


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


def scan(root: Path) -> tuple[set[str], set[str], int, int]:
    files: set[str] = set()
    directories: set[str] = set()
    symlinks = 0
    nonregular = 0
    for path in sorted(root.rglob("*")):
        item = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(item.st_mode):
            symlinks += 1
        elif stat.S_ISREG(item.st_mode):
            files.add(relative)
        elif stat.S_ISDIR(item.st_mode):
            directories.add(relative)
        else:
            nonregular += 1
    return files, directories, symlinks, nonregular


def identity(root: Path) -> dict[str, tuple[object, ...]]:
    result: dict[str, tuple[object, ...]] = {}
    item = root.lstat()
    result["."] = (
        "DIR",
        stat.S_IMODE(item.st_mode),
        item.st_uid,
        item.st_gid,
        item.st_mtime_ns,
    )
    files, directories, symlinks, nonregular = scan(root)
    require(symlinks == 0, f"IDENTITY_SYMLINK:{root}")
    require(nonregular == 0, f"IDENTITY_NONREGULAR:{root}")
    for relative in sorted(directories):
        child = (root / relative).lstat()
        result[relative + "/"] = (
            "DIR",
            stat.S_IMODE(child.st_mode),
            child.st_uid,
            child.st_gid,
            child.st_mtime_ns,
        )
    for relative in sorted(files):
        path = root / relative
        child = path.lstat()
        result[relative] = (
            "FILE",
            child.st_size,
            stat.S_IMODE(child.st_mode),
            child.st_uid,
            child.st_gid,
            child.st_mtime_ns,
            sha256(path),
        )
    return result


def tree_identity(root: Path) -> tuple[str, list[dict[str, object]]]:
    files, _, symlinks, nonregular = scan(root)
    require(symlinks == 0 and nonregular == 0, f"TREE_SPECIAL:{root}")
    entries: list[dict[str, object]] = []
    lines: list[str] = []
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        digest = sha256(path)
        mode = f"{stat.S_IMODE(item.st_mode):04o}"
        entries.append({
            "relative_path": relative,
            "size_bytes": item.st_size,
            "mode": mode,
            "uid": item.st_uid,
            "gid": item.st_gid,
            "sha256": digest,
        })
        lines.append(
            f"{digest}  {item.st_size}  {mode}  "
            f"{item.st_uid}  {item.st_gid}  {relative}"
        )
    tree_sha = hashlib.sha256(
        ("\n".join(lines) + "\n").encode("utf-8")
    ).hexdigest()
    return tree_sha, entries


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_NOT_OBJECT:{path}")
    return value


def manifest_entries(value: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("packet_files", "files", "artifacts", "candidate_files"):
        entries = value.get(key)
        if isinstance(entries, list):
            require(
                all(isinstance(entry, dict) for entry in entries),
                f"MANIFEST_ENTRY_TYPE:{key}",
            )
            return entries
    raise AssertionError("MANIFEST_ENTRY_LIST_NOT_FOUND")


def entry_name(entry: dict[str, Any]) -> str:
    for key in ("name", "relative_path", "path", "filename"):
        value = entry.get(key)
        if isinstance(value, str):
            return value
    raise AssertionError("MANIFEST_ENTRY_NAME_NOT_FOUND")


def evidence_manifest_map(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, raw in enumerate(
        (root / "evidence-manifest.txt")
        .read_text(encoding="utf-8")
        .splitlines(),
        start=1,
    ):
        require("  " in raw, f"EVIDENCE_FORMAT:{line_number}")
        digest, relative = raw.split("  ", 1)
        require(relative not in result, f"EVIDENCE_DUP:{relative}")
        result[relative] = digest
    return result


def json_manifest_map(path: Path) -> dict[str, dict[str, Any]]:
    value = json_object(path)
    result: dict[str, dict[str, Any]] = {}
    for entry in manifest_entries(value):
        relative = entry_name(entry)
        require(relative not in result, f"JSON_MANIFEST_DUP:{relative}")
        result[relative] = entry
    return result


def validate_evidence(root: Path, expected_files: int, expected_entries: int) -> dict[str, str]:
    files, _, links, other = scan(root)
    require(links == 0 and other == 0, f"EVIDENCE_SPECIAL:{root}")
    require(len(files) == expected_files, f"EVIDENCE_FILE_COUNT:{len(files)}")
    mapping = evidence_manifest_map(root)
    require(len(mapping) == expected_entries, f"EVIDENCE_ENTRY_COUNT:{len(mapping)}")
    require(
        set(mapping) == files - {"evidence-manifest.txt"},
        "EVIDENCE_EXACT_SET",
    )
    for relative, expected in mapping.items():
        require(sha256(root / relative) == expected, f"EVIDENCE_SHA:{relative}")
    return mapping


def validate_packet(root: Path, expected_files: int, expected_entries: int) -> dict[str, dict[str, Any]]:
    files, _, links, other = scan(root)
    require(links == 0 and other == 0, f"PACKET_SPECIAL:{root}")
    require(len(files) == expected_files, f"PACKET_FILE_COUNT:{len(files)}")
    mapping = json_manifest_map(root / "packet-manifest.json")
    require(len(mapping) == expected_entries, f"PACKET_ENTRY_COUNT:{len(mapping)}")
    require(
        set(mapping) == files - {"packet-manifest.json"},
        "PACKET_EXACT_SET",
    )
    for relative, entry in mapping.items():
        path = root / relative
        require(entry.get("sha256") == sha256(path), f"PACKET_SHA:{relative}")
        require(
            entry.get("size_bytes") == path.stat().st_size,
            f"PACKET_SIZE:{relative}",
        )
    return mapping


def rename_noreplace(source: Path, destination: Path) -> None:
    require(not os.path.lexists(destination), "FINAL_PATH_ENTRY_EXISTS")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = libc.renameat2
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100,
        os.fsencode(source),
        -100,
        os.fsencode(destination),
        1,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise FileExistsError(destination)
        raise OSError(error, os.strerror(error))


# Resolve only repository Evidence paths. No /opt or real sudoers access.
for name, path in (
    ("SOURCE_R2", SOURCE_R2),
    ("CANDIDATE_SOURCE", CANDIDATE_SOURCE),
    ("FAILED_STAGING_1", FAILED_STAGING_1),
    ("FAILED_STAGING_2", FAILED_STAGING_2),
):
    require(path.is_relative_to(REPO), f"{name}_OUTSIDE_REPO")
    item = path.lstat()
    require(
        stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode),
        f"{name}_TYPE",
    )

staging_parent = STAGING_ARGUMENT.parent.resolve(strict=True)
final_parent = FINAL_ARGUMENT.parent.resolve(strict=True)
require(staging_parent == final_parent, "STAGING_FINAL_PARENT_MISMATCH")
require(staging_parent.is_relative_to(REPO), "STAGING_PARENT_OUTSIDE_REPO")
require(not os.path.lexists(STAGING_ARGUMENT), "STAGING_PATH_ENTRY_EXISTS")
require(not os.path.lexists(FINAL_ARGUMENT), "FINAL_PATH_ENTRY_EXISTS")

source_identity_before = identity(SOURCE_R2)
candidate_identity_before = identity(CANDIDATE_SOURCE)
failed_identity_before = tuple(identity(path) for path in FAILED_STAGINGS)

os.mkdir(STAGING_ARGUMENT, 0o750)
STAGING = STAGING_ARGUMENT.resolve(strict=True)
FINAL = FINAL_ARGUMENT
PACKET = STAGING / "packet-snapshot"
os.mkdir(PACKET, 0o750)

print("===== R2 SOURCE EVIDENCE REVALIDATION =====")

source_files, source_dirs, source_links, source_other = scan(SOURCE_R2)
require(source_files == EXPECTED_R2_FILES, "R2_SOURCE_EXACT_FILE_SET")
require(source_dirs == EXPECTED_R2_DIRECTORIES, "R2_SOURCE_EXACT_DIR_SET")
require(source_links == 0 and source_other == 0, "R2_SOURCE_SPECIAL")
require(stat.S_IMODE(SOURCE_R2.lstat().st_mode) == 0o555, "R2_SOURCE_ROOT_MODE")
for relative in source_files:
    require(
        stat.S_IMODE((SOURCE_R2 / relative).lstat().st_mode) == 0o444,
        f"R2_SOURCE_FILE_MODE:{relative}",
    )
for relative in source_dirs:
    require(
        stat.S_IMODE((SOURCE_R2 / relative).lstat().st_mode) == 0o555,
        f"R2_SOURCE_DIR_MODE:{relative}",
    )
for relative, expected in EXPECTED_R2_FIXED_SHA.items():
    require(sha256(SOURCE_R2 / relative) == expected, f"R2_SOURCE_FIXED_SHA:{relative}")

source_evidence_map = validate_evidence(SOURCE_R2, 20, 19)
source_packet_root = SOURCE_R2 / "packet-snapshot"
source_packet_map = validate_packet(source_packet_root, 18, 17)
require(set(source_packet_map) == EXPECTED_PACKET_PAYLOAD_FILES, "R2_PACKET_PAYLOAD_SET")

source_result = json_object(SOURCE_R2 / "result.json")
require(
    source_result.get("result")
    == (
        "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
        "PACKET_R2_RUNNER_SOURCE_BINDING_CORRECTION_"
        "PREPARED_AND_SEALED_NO_EXECUTION"
    ),
    "R2_SOURCE_RESULT",
)
require(source_result.get("canonical_runner_source_binding") == "PASS", "R2_RUNNER_BINDING")
require(source_result.get("three_level_runner_manifest_binding") == "PASS", "R2_THREE_LEVEL")
require(source_result.get("failed_staging_count") == 2, "R2_FAILED_STAGING_COUNT")
require(source_result.get("failed_staging_unchanged") is True, "R2_FAILED_STAGING")
require(source_result.get("protected_sha_revalidation") == "PASS", "R2_PROTECTED_SHA")
for key in (
    "final_execution_approval_issued",
    "final_execution_token_consumed",
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "corrected_wrapper_execution_allowed",
    "approval_binding_created",
    "one_shot_deployment_guard_created",
):
    require(source_result.get(key) is False, f"R2_FALSE_FLAG:{key}")
require(source_result.get("writer_freeze_execution") == "HOLD", "R2_WRITER_HOLD")
require(source_result.get("production_release_decision") == "HOLD", "R2_PRODUCTION_HOLD")
require(source_result.get("release_status") == "CANDIDATE_NOT_APPROVED", "R2_RELEASE_STATUS")

print("R2_SOURCE_EVIDENCE_FILE_COUNT=20")
print("R2_SOURCE_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("R2_SOURCE_PACKET_MANIFEST_ENTRY_COUNT=17")
print("R2_SOURCE_EVIDENCE_MANIFEST_ENTRY_COUNT=19")
print("R2_SOURCE_EVIDENCE_REVALIDATION=PASS")
print("R2_SOURCE_EVIDENCE_UNCHANGED=true")

print("\n===== TARGET LAYOUT SCHEMA REVALIDATION =====")

target_path = source_packet_root / "target-layout.json"
target = json_object(target_path)
require(set(target) == EXPECTED_TARGET_TOP_LEVEL, "TARGET_LAYOUT_TOP_LEVEL")
require(target.get("deployment_parent") == "/opt/ai-media-os", "TARGET_DEPLOYMENT_PARENT")
require(target.get("deployment_root") == "/opt/ai-media-os/3e-j", "TARGET_DEPLOYMENT_ROOT")
require(target.get("directories") == EXPECTED_TARGET_DIRECTORIES, "TARGET_DIRECTORIES")
files = target.get("files")
require(isinstance(files, list) and len(files) == 6, "TARGET_FILES")
require(target.get("preparation_phase_target_write_allowed") is False, "TARGET_WRITE_ALLOWED")
sudoers_target = target.get("sudoers_target")
require(isinstance(sudoers_target, dict), "TARGET_SUDOERS_OBJECT")
require(sudoers_target.get("path") == "/etc/sudoers.d/ai-media-os-3e-j-root-helper", "TARGET_SUDOERS_PATH")
require(sudoers_target.get("owner") == "root", "TARGET_SUDOERS_OWNER")
require(sudoers_target.get("group") == "root", "TARGET_SUDOERS_GROUP")
require(sudoers_target.get("mode") == "0440", "TARGET_SUDOERS_MODE")
require(sudoers_target.get("exclusive_create") is True, "TARGET_SUDOERS_EXCLUSIVE")
require(sudoers_target.get("overwrite_allowed") is False, "TARGET_SUDOERS_OVERWRITE")
require(
    sudoers_target.get("content_sha256")
    == "d7d20b84f5f2b03d9a75683853a17958a2e70c93cc0b0c5e150d89511b8ee3b2",
    "TARGET_SUDOERS_SHA",
)
require("target_state_inspected" not in target, "TARGET_UNEXPECTED_INSPECTED_KEY")
require(
    "target_state_inspected_during_preparation" not in target,
    "TARGET_UNEXPECTED_PREPARATION_KEY",
)
require(
    "target_state_inspection_allowed_current_phase" not in target,
    "TARGET_UNEXPECTED_ALLOWED_KEY",
)
require(
    source_packet_map["target-layout.json"].get("sha256")
    == EXPECTED_R2_FIXED_SHA["packet-snapshot/target-layout.json"],
    "TARGET_PACKET_SHA",
)
require(
    source_evidence_map["packet-snapshot/target-layout.json"]
    == EXPECTED_R2_FIXED_SHA["packet-snapshot/target-layout.json"],
    "TARGET_EVIDENCE_SHA",
)
preflight = json_object(source_packet_root / "preflight-path-state-contract.json")
require(preflight.get("target_state_inspected_during_preparation") is False, "PREFLIGHT_INSPECTED")
require(
    preflight.get("target_state_verification_deferred_to_final_execution_preflight")
    is True,
    "PREFLIGHT_DEFERRED",
)
require(preflight.get("production_release_must_remain_hold") is True, "PREFLIGHT_HOLD")

print("TARGET_LAYOUT_EXACT_TOP_LEVEL_SCHEMA=PASS")
print("TARGET_LAYOUT_EXACT_DIRECTORY_SET=PASS")
print("TARGET_LAYOUT_FILE_COUNT=6")
print("TARGET_LAYOUT_EXACT_SUDOERS_TARGET=PASS")
print("TARGET_LAYOUT_PACKET_MANIFEST_BINDING=PASS")
print("TARGET_LAYOUT_EVIDENCE_MANIFEST_BINDING=PASS")
print("TARGET_LAYOUT_FIXED_SHA_REVALIDATION=PASS")
print("TARGET_LAYOUT_OWNS_LAYOUT_ONLY=true")
print("RESULT_OWNS_PREPARATION_INSPECTION_RESULT=true")
print("PREFLIGHT_CONTRACT_OWNS_FUTURE_STATE_VERIFICATION=true")
print("TARGET_STATE_INSPECTED_DURING_PREPARATION=false")
print("TARGET_STATE_VERIFICATION_DEFERRED=true")

print("\n===== CANDIDATE SOURCE AND RUNNER REVALIDATION =====")

candidate_files, candidate_dirs, candidate_links, candidate_other = scan(CANDIDATE_SOURCE)
require(len(candidate_files) == 245, "CANDIDATE_FILE_COUNT")
require(len(candidate_dirs) == 46, "CANDIDATE_DIR_COUNT")
require(candidate_links == 0 and candidate_other == 0, "CANDIDATE_SPECIAL")
for relative, expected in EXPECTED_CANDIDATE_FIXED_SHA.items():
    require(sha256(CANDIDATE_SOURCE / relative) == expected, f"CANDIDATE_FIXED_SHA:{relative}")
candidate_tree_sha, candidate_entries = tree_identity(CANDIDATE_SOURCE)
require(candidate_tree_sha == EXPECTED_CANDIDATE_TREE_SHA, "CANDIDATE_TREE_SHA")

execution_evidence = CANDIDATE_SOURCE / EXECUTION_EVIDENCE_REL
execution_packet = execution_evidence / "packet-snapshot"
runner_root = CANDIDATE_SOURCE / CANONICAL_RUNNER_REL
execution_evidence_map = validate_evidence(execution_evidence, 65, 64)
execution_packet_map = validate_packet(execution_packet, 63, 62)
runner_files, runner_dirs, runner_links, runner_other = scan(runner_root)
require(len(runner_files) == 7, "RUNNER_FILE_COUNT")
require(len(runner_dirs) == 0, "RUNNER_DIR_COUNT")
require(runner_links == 0 and runner_other == 0, "RUNNER_SPECIAL")
require(
    sha256(runner_root / "candidate-manifest.json")
    == RUNNER_CANDIDATE_MANIFEST_SHA,
    "RUNNER_MANIFEST_SHA",
)
runner_map = validate_packet(runner_root, 7, 6)
require(set(runner_map) == set(RUNNER_PAYLOAD_SHA), "RUNNER_PAYLOAD_SET")
for filename, expected in RUNNER_PAYLOAD_SHA.items():
    path = runner_root / filename
    require(sha256(path) == expected, f"RUNNER_SHA:{filename}")
    require(runner_map[filename].get("sha256") == expected, f"RUNNER_MANIFEST_ENTRY_SHA:{filename}")
    require(
        runner_map[filename].get("size_bytes") == path.stat().st_size,
        f"RUNNER_MANIFEST_ENTRY_SIZE:{filename}",
    )
    packet_relative = (
        "source-partial-evidence-snapshot/packet-snapshot/"
        f"deployment-input-snapshot/runner-candidate/{filename}"
    )
    evidence_relative = f"packet-snapshot/{packet_relative}"
    require(packet_relative in execution_packet_map, f"THREE_LEVEL_PACKET:{filename}")
    require(evidence_relative in execution_evidence_map, f"THREE_LEVEL_EVIDENCE:{filename}")
    require(execution_packet_map[packet_relative].get("sha256") == expected, f"THREE_LEVEL_PACKET_SHA:{filename}")
    require(execution_evidence_map[evidence_relative] == expected, f"THREE_LEVEL_EVIDENCE_SHA:{filename}")

print("CANDIDATE_SOURCE_FILE_COUNT=245")
print("CANDIDATE_SOURCE_DIRECTORY_COUNT_EXCLUDING_ROOT=46")
print(f"CANDIDATE_SOURCE_TREE_IDENTITY_SHA256={candidate_tree_sha}")
print("CANDIDATE_SOURCE_IDENTITY_REVALIDATION=PASS")
print("EXECUTION_EVIDENCE_FILE_COUNT=65")
print("EXECUTION_EVIDENCE_MANIFEST_ENTRY_COUNT=64")
print("EXECUTION_PACKET_FILE_COUNT=63")
print("EXECUTION_PACKET_MANIFEST_ENTRY_COUNT=62")
print("CANONICAL_RUNNER_SOURCE_BINDING=PASS")
print("RUNNER_CANDIDATE_FILE_COUNT=7")
print("RUNNER_CANDIDATE_MANIFEST_ENTRY_COUNT=6")
print("RUNNER_CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("THREE_LEVEL_RUNNER_MANIFEST_BINDING=PASS")

print("\n===== FAILED STAGING AND PROTECTED SHA REVALIDATION =====")

failed_records: list[dict[str, object]] = []
for index, (root, expected) in enumerate(zip(FAILED_STAGINGS, EXPECTED_FAILED), start=1):
    item = root.lstat()
    files, directories, links, other = scan(root)
    require(stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode), f"FAILED_TYPE:{index}")
    require(stat.S_IMODE(item.st_mode) == expected["mode"], f"FAILED_MODE:{index}")
    require(item.st_uid == expected["uid"], f"FAILED_UID:{index}")
    require(item.st_gid == expected["gid"], f"FAILED_GID:{index}")
    require(item.st_mtime_ns == expected["mtime_ns"], f"FAILED_MTIME:{index}")
    require(len(files) == 0 and len(directories) == 0, f"FAILED_CONTENT:{index}")
    require(links == 0 and other == 0, f"FAILED_SPECIAL:{index}")
    failed_records.append({
        "index": index,
        "relative_path": root.relative_to(REPO).as_posix(),
        "mode": "0750",
        "uid": item.st_uid,
        "gid": item.st_gid,
        "mtime_ns": item.st_mtime_ns,
        "file_count": 0,
        "directory_count_excluding_root": 0,
        "symlink_count": 0,
        "nonregular_count": 0,
        "identity_revalidation": "PASS",
        "empty": True,
        "unchanged": True,
    })
    print(f"FAILED_STAGING_{index}_IDENTITY=PASS")
    print(f"FAILED_STAGING_{index}_EMPTY=true")

for relative, expected in PROTECTED_SHA.items():
    path = REPO / relative
    require(path.is_file() and not path.is_symlink(), f"PROTECTED_PATH:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

print("FAILED_STAGING_COUNT=2")
print("FAILED_STAGING_UNCHANGED=true")
print("PROTECTED_SHA_COUNT=6")
print("PROTECTED_SHA_REVALIDATION=PASS")
print("DATABASE_CONNECTION_PERFORMED=false")
print("SQL_PERFORMED=false")
print("PRODUCTION_MANIFEST_CHANGED=false")

source_inventory = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_r2_evidence_root": SOURCE_R2.relative_to(REPO).as_posix(),
    "source_r2_evidence_file_count": 20,
    "source_r2_evidence_directory_count_excluding_root": 1,
    "source_r2_evidence_manifest_entry_count": 19,
    "source_r2_packet_manifest_entry_count": 17,
    "candidate_source_root": CANDIDATE_SOURCE.relative_to(REPO).as_posix(),
    "candidate_source_file_count": 245,
    "candidate_source_directory_count_excluding_root": 46,
    "candidate_source_tree_identity_sha256": candidate_tree_sha,
    "candidate_source_files": candidate_entries,
}

source_verification = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_r2_fixed_sha": EXPECTED_R2_FIXED_SHA,
    "source_r2_exact_file_set": "PASS",
    "source_r2_evidence_manifest_revalidation": "PASS",
    "source_r2_packet_manifest_revalidation": "PASS",
    "target_layout_exact_schema": "PASS",
    "target_layout_packet_manifest_binding": "PASS",
    "target_layout_evidence_manifest_binding": "PASS",
    "target_layout_fixed_sha_revalidation": "PASS",
    "candidate_source_identity_revalidation": "PASS",
    "canonical_runner_source_binding": "PASS",
    "runner_candidate_manifest_revalidation": "PASS",
    "three_level_runner_manifest_binding": "PASS",
    "failed_staging_count": 2,
    "failed_staging_unchanged": True,
    "protected_sha_count": 6,
    "protected_sha_revalidation": "PASS",
    "database_connection_performed": False,
    "sql_performed": False,
    "production_manifest_changed": False,
    "bytecode_side_effect": False,
}

target_schema_correction = {
    "schema_version": "1.0",
    "phase": PHASE,
    "initial_readonly_review_exit_code": 1,
    "initial_assertion": "TARGET_LAYOUT_INSPECTED",
    "error_class": "REVIEWER_TARGET_LAYOUT_SCHEMA_ASSUMPTION",
    "reviewer_target_layout_schema_assumption_confirmed": True,
    "initial_target_layout_assertion_was_packet_defect": False,
    "target_layout_exact_top_level_schema": "PASS",
    "target_layout_exact_directory_set": "PASS",
    "target_layout_file_count": 6,
    "target_layout_exact_sudoers_target": "PASS",
    "target_layout_packet_manifest_binding": "PASS",
    "target_layout_evidence_manifest_binding": "PASS",
    "target_layout_fixed_sha_revalidation": "PASS",
    "target_layout_owns_layout_only": True,
    "result_owns_preparation_inspection_result": True,
    "preflight_contract_owns_future_state_verification": True,
    "target_state_inspected_during_preparation": False,
    "target_state_verification_deferred": True,
    "corrected_readonly_review_exit_code": 0,
    "combined_readonly_review_result": "PASS",
}

combined_review = {
    "schema_version": "1.0",
    "phase": PHASE,
    "human_review_result": "PASS",
    "root_deployment_final_execution_approval_packet_r2_seal_readonly_review_combined": "PASS",
    "seal_review_readonly_only": True,
    "prior_r2_seal_review_sections": "PASS_BEFORE_TARGET_LAYOUT_ASSERTION",
    "reviewer_target_layout_schema_assumption_confirmed": True,
    "initial_target_layout_assertion_was_packet_defect": False,
    "target_layout_schema_correction_readonly": "PASS",
    "evidence_mutation": False,
    "candidate_source_mutation": False,
    "failed_staging_mutation": False,
    "bytecode_side_effect": False,
}

failed_staging_verification = {
    "schema_version": "1.0",
    "phase": PHASE,
    "failed_staging_count": 2,
    "records": failed_records,
    "failed_staging_mutation": False,
    "immutable_partial_failure_records": True,
}

protected_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "protected_sha256": PROTECTED_SHA,
    "protected_sha_count": 6,
    "revalidation_result": "PASS",
    "database_connection_performed": False,
    "sql_performed": False,
    "production_manifest_changed": False,
}

seal_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "staging_required": True,
    "python_is_sole_staging_creator": True,
    "shell_staging_mkdir_allowed": False,
    "file_mode_after_seal": "0444",
    "directory_mode_after_seal": "0555",
    "final_promotion": "renameat2(RENAME_NOREPLACE)",
    "source_r2_evidence_mutation_allowed": False,
    "candidate_source_mutation_allowed": False,
    "failed_staging_mutation_allowed": False,
    "root_deployment_execution_allowed": False,
    "production_release_decision": "HOLD",
}


def write_json(name: str, value: dict[str, Any]) -> None:
    write_exclusive(
        PACKET / name,
        (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"),
    )


write_json("source-inventory.json", source_inventory)
write_json("source-verification.json", source_verification)
write_json("target-layout-schema-correction.json", target_schema_correction)
write_json("combined-readonly-review-result.json", combined_review)
write_json("failed-staging-verification.json", failed_staging_verification)
write_json("protected-sha-contract.json", protected_contract)
write_json("seal-contract.json", seal_contract)
write_exclusive(PACKET / "human-approval-verbatim.txt", APPROVAL_TEXT)
write_exclusive(PACKET / "human-review-result-verbatim.txt", REVIEW_RESULT_TEXT)
write_exclusive(PACKET / "operation-manual.md", MANUAL_TEXT)
write_exclusive(PACKET / "review-contract.json", REVIEW_CONTRACT_BYTES)

review_result = {
    "schema_version": "1.0",
    "phase": PHASE,
    "result": (
        "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
        "PACKET_R2_HUMAN_REVIEW_RESULT_REGISTERED_AND_SEALED_NO_EXECUTION"
    ),
    "evidence_root": FINAL_REL,
    "source_r2_evidence_root": SOURCE_R2.relative_to(REPO).as_posix(),
    "candidate_source_root": CANDIDATE_SOURCE.relative_to(REPO).as_posix(),
    "human_review_result": "PASS",
    "combined_readonly_review_result": "PASS",
    "reviewer_target_layout_schema_assumption_confirmed": True,
    "initial_target_layout_assertion_was_packet_defect": False,
    "target_layout_schema_correction_readonly": "PASS",
    "source_r2_evidence_file_count": 20,
    "source_r2_evidence_directory_count_excluding_root": 1,
    "source_r2_packet_manifest_entry_count": 17,
    "source_r2_evidence_manifest_entry_count": 19,
    "candidate_source_file_count": 245,
    "candidate_source_directory_count_excluding_root": 46,
    "candidate_source_tree_identity_sha256": candidate_tree_sha,
    "target_layout_exact_schema": "PASS",
    "target_layout_fixed_sha_revalidation": "PASS",
    "canonical_runner_source_binding": "PASS",
    "runner_candidate_manifest_revalidation": "PASS",
    "three_level_runner_manifest_binding": "PASS",
    "failed_staging_count": 2,
    "failed_staging_unchanged": True,
    "protected_sha_count": 6,
    "protected_sha_revalidation": "PASS",
    "target_state_inspected_during_preparation": False,
    "target_state_verification_deferred": True,
    "evidence_mutation": False,
    "candidate_source_mutation": False,
    "failed_staging_mutation": False,
    "bytecode_side_effect": False,
    "human_review_result_registration_and_seal_only": True,
    "sealed": True,
    "seal_file_mode": "0444",
    "seal_directory_mode": "0555",
    "final_promotion": "renameat2(RENAME_NOREPLACE)",
    "root_deployment_execution_allowed": False,
    "sudoers_installation_allowed": False,
    "corrected_wrapper_execution_allowed": False,
    "approval_binding_created": False,
    "one_shot_deployment_guard_created": False,
    "final_execution_approval_issued": False,
    "final_execution_token_consumed": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": (
        "HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
        "PACKET_R2_HUMAN_REVIEW_RESULT_SEAL_READONLY"
    ),
}
write_exclusive(
    STAGING / "review-result.json",
    (json.dumps(review_result, sort_keys=True, indent=2) + "\n").encode("utf-8"),
)

packet_entries: list[dict[str, object]] = []
for path in sorted(PACKET.rglob("*")):
    if path.is_file():
        relative = path.relative_to(PACKET).as_posix()
        if relative != "packet-manifest.json":
            packet_entries.append({
                "name": relative,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            })

packet_manifest = {
    "schema_version": "1.0",
    "phase": PHASE,
    "status": "R2_HUMAN_REVIEW_RESULT_REGISTERED_AND_SEALED_NO_EXECUTION",
    "packet_file_count_excluding_manifest": len(packet_entries),
    "packet_files": packet_entries,
    "source_r2_evidence_file_count": 20,
    "source_r2_evidence_manifest_entry_count": 19,
    "source_r2_packet_manifest_entry_count": 17,
    "candidate_source_file_count": 245,
    "candidate_source_tree_identity_sha256": candidate_tree_sha,
    "human_review_result": "PASS",
    "combined_readonly_review_result": "PASS",
    "target_layout_schema_correction_readonly": "PASS",
    "failed_staging_count": 2,
    "protected_sha_count": 6,
    "human_review_result_registration_and_seal_only": True,
    "sealed": True,
    "root_deployment_execution_allowed": False,
    "final_execution_approval_issued": False,
    "final_execution_token_consumed": False,
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_exclusive(
    PACKET / "packet-manifest.json",
    (json.dumps(packet_manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"),
)

evidence_lines: list[str] = []
for path in sorted(STAGING.rglob("*")):
    if path.is_file():
        relative = path.relative_to(STAGING).as_posix()
        if relative != "evidence-manifest.txt":
            evidence_lines.append(f"{sha256(path)}  {relative}")
write_exclusive(
    STAGING / "evidence-manifest.txt",
    ("\n".join(evidence_lines) + "\n").encode("utf-8"),
)

staging_files, staging_dirs, staging_links, staging_other = scan(STAGING)
require(staging_links == 0 and staging_other == 0, "NEW_EVIDENCE_SPECIAL")
require(len(staging_files) == 14, f"NEW_EVIDENCE_FILE_COUNT:{len(staging_files)}")
require(len(staging_dirs) == 1, f"NEW_EVIDENCE_DIR_COUNT:{len(staging_dirs)}")
require(len(packet_entries) == 11, f"NEW_PACKET_ENTRY_COUNT:{len(packet_entries)}")
require(len(evidence_lines) == 13, f"NEW_EVIDENCE_ENTRY_COUNT:{len(evidence_lines)}")

new_packet_map = validate_packet(PACKET, 12, 11)
new_evidence_map = validate_evidence(STAGING, 14, 13)

require(identity(SOURCE_R2) == source_identity_before, "SOURCE_R2_CHANGED_PRE_SEAL")
require(identity(CANDIDATE_SOURCE) == candidate_identity_before, "CANDIDATE_CHANGED_PRE_SEAL")
for index, (root, expected_identity) in enumerate(
    zip(FAILED_STAGINGS, failed_identity_before),
    start=1,
):
    require(identity(root) == expected_identity, f"FAILED_CHANGED_PRE_SEAL:{index}")

for path in sorted(
    (item for item in STAGING.rglob("*") if item.is_file()),
    key=lambda item: item.as_posix(),
):
    os.chmod(path, 0o444)

for path in sorted(
    (item for item in STAGING.rglob("*") if item.is_dir()),
    key=lambda item: item.as_posix(),
    reverse=True,
):
    os.chmod(path, 0o555)

os.chmod(STAGING, 0o555)

for path in sorted(STAGING.rglob("*")):
    item = path.lstat()
    if stat.S_ISREG(item.st_mode):
        require(stat.S_IMODE(item.st_mode) == 0o444, f"SEALED_FILE_MODE:{path}")
    elif stat.S_ISDIR(item.st_mode):
        require(stat.S_IMODE(item.st_mode) == 0o555, f"SEALED_DIR_MODE:{path}")
    else:
        raise AssertionError(f"SEALED_SPECIAL:{path}")
require(stat.S_IMODE(STAGING.lstat().st_mode) == 0o555, "SEALED_ROOT_MODE")

require(identity(SOURCE_R2) == source_identity_before, "SOURCE_R2_CHANGED_POST_SEAL")
require(identity(CANDIDATE_SOURCE) == candidate_identity_before, "CANDIDATE_CHANGED_POST_SEAL")
for index, (root, expected_identity) in enumerate(
    zip(FAILED_STAGINGS, failed_identity_before),
    start=1,
):
    require(identity(root) == expected_identity, f"FAILED_CHANGED_POST_SEAL:{index}")
for relative, expected in PROTECTED_SHA.items():
    require(sha256(REPO / relative) == expected, f"PROTECTED_CHANGED:{relative}")

rename_noreplace(STAGING, FINAL)
final_resolved = FINAL.resolve(strict=True)
require(final_resolved == FINAL, "FINAL_RESOLUTION")
require(stat.S_IMODE(FINAL.lstat().st_mode) == 0o555, "FINAL_ROOT_MODE")

final_files, final_dirs, final_links, final_other = scan(FINAL)
require(len(final_files) == 14, "FINAL_FILE_COUNT")
require(len(final_dirs) == 1, "FINAL_DIR_COUNT")
require(final_links == 0 and final_other == 0, "FINAL_SPECIAL")

print(
    "RESULT=PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
    "PACKET_R2_HUMAN_REVIEW_RESULT_REGISTERED_AND_SEALED_NO_EXECUTION"
)
print(f"EVIDENCE_ROOT={FINAL_REL}")
print("SOURCE_R2_EVIDENCE_FILE_COUNT=20")
print("SOURCE_R2_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("SOURCE_R2_PACKET_MANIFEST_ENTRY_COUNT=17")
print("SOURCE_R2_EVIDENCE_MANIFEST_ENTRY_COUNT=19")
print("SOURCE_R2_EVIDENCE_REVALIDATION=PASS")
print("SOURCE_R2_EVIDENCE_UNCHANGED=true")
print("HUMAN_REVIEW_RESULT=PASS")
print("COMBINED_READONLY_REVIEW_RESULT=PASS")
print("REVIEWER_TARGET_LAYOUT_SCHEMA_ASSUMPTION_CONFIRMED=true")
print("INITIAL_TARGET_LAYOUT_ASSERTION_WAS_PACKET_DEFECT=false")
print("TARGET_LAYOUT_SCHEMA_CORRECTION_READONLY=PASS")
print("TARGET_LAYOUT_EXACT_TOP_LEVEL_SCHEMA=PASS")
print("TARGET_LAYOUT_PACKET_MANIFEST_BINDING=PASS")
print("TARGET_LAYOUT_EVIDENCE_MANIFEST_BINDING=PASS")
print("TARGET_LAYOUT_FIXED_SHA_REVALIDATION=PASS")
print("CANDIDATE_SOURCE_FILE_COUNT=245")
print("CANDIDATE_SOURCE_DIRECTORY_COUNT_EXCLUDING_ROOT=46")
print(f"CANDIDATE_SOURCE_TREE_IDENTITY_SHA256={candidate_tree_sha}")
print("CANDIDATE_SOURCE_IDENTITY_REVALIDATION=PASS")
print("CANONICAL_RUNNER_SOURCE_BINDING=PASS")
print("RUNNER_CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("THREE_LEVEL_RUNNER_MANIFEST_BINDING=PASS")
print("FAILED_STAGING_COUNT=2")
print("FAILED_STAGING_UNCHANGED=true")
print("PROTECTED_SHA_COUNT=6")
print("PROTECTED_SHA_REVALIDATION=PASS")
print("TARGET_STATE_INSPECTED_DURING_PREPARATION=false")
print("TARGET_STATE_VERIFICATION_DEFERRED=true")
print("NEW_EVIDENCE_FILE_COUNT=14")
print("NEW_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("NEW_PACKET_MANIFEST_ENTRY_COUNT=11")
print("NEW_EVIDENCE_MANIFEST_ENTRY_COUNT=13")
print("SEALED_FILE_MODE=0444")
print("SEALED_DIRECTORY_MODE=0555")
print("SEAL_VALIDATION=PASS")
print("FINAL_PROMOTION=RENAMEAT2_RENAME_NOREPLACE")
print("HUMAN_REVIEW_RESULT_REGISTRATION_AND_SEAL_ONLY=true")
print("ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false")
print("SUDOERS_INSTALLATION_ALLOWED=false")
print("CORRECTED_WRAPPER_EXECUTION_ALLOWED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false")
print("FINAL_EXECUTION_APPROVAL_ISSUED=false")
print("FINAL_EXECUTION_TOKEN_CONSUMED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE=HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
    "PACKET_R2_HUMAN_REVIEW_RESULT_SEAL_READONLY"
)
print(f"REVIEW_RESULT_SHA={sha256(FINAL / 'review-result.json')}")
print(f"PACKET_MANIFEST_SHA={sha256(FINAL / 'packet-snapshot/packet-manifest.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(FINAL / 'evidence-manifest.txt')}")
PY

echo "SCRIPT_EXIT_CODE=0"
