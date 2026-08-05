from __future__ import annotations

import re
from typing import Any, Dict, List

_DEFAULT_AFFILIATE_URL = "公式情報をご確認ください"

_READER_KEYWORDS = {
    "バトル好き": ["バトル", "戦い", "アクション", "武闘"],
    "恋愛好き": ["恋愛", "ラブ", "純愛", "片思い"],
    "異世界好き": ["異世界", "転生", "召喚", "ファンタジー"],
    "ミステリー好き": ["ミステリー", "謎", "推理", "サスペンス"],
    "日常系好き": ["日常", "ほのぼの", "学園", "コメディ"],
}


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "").strip()


def _pick_title(candidate: Dict[str, Any]) -> str:
    title = str(
        candidate.get("title_candidate")
        or candidate.get("title")
        or candidate.get("work_title")
        or "タイトル未設定"
    ).strip()
    return title or "タイトル未設定"


def _pick_affiliate_url(candidate: Dict[str, Any]) -> str:
    url = str(candidate.get("affiliate_url") or "").strip()
    if url:
        return url

    source_builder = candidate.get("source_builder")
    if isinstance(source_builder, dict):
        url = str(source_builder.get("affiliate_url") or "").strip()
        if url:
            return url

    return _DEFAULT_AFFILIATE_URL


def _summarize_overview(candidate: Dict[str, Any], title: str) -> List[str]:
    base_text = _strip_html(str(candidate.get("content_html_candidate") or candidate.get("content") or ""))
    if not base_text:
        return [
            f"『{title}』の魅力を短時間で把握できるように、要点を整理しました。",
            "作品の世界観・主要テーマ・読みどころを中心に紹介します。",
        ]

    compact = re.sub(r"\s+", " ", base_text)
    lead = compact[:120]
    return [
        f"『{title}』は、テンポの良い展開と読みやすさが魅力の作品です。",
        f"概要: {lead}",
        "ネタバレを避けながら、購入判断に役立つポイントを整理しています。",
    ]


def _recommend_points(title: str) -> List[str]:
    return [
        f"短時間で『{title}』の雰囲気を掴みたい人",
        "次に読む電子書籍を探している人",
        "失敗しにくい作品選びをしたい人",
        "レビューの要点を先に確認したい人",
    ]


def _highlight_points() -> List[str]:
    return [
        "導入が分かりやすく、最初の1話から入りやすい",
        "中盤以降の展開にメリハリがあり、読み進めやすい",
        "印象に残るキャラクター描写がある",
        "読後に感想を共有したくなる構成",
    ]


def _rating_points() -> List[str]:
    return [
        "テンポ: 間延びしにくく読みやすい",
        "没入感: 世界観に入り込みやすい",
        "満足度: 続きが気になる構成",
    ]


def _faq_items() -> List[str]:
    return [
        "Q. 初心者でも読めますか？\nA. 公式情報をご確認ください。",
        "Q. 完結していますか？\nA. 公式情報をご確認ください。",
        "Q. アニメ化されていますか？\nA. 公式情報をご確認ください。",
    ]


def _pick_reader_profiles(candidate: Dict[str, Any]) -> List[str]:
    pool: List[str] = []
    for key in ("title_candidate", "title", "work_title", "content_html_candidate", "content"):
        value = candidate.get(key)
        if value:
            pool.append(str(value))

    categories = candidate.get("category_candidates")
    if isinstance(categories, list):
        pool.extend(str(x) for x in categories)

    tags = candidate.get("tag_candidates")
    if isinstance(tags, list):
        pool.extend(str(x) for x in tags)

    text = " ".join(pool)
    found: List[str] = []
    for profile, keywords in _READER_KEYWORDS.items():
        if any(k in text for k in keywords):
            found.append(profile)

    if found:
        return [f"{profile}に刺さりやすい要素があります" for profile in found[:5]]

    return ["幅広い読者におすすめ"]


def _build_content(title: str, candidate: Dict[str, Any], affiliate_url: str) -> str:
    overview_lines = _summarize_overview(candidate, title)
    recommend = _recommend_points(title)
    highlights = _highlight_points()
    ratings = _rating_points()
    faq = _faq_items()
    reader_profiles = _pick_reader_profiles(candidate)

    sections: List[str] = [
        f"# {title}",
        "",
        "## 作品概要",
        *overview_lines,
        "",
        "## こんな人におすすめ",
        *[f"- {line}" for line in recommend],
        "",
        "## 見どころ",
        *[f"- {line}" for line in highlights],
        "",
        "## 読者評価ポイント",
        *[f"- {line}" for line in ratings],
        "",
        "## よくある質問",
        *faq,
        "",
        "## 関連作品",
        "- 関連作品情報は準備中です。公式情報をご確認ください。",
        "",
        "## 関連記事",
        "- 関連記事は準備中です。公開後に随時更新します。",
        "",
        "## この作品が刺さる読者",
        *[f"- {line}" for line in reader_profiles],
        "",
        "## 購入はこちら",
        affiliate_url,
        "",
        "## PR表記",
        "本記事には広告が含まれています。",
    ]
    return "\n".join(sections).strip()


def build_draft_payload(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Build WordPress draft payload while keeping DRY_RUN compatibility."""
    title = _pick_title(candidate)
    affiliate_url = _pick_affiliate_url(candidate)
    content = _build_content(title, candidate, affiliate_url)

    item_id = str(candidate.get("item_id") or "").strip()

    meta = {
        "source_builder": candidate.get("source_builder", {}),
        "generated_at": candidate.get("created_at", ""),
        "seo_version": "v1",
        "generated_sections": [
            "title",
            "works_overview",
            "recommend_for",
            "highlights",
            "reader_rating_points",
            "faq",
            "related_works",
            "related_articles",
            "reader_profiles",
            "purchase_link",
            "pr_disclosure",
        ],
        "reader_profile_version": "v1",
    }

    payload = {
        "dry_run": True,
        "wordpress_post_must_not_be_called": True,
        "status": "draft",
        "title": title,
        "content": content,
        "categories_hint": candidate.get("category_candidates", []),
        "tags_hint": candidate.get("tag_candidates", []),
        "affiliate_url": affiliate_url,
        "item_id": item_id,
        "meta": meta,
        "_note": "このファイルはdry-run用のpayload候補です。WordPress REST APIへのPOSTは禁止。",
    }

    return payload
