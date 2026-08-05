#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
SOURCE_REL="${BASE_REL}/i2f3e-j-root-deployment-execution-packet-r1-r2-r2-negative-test-mutation-indentation-correction-preparation-20260726T072647Z-534604"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
FINAL_PREFIX="i2f3e-j-root-deployment-execution-packet-r1-r2-r2-human-review-result-registration-and-seal"
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
test -d "$SOURCE_ROOT"
test ! -e "$FINAL_ROOT"
test ! -L "$FINAL_ROOT"
test ! -e "$STAGING_ROOT"
test ! -L "$STAGING_ROOT"

cd "$REPO_ROOT"

printf '\n===== APPROVED R1-R2-R2 SOURCE FIXED SHA REVIEW =====\n'
sha256sum -c <<SHAS
8db446727c08e063661fb7272d390b20bcb31280f08a945fd464f148c38b370d  ${SOURCE_ROOT}/result.json
e3d74993dbafac43853e09391c35f3c591dd7dbb36f1b66b72921baa25dd9e57  ${SOURCE_ROOT}/packet-snapshot/packet-manifest.json
fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577  ${SOURCE_ROOT}/packet-snapshot/candidate-artifacts/candidate-manifest.json
78aa0778009d37ad1a6ec75c0ff62c2e07b42bf0dc80e32e8ce78f15e3b126f7  ${SOURCE_ROOT}/evidence-manifest.txt
SHAS

mkdir "$STAGING_ROOT"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - \
  "$REPO_ROOT" \
  "$SOURCE_ROOT" \
  "$STAGING_ROOT" \
  "$FINAL_ROOT" \
  "$FINAL_REL" <<'PY'

from __future__ import annotations

import ast
import base64
import ctypes
import difflib
import errno
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

REPO = Path(sys.argv[1]).resolve(strict=True)
SOURCE = Path(sys.argv[2]).resolve(strict=True)
STAGING = Path(sys.argv[3]).resolve(strict=True)
FINAL = Path(sys.argv[4])
FINAL_REL = sys.argv[5]

PACKET = STAGING / "packet-snapshot"

PHASE = (
    "TST-5D-W2B-I2F-3E-J-ROOT-DEPLOYMENT-EXECUTION-PACKET-"
    "R1-R2-R2-HUMAN-REVIEW-RESULT-SEAL"
)

