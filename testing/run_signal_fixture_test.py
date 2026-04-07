from __future__ import annotations

# run_signal_fixture_test.py
# normal / price_only / release_only / combined の4パターンを
# generator → links → journey の順に実行し、
# combined ケースの全確認ポイントを検証してレポートする。
#
# 実行コマンド:
#   cd /home/deploy/ai_media_os
#   python3 -m testing.run_signal_fixture_test
#
# 環境変数:
#   FIXTURE_TYPES  : カンマ区切りで絞り込み (例: "combined,price_only")
#   ARTICLE_TYPES  : "sale_article" / "latest_volume" / "all"  (デフォルト: all)
#   SAVE_OUTPUTS   : "0" を指定すると JSON 保存をスキップ (デフォルト: 1)

from __future__ import annotations

import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---- プロジェクトルートをパスに追加 ----
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from article_generator.generator import generate_article_content
from buyer_journey_ai.journey_builder import build_journey, build_journey_html
from internal_link_ai.link_engine import build_related_links
from internal_link_ai.link_inserter import insert_related_links
from monitoring.combined_signal_notifier import build_combined_signal_lines
from monitoring.combined_signal_reporter import (
    normalize_combined_event,
    classify_event_type,
)
from pipelines.combined_signal_policy import evaluate_combined_signal
from testing.signal_fixture_builder import build_all_fixtures, build_fixtures

# ------------------------------------------------------------------ #
# 出力先
# ------------------------------------------------------------------ #

OUTPUT_DIR = _PROJECT_ROOT / "data" / "test_outputs"

# ------------------------------------------------------------------ #
# 確認ポイント定義（combined 専用）
# ------------------------------------------------------------------ #

COMBINED_CHECKS: list[dict[str, Any]] = [
    {
        "key": "signal_mode",
        "expected": "combined",
        "description": "signal_mode が combined であること",
    },
    {
        "key": "decision",
        "expected": "would_republish_combined_signal",
        "description": "decision が would_republish_combined_signal であること",
    },
    {
        "key": "reason",
        "expected": "combined_price_and_release_changed",
        "description": "reason が combined_price_and_release_changed であること",
    },
]

# combined_optimized は journey の中にある
JOURNEY_COMBINED_CHECKS: list[dict[str, Any]] = [
    {
        "key": "journey_mode",
        "expected": "combined_optimized",
        "description": "journey_mode が combined_optimized であること",
    },
    {
        "key": "is_sale_optimized",
        "expected": True,
        "description": "is_sale_optimized が True であること",
    },
    {
        "key": "is_release_optimized",
        "expected": True,
        "description": "is_release_optimized が True であること",
    },
    {
        "key": "stage",
        "expected": "purchase_ready",
        "description": "stage が purchase_ready であること",
    },
]

# ------------------------------------------------------------------ #
# パイプライン実行
# ------------------------------------------------------------------ #

def _run_generator(fixture: dict[str, Any]) -> dict[str, Any]:
    """article_generator を実行する。"""
    return generate_article_content(fixture)


def _run_links(article_output: dict[str, Any]) -> dict[str, Any]:
    """Internal Link AI を実行して related_links を付与する。"""
    try:
        related_links = build_related_links(article_output)
        enriched_html = insert_related_links(
            str(article_output.get("content_html", "")),
            related_links,
        )
        result = dict(article_output)
        result["related_links"] = related_links
        result["content_html"] = enriched_html
        return result
    except Exception as exc:
        # links が失敗してもテスト継続
        result = dict(article_output)
        result["related_links"] = []
        result["_links_error"] = str(exc)
        return result


def _run_journey(article_output: dict[str, Any]) -> dict[str, Any]:
    """Buyer Journey AI を実行して journey 情報を付与する。"""
    try:
        journey = build_journey(article_output)
        journey_html = build_journey_html(journey)
        content = str(article_output.get("content_html", ""))
        from buyer_journey_ai.journey_builder import insert_journey_block
        enriched_html = insert_journey_block(content, journey_html)

        result = dict(article_output)
        result["journey"] = journey
        result["journey_mode"] = journey.get("journey_mode", "standard")
        result["journey_stage"] = journey.get("stage", "")
        result["journey_cta_text"] = journey.get("cta_text", "")
        result["content_html"] = enriched_html
        return result
    except Exception as exc:
        result = dict(article_output)
        result["_journey_error"] = str(exc)
        return result


