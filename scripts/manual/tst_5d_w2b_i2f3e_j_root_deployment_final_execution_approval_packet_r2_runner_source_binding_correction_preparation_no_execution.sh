#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

SEALED_SOURCE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-human-review-result-registration-and-seal-20260726T094913Z-537139"
CANDIDATE_SOURCE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-negative-test-mutation-indentation-correction-preparation-20260726T072647Z-534604"

SEALED_SOURCE_ROOT="${REPO_ROOT}/${SEALED_SOURCE_REL}"
CANDIDATE_SOURCE_ROOT="${REPO_ROOT}/${CANDIDATE_SOURCE_REL}"
FAILED_STAGING_1_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/.i2f3e-j-root-deployment-final-execution-approval-packet-preparation-and-seal-staging-20260726T102320Z-537656"
FAILED_STAGING_1_ROOT="${REPO_ROOT}/${FAILED_STAGING_1_REL}"
FAILED_STAGING_2_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/.i2f3e-j-root-deployment-final-execution-approval-packet-r1-staging-lifecycle-correction-preparation-and-seal-staging-20260726T110354Z-538346"
FAILED_STAGING_2_ROOT="${REPO_ROOT}/${FAILED_STAGING_2_REL}"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
FINAL_PREFIX="i2f3e-j-root-deployment-final-execution-approval-packet-r2-runner-source-binding-correction-preparation-and-seal"
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
test -d "$SEALED_SOURCE_ROOT"
test -d "$CANDIDATE_SOURCE_ROOT"
test -d "$FAILED_STAGING_1_ROOT"
test ! -L "$FAILED_STAGING_1_ROOT"
test -d "$FAILED_STAGING_2_ROOT"
test ! -L "$FAILED_STAGING_2_ROOT"
test ! -e "$FINAL_ROOT"
test ! -L "$FINAL_ROOT"
test ! -e "$STAGING_ROOT"
test ! -L "$STAGING_ROOT"

cd "$REPO_ROOT"

printf '\n===== SEALED HUMAN REVIEW RESULT FIXED SHA REVIEW =====\n'
sha256sum -c <<SHAS
d4ddedce041a93a46eef3c9f66a572c5885630c8225f6d29eb437036f6538437  ${SEALED_SOURCE_ROOT}/review-result.json
790b18408c1821eddadfa8795b1d96267f26c8983b5479ea42bd250492cdaebb  ${SEALED_SOURCE_ROOT}/packet-snapshot/packet-manifest.json
6c6201d3543f33cca72ef16e0df1773449e60fd1c58add6d0cb4d1dde03f1747  ${SEALED_SOURCE_ROOT}/evidence-manifest.txt
SHAS