APPROVAL_TEXT = base64.b64decode("QVBQUk9WRV8zRV9KX1JPT1RfREVQTE9ZTUVOVF9FWEVDVVRJT05fUEFDS0VUX1IxX1IyX1IyX0hVTUFOX1JFVklFV19SRVNVTFRfUkVHSVNUUkFUSU9OX0FORF9TRUFMX1BSRVBBUkFUSU9OX05PX0VYRUNVVElPTgoK5a++6LGhRXZpZGVuY2XvvJoKZXhjaGFuZ2UvcmV2aWV3X2V2aWRlbmNlL3NsYWNrX3dvcmtlcl9yZWxlYXNlX3JlYmluZGluZy8Kc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzLwp0c3QtNWQtdzJiLWkyZS1iYXNlbGluZS1hYnNvcnB0aW9uLXJlcmV2aWV3LTIwMjYwNzI1VDE0MTYzMi8KaTJmM2Utai1yb290LWRlcGxveW1lbnQtZXhlY3V0aW9uLXBhY2tldC1yMS1yMi1yMi0KbmVnYXRpdmUtdGVzdC1tdXRhdGlvbi1pbmRlbnRhdGlvbi1jb3JyZWN0aW9uLXByZXBhcmF0aW9uLQoyMDI2MDcyNlQwNzI2NDdaLTUzNDYwNAoKSHVtYW4gUmV2aWV357WQ5p6c77yaClJPT1RfREVQTE9ZTUVOVF9FWEVDVVRJT05fUEFDS0VUX1IxX1IyX1IyX0NPUlJFQ1RJT05fSFVNQU5fUkVWSUVXPVBBU1MKQ09SUkVDVEVEX0hVTUFOX1JFVklFV19FWElUX0NPREU9MApSRVZJRVdFUl9BU1RfU0NPUEVfQ09SUkVDVElPTj1SMVIxX05FR0FUSVZFX1RFU1RTX0NMQVNTX01FVEhPRF9FWEFDVF9PTkUKClJFU1VMVF9TSEE9OGRiNDQ2NzI3YzA4ZTA2MzY2MWZiNzI3MmQzOTBiMjBiY2IzMTI4MGYwOGE5NDVmZDQ2NGYxNDhjMzhiMzcwZApQQUNLRVRfTUFOSUZFU1RfU0hBPWUzZDc0OTkzZGJhZmFjNDM4NTNlMDkzOTFjMzVmM2M1OTFkZDdkYmIzNmYxYjY2YjcyOTIxYmFhMjVkZDllNTcKQ0FORElEQVRFX01BTklGRVNUX1NIQT1mYjExNTk5NDMwNjM4OTgyNjg4OWNmOTE2NjZmNjVlMjM3NjBkNjU3NDNkYTUyOGMxM2NhYjA3ZWI1OGE2NTc3CkVWSURFTkNFX01BTklGRVNUX1NIQT03OGFhMDc3ODAwOWQzN2FkMWE2ZWM3NWMwZmY2MmMyZTA3YjQyYmYwZGM4MGUzMmU4Y2U3OGYxNWUzYjEyNmY3CgpIVU1BTl9SRVZJRVdfUkVTVUxUX1JFR0lTVFJBVElPTl9PTkxZPXRydWUKUk9PVF9ERVBMT1lNRU5UX0VYRUNVVElPTl9BTExPV0VEPWZhbHNlClNVRE9FUlNfSU5TVEFMTEFUSU9OX0FMTE9XRUQ9ZmFsc2UKQ09SUkVDVEVEX1dSQVBQRVJfRVhFQ1VUSU9OX0FMTE9XRUQ9ZmFsc2UKQVBQUk9WQUxfQklORElOR19DUkVBVEVEPWZhbHNlCk9ORV9TSE9UX0RFUExPWU1FTlRfR1VBUkRfQ1JFQVRFRD1mYWxzZQpXUklURVJfRlJFRVpFX0VYRUNVVElPTj1IT0xEClBST0RVQ1RJT05fUkVMRUFTRV9ERUNJU0lPTj1IT0xEClJFTEVBU0VfU1RBVFVTPUNBTkRJREFURV9OT1RfQVBQUk9WRUQK", validate=True)
REVIEW_RESULT_TEXT = base64.b64decode("Uk9PVF9ERVBMT1lNRU5UX0VYRUNVVElPTl9QQUNLRVRfUjFfUjJfUjJfQ09SUkVDVElPTl9IVU1BTl9SRVZJRVc9UEFTUwpDT1JSRUNURURfSFVNQU5fUkVWSUVXX0VYSVRfQ09ERT0wClJFVklFV0VSX0FTVF9TQ09QRV9DT1JSRUNUSU9OPVIxUjFfTkVHQVRJVkVfVEVTVFNfQ0xBU1NfTUVUSE9EX0VYQUNUX09ORQpQUkVWSU9VU19SRVZJRVdfU0VDVElPTlNfVEhST1VHSF9PTkVfTElORV9ESUZGPVBBU1MKRVZJREVOQ0VfRVhBQ1RfRklMRV9TRVQ9UEFTUwpFVklERU5DRV9NQU5JRkVTVF9SRVZBTElEQVRJT049UEFTUwpQQUNLRVRfTUFOSUZFU1RfUkVWQUxJREFUSU9OPVBBU1MKQ0FORElEQVRFX01BTklGRVNUX1JFVkFMSURBVElPTj1QQVNTClNPVVJDRV9TTkFQU0hPVF9SRVZJRVc9UEFTUwpWQUxJREFUT1JfVEFSR0VUX1JFVklFVz1QQVNTCk5FR0FUSVZFX1RFU1RfNDBfUEFTU19MT0dfUkVWSUVXPVBBU1MKVkFMSURBVE9SX1BBU1NfTE9HX1JFVklFVz1QQVNTClZJU1VET19QQVNTX0xPR19SRVZJRVc9UEFTUwpPTkVfTElORV9ORUdBVElWRV9URVNUX0NIQU5HRV9SRVZJRVc9UEFTUwpURVNUXzIxX0FTVF9TRUxFQ1RPUl9SRVZJRVc9UEFTUwpURVNUXzI2X0FTVF9TRUxFQ1RPUl9SRVZJRVc9UEFTUwpQUk9URUNURURfU0hBX1VOQ0hBTkdFRD10cnVlCkJZVEVDT0RFX1NJREVfRUZGRUNUPWZhbHNlCkhVTUFOX1JFVklFV19SRUFET05MWV9PTkxZPXRydWUKRVZJREVOQ0VfTVVUQVRJT049ZmFsc2UKUk9PVF9ERVBMT1lNRU5UX0VYRUNVVElPTl9BTExPV0VEPWZhbHNlClNVRE9FUlNfSU5TVEFMTEFUSU9OX0FMTE9XRUQ9ZmFsc2UKQ09SUkVDVEVEX1dSQVBQRVJfRVhFQ1VUSU9OX0FMTE9XRUQ9ZmFsc2UKQVBQUk9WQUxfQklORElOR19DUkVBVEVEPWZhbHNlCk9ORV9TSE9UX0RFUExPWU1FTlRfR1VBUkRfQ1JFQVRFRD1mYWxzZQpXUklURVJfRlJFRVpFX0VYRUNVVElPTj1IT0xEClBST0RVQ1RJT05fUkVMRUFTRV9ERUNJU0lPTj1IT0xEClJFTEVBU0VfU1RBVFVTPUNBTkRJREFURV9OT1RfQVBQUk9WRUQK", validate=True)
MANUAL_TEXT = base64.b64decode("IyAzRS1KIFIxLVIyLVIyIEh1bWFuIFJldmlldyBSZXN1bHQgUmVnaXN0cmF0aW9uIGFuZCBTZWFsCgpUaGlzIG9wZXJhdGlvbiByZWFkcyB0aGUgYXBwcm92ZWQgUjEtUjItUjIgY29ycmVjdGlvbiBFdmlkZW5jZSBvbmx5LgoKSXQgcmV2YWxpZGF0ZXM6CgotIHRoZSBleGFjdCBFdmlkZW5jZSwgUGFja2V0LCBhbmQgQ2FuZGlkYXRlIGZpbGUgc2V0czsKLSBhbGwgRXZpZGVuY2UsIFBhY2tldCwgYW5kIENhbmRpZGF0ZSBtYW5pZmVzdCBoYXNoZXMgYW5kIHNpemVzOwotIHRoZSBmaXhlZCByZXN1bHQsIFBhY2tldCBtYW5pZmVzdCwgQ2FuZGlkYXRlIG1hbmlmZXN0LCBhbmQgRXZpZGVuY2UgbWFuaWZlc3QgU0hBLTI1NiB2YWx1ZXM7Ci0gdGhlIDE1MC1maWxlIHNvdXJjZSBzbmFwc2hvdCBhbmQgdGhlIDY1LWZpbGUgdmFsaWRhdG9yIHRhcmdldDsKLSB0aGUgZml4ZWQgcm9vdC1kZXBsb3ltZW50IHdyYXBwZXIgYW5kIHVuY2hhbmdlZCBSMS1SMSB2YWxpZGF0b3I7Ci0gdGhlIG9uZS1saW5lIG5lZ2F0aXZlLXRlc3QgbXV0YXRpb24taW5kZW50YXRpb24gY29ycmVjdGlvbjsKLSB0aGUgY2xhc3MtbWV0aG9kIEFTVCBzZWxlY3RvciB1c2VkIGJ5IHRlc3RzIDIxIGFuZCAyNjsKLSBwZXJzaXN0ZWQgbmVnYXRpdmUtdGVzdCwgdmFsaWRhdG9yLCB2aXN1ZG8sIGFuZCBQeXRob24tY29tcGlsZSBQQVNTIGxvZ3M7Ci0gdGhlIHNpeCBwcm90ZWN0ZWQgcHJvZHVjdGlvbiBTSEEtMjU2IHZhbHVlcy4KCkEgc2VwYXJhdGUgc3RhZ2luZyBFdmlkZW5jZSBpcyBjcmVhdGVkLiBBbGwgb3V0cHV0IGZpbGVzIGFyZSBzZXQgdG8gbW9kZSAwNDQ0CmFuZCBhbGwgb3V0cHV0IGRpcmVjdG9yaWVzIGFyZSBzZXQgdG8gbW9kZSAwNTU1IGJlZm9yZSB0aGUgc3RhZ2luZyBkaXJlY3RvcnkKaXMgcHJvbW90ZWQgdG8gaXRzIGZpbmFsIHVuaXF1ZSBFdmlkZW5jZSBuYW1lIHdpdGggTGludXggcmVuYW1lYXQyClJFTkFNRV9OT1JFUExBQ0UuCgpUaGUgc291cmNlIEV2aWRlbmNlIGlzIG5ldmVyIG1vZGlmaWVkLiBObyBkZXBsb3ltZW50IHdyYXBwZXIsIGJsb2NrZWQKZW50cnlwb2ludCwgcm9vdCBoZWxwZXIsIHJ1bm5lciwgYXBwcm92YWwgYmluZGluZywgb25lLXNob3QgZ3VhcmQsIGAvb3B0YAp0YXJnZXQsIHN1ZG9lcnMgdGFyZ2V0LCBkYXRhYmFzZSwgbWlncmF0aW9uLCBHaXQsIEdpdEh1Yiwgb3IgZXh0ZXJuYWwgbmV0d29yawpvcGVyYXRpb24gaXMgZXhlY3V0ZWQuCgpQcm9kdWN0aW9uIHJlbGVhc2UgcmVtYWlucyBIT0xELgo=", validate=True)
CONTRACT_BYTES = base64.b64decode("ewogICJhcHByb3ZhbF9iaW5kaW5nX2NyZWF0ZWQiOiBmYWxzZSwKICAiY29ycmVjdGVkX3dyYXBwZXJfZXhlY3V0aW9uX2FsbG93ZWQiOiBmYWxzZSwKICAiZmluYWxfcHJvbW90aW9uIjogIlJFTkFNRUFUMl9SRU5BTUVfTk9SRVBMQUNFIiwKICAibmVnYXRpdmVfdGVzdF9jb3VudCI6IDQwLAogICJvbmVfc2hvdF9kZXBsb3ltZW50X2d1YXJkX2NyZWF0ZWQiOiBmYWxzZSwKICAib3BlcmF0aW9uIjogIkhVTUFOX1JFVklFV19SRVNVTFRfUkVHSVNUUkFUSU9OX0FORF9TRUFMX09OTFkiLAogICJwaGFzZSI6ICJUU1QtNUQtVzJCLUkyRi0zRS1KLVJPT1QtREVQTE9ZTUVOVC1FWEVDVVRJT04tUEFDS0VULVIxLVIyLVIyLUhVTUFOLVJFVklFVy1SRVNVTFQtU0VBTCIsCiAgInByb2R1Y3Rpb25fcmVsZWFzZV9kZWNpc2lvbiI6ICJIT0xEIiwKICAicmVsZWFzZV9zdGF0dXMiOiAiQ0FORElEQVRFX05PVF9BUFBST1ZFRCIsCiAgInJldmlld19yZXN1bHQiOiAiUEFTUyIsCiAgInJldmlld2VyX2FzdF9zY29wZV9jb3JyZWN0aW9uIjogIlIxUjFfTkVHQVRJVkVfVEVTVFNfQ0xBU1NfTUVUSE9EX0VYQUNUX09ORSIsCiAgInJvb3RfZGVwbG95bWVudF9leGVjdXRpb25fYWxsb3dlZCI6IGZhbHNlLAogICJzY2hlbWFfdmVyc2lvbiI6ICIxLjAiLAogICJzZWFsX2RpcmVjdG9yeV9tb2RlIjogIjA1NTUiLAogICJzZWFsX2ZpbGVfbW9kZSI6ICIwNDQ0IiwKICAic291cmNlX2NhbmRpZGF0ZV9hcnRpZmFjdF9jb3VudCI6IDE4LAogICJzb3VyY2VfZXZpZGVuY2VfZGlyZWN0b3J5X2NvdW50X2V4Y2x1ZGluZ19yb290IjogNDYsCiAgInNvdXJjZV9ldmlkZW5jZV9maWxlX2NvdW50IjogMjQ1LAogICJzb3VyY2VfZXZpZGVuY2VfbWFuaWZlc3RfZW50cnlfY291bnQiOiAyNDQsCiAgInNvdXJjZV9tdXRhdGlvbl9hbGxvd2VkIjogZmFsc2UsCiAgInNvdXJjZV9wYWNrZXRfZGlyZWN0b3J5X2NvdW50IjogNDUsCiAgInNvdXJjZV9wYWNrZXRfZmlsZV9jb3VudCI6IDI0MywKICAic291cmNlX3BhY2tldF9tYW5pZmVzdF9lbnRyeV9jb3VudCI6IDI0MiwKICAic291cmNlX3NuYXBzaG90X2RpcmVjdG9yeV9jb3VudCI6IDI5LAogICJzb3VyY2Vfc25hcHNob3RfZmlsZV9jb3VudCI6IDE1MCwKICAic3Vkb2Vyc19pbnN0YWxsYXRpb25fYWxsb3dlZCI6IGZhbHNlLAogICJ2YWxpZGF0b3JfdGFyZ2V0X2RpcmVjdG9yeV9jb3VudCI6IDEyLAogICJ2YWxpZGF0b3JfdGFyZ2V0X2ZpbGVfY291bnQiOiA2NSwKICAid3JpdGVyX2ZyZWV6ZV9leGVjdXRpb24iOiAiSE9MRCIKfQo=", validate=True)

