#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

REPO_ROOT="/home/deploy/ai_media_os"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
SOURCE_REL="${BASE_REL}/i2f3e-j-r2-r6-negative-test-log-marker-correction-20260725T170657Z-517926"
SOURCE_ROOT="${REPO_ROOT}/${SOURCE_REL}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_REL="${BASE_REL}/i2f3e-j-r2-r7-evidence-seal-correction-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "RUN_AS_ROOT_FORBIDDEN=true" >&2
  exit 1
fi

test -x "$PYTHON_BIN"
test -d "$SOURCE_ROOT"
cd "$REPO_ROOT"

"$PYTHON_BIN" - "$REPO_ROOT" "$SOURCE_ROOT" "$SOURCE_REL" "$EVIDENCE_ROOT" "$EVIDENCE_REL" <<'PY'
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

repo_root = Path(sys.argv[1]).resolve(strict=True)
source_root = Path(sys.argv[2]).resolve(strict=True)
source_rel = sys.argv[3]
evidence_root = Path(sys.argv[4])
evidence_rel = sys.argv[5]
snapshot_root = evidence_root / "source-r2-r6-snapshot"
phase = "TST-5D-W2B-I2F-3E-J-R2-R7"

approval_text = base64.b64decode(
    "5om/6KqN77yaCkpfUjJfUjZfUFJFUEFSQVRJT05fRVZJREVOQ0VfUkVWSUVXPVBBU1MKSl9SMl9SNl9QQUNLRVRfSU5URUdSSVRZX1JFVklFVz1QQVNTCkpfUjJfUjZfQ0FORElEQVRFX01BTklGRVNUX1JFVklFVz1QQVNTCkpfUjJfUjZfREVQTE9ZTUVOVF9DT05UUkFDVF9SRVZJRVc9UEFTUwpKX1IyX1I2X1NVRE9fQ09NTUFORF9DT05UUkFDVF9SRVZJRVc9UEFTUwpKX1IyX1I2X1ZBTElEQVRJT05fTE9HX1JFVklFVz1QQVNTCkpfUjJfUjZfUEVSTUlTU0lPTl9TQUZFX01FVEFEQVRBX1JFVklFVz1QQVNTCkpfUjJfUjZfRVhQRUNURURfUExBTk5FUl9CTE9DS19SRVZJRVc9UEFTUwpKX1IyX1I2X05FR0FUSVZFX1RFU1RfTE9HX1JFVklFVz1QQVNTCkVWSURFTkNFX01BTklGRVNUX0NPTlRFTlRfVkFMSUQ9dHJ1ZQpFVklERU5DRV9TRUFMX1JFVklFVz1GQUlMX1JFUVVJUkVTX1IyX1I3X1NFQUxfQ09SUkVDVElPTgpKX1IyX1I2X1JVTk5FUl9BUFBST1ZBTF9ERUNJU0lPTj1IT0xEX1BFTkRJTkdfRVZJREVOQ0VfU0VBTF9DT1JSRUNUSU9OCkFQUFJPVkVfM0VfSl9SMl9SN19FVklERU5DRV9TRUFMX0NPUlJFQ1RJT05fTk9fRVhFQ1VUSU9OCgroqLHlj6/nr4Tlm7LvvJoKMS4g5qyh44GuUjItUjYgRXZpZGVuY2XjgpLoqq3jgb/lj5bjgorlsILnlKjlhaXlipvjgajjgZfjgabkvb/nlKjjgZnjgovjgIIKICAgZXhjaGFuZ2UvcmV2aWV3X2V2aWRlbmNlL3NsYWNrX3dvcmtlcl9yZWxlYXNlX3JlYmluZGluZy8KICAgc2xhY2std29ya2VyLUNBTkRJREFURS1OT1QtQVBQUk9WRUQtMDFiYTg4MDlmMTMzLwogICB0c3QtNWQtdzJiLWkyZS1iYXNlbGluZS1hYnNvcnB0aW9uLXJlcmV2aWV3LTIwMjYwNzI1VDE0MTYzMi8KICAgaTJmM2Utai1yMi1yNi1uZWdhdGl2ZS10ZXN0LWxvZy1tYXJrZXItY29ycmVjdGlvbi0KICAgMjAyNjA3MjVUMTcwNjU3Wi01MTc5MjYKCjIuIFIyLVI2IEV2aWRlbmNl44Gu5pei5a2Y44OV44Kh44Kk44Or44CB44OH44Kj44Os44Kv44OI44Oq44CBCiAgIG93bmVy44CBZ3JvdXDjgIFtb2Rl44CBbXRpbWXjgIHlhoXlrrnjgpLlpInmm7TjgZfjgarjgYTjgIIKCjMuIFIyLVI244Gu5Zu65a6a5YCk44KS5a6f6KGM5YmN44Gr56K66KqN44GZ44KL44CCCiAgIFJFU1VMVF9TSEE9CiAgIGE2YWYyNzhlYjM4YjMxNTkwYjhkZmIzZmZjMDNhOGFiMDIyNzQxOWEyY2VlYTQ2NzU2MTY2MGIzYjBlOGFkZDAKCiAgIFBBQ0tFVF9NQU5JRkVTVF9TSEE9CiAgIDA2YzEwY2ZkYjdjODNjMDY5OWM3M2NhZWI3MjQ4ZDg0MjkwMjdlMjdjNmQ2OTZjNDM3YmFjMzhhYWQzZWFhNjYKCiAgIFBBQ0tFVF9TRU1BTlRJQ19WQUxJREFUSU9OX1NIQT0KICAgZGYwNDYzYWM1OWFmYzQ0ZDA2ZjAwYjE5MDgzNzZkZDRjNzA2ZGI0NzQ5MzYwMjk4OWU0ODMxZmFkZGM3ZmIyZgoKICAgRVZJREVOQ0VfTUFOSUZFU1RfU0hBPQogICAzNDdhMDAzMmJkNGI2OGRiNTMxNjYxMjQ5ZTEwODg2YzZjZTc5ZjJiM2RiNzBmYzE1NDEzZjg4YTBiYmU0ZDE2Cgo0LiBSMi1SNiBFdmlkZW5jZSBtYW5pZmVzdOOBrjMw44Ko44Oz44OI44Oq44Go44CBCiAgIG1hbmlmZXN05aSW44KS5ZCr44KA5YWoMzHjg5XjgqHjgqTjg6vjgpLlho3mpJzoqLzjgZnjgovjgIIKCjUuIFIyLVI244Gu54++5Zyo54q25oWL44KS6KiY6Yyy44GZ44KL44CCCiAgIGZpbGVfY291bnQ9MzEKICAgZGlyZWN0b3J5X2NvdW50PTkKICAgZmlsZV9tb2RlPTA2NDAKICAgZGlyZWN0b3J5X21vZGU9MDc1MAogICBzeW1saW5rX2NvdW50PTAKICAgb3duZXIvZ3JvdXA9ZGVwbG955YG0UmVwb3NpdG9yeeOBqOS4gOiHtAoKNi4g5paw44GX44GE5LiA5oSP44GqUjItUjcgRXZpZGVuY2Ugcm9vdOOCkuS9nOaIkOOBmeOCi+OAggoKNy4gUjItUjbjga7lhagzMeODleOCoeOCpOODq+OCkuOAgQogICBSMi1SN+WGheOBruWwgueUqHNuYXBzaG9044OH44Kj44Os44Kv44OI44Oq44G4CiAgIHJlbGF0aXZlIHBhdGjjgpLntq3mjIHjgZfjgabopIfoo73jgZnjgovjgIIKCjguIOikh+ijveOBq+OBr2V4Y2x1c2l2ZS1jcmVhdGXjgpLkvb/nlKjjgZfjgIEKICAg5pei5a2Y44OV44Kh44Kk44Or44Gu5LiK5pu444GN44KS56aB5q2i44GZ44KL44CCCgo5LiBzb3VyY2XjgahzbmFwc2hvdOOBruWQhOODleOCoeOCpOODq+OBq+OBpOOBhOOBpuOAgQogICBTSEEtMjU244Goc2l6ZeOBjOWujOWFqOS4gOiHtOOBmeOCi+OBk+OBqOOCkueiuuiqjeOBmeOCi+OAggoKMTAuIHN5bWxpbmvjgIFkZXZpY2XjgIFzb2NrZXTjgIFGSUZP44Gq44Gp44GuCiAgICByZWd1bGFyIGZpbGXvvI9kaXJlY3Rvcnnku6XlpJbjgpLmi5LlkKbjgZnjgovjgIIKCjExLiBSMi1SN+OBq+OBr+asoeOCkuS/neWtmOOBmeOCi+OAggogICAgLSBzb3VyY2UtcjItcjYtZml4ZWQtc2hhLmpzb24KICAgIC0gc291cmNlLXIyLXI2LW1vZGUtaW52ZW50b3J5Lmpzb24KICAgIC0gc25hcHNob3QtY29weS1tYW5pZmVzdC5qc29uCiAgICAtIHNlYWwtcG9saWN5Lmpzb24KICAgIC0gc2VhbC12YWxpZGF0aW9uLmpzb24KICAgIC0gcmVzdWx0Lmpzb24KICAgIC0gZXZpZGVuY2UtbWFuaWZlc3QudHh0CiAgICAtIGh1bWFuLWFwcHJvdmFsLXZlcmJhdGltLnR4dAoKMTIuIHNuYXBzaG90LWNvcHktbWFuaWZlc3Tjgavjga/jgIEKICAgIHNvdXJjZSByZWxhdGl2ZSBwYXRo44CBc25hcHNob3QgcmVsYXRpdmUgcGF0aOOAgQogICAgU0hBLTI1NuOAgXNpemXjgpLkv53lrZjjgZnjgovjgIIKCjEzLiBzZWFsLXBvbGljeeOBq+OBr+asoeOCkuWbuuWumuOBmeOCi+OAggogICAgZmlsZV9tb2RlPTA0NDQKICAgIGRpcmVjdG9yeV9tb2RlPTA1NTUKICAgIG93bmVyL2dyb3VwPWRlcGxveQogICAgc3ltbGlua19hbGxvd2VkPWZhbHNlCiAgICBjaG1vZF9zY29wZT1ORVdfUjJfUjdfRVZJREVOQ0VfUk9PVF9PTkxZCgoxNC4g5YWo5YaF5a6544GoZXZpZGVuY2UtbWFuaWZlc3TjgpLlrozmiJDjgZXjgZvjgIEKICAgIFNIQeODu3NpemXjg7tmaWxlIHNldOOCkuaknOiovOOBl+OBpuOBi+OCieWwgeWNsOOBmeOCi+OAggoKMTUuIFIyLVI35YaF44Gu5YWocmVndWxhciBmaWxl44KSMDQ0NOOBq+WkieabtOOBmeOCi+OAggoKMTYuIFIyLVI35YaF44Gu5YWoZGlyZWN0b3J544KS44CBCiAgICDmnIDmt7HlsaTjgYvjgonpoIbjgaswNTU144G45aSJ5pu044GZ44KL44CCCgoxNy4gY2htb2Tlr77osaHjgYxSMi1SNyBFdmlkZW5jZSByb2905aSW44G45Ye644Gq44GE44GT44Go44KS44CBCiAgICByZXNvbHZl5riI44G/cGF0aOOBp+aknOiovOOBmeOCi+OAggoKMTguIGNobW9k5b6M44Gr5qyh44KS5YaN5qSc6Ki844GZ44KL44CCCiAgICAtIOWFqGZpbGUgbW9kZT0wNDQ0CiAgICAtIOWFqGRpcmVjdG9yeSBtb2RlPTA1NTUKICAgIC0gb3duZXIvZ3JvdXDkuI3lpIkKICAgIC0gc3ltbGluayBjb3VudD0wCiAgICAtIHNvdXJjZS9zbmFwc2hvdCBTSEHkuIDoh7QKICAgIC0gZXZpZGVuY2UtbWFuaWZlc3TlhoXlrrnkuIDoh7QKCjE5LiBSMi1SNiBFdmlkZW5jZeOBrm1vZGXjgYzlrp/ooYzliY3lvozjgacKICAgIDA2NDAvMDc1MOOBruOBvuOBvuWkieWMluOBl+OBpuOBhOOBquOBhOOBk+OBqOOCkueiuuiqjeOBmeOCi+OAggoKMjAuIFByb2R1Y3Rpb27kv53orbflr77osaE244OV44Kh44Kk44Or44GuU0hB44KSCiAgICDlrp/ooYzliY3lvozjgafnorroqo3jgZnjgovjgIIKCjIxLiBSMi1SN+WujOS6huW+jOOCglJ1bm5lciBzdGF0dXPjgpIKICAgIEJMT0NLRURfVU5USUxfRVhQTElDSVRfRklOQUxfRVhFQ1VUSU9OX0FQUFJPVkFMCiAgICDjgavntq3mjIHjgZnjgovjgIIKCjIyLiBzdWRvZXJzIGRlc3RpbmF0aW9u44Gu54q25oWL44KSCiAgICBVTktOT1dOX1BFUk1JU1NJT05fREVOSUVE44Gu44G+44G+5L+d5oyB44GX44CBCiAgICBSRUFEWeOBuOaYh+agvOOBleOBm+OBquOBhOOAggoKMjMuIFIyLVI35a6M5LqG5b6M44Gv6Ieq5YuV55qE44Grcm9vdOeiuuiqjeOAgQogICAgUHJvZHVjdGlvbumFjee9ruOAgXN1ZG9lcnPlpInmm7TjgbjpgLLjgb7jgarjgYTjgIIKCuemgeatouS6i+mghe+8mgpSMi1SNiBFdmlkZW5jZeOBrmNobW9k44CBY2hvd27jgIHlhoXlrrnlpInmm7TjgIHliYrpmaTjgIEKcmVuYW1l44CB56e75YuV44CB5LiK5pu444GN44CBClByb2R1Y3Rpb24gYXJ0aWZhY3TphY3nva7jgIEvb3B06YWN5LiL5L2c5oiQ44CBCi9ldGMvc3Vkb2Vyc+OBvuOBn+OBry9ldGMvc3Vkb2Vycy5k5aSJ5pu044CBCnJvb3Tlrp/ooYzjgIFzdWRv5a6f6KGM44CBY2hvd27jgIFncm91cOWkieabtOOAgQpQcm9kdWN0aW9uIHByb2Nlc3Pjgbjjga5zaWduYWzpgIHkv6HjgIEKR1VJ5YGc5q2i44O75YaN6LW35YuV44CBd3JpdGVy5YGc5q2i44CBCmNyb250YWLlpInmm7TjgIF0aW1lcuWkieabtOOAgXN5c3RlbWN0bOaTjeS9nOOAgQpQcm9kdWN0aW9uIERC5o6l57aa44CBU1FM5a6f6KGM44CBClByb2R1Y3Rpb24gYmFja3Vw44CBcmVzdG9yZeOAgW1pZ3JhdGlvbuOAgQpQcm9kdWN0aW9uIG1hbmlmZXN05aSJ5pu044CBCmdpdCBhZGTjgIFnaXQgY29tbWl044CB5aSW6YOo6YCa5L+h44CBClNsYWNrIFdvcmtlcui1t+WLleOAgWZpbmFsIHRva2Vu55m66KGM44CBCmFwcHJvdmFsIGJpbmRpbmfnmbrooYzjgIFwcm9kdWN0aW9uIGFwcHJvdmFs44CBCnByb2R1Y3Rpb24gcmVsZWFzZeaJv+iqjeOBr+emgeatouOBmeOCi+OAggoK6L+95Yqg5p2h5Lu277yaCjEuIFIyLVI244Gu5Zu65a6aU0hB44GM5LiA6Ie044GX44Gq44GE5aC05ZCI44Gv5YGc5q2i44GZ44KL44CCCjIuIFIyLVI244Grc3ltbGlua+OBvuOBn+OBr+mdnnJlZ3VsYXIgZmlsZeOBjOOBguOCi+WgtOWQiOOBr+WBnOatouOBmeOCi+OAggozLiBzb3VyY2XjgahzbmFwc2hvdOOBrlNIQeOBvuOBn+OBr3NpemXjgYzkuIDoh7TjgZfjgarjgYTloLTlkIjjga/lgZzmraLjgZnjgovjgIIKNC4gUjItUjcgcm9vdOWkluOCkmNobW9k44GX44KI44GG44Go44GZ44KL5aC05ZCI44Gv5YGc5q2i44GZ44KL44CCCjUuIFIyLVI244GubW9kZeOBjOWkieWMluOBl+OBn+WgtOWQiOOBr0ZBSUzjgajjgZnjgovjgIIKNi4gUjItUjfjga5maWxl44GMMeS7tuOBp+OCgjA0NDTjgafjgarjgZHjgozjgbBGQUlM44Go44GZ44KL44CCCjcuIFIyLVI344GuZGlyZWN0b3J544GMMeS7tuOBp+OCgjA1NTXjgafjgarjgZHjgozjgbBGQUlM44Go44GZ44KL44CCCjguIFIyLVI35a6M5LqG5b6M44Gv5Lq66ZaT44Os44OT44Ol44O844KS5qyh44Ky44O844OI44Go44GZ44KL44CCCgpSVU5ORVJfU1RBVFVTPUJMT0NLRURfVU5USUxfRVhQTElDSVRfRklOQUxfRVhFQ1VUSU9OX0FQUFJPVkFMClNPVVJDRV9SMl9SNl9NVVRBVElPTl9BTExPV0VEPWZhbHNlClNPVVJDRV9SMl9SNl9DSE1PRF9BTExPV0VEPWZhbHNlCk5FV19SMl9SN19FVklERU5DRV9ST09UX1JFUVVJUkVEPXRydWUKU05BUFNIT1RfQllURV9FUVVJVkFMRU5DRV9SRVFVSVJFRD10cnVlCkVWSURFTkNFX0ZJTEVfTU9ERV9SRVFVSVJFRD0wNDQ0CkVWSURFTkNFX0RJUkVDVE9SWV9NT0RFX1JFUVVJUkVEPTA1NTUKRVZJREVOQ0VfU1lNTElOS19BTExPV0VEPWZhbHNlCkNITU9EX1NDT1BFPU5FV19SMl9SN19FVklERU5DRV9ST09UX09OTFkKU1VET0VSU19ERVNUSU5BVElPTl9FWElTVEVOQ0VfU1RBVEU9VU5LTk9XTl9QRVJNSVNTSU9OX0RFTklFRApERVBMT1lNRU5UX0FVVEhPUklaQVRJT05fUEFDS0VUX1NUQVRVUz1IT0xEX1BFTkRJTkdfQ09ORElUSU9OX1JFU09MVVRJT04KQ0FORElEQVRFX0RFUExPWUVEX1RPX1BST0RVQ1RJT049ZmFsc2UKU1VET0VSU19DSEFOR0VEPWZhbHNlCkZJTkFMX0FQUFJPVkFMX1RPS0VOX0NSRUFURUQ9ZmFsc2UKQVBQUk9WQUxfQklORElOR19DUkVBVEVEPWZhbHNlCldSSVRFUl9GUkVFWkVfRVhFQ1VUSU9OPUhPTEQKUFJPRFVDVElPTl9SRUxFQVNFX0RFQ0lTSU9OPUhPTEQKUkVMRUFTRV9TVEFUVVM9Q0FORElEQVRFX05PVF9BUFBST1ZFRA==",
    validate=True,
).decode("utf-8")

