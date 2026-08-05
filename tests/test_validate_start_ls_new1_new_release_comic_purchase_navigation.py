from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/validate_start_ls_new1_new_release_comic_purchase_navigation.py"
VALID = "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_VALIDATED_DESIGN_ONLY_NO_EXECUTION"
INVALID = "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_NOT_VALIDATED"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-1",
        "name": "New Release Comic Purchase Navigation Protocol",
        "japanese_name": "新刊コミック購入ナビ・プロトコル",
        "status": "DESIGN_ONLY_NO_EXECUTION",
        "production_status": "NO_GO",
        "execution_mode": "PROTOCOL_AND_VALIDATION_DESIGN_ONLY",
        "route_policy": {
            "sale_route_status": "ON_HOLD",
            "new_release_comic_route_status": "PRIMARY_NEXT_ROUTE",
        },
        "content_strategy": {
            "media_type": "purchase_navigation_media",
            "not_media_type": "work_explanation_media",
            "work_introduction_required": False,
            "long_work_explanation_required": False,
        },
        "copy_policy": {
            "official_synopsis_copy_allowed": False,
            "store_description_copy_allowed": False,
            "publisher_description_copy_allowed": False,
            "review_copy_allowed": False,
            "user_comment_copy_allowed": False,
            "catchcopy_copy_allowed": False,
        },
        "source_policy": {
            "hon_no_hikidashi": {
                "usage": "human_checked_auxiliary_source_only",
                "forbidden": ["auto_scraping", "database_creation"],
            },
            "canonical_sources": [
                "publisher_official",
                "amazon_kindle",
                "rakuten_books_kobo",
                "dmm_books",
                "ebookjapan",
                "booklive",
                "asp_permitted_store",
            ],
            "preferred_acquisition_methods": [
                "api",
                "official_affiliate_materials",
                "manual_confirmation",
                "permission_compliant_data_acquisition",
            ],
        },
        "resource_allocation_policy": {
            "priority_high": [
                "x_post_generation",
                "release_date_announcement",
                "reservation_start_announcement",
                "delivery_start_announcement",
                "sale_article_generation",
                "point_reward_rate_comparison",
                "price_comparison",
                "store_availability_diff_detection",
            ],
            "priority_medium": [
                "short_original_helper_comment",
                "author_summary",
                "anime_or_trending_work_supplement",
            ],
            "priority_low": [
                "averaging_external_descriptions",
                "long_work_explanation",
                "official_synopsis_style_generation",
            ],
        },
        "safety": {
            "design_only": True,
            "no_execution": True,
            "no_go": True,
            "human_review_required": True,
            "wordpress_write_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "scraping_allowed": False,
            "publish_allowed": False,
        },
        "must_remain_false_flags": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_created": False,
            "publish_executed": False,
            "x_post_executed": False,
            "external_api_call_executed": False,
            "http_get_executed": False,
            "web_scraping_executed": False,
            "rss_fetch_executed": False,
            "amazon_api_call_executed": False,
            "pa_api_call_executed": False,
            "creators_api_call_executed": False,
            "credential_env_read_executed": False,
            "credential_value_output": False,
            "credential_secret_output": False,
            "authorization_header_generated": False,
            "authorization_header_output": False,
            "basic_auth_string_generated": False,
            "basic_auth_string_output": False,
            "post119_update_executed": False,
            "post183_update_executed": False,
            "ls_next1_fill_updated": False,
            "ls_next2_started": False,
            "ls_sale_route_started": False,
            "asin_auto_inferred": False,
            "title_auto_inferred": False,
            "release_date_auto_inferred": False,
            "price_auto_inferred": False,
            "point_reward_rate_auto_inferred": False,
            "candidate_ranking_executed": False,
            "candidate_selected": False,
        },
        "next_phase": {
            "recommended_next_action": "BEGIN_LS_NEW_2_CANDIDATE_INTAKE_SCHEMA_OR_CONTINUE_MONITORING",
            "recommended_next_phase_options": ["LS-NEW-2", "LS-MON-2", "LS-NEXT-1-FILL_AFTER_HUMAN_INPUT"],
        },
    }