EXPECTED_FIXED_SHA = {
    "result.json":
        "8db446727c08e063661fb7272d390b20bcb31280f08a945fd464f148c38b370d",
    "packet-snapshot/packet-manifest.json":
        "e3d74993dbafac43853e09391c35f3c591dd7dbb36f1b66b72921baa25dd9e57",
    "packet-snapshot/candidate-artifacts/candidate-manifest.json":
        "fb115994306389826889cf91666f65e23760d65743da528c13cab07eb58a6577",
    "evidence-manifest.txt":
        "78aa0778009d37ad1a6ec75c0ff62c2e07b42bf0dc80e32e8ce78f15e3b126f7",
}

WRAPPER_SHA = (
    "0d712c6e12dc0b98213ca1995e4f22d1"
    "e9088ab5ffc31a97a497d60ba769fa53"
)
VALIDATOR_SHA = (
    "efdabbe83c61a2618128f5518a726f00"
    "7062bba0e91959a01eed1f380d4b2d74"
)
FAILED_NEGATIVE_SHA = (
    "d626c22cab0e11f89323df6a5b81cb8"
    "b44a15d614928220e16d5954ac9676f99"
)
CORRECTED_NEGATIVE_SHA = (
    "6dad37c21c35921587e1839002a2435e"
    "bab4f4b88399f6035a9dcd9569156ca7"
)

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


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_NOT_OBJECT:{path}")
    return value


