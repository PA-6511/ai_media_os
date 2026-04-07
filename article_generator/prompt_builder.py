from __future__ import annotations

from typing import Any


def build_prompt(article_plan: dict[str, Any]) -> str:
    """将来LLMへ渡すための最小プロンプト文字列を作る。"""
    title = str(article_plan.get("title", "無題記事")).strip()
    keyword = str(article_plan.get("keyword", "")).strip()
    article_type = str(article_plan.get("article_type", "work_article")).strip()
    sections = article_plan.get("sections", [])
    if not isinstance(sections, list):
        sections = []

    section_lines = "\n".join(f"- {str(section)}" for section in sections)

    return (
        "あなたは電子書籍メディアの記事生成AIです。\n"
        "以下の設計図に従って本文を作成してください。\n\n"
        f"タイトル: {title}\n"
        f"キーワード: {keyword}\n"
        f"記事タイプ: {article_type}\n"
        "セクション:\n"
        f"{section_lines}\n"
    )
