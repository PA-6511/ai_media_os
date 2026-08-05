from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "AUTHENTICITY-GATE"
)

EXPECTED_SOURCE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "SOURCE-DETAIL"
)

EXPECTED_SOURCE_STATUS = (
    "PASS_PRODUCTION_SOURCE_DETAIL_"
    "READY_NO_EXECUTION"
)

SYNTHETIC_TITLE_TOKENS = (
    "sample",
    "test",
    "dummy",
    "demo",
    "fixture",
    "サンプル",
    "テスト",
    "ダミー",
    "デモ",
    "検証用",
    "動作確認",
)

PLACEHOLDER_HOSTS = {
    "example.com",
    "www.example.com",
    "example.org",
    "www.example.org",
    "example.net",
    "www.example.net",
    "localhost",
    "127.0.0.1",
    "::1",
}

NON_RETAIL_STORE_TOKENS = (
    "catalog",
    "source",
    "import",
    "discovery",
)

AUTHENTIC_SOURCE_STATE = (
    "AUTHENTIC_SOURCE_NOT_DRAFT_READY"
)

DRAFT_READY_STATE = (
    "AUTHENTIC_SOURCE_AND_WORDPRESS_DRAFT_READY"
)

SYNTHETIC_STATE = (
    "SYNTHETIC_OR_PLACEHOLDER_SOURCE"
)