def _base_example() -> dict:
    return {
        "protocol": "LS-NEW-1",
        "content_type": "new_release_comic",
        "item": {
            "title": "作品名",
            "volume": "第12巻",
            "author": "著者名",
            "publisher": "出版社",
            "label": "レーベル",
            "release_date": "2026-07-10",
            "ebook_release_date": "2026-07-10",
            "paper_release_date": "2026-07-10",
        },
        "sales_channels": [
            {
                "store": "Kindle",
                "price": 792,
                "point_rate": None,
                "reservation_status": "available",
                "delivery_status": "scheduled",
                "affiliate_url": None,
                "source_url": "https://example.com/kindle",
                "checked_at": "2026-07-04T16:00:00+09:00",
            },
            {
                "store": "Rakuten Kobo",
                "price": 792,
                "point_rate": "variable",
                "reservation_status": "available",
                "delivery_status": "scheduled",
                "affiliate_url": None,
                "source_url": None,
                "checked_at": "2026-07-04T16:00:00+09:00",
            },
        ],
        "content_policy": {
            "official_synopsis_copy_allowed": False,
            "store_description_copy_allowed": False,
            "publisher_description_copy_allowed": False,
            "review_copy_allowed": False,
            "user_comment_copy_allowed": False,
            "catchcopy_copy_allowed": False,
            "short_original_comment_allowed": True,
            "long_work_explanation_required": False,
        },
        "output_targets": {
            "wordpress_draft": False,
            "x_post": False,
            "sale_article": False,
        },
        "safety": {
            "scraping_allowed": False,
            "external_api_call_allowed": False,
            "wordpress_write_allowed": False,
            "x_post_allowed": False,
            "human_review_required": True,
            "publish_allowed": False,
        },
    }


def _base_wp_template() -> str:
    return """# LS-NEW-1 WP Purchase Navigation Template (Design Only)

【○月○日発売】○○ 第○巻 電子書籍ストア比較

販売ストア確認:
- Kindle：価格 ○円 / 予約 ○ / 配信予定 ○
- 楽天Kobo：価格 ○円 / 還元率 ○% / 予約 ○
- DMMブックス：価格 ○円 / 還元率 ○% / クーポン対象 ○
- ebookjapan：価格 ○円 / 還元率 ○% / 配信予定 ○

購入前に、価格・還元率・クーポン・配信状態を各ストアで確認してください。

- 作品説明なしでも購入判断ページとして成立すること。
- 長文作品解説を必須にしないこと。
- 公式あらすじ・販売ストア説明文・レビュー文を本文へ転載しないこと。
"""


def _base_x_templates() -> str:
    return """# LS-NEW-1 X Post Templates (Design Only)

【新刊予定】
『○○』第○巻は○月○日発売予定。

Kindle / 楽天Kobo / DMMブックスなどで配信予定を確認中。
価格・ポイント還元率はストアごとに変わるため、購入前に各販売ページをご確認ください。

#漫画新刊 #電子書籍

【電子書籍セール】
『○○』が○○でポイント還元・クーポン対象。

対象ストア：DMMブックス / 楽天Kobo / Kindle など
還元率・価格は購入時点で要確認。

#電子書籍セール #漫画
"""


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "example": tmp_path / "exchange/examples/example.json",
        "wp": tmp_path / "exchange/templates/wp.md",
        "x": tmp_path / "exchange/templates/x.md",
        "output": tmp_path / "exchange/logs/result.json",
        "report": tmp_path / "reports/report.md",
    }
    _write_json(paths["policy"], _base_policy())
    _write_json(paths["example"], _base_example())
    _write_text(paths["wp"], _base_wp_template())
    _write_text(paths["x"], _base_x_templates())
    return paths


