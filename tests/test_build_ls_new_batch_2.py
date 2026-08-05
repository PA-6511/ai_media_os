from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = ROOT / "config/new_release_verification_policy.json"
BATCH_PATH = (
    ROOT / "exchange/examples/"
    "new_release_batch_normalized.example.json"
)
REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "new_release_verification_request.example.json"
)
OUTPUT_PATH = (
    ROOT / "exchange/examples/"
    "new_release_verification_result.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_2_result.json"
REPORT_PATH = ROOT / "reports/ls_new_batch_2_verification_report.md"
SCRIPT_PATH = ROOT / "scripts/build_ls_new_batch_2.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_2_test_module",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_at() -> str:
    return "2026-07-10T12:00:00+09:00"


def found_store(
    name: str,
    *,
    price: int | None,
    image: bool = False,
    release_date: str = "2026-07-17",
    title: str = "サンプル作品",
    volume_label: str = "第1巻",
) -> dict:
    host = {
        "amazon": "amazon.test",
        "rakuten_kobo": "rakuten.test",
        "dmm": "dmm.test",
    }[name]

    return {
        "status": "FOUND",
        "checked_at": checked_at(),
        "url": f"https://{host}/product",
        "title": title,
        "volume_label": volume_label,
        "release_date": release_date,
        "price_jpy": price,
        "image_url": (
            f"https://{host}/cover.jpg"
            if image
            else None
        ),
    }


def not_found_store() -> dict:
    return {
        "status": "NOT_FOUND",
        "checked_at": checked_at(),
        "url": None,
        "title": None,
        "volume_label": None,
        "release_date": None,
        "price_jpy": None,
        "image_url": None,
    }


def checked_publisher(
    *,
    release_date: str = "2026-07-17",
    title: str = "サンプル作品",
    volume_label: str = "第1巻",
) -> dict:
    return {
        "status": "CHECKED",
        "checked_at": checked_at(),
        "url": "https://publisher.test/book",
        "title": title,
        "volume_label": volume_label,
        "release_date": release_date,
    }


def ready_request() -> dict:
    request = load_json(REQUEST_PATH)
    observation = request["observations"][0]

    observation["publisher_official"] = checked_publisher()
    observation["stores"] = {
        "amazon": found_store(
            "amazon",
            price=770,
        ),
        "rakuten_kobo": found_store(
            "rakuten_kobo",
            price=770,
            image=True,
        ),
        "dmm": not_found_store(),
    }

    return request


def classify(request: dict) -> tuple[str, dict]:
    module = load_module()
    policy = load_json(POLICY_PATH)
    batch = load_json(BATCH_PATH)

    output = module.build_verification_output(
        batch=batch,
        request=request,
        policy=policy,
    )

    item = output["items"][0]
    return item["verification_classification"], item


def run_builder(
    request_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--verification",
            str(request_path),
            "--check-only",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_policy_identity_and_safety_boundary() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-2"
    assert (
        policy["policy_id"]
        == "NEW_RELEASE_VERIFICATION_POLICY_V1"
    )
    assert boundary["external_api_call_allowed"] is False
    assert boundary["web_scraping_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["automatic_draft_creation_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "DRY_RUN_ONLY"


def test_example_is_classified_without_external_access() -> None:
    completed = run_builder(REQUEST_PATH)

    assert completed.returncode == 0

    result = json.loads(completed.stdout)

    assert (
        result["status"]
        == "PASS_VERIFICATION_BASELINE_NO_EXTERNAL_ACCESS"
    )
    assert result["classification_counts"] == {
        "NEEDS_RELEASE_DATE_CONFIRMATION": 1
    }
    assert result["external_api_call_allowed"] is False
    assert result["ready_for_ls_new_batch_3"] is True


def test_ready_for_draft_classification() -> None:
    status, item = classify(ready_request())

    assert status == "READY_FOR_DRAFT"
    assert (
        item["resolved_store_links"]["amazon"]
        == "https://amazon.test/product"
    )
    assert (
        item["resolved_image"]["source"]
        == "rakuten_kobo"
    )


def test_release_date_mismatch_requires_confirmation() -> None:
    request = ready_request()
    request["observations"][0]["stores"]["amazon"][
        "release_date"
    ] = "2026-07-18"

    status, item = classify(request)

    assert status == "NEEDS_RELEASE_DATE_CONFIRMATION"
    assert any(
        mismatch["field"] == "release_date"
        for mismatch in item["mismatches"]
    )


def test_title_mismatch_is_fact_mismatch() -> None:
    request = ready_request()
    request["observations"][0]["stores"]["amazon"][
        "title"
    ] = "別の作品"

    status, _ = classify(request)

    assert status == "FACT_MISMATCH"


def test_no_store_page_found() -> None:
    request = ready_request()
    request["observations"][0]["stores"] = {
        "amazon": not_found_store(),
        "rakuten_kobo": not_found_store(),
        "dmm": not_found_store(),
    }

    status, _ = classify(request)

    assert status == "STORE_PAGE_NOT_FOUND"


def test_missing_image_is_blocked() -> None:
    request = ready_request()

    for store in request["observations"][0][
        "stores"
    ].values():
        store["image_url"] = None

    status, _ = classify(request)

    assert status == "MISSING_IMAGE"


def test_partial_store_coverage_is_blocked() -> None:
    request = ready_request()
    request["observations"][0]["stores"] = {
        "amazon": found_store(
            "amazon",
            price=770,
            image=True,
        ),
        "rakuten_kobo": not_found_store(),
        "dmm": not_found_store(),
    }

    status, _ = classify(request)

    assert status == "PARTIAL_STORE_COVERAGE"


def test_missing_price_requires_confirmation() -> None:
    request = ready_request()
    request["observations"][0]["stores"] = {
        "amazon": found_store(
            "amazon",
            price=None,
        ),
        "rakuten_kobo": found_store(
            "rakuten_kobo",
            price=None,
            image=True,
        ),
        "dmm": not_found_store(),
    }

    status, _ = classify(request)

    assert status == "NEEDS_PRICE_CONFIRMATION"


def test_manual_exclusion_has_highest_precedence() -> None:
    request = ready_request()
    observation = request["observations"][0]

    observation["manual_exclusion"] = True
    observation["manual_exclusion_reason"] = (
        "対象カテゴリ外"
    )
    observation["cross_batch_duplicate_suspected"] = True

    status, _ = classify(request)

    assert status == "EXCLUDED"


def test_duplicate_suspicion_precedes_readiness() -> None:
    request = ready_request()
    request["observations"][0][
        "cross_batch_duplicate_suspected"
    ] = True

    status, _ = classify(request)

    assert status == "DUPLICATE_SUSPECTED"


def test_reserved_test_domain_rejected_outside_example_mode(
    tmp_path: Path,
) -> None:
    request = ready_request()
    request["example_mode"] = False

    request_path = tmp_path / "production-request.json"
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    completed = run_builder(request_path)

    assert completed.returncode == 1
    assert "reserved test domain" in completed.stderr


def test_generated_evidence_is_complete() -> None:
    assert OUTPUT_PATH.exists()
    assert RESULT_PATH.exists()
    assert REPORT_PATH.exists()

    result = load_json(RESULT_PATH)
    output = load_json(OUTPUT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_VERIFICATION_BASELINE_NO_EXTERNAL_ACCESS"
    )
    assert result["all_records_classified"] is True
    assert result["wordpress_write_allowed"] is False
    assert result["ready_for_real_verification_input"] is True
    assert output["record_count"] == 1
    assert "Web scraping allowed: `false`" in report
    assert "WordPress write allowed: `false`" in report