class XR11CandidateAuthenticityError(
    RuntimeError
):
    """Raised when authenticity-gate validation fails."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11CandidateAuthenticityError(
            message
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"source detail is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise XR11CandidateAuthenticityError(
            f"source detail JSON is invalid: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        "source detail must be a JSON object",
    )

    return value


def is_positive_integer(
    value: Any,
) -> bool:
    try:
        return int(str(value).strip()) > 0
    except (
        TypeError,
        ValueError,
    ):
        return False


def is_excluded(
    value: Any,
) -> bool:
    return value in {
        True,
        1,
        "1",
        "true",
        "TRUE",
        "True",
    }


def title_is_synthetic(
    title: Any,
) -> bool:
    normalized = str(
        title or ""
    ).strip().lower()

    if not normalized:
        return True

    return any(
        token in normalized
        for token in SYNTHETIC_TITLE_TOKENS
    )


def assess_store_offer(
    offer: dict[str, Any],
) -> dict[str, Any]:
    store = str(
        offer.get("store") or ""
    ).strip()

    raw_url = str(
        offer.get("url") or ""
    ).strip()

    blockers: list[str] = []

    if not store:
        blockers.append(
            "STORE_NAME_MISSING"
        )
    elif any(
        token in store.lower()
        for token in NON_RETAIL_STORE_TOKENS
    ):
        blockers.append(
            "NON_RETAIL_STORE_SOURCE"
        )

    if not raw_url:
        blockers.append(
            "STORE_URL_MISSING"
        )
        parsed_host = ""
    else:
        parsed = urlparse(raw_url)
        parsed_host = (
            parsed.hostname or ""
        ).lower()

        if parsed.scheme not in {
            "http",
            "https",
        }:
            blockers.append(
                "STORE_URL_SCHEME_INVALID"
            )

        if not parsed_host:
            blockers.append(
                "STORE_URL_HOST_MISSING"
            )
        elif parsed_host in PLACEHOLDER_HOSTS:
            blockers.append(
                "PLACEHOLDER_STORE_URL"
            )

    return {
        "store": store or None,
        "url": raw_url or None,
        "host": parsed_host or None,
        "valid_retail_offer": (
            not blockers
        ),
        "blockers": blockers,
    }


def assess_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    authenticity_blockers: list[str] = []
    readiness_blockers: list[str] = []

    title = candidate.get("title")
    release_date = candidate.get(
        "release_date"
    )

    if title_is_synthetic(title):
        authenticity_blockers.append(
            "SYNTHETIC_OR_MISSING_TITLE"
        )

    if release_date in (
        None,
        "",
    ):
        authenticity_blockers.append(
            "RELEASE_DATE_MISSING"
        )

    offer_assessments = [
        assess_store_offer(offer)
        for offer in candidate.get(
            "store_offers",
            [],
        )
        if isinstance(offer, dict)
    ]

    valid_offer_count = sum(
        1
        for offer in offer_assessments
        if offer["valid_retail_offer"]
    )

    if valid_offer_count == 0:
        authenticity_blockers.append(
            "NO_VALID_RETAIL_STORE_OFFER"
        )

    if is_excluded(
        candidate.get("excluded")
    ):
        authenticity_blockers.append(
            "CANDIDATE_EXCLUDED"
        )

    wordpress_post_id = candidate.get(
        "wordpress_post_id"
    )
    wordpress_status = candidate.get(
        "wordpress_status"
    )

    if not is_positive_integer(
        wordpress_post_id
    ):
        readiness_blockers.append(
            "WORDPRESS_POST_ID_MISSING_OR_INVALID"
        )

    if wordpress_status != "DRAFT":
        readiness_blockers.append(
            "WORDPRESS_STATUS_NOT_DRAFT"
        )

    source_authentic = (
        not authenticity_blockers
    )

    wordpress_draft_ready = (
        source_authentic
        and not readiness_blockers
    )

    if wordpress_draft_ready:
        classification = DRAFT_READY_STATE
    elif source_authentic:
        classification = AUTHENTIC_SOURCE_STATE
    else:
        classification = SYNTHETIC_STATE

    return {
        "ebook_item_id": candidate.get(
            "ebook_item_id"
        ),
        "title": title,
        "release_date": release_date,
        "wordpress_post_id": (
            wordpress_post_id
        ),
        "wordpress_status": (
            wordpress_status
        ),
        "excluded": candidate.get(
            "excluded"
        ),
        "classification": classification,
        "source_authentic": (
            source_authentic
        ),
        "wordpress_draft_ready": (
            wordpress_draft_ready
        ),
        "valid_retail_offer_count": (
            valid_offer_count
        ),
        "store_offer_assessments": (
            offer_assessments
        ),
        "authenticity_blockers": (
            authenticity_blockers
        ),
        "readiness_blockers": (
            readiness_blockers
        ),
    }


def run_authenticity_gate(
    *,
    source_detail_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    source_detail_path = (
        source_detail_path.resolve()
    )
    output_root = output_root.resolve()

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    source_detail = load_json_object(
        source_detail_path
    )

    require(
        source_detail.get("phase")
        == EXPECTED_SOURCE_PHASE,
        "source detail phase is invalid",
    )
    require(
        source_detail.get("status")
        == EXPECTED_SOURCE_STATUS,
        "source detail status is invalid",
    )
    require(
        source_detail.get(
            "database_scope"
        )
        == "PRODUCTION_READ_ONLY",
        (
            "source detail database scope "
            "must be PRODUCTION_READ_ONLY"
        ),
    )
    require(
        source_detail.get(
            "source_database_unchanged"
        )
        is True,
        (
            "source detail must confirm "
            "unchanged production database"
        ),
    )
    require(
        source_detail.get(
            "database_write"
        )
        is False,
        (
            "source detail database_write "
            "must be false"
        ),
    )
    require(
        source_detail.get(
            "production_status"
        )
        == "NO_GO",
        (
            "source detail production_status "
            "must remain NO_GO"
        ),
    )

    candidates = source_detail.get(
        "candidate_details"
    )

    require(
        isinstance(candidates, list),
        (
            "source detail candidate_details "
            "must be a list"
        ),
    )

    assessments = [
        assess_candidate(candidate)
        for candidate in candidates
        if isinstance(candidate, dict)
    ]

    authentic_candidates = [
        candidate
        for candidate in assessments
        if candidate["source_authentic"]
    ]

    draft_ready_candidates = [
        candidate
        for candidate in assessments
        if candidate[
            "wordpress_draft_ready"
        ]
    ]

    if not authentic_candidates:
        status = (
            "PASS_AUTHENTICITY_GATE_"
            "NO_AUTHENTIC_PRODUCTION_CANDIDATE"
        )
        gate_state = (
            "NO_AUTHENTIC_PRODUCTION_SOURCE"
        )
        authorized_next_phase = (
            "REAL_SOURCE_IMPORT_AND_"
            "WORDPRESS_DRAFT_PREPARATION"
        )
    elif not draft_ready_candidates:
        status = (
            "PASS_AUTHENTICITY_GATE_"
            "AUTHENTIC_SOURCE_NOT_DRAFT_READY"
        )
        gate_state = (
            "AUTHENTIC_SOURCE_REQUIRES_"
            "WORDPRESS_DRAFT"
        )
        authorized_next_phase = (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-DRAFT-PREP"
        )
    elif len(draft_ready_candidates) == 1:
        status = (
            "PASS_AUTHENTICITY_GATE_"
            "ONE_DRAFT_READY_CANDIDATE_"
            "HUMAN_REVIEW_REQUIRED"
        )
        gate_state = (
            "ONE_DRAFT_READY_CANDIDATE_"
            "NOT_SELECTED"
        )
        authorized_next_phase = (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "HUMAN-SELECTION"
        )
    else:
        status = (
            "BLOCKED_MULTIPLE_AUTHENTIC_"
            "DRAFT_READY_CANDIDATES"
        )
        gate_state = (
            "MULTIPLE_DRAFT_READY_CANDIDATES_"
            "NO_AUTOMATIC_SELECTION"
        )
        authorized_next_phase = None

    source_detail_sha = sha256_file(
        source_detail_path
    )

    pack_payload = {
        "phase": PHASE,
        "status": (
            "PRODUCTION_CANDIDATE_"
            "AUTHENTICITY_PACK_READY"
        ),
        "gate_state": gate_state,
        "source_detail_path": str(
            source_detail_path
        ),
        "source_detail_sha256": (
            source_detail_sha
        ),
        "candidate_count": len(
            assessments
        ),
        "authentic_candidate_count": len(
            authentic_candidates
        ),
        "wordpress_draft_ready_candidate_count": (
            len(draft_ready_candidates)
        ),
        "candidate_assessments": (
            assessments
        ),
        "candidate_selected": False,
        "automatic_selection_allowed": False,
        "human_selection_required": (
            len(draft_ready_candidates) == 1
        ),
        "approval_request_creation_allowed": (
            False
        ),
        "workflow_update_allowed": False,
        "wordpress_write_allowed": False,
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CANDIDATE_"
            "AUTHENTICITY_GATE_ONLY"
        ),
    }

    pack_digest = canonical_digest(
        pack_payload
    )

    pack = {
        **pack_payload,
        "authenticity_pack_digest_sha256": (
            pack_digest
        ),
    }

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    pack_path = (
        output_root
        / (
            "x_r11_production_candidate_1_"
            "authenticity_pack.json"
        )
    )
    result_path = (
        output_root
        / (
            "x_r11_production_candidate_1_"
            "authenticity_result.json"
        )
    )

    atomic_write_json(
        pack_path,
        pack,
    )

    result = {
        "phase": PHASE,
        "status": status,
        "gate_state": gate_state,
        "source_detail_path": str(
            source_detail_path
        ),
        "source_detail_sha256": (
            source_detail_sha
        ),
        "candidate_count": len(
            assessments
        ),
        "authentic_candidate_count": len(
            authentic_candidates
        ),
        "wordpress_draft_ready_candidate_count": (
            len(draft_ready_candidates)
        ),
        "authenticity_pack_path": str(
            pack_path
        ),
        "authenticity_pack_digest_sha256": (
            pack_digest
        ),
        "candidate_selected": False,
        "automatic_selection_allowed": False,
        "approval_request_created": False,
        "workflow_updated": False,
        "wordpress_draft_created": False,
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CANDIDATE_"
            "AUTHENTICITY_GATE_ONLY"
        ),
    }

    atomic_write_json(
        result_path,
        result,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-detail",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_authenticity_gate(
            source_detail_path=(
                args.source_detail
            ),
            output_root=args.output_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "candidate_selected": False,
                    "approval_request_created": False,
                    "database_write": False,
                    "wordpress_write": False,
                    "normal_x_fb_write_allowed": False,
                    "production_execution": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
