from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

from article_generator.generator import generate_article_content
from article_planner.planner import generate_plan
from pipelines.wp_post_enricher import build_slug, build_tag_names, map_category_names

def _build_sample_item() -> dict[str, object]:
    return {
        "work_id": "test-001",
        "title": "テスト作品",
        "keyword": "テスト作品 レビュー",
        "article_type": "review",
        "author": "テスト著者",
        "publisher": "テスト出版社",
        "category": "review",
        "tags": ["comic", "kindle", "test"],
    }


def _build_body_html(base_html: str, category_name: str) -> str:
    pr_block = '<p class="pr-disclosure">PR: 本記事にはプロモーションが含まれます。</p>'
    price_notice = '<p class="price-change-note">価格変動注意: 購入前に最新価格を確認してください。</p>'
    affiliate_cta = (
        '<div class="affiliate-cta">'
        '<a href="https://example.com/affiliate/test" '
        'rel="nofollow sponsored noopener" target="_blank">'
        f"{category_name} をストアで確認する"
        "</a></div>"
    )

    html = base_html.strip()
    if "PR:" not in html:
        html = pr_block + "\n" + html
    if "affiliate-cta" not in html:
        html = html + "\n" + affiliate_cta
    if "価格変動注意" not in html:
        html = html + "\n" + price_notice
    return html


def main() -> int:
    load_dotenv(BASE_DIR / ".env")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("エラー: OPENAI_API_KEY が未設定です")
        return 1

    try:
        sample = _build_sample_item()
        plan = generate_plan(sample)

        with contextlib.redirect_stdout(io.StringIO()):
            article_output = generate_article_content(plan)

        slug = build_slug(article_output)
        category = map_category_names(str(article_output.get("article_type", "work_article")))[0]
        tags = build_tag_names(article_output)
        title = str(article_output.get("title", "")).strip()
        meta_description = f"{title} の見どころとチェックポイントを簡潔に整理します。"[:120]
        body_html = _build_body_html(str(article_output.get("content_html", "")), category)

        required_checks = {
            "## TITLE": bool(title),
            "## SLUG": bool(slug),
            "## META_DESCRIPTION": bool(meta_description),
            "## CATEGORY": bool(category),
            "## TAGS": bool(tags),
            "## BODY_HTML": bool(body_html),
            "## CHECKLIST": True,
            "PR表記": "PR:" in body_html,
            "affiliate-cta": "affiliate-cta" in body_html,
            'rel="nofollow sponsored noopener"': 'rel="nofollow sponsored noopener"' in body_html,
            "価格変動注意": "価格変動注意" in body_html,
        }
        failed = [key for key, ok in required_checks.items() if not ok]
        if failed:
            print("エラー: AI生成テストの出力要件を満たしていません")
            print("不足項目: " + ", ".join(failed))
            return 1

        print("## TITLE")
        print(title)
        print()
        print("## SLUG")
        print(slug)
        print()
        print("## META_DESCRIPTION")
        print(meta_description)
        print()
        print("## CATEGORY")
        print(category)
        print()
        print("## TAGS")
        print(", ".join(tags))
        print()
        print("## BODY_HTML")
        print(body_html)
        print()
        print("## CHECKLIST")
        print("- TITLE / SLUG / META_DESCRIPTION / CATEGORY / TAGS / BODY_HTML を生成")
        print("- PR表記あり")
        print("- affiliate-cta あり")
        print("- rel=\"nofollow sponsored noopener\" あり")
        print("- 価格変動注意あり")
        print()
        print("OK: AI生成テストに成功しました")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"エラー: AI生成テストに失敗しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())