def _run_policy(fixture: dict[str, Any]) -> dict[str, Any]:
    """combined_signal_policy を実行して policy 結果を返す。"""
    try:
        policy_result = evaluate_combined_signal(fixture, dry_run=True)
        return {
            "policy_priority": policy_result.priority,
            "policy_decision": policy_result.decision,
            "policy_reason": policy_result.reason,
            "policy_sub_reasons": policy_result.sub_reasons,
            "policy_signal_mode": policy_result.signal_mode,
        }
    except Exception as exc:
        return {"_policy_error": str(exc)}


def run_fixture(
    fixture_name: str,
    fixture: dict[str, Any],
    *,
    verbose: bool = True,
) -> dict[str, Any]:
    """1件のフィクスチャをパイプライン全体で実行して結果を返す。"""
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"[fixture] {fixture_name}")
        print(f"  article_type   : {fixture.get('article_type', '')}")
        print(f"  price_changed  : {fixture.get('price_changed', False)}")
        print(f"  release_changed: {fixture.get('release_changed', False)}")
        print(f"{'=' * 60}")

    # ---- step 1: generator ----
    article_output = _run_generator(fixture)

    # ---- step 2: links ----
    with_links = _run_links(article_output)

    # ---- step 3: journey ----
    with_journey = _run_journey(with_links)

    # ---- step 4: policy ----
    policy = _run_policy(fixture)

    # ---- step 5: reporter 正規化 ----
    normalized_event = normalize_combined_event({**with_journey, **fixture})

    result = {
        "_fixture_name": fixture_name,
        "_fixture_label": fixture.get("_fixture_label", fixture_name),
        "_ran_at": datetime.now(timezone.utc).isoformat(),
        # generator 出力の主要フィールド
        "signal_mode": article_output.get("signal_mode", ""),
        "template_mode": article_output.get("template_mode", ""),
        "is_combined_signal": article_output.get("is_combined_signal", False),
        "decision": article_output.get("decision", ""),
        "reason": article_output.get("reason", ""),
        "cta_experiment": article_output.get("cta_experiment", ""),
        "cta_variant": article_output.get("cta_variant", ""),
        "cta_mode": article_output.get("cta_mode", ""),
        # content_html 先頭200文字（確認用）
        "content_html_head200": str(with_journey.get("content_html", ""))[:200],
        # combined-alert-box の有無
        "has_combined_alert_box": "combined-alert-box" in str(
            with_journey.get("content_html", "")
        ),
        # journey フィールド
        "journey_mode": with_journey.get("journey_mode", ""),
        "journey_stage": with_journey.get("journey_stage", ""),
        "journey_cta_text": with_journey.get("journey_cta_text", ""),
        "journey_is_sale_optimized": with_journey.get("journey", {}).get(
            "is_sale_optimized", False
        ) if isinstance(with_journey.get("journey"), dict) else False,
        "journey_is_release_optimized": with_journey.get("journey", {}).get(
            "is_release_optimized", False
        ) if isinstance(with_journey.get("journey"), dict) else False,
        # policy フィールド
        **policy,
        # reporter 正規化後のイベント
        "normalized_event_type": normalized_event.get("event_type", ""),
        "normalized_stage": normalized_event.get("stage", ""),
        "normalized_journey_mode": normalized_event.get("journey_mode", ""),
        # エラー情報
        **{k: v for k, v in with_journey.items() if k.startswith("_") and "error" in k},
    }

    if verbose:
        _print_result_summary(fixture_name, result)

    return result


def _print_result_summary(fixture_name: str, result: dict[str, Any]) -> None:
    """確認ポイントを表示する。"""
    print(f"\n  --- 出力サマリー: {fixture_name} ---")
    print(f"  signal_mode           : {result.get('signal_mode', '')}")
    print(f"  template_mode         : {result.get('template_mode', '')}")
    print(f"  is_combined_signal    : {result.get('is_combined_signal', False)}")
    print(f"  decision              : {result.get('decision', '')}")
    print(f"  reason                : {result.get('reason', '')}")
    print(f"  has_combined_alert_box: {result.get('has_combined_alert_box', False)}")
    print(f"  journey_mode          : {result.get('journey_mode', '')}")
    print(f"  journey_stage         : {result.get('journey_stage', '')}")
    print(f"  is_sale_optimized     : {result.get('journey_is_sale_optimized', False)}")
    print(f"  is_release_optimized  : {result.get('journey_is_release_optimized', False)}")
    print(f"  cta_mode              : {result.get('cta_mode', '')}")
    print(f"  cta_variant           : {result.get('cta_variant', '')}")

    errors = {k: v for k, v in result.items() if "error" in k}
    if errors:
        print(f"\n  [警告] エラーあり:")
        for k, v in errors.items():
            print(f"    {k}: {v}")