def _run(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--policy",
            str(paths["policy"]),
            "--example",
            str(paths["example"]),
            "--wp-template",
            str(paths["wp"]),
            "--x-templates",
            str(paths["x"]),
            "--output",
            str(paths["output"]),
            "--report",
            str(paths["report"]),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def _payload(paths: dict[str, Path]) -> dict:
    return json.loads(paths["output"].read_text(encoding="utf-8"))


# 1-5

def test_01_valid_protocol_validates(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    assert _payload(paths)["validation_status"] == VALID


def test_02_missing_policy_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_03_missing_example_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["example"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_04_missing_wp_template_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["wp"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_05_missing_x_templates_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["x"].unlink()
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 6-34 policy checks

def test_06_policy_phase_mismatch_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["phase"] = "BAD"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_07_policy_status_mismatch_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["status"] = "BAD"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_08_policy_production_status_mismatch_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["production_status"] = "BAD"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_09_design_only_false_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["design_only"] = False
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_10_no_execution_false_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["no_execution"] = False
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_11_wordpress_write_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["wordpress_write_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_12_x_post_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["x_post_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_13_external_api_call_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["external_api_call_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_14_scraping_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["scraping_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_15_publish_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["publish_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_16_human_review_required_false_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["safety"]["human_review_required"] = False
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_17_sale_route_status_not_on_hold_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["route_policy"]["sale_route_status"] = "ACTIVE"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_18_new_release_route_status_not_primary_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["route_policy"]["new_release_comic_route_status"] = "BAD"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_19_media_type_not_purchase_navigation_media_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["content_strategy"]["media_type"] = "other"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_20_work_introduction_required_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["content_strategy"]["work_introduction_required"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_21_long_work_explanation_required_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["content_strategy"]["long_work_explanation_required"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_22_official_synopsis_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["copy_policy"]["official_synopsis_copy_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_23_store_description_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["copy_policy"]["store_description_copy_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_24_publisher_description_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["copy_policy"]["publisher_description_copy_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_25_review_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["copy_policy"]["review_copy_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_26_user_comment_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["copy_policy"]["user_comment_copy_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_27_catchcopy_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["copy_policy"]["catchcopy_copy_allowed"] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_28_hon_no_hikidashi_usage_not_auxiliary_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["source_policy"]["hon_no_hikidashi"]["usage"] = "bad"
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_29_hon_no_hikidashi_auto_scraping_not_forbidden_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["source_policy"]["hon_no_hikidashi"]["forbidden"] = ["database_creation"]
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_30_canonical_sources_missing_publisher_official_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["source_policy"]["canonical_sources"] = ["amazon_kindle"]
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_31_canonical_sources_missing_amazon_kindle_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["source_policy"]["canonical_sources"] = ["publisher_official"]
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_32_preferred_acquisition_methods_missing_api_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["source_policy"]["preferred_acquisition_methods"] = ["manual_confirmation"]
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_33_resource_allocation_missing_x_post_generation_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["resource_allocation_policy"]["priority_high"] = ["price_comparison"]
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_34_resource_allocation_missing_price_comparison_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["resource_allocation_policy"]["priority_high"] = ["x_post_generation"]
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 35-50 example checks

def test_35_example_protocol_mismatch_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["protocol"] = "BAD"
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_36_example_content_type_mismatch_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["content_type"] = "BAD"
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_37_missing_item_title_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["item"]["title"] = ""
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_38_missing_release_date_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["item"]["release_date"] = ""
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_39_missing_sales_channels_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["sales_channels"] = []
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_40_missing_checked_at_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["sales_channels"][0]["checked_at"] = ""
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_41_missing_source_url_and_source_pending_false_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    for ch in e["sales_channels"]:
        ch["source_url"] = None
    e["source_pending"] = False
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_42_content_policy_official_synopsis_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["content_policy"]["official_synopsis_copy_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_43_content_policy_store_description_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["content_policy"]["store_description_copy_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_44_content_policy_review_copy_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["content_policy"]["review_copy_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_45_content_policy_long_work_explanation_required_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["content_policy"]["long_work_explanation_required"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_46_example_safety_scraping_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["safety"]["scraping_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_47_example_safety_external_api_call_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["safety"]["external_api_call_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_48_example_safety_wordpress_write_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["safety"]["wordpress_write_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_49_example_safety_x_post_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["safety"]["x_post_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_50_example_safety_publish_allowed_true_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    e = _base_example()
    e["safety"]["publish_allowed"] = True
    _write_json(paths["example"], e)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


# 51-56 template checks

def test_51_wp_template_missing_store_comparison_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["wp"], "作品説明なしでも購入判断ページとして成立すること。")
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_52_wp_template_requires_synopsis_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["wp"], _base_wp_template() + "\n公式あらすじ必須\n")
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_53_wp_template_requires_long_explanation_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["wp"], _base_wp_template() + "\n長文作品解説必須\n")
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_54_x_template_missing_new_release_template_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["x"], _base_x_templates().replace("【新刊予定】", "新刊予定"))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_55_x_template_missing_sale_template_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_text(paths["x"], _base_x_templates().replace("【電子書籍セール】", "電子書籍セール"))
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_56_x_template_over_280_char_design_warning_recorded(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    long_text = "あ" * 310
    _write_text(
        paths["x"],
        "【新刊予定】\n" + long_text + "\n\n【電子書籍セール】\n" + "通常文" + "\n",
    )
    _run(paths)
    payload = _payload(paths)
    assert payload["validation_status"] == VALID
    assert any("exceeds 280 chars" in w for w in payload["warnings"])


# 57-65 must_remain_false checks

def _assert_must_false_violation(tmp_path: Path, key: str) -> None:
    paths = _prepare(tmp_path)
    p = _base_policy()
    p["must_remain_false_flags"][key] = True
    _write_json(paths["policy"], p)
    _run(paths)
    assert _payload(paths)["validation_status"] == INVALID


def test_57_must_remain_false_wordpress_api_call_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "wordpress_api_call_executed")


def test_58_must_remain_false_external_api_call_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "external_api_call_executed")


def test_59_must_remain_false_http_get_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "http_get_executed")


def test_60_must_remain_false_amazon_api_call_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "amazon_api_call_executed")


def test_61_must_remain_false_credential_env_read_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "credential_env_read_executed")


def test_62_must_remain_false_post119_update_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "post119_update_executed")


def test_63_must_remain_false_post183_update_executed_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "post183_update_executed")


def test_64_must_remain_false_ls_next1_fill_updated_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "ls_next1_fill_updated")


def test_65_must_remain_false_candidate_selected_true_fails(tmp_path: Path) -> None:
    _assert_must_false_violation(tmp_path, "candidate_selected")


# 66-72 forbidden implementation checks

def _source() -> str:
    return Path(SCRIPT).read_text(encoding="utf-8")


def test_66_source_code_has_no_requests_call() -> None:
    assert "requests." not in _source()


def test_67_source_code_has_no_urllib_request() -> None:
    assert "urllib.request" not in _source()


def test_68_source_code_has_no_wp_json() -> None:
    assert "wp-json" not in _source()


def test_69_source_code_has_no_credential_env_open() -> None:
    src = _source()
    assert "credential.env" not in src
    assert "open(" not in src or "credential" not in src


def test_70_source_code_has_no_auth_header_output() -> None:
    src = _source()
    assert "Authorization:" not in src
    assert "print(" not in src or "Authorization" not in src


def test_71_source_code_has_no_basic_string_output() -> None:
    src = _source()
    assert "Basic " not in src
    assert "print(" not in src or "Basic" not in src


def test_72_source_code_has_no_base64_import_or_use() -> None:
    assert "base64" not in _source()
