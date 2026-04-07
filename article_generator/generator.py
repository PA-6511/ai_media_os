from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from article_generator.content_formatter import format_article_html
from article_generator.prompt_builder import build_prompt
from article_generator.template_mode_resolver import (
    resolve_template_mode,
    is_combined_signal,
)
from article_generator.signal_template_router import detect_signal_mode
from article_generator.cta_experiment_registry import EXPERIMENT_PRICE_CHANGED_V1
from article_generator.cta_variant_selector import (
    select_price_changed_variant,
    get_cta_mode,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ARTICLE_PLAN_PATH = DATA_DIR / "article_plan.json"
ARTICLE_OUTPUT_PATH = DATA_DIR / "article_output.json"


def load_article_plan(path: Path) -> dict[str, Any]:
    """article_plan.json を読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON形式が不正です: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"ファイル読み込みに失敗しました: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("article_plan.json はオブジェクト形式である必要があります")

    return data


# release 情報として article_plan から引き継ぐフィールド一覧
_RELEASE_FIELDS: tuple[str, ...] = (
    "release_changed",
    "release_change_reason",
    "previous_latest_volume_number",
    "current_latest_volume_number",
    "previous_latest_release_date",
    "current_latest_release_date",
    "previous_availability_status",
    "current_availability_status",
)

# price 情報として article_plan から引き継ぐフィールド一覧
_PRICE_FIELDS: tuple[str, ...] = (
    "price_changed",
    "change_reason",
    "previous_price",
    "current_price",
    "price_diff",
    "discount_rate",
    "discount_rate_diff",
    "checked_at",
)


def generate_article_content(
    article_plan: dict[str, Any],
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """article_plan から記事本文データを生成する。

    template_mode_resolver でテンプレモードを確定し、
    content_formatter を通じて適切な builder に委譲する。

    template_mode / is_combined_signal / decision / reason は
    article_output に出力し、後段パイプラインが参照できるようにする。
    """
    # extra_context があれば article_plan にマージして生成へ渡す。
    merged_plan = dict(article_plan)
    if isinstance(extra_context, dict):
        merged_plan.update(extra_context)

    article_type = str(merged_plan.get("article_type", "work_article")).strip()
    release_changed = bool(merged_plan.get("release_changed", False))
    price_changed = bool(merged_plan.get("price_changed", False))

    # テンプレモードを確定（ログは content_formatter 内でも出力）
    template_mode = resolve_template_mode(merged_plan)
    combined = is_combined_signal(merged_plan)
    signal_mode = detect_signal_mode(merged_plan)
    merged_plan["signal_mode"] = signal_mode

    # 将来のLLM差し替えのため、プロンプト作成関数は呼び出しておく
    _prompt = build_prompt(merged_plan)
    _ = _prompt  # 最小版では未使用だが、将来拡張ポイントとして保持

    # ---- 確認ログ ----
    print(f"[generator] article_type: {article_type}")
    print(f"[generator] template_mode: {template_mode}")
    print(f"[generator] signal_mode: {signal_mode}")
    print(f"[generator] is_combined_signal: {combined}")
    print(f"[generator] price_changed: {price_changed}")
    print(f"[generator] release_changed: {release_changed}")

    if article_type == "latest_volume":
        print(
            f"[generator] current_latest_volume_number:"
            f" {merged_plan.get('current_latest_volume_number')}"
        )
    if article_type == "sale_article":
        print(f"[generator] previous_price: {merged_plan.get('previous_price')}")
        print(f"[generator] current_price: {merged_plan.get('current_price')}")

    formatter_context = dict(extra_context) if isinstance(extra_context, dict) else {}
    formatter_context["signal_mode"] = signal_mode
    content_html = format_article_html(merged_plan, extra_context=formatter_context)

    # ---- CTA AB テスト情報を解決 ----
    # select_price_changed_variant は決定論的なので、
    # content_formatter 内の呼び出しと同じ結果になる。
    cta_mode = get_cta_mode(merged_plan)
    if cta_mode == "ab_test":
        _variant = select_price_changed_variant(merged_plan)
        cta_experiment: str = EXPERIMENT_PRICE_CHANGED_V1
        cta_variant: str = _variant.get("name", "") if _variant else ""
    else:
        cta_experiment = ""
        cta_variant = ""

    print(f"[generator] cta_experiment: {cta_experiment or '(none)'}")
    print(f"[generator] cta_variant: {cta_variant or '(none)'}")
    print(f"[generator] cta_mode: {cta_mode}")

    # decision / reason の計算（combined_signal_policy と整合させる）
    if combined:
        decision = "would_republish_combined_signal"
        reason = "combined_price_and_release_changed"
    elif price_changed and article_type == "sale_article":
        decision = "would_republish_price_changed"
        reason = str(merged_plan.get("change_reason", "price_changed"))
    elif release_changed:
        decision = "would_republish_release_changed"
        reason = str(merged_plan.get("release_change_reason", "release_changed"))
    else:
        decision = "standard_publish"
        reason = "no_signal"

    output: dict[str, Any] = {
        "work_id": str(merged_plan.get("work_id", "")).strip(),
        "keyword": str(merged_plan.get("keyword", "")).strip(),
        "article_type": article_type,
        "title": str(merged_plan.get("title", "無題記事")).strip(),
        "content_html": content_html,
        "cta_type": str(merged_plan.get("cta_type", "")).strip(),
        "internal_link_hints": merged_plan.get("internal_link_hints", []),
        # テンプレート制御情報（後段パイプラインが参照）
        "template_mode": template_mode,
        "signal_mode": signal_mode,
        "is_combined_signal": combined,
        "decision": decision,
        "reason": reason,
        # CTA AB テスト情報（計測・分析基盤との接続用）
        "cta_experiment": cta_experiment,
        "cta_variant": cta_variant,
        "cta_mode": cta_mode,
    }

    # release フィールドを出力に引き継ぐ
    for field in _RELEASE_FIELDS:
        if field in merged_plan:
            output[field] = merged_plan[field]

    # price フィールドを出力に引き継ぐ
    for field in _PRICE_FIELDS:
        if field in merged_plan:
            output[field] = merged_plan[field]

    return output


def save_article_output(data: dict[str, Any], path: Path) -> None:
    """article_output.json を保存する。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(f"article_output.json 保存に失敗しました: {exc}") from exc


def run() -> dict[str, Any]:
    """article_plan 読込 -> 本文生成 -> article_output 保存を実行する。"""
    article_plan = load_article_plan(ARTICLE_PLAN_PATH)
    output = generate_article_content(article_plan)
    save_article_output(output, ARTICLE_OUTPUT_PATH)
    return output


def main() -> None:
    """Article Generator 実行。"""
    try:
        output = run()
        print(f"保存先: {ARTICLE_OUTPUT_PATH}")
        print(f"template_mode: {output.get('template_mode', '')}")
        print(f"is_combined_signal: {output.get('is_combined_signal', False)}")
        print(f"decision: {output.get('decision', '')}")
        print(json.dumps(output, ensure_ascii=False, indent=2)[:1200])
    except Exception as exc:
        print(f"エラー: {exc}")


if __name__ == "__main__":
    main()