# ------------------------------------------------------------------ #
# アサーション
# ------------------------------------------------------------------ #

def assert_combined_result(result: dict[str, Any]) -> list[str]:
    """combined フィクスチャの確認ポイントを検証してエラーメッセージリストを返す。

    Returns:
        バリデーションエラーの説明リスト。空なら全パス。
    """
    failures: list[str] = []

    # generator フィールドのチェック
    for check in COMBINED_CHECKS:
        actual = result.get(check["key"])
        expected = check["expected"]
        if actual != expected:
            failures.append(
                f"FAIL [{check['description']}] "
                f"期待: {expected!r}, 実際: {actual!r}"
            )

    # combined-alert-box の有無チェック
    if not result.get("has_combined_alert_box"):
        failures.append(
            "FAIL [content_html に combined-alert-box が含まれること] "
            f"has_combined_alert_box={result.get('has_combined_alert_box')}"
        )

    # journey フィールドのチェック
    for check in JOURNEY_COMBINED_CHECKS:
        actual: Any
        if check["key"] == "journey_mode":
            actual = result.get("journey_mode")
        elif check["key"] == "is_sale_optimized":
            actual = result.get("journey_is_sale_optimized")
        elif check["key"] == "is_release_optimized":
            actual = result.get("journey_is_release_optimized")
        elif check["key"] == "stage":
            actual = result.get("journey_stage")
        else:
            actual = result.get(check["key"])

        expected = check["expected"]
        if actual != expected:
            failures.append(
                f"FAIL [{check['description']}] "
                f"期待: {expected!r}, 実際: {actual!r}"
            )

    # normalized_event_type チェック
    if result.get("normalized_event_type") != "combined":
        failures.append(
            "FAIL [normalized_event_type が combined であること] "
            f"実際: {result.get('normalized_event_type')!r}"
        )

    return failures