def manifest_entries(value: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("packet_files", "files", "artifacts"):
        candidate = value.get(key)
        if isinstance(candidate, list):
            require(
                all(isinstance(item, dict) for item in candidate),
                f"MANIFEST_ENTRY_TYPE:{key}",
            )
            return candidate
    raise AssertionError("MANIFEST_ENTRY_LIST_NOT_FOUND")


def inventory(root: Path) -> tuple[str, list[dict[str, object]]]:
    files, _, symlinks, nonregular = scan(root)
    require(symlinks == 0 and nonregular == 0, "INVENTORY_SPECIAL")
    entries: list[dict[str, object]] = []
    lines: list[str] = []
    for relative in sorted(files):
        path = root / relative
        item = path.lstat()
        digest = sha256(path)
        entry = {
            "relative_path": relative,
            "size_bytes": item.st_size,
            "mode": f"{stat.S_IMODE(item.st_mode):04o}",
            "uid": item.st_uid,
            "gid": item.st_gid,
            "sha256": digest,
        }
        entries.append(entry)
        lines.append(
            f"{digest}  {item.st_size}  "
            f"{stat.S_IMODE(item.st_mode):04o}  "
            f"{item.st_uid}  {item.st_gid}  {relative}"
        )
    tree_sha = hashlib.sha256(
        ("\n".join(lines) + "\n").encode("utf-8")
    ).hexdigest()
    return tree_sha, entries


def direct_class_method(
    class_node: ast.ClassDef,
    method_name: str,
) -> ast.FunctionDef:
    methods = [
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    ]
    require(
        len(methods) == 1,
        f"CLASS_METHOD_COUNT:{method_name}:{len(methods)}",
    )
    return methods[0]


def self_method_calls(
    function: ast.FunctionDef,
    method_name: str,
) -> list[ast.Call]:
    result: list[ast.Call] = []
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr == method_name
        ):
            result.append(node)
    return result


def keyword_value(call: ast.Call, name: str) -> ast.expr:
    matches = [
        keyword.value
        for keyword in call.keywords
        if keyword.arg == name
    ]
    require(len(matches) == 1, f"CALL_KEYWORD_COUNT:{name}")
    return matches[0]


def tuple_strings(node: ast.expr) -> tuple[str, ...]:
    require(isinstance(node, ast.Tuple), "EXPECTED_TUPLE")
    values: list[str] = []
    for element in node.elts:
        require(
            isinstance(element, ast.Constant)
            and isinstance(element.value, str),
            "EXPECTED_STRING_TUPLE_ELEMENT",
        )
        values.append(element.value)
    return tuple(values)


def rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "RENAMEAT2_UNAVAILABLE")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    AT_FDCWD = -100
    RENAME_NOREPLACE = 1
    result = renameat2(
        AT_FDCWD,
        os.fsencode(source),
        AT_FDCWD,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


require(SOURCE.is_relative_to(REPO), "SOURCE_OUTSIDE_REPOSITORY")
require(STAGING.is_relative_to(REPO), "STAGING_OUTSIDE_REPOSITORY")
require(FINAL.parent.resolve(strict=True) == STAGING.parent.resolve(strict=True),
        "FINAL_PARENT_MISMATCH")
require(not FINAL.exists() and not FINAL.is_symlink(), "FINAL_ALREADY_EXISTS")

source_identity_before = identity(SOURCE)
source_files, source_dirs, source_links, source_other = scan(SOURCE)
require(len(source_files) == 245, f"SOURCE_FILE_COUNT:{len(source_files)}")
require(len(source_dirs) == 46, f"SOURCE_DIR_COUNT:{len(source_dirs)}")
require(source_links == 0 and source_other == 0, "SOURCE_SPECIAL_PATH")

for relative, expected in EXPECTED_FIXED_SHA.items():
    path = SOURCE / relative
    require(path.is_file(), f"FIXED_FILE_MISSING:{relative}")
    require(sha256(path) == expected, f"FIXED_SHA_MISMATCH:{relative}")

evidence_manifest_map: dict[str, str] = {}
for line_number, raw in enumerate(
    (SOURCE / "evidence-manifest.txt").read_text(encoding="utf-8").splitlines(),
    start=1,
):
    require("  " in raw, f"EVIDENCE_MANIFEST_FORMAT:{line_number}")
    digest, relative = raw.split("  ", 1)
    require(relative not in evidence_manifest_map,
            f"EVIDENCE_MANIFEST_DUPLICATE:{relative}")
    evidence_manifest_map[relative] = digest
require(len(evidence_manifest_map) == 244, "EVIDENCE_MANIFEST_COUNT")
require(set(evidence_manifest_map) == source_files - {"evidence-manifest.txt"},
        "EVIDENCE_MANIFEST_EXACT_SET")
for relative, expected in evidence_manifest_map.items():
    require(sha256(SOURCE / relative) == expected,
            f"EVIDENCE_MANIFEST_CONTENT:{relative}")

source_packet = SOURCE / "packet-snapshot"
packet_files, packet_dirs, packet_links, packet_other = scan(source_packet)
require(len(packet_files) == 243, "PACKET_FILE_COUNT")
require(len(packet_dirs) == 45, "PACKET_DIR_COUNT")
require(packet_links == 0 and packet_other == 0, "PACKET_SPECIAL")

packet_manifest = json_object(source_packet / "packet-manifest.json")
packet_entries = manifest_entries(packet_manifest)
require(len(packet_entries) == 242, "PACKET_MANIFEST_COUNT")
packet_map: dict[str, dict[str, Any]] = {}
for entry in packet_entries:
    name = entry.get("name")
    require(isinstance(name, str), "PACKET_ENTRY_NAME")
    require(name not in packet_map, f"PACKET_DUPLICATE:{name}")
    packet_map[name] = entry
require(set(packet_map) == packet_files - {"packet-manifest.json"},
        "PACKET_MANIFEST_EXACT_SET")
for relative, entry in packet_map.items():
    path = source_packet / relative
    require(entry.get("sha256") == sha256(path),
            f"PACKET_MANIFEST_SHA:{relative}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"PACKET_MANIFEST_SIZE:{relative}")

candidate = source_packet / "candidate-artifacts"
candidate_files, candidate_dirs, candidate_links, candidate_other = scan(candidate)
require(len(candidate_files) == 18, "CANDIDATE_FILE_COUNT")
require(len(candidate_dirs) == 0, "CANDIDATE_DIR_COUNT")
require(candidate_links == 0 and candidate_other == 0, "CANDIDATE_SPECIAL")

candidate_manifest = json_object(candidate / "candidate-manifest.json")
candidate_entries = manifest_entries(candidate_manifest)
require(len(candidate_entries) == 17, "CANDIDATE_MANIFEST_COUNT")
candidate_map: dict[str, dict[str, Any]] = {}
for entry in candidate_entries:
    name = entry.get("name")
    require(isinstance(name, str), "CANDIDATE_ENTRY_NAME")
    require(name not in candidate_map, f"CANDIDATE_DUPLICATE:{name}")
    candidate_map[name] = entry
require(set(candidate_map) == candidate_files - {"candidate-manifest.json"},
        "CANDIDATE_MANIFEST_EXACT_SET")
for relative, entry in candidate_map.items():
    path = candidate / relative
    require(entry.get("sha256") == sha256(path),
            f"CANDIDATE_MANIFEST_SHA:{relative}")
    require(entry.get("size_bytes") == path.stat().st_size,
            f"CANDIDATE_MANIFEST_SIZE:{relative}")

snapshot = source_packet / "source-r1-r2-r1-partial-evidence-snapshot"
snapshot_files, snapshot_dirs, snapshot_links, snapshot_other = scan(snapshot)
require(len(snapshot_files) == 150, "SNAPSHOT_FILE_COUNT")
require(len(snapshot_dirs) == 29, "SNAPSHOT_DIR_COUNT")
require(snapshot_links == 0 and snapshot_other == 0, "SNAPSHOT_SPECIAL")

validator_target = source_packet / "r1-r1-validator-target"
target_files, target_dirs, target_links, target_other = scan(validator_target)
require(len(target_files) == 65, "TARGET_FILE_COUNT")
require(len(target_dirs) == 12, "TARGET_DIR_COUNT")
require(target_links == 0 and target_other == 0, "TARGET_SPECIAL")

wrapper = candidate / "root_deployment_execution_once_r1.py"
validator = candidate / "validate_root_deployment_execution_packet_r1.py"
negative = candidate / "test_root_deployment_execution_packet_r1_negative.py"
require(sha256(wrapper) == WRAPPER_SHA, "WRAPPER_SHA")
require(sha256(validator) == VALIDATOR_SHA, "VALIDATOR_SHA")
require(sha256(negative) == CORRECTED_NEGATIVE_SHA, "NEGATIVE_SHA")

failed_negative = (
    snapshot
    / "packet-snapshot/candidate-artifacts/"
    "test_root_deployment_execution_packet_r1_negative.py"
)
require(sha256(failed_negative) == FAILED_NEGATIVE_SHA,
        "FAILED_NEGATIVE_SHA")
before = failed_negative.read_text(encoding="utf-8").splitlines()
after = negative.read_text(encoding="utf-8").splitlines()
diff = list(difflib.unified_diff(
    before, after,
    fromfile="failed-negative",
    tofile="corrected-negative",
    lineterm="",
))
removed = [
    line[1:] for line in diff
    if line.startswith("-") and not line.startswith("---")
]
added = [
    line[1:] for line in diff
    if line.startswith("+") and not line.startswith("+++")
]
require(len(removed) == 1 and len(added) == 1, "ONE_LINE_DIFF_COUNT")
require(
    removed[0].strip()
    == 'replacement = (" " * statement.col_offset) + replacement_source',
    "ONE_LINE_DIFF_REMOVED",
)
require(
    added[0].strip() == "replacement = replacement_source",
    "ONE_LINE_DIFF_ADDED",
)

negative_source = negative.read_text(encoding="utf-8")
negative_tree = ast.parse(negative_source)
classes = [
    node for node in negative_tree.body
    if isinstance(node, ast.ClassDef)
    and node.name == "R1R1NegativeTests"
]
require(len(classes) == 1, "NEGATIVE_TEST_CLASS_COUNT")
test_class = classes[0]
helper = direct_class_method(test_class, "mutate_preflight_call")
helper_source = ast.get_source_segment(negative_source, helper)
require(helper_source is not None, "HELPER_SOURCE")
for token in (
    "statement.lineno",
    "statement.col_offset",
    "statement.end_lineno",
    "statement.end_col_offset",
    "actual_arg_names",
    "expected_arg_names",
    "compile(mutated",
):
    require(token in helper_source, f"HELPER_TOKEN:{token}")
require(helper_source.count("replacement = replacement_source") == 1,
        "HELPER_CORRECTED_LINE")
require('(" " * statement.col_offset) + replacement_source'
        not in helper_source, "HELPER_OLD_LINE")

test21 = direct_class_method(
    test_class,
    "test_21_wrapper_evidence_call_removed_rejected",
)
test26 = direct_class_method(
    test_class,
    "test_26_wrapper_protected_validation_call_removed_rejected",
)
test21_calls = self_method_calls(test21, "mutate_preflight_call")
test26_calls = self_method_calls(test26, "mutate_preflight_call")
require(len(test21_calls) == 1, "TEST21_CALL_COUNT")
require(len(test26_calls) == 1, "TEST26_CALL_COUNT")
require(
    isinstance(test21_calls[0].args[0], ast.Constant)
    and test21_calls[0].args[0].value == "validate_evidence_integrity",
    "TEST21_FUNCTION",
)
require(
    tuple_strings(keyword_value(
        test21_calls[0], "expected_arg_names"
    )) == ("evidence_root", "binding"),
    "TEST21_ARGS",
)
require(
    isinstance(test26_calls[0].args[0], ast.Constant)
    and test26_calls[0].args[0].value == "validate_protected_sha",
    "TEST26_FUNCTION",
)
require(
    tuple_strings(keyword_value(
        test26_calls[0], "expected_arg_names"
    )) == (),
    "TEST26_ARGS",
)
require(len(self_method_calls(test21, "assert_rejected")) == 1,
        "TEST21_REJECTION_ASSERTION")
require(len(self_method_calls(test26, "assert_rejected")) == 1,
        "TEST26_REJECTION_ASSERTION")

logs = source_packet / "validation-logs"
negative_log = (logs / "negative-tests.log").read_text(encoding="utf-8")
validator_log = (logs / "validator.log").read_text(encoding="utf-8")
visudo_log = (logs / "visudo.log").read_text(encoding="utf-8")
compile_log = (logs / "python-compile.log").read_text(encoding="utf-8")
require("Ran 40 tests" in negative_log, "NEGATIVE_TEST_COUNT")
require(any(line.strip() == "OK" for line in negative_log.splitlines()),
        "NEGATIVE_TEST_OK")
require("FAILED (" not in negative_log and "ERROR" not in negative_log,
        "NEGATIVE_TEST_FAILURE")
require("VALIDATION=PASS" in validator_log, "VALIDATOR_LOG")
require("VISUDO_VALIDATION=PASS" in visudo_log, "VISUDO_LOG")
require(
    "PYTHON_COMPILE_PASS=root_deployment_execution_once_r1.py"
    in compile_log,
    "WRAPPER_COMPILE_LOG",
)
require(
    "PYTHON_COMPILE_PASS=test_root_deployment_execution_packet_r1_negative.py"
    in compile_log,
    "NEGATIVE_COMPILE_LOG",
)

source_result = json_object(SOURCE / "result.json")
for key in (
    "root_deployment_execution_allowed",
    "sudoers_installation_allowed",
    "production_file_creation_allowed",
    "production_directory_creation_allowed",
    "root_helper_execution_allowed",
    "runner_execution_allowed",
    "one_shot_deployment_guard_created",
    "approval_binding_created",
    "sudoers_changed",
    "automatic_deployment_performed",
    "candidate_deployed_to_production",
    "corrected_wrapper_changed",
    "corrected_wrapper_executed",
    "validator_changed",
):
    require(source_result.get(key) is False, f"SOURCE_RESULT_FLAG:{key}")
require(source_result.get("negative_test_count") == 40,
        "SOURCE_RESULT_NEGATIVE_COUNT")
require(source_result.get("negative_tests") == "PASS",
        "SOURCE_RESULT_NEGATIVE_PASS")
require(source_result.get("validator") == "PASS",
        "SOURCE_RESULT_VALIDATOR")
require(source_result.get("visudo_static_validation") == "PASS",
        "SOURCE_RESULT_VISUDO")
require(source_result.get("corrected_test_ids") == [21, 26],
        "SOURCE_RESULT_TEST_IDS")
require(source_result.get("changed_line_count") == 1,
        "SOURCE_RESULT_CHANGED_LINES")
require(source_result.get("writer_freeze_execution") == "HOLD",
        "SOURCE_RESULT_FREEZE")
require(source_result.get("production_release_decision") == "HOLD",
        "SOURCE_RESULT_RELEASE")
require(source_result.get("release_status") == "CANDIDATE_NOT_APPROVED",
        "SOURCE_RESULT_STATUS")

for relative, expected in PROTECTED_SHA.items():
    path = REPO / relative
    require(path.is_file(), f"PROTECTED_MISSING:{relative}")
    require(sha256(path) == expected, f"PROTECTED_SHA:{relative}")

require(not list(SOURCE.rglob("*.pyc")), "SOURCE_BYTECODE_SIDE_EFFECT")

tree_sha, inventory_entries = inventory(SOURCE)

os.mkdir(PACKET, 0o750)

source_inventory = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_evidence_root": SOURCE.relative_to(REPO).as_posix(),
    "source_file_count": 245,
    "source_directory_count_excluding_root": 46,
    "source_symlink_count": 0,
    "source_nonregular_count": 0,
    "source_tree_identity_sha256": tree_sha,
    "files": inventory_entries,
}
write_exclusive(
    PACKET / "source-inventory.json",
    (json.dumps(source_inventory, sort_keys=True, indent=2) + "\n").encode(),
)

source_verification = {
    "schema_version": "1.0",
    "phase": PHASE,
    "source_fixed_sha": EXPECTED_FIXED_SHA,
    "evidence_exact_file_set": "PASS",
    "evidence_manifest_entry_count": 244,
    "evidence_manifest_exact_set": "PASS",
    "evidence_manifest_content_revalidation": "PASS",
    "packet_file_count": 243,
    "packet_directory_count": 45,
    "packet_manifest_entry_count": 242,
    "packet_manifest_exact_set": "PASS",
    "packet_manifest_content_revalidation": "PASS",
    "candidate_artifact_count": 18,
    "candidate_manifest_entry_count": 17,
    "candidate_manifest_exact_set": "PASS",
    "candidate_manifest_content_revalidation": "PASS",
    "source_snapshot_file_count": 150,
    "source_snapshot_directory_count": 29,
    "validator_target_file_count": 65,
    "validator_target_directory_count": 12,
    "negative_test_count": 40,
    "negative_tests_log": "PASS",
    "validator_log": "PASS",
    "visudo_static_validation_log": "PASS",
    "python_compile_log": "PASS",
    "one_line_negative_test_change_review": "PASS",
    "test_21_ast_selector_review": "PASS",
    "test_26_ast_selector_review": "PASS",
    "corrected_wrapper_sha256": WRAPPER_SHA,
    "corrected_wrapper_changed": False,
    "corrected_wrapper_executed": False,
    "validator_sha256": VALIDATOR_SHA,
    "validator_changed": False,
    "corrected_negative_test_sha256": CORRECTED_NEGATIVE_SHA,
    "protected_sha_unchanged": True,
    "bytecode_side_effect": False,
}
write_exclusive(
    PACKET / "source-verification.json",
    (json.dumps(source_verification, sort_keys=True, indent=2) + "\n").encode(),
)

reviewer_correction = {
    "schema_version": "1.0",
    "phase": PHASE,
    "initial_reviewer_result": "INCOMPLETE_REVIEWER_AST_SCOPE_ERROR",
    "initial_reviewer_error": "MUTATE_PREFLIGHT_CALL_FUNCTION_COUNT",
    "packet_defect_detected": False,
    "correction": (
        "R1R1NegativeTests class direct method "
        "mutate_preflight_call exact-one search"
    ),
    "reviewer_ast_scope_correction":
        "R1R1_NEGATIVE_TESTS_CLASS_METHOD_EXACT_ONE",
    "corrected_review_result": "PASS",
    "corrected_human_review_exit_code": 0,
}
write_exclusive(
    PACKET / "reviewer-ast-scope-correction.json",
    (json.dumps(reviewer_correction, sort_keys=True, indent=2) + "\n").encode(),
)

seal_contract = {
    "schema_version": "1.0",
    "phase": PHASE,
    "staging_required": True,
    "file_mode_after_seal": "0444",
    "directory_mode_after_seal": "0555",
    "final_promotion": "renameat2(RENAME_NOREPLACE)",
    "source_evidence_mutation_allowed": False,
    "root_deployment_execution_allowed": False,
    "production_release_decision": "HOLD",
}
write_exclusive(
    PACKET / "seal-contract.json",
    (json.dumps(seal_contract, sort_keys=True, indent=2) + "\n").encode(),
)

write_exclusive(PACKET / "human-approval-verbatim.txt", APPROVAL_TEXT)
write_exclusive(PACKET / "human-review-result-verbatim.txt",
                REVIEW_RESULT_TEXT)
write_exclusive(PACKET / "operation-manual.md", MANUAL_TEXT)
write_exclusive(PACKET / "review-contract.json", CONTRACT_BYTES)

review_result = {
    "schema_version": "1.0",
    "phase": PHASE,
    "result": (
        "PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
        "R1_R2_R2_HUMAN_REVIEW_RESULT_REGISTERED_AND_SEALED_NO_EXECUTION"
    ),
    "evidence_root": FINAL_REL,
    "source_evidence_root": SOURCE.relative_to(REPO).as_posix(),
    "human_review_result": "PASS",
    "corrected_human_review_exit_code": 0,
    "reviewer_ast_scope_correction":
        "R1R1_NEGATIVE_TESTS_CLASS_METHOD_EXACT_ONE",
    "initial_reviewer_error_was_packet_defect": False,
    "source_file_count": 245,
    "source_directory_count_excluding_root": 46,
    "source_tree_identity_sha256": tree_sha,
    "source_fixed_sha": EXPECTED_FIXED_SHA,
    "evidence_manifest_revalidation": "PASS",
    "packet_manifest_revalidation": "PASS",
    "candidate_manifest_revalidation": "PASS",
    "source_snapshot_review": "PASS",
    "validator_target_review": "PASS",
    "negative_test_40_pass_log_review": "PASS",
    "validator_pass_log_review": "PASS",
    "visudo_pass_log_review": "PASS",
    "one_line_negative_test_change_review": "PASS",
    "test_21_ast_selector_review": "PASS",
    "test_26_ast_selector_review": "PASS",
    "protected_sha_unchanged": True,
    "bytecode_side_effect": False,
    "human_review_result_registration_only": True,
    "sealed": True,
    "seal_file_mode": "0444",
    "seal_directory_mode": "0555",
    "root_deployment_execution_allowed": False,
    "sudoers_installation_allowed": False,
    "corrected_wrapper_execution_allowed": False,
    "approval_binding_created": False,
    "one_shot_deployment_guard_created": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": (
        "HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
        "R1_R2_R2_HUMAN_REVIEW_RESULT_SEAL_READONLY"
    ),
}
write_exclusive(
    STAGING / "review-result.json",
    (json.dumps(review_result, sort_keys=True, indent=2) + "\n").encode(),
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
    "status": "HUMAN_REVIEW_RESULT_REGISTERED_AND_SEALED_NO_EXECUTION",
    "packet_file_count_excluding_manifest": len(packet_entries),
    "packet_files": packet_entries,
    "source_evidence_file_count": 245,
    "source_evidence_directory_count_excluding_root": 46,
    "human_review_result": "PASS",
    "sealed": True,
    "root_deployment_execution_allowed": False,
    "production_release_decision": "HOLD",
}
write_exclusive(
    PACKET / "packet-manifest.json",
    (json.dumps(packet_manifest, sort_keys=True, indent=2) + "\n").encode(),
)

