import html
import re
from typing import Any, Dict


class ArticleFormatter:
    """Convert generated article text into simple WordPress-ready HTML."""

    def to_wp_payload(self, article: Dict[str, Any], status: str = "draft") -> Dict[str, Any]:
        title = str(article.get("title", "無題記事")).strip() or "無題記事"
        content = str(article.get("content", "")).strip()
        html_content = self._normalize_content(content)

        payload: Dict[str, Any] = {
            "title": title,
            "content": html_content,
            "status": status,
        }

        # 将来のタクソノミーID解決に備え、名前ベースの情報も保持する。
        slug = str(article.get("slug", "")).strip()
        if slug:
            payload["slug"] = slug

        category_names = article.get("category_names", [])
        if isinstance(category_names, list):
            normalized_categories = [str(v).strip() for v in category_names if str(v).strip()]
            if normalized_categories:
                payload["category_names"] = normalized_categories

        tag_names = article.get("tag_names", [])
        if isinstance(tag_names, list):
            normalized_tags = [str(v).strip() for v in tag_names if str(v).strip()]
            if normalized_tags:
                payload["tag_names"] = normalized_tags

        return payload

    def _normalize_content(self, content: str) -> str:
        """本文がHTMLならそのまま使い、テキストなら簡易Markdown変換する。"""
        if not content:
            return "<p>本文がありません。</p>"

        # content_html のような完成HTMLはエスケープせずそのまま投稿する。
        if "<" in content and ">" in content:
            return content

        return self.markdown_like_to_html(content)

    def markdown_like_to_html(self, text: str) -> str:
        if not text:
            return "<p>本文がありません。</p>"

        lines = text.splitlines()
        html_lines = []
        in_list = False

        for raw_line in lines:
            line = raw_line.rstrip()
            if not line:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                continue

            if line.startswith("### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h3>{self._inline_format(line[4:])}</h3>")
                continue

            if line.startswith("## "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h2>{self._inline_format(line[3:])}</h2>")
                continue

            if line.startswith("# "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h1>{self._inline_format(line[2:])}</h1>")
                continue

            if line.startswith("- "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(f"<li>{self._inline_format(line[2:])}</li>")
                continue

            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{self._inline_format(line)}</p>")

        if in_list:
            html_lines.append("</ul>")

        return "\n".join(html_lines)

    def _inline_format(self, text: str) -> str:
        escaped = html.escape(text)

        # Bold: **text** -> <strong>text</strong>
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

        # Simple links: [label](url) -> <a href="url">label</a>
        escaped = re.sub(
            r"\[(.+?)\]\((https?://[^\s\)]+)\)",
            r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
            escaped,
        )
        return escaped