def assert_price_only_result(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if result.get("signal_mode") != "price_only":
        failures.append(
            f"FAIL [signal_mode=price_only] 実際: {result.get('signal_mode')!r}"
        )
    if result.get("has_combined_alert_box"):
        failures.append("FAIL [price_only に combined-alert-box があってはならない]")
    return failures


def assert_release_only_result(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if result.get("signal_mode") != "release_only":
        failures.append(
            f"FAIL [signal_mode=release_only] 実際: {result.get('signal_mode')!r}"
        )
    if result.get("has_combined_alert_box"):
        failures.append("FAIL [release_only に combined-alert-box があってはならない]")
    return failures


def assert_normal_result(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if result.get("signal_mode") != "normal":
        failures.append(
            f"FAIL [signal_mode=normal] 実際: {result.get('signal_mode')!r}"
        )
    if result.get("has_combined_alert_box"):
        failures.append("FAIL [normal に combined-alert-box があってはならない]")
    return failures


_ASSERT_MAP: dict[str, Any] = {
    "combined": assert_combined_result,
    "sale_combined": assert_combined_result,
    "volume_combined": assert_combined_result,
    "price_only": assert_price_only_result,
    "sale_price_only": assert_price_only_result,
    "release_only": assert_release_only_result,
    "volume_release_only": assert_release_only_result,
    "normal": assert_normal_result,
    "sale_normal": assert_normal_result,
    "volume_normal": assert_normal_result,
}


# ------------------------------------------------------------------ #
# 保存
# ------------------------------------------------------------------ #

def save_result(fixture_name: str, result: dict[str, Any]) -> Path:
    """テスト結果を JSON で保存する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"signal_fixture_{fixture_name}.json"
    with path.open("w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)
    return path


# ------------------------------------------------------------------ #
# メイン
# ------------------------------------------------------------------ #

def main() -> None:
    """全フィクスチャを順に実行し、確認ポイントをレポートする。"""
    # 環境変数によるフィルタ
    fixture_filter_raw = os.getenv("FIXTURE_TYPES", "").strip()
    fixture_filter = {x.strip() for x in fixture_filter_raw.split(",") if x.strip()}

    article_types_raw = os.getenv("ARTICLE_TYPES", "all").strip().lower()
    save_outputs = os.getenv("SAVE_OUTPUTS", "1").strip() not in {"0", "false", "no"}

    # フィクスチャを選択
    if article_types_raw == "all":
        all_fixtures = build_all_fixtures()
    elif article_types_raw in {"sale_article", "sale"}:
        raw = build_fixtures("sale_article")
        all_fixtures = {f"sale_{k}": v for k, v in raw.items()}
    elif article_types_raw in {"latest_volume", "volume"}:
        raw = build_fixtures("latest_volume")
        all_fixtures = {f"volume_{k}": v for k, v in raw.items()
                       if k in ("normal", "release_only", "combined")}
    else:
        raw = build_fixtures("sale_article")
        all_fixtures = {f"sale_{k}": v for k, v in raw.items()}

    if fixture_filter:
        all_fixtures = {
            name: data
            for name, data in all_fixtures.items()
            if any(f in name for f in fixture_filter)
        }

    if not all_fixtures:
        print("[ERROR] フィルタ後に実行対象フィクスチャが0件です。")
        sys.exit(1)

    print(f"\n{'#' * 60}")
    print("# AI Media OS - 複合シグナル強制テスト基盤")
    print(f"# 実行対象: {', '.join(all_fixtures.keys())}")
    print(f"{'#' * 60}")

    all_results: dict[str, dict[str, Any]] = {}
    all_failures: dict[str, list[str]] = {}
    saved_paths: list[Path] = []

    for fixture_name, fixture_data in all_fixtures.items():
        result = run_fixture(fixture_name, fixture_data, verbose=True)
        all_results[fixture_name] = result

        if save_outputs:
            path = save_result(fixture_name, result)
            saved_paths.append(path)

        # アサーション実行
        assert_fn = _ASSERT_MAP.get(fixture_name)
        if assert_fn:
            failures = assert_fn(result)
            if failures:
                all_failures[fixture_name] = failures

    # ---- 最終レポート ----
    print(f"\n\n{'#' * 60}")
    print("# 最終レポート")
    print(f"{'#' * 60}")

    # 比較表
    print("\n  ---- シグナルモード比較表 ----")
    header = f"  {'フィクスチャ名':<28} {'signal_mode':<14} {'template_mode':<32} {'decision':<36} {'journey_mode':<22} {'alert_box'}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for name, res in all_results.items():
        alert = "✓" if res.get("has_combined_alert_box") else "✗"
        print(
            f"  {name:<28} "
            f"{res.get('signal_mode', ''):<14} "
            f"{res.get('template_mode', ''):<32} "
            f"{res.get('decision', ''):<36} "
            f"{res.get('journey_mode', ''):<22} "
            f"{alert}"
        )

    # アサーション結果
    print(f"\n  ---- アサーション結果 ----")
    if not all_failures:
        print("\n  ✅ 全アサーション PASS")
    else:
        print(f"\n  ❌ {len(all_failures)} フィクスチャでアサーション失敗:")
        for name, failures in all_failures.items():
            print(f"\n  [{name}]")
            for msg in failures:
                print(f"    {msg}")

    # combined ケースの詳細表示
    for name, res in all_results.items():
        if "combined" in name:
            print(f"\n  ---- combined 確認ポイント詳細: {name} ----")
            checks = [
                ("signal_mode",            res.get("signal_mode")),
                ("decision",               res.get("decision")),
                ("reason",                 res.get("reason")),
                ("has_combined_alert_box", res.get("has_combined_alert_box")),
                ("journey_mode",           res.get("journey_mode")),
                ("is_sale_optimized",      res.get("journey_is_sale_optimized")),
                ("is_release_optimized",   res.get("journey_is_release_optimized")),
                ("stage",                  res.get("journey_stage")),
                ("cta_mode",               res.get("cta_mode")),
                ("cta_variant",            res.get("cta_variant")),
                ("normalized_event_type",  res.get("normalized_event_type")),
                ("normalized_journey_mode",res.get("normalized_journey_mode")),
            ]
            for label, value in checks:
                status = "✓" if value not in (None, False, "") else "△"
                print(f"    {status} {label:<30}: {value!r}")

    # 保存先リスト
    if saved_paths:
        print(f"\n  ---- 保存ファイル ----")
        for p in saved_paths:
            print(f"    {p}")

    # 終了コード
    sys.exit(1 if all_failures else 0)


if __name__ == "__main__":
    main()