printf '\n===== R1-R2-R2 CANDIDATE SOURCE FIXED SHA REVIEW =====\n'
sha256sum -c <<SHAS
8db446727c08e063661fb7272d390b20bcb31280f08a945fd464f148c38b370d  ${CANDIDATE_SOURCE_ROOT}/result.json
e3d74993dbafac43853e09391c35f3c591dd7dbb36f1b66b72921baa25dd9e57  ${CANDIDATE_SOURCE_ROOT}/packet-snapshot/packet-manifest.json
fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577  ${CANDIDATE_SOURCE_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
78aa0778009d37ad1a6ec75c0ff62c2e07b42bf0dc80e32e8ce78f15e3b126f7  ${CANDIDATE_SOURCE_ROOT}/evidence-manifest.txt
0d712c6e12dc0b98213ca1995e4f22d1e9088ab5ffc31a97a497d60ba769fa53  ${CANDIDATE_SOURCE_ROOT}/packet-snapshot/candidate-artifacts/root_deployment_execution_once_r1.py
efdabbe83c61a2618128f5518a726f007062bba0e91959a01eed1f380d4b2d74  ${CANDIDATE_SOURCE_ROOT}/packet-snapshot/candidate-artifacts/validate_root_deployment_execution_packet_r1.py
6dad37c21c35921587e1839002a2435ebab4f4b88399f6035a9dcd9569156ca7  ${CANDIDATE_SOURCE_ROOT}/packet-snapshot/candidate-artifacts/test_root_deployment_execution_packet_r1_negative.py
SHAS


PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$SEALED_SOURCE_ROOT" \
  "$CANDIDATE_SOURCE_ROOT" \
  "$FAILED_STAGING_1_ROOT" \
  "$FAILED_STAGING_2_ROOT" \
  "$STAGING_ROOT" \
  "$FINAL_ROOT" \
  "$FINAL_REL" <<'PY'

from __future__ import annotations

import ast
import base64
import ctypes
import difflib
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

REPO = Path(sys.argv[1]).resolve(strict=True)
SEALED_SOURCE = Path(sys.argv[2]).resolve(strict=True)
CANDIDATE_SOURCE = Path(sys.argv[3]).resolve(strict=True)
FAILED_STAGING_1 = Path(sys.argv[4]).resolve(strict=True)
FAILED_STAGING_2 = Path(sys.argv[5]).resolve(strict=True)
FAILED_STAGINGS = (FAILED_STAGING_1, FAILED_STAGING_2)
STAGING_ARGUMENT = Path(sys.argv[6])
FINAL_ARGUMENT = Path(sys.argv[7])
FINAL_REL = sys.argv[8]

PHASE = (
    "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-"
    "FINAL-EXECUTION-APPROVAL-PACKET-R2-RUNNER-SOURCE-BINDING-CORRECTION"
)

APPROVAL_TEXT = base64.b64decode("QVBQUk9WRV8zRV9KX1JPT1RfREVQTE9ZTUVOVF9GSU5BTF9FWEVDVVRJT05fQVBQUk9WQUxfUEFDS0VUX1IyX1JVTk5FUl9TT1VSQ0VfQklORElOR19DT1JSRUNUSU9OX1BSRVBBUkFUSU9OX05PX0VYRUNVVElPTgoK5YmN5o+Q57WQ5p6c77yaCkJJTkRJTkdfUkVDT1JEX1NDSEVNQV9SRUFET05MWV9SRVZJRVc9UEFTUwpCSU5ESU5HX1JFQ09SRF9TQ0hFTUFfUkVWSUVXX0VYSVRfQ09ERT0wCkFVVEhPUklUQVRJVkVfTUFOSUZFU1RfTUFQUz1QQVNTCkJJTkRJTkdfUkVDT1JEX01BTklGRVNUX1JFR0lTVFJBVElPTj1QQVNTCkFDVFVBTF9CSU5ESU5HX1JFQ09SRF9TQ0hFTUFfRFVNUD1QQVNTClJVTk5FUl9GSUxFTkFNRV9SRUNPUkRfQ09WRVJBR0U9UEFTUwpUSFJFRV9MRVZFTF9SVU5ORVJfTUFOSUZFU1RfQklORElORz1QQVNTClNPVVJDRV9CSU5ESU5HX0NPTlRSQUNUX0xJVEVSQUxfUEFUSF9SRVFVSVJFRD1mYWxzZQpJTklUSUFMX1JFVklFV0VSX0VSUk9SX1dBU19QQUNLRVRfREVGRUNUPWZhbHNlClJFVklFV0VSX0JJTkRJTkdfUkVDT1JEX1NDSEVNQV9BU1NVTVBUSU9OX0NPUlJFQ1RFRD10cnVlCgpDYW5vbmljYWwgUnVubmVyIFNvdXJjZe+8mgpleGNoYW5nZS9yZXZpZXdfZXZpZGVuY2Uvc2xhY2tfd29ya2VyX3JlbGVhc2VfcmViaW5kaW5nLwpzbGFjay13b3JrZXItQ0FORElEQVRFLU5PVC1BUFBST1ZFRC0wMWJhODgwOWYxMzMvCnRzdC01ZC13MmItaTJlLWJhc2VsaW5lLWFic29ycHRpb24tcmVyZXZpZXctMjAyNjA3MjVUMTQxNjMyLwppMmYzZS1qLXJvb3QtZGVwbG95bWVudC1leGVjdXRpb24tcGFja2V0LXIxLXIyLXIyLQpuZWdhdGl2ZS10ZXN0LW11dGF0aW9uLWluZGVudGF0aW9uLWNvcnJlY3Rpb24tcHJlcGFyYXRpb24tCjIwMjYwNzI2VDA3MjY0N1otNTM0NjA0LwpwYWNrZXQtc25hcHNob3QvcjEtcjEtdmFsaWRhdG9yLXRhcmdldC8KcGFja2V0LXNuYXBzaG90L3NvdXJjZS1wYXJ0aWFsLWV2aWRlbmNlLXNuYXBzaG90LwpwYWNrZXQtc25hcHNob3QvZGVwbG95bWVudC1pbnB1dC1zbmFwc2hvdC9ydW5uZXItY2FuZGlkYXRlCgpFeGVjdXRpb24gQ2FuZGlkYXRlIFJvb3TvvJoKZXhjaGFuZ2UvcmV2aWV3X2V2aWRlbmNlL3NsYWNrX3dvcmtlcl9yZWxlYXNlX3JlYmluZGluZy8Kc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzLwp0c3QtNWQtdzJiLWkyZS1iYXNlbGluZS1hYnNvcnB0aW9uLXJlcmV2aWV3LTIwMjYwNzI1VDE0MTYzMi8KaTJmM2Utai1yb290LWRlcGxveW1lbnQtZXhlY3V0aW9uLXBhY2tldC1yMS1yMi1yMi0KbmVnYXRpdmUtdGVzdC1tdXRhdGlvbi1pbmRlbnRhdGlvbi1jb3JyZWN0aW9uLXByZXBhcmF0aW9uLQoyMDI2MDcyNlQwNzI2NDdaLTUzNDYwNC8KcGFja2V0LXNuYXBzaG90L3IxLXIxLXZhbGlkYXRvci10YXJnZXQvCnBhY2tldC1zbmFwc2hvdC9jYW5kaWRhdGUtYXJ0aWZhY3RzCgpDQU5ESURBVEVfU09VUkNFX1RSRUVfSURFTlRJVFlfU0hBMjU2PQpmNTU4MjNiZGZmZDkxOThlMDVlMWI3MjdiNzhmNDdlZDhhMzk1YjM3ZjZmOWVlN2VlNTU3ZDBjMzVjYWM2NjZlCkVYRUNVVElPTl9DQU5ESURBVEVfTUFOSUZFU1RfU0hBPQpmYjExNTk5NDMwNjM4OTgyNjg4OWNmOTE2NjZmNjVlMjM3NjBkNjU3NDNkYTUyOGMxM2NhYjA3ZWI1OGE2NTc3ClJVTk5FUl9DQU5ESURBVEVfTUFOSUZFU1RfU0hBPQowNjc3YTlhOTQ3OWUyMDlhNmUxZWUzMGZkY2QwNzk5NmI2NzE3Mzc4NTBiMTdlNzliOTc5ODc1NzhhNzNlYzdmCkNPUlJFQ1RFRF9XUkFQUEVSX1NIQT0KMGQ3MTJjNmUxMmRjMGI5ODIxM2NhMTk5NWU0ZjIyZDFlOTA4OGFiNWZmYzMxYTk3YTQ5N2Q2MGJhNzY5ZmE1MwpSMV9SMV9WQUxJREFUT1JfU0hBPQplZmRhYmJlODNjNjFhMjYxODEyOGY1NTE4YTcyNmYwMDcwNjJiYmEwZTkxOTU5YTAxZWVkMWYzODBkNGIyZDc0CkNPUlJFQ1RFRF9ORUdBVElWRV9URVNUX1NIQT0KNmRhZDM3YzIxYzM1OTIxNTg3ZTE4MzkwMDJhMjQzNWViYWI0ZjRiODgzOTlmNjAzNWE5ZGNkOTU2OTE1NmNhNwpTT1VSQ0VfQklORElOR19DT05UUkFDVF9TSEE9CjQwMTBhZmUyYmY2ZTVjODY1NGIzNGQyMWNiZDY4MTcyNzBlNTFlNmExNjdlYjc5MmFiMmI4NzE3YzY1M2IzZmEKUEFSVElBTF9TT1VSQ0VfSU5WRU5UT1JZX1NIQT0KYmFlMTg0MjEyYTFiNzJiNjc2MDJlYjExY2MyNDRhZGUzMGM2YmE0MjgwZjEzMzIzMWZiYTUyNjM2MDY0YzIxMwoKRVhFQ1VUSU9OX0VWSURFTkNFX0ZJTEVfQ09VTlQ9NjUKRVhFQ1VUSU9OX0VWSURFTkNFX01BTklGRVNUX0VOVFJZX0NPVU5UPTY0CkVYRUNVVElPTl9QQUNLRVRfRklMRV9DT1VOVD02MwpFWEVDVVRJT05fUEFDS0VUX01BTklGRVNUX0VOVFJZX0NPVU5UPTYyClJVTk5FUl9DQU5ESURBVEVfRklMRV9DT1VOVD03ClJVTk5FUl9DQU5ESURBVEVfTUFOSUZFU1RfRU5UUllfQ09VTlQ9NgoKUjJfUlVOTkVSX1NPVVJDRV9CSU5ESU5HX0NPUlJFQ1RJT05fT05MWT10cnVlCkZJTkFMX0VYRUNVVElPTl9BUFBST1ZBTF9QQUNLRVRfUFJFUEFSQVRJT05fT05MWT10cnVlCkZJTkFMX0VYRUNVVElPTl9BUFBST1ZBTF9JU1NVRUQ9ZmFsc2UKRklOQUxfRVhFQ1VUSU9OX1RPS0VOX0NPTlNVTUVEPWZhbHNlClJPT1RfREVQTE9ZTUVOVF9FWEVDVVRJT05fQUxMT1dFRD1mYWxzZQpTVURPRVJTX0lOU1RBTExBVElPTl9BTExPV0VEPWZhbHNlCkNPUlJFQ1RFRF9XUkFQUEVSX0VYRUNVVElPTl9BTExPV0VEPWZhbHNlCkFQUFJPVkFMX0JJTkRJTkdfQ1JFQVRFRD1mYWxzZQpPTkVfU0hPVF9ERVBMT1lNRU5UX0dVQVJEX0NSRUFURUQ9ZmFsc2UKVEFSR0VUX1NUQVRFX0lOU1BFQ1RJT05fQUxMT1dFRD1mYWxzZQpXUklURVJfRlJFRVpFX0VYRUNVVElPTj1IT0xEClBST0RVQ1RJT05fUkVMRUFTRV9ERUNJU0lPTj1IT0xEClJFTEVBU0VfU1RBVFVTPUNBTkRJREFURV9OT1RfQVBQUk9WRUQK", validate=True)
MANUAL_TEXT = base64.b64decode("IyAzRS1KIFJvb3QgRGVwbG95bWVudCBGaW5hbCBFeGVjdXRpb24gQXBwcm92YWwgUGFja2V0CgojIyBTY29wZQoKVGhpcyBQYWNrZXQgcHJlcGFyZXMgdGhlIG1hdGVyaWFscyBuZWVkZWQgZm9yIGEgbGF0ZXIsIHNlcGFyYXRlIGh1bWFuIGRlY2lzaW9uLgpJdCBkb2VzIG5vdCBpc3N1ZSB0aGUgZmluYWwgZXhlY3V0aW9uIGFwcHJvdmFsIGFuZCBkb2VzIG5vdCBleGVjdXRlIFJvb3QKRGVwbG95bWVudC4KClRoZSBQYWNrZXQgcmV2YWxpZGF0ZXMgdGhlIHNlYWxlZCBIdW1hbiBSZXZpZXcgUmVzdWx0IEV2aWRlbmNlIGFuZCB0aGUKUjEtUjItUjIgQ2FuZGlkYXRlIGJvdW5kIGJ5IHRoYXQgRXZpZGVuY2UuIFRoZSBleGVjdXRhYmxlIEV2aWRlbmNlIGlzIHRoZQpjb21wbGV0ZSBuZXN0ZWQgYHBhY2tldC1zbmFwc2hvdC9yMS1yMS12YWxpZGF0b3ItdGFyZ2V0YCwgYmVjYXVzZSBpdCBob2xkcwpgY2FuZGlkYXRlLWFydGlmYWN0c2AgYW5kIGBkZXBsb3ltZW50LWlucHV0LXNuYXBzaG90YCBzaWRlIGJ5IHNpZGUuIFRoZQpvdXRlciBhbmQgbmVzdGVkIENhbmRpZGF0ZSBhcnRpZmFjdCBzZXRzIG11c3QgYmUgYnl0ZS1mb3ItYnl0ZSBpZGVudGljYWwuCkl0IHJlY29yZHMgdGhlIGV4YWN0IENhbmRpZGF0ZQppZGVudGl0aWVzLCBwcm90ZWN0ZWQgUHJvZHVjdGlvbiBTSEEtMjU2IHZhbHVlcywgdGFyZ2V0IGxheW91dCwgcHJlZmxpZ2h0CnJlcXVpcmVtZW50cywgcm9sbGJhY2sgYW5kIHN0b3AgY29uZGl0aW9ucywgZnV0dXJlIGNvbW1hbmQgYXJndiwgb3BlcmF0b3IKY2hlY2tsaXN0LCBhbmQgYSBub24tdmFsaWQgYXBwcm92YWwtdG9rZW4gdGVtcGxhdGUuCgojIyBObyB0YXJnZXQtc3RhdGUgcHJvYmUgaW4gdGhpcyBwaGFzZQoKVGhlIGZvbGxvd2luZyBhcmUgcmVjb3JkZWQgYXMgcmVxdWlyZWQgZnV0dXJlIHByZWNvbmRpdGlvbnMgb25seToKCi0gYC9vcHQvYWktbWVkaWEtb3MvM2UtamAgbXVzdCBiZSBwYXRoLWVudHJ5IGFic2VudDsKLSBgL2V0Yy9zdWRvZXJzLmQvYWktbWVkaWEtb3MtM2Utai1yb290LWhlbHBlcmAgbXVzdCBiZSBwYXRoLWVudHJ5IGFic2VudDsKLSBgL3Zhci9saWIvYWktbWVkaWEtb3MvZ3VhcmRzLzNlLWotcm9vdC1kZXBsb3ltZW50LXYxLmd1YXJkYCBtdXN0IGJlCiAgcGF0aC1lbnRyeSBhYnNlbnQ7Ci0gdGhlIHRyYW5zYWN0aW9uLWRlcml2ZWQgc3RhZ2luZyBwYXRoIG11c3QgYmUgcGF0aC1lbnRyeSBhYnNlbnQuCgpUaGlzIHByZXBhcmF0aW9uIGRvZXMgbm90IGluc3BlY3QsIGNyZWF0ZSwgbW9kaWZ5LCBvciByZW1vdmUgdGhvc2UgcGF0aHMuClRoZSBmdXR1cmUgZml4ZWQgd3JhcHBlciBwZXJmb3JtcyBgb3MucGF0aC5sZXhpc3RzYCBhbmQgYGxzdGF0YC1iYXNlZApwYXJlbnQtY2hhaW4gY2hlY2tzIGltbWVkaWF0ZWx5IGJlZm9yZSBtdXRhdGlvbi4KCiMjIEZpbmFsIGFwcHJvdmFsIGJvdW5kYXJ5CgpUaGUgZnV0dXJlIHRva2VuIGlkZW50aWZpZXIgcmVtYWluczoKCmBBUFBST1ZFXzNFX0pfUk9PVF9ERVBMT1lNRU5UX0VYRUNVVElPTl9PTkNFYAoKSXRzIFNIQS0yNTYgaXM6CgpgMGViYzZkOGRkNDY1ZWQzMGQwN2Q5NWRkNDhhYmYxZWUxOTQ4NjNlZmI5OTI3Y2ExNzRmYTlkMzNlMmEwZWI0YWAKClRoZSB0b2tlbiBzaG93biBpbiB0aGlzIFBhY2tldCBpcyBhIHRlbXBsYXRlIHJlZmVyZW5jZSBvbmx5LiBJdCBpcyBub3QgaXNzdWVkLAppcyBub3QgY29uc3VtYWJsZSwgYW5kIGlzIGludmFsaWQgd2l0aG91dCBhIGxhdGVyIGV4cGxpY2l0IGh1bWFuIGFwcHJvdmFsIGFuZAphIHNlcGFyYXRlbHkgY3JlYXRlZCByb290LW93bmVkLCBtb2RlIGAwNDAwYCwgdW5leHBpcmVkIGFwcHJvdmFsIGJpbmRpbmcuCgojIyBQcm9kdWN0aW9uIHN0YXRlCgotIFJvb3QgRGVwbG95bWVudCBleGVjdXRpb24gYWxsb3dlZCBub3c6IGBmYWxzZWAKLSBTdWRvZXJzIGluc3RhbGxhdGlvbiBhbGxvd2VkIG5vdzogYGZhbHNlYAotIEFwcHJvdmFsIGJpbmRpbmcgY3JlYXRlZDogYGZhbHNlYAotIE9uZS1zaG90IGd1YXJkIGNyZWF0ZWQ6IGBmYWxzZWAKLSBXcml0ZXIgZnJlZXplIGV4ZWN1dGlvbjogYEhPTERgCi0gUHJvZHVjdGlvbiByZWxlYXNlIGRlY2lzaW9uOiBgSE9MRGAKLSBSZWxlYXNlIHN0YXR1czogYENBTkRJREFURV9OT1RfQVBQUk9WRURgCgojIyBSMSBzdGFnaW5nIGxpZmVjeWNsZSBjb3JyZWN0aW9uCgpUaGUgb3JpZ2luYWwgcHJlcGFyYXRpb24gc3RvcHBlZCBiZWZvcmUgUGFja2V0IGNyZWF0aW9uIGJlY2F1c2UgdGhlIHNoZWxsCmNyZWF0ZWQgdGhlIHN0YWdpbmcgZGlyZWN0b3J5IGFuZCB0aGUgZW1iZWRkZWQgUHl0aG9uIGltbWVkaWF0ZWx5IHJlcXVpcmVkCnRoYXQgc2FtZSBwYXRoIHRvIGJlIGFic2VudC4KClRoZSBmYWlsZWQgc3RhZ2luZyBwYXRoIGlzIHJldGFpbmVkIHVuY2hhbmdlZCBhcyBhbiBlbXB0eSBwYXJ0aWFsLWZhaWx1cmUKcmVjb3JkOgoKYGV4Y2hhbmdlL3Jldmlld19ldmlkZW5jZS9zbGFja193b3JrZXJfcmVsZWFzZV9yZWJpbmRpbmcvc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzL3RzdC01ZC13MmItaTJlLWJhc2VsaW5lLWFic29ycHRpb24tcmVyZXZpZXctMjAyNjA3MjVUMTQxNjMyLy5pMmYzZS1qLXJvb3QtZGVwbG95bWVudC1maW5hbC1leGVjdXRpb24tYXBwcm92YWwtcGFja2V0LXByZXBhcmF0aW9uLWFuZC1zZWFsLXN0YWdpbmctMjAyNjA3MjZUMTAyMzIwWi01Mzc2NTZgCgpJdHMgYXBwcm92ZWQgZml4ZWQgbWV0YWRhdGEgaXM6CgotIG1vZGU6IGAwNzUwYAotIHVpZDogYDEwMDFgCi0gZ2lkOiBgMTAwMWAKLSBtdGltZV9uczogYDE3ODUwNjE0MDA1ODU2MTA2OTNgCi0gZmlsZXM6IGAwYAotIGNoaWxkIGRpcmVjdG9yaWVzOiBgMGAKLSBzeW1saW5rczogYDBgCi0gbm9ucmVndWxhciBwYXRoczogYDBgCgpSMSByZW1vdmVzIHRoZSBzaGVsbC1zaWRlIHN0YWdpbmcgYG1rZGlyYC4gVGhlIGVtYmVkZGVkIFB5dGhvbiByZXNvbHZlcyBvbmx5CnRoZSBleGlzdGluZyBwYXJlbnQgZGlyZWN0b3J5LCBjaGVja3MgYm90aCBzdGFnaW5nIGFuZCBmaW5hbCBwYXRoIGVudHJpZXMgd2l0aApgb3MucGF0aC5sZXhpc3RzYCwgY3JlYXRlcyBzdGFnaW5nIG9uY2Ugd2l0aCBgb3MubWtkaXIoLi4uLCAwbzc1MClgLCBhbmQgb25seQp0aGVuIHJlc29sdmVzIHRoZSBuZXcgc3RhZ2luZyBwYXRoIHN0cmljdGx5LgoKVGhlIGZhaWxlZCBzdGFnaW5nIGRpcmVjdG9yeSBpcyByZWFkIGFuZCByZWdpc3RlcmVkIGJ1dCBpcyBuZXZlciBjaGFuZ2VkLApyZW1vdmVkLCBzZWFsZWQsIHJlbmFtZWQsIGNobW9kZGVkLCBvciBjaG93bmVkLgoKIyMgUjIgY2Fub25pY2FsIFJ1bm5lciBzb3VyY2UgYmluZGluZyBjb3JyZWN0aW9uCgpSMiBwcmVzZXJ2ZXMgdGhlIFIxIFB5dGhvbi1vbmx5IHN0YWdpbmcgbGlmZWN5Y2xlIGFuZCBjaGFuZ2VzIG9ubHkgdGhlIFJ1bm5lcgpwYXlsb2FkIHNvdXJjZSBiaW5kaW5nLgoKQ2Fub25pY2FsIFJ1bm5lciBzb3VyY2UsIHJlbGF0aXZlIHRvIHRoZSBSMS1SMi1SMiBDYW5kaWRhdGUgc291cmNlIEV2aWRlbmNlOgoKYHBhY2tldC1zbmFwc2hvdC9yMS1yMS12YWxpZGF0b3ItdGFyZ2V0L3BhY2tldC1zbmFwc2hvdC9zb3VyY2UtcGFydGlhbC1ldmlkZW5jZS1zbmFwc2hvdC9wYWNrZXQtc25hcHNob3QvZGVwbG95bWVudC1pbnB1dC1zbmFwc2hvdC9ydW5uZXItY2FuZGlkYXRlYAoKRXhlY3V0aW9uIENhbmRpZGF0ZSByb290LCByZWxhdGl2ZSB0byB0aGUgc2FtZSBzb3VyY2UgRXZpZGVuY2U6CgpgcGFja2V0LXNuYXBzaG90L3IxLXIxLXZhbGlkYXRvci10YXJnZXQvcGFja2V0LXNuYXBzaG90L2NhbmRpZGF0ZS1hcnRpZmFjdHNgCgpUaGUgUnVubmVyIHNvdXJjZSBpcyB2YWxpZGF0ZWQgdGhyb3VnaCB0aHJlZSBhdXRob3JpdGF0aXZlIGxheWVyczoKCjEuIEV4ZWN1dGlvbiBFdmlkZW5jZSBtYW5pZmVzdDogNjQgZW50cmllcy4KMi4gRXhlY3V0aW9uIFBhY2tldCBtYW5pZmVzdDogNjIgZW50cmllcy4KMy4gUnVubmVyIENhbmRpZGF0ZSBtYW5pZmVzdDogNiBwYXlsb2FkIGVudHJpZXMuCgpUaGUgaW50ZXJtZWRpYXRlIGBzb3VyY2UtcGFydGlhbC1ldmlkZW5jZS1zbmFwc2hvdGAgZGlyZWN0b3J5IGlzIGEgcmVjdXJzaXZlCmZpbGUgY29udGFpbmVyLiBJdCBpcyBub3QgcmVxdWlyZWQgdG8gaGF2ZSBpdHMgb3duIEV2aWRlbmNlIG1hbmlmZXN0IG9yIGRpcmVjdApQYWNrZXQgbWFuaWZlc3QuCgpUaGUgdHdvIGZhaWxlZCBzdGFnaW5nIGRpcmVjdG9yaWVzIHJlbWFpbiBpbW11dGFibGUgZW1wdHkgcGFydGlhbC1mYWlsdXJlCnJlY29yZHMuIFIyIHJlYWRzIGFuZCByZWdpc3RlcnMgdGhlaXIgZXhhY3QgaWRlbnRpdGllcyBidXQgZG9lcyBub3QgZGVsZXRlLAptb2RpZnksIGNobW9kLCBjaG93biwgc2VhbCwgb3IgcmVuYW1lIHRoZW0uCgpSZXZpZXdlciBjb3JyZWN0aW9ucyByZWNvcmRlZCBieSBSMjoKCi0gcGFydGlhbCBTbmFwc2hvdCByb290IHdhcyBpbmNvcnJlY3RseSBhc3N1bWVkIHRvIGJlIGEgY29tcGxldGUgRXZpZGVuY2Ugcm9vdDsKLSBhbiBleHRyYSBpbnRlcm1lZGlhdGUgUGFja2V0IG1hbmlmZXN0IHdhcyBpbmNvcnJlY3RseSBhc3N1bWVkOwotIGV2ZXJ5IGF1eGlsaWFyeSBiaW5kaW5nIHJlY29yZCB3YXMgaW5jb3JyZWN0bHkgcmVxdWlyZWQgdG8gY29udGFpbiBsaXRlcmFsCiAgcGF0aCB0b2tlbnMuCgpUaGVzZSB3ZXJlIHJldmlld2VyIGFzc3VtcHRpb25zLCBub3QgUGFja2V0IGRlZmVjdHMuCg==", validate=True)
PACKET_CONTRACT_BYTES = base64.b64decode(
    "ewogICJhcHByb3ZhbF9iaW5kaW5nX2NyZWF0ZWQiOiBmYWxzZSwKICAiY2FuZGlkYXRlX3NvdXJjZV9ldmlkZW5jZV9yb290IjogImV4Y2hhbmdlL3Jldmlld19ldmlkZW5jZS9zbGFja193b3JrZXJfcmVsZWFzZV9yZWJpbmRpbmcvc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzL3RzdC01ZC13MmItaTJlLWJhc2VsaW5lLWFic29ycHRpb24tcmVyZXZpZXctMjAyNjA3MjVUMTQxNjMyL2kyZjNlLWotcm9vdC1kZXBsb3ltZW50LWV4ZWN1dGlvbi1wYWNrZXQtcjEtcjItcjItbmVnYXRpdmUtdGVzdC1tdXRhdGlvbi1pbmRlbnRhdGlvbi1jb3JyZWN0aW9uLXByZXBhcmF0aW9uLTIwMjYwNzI2VDA3MjY0N1otNTM0NjA0IiwKICAiY2Fub25pY2FsX3J1bm5lcl9zb3VyY2VfcmVsYXRpdmVfcGF0aCI6ICJwYWNrZXQtc25hcHNob3QvcjEtcjEtdmFsaWRhdG9yLXRhcmdldC9wYWNrZXQtc25hcHNob3Qvc291cmNlLXBhcnRpYWwtZXZpZGVuY2Utc25hcHNob3QvcGFja2V0LXNuYXBzaG90L2RlcGxveW1lbnQtaW5wdXQtc25hcHNob3QvcnVubmVyLWNhbmRpZGF0ZSIsCiAgImNvcnJlY3RlZF93cmFwcGVyX2V4ZWN1dGlvbl9hbGxvd2VkIjogZmFsc2UsCiAgImV4ZWN1dGlvbl9jYW5kaWRhdGVfcmVsYXRpdmVfcGF0aCI6ICJwYWNrZXQtc25hcHNob3QvcjEtcjEtdmFsaWRhdG9yLXRhcmdldC9wYWNrZXQtc25hcHNob3QvY2FuZGlkYXRlLWFydGlmYWN0cyIsCiAgImV4ZWN1dGlvbl9ldmlkZW5jZV9tYW5pZmVzdF9lbnRyeV9jb3VudCI6IDY0LAogICJleGVjdXRpb25fcGFja2V0X21hbmlmZXN0X2VudHJ5X2NvdW50IjogNjIsCiAgImZhaWxlZF9zY3JpcHRfZXhpdF9jb2RlIjogMSwKICAiZmFpbGVkX3N0YWdpbmdfY291bnQiOiAyLAogICJmYWlsZWRfc3RhZ2luZ19kaXJlY3RvcnlfY291bnRfZXhjbHVkaW5nX3Jvb3QiOiAwLAogICJmYWlsZWRfc3RhZ2luZ19maWxlX2NvdW50IjogMCwKICAiZmFpbGVkX3N0YWdpbmdfZ2lkIjogMTAwMSwKICAiZmFpbGVkX3N0YWdpbmdfbW9kZSI6ICIwNzUwIiwKICAiZmFpbGVkX3N0YWdpbmdfbXRpbWVfbnMiOiAxNzg1MDYxNDAwNTg1NjEwNjkzLAogICJmYWlsZWRfc3RhZ2luZ19tdXRhdGlvbl9hbGxvd2VkIjogZmFsc2UsCiAgImZhaWxlZF9zdGFnaW5nX25vbnJlZ3VsYXJfY291bnQiOiAwLAogICJmYWlsZWRfc3RhZ2luZ19yZWxhdGl2ZV9wYXRoIjogImV4Y2hhbmdlL3Jldmlld19ldmlkZW5jZS9zbGFja193b3JrZXJfcmVsZWFzZV9yZWJpbmRpbmcvc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzL3RzdC01ZC13MmItaTJlLWJhc2VsaW5lLWFic29ycHRpb24tcmVyZXZpZXctMjAyNjA3MjVUMTQxNjMyLy5pMmYzZS1qLXJvb3QtZGVwbG95bWVudC1maW5hbC1leGVjdXRpb24tYXBwcm92YWwtcGFja2V0LXByZXBhcmF0aW9uLWFuZC1zZWFsLXN0YWdpbmctMjAyNjA3MjZUMTAyMzIwWi01Mzc2NTYiLAogICJmYWlsZWRfc3RhZ2luZ19yZWxhdGl2ZV9wYXRocyI6IFsKICAgICJleGNoYW5nZS9yZXZpZXdfZXZpZGVuY2Uvc2xhY2tfd29ya2VyX3JlbGVhc2VfcmViaW5kaW5nL3NsYWNrLXdvcmtlci1DQU5ESURBVEUtTk9ULUFQUFJPVkVELTAxYmE4ODA5ZjEzMy90c3QtNWQtdzJiLWkyZS1iYXNlbGluZS1hYnNvcnB0aW9uLXJlcmV2aWV3LTIwMjYwNzI1VDE0MTYzMi8uaTJmM2Utai1yb290LWRlcGxveW1lbnQtZmluYWwtZXhlY3V0aW9uLWFwcHJvdmFsLXBhY2tldC1wcmVwYXJhdGlvbi1hbmQtc2VhbC1zdGFnaW5nLTIwMjYwNzI2VDEwMjMyMFotNTM3NjU2IiwKICAgICJleGNoYW5nZS9yZXZpZXdfZXZpZGVuY2Uvc2xhY2tfd29ya2VyX3JlbGVhc2VfcmViaW5kaW5nL3NsYWNrLXdvcmtlci1DQU5ESURBVEUtTk9ULUFQUFJPVkVELTAxYmE4ODA5ZjEzMy90c3QtNWQtdzJiLWkyZS1iYXNlbGluZS1hYnNvcnB0aW9uLXJlcmV2aWV3LTIwMjYwNzI1VDE0MTYzMi8uaTJmM2Utai1yb290LWRlcGxveW1lbnQtZmluYWwtZXhlY3V0aW9uLWFwcHJvdmFsLXBhY2tldC1yMS1zdGFnaW5nLWxpZmVjeWNsZS1jb3JyZWN0aW9uLXByZXBhcmF0aW9uLWFuZC1zZWFsLXN0YWdpbmctMjAyNjA3MjZUMTEwMzU0Wi01MzgzNDYiCiAgXSwKICAiZmFpbGVkX3N0YWdpbmdfc3ltbGlua19jb3VudCI6IDAsCiAgImZhaWxlZF9zdGFnaW5nX3VpZCI6IDEwMDEsCiAgImZhaWx1cmVfY2xhc3MiOiAiU1RBR0lOR19MSUZFQ1lDTEVfQ09OVFJBQ1RfQ09OVFJBRElDVElPTiIsCiAgImZhaWx1cmVfbWFya2VyIjogIlNUQUdJTkdfUEFUSF9FTlRSWV9FWElTVFMiLAogICJmaW5hbF9leGVjdXRpb25fYXBwcm92YWxfaXNzdWVkIjogZmFsc2UsCiAgImZpbmFsX2V4ZWN1dGlvbl90b2tlbl9jb25zdW1lZCI6IGZhbHNlLAogICJmaW5hbF9wcm9tb3Rpb24iOiAicmVuYW1lYXQyKFJFTkFNRV9OT1JFUExBQ0UpIiwKICAib25lX3Nob3RfZGVwbG95bWVudF9ndWFyZF9jcmVhdGVkIjogZmFsc2UsCiAgIm9wZXJhdGlvbiI6ICJGSU5BTF9FWEVDVVRJT05fQVBQUk9WQUxfUEFDS0VUX1IyX1JVTk5FUl9TT1VSQ0VfQklORElOR19DT1JSRUNUSU9OX1BSRVBBUkFUSU9OX09OTFkiLAogICJwaGFzZSI6ICJUU1QtNUQtVzJCLUkyRi0zRS1KLVJPT1QtREVQTE9ZTUVOVC1GSU5BTC1FWEVDVVRJT04tQVBQUk9WQUwtUEFDS0VULVIyLVJVTk5FUi1TT1VSQ0UtQklORElORy1DT1JSRUNUSU9OIiwKICAicHJvZHVjdGlvbl9yZWxlYXNlX2RlY2lzaW9uIjogIkhPTEQiLAogICJweXRob25faXNfc29sZV9zdGFnaW5nX2NyZWF0b3IiOiB0cnVlLAogICJyMV9zdGFnaW5nX2xpZmVjeWNsZV9jb3JyZWN0aW9uX29ubHkiOiBmYWxzZSwKICAicjJfcnVubmVyX3NvdXJjZV9iaW5kaW5nX2NvcnJlY3Rpb25fb25seSI6IHRydWUsCiAgInJlbGVhc2Vfc3RhdHVzIjogIkNBTkRJREFURV9OT1RfQVBQUk9WRUQiLAogICJyZXZpZXdlcl9hc3N1bXB0aW9uX2NvcnJlY3Rpb25zX3JlZ2lzdGVyZWQiOiB0cnVlLAogICJyb290X2RlcGxveW1lbnRfZXhlY3V0aW9uX2FsbG93ZWQiOiBmYWxzZSwKICAicnVubmVyX2NhbmRpZGF0ZV9tYW5pZmVzdF9lbnRyeV9jb3VudCI6IDYsCiAgInNjaGVtYV92ZXJzaW9uIjogIjEuMCIsCiAgInNlYWxlZF9kaXJlY3RvcnlfbW9kZSI6ICIwNTU1IiwKICAic2VhbGVkX2ZpbGVfbW9kZSI6ICIwNDQ0IiwKICAic2VhbGVkX3Jldmlld19ldmlkZW5jZV9yb290IjogImV4Y2hhbmdlL3Jldmlld19ldmlkZW5jZS9zbGFja193b3JrZXJfcmVsZWFzZV9yZWJpbmRpbmcvc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzL3RzdC01ZC13MmItaTJlLWJhc2VsaW5lLWFic29ycHRpb24tcmVyZXZpZXctMjAyNjA3MjVUMTQxNjMyL2kyZjNlLWotcm9vdC1kZXBsb3ltZW50LWV4ZWN1dGlvbi1wYWNrZXQtcjEtcjItcjItaHVtYW4tcmV2aWV3LXJlc3VsdC1yZWdpc3RyYXRpb24tYW5kLXNlYWwtMjAyNjA3MjZUMDk0OTEzWi01MzcxMzkiLAogICJzaGVsbF9zdGFnaW5nX21rZGlyX2FsbG93ZWQiOiBmYWxzZSwKICAic291cmNlX2JpbmRpbmdfY29udHJhY3RfbGl0ZXJhbF9wYXRoX3JlcXVpcmVkIjogZmFsc2UsCiAgInN0YWdpbmdfYW5kX2ZpbmFsX2xleGlzdHNfcmVxdWlyZWRfYmVmb3JlX2NyZWF0ZSI6IHRydWUsCiAgInN0YWdpbmdfYXJndW1lbnRfc3RyaWN0X3Jlc29sdmVfYmVmb3JlX2NyZWF0ZSI6IGZhbHNlLAogICJzdGFnaW5nX3BhcmVudF9zdHJpY3RfcmVzb2x2ZV9iZWZvcmVfY3JlYXRlIjogdHJ1ZSwKICAic3Vkb2Vyc19pbnN0YWxsYXRpb25fYWxsb3dlZCI6IGZhbHNlLAogICJ3cml0ZXJfZnJlZXplX2V4ZWN1dGlvbiI6ICJIT0xEIgp9Cg==",
    validate=True,
)

SEALED_EXPECTED_FILES = {
    "review-result.json",
    "evidence-manifest.txt",
    "packet-snapshot/human-approval-verbatim.txt",
    "packet-snapshot/human-review-result-verbatim.txt",
    "packet-snapshot/operation-manual.md",
    "packet-snapshot/review-contract.json",
    "packet-snapshot/reviewer-ast-scope-correction.json",
    "packet-snapshot/seal-contract.json",
    "packet-snapshot/source-inventory.json",
    "packet-snapshot/source-verification.json",
    "packet-snapshot/packet-manifest.json",
}

SEALED_EXPECTED_DIRECTORIES = {"packet-snapshot"}

SEALED_FIXED_SHA = {
    "review-result.json":
        "d4ddedce041a93a46eef3c9f66a572c5885630c8225f6d29eb437036f6538437",
    "packet-snapshot/packet-manifest.json":
        "790b18408c1821eddadfa8795b1d96267f26c8983b5479ea42bd250492cdaebb",
    "evidence-manifest.txt":
        "6c6201d3543f33cca72ef16e0df1773449e60fd1c58add6d0cb4d1dde03f1747",
}

CANDIDATE_SOURCE_FIXED_SHA = {
    "result.json":
        "8db446727c08e063661fb7272d390b20bcb31280f08a945fd464f148c38b370d",
    "packet-snapshot/packet-manifest.json":
        "e3d74993dbafac43853e09391c35f3c591dd7dbb36f1b66b72921baa25dd9e57",
    "packet-snapshot/candidate-artifacts/candidate-manifest.json":
        "fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577",
    "evidence-manifest.txt":
        "78aa0778009d37ad1a6ec75c0ff62c2e07b42bf0dc80e32e8ce78f15e3b126f7",
}

CANDIDATE_SOURCE_TREE_SHA = (
    "f55823bdffd9198e05e1b727b78f47ed"
    "8a395b37f6f9ee7ee557d0c35cac666e"
)

CRITICAL_CANDIDATE_SHA = {
    "candidate-manifest.json":
        "fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577",
    "root_deployment_execution_once_r1.py":
        "0d712c6e12dc0b98213ca1995e4f22d1e9088ab5ffc31a97a497d60ba769fa53",
    "validate_root_deployment_execution_packet_r1.py":
        "efdabbe83c61a2618128f5518a726f007062bba0e91959a01eed1f380d4b2d74",
    "test_root_deployment_execution_packet_r1_negative.py":
        "6dad37c21c35921587e1839002a2435ebab4f4b88399f6035a9dcd9569156ca7",
}

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

APPROVAL_TOKEN_LITERAL = "APPROVE_3E_J_ROOT_DEPLOYMENT_EXECUTION_ONCE"
APPROVAL_TOKEN_SHA = (
    "0ebc6d8dd465ed30d07d95dd48abf1ee"
    "194863efb9927ca174fa9d33e2a0eb4a"
)

APPROVAL_BINDING_PATH = (
    "/var/lib/ai-media-os/approvals/3e-j-root-deployment-v1.json"
)
GUARD_PATH = (
    "/var/lib/ai-media-os/guards/3e-j-root-deployment-v1.guard"
)
DEPLOYMENT_PARENT = "/opt/ai-media-os"
DEPLOYMENT_ROOT = "/opt/ai-media-os/3e-j"
SUDOERS_TARGET = "/etc/sudoers.d/ai-media-os-3e-j-root-helper"
VISUDO_PATH = "/usr/sbin/visudo"

TARGET_DIRECTORIES = [
    {"path": "/opt/ai-media-os/3e-j", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/bin", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/libexec", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/review", "owner": "root", "group": "root", "mode": "0755"},
    {"path": "/opt/ai-media-os/3e-j/docs", "owner": "root", "group": "root", "mode": "0755"},
]

TARGET_FILES = [
    {
        "source_relative":
            "packet-snapshot/deployment-input-snapshot/runner-candidate/"
            "one_shot_writer_freeze_backup_restart_runner.py",
        "source_sha256":
            RUNNER_PAYLOAD_SHA["one_shot_writer_freeze_backup_restart_runner.py"],
        "target":
            "/opt/ai-media-os/3e-j/bin/"
            "one_shot_writer_freeze_backup_restart_runner.py",
        "owner": "root",
        "group": "root",
        "mode": "0755",
    },
    {
        "source_relative":
            "packet-snapshot/deployment-input-snapshot/runner-candidate/"
            "root_fd_metadata_helper.py",
        "source_sha256":
            RUNNER_PAYLOAD_SHA["root_fd_metadata_helper.py"],
        "target": "/opt/ai-media-os/3e-j/libexec/root_fd_metadata_helper.py",
        "owner": "root",
        "group": "root",
        "mode": "0755",
    },
    {
        "source_relative":
            "packet-snapshot/deployment-input-snapshot/runner-candidate/"
            "runner-policy.json",
        "source_sha256": RUNNER_PAYLOAD_SHA["runner-policy.json"],
        "target": "/opt/ai-media-os/3e-j/runner-policy.json",
        "owner": "root",
        "group": "root",
        "mode": "0644",
    },
    {
        "source_relative":
            "packet-snapshot/deployment-input-snapshot/runner-candidate/"
            "validate_3e_j_runner_packet.py",
        "source_sha256":
            RUNNER_PAYLOAD_SHA["validate_3e_j_runner_packet.py"],
        "target":
            "/opt/ai-media-os/3e-j/review/validate_3e_j_runner_packet.py",
        "owner": "root",
        "group": "root",
        "mode": "0755",
    },
    {
        "source_relative":
            "packet-snapshot/deployment-input-snapshot/runner-candidate/"
            "test_3e_j_runner_negative.py",
        "source_sha256":
            RUNNER_PAYLOAD_SHA["test_3e_j_runner_negative.py"],
        "target":
            "/opt/ai-media-os/3e-j/review/test_3e_j_runner_negative.py",
        "owner": "root",
        "group": "root",
        "mode": "0644",
    },
    {
        "source_relative":
            "packet-snapshot/deployment-input-snapshot/runner-candidate/"
            "3e_j_operation_manual.md",
        "source_sha256": RUNNER_PAYLOAD_SHA["3e_j_operation_manual.md"],
        "target": "/opt/ai-media-os/3e-j/docs/3e_j_operation_manual.md",
        "owner": "root",
        "group": "root",
        "mode": "0644",
    },
]

SUDOERS_CONTENT = (
    "Cmnd_Alias AI_MEDIA_OS_3E_J_ROOT_HELPER = "
    "/opt/ai-media-os/3e-j/libexec/root_fd_metadata_helper.py "
    "self-check --db-path "
    "/home/deploy/ai_media_os/data/database/ebook_affiliate.db, "
    "/opt/ai-media-os/3e-j/libexec/root_fd_metadata_helper.py "
    "inspect --db-path "
    "/home/deploy/ai_media_os/data/database/ebook_affiliate.db "
    "--require-zero\n"
    "deploy ALL=(root) NOPASSWD:NOSETENV: "
    "AI_MEDIA_OS_3E_J_ROOT_HELPER\n"
)
SUDOERS_CONTENT_SHA = (
    "d7d20b84f5f2b03d9a75683853a17958"
    "a2e70c93cc0b0c5e150d89511b8ee3b2"
)

SOURCE_ROOT_DEPLOYMENT_PACKET_RESULT_SHA = (
    "07951222582d6dda8ae07bcef6cd920d"
    "b0d7cbdf22b20b39e48593cf716f9e6f"
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


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
    files, directories, symlinks, nonregular = scan(root)
    require(symlinks == 0 and nonregular == 0, f"SPECIAL_PATH:{root}")
    result: dict[str, tuple[object, ...]] = {}
    for relative in sorted(directories):
        item = (root / relative).lstat()
        result[relative + "/"] = (
            "DIR",
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        result[relative] = (
            sha256(path),
            item.st_size,
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
        )
    return result


def tree_identity(
    root: Path,
) -> tuple[str, list[dict[str, object]]]:
    files, _, symlinks, nonregular = scan(root)
    require(symlinks == 0 and nonregular == 0, "TREE_SPECIAL_PATH")
    entries: list[dict[str, object]] = []
    lines: list[str] = []
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        digest = sha256(path)
        mode = f"{stat.S_IMODE(item.st_mode):04o}"
        entry = {
            "relative_path": relative,
            "size_bytes": item.st_size,
            "mode": mode,
            "uid": item.st_uid,
            "gid": item.st_gid,
            "sha256": digest,
        }
        entries.append(entry)
        lines.append(
            f"{digest}  {item.st_size}  {mode}  "
            f"{item.st_uid}  {item.st_gid}  {relative}"
        )
    digest = hashlib.sha256(
        ("\n".join(lines) + "\n").encode("utf-8")
    ).hexdigest()
    return digest, entries


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_NOT_OBJECT:{path}")
    return value


def manifest_entries(value: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("packet_files", "files", "artifacts"):
        candidate = value.get(key)
        if isinstance(candidate, list):
            require(
                all(isinstance(entry, dict) for entry in candidate),
                f"MANIFEST_ENTRY_TYPE:{key}",
            )
            return candidate
    raise AssertionError("MANIFEST_ENTRY_LIST_NOT_FOUND")


def parse_string_assignment(tree: ast.Module, name: str) -> str:
    matches: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, Path):
            value = str(value)
        require(isinstance(value, str), f"ASSIGNMENT_NOT_STRING:{name}")
        matches.append(value)
    require(len(matches) == 1, f"ASSIGNMENT_COUNT:{name}:{len(matches)}")
    return matches[0]


def parse_path_assignment(tree: ast.Module, name: str) -> str:
    matches: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        require(isinstance(node.value, ast.Call), f"PATH_CALL:{name}")
        require(
            isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Path",
            f"PATH_CONSTRUCTOR:{name}",
        )
        require(len(node.value.args) == 1, f"PATH_ARGUMENT_COUNT:{name}")
        value = ast.literal_eval(node.value.args[0])
        require(isinstance(value, str), f"PATH_VALUE:{name}")
        matches.append(value)
    require(len(matches) == 1, f"PATH_ASSIGNMENT_COUNT:{name}")
    return matches[0]


def parse_int_assignment(tree: ast.Module, name: str) -> int:
    values: list[int] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        require(isinstance(value, int), f"INT_VALUE:{name}")
        values.append(value)
    require(len(values) == 1, f"INT_ASSIGNMENT_COUNT:{name}")
    return values[0]


def rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    require(function is not None, "RENAMEAT2_UNAVAILABLE")
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    AT_FDCWD = -100
    RENAME_NOREPLACE = 1
    result = function(
        AT_FDCWD,
        os.fsencode(source),
        AT_FDCWD,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


require(SEALED_SOURCE.is_relative_to(REPO), "SEALED_SOURCE_OUTSIDE_REPO")
require(CANDIDATE_SOURCE.is_relative_to(REPO), "CANDIDATE_SOURCE_OUTSIDE_REPO")
for index, failed_root in enumerate(FAILED_STAGINGS, start=1):
    require(
        failed_root.is_relative_to(REPO),
        f"FAILED_STAGING_OUTSIDE_REPO:{index}",
    )

staging_parent = STAGING_ARGUMENT.parent.resolve(strict=True)
final_parent = FINAL_ARGUMENT.parent.resolve(strict=True)
require(staging_parent == final_parent, "FINAL_PARENT_MISMATCH")
require(staging_parent.is_relative_to(REPO), "STAGING_PARENT_OUTSIDE_REPO")
require(not os.path.lexists(FINAL_ARGUMENT), "FINAL_PATH_ENTRY_EXISTS")
require(not os.path.lexists(STAGING_ARGUMENT), "STAGING_PATH_ENTRY_EXISTS")

expected_failed_staging = (
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
failed_staging_identities_before: list[tuple[int, int, int, int]] = []

for index, (failed_root, expected) in enumerate(
    zip(FAILED_STAGINGS, expected_failed_staging),
    start=1,
):
    item = failed_root.lstat()
    require(
        stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode),
        f"FAILED_STAGING_TYPE:{index}",
    )
    require(
        stat.S_IMODE(item.st_mode) == expected["mode"],
        f"FAILED_STAGING_MODE:{index}",
    )
    require(item.st_uid == expected["uid"], f"FAILED_STAGING_UID:{index}")
    require(item.st_gid == expected["gid"], f"FAILED_STAGING_GID:{index}")
    require(
        item.st_mtime_ns == expected["mtime_ns"],
        f"FAILED_STAGING_MTIME_NS:{index}",
    )
    files, directories, links, other = scan(failed_root)
    require(len(files) == 0, f"FAILED_STAGING_FILE_COUNT:{index}")
    require(len(directories) == 0, f"FAILED_STAGING_DIR_COUNT:{index}")
    require(links == 0, f"FAILED_STAGING_LINK_COUNT:{index}")
    require(other == 0, f"FAILED_STAGING_OTHER_COUNT:{index}")
    failed_staging_identities_before.append(
        (
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
            item.st_mtime_ns,
        )
    )

# Python remains the sole staging creator in R2.
os.mkdir(STAGING_ARGUMENT, 0o750)
STAGING = STAGING_ARGUMENT.resolve(strict=True)
FINAL = FINAL_ARGUMENT
PACKET = STAGING / "packet-snapshot"
require(STAGING.parent == staging_parent, "STAGING_PARENT_AFTER_CREATE")
require(stat.S_IMODE(STAGING.lstat().st_mode) == 0o750,
        "STAGING_CREATED_MODE")

sealed_identity_before = identity(SEALED_SOURCE)
candidate_identity_before = identity(CANDIDATE_SOURCE)

# Sealed Human Review Result Evidence.
sealed_files, sealed_dirs, sealed_links, sealed_other = scan(SEALED_SOURCE)
require(sealed_files == SEALED_EXPECTED_FILES, "SEALED_EXACT_FILE_SET")
require(sealed_dirs == SEALED_EXPECTED_DIRECTORIES, "SEALED_EXACT_DIR_SET")
require(sealed_links == 0 and sealed_other == 0, "SEALED_SPECIAL_PATH")
require(stat.S_IMODE(SEALED_SOURCE.lstat().st_mode) == 0o555, "SEALED_ROOT_MODE")
for relative in sealed_files:
    require(
        stat.S_IMODE((SEALED_SOURCE / relative).lstat().st_mode) == 0o444,
        f"SEALED_FILE_MODE:{relative}",
    )
for relative in sealed_dirs:
    require(
        stat.S_IMODE((SEALED_SOURCE / relative).lstat().st_mode) == 0o555,
        f"SEALED_DIR_MODE:{relative}",
    )
for relative, expected in SEALED_FIXED_SHA.items():
    require(
        sha256(SEALED_SOURCE / relative) == expected,
        f"SEALED_FIXED_SHA:{relative}",
    )

sealed_evidence_map: dict[str, str] = {}
for raw in (SEALED_SOURCE / "evidence-manifest.txt").read_text(
    encoding="utf-8"
).splitlines():
    digest, relative = raw.split("  ", 1)
    require(relative not in sealed_evidence_map, f"SEALED_MANIFEST_DUP:{relative}")
    sealed_evidence_map[relative] = digest
require(len(sealed_evidence_map) == 10, "SEALED_MANIFEST_COUNT")
require(
    set(sealed_evidence_map) == sealed_files - {"evidence-manifest.txt"},
    "SEALED_MANIFEST_SET",
)
for relative, expected in sealed_evidence_map.items():
    require(
        sha256(SEALED_SOURCE / relative) == expected,
        f"SEALED_MANIFEST_SHA:{relative}",
    )

sealed_packet_root = SEALED_SOURCE / "packet-snapshot"
sealed_packet_manifest = json_object(
    sealed_packet_root / "packet-manifest.json"
)
sealed_packet_entries = manifest_entries(sealed_packet_manifest)
require(len(sealed_packet_entries) == 8, "SEALED_PACKET_ENTRY_COUNT")
sealed_packet_files, _, sealed_packet_links, sealed_packet_other = scan(
    sealed_packet_root
)
require(sealed_packet_links == 0 and sealed_packet_other == 0,
        "SEALED_PACKET_SPECIAL")
sealed_packet_map: dict[str, dict[str, Any]] = {}
for entry in sealed_packet_entries:
    name = entry.get("name")
    require(isinstance(name, str), "SEALED_PACKET_ENTRY_NAME")
    require(name not in sealed_packet_map, f"SEALED_PACKET_DUP:{name}")
    sealed_packet_map[name] = entry
require(
    set(sealed_packet_map)
    == sealed_packet_files - {"packet-manifest.json"},
    "SEALED_PACKET_SET",
)
for relative, entry in sealed_packet_map.items():
    path = sealed_packet_root / relative
    require(entry.get("sha256") == sha256(path),
            f"SEALED_PACKET_SHA:{relative}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"SEALED_PACKET_SIZE:{relative}")

sealed_review_result = json_object(SEALED_SOURCE / "review-result.json")
require(sealed_review_result.get("human_review_result") == "PASS",
        "SEALED_HUMAN_REVIEW")
require(sealed_review_result.get("sealed") is True, "SEALED_RESULT_SEALED")
require(
    sealed_review_result.get("source_tree_identity_sha256")
    == CANDIDATE_SOURCE_TREE_SHA,
    "SEALED_SOURCE_TREE_BINDING",
)
require(
    sealed_review_result.get("source_evidence_root")
    == CANDIDATE_SOURCE.relative_to(REPO).as_posix(),
    "SEALED_CANDIDATE_SOURCE_PATH",
)
require(
    sealed_review_result.get("root_deployment_execution_allowed") is False,
    "SEALED_ROOT_EXECUTION_FLAG",
)
require(
    sealed_review_result.get("production_release_decision") == "HOLD",
    "SEALED_RELEASE_DECISION",
)

source_inventory_record = json_object(
    sealed_packet_root / "source-inventory.json"
)
inventory_entries = source_inventory_record.get("files")
require(isinstance(inventory_entries, list), "SEALED_SOURCE_INVENTORY_LIST")
require(len(inventory_entries) == 245, "SEALED_SOURCE_INVENTORY_COUNT")
require(
    source_inventory_record.get("source_tree_identity_sha256")
    == CANDIDATE_SOURCE_TREE_SHA,
    "SEALED_SOURCE_INVENTORY_TREE_SHA",
)

# Candidate source Evidence exact identity.
candidate_files, candidate_dirs, candidate_links, candidate_other = scan(
    CANDIDATE_SOURCE
)
require(len(candidate_files) == 245, "CANDIDATE_SOURCE_FILE_COUNT")
require(len(candidate_dirs) == 46, "CANDIDATE_SOURCE_DIR_COUNT")
require(candidate_links == 0 and candidate_other == 0,
        "CANDIDATE_SOURCE_SPECIAL")
candidate_tree_sha, candidate_tree_entries = tree_identity(CANDIDATE_SOURCE)
require(candidate_tree_sha == CANDIDATE_SOURCE_TREE_SHA,
        "CANDIDATE_SOURCE_TREE_SHA")
for relative, expected in CANDIDATE_SOURCE_FIXED_SHA.items():
    require(
        sha256(CANDIDATE_SOURCE / relative) == expected,
        f"CANDIDATE_SOURCE_FIXED_SHA:{relative}",
    )

record_map: dict[str, dict[str, Any]] = {}
for entry in inventory_entries:
    require(isinstance(entry, dict), "INVENTORY_ENTRY_OBJECT")
    relative = entry.get("relative_path")
    require(isinstance(relative, str), "INVENTORY_ENTRY_PATH")
    require(relative not in record_map, f"INVENTORY_DUP:{relative}")
    record_map[relative] = entry
actual_map = {
    str(entry["relative_path"]): entry
    for entry in candidate_tree_entries
}
require(set(record_map) == set(actual_map), "INVENTORY_ACTUAL_SET")
for relative, expected in record_map.items():
    actual = actual_map[relative]
    for field in ("size_bytes", "mode", "uid", "gid", "sha256"):
        require(
            actual.get(field) == expected.get(field),
            f"INVENTORY_ACTUAL_FIELD:{relative}:{field}",
        )

outer_candidate_root = (
    CANDIDATE_SOURCE
    / "packet-snapshot/candidate-artifacts"
)
execution_evidence_root = (
    CANDIDATE_SOURCE
    / "packet-snapshot/r1-r1-validator-target"
)
execution_packet_root = execution_evidence_root / "packet-snapshot"
candidate_root = execution_packet_root / "candidate-artifacts"
partial_snapshot_root = (
    execution_packet_root / "source-partial-evidence-snapshot"
)
runner_source = (
    partial_snapshot_root
    / "packet-snapshot/deployment-input-snapshot/runner-candidate"
)

# The nested validator target is the complete executable Evidence because it
# contains candidate-artifacts and deployment-input-snapshot side by side.
execution_files, execution_dirs, execution_links, execution_other = scan(
    execution_evidence_root
)
require(len(execution_files) == 65, "EXECUTION_EVIDENCE_FILE_COUNT")
require(len(execution_dirs) == 12, "EXECUTION_EVIDENCE_DIR_COUNT")
require(execution_links == 0 and execution_other == 0,
        "EXECUTION_EVIDENCE_SPECIAL")

execution_evidence_map: dict[str, str] = {}
for raw in (execution_evidence_root / "evidence-manifest.txt").read_text(
    encoding="utf-8"
).splitlines():
    digest, relative = raw.split("  ", 1)
    require(relative not in execution_evidence_map,
            f"EXECUTION_EVIDENCE_MANIFEST_DUP:{relative}")
    execution_evidence_map[relative] = digest
require(len(execution_evidence_map) == 64,
        "EXECUTION_EVIDENCE_MANIFEST_COUNT")
require(
    set(execution_evidence_map)
    == execution_files - {"evidence-manifest.txt"},
    "EXECUTION_EVIDENCE_MANIFEST_SET",
)
for relative, expected in execution_evidence_map.items():
    require(
        sha256(execution_evidence_root / relative) == expected,
        f"EXECUTION_EVIDENCE_MANIFEST_SHA:{relative}",
    )

execution_packet_files, execution_packet_dirs, execution_packet_links, execution_packet_other = scan(
    execution_packet_root
)
require(len(execution_packet_files) == 63, "EXECUTION_PACKET_FILE_COUNT")
require(len(execution_packet_dirs) == 11, "EXECUTION_PACKET_DIR_COUNT")
require(execution_packet_links == 0 and execution_packet_other == 0,
        "EXECUTION_PACKET_SPECIAL")
execution_packet_manifest = json_object(
    execution_packet_root / "packet-manifest.json"
)
execution_packet_entries = manifest_entries(execution_packet_manifest)
require(len(execution_packet_entries) == 62,
        "EXECUTION_PACKET_MANIFEST_COUNT")
execution_packet_map: dict[str, dict[str, Any]] = {}
for entry in execution_packet_entries:
    name = entry.get("name")
    require(isinstance(name, str), "EXECUTION_PACKET_ENTRY_NAME")
    require(name not in execution_packet_map,
            f"EXECUTION_PACKET_ENTRY_DUP:{name}")
    execution_packet_map[name] = entry
require(
    set(execution_packet_map)
    == execution_packet_files - {"packet-manifest.json"},
    "EXECUTION_PACKET_MANIFEST_SET",
)
for relative, entry in execution_packet_map.items():
    path = execution_packet_root / relative
    require(entry.get("sha256") == sha256(path),
            f"EXECUTION_PACKET_MANIFEST_SHA:{relative}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"EXECUTION_PACKET_MANIFEST_SIZE:{relative}")

candidate_artifact_files, candidate_artifact_dirs, cand_links, cand_other = scan(
    candidate_root
)
require(len(candidate_artifact_files) == 18, "CANDIDATE_ARTIFACT_COUNT")
require(len(candidate_artifact_dirs) == 0, "CANDIDATE_ARTIFACT_DIR_COUNT")
require(cand_links == 0 and cand_other == 0, "CANDIDATE_ARTIFACT_SPECIAL")
for name, expected in CRITICAL_CANDIDATE_SHA.items():
    require(sha256(candidate_root / name) == expected,
            f"CRITICAL_CANDIDATE_SHA:{name}")

candidate_manifest = json_object(candidate_root / "candidate-manifest.json")
candidate_entries = manifest_entries(candidate_manifest)
require(len(candidate_entries) == 17, "CANDIDATE_MANIFEST_ENTRY_COUNT")
candidate_manifest_map: dict[str, dict[str, Any]] = {}
for entry in candidate_entries:
    name = entry.get("name")
    require(isinstance(name, str), "CANDIDATE_MANIFEST_NAME")
    require(name not in candidate_manifest_map, f"CANDIDATE_MANIFEST_DUP:{name}")
    candidate_manifest_map[name] = entry
require(
    set(candidate_manifest_map)
    == candidate_artifact_files - {"candidate-manifest.json"},
    "CANDIDATE_MANIFEST_SET",
)
for relative, entry in candidate_manifest_map.items():
    path = candidate_root / relative
    require(entry.get("sha256") == sha256(path),
            f"CANDIDATE_MANIFEST_SHA:{relative}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"CANDIDATE_MANIFEST_SIZE:{relative}")

# The outer correction Candidate and the nested complete Execution Candidate
# must contain the same exact 18 candidate artifacts.
outer_candidate_files, outer_candidate_dirs, outer_links, outer_other = scan(
    outer_candidate_root
)
require(len(outer_candidate_files) == 18, "OUTER_CANDIDATE_FILE_COUNT")
require(len(outer_candidate_dirs) == 0, "OUTER_CANDIDATE_DIR_COUNT")
require(outer_links == 0 and outer_other == 0, "OUTER_CANDIDATE_SPECIAL")
require(outer_candidate_files == candidate_artifact_files,
        "OUTER_EXECUTION_CANDIDATE_SET")
for relative in sorted(candidate_artifact_files):
    require(
        sha256(outer_candidate_root / relative)
        == sha256(candidate_root / relative),
        f"OUTER_EXECUTION_CANDIDATE_SHA:{relative}",
    )
    require(
        (outer_candidate_root / relative).stat().st_size
        == (candidate_root / relative).stat().st_size,
        f"OUTER_EXECUTION_CANDIDATE_SIZE:{relative}",
    )

# Runner payload source and target-layout identity.
RUNNER_CANDIDATE_MANIFEST_SHA = (
    "0677a9a9479e209a6e1ee30fdcd07996"
    "b671737850b17e79b97987578a73ec7f"
)
SOURCE_BINDING_CONTRACT_SHA = (
    "4010afe2bf6e5c8654b34d21cbd68172"
    "70e51e6a167eb792ab2b8717c653b3fa"
)
PARTIAL_SOURCE_INVENTORY_SHA = (
    "bae184212a1b72b67602eb11cc244ade"
    "30c6ba4280f133231fba52636064c213"
)

require(
    not os.path.lexists(partial_snapshot_root / "evidence-manifest.txt"),
    "PARTIAL_SNAPSHOT_UNEXPECTED_EVIDENCE_MANIFEST",
)
require(
    not os.path.lexists(
        partial_snapshot_root / "packet-snapshot/packet-manifest.json"
    ),
    "PARTIAL_SNAPSHOT_UNEXPECTED_DIRECT_PACKET_MANIFEST",
)

runner_files, runner_dirs, runner_links, runner_other = scan(runner_source)
require(len(runner_files) == 7, "RUNNER_CANDIDATE_FILE_COUNT")
require(len(runner_dirs) == 0, "RUNNER_CANDIDATE_DIR_COUNT")
require(runner_links == 0 and runner_other == 0,
        "RUNNER_CANDIDATE_SPECIAL_PATH")

runner_manifest_path = runner_source / "candidate-manifest.json"
require(
    sha256(runner_manifest_path) == RUNNER_CANDIDATE_MANIFEST_SHA,
    "RUNNER_CANDIDATE_MANIFEST_FIXED_SHA",
)
runner_manifest = json_object(runner_manifest_path)
runner_entries = manifest_entries(runner_manifest)
require(len(runner_entries) == 6, "RUNNER_CANDIDATE_MANIFEST_ENTRY_COUNT")
runner_manifest_map: dict[str, dict[str, Any]] = {}
for entry in runner_entries:
    name = entry.get("name")
    require(isinstance(name, str), "RUNNER_CANDIDATE_ENTRY_NAME")
    require(name not in runner_manifest_map, f"RUNNER_CANDIDATE_DUP:{name}")
    runner_manifest_map[name] = entry
require(
    set(runner_manifest_map) == runner_files - {"candidate-manifest.json"},
    "RUNNER_CANDIDATE_MANIFEST_EXACT_SET",
)

for name, expected in RUNNER_PAYLOAD_SHA.items():
    path = runner_source / name
    require(path.is_file(), f"RUNNER_PAYLOAD_MISSING:{name}")
    require(sha256(path) == expected, f"RUNNER_PAYLOAD_SHA:{name}")
    entry = runner_manifest_map[name]
    require(entry.get("sha256") == expected,
            f"RUNNER_CANDIDATE_MANIFEST_SHA:{name}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"RUNNER_CANDIDATE_MANIFEST_SIZE:{name}")

    packet_relative = (
        "source-partial-evidence-snapshot/packet-snapshot/"
        f"deployment-input-snapshot/runner-candidate/{name}"
    )
    evidence_relative = f"packet-snapshot/{packet_relative}"
    require(
        packet_relative in execution_packet_map,
        f"THREE_LEVEL_PACKET_BINDING:{name}",
    )
    require(
        evidence_relative in execution_evidence_map,
        f"THREE_LEVEL_EVIDENCE_BINDING:{name}",
    )
    packet_entry = execution_packet_map[packet_relative]
    require(
        packet_entry.get("sha256") == expected,
        f"THREE_LEVEL_PACKET_SHA:{name}",
    )
    require(
        packet_entry.get("size_bytes") == path.stat().st_size,
        f"THREE_LEVEL_PACKET_SIZE:{name}",
    )
    require(
        execution_evidence_map[evidence_relative] == expected,
        f"THREE_LEVEL_EVIDENCE_SHA:{name}",
    )

source_binding_path = candidate_root / "source-binding-contract.json"
partial_inventory_path = candidate_root / "partial-source-inventory.json"
require(
    sha256(source_binding_path) == SOURCE_BINDING_CONTRACT_SHA,
    "SOURCE_BINDING_CONTRACT_FIXED_SHA",
)
require(
    sha256(partial_inventory_path) == PARTIAL_SOURCE_INVENTORY_SHA,
    "PARTIAL_SOURCE_INVENTORY_FIXED_SHA",
)

for record_name, record_path in (
    ("source-binding-contract.json", source_binding_path),
    ("partial-source-inventory.json", partial_inventory_path),
):
    packet_relative = f"candidate-artifacts/{record_name}"
    evidence_relative = f"packet-snapshot/{packet_relative}"
    require(
        packet_relative in execution_packet_map,
        f"BINDING_RECORD_PACKET_REGISTRATION:{record_name}",
    )
    require(
        evidence_relative in execution_evidence_map,
        f"BINDING_RECORD_EVIDENCE_REGISTRATION:{record_name}",
    )
    require(
        execution_packet_map[packet_relative].get("sha256")
        == sha256(record_path),
        f"BINDING_RECORD_PACKET_SHA:{record_name}",
    )
    require(
        execution_packet_map[packet_relative].get("size_bytes")
        == record_path.stat().st_size,
        f"BINDING_RECORD_PACKET_SIZE:{record_name}",
    )
    require(
        execution_evidence_map[evidence_relative] == sha256(record_path),
        f"BINDING_RECORD_EVIDENCE_SHA:{record_name}",
    )

source_binding_contract = json_object(source_binding_path)
require(
    source_binding_contract.get("runner_candidate", {}).get(
        "fixed_file_count"
    ) == 7,
    "SOURCE_BINDING_RUNNER_FILE_COUNT",
)
source_binding_runner_sha = (
    source_binding_contract.get("runner_candidate", {}).get("fixed_sha256")
)
require(
    isinstance(source_binding_runner_sha, dict),
    "SOURCE_BINDING_RUNNER_SHA_OBJECT",
)
require(
    source_binding_runner_sha.get("candidate-manifest.json")
    == RUNNER_CANDIDATE_MANIFEST_SHA,
    "SOURCE_BINDING_RUNNER_MANIFEST_SHA",
)
for name, expected in RUNNER_PAYLOAD_SHA.items():
    require(
        source_binding_runner_sha.get(name) == expected,
        f"SOURCE_BINDING_RUNNER_SHA:{name}",
    )

partial_inventory = json_object(partial_inventory_path)
partial_files = partial_inventory.get("files")
require(isinstance(partial_files, list), "PARTIAL_INVENTORY_FILES_LIST")
partial_map: dict[str, dict[str, Any]] = {}
for entry in partial_files:
    require(isinstance(entry, dict), "PARTIAL_INVENTORY_ENTRY_OBJECT")
    relative = entry.get("relative_path")
    require(isinstance(relative, str), "PARTIAL_INVENTORY_ENTRY_PATH")
    require(relative not in partial_map, f"PARTIAL_INVENTORY_DUP:{relative}")
    partial_map[relative] = entry
for name, expected in RUNNER_PAYLOAD_SHA.items():
    relative = (
        "packet-snapshot/deployment-input-snapshot/"
        f"runner-candidate/{name}"
    )
    require(relative in partial_map, f"PARTIAL_INVENTORY_RUNNER_PATH:{name}")
    require(
        partial_map[relative].get("sha256") == expected,
        f"PARTIAL_INVENTORY_RUNNER_SHA:{name}",
    )

sudoers_candidate = candidate_root / "ai-media-os-3e-j-root-helper.sudoers"
require(sha256(sudoers_candidate) == SUDOERS_CONTENT_SHA,
        "SUDOERS_CANDIDATE_SHA")
require(
    sudoers_candidate.read_text(encoding="utf-8") == SUDOERS_CONTENT,
    "SUDOERS_CANDIDATE_CONTENT",
)

# Wrapper static binding review. The wrapper is parsed but never executed.
wrapper = candidate_root / "root_deployment_execution_once_r1.py"
wrapper_source = wrapper.read_text(encoding="utf-8")
wrapper_tree = ast.parse(wrapper_source)
require(parse_path_assignment(wrapper_tree, "REPO_ROOT")
        == "/home/deploy/ai_media_os", "WRAPPER_REPO_ROOT")
require(parse_path_assignment(wrapper_tree, "APPROVAL_BINDING")
        == APPROVAL_BINDING_PATH, "WRAPPER_APPROVAL_BINDING")
require(parse_path_assignment(wrapper_tree, "GUARD_PATH")
        == GUARD_PATH, "WRAPPER_GUARD")
require(parse_path_assignment(wrapper_tree, "DEPLOYMENT_PARENT")
        == DEPLOYMENT_PARENT, "WRAPPER_DEPLOYMENT_PARENT")
require(parse_path_assignment(wrapper_tree, "DEPLOYMENT_ROOT")
        == DEPLOYMENT_ROOT, "WRAPPER_DEPLOYMENT_ROOT")
require(parse_path_assignment(wrapper_tree, "SUDOERS_TARGET")
        == SUDOERS_TARGET, "WRAPPER_SUDOERS_TARGET")
require(parse_path_assignment(wrapper_tree, "VISUDO")
        == VISUDO_PATH, "WRAPPER_VISUDO")
require(parse_string_assignment(wrapper_tree, "SOURCE_PACKET_RESULT_SHA")
        == SOURCE_ROOT_DEPLOYMENT_PACKET_RESULT_SHA,
        "WRAPPER_SOURCE_PACKET_RESULT_SHA")
require(parse_string_assignment(wrapper_tree, "APPROVAL_TOKEN_SHA")
        == APPROVAL_TOKEN_SHA, "WRAPPER_APPROVAL_TOKEN_SHA")
require(parse_int_assignment(wrapper_tree, "MAX_EXECUTION_ATTEMPTS") == 1,
        "WRAPPER_MAX_ATTEMPTS")
require(parse_int_assignment(wrapper_tree, "RENAME_NOREPLACE") == 1,
        "WRAPPER_RENAME_NOREPLACE")
require("os.path.lexists" in wrapper_source, "WRAPPER_LEXISTS")
require("renameat2" in wrapper_source, "WRAPPER_RENAMEAT2")
require("os.rename(" not in wrapper_source, "WRAPPER_OS_RENAME_FALLBACK")
require("parent_dev" in wrapper_source and "parent_ino" in wrapper_source,
        "WRAPPER_PARENT_IDENTITY_CAPTURE")
require("remove_created_parent_checked" in wrapper_source,
        "WRAPPER_CREATED_PARENT_ROLLBACK_FUNCTION")
require("expected_dev" in wrapper_source and "expected_ino" in wrapper_source,
        "WRAPPER_ROLLBACK_IDENTITY")
compile(wrapper_source, str(wrapper), "exec")

# Production protected identities. This is byte hashing only, not DB access.
for relative, expected in PROTECTED_SHA.items():
    path = REPO / relative
    require(path.is_file(), f"PROTECTED_MISSING:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

# Candidate binding data, including all 18 exact artifact identities.
candidate_binding_entries: list[dict[str, object]] = []
for relative in sorted(candidate_artifact_files):
    path = candidate_root / relative
    item = path.lstat()
    candidate_binding_entries.append({
        "name": relative,
        "sha256": sha256(path),
        "size_bytes": item.st_size,
        "mode": f"{stat.S_IMODE(item.st_mode):04o}",
        "uid": item.st_uid,
        "gid": item.st_gid,
    })

critical_sizes = {
    name: (candidate_root / name).stat().st_size
    for name in CRITICAL_CANDIDATE_SHA
}

execution_wrapper_path = (
    candidate_root / "root_deployment_execution_once_r1.py"
)
future_command_argv = [
    "/usr/bin/sudo",
    "--",
    "/usr/bin/python3",
    "-B",
    str(execution_wrapper_path),
]

target_layout = {
    "schema_version": "1.0",
    "phase": PHASE,
    "deployment_parent": DEPLOYMENT_PARENT,
    "deployment_root": DEPLOYMENT_ROOT,
    "directories": TARGET_DIRECTORIES,
    "files": TARGET_FILES,
    "sudoers_target": {
        "path": SUDOERS_TARGET,
        "owner": "root",
        "group": "root",
        "mode": "0440",
        "content_sha256": SUDOERS_CONTENT_SHA,
        "exclusive_create": True,
        "overwrite_allowed": False,
        "staged_visudo_validation_required": True,
    },
    "preparation_phase_target_write_allowed": False,
}

preflight_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "target_state_inspected_during_preparation": False,
    "target_state_verification_deferred_to_final_execution_preflight": True,
    "expected_future_prestate": {
        "deployment_root": {
            "path": DEPLOYMENT_ROOT,
            "required_state": "PATH_ENTRY_ABSENT",
            "dangling_symlink_counts_as_present": True,
            "verification_primitive": "os.path.lexists+lstat",
        },
        "sudoers_target": {
            "path": SUDOERS_TARGET,
            "required_state": "PATH_ENTRY_ABSENT",
            "dangling_symlink_counts_as_present": True,
            "verification_primitive": "os.path.lexists+lstat",
        },
        "one_shot_guard": {
            "path": GUARD_PATH,
            "required_state": "PATH_ENTRY_ABSENT",
            "dangling_symlink_counts_as_present": True,
            "verification_primitive": "os.path.lexists+lstat",
        },
        "transaction_stage": {
            "parent": DEPLOYMENT_PARENT,
            "prefix": ".3e-j-stage-",
            "required_state": "DERIVED_PATH_ENTRY_ABSENT",
            "dangling_symlink_counts_as_present": True,
            "verification_primitive": "os.path.lexists+lstat",
        },
    },
    "approval_binding": {
        "path": APPROVAL_BINDING_PATH,
        "future_required_state": "ROOT_OWNED_REGULAR_FILE",
        "owner": "root",
        "group": "root",
        "mode": "0400",
        "symlink_forbidden": True,
        "expiration_required": True,
        "max_execution_attempts": 1,
        "creation_allowed_current_phase": False,
    },
    "parent_chain_symlink_rejection_required": True,
    "protected_sha_revalidation_before_guard_required": True,
    "evidence_manifest_revalidation_before_guard_required": True,
    "renameat2_rename_noreplace_availability_before_guard_required": True,
    "visudo_required": True,
    "visudo_path": VISUDO_PATH,
    "production_release_must_remain_hold": True,
}

rollback_stop_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "rollback_scope": "CURRENT_TRANSACTION_CREATED_PATHS_ONLY",
    "automatic_retry_allowed": False,
    "max_execution_attempts": 1,
    "guard_removal_allowed": False,
    "existing_path_removal_allowed": False,
    "process_group_signal_allowed": False,
    "sigkill_allowed": False,
    "created_parent_contract": {
        "path": DEPLOYMENT_PARENT,
        "may_be_created_exclusively": True,
        "owner": "root",
        "group": "root",
        "mode": "0755",
        "capture_st_dev_and_st_ino_immediately": True,
        "rollback_removal_requires": [
            "created_by_current_transaction",
            "directory_type",
            "non_symlink",
            "root_owner",
            "root_group",
            "mode_0755",
            "captured_st_dev_match",
            "captured_st_ino_match",
            "directory_empty",
        ],
        "preexisting_parent_never_removed": True,
    },
    "deployment_root_rollback_requires": [
        "created_by_current_transaction",
        "captured_st_dev_match",
        "captured_st_ino_match",
        "exact_tree_identity_match",
    ],
    "stage_rollback_requires": [
        "created_by_current_transaction",
        "captured_st_dev_match",
        "captured_st_ino_match",
        "exact_tree_identity_match",
    ],
    "sudoers_rollback_requires": [
        "created_by_current_transaction",
        "captured_st_dev_match",
        "captured_st_ino_match",
        "exact_content_sha256_match",
    ],
    "stop_conditions_before_guard": [
        "sealed_review_evidence_identity_mismatch",
        "candidate_source_tree_identity_mismatch",
        "candidate_manifest_or_payload_mismatch",
        "production_protected_sha_mismatch",
        "approval_binding_missing_invalid_or_expired",
        "approval_token_sha_mismatch",
        "renameat2_or_RENAME_NOREPLACE_unavailable",
        "guard_path_entry_present_including_dangling_symlink",
        "deployment_root_path_entry_present_including_dangling_symlink",
        "sudoers_target_path_entry_present_including_dangling_symlink",
        "derived_stage_path_entry_present_including_dangling_symlink",
        "parent_chain_symlink_or_non_directory",
        "visudo_unavailable",
    ],
    "stop_conditions_after_guard": [
        "exclusive_parent_or_stage_creation_failure",
        "staged_payload_identity_or_mode_mismatch",
        "candidate_sudoers_visudo_failure",
        "promotion_no_replace_failure",
        "sudoers_exclusive_create_failure",
        "post_install_identity_mismatch",
        "rollback_identity_mismatch",
    ],
    "rollback_incomplete_action":
        "EMERGENCY_HOLD_AND_EXPLICIT_HUMAN_REVIEW",
    "success_terminal_state": "SUCCESS_HUMAN_REVIEW_REQUIRED",
    "production_release_after_success": "HOLD",
}

exact_command_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "current_phase_execution_allowed": False,
    "future_command_requires_separate_final_human_approval": True,
    "future_command_requires_valid_approval_binding": True,
    "cwd": "/home/deploy/ai_media_os",
    "argv": future_command_argv,
    "shell": False,
    "arbitrary_arguments_allowed": False,
    "python_bytecode_disabled_by_flag": True,
    "wrapper_path": str(execution_wrapper_path),
    "wrapper_sha256":
        CRITICAL_CANDIDATE_SHA["root_deployment_execution_once_r1.py"],
    "wrapper_size_bytes":
        critical_sizes["root_deployment_execution_once_r1.py"],
    "expected_terminal_states": [
        "NO_MUTATION_PREFLIGHT_FAILURE",
        "GUARD_CREATION_FAILED_HUMAN_REVIEW_REQUIRED",
        "GUARD_CREATED_NO_PRODUCTION_MUTATION",
        "PARENT_CREATED_STAGE_NOT_CREATED",
        "STAGING_CREATED_NOT_PROMOTED",
        "DEPLOYMENT_ROOT_PROMOTED_SUDOERS_NOT_INSTALLED",
        "SUDOERS_INSTALLED_POSTCHECK_FAILED",
        "ROLLBACK_COMPLETE_HUMAN_REVIEW_REQUIRED",
        "ROLLBACK_INCOMPLETE_EMERGENCY_HOLD",
        "SUCCESS_HUMAN_REVIEW_REQUIRED",
    ],
    "root_helper_executed_by_wrapper": False,
    "runner_executed_by_wrapper": False,
    "production_release_after_wrapper": "HOLD",
}

approval_binding_required_values = {
    "schema_version": "1.1",
    "template_only": True,
    "binding_created": False,
    "binding_path": APPROVAL_BINDING_PATH,
    "binding_owner": "root",
    "binding_group": "root",
    "binding_mode": "0400",
    "binding_symlink_forbidden": True,
    "approved": True,
    "approval_token_sha256": APPROVAL_TOKEN_SHA,
    "execution_packet_evidence_root":
        execution_evidence_root.relative_to(REPO).as_posix(),
    "execution_packet_evidence_manifest_sha256":
        sha256(execution_evidence_root / "evidence-manifest.txt"),
    "execution_packet_evidence_manifest_size_bytes":
        (execution_evidence_root / "evidence-manifest.txt").stat().st_size,
    "execution_packet_result_sha256":
        sha256(execution_evidence_root / "result.json"),
    "execution_packet_result_size_bytes":
        (execution_evidence_root / "result.json").stat().st_size,
    "execution_packet_packet_manifest_sha256":
        sha256(execution_packet_root / "packet-manifest.json"),
    "execution_packet_packet_manifest_size_bytes":
        (execution_packet_root / "packet-manifest.json").stat().st_size,
    "execution_packet_candidate_manifest_sha256":
        CRITICAL_CANDIDATE_SHA["candidate-manifest.json"],
    "execution_packet_candidate_manifest_size_bytes":
        critical_sizes["candidate-manifest.json"],
    "execution_wrapper_sha256":
        CRITICAL_CANDIDATE_SHA["root_deployment_execution_once_r1.py"],
    "execution_wrapper_size_bytes":
        critical_sizes["root_deployment_execution_once_r1.py"],
    "source_root_deployment_packet_result_sha256":
        SOURCE_ROOT_DEPLOYMENT_PACKET_RESULT_SHA,
    "approved_at_utc": "<REQUIRED_FUTURE_UTC_TIMESTAMP>",
    "expires_at_utc": "<REQUIRED_FUTURE_UTC_EXPIRATION>",
    "max_execution_attempts": 1,
    "requires_separate_human_approval": True,
    "current_packet_may_create_binding": False,
}

token_template = {
    "schema_version": "1.0",
    "template_only": True,
    "valid_approval": False,
    "final_execution_approval_issued": False,
    "final_execution_token_consumed": False,
    "required_future_token_identifier": APPROVAL_TOKEN_LITERAL,
    "required_future_token_sha256": APPROVAL_TOKEN_SHA,
    "literal_presence_does_not_issue_approval": True,
    "requires_new_explicit_human_message": True,
    "requires_valid_root_owned_approval_binding": True,
    "do_not_execute_from_this_template": True,
}

candidate_binding = {
    "schema_version": "1.0",
    "phase": PHASE,
    "candidate_source_evidence_root":
        CANDIDATE_SOURCE.relative_to(REPO).as_posix(),
    "execution_evidence_root":
        execution_evidence_root.relative_to(REPO).as_posix(),
    "execution_evidence_file_count": 65,
    "execution_evidence_directory_count_excluding_root": 12,
    "execution_packet_file_count": 63,
    "execution_packet_directory_count": 11,
    "execution_packet_manifest_entry_count": 62,
    "execution_evidence_manifest_entry_count": 64,
    "outer_and_execution_candidate_equivalent": True,
    "candidate_source_file_count": 245,
    "candidate_source_directory_count_excluding_root": 46,
    "candidate_source_tree_identity_sha256": candidate_tree_sha,
    "candidate_artifact_count": 18,
    "candidate_manifest_entry_count": 17,
    "critical_candidate_sha256": CRITICAL_CANDIDATE_SHA,
    "canonical_runner_source_relative_path":
        runner_source.relative_to(CANDIDATE_SOURCE).as_posix(),
    "runner_candidate_file_count": 7,
    "runner_candidate_manifest_entry_count": 6,
    "runner_candidate_manifest_sha256": RUNNER_CANDIDATE_MANIFEST_SHA,
    "runner_payload_sha256": RUNNER_PAYLOAD_SHA,
    "three_level_runner_manifest_binding": "PASS",
    "source_binding_contract_sha256": SOURCE_BINDING_CONTRACT_SHA,
    "partial_source_inventory_sha256": PARTIAL_SOURCE_INVENTORY_SHA,
    "source_binding_contract_literal_path_required": False,
    "sudoers_candidate_sha256": SUDOERS_CONTENT_SHA,
    "candidate_artifacts": candidate_binding_entries,
    "candidate_source_unchanged": True,
    "corrected_wrapper_executed": False,
}

protected_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "protected_sha256": PROTECTED_SHA,
    "revalidation_result": "PASS",
    "database_connection_performed": False,
    "sql_performed": False,
    "production_manifest_changed": False,
    "future_revalidation_before_guard_required": True,
}

sealed_source_verification = {
    "schema_version": "1.0",
    "phase": PHASE,
    "sealed_review_evidence_root":
        SEALED_SOURCE.relative_to(REPO).as_posix(),
    "sealed_review_evidence_file_count": 11,
    "sealed_review_evidence_directory_count_excluding_root": 1,
    "sealed_review_evidence_fixed_sha256": SEALED_FIXED_SHA,
    "sealed_file_mode": "0444",
    "sealed_directory_mode": "0555",
    "sealed_evidence_manifest_entry_count": 10,
    "sealed_packet_manifest_entry_count": 8,
    "human_review_result": "PASS",
    "seal_readonly_review": "PASS",
    "candidate_source_tree_identity_sha256": candidate_tree_sha,
    "sealed_source_unchanged": True,
}

operator_checklist = """# Final Execution Operator Checklist

This checklist is informational only. It does not approve or execute the
transaction.

## Before a later final approval

- [ ] Confirm this Final Execution Approval Packet passed a separate readonly review.
- [ ] Confirm a new explicit human approval issues the exact one-shot token.
- [ ] Confirm the root-owned approval-binding parent already exists and is not a symlink.
- [ ] Create the approval binding only under a separately approved procedure.
- [ ] Confirm the binding is root:root, mode 0400, regular, non-symlink, and unexpired.
- [ ] Confirm every binding SHA and size matches `approval-binding-required-values.json`.
- [ ] Confirm no prior execution attempt consumed the one-shot guard.
- [ ] Confirm the operator understands that the guard is permanent and never removed.
- [ ] Confirm Writer Freeze remains HOLD and Production release remains HOLD.

## Future wrapper preflight

The wrapper—not this preparation Packet—must verify immediately before
mutation:

- [ ] sealed Evidence and Candidate exact identities;
- [ ] all six protected Production SHA-256 values;
- [ ] approval binding validity, token SHA, expiry, and one-attempt limit;
- [ ] renameat2(RENAME_NOREPLACE) availability;
- [ ] guard path-entry absence using lexists;
- [ ] `/opt/ai-media-os/3e-j` path-entry absence using lexists;
- [ ] sudoers target path-entry absence using lexists;
- [ ] derived staging path-entry absence using lexists;
- [ ] parent-chain lstat symlink rejection;
- [ ] `/usr/sbin/visudo` availability.

## Execution and stop rules

- [ ] Use only the exact argv in `exact-command-contract.json`.
- [ ] Pass no arbitrary arguments.
- [ ] Never retry automatically.
- [ ] Stop after any non-success terminal state.
- [ ] Treat incomplete rollback as Emergency HOLD.
- [ ] Do not execute the root helper or writer runner as part of deployment.
- [ ] Keep Production release at HOLD after a successful deployment.
"""

seal_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "staging_required": True,
    "file_mode_after_seal": "0444",
    "directory_mode_after_seal": "0555",
    "final_promotion": "renameat2(RENAME_NOREPLACE)",
    "source_evidence_mutation_allowed": False,
    "candidate_source_mutation_allowed": False,
    "root_deployment_execution_allowed": False,
    "production_release_decision": "HOLD",
}

# Create the new Packet under the Python-created staging root.
os.mkdir(PACKET, 0o750)

failed_staging_inventory = {
    "schema_version": "1.0",
    "phase": PHASE,
    "failed_staging_count": 2,
    "records": [
        {
            "index": 1,
            "failure_class": "STAGING_LIFECYCLE_CONTRACT_CONTRADICTION",
            "failure_marker": "STAGING_PATH_ENTRY_EXISTS",
            "failed_script_exit_code": 1,
            "relative_path":
                FAILED_STAGING_1.relative_to(REPO).as_posix(),
            "mode": "0750",
            "uid": 1001,
            "gid": 1001,
            "mtime_ns": 1785061400585610693,
            "file_count": 0,
            "directory_count_excluding_root": 0,
            "symlink_count": 0,
            "nonregular_count": 0,
            "immutable_partial_failure_record": True,
        },
        {
            "index": 2,
            "failure_class": "EXECUTION_RUNNER_SOURCE_PATH_BINDING_MISMATCH",
            "failure_marker": "FileNotFoundError",
            "failed_script_exit_code": 1,
            "relative_path":
                FAILED_STAGING_2.relative_to(REPO).as_posix(),
            "mode": "0750",
            "uid": 1001,
            "gid": 1001,
            "mtime_ns": 1785063834302475917,
            "file_count": 0,
            "directory_count_excluding_root": 0,
            "symlink_count": 0,
            "nonregular_count": 0,
            "immutable_partial_failure_record": True,
        },
    ],
    "final_evidence_candidate_count_before_r2": 0,
    "readonly_inventory": "PASS",
    "failed_staging_mutation": False,
}

runner_source_binding_correction = {
    "schema_version": "1.0",
    "phase": PHASE,
    "correction_scope": "RUNNER_SOURCE_BINDING_ONLY",
    "canonical_runner_source_relative_path":
        runner_source.relative_to(CANDIDATE_SOURCE).as_posix(),
    "execution_candidate_relative_path":
        candidate_root.relative_to(CANDIDATE_SOURCE).as_posix(),
    "execution_evidence_file_count": 65,
    "execution_evidence_manifest_entry_count": 64,
    "execution_packet_file_count": 63,
    "execution_packet_manifest_entry_count": 62,
    "runner_candidate_file_count": 7,
    "runner_candidate_manifest_entry_count": 6,
    "runner_candidate_manifest_sha256": RUNNER_CANDIDATE_MANIFEST_SHA,
    "runner_payload_sha256": RUNNER_PAYLOAD_SHA,
    "source_binding_contract_sha256": SOURCE_BINDING_CONTRACT_SHA,
    "partial_source_inventory_sha256": PARTIAL_SOURCE_INVENTORY_SHA,
    "three_level_runner_manifest_binding": "PASS",
    "source_binding_contract_literal_path_required": False,
    "candidate_code_changed": False,
    "corrected_wrapper_changed": False,
    "corrected_wrapper_executed": False,
}

reviewer_assumption_corrections = {
    "schema_version": "1.0",
    "phase": PHASE,
    "initial_reviewer_error_was_packet_defect": False,
    "corrections": [
        {
            "error_class": "REVIEWER_PARTIAL_SNAPSHOT_ROOT_TYPE_ASSUMPTION",
            "incorrect_assumption":
                "source-partial-evidence-snapshot is a complete Evidence root",
            "corrected_fact":
                "source-partial-evidence-snapshot is a recursive file container",
            "packet_defect": False,
        },
        {
            "error_class":
                "REVIEWER_EXTRA_INTERMEDIATE_PACKET_MANIFEST_ASSUMPTION",
            "incorrect_assumption":
                "source-partial-evidence-snapshot has a direct packet manifest",
            "corrected_fact":
                "Execution Packet manifest directly binds recursive files",
            "packet_defect": False,
        },
        {
            "error_class": "REVIEWER_BINDING_RECORD_SCHEMA_ASSUMPTION",
            "incorrect_assumption":
                "all auxiliary binding records must contain literal path tokens",
            "corrected_fact":
                "literal paths and logical SHA bindings are split by schema",
            "packet_defect": False,
        },
    ],
    "reviewer_root_type_correction_registered": True,
    "reviewer_intermediate_manifest_correction_registered": True,
    "reviewer_binding_schema_correction_registered": True,
}

def write_json(name: str, value: dict[str, Any]) -> None:
    write_exclusive(
        PACKET / name,
        (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"),
    )

write_json("failed-staging-inventory.json", failed_staging_inventory)
write_json(
    "runner-source-binding-correction.json",
    runner_source_binding_correction,
)
write_json(
    "reviewer-assumption-corrections.json",
    reviewer_assumption_corrections,
)
write_exclusive(PACKET / "human-approval-verbatim.txt", APPROVAL_TEXT)
write_exclusive(PACKET / "operation-manual.md", MANUAL_TEXT)
write_exclusive(PACKET / "packet-contract.json", PACKET_CONTRACT_BYTES)
write_json("sealed-source-verification.json", sealed_source_verification)
write_json("execution-candidate-binding.json", candidate_binding)
write_json("protected-sha-contract.json", protected_contract)
write_json("target-layout.json", target_layout)
write_json("preflight-path-state-contract.json", preflight_contract)
write_json("rollback-stop-contract.json", rollback_stop_contract)
write_json("exact-command-contract.json", exact_command_contract)
write_json(
    "approval-binding-required-values.json",
    approval_binding_required_values,
)
write_json(
    "final-execution-approval-token-template.json",
    token_template,
)
write_json("seal-contract.json", seal_contract)
write_exclusive(
    PACKET / "operator-checklist.md",
    operator_checklist.encode("utf-8"),
)

result = {
    "schema_version": "1.0",
    "phase": PHASE,
    "result": (
        "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
        "PACKET_R2_RUNNER_SOURCE_BINDING_CORRECTION_"
        "PREPARED_AND_SEALED_NO_EXECUTION"
    ),
    "r2_runner_source_binding_correction_only": True,
    "r1_python_only_staging_lifecycle_maintained": True,
    "staging_creation_owner": "PYTHON_ONLY",
    "shell_staging_mkdir_removed": True,
    "canonical_runner_source_binding": "PASS",
    "canonical_runner_source_relative_path":
        runner_source.relative_to(CANDIDATE_SOURCE).as_posix(),
    "three_level_runner_manifest_binding": "PASS",
    "runner_candidate_manifest_revalidation": "PASS",
    "source_binding_record_schema_review": "PASS",
    "source_binding_contract_literal_path_required": False,
    "reviewer_assumption_corrections_registered": True,
    "failed_staging_inventory_registered": True,
    "failed_staging_count": 2,
    "failed_staging_unchanged": True,
    "evidence_root": FINAL_REL,
    "sealed_review_evidence_root":
        SEALED_SOURCE.relative_to(REPO).as_posix(),
    "candidate_source_evidence_root":
        CANDIDATE_SOURCE.relative_to(REPO).as_posix(),
    "sealed_review_evidence_revalidation": "PASS",
    "candidate_source_identity_revalidation": "PASS",
    "candidate_manifest_revalidation": "PASS",
    "execution_evidence_root":
        execution_evidence_root.relative_to(REPO).as_posix(),
    "execution_evidence_file_count": 65,
    "execution_evidence_directory_count_excluding_root": 12,
    "execution_packet_file_count": 63,
    "execution_packet_directory_count": 11,
    "execution_packet_manifest_entry_count": 62,
    "execution_evidence_manifest_entry_count": 64,
    "outer_and_execution_candidate_equivalence": "PASS",
    "protected_sha_revalidation": "PASS",
    "wrapper_static_binding_review": "PASS",
    "target_layout_registered": True,
    "expected_prestate_registered": True,
    "target_state_inspected_during_preparation": False,
    "rollback_stop_contract_registered": True,
    "exact_command_contract_registered": True,
    "operator_checklist_generated": True,
    "final_execution_approval_token_template_generated": True,
    "approval_binding_required_values_registered": True,
    "final_execution_approval_packet_preparation_only": True,
    "final_execution_approval_issued": False,
    "final_execution_token_consumed": False,
    "root_deployment_execution_allowed": False,
    "sudoers_installation_allowed": False,
    "corrected_wrapper_execution_allowed": False,
    "approval_binding_created": False,
    "one_shot_deployment_guard_created": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "sealed": True,
    "seal_file_mode": "0444",
    "seal_directory_mode": "0555",
    "next_gate": (
        "HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_"
        "FINAL_EXECUTION_APPROVAL_PACKET_SEAL_READONLY"
    ),
}
write_exclusive(
    STAGING / "result.json",
    (json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"),
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
    "status": (
        "FINAL_EXECUTION_APPROVAL_PACKET_R2_RUNNER_SOURCE_BINDING_"
        "CORRECTION_PREPARED_AND_SEALED_NO_EXECUTION"
    ),
    "r2_runner_source_binding_correction_only": True,
    "r1_python_only_staging_lifecycle_maintained": True,
    "canonical_runner_source_binding": "PASS",
    "three_level_runner_manifest_binding": "PASS",
    "reviewer_assumption_corrections_registered": True,
    "failed_staging_inventory_registered": True,
    "failed_staging_count": 2,
    "packet_file_count_excluding_manifest": len(packet_entries),
    "packet_files": packet_entries,
    "candidate_artifact_count": 18,
    "target_directory_count": len(TARGET_DIRECTORIES),
    "target_file_count": len(TARGET_FILES),
    "protected_sha_count": len(PROTECTED_SHA),
    "final_execution_approval_issued": False,
    "final_execution_token_consumed": False,
    "root_deployment_execution_allowed": False,
    "production_release_decision": "HOLD",
    "sealed": True,
}
write_exclusive(
    PACKET / "packet-manifest.json",
    (json.dumps(packet_manifest, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    ),
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

new_files, new_dirs, new_links, new_other = scan(STAGING)
require(new_links == 0 and new_other == 0, "NEW_EVIDENCE_SPECIAL")
require(len(new_files) == 20, f"NEW_EVIDENCE_FILE_COUNT:{len(new_files)}")
require(len(new_dirs) == 1, f"NEW_EVIDENCE_DIR_COUNT:{len(new_dirs)}")
require(len(packet_entries) == 17,
        f"NEW_PACKET_ENTRY_COUNT:{len(packet_entries)}")
require(len(evidence_lines) == 19,
        f"NEW_EVIDENCE_ENTRY_COUNT:{len(evidence_lines)}")

# New manifest revalidation before sealing.
new_packet_manifest = json_object(PACKET / "packet-manifest.json")
new_packet_entries = manifest_entries(new_packet_manifest)
require(len(new_packet_entries) == 17, "NEW_PACKET_MANIFEST_COUNT")
new_packet_map: dict[str, dict[str, Any]] = {}
for entry in new_packet_entries:
    name = entry.get("name")
    require(isinstance(name, str), "NEW_PACKET_NAME")
    require(name not in new_packet_map, f"NEW_PACKET_DUP:{name}")
    new_packet_map[name] = entry
packet_files_actual, _, _, _ = scan(PACKET)
require(
    set(new_packet_map) == packet_files_actual - {"packet-manifest.json"},
    "NEW_PACKET_EXACT_SET",
)
for relative, entry in new_packet_map.items():
    path = PACKET / relative
    require(entry.get("sha256") == sha256(path),
            f"NEW_PACKET_SHA:{relative}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"NEW_PACKET_SIZE:{relative}")

new_evidence_map: dict[str, str] = {}
for raw in (STAGING / "evidence-manifest.txt").read_text(
    encoding="utf-8"
).splitlines():
    digest, relative = raw.split("  ", 1)
    require(relative not in new_evidence_map, f"NEW_EVIDENCE_DUP:{relative}")
    new_evidence_map[relative] = digest
require(len(new_evidence_map) == 19, "NEW_EVIDENCE_MANIFEST_COUNT")
require(
    set(new_evidence_map) == new_files - {"evidence-manifest.txt"},
    "NEW_EVIDENCE_EXACT_SET",
)
for relative, expected in new_evidence_map.items():
    require(sha256(STAGING / relative) == expected,
            f"NEW_EVIDENCE_SHA:{relative}")

# Sources must remain byte-for-byte and metadata invariant.
require(identity(SEALED_SOURCE) == sealed_identity_before,
        "SEALED_SOURCE_CHANGED_PRE_SEAL")
require(identity(CANDIDATE_SOURCE) == candidate_identity_before,
        "CANDIDATE_SOURCE_CHANGED_PRE_SEAL")
for index, (failed_root, expected_identity) in enumerate(
    zip(FAILED_STAGINGS, failed_staging_identities_before),
    start=1,
):
    item = failed_root.lstat()
    require(
        (
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
            item.st_mtime_ns,
        )
        == expected_identity,
        f"FAILED_STAGING_CHANGED_PRE_SEAL:{index}",
    )
    require(
        scan(failed_root) == (set(), set(), 0, 0),
        f"FAILED_STAGING_CONTENT_CHANGED_PRE_SEAL:{index}",
    )

# Seal only the newly created staging Evidence.
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
        require(stat.S_IMODE(item.st_mode) == 0o444,
                f"SEALED_NEW_FILE_MODE:{path}")
    elif stat.S_ISDIR(item.st_mode):
        require(stat.S_IMODE(item.st_mode) == 0o555,
                f"SEALED_NEW_DIR_MODE:{path}")
    else:
        raise AssertionError(f"SEALED_NEW_SPECIAL:{path}")
require(stat.S_IMODE(STAGING.lstat().st_mode) == 0o555,
        "SEALED_NEW_ROOT_MODE")

require(identity(SEALED_SOURCE) == sealed_identity_before,
        "SEALED_SOURCE_CHANGED_POST_SEAL")
require(identity(CANDIDATE_SOURCE) == candidate_identity_before,
        "CANDIDATE_SOURCE_CHANGED_POST_SEAL")
for index, (failed_root, expected_identity) in enumerate(
    zip(FAILED_STAGINGS, failed_staging_identities_before),
    start=1,
):
    item = failed_root.lstat()
    require(
        (
            stat.S_IMODE(item.st_mode),
            item.st_uid,
            item.st_gid,
            item.st_mtime_ns,
        )
        == expected_identity,
        f"FAILED_STAGING_CHANGED_POST_SEAL:{index}",
    )
    require(
        scan(failed_root) == (set(), set(), 0, 0),
        f"FAILED_STAGING_CONTENT_CHANGED_POST_SEAL:{index}",
    )
for relative, expected in PROTECTED_SHA.items():
    require(sha256(REPO / relative) == expected,
            f"PROTECTED_CHANGED:{relative}")

fsync_directory(PACKET)
fsync_directory(STAGING)
fsync_directory(STAGING.parent)
rename_noreplace(STAGING, FINAL)
fsync_directory(FINAL.parent)

require(FINAL.resolve(strict=True) == FINAL, "FINAL_RESOLUTION")
require(stat.S_IMODE(FINAL.lstat().st_mode) == 0o555,
        "FINAL_ROOT_MODE")
final_files, final_dirs, final_links, final_other = scan(FINAL)
require(len(final_files) == 20, "FINAL_FILE_COUNT")
require(len(final_dirs) == 1, "FINAL_DIR_COUNT")
require(final_links == 0 and final_other == 0, "FINAL_SPECIAL_PATH")
require(not list(FINAL.rglob("*.pyc")), "FINAL_BYTECODE_SIDE_EFFECT")

print(
    "RESULT=PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_FINAL_EXECUTION_APPROVAL_"
    "PACKET_R2_RUNNER_SOURCE_BINDING_CORRECTION_"
    "PREPARED_AND_SEALED_NO_EXECUTION"
)
print("R2_RUNNER_SOURCE_BINDING_CORRECTION_ONLY=true")
print("R1_PYTHON_ONLY_STAGING_LIFECYCLE_MAINTAINED=true")
print("STAGING_CREATION_OWNER=PYTHON_ONLY")
print("SHELL_STAGING_MKDIR_REMOVED=true")
print(
    "CANONICAL_RUNNER_ROOT="
    f"{runner_source.relative_to(CANDIDATE_SOURCE).as_posix()}"
)
print("CANONICAL_RUNNER_SOURCE_BINDING=PASS")
print("RUNNER_CANDIDATE_FILE_COUNT=7")
print("RUNNER_CANDIDATE_MANIFEST_ENTRY_COUNT=6")
print("RUNNER_CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("THREE_LEVEL_RUNNER_MANIFEST_BINDING=PASS")
print("SOURCE_BINDING_RECORD_SCHEMA_REVIEW=PASS")
print("SOURCE_BINDING_CONTRACT_LITERAL_PATH_REQUIRED=false")
print("REVIEWER_ASSUMPTION_CORRECTIONS_REGISTERED=true")
for index, failed_root in enumerate(FAILED_STAGINGS, start=1):
    print(
        f"FAILED_STAGING_{index}_ROOT="
        f"{failed_root.relative_to(REPO).as_posix()}"
    )
    print(f"FAILED_STAGING_{index}_MODE=0750")
    print(f"FAILED_STAGING_{index}_UID=1001")
    print(f"FAILED_STAGING_{index}_GID=1001")
    print(f"FAILED_STAGING_{index}_FILE_COUNT=0")
    print(f"FAILED_STAGING_{index}_DIRECTORY_COUNT_EXCLUDING_ROOT=0")
    print(f"FAILED_STAGING_{index}_SYMLINK_COUNT=0")
    print(f"FAILED_STAGING_{index}_NONREGULAR_COUNT=0")
    print(f"FAILED_STAGING_{index}_IDENTITY=PASS")
    print(f"FAILED_STAGING_{index}_EMPTY=true")
print("FAILED_STAGING_COUNT=2")
print("FAILED_STAGING_INVENTORY_REGISTERED=true")
print("FAILED_STAGING_UNCHANGED=true")
print(f"EVIDENCE_ROOT={FINAL_REL}")
print("SEALED_REVIEW_EVIDENCE_FILE_COUNT=11")
print("SEALED_REVIEW_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("SEALED_REVIEW_EVIDENCE_REVALIDATION=PASS")
print("SEALED_REVIEW_EVIDENCE_UNCHANGED=true")
print("CANDIDATE_SOURCE_FILE_COUNT=245")
print("CANDIDATE_SOURCE_DIRECTORY_COUNT_EXCLUDING_ROOT=46")
print(f"CANDIDATE_SOURCE_TREE_IDENTITY_SHA256={candidate_tree_sha}")
print("CANDIDATE_SOURCE_IDENTITY_REVALIDATION=PASS")
print("CANDIDATE_SOURCE_UNCHANGED=true")
print(
    "EXECUTION_EVIDENCE_ROOT="
    f"{execution_evidence_root.relative_to(REPO).as_posix()}"
)
print("EXECUTION_EVIDENCE_FILE_COUNT=65")
print("EXECUTION_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=12")
print("EXECUTION_PACKET_FILE_COUNT=63")
print("EXECUTION_PACKET_DIRECTORY_COUNT=11")
print("EXECUTION_PACKET_MANIFEST_ENTRY_COUNT=62")
print("EXECUTION_EVIDENCE_MANIFEST_ENTRY_COUNT=64")
print("CANDIDATE_ARTIFACT_COUNT=18")
print("CANDIDATE_MANIFEST_ENTRY_COUNT=17")
print("CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("OUTER_AND_EXECUTION_CANDIDATE_EQUIVALENCE=PASS")
print("WRAPPER_STATIC_BINDING_REVIEW=PASS")
print("CORRECTED_WRAPPER_EXECUTED=false")
print("PROTECTED_SHA_COUNT=6")
print("PROTECTED_SHA_REVALIDATION=PASS")
print("TARGET_DIRECTORY_COUNT=5")
print("TARGET_FILE_COUNT=6")
print("TARGET_LAYOUT_REGISTERED=true")
print("EXPECTED_PRESTATE_REGISTERED=true")
print("TARGET_STATE_INSPECTED_DURING_PREPARATION=false")
print("TARGET_STATE_INSPECTION_ALLOWED=false")
print("REVIEWER_ROOT_TYPE_CORRECTION_REGISTERED=true")
print("REVIEWER_INTERMEDIATE_MANIFEST_CORRECTION_REGISTERED=true")
print("REVIEWER_BINDING_SCHEMA_CORRECTION_REGISTERED=true")
print("LEXISTS_PREFLIGHT_CONTRACT_REGISTERED=true")
print("PARENT_DEVICE_INODE_ROLLBACK_CONTRACT_REGISTERED=true")
print("RENAMEAT2_RENAME_NOREPLACE_CONTRACT_REGISTERED=true")
print(f"ONE_SHOT_GUARD_PLANNED_PATH={GUARD_PATH}")
print("ROLLBACK_STOP_CONTRACT_REGISTERED=true")
print("EXACT_COMMAND_CONTRACT_REGISTERED=true")
print("OPERATOR_CHECKLIST_GENERATED=true")
print("FINAL_EXECUTION_APPROVAL_TOKEN_TEMPLATE_GENERATED=true")
print("APPROVAL_BINDING_REQUIRED_VALUES_REGISTERED=true")
print("NEW_EVIDENCE_FILE_COUNT=20")
print("NEW_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("NEW_PACKET_MANIFEST_ENTRY_COUNT=17")
print("NEW_EVIDENCE_MANIFEST_ENTRY_COUNT=19")
print("SEALED_FILE_MODE=0444")
print("SEALED_DIRECTORY_MODE=0555")
print("SEAL_VALIDATION=PASS")
print("FINAL_PROMOTION=RENAMEAT2_RENAME_NOREPLACE")
print("FINAL_EXECUTION_APPROVAL_PACKET_PREPARATION_ONLY=true")
print("FINAL_EXECUTION_APPROVAL_ISSUED=false")
print("FINAL_EXECUTION_TOKEN_CONSUMED=false")
print("ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false")
print("SUDOERS_INSTALLATION_ALLOWED=false")
print("CORRECTED_WRAPPER_EXECUTION_ALLOWED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE=HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_"
    "FINAL_EXECUTION_APPROVAL_PACKET_SEAL_READONLY"
)
print(f"RESULT_SHA={sha256(FINAL / 'result.json')}")
print(
    "PACKET_MANIFEST_SHA="
    f"{sha256(FINAL / 'packet-snapshot/packet-manifest.json')}"
)
print(
    "CANDIDATE_BINDING_SHA="
    f"{sha256(FINAL / 'packet-snapshot/execution-candidate-binding.json')}"
)
print(
    "EXACT_COMMAND_CONTRACT_SHA="
    f"{sha256(FINAL / 'packet-snapshot/exact-command-contract.json')}"
)
print(
    "TOKEN_TEMPLATE_SHA="
    f"{sha256(FINAL / 'packet-snapshot/final-execution-approval-token-template.json')}"
)
print(
    "EVIDENCE_MANIFEST_SHA="
    f"{sha256(FINAL / 'evidence-manifest.txt')}"
)

PY

echo "SCRIPT_EXIT_CODE=0"