evidence_lines: list[str] = []
for path in sorted(STAGING.rglob("*")):
    if path.is_file():
        relative = path.relative_to(STAGING).as_posix()
        if relative != "evidence-manifest.txt":
            evidence_lines.append(f"{sha256(path)}  {relative}")
write_exclusive(
    STAGING / "evidence-manifest.txt",
    ("\n".join(evidence_lines) + "\n").encode(),
)

staging_files, staging_dirs, staging_links, staging_other = scan(STAGING)
require(staging_links == 0 and staging_other == 0, "STAGING_SPECIAL")
require(len(staging_files) == 11, f"STAGING_FILE_COUNT:{len(staging_files)}")
require(len(staging_dirs) == 1, f"STAGING_DIR_COUNT:{len(staging_dirs)}")
require(len(packet_entries) == 8, f"PACKET_ENTRY_COUNT:{len(packet_entries)}")
require(len(evidence_lines) == 10,
        f"EVIDENCE_ENTRY_COUNT:{len(evidence_lines)}")

# Revalidate new manifests before sealing.
new_packet_manifest = json_object(PACKET / "packet-manifest.json")
new_packet_entries = manifest_entries(new_packet_manifest)
require(len(new_packet_entries) == 8, "NEW_PACKET_MANIFEST_COUNT")
for entry in new_packet_entries:
    relative = entry["name"]
    path = PACKET / relative
    require(path.is_file(), f"NEW_PACKET_FILE:{relative}")
    require(entry["sha256"] == sha256(path),
            f"NEW_PACKET_SHA:{relative}")
    require(entry["size_bytes"] == path.stat().st_size,
            f"NEW_PACKET_SIZE:{relative}")