fixed_sha = {
    "result.json": "a6af278eb38b31590b8dfb3ffc03a8ab0227419a2ceea467561660b3b0e8add0",
    "packet-snapshot/packet-manifest.json": "06c10cfdb7c83c0699c73caeb7248d8429027e27c6d696c437bac38aad3eaa66",
    "packet-snapshot/packet-semantic-validation.json": "df0463ac59afc44d06f00b1908376dd4c706db47493602989e4831faddc7fb2f",
    "evidence-manifest.txt": "347a0032bd4b68db531661249e10886c6ce79f2b3db70fc15413f88a0bbe4d16",
}

protected_sha = {
    "data/database/ebook_affiliate.db": "1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9",
    "config/slack_worker_release_source_manifest.json": "ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d",
    "app/db/repositories/workflow_state_repository.py": "00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e",
    "migrations/versions/00241611109d_add_unique_wordpress_post_id.py": "e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a",
    "scripts/run_slack_approval_socket.py": "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6",
    "tests/test_slack_approval_socket_hold_remediation_offline.py": "86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72",
}


class SealError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SealError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def scan_tree(root: Path) -> tuple[list[Path], list[Path]]:
    item = root.lstat()
    require(stat.S_ISDIR(item.st_mode), f"ROOT_NOT_DIRECTORY:{root}")
    require(not stat.S_ISLNK(item.st_mode), f"ROOT_SYMLINK:{root}")

    files: list[Path] = []
    directories: list[Path] = [root]

    def walk(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            state = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(state.st_mode):
                raise SealError(f"SYMLINK_FORBIDDEN:{path}")
            if stat.S_ISDIR(state.st_mode):
                directories.append(path)
                walk(path)
            elif stat.S_ISREG(state.st_mode):
                files.append(path)
            else:
                raise SealError(f"NON_REGULAR_ENTRY_FORBIDDEN:{path}")

    walk(root)
    return sorted(files), sorted(directories)


def metadata(path: Path, root: Path) -> dict[str, Any]:
    state = path.lstat()
    relative = "." if path == root else path.relative_to(root).as_posix()
    value: dict[str, Any] = {
        "relative_path": relative,
        "uid": state.st_uid,
        "gid": state.st_gid,
        "mode": f"{stat.S_IMODE(state.st_mode):04o}",
        "mtime_ns": state.st_mtime_ns,
        "size_bytes": state.st_size,
        "is_regular_file": stat.S_ISREG(state.st_mode),
        "is_directory": stat.S_ISDIR(state.st_mode),
        "is_symlink": stat.S_ISLNK(state.st_mode),
    }
    if value["is_regular_file"]:
        value["sha256"] = sha256(path)
    return value


def tree_state(root: Path, files: list[Path], directories: list[Path]) -> dict[str, Any]:
    return {
        "file_count": len(files),
        "directory_count": len(directories),
        "symlink_count": 0,
        "files": [metadata(path, root) for path in files],
        "directories": [metadata(path, root) for path in directories],
    }


def mkdir_exclusive(path: Path, mode: int = 0o750) -> None:
    require(not path.exists(), f"DIRECTORY_EXISTS:{path}")
    require(not path.is_symlink(), f"DIRECTORY_SYMLINK:{path}")
    os.mkdir(path, mode)


def write_exclusive(path: Path, data: bytes, mode: int = 0o640) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
    )
    with os.fdopen(descriptor, "wb", closefd=True) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path: Path, value: Any) -> None:
    write_exclusive(
        path,
        (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8"),
    )


def ensure_inside(path: Path, root: Path) -> None:
    resolved_root = root.resolve(strict=True)
    resolved_path = path.resolve(strict=True)
    require(
        resolved_path == resolved_root or resolved_root in resolved_path.parents,
        f"CHMOD_PATH_OUTSIDE_R2_R7:{path}",
    )


def verify_protected() -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in protected_sha.items():
        path = repo_root / relative
        require(path.is_file(), f"PROTECTED_FILE_MISSING:{relative}")
        current = sha256(path)
        require(current == expected, f"PROTECTED_SHA_MISMATCH:{relative}")
        actual[relative] = current
    return actual


def verify_source_manifest(files: list[Path]) -> int:
    path = source_root / "evidence-manifest.txt"
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        require(relative not in entries, f"DUPLICATE_SOURCE_MANIFEST_ENTRY:{relative}")
        entries[relative] = expected

    actual = {
        item.relative_to(source_root).as_posix()
        for item in files
        if item != path
    }
    require(len(entries) == 30, "SOURCE_MANIFEST_ENTRY_COUNT_NOT_30")
    require(set(entries) == actual, "SOURCE_MANIFEST_FILE_SET_MISMATCH")
    for relative, expected in entries.items():
        require(sha256(source_root / relative) == expected, f"SOURCE_MANIFEST_SHA_MISMATCH:{relative}")
    return len(entries)


# Source checks before creating the R2-R7 root.
require(source_root == repo_root / source_rel, "SOURCE_PATH_BINDING_INVALID")
source_files, source_dirs = scan_tree(source_root)
require(len(source_files) == 31, "SOURCE_FILE_COUNT_NOT_31")
require(len(source_dirs) == 9, "SOURCE_DIRECTORY_COUNT_NOT_9")

repo_state = repo_root.stat()
uid = repo_state.st_uid
gid = repo_state.st_gid

for path in source_files:
    state = path.lstat()
    require(stat.S_IMODE(state.st_mode) == 0o640, f"SOURCE_FILE_MODE_NOT_0640:{path}")
    require(state.st_uid == uid and state.st_gid == gid, f"SOURCE_FILE_OWNER_INVALID:{path}")
for path in source_dirs:
    state = path.lstat()
    require(stat.S_IMODE(state.st_mode) == 0o750, f"SOURCE_DIR_MODE_NOT_0750:{path}")
    require(state.st_uid == uid and state.st_gid == gid, f"SOURCE_DIR_OWNER_INVALID:{path}")

for relative, expected in fixed_sha.items():
    require(sha256(source_root / relative) == expected, f"SOURCE_FIXED_SHA_MISMATCH:{relative}")

manifest_entry_count = verify_source_manifest(source_files)
source_before = tree_state(source_root, source_files, source_dirs)
source_before_sha = canonical_sha(source_before)
protected_before = verify_protected()

# New unique R2-R7 root only.
expected_parent = (repo_root / Path(evidence_rel).parent).resolve(strict=True)
require(evidence_root.parent.resolve(strict=True) == expected_parent, "EVIDENCE_PARENT_INVALID")
mkdir_exclusive(evidence_root)
mkdir_exclusive(snapshot_root)

for source_dir in sorted(source_dirs, key=lambda path: len(path.relative_to(source_root).parts)):
    if source_dir == source_root:
        continue
    relative = source_dir.relative_to(source_root)
    mkdir_exclusive(snapshot_root / relative)

copy_records: list[dict[str, Any]] = []
for source_path in source_files:
    relative = source_path.relative_to(source_root)
    destination = snapshot_root / relative
    source_hash = sha256(source_path)
    source_size = source_path.stat().st_size

    descriptor = os.open(
        destination,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o640,
    )
    with os.fdopen(descriptor, "wb", closefd=True) as target:
        with source_path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                target.write(block)
        target.flush()
        os.fsync(target.fileno())

    require(sha256(destination) == source_hash, f"SNAPSHOT_SHA_MISMATCH:{relative}")
    require(destination.stat().st_size == source_size, f"SNAPSHOT_SIZE_MISMATCH:{relative}")
    copy_records.append({
        "source_relative_path": relative.as_posix(),
        "snapshot_relative_path": (Path("source-r2-r6-snapshot") / relative).as_posix(),
        "sha256": source_hash,
        "size_bytes": source_size,
    })

write_json(evidence_root / "source-r2-r6-fixed-sha.json", {
    "schema_version": "1.0",
    "phase": phase,
    "source_evidence_root": source_rel,
    "source_fixed_sha256": fixed_sha,
    "source_manifest_entry_count": manifest_entry_count,
    "source_total_file_count": 31,
    "protected_production_sha256": protected_before,
    "source_r2_r6_mutation_allowed": False,
    "source_r2_r6_chmod_allowed": False,
})

write_json(evidence_root / "source-r2-r6-mode-inventory.json", {
    "schema_version": "1.0",
    "phase": phase,
    "source_state_sha256": source_before_sha,
    "expected_uid": uid,
    "expected_gid": gid,
    "file_count": 31,
    "directory_count": 9,
    "file_mode": "0640",
    "directory_mode": "0750",
    "symlink_count": 0,
    "state": source_before,
})

write_json(evidence_root / "snapshot-copy-manifest.json", {
    "schema_version": "1.0",
    "phase": phase,
    "copy_method": "O_EXCL_O_NOFOLLOW",
    "source_file_count": 31,
    "snapshot_file_count": 31,
    "sha256_and_size_equivalence_required": True,
    "records": copy_records,
})

write_json(evidence_root / "seal-policy.json", {
    "schema_version": "1.0",
    "phase": phase,
    "file_mode": "0444",
    "directory_mode": "0555",
    "owner_uid": uid,
    "group_gid": gid,
    "symlink_allowed": False,
    "chmod_scope": "NEW_R2_R7_EVIDENCE_ROOT_ONLY",
    "directory_chmod_order": "DEEPEST_FIRST",
    "source_r2_r6_mutation_allowed": False,
    "source_r2_r6_chmod_allowed": False,
    "runner_status": "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "sudoers_destination_existence_state": "UNKNOWN_PERMISSION_DENIED",
    "deployment_authorization_packet_status": "HOLD_PENDING_CONDITION_RESOLUTION",
})

write_exclusive(
    evidence_root / "human-approval-verbatim.txt",
    (approval_text + "\n").encode("utf-8"),
)

write_json(evidence_root / "seal-validation.json", {
    "schema_version": "1.0",
    "phase": phase,
    "recording_semantics": "PRECOMMITTED_BEFORE_SEAL",
    "valid_only_if_script_exit_code_zero": True,
    "required_runtime_markers": [
        "POST_SEAL_VALIDATION=PASS",
        "SOURCE_R2_R6_UNCHANGED=true",
        "PROTECTED_SHA_UNCHANGED=true",
        "EVIDENCE_MANIFEST_CONTENT_VALID=true",
        "SCRIPT_EXIT_CODE=0",
    ],
    "required_final_file_mode": "0444",
    "required_final_directory_mode": "0555",
    "required_final_symlink_count": 0,
    "source_snapshot_sha_and_size_equivalence": True,
    "source_r2_r6_must_remain_unchanged": True,
})

write_json(evidence_root / "result.json", {
    "schema_version": "1.0",
    "phase": phase,
    "result": "PASS_W2B_I2F3E_J_R2_R7_EVIDENCE_SEAL_CORRECTION_NO_EXECUTION",
    "recording_semantics": "PRECOMMITTED_BEFORE_SEAL",
    "valid_only_if_script_exit_code_zero": True,
    "evidence_root": evidence_rel,
    "source_evidence_root": source_rel,
    "source_file_count": 31,
    "source_directory_count": 9,
    "snapshot_file_count": 31,
    "evidence_file_mode_required": "0444",
    "evidence_directory_mode_required": "0555",
    "chmod_scope": "NEW_R2_R7_EVIDENCE_ROOT_ONLY",
    "runner_status": "BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL",
    "sudoers_destination_existence_state": "UNKNOWN_PERMISSION_DENIED",
    "deployment_authorization_packet_status": "HOLD_PENDING_CONDITION_RESOLUTION",
    "candidate_deployed_to_production": False,
    "sudoers_changed": False,
    "final_approval_token_created": False,
    "approval_binding_created": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_J_R2_R7_EVIDENCE_SEAL",
})

# Manifest before seal.
pre_files, pre_dirs = scan_tree(evidence_root)
require(len(pre_files) == 38, f"PRESEAL_FILE_COUNT_NOT_38:{len(pre_files)}")
require(len(pre_dirs) == 10, f"PRESEAL_DIR_COUNT_NOT_10:{len(pre_dirs)}")

manifest_path = evidence_root / "evidence-manifest.txt"
manifest_lines = [
    f"{sha256(path)}  {path.relative_to(evidence_root).as_posix()}"
    for path in pre_files
]
write_exclusive(manifest_path, ("\n".join(manifest_lines) + "\n").encode("utf-8"))

all_files, all_dirs = scan_tree(evidence_root)
require(len(all_files) == 39, f"FINAL_FILE_COUNT_NOT_39:{len(all_files)}")
require(len(all_dirs) == 10, f"FINAL_DIR_COUNT_NOT_10:{len(all_dirs)}")

manifest_entries: dict[str, str] = {}
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    require(relative not in manifest_entries, f"DUPLICATE_R2_R7_MANIFEST_ENTRY:{relative}")
    manifest_entries[relative] = expected
actual_manifest_set = {
    path.relative_to(evidence_root).as_posix()
    for path in all_files
    if path != manifest_path
}
require(len(manifest_entries) == 38, "R2_R7_MANIFEST_ENTRY_COUNT_NOT_38")
require(set(manifest_entries) == actual_manifest_set, "R2_R7_MANIFEST_SET_MISMATCH")
for relative, expected in manifest_entries.items():
    require(sha256(evidence_root / relative) == expected, f"R2_R7_MANIFEST_SHA_MISMATCH:{relative}")

# Byte equivalence before seal.
for record in copy_records:
    source_path = source_root / record["source_relative_path"]
    snapshot_path = evidence_root / record["snapshot_relative_path"]
    require(sha256(source_path) == record["sha256"], f"SOURCE_CHANGED_BEFORE_SEAL:{record['source_relative_path']}")
    require(sha256(snapshot_path) == record["sha256"], f"SNAPSHOT_CHANGED_BEFORE_SEAL:{record['snapshot_relative_path']}")
    require(source_path.stat().st_size == record["size_bytes"], f"SOURCE_SIZE_CHANGED_BEFORE_SEAL:{record['source_relative_path']}")
    require(snapshot_path.stat().st_size == record["size_bytes"], f"SNAPSHOT_SIZE_CHANGED_BEFORE_SEAL:{record['snapshot_relative_path']}")

# Seal only R2-R7.
for path in all_files:
    ensure_inside(path, evidence_root)
    os.chmod(path, 0o444, follow_symlinks=False)

for path in sorted(
    all_dirs,
    key=lambda item: len(item.relative_to(evidence_root).parts),
    reverse=True,
):
    ensure_inside(path, evidence_root)
    os.chmod(path, 0o555, follow_symlinks=False)

# Post-seal validation.
sealed_files, sealed_dirs = scan_tree(evidence_root)
require(len(sealed_files) == 39, "POST_SEAL_FILE_COUNT_NOT_39")
require(len(sealed_dirs) == 10, "POST_SEAL_DIR_COUNT_NOT_10")

for path in sealed_files:
    state = path.lstat()
    require(stat.S_IMODE(state.st_mode) == 0o444, f"POST_SEAL_FILE_MODE_INVALID:{path}")
    require(state.st_uid == uid and state.st_gid == gid, f"POST_SEAL_FILE_OWNER_CHANGED:{path}")
for path in sealed_dirs:
    state = path.lstat()
    require(stat.S_IMODE(state.st_mode) == 0o555, f"POST_SEAL_DIR_MODE_INVALID:{path}")
    require(state.st_uid == uid and state.st_gid == gid, f"POST_SEAL_DIR_OWNER_CHANGED:{path}")

post_manifest_entries: dict[str, str] = {}
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    require(relative not in post_manifest_entries, f"POST_SEAL_DUPLICATE_MANIFEST_ENTRY:{relative}")
    post_manifest_entries[relative] = expected
post_actual_set = {
    path.relative_to(evidence_root).as_posix()
    for path in sealed_files
    if path != manifest_path
}
require(set(post_manifest_entries) == post_actual_set, "POST_SEAL_MANIFEST_SET_MISMATCH")
for relative, expected in post_manifest_entries.items():
    require(sha256(evidence_root / relative) == expected, f"POST_SEAL_MANIFEST_SHA_MISMATCH:{relative}")

for record in copy_records:
    source_path = source_root / record["source_relative_path"]
    snapshot_path = evidence_root / record["snapshot_relative_path"]
    require(sha256(source_path) == record["sha256"], f"SOURCE_CHANGED_AFTER_SEAL:{record['source_relative_path']}")
    require(sha256(snapshot_path) == record["sha256"], f"SNAPSHOT_CHANGED_AFTER_SEAL:{record['snapshot_relative_path']}")
    require(source_path.stat().st_size == record["size_bytes"], f"SOURCE_SIZE_CHANGED_AFTER_SEAL:{record['source_relative_path']}")
    require(snapshot_path.stat().st_size == record["size_bytes"], f"SNAPSHOT_SIZE_CHANGED_AFTER_SEAL:{record['snapshot_relative_path']}")

source_files_after, source_dirs_after = scan_tree(source_root)
source_after = tree_state(source_root, source_files_after, source_dirs_after)
require(canonical_sha(source_after) == source_before_sha, "SOURCE_R2_R6_STATE_CHANGED")
require(source_after == source_before, "SOURCE_R2_R6_METADATA_CHANGED")

protected_after = verify_protected()
require(protected_after == protected_before, "PROTECTED_SHA_CHANGED")

for relative, expected in fixed_sha.items():
    require(sha256(source_root / relative) == expected, f"SOURCE_FIXED_SHA_CHANGED:{relative}")

print("RESULT=PASS_W2B_I2F3E_J_R2_R7_EVIDENCE_SEAL_CORRECTION_NO_EXECUTION")
print(f"EVIDENCE_ROOT={evidence_rel}")
print("SOURCE_R2_R6_FIXED_SHA_REVIEW=PASS")
print("SOURCE_R2_R6_MANIFEST_ENTRY_COUNT=30")
print("SOURCE_R2_R6_FILE_COUNT=31")
print("SOURCE_R2_R6_DIRECTORY_COUNT=9")
print("SOURCE_R2_R6_FILE_MODE=0640")
print("SOURCE_R2_R6_DIRECTORY_MODE=0750")
print("SOURCE_R2_R6_SYMLINK_COUNT=0")
print("SNAPSHOT_FILE_COUNT=31")
print("SNAPSHOT_BYTE_EQUIVALENCE=PASS")
print("SNAPSHOT_SIZE_EQUIVALENCE=PASS")
print("EXCLUSIVE_CREATE=PASS")
print("R2_R7_EVIDENCE_FILE_COUNT=39")
print("R2_R7_EVIDENCE_DIRECTORY_COUNT=10")
print("R2_R7_EVIDENCE_MANIFEST_ENTRY_COUNT=38")
print("R2_R7_EVIDENCE_FILE_MODE=0444")
print("R2_R7_EVIDENCE_DIRECTORY_MODE=0555")
print("R2_R7_EVIDENCE_SYMLINK_COUNT=0")
print("EVIDENCE_MANIFEST_CONTENT_VALID=true")
print("POST_SEAL_VALIDATION=PASS")
print("SOURCE_R2_R6_UNCHANGED=true")
print("SOURCE_R2_R6_MODE_UNCHANGED=true")
print("SOURCE_R2_R6_MTIME_UNCHANGED=true")
print("PROTECTED_SHA_UNCHANGED=true")
print("CHMOD_SCOPE=NEW_R2_R7_EVIDENCE_ROOT_ONLY")
print(f"RESULT_SHA={sha256(evidence_root / 'result.json')}")
print(f"SEAL_VALIDATION_SHA={sha256(evidence_root / 'seal-validation.json')}")
print(f"SNAPSHOT_COPY_MANIFEST_SHA={sha256(evidence_root / 'snapshot-copy-manifest.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(manifest_path)}")
print("RUNNER_STATUS=BLOCKED_UNTIL_EXPLICIT_FINAL_EXECUTION_APPROVAL")
print("SUDOERS_DESTINATION_EXISTENCE_STATE=UNKNOWN_PERMISSION_DENIED")
print("DEPLOYMENT_AUTHORIZATION_PACKET_STATUS=HOLD_PENDING_CONDITION_RESOLUTION")
print("CANDIDATE_DEPLOYED_TO_PRODUCTION=false")
print("PRODUCTION_DIRECTORY_CREATED=false")
print("PRODUCTION_FILE_CREATED=false")
print("SUDOERS_CHANGED=false")
print("FINAL_APPROVAL_TOKEN_CREATED=false")
print("APPROVAL_BINDING_CREATED=false")
print("PRODUCTION_PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("PRODUCTION_DB_SQL_CONNECTION_USED=false")
print("PRODUCTION_BACKUP_CREATED=false")
print("RESTORE_EXECUTED=false")
print("MIGRATION_EXECUTED=false")
print("PRODUCTION_MANIFEST_MODIFIED=false")
print("GIT_ADD_PERFORMED=false")
print("GIT_COMMIT_PERFORMED=false")
print("PRODUCTION_DEPLOYMENT_PERFORMED=false")
print("EXTERNAL_NETWORK_USED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print("NEXT_GATE=HUMAN_REVIEW_3E_J_R2_R7_EVIDENCE_SEAL")
print("SCRIPT_EXIT_CODE=0")
PY
