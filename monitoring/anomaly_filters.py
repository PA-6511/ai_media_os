from __future__ import annotations

# anomaly_filters.py
# fixture / test 由来の slug を異常判定から除外する。


FIXTURE_SLUG_PREFIXES: tuple[str, ...] = (
    "fail_",
    "skip_",
    "draft_",
    "signal_fixture_",
    "test_",
)


def is_fixture_slug(slug: str) -> bool:
    """fixture / test 由来の slug かどうかを判定する。"""
    normalized = (slug or "").strip().lower()
    if not normalized:
        return False
    return normalized.startswith(FIXTURE_SLUG_PREFIXES)


def filter_real_failed_slugs(slugs: list[str]) -> list[str]:
    """実運用由来の failed slug のみを返す。"""
    return [slug for slug in slugs if not is_fixture_slug(slug)]