new_evidence_map: dict[str, str] = {}
for raw in (STAGING / "evidence-manifest.txt").read_text(
    encoding="utf-8"
).splitlines():
    digest, relative = raw.split("  ", 1)
    new_evidence_map[relative] = digest
require(len(new_evidence_map) == 10, "NEW_EVIDENCE_MANIFEST_COUNT")
require(set(new_evidence_map) == staging_files - {"evidence-manifest.txt"},
        "NEW_EVIDENCE_MANIFEST_SET")
for relative, expected in new_evidence_map.items():
    require(sha256(STAGING / relative) == expected,
            f"NEW_EVIDENCE_SHA:{relative}")

require(identity(SOURCE) == source_identity_before, "SOURCE_CHANGED_PRE_SEAL")

# Seal the complete staging tree.
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
                f"SEALED_FILE_MODE:{path}")
    elif stat.S_ISDIR(item.st_mode):
        require(stat.S_IMODE(item.st_mode) == 0o555,
                f"SEALED_DIR_MODE:{path}")
    else:
        raise AssertionError(f"SEALED_SPECIAL:{path}")
require(stat.S_IMODE(STAGING.lstat().st_mode) == 0o555,
        "SEALED_ROOT_MODE")

require(identity(SOURCE) == source_identity_before, "SOURCE_CHANGED_POST_SEAL")
for relative, expected in PROTECTED_SHA.items():
    require(sha256(REPO / relative) == expected,
            f"PROTECTED_CHANGED:{relative}")

rename_noreplace(STAGING, FINAL)

final_resolved = FINAL.resolve(strict=True)
require(final_resolved == FINAL, "FINAL_RESOLUTION")
require(stat.S_IMODE(FINAL.lstat().st_mode) == 0o555,
        "FINAL_ROOT_MODE")

final_files, final_dirs, final_links, final_other = scan(FINAL)
require(len(final_files) == 11, "FINAL_FILE_COUNT")
require(len(final_dirs) == 1, "FINAL_DIR_COUNT")
require(final_links == 0 and final_other == 0, "FINAL_SPECIAL")

print(
    "RESULT=PASS_W2B_I2F3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
    "R1_R2_R2_HUMAN_REVIEW_RESULT_REGISTERED_AND_SEALED_NO_EXECUTION"
)
print(f"EVIDENCE_ROOT={FINAL_REL}")
print("SOURCE_EVIDENCE_FILE_COUNT=245")
print("SOURCE_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=46")
print(f"SOURCE_TREE_IDENTITY_SHA256={tree_sha}")
print("SOURCE_EVIDENCE_UNCHANGED=true")
print("SOURCE_FIXED_SHA_REVALIDATION=PASS")
print("SOURCE_EVIDENCE_MANIFEST_REVALIDATION=PASS")
print("SOURCE_PACKET_MANIFEST_REVALIDATION=PASS")
print("SOURCE_CANDIDATE_MANIFEST_REVALIDATION=PASS")
print("HUMAN_REVIEW_RESULT=PASS")
print("CORRECTED_HUMAN_REVIEW_EXIT_CODE=0")
print(
    "REVIEWER_AST_SCOPE_CORRECTION="
    "R1R1_NEGATIVE_TESTS_CLASS_METHOD_EXACT_ONE"
)
print("INITIAL_REVIEWER_ERROR_WAS_PACKET_DEFECT=false")
print("NEW_EVIDENCE_FILE_COUNT=11")
print("NEW_EVIDENCE_DIRECTORY_COUNT_EXCLUDING_ROOT=1")
print("NEW_PACKET_MANIFEST_ENTRY_COUNT=8")
print("NEW_EVIDENCE_MANIFEST_ENTRY_COUNT=10")
print("SEALED_FILE_MODE=0444")
print("SEALED_DIRECTORY_MODE=0555")
print("SEAL_VALIDATION=PASS")
print("FINAL_PROMOTION=RENAMEAT2_RENAME_NOREPLACE")
print("HUMAN_REVIEW_RESULT_REGISTRATION_ONLY=true")
print("ROOT_DEPLOYMENT_EXECUTION_ALLOWED=false")
print("SUDOERS_INSTALLATION_ALLOWED=false")
print("CORRECTED_WRAPPER_EXECUTION_ALLOWED=false")
print("APPROVAL_BINDING_CREATED=false")
print("ONE_SHOT_DEPLOYMENT_GUARD_CREATED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print(
    "NEXT_GATE=HUMAN_REVIEW_3E_J_ROOT_DEPLOYMENT_EXECUTION_PACKET_"
    "R1_R2_R2_HUMAN_REVIEW_RESULT_SEAL_READONLY"
)
print(f"REVIEW_RESULT_SHA={sha256(FINAL / 'review-result.json')}")
print(f"PACKET_MANIFEST_SHA={sha256(FINAL / 'packet-snapshot/packet-manifest.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(FINAL / 'evidence-manifest.txt')}")

PY

echo "SCRIPT_EXIT_CODE=0"
