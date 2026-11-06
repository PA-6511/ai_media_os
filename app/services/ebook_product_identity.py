"""Canonical ebook product identity normalization.

This module is intentionally side-effect free.
No DB access, network access, WordPress access, or runtime writes.
"""

from __future__ import annotations

import html
import re
import unicodedata


# Kobo/provider annotations which describe the electronic edition,
# not the underlying work/volume identity.
_EXACT_KOBO_EDITION_ANNOTATIONS = (
    "【2色カラー特別版】",
    "【コミックス版】",
    "【電子限定特典付】",
    "【電子限定特典付き】",
    "【電子限定特典つき】",
    "【電子限定特典ペーパー付き】",
    "【電子単行本限定特典付き】",
    "【電子特別版】",
    "【単行本版】",
)


def strip_kobo_edition_annotations(value: str) -> str:
    """Remove known Kobo electronic-edition annotations only.

    Work title and volume identity are preserved. In particular, 上/下 and
    numeric volume designators are never removed or made equivalent here.
    """

    normalized = str(value or "")

    for annotation in _EXACT_KOBO_EDITION_ANNOTATIONS:
        normalized = normalized.replace(annotation, "")

    # Kobo has multiple free-text forms of electronic-only bonuses:
    #   【電子限定描き下ろし漫画付き】
    #   【電子限定描きおろし特典付き】
    #
    # Restrict removal to bracket annotations explicitly containing
    # 電子限定 or 電子単行本限定. Ordinary bracketed title text remains.
    normalized = re.sub(
        r"【[^【】]*(?:電子限定|電子単行本限定)[^【】]*】",
        "",
        normalized,
    )

    return normalized


# COV7C_KOBO_COVER_PROVIDER_VARIANTS_V1

_EXACT_KOBO_COVER_BONUS_ANNOTATIONS = (
    "【特典ペーパー付き】",
    "【イラスト特典付】",
    "【電子版特典付き】",
    "【電子特典付き】",
)


def strip_kobo_cover_bonus_annotations(
    value: str,
) -> str:
    """Remove provider-only bonus labels for cover identity only.

    This deliberately does not remove meaningful edition labels such as
    特装版 or ordinary 【電子単行本】.
    """

    normalized = str(
        value or ""
    )

    for annotation in (
        _EXACT_KOBO_COVER_BONUS_ANNOTATIONS
    ):
        normalized = normalized.replace(
            annotation,
            "",
        )

    # Provider notation:
    #   作品名3(特典付き)
    #
    # Restrict this to an entire parenthetical bonus annotation.
    normalized = re.sub(
        r"\((?:電子)?特典(?:付き|付)\)",
        "",
        normalized,
    )

    return normalized


# PI2B_SHARED_PRODUCT_IDENTITY_CORE_V1


def normalize_visible_title_text(
    value: str,
) -> str:
    """Normalize HTML entities and visible whitespace only.

    This intentionally does not remove edition, volume, catalog,
    or other semantic title tokens.
    """

    return re.sub(
        r"\s+",
        " ",
        html.unescape(
            str(value or "")
        ),
    ).strip()


def kobo_identity_title_candidates(
    value: str,
) -> tuple[str, ...]:
    """Return the full title plus one safe catalog-suffix-free candidate.

    This preserves the existing Kobo resolver behavior: only a trailing
    ASCII parenthetical segment preceded by whitespace is offered as an
    alternate candidate. The original normalized title is always retained.
    """

    normalized = unicodedata.normalize(
        "NFKC",
        normalize_visible_title_text(
            value
        ),
    )

    if not normalized:
        return ()

    without_catalog_suffix = re.sub(
        r"\s+\([^()]{1,120}\)\s*$",
        "",
        normalized,
    ).strip()

    if (
        without_catalog_suffix
        and without_catalog_suffix
        != normalized
    ):
        return (
            normalized,
            without_catalog_suffix,
        )

    return (normalized,)


def normalize_kobo_title_identity(
    value: str,
) -> str:
    """Canonical Kobo title identity used by the strict resolver path.

    This is a side-effect-free extraction of the current resolver rules.
    It deliberately preserves work and volume distinctions.
    """

    normalized = normalize_visible_title_text(
        unicodedata.normalize(
            "NFKC",
            str(value or ""),
        )
    )

    normalized = strip_kobo_edition_annotations(
        normalized
    )

    # Storefront promotional wrappers are not work identity.
    normalized = re.sub(
        r"【[^【】]*(?:期間限定|試し読み|お試し)[^【】]*】",
        "",
        normalized,
    )

    normalized = normalize_visible_title_text(
        normalized
    )

    # Typographic spacing around punctuation variants.
    normalized = re.sub(
        r"(?<=[!！〜～])\s+|\s+(?=[!！〜～])",
        "",
        normalized,
    )

    # Existing Kobo resolver contract:
    #   "25 -subtitle" and "25 ーsubtitle"
    # are equivalent typographic separators.
    normalized = re.sub(
        r"\s+(?=[0-9])|(?<=[0-9])\s*[\-ー]\s*",
        "",
        normalized,
    )

    # Explicit parenthetical volume.
    normalized = re.sub(
        r"[（(]\s*([0-9]+)\s*[）)]",
        r"〔\1〕",
        normalized,
    )

    # Bare trailing numeric volume.
    normalized = re.sub(
        r"(?<![0-9])([0-9]{1,3})$",
        r"〔\1〕",
        normalized,
    )

    return normalized


def matches_kobo_title_identity(
    *,
    requested_candidates: tuple[str, ...],
    provider_title: str,
) -> bool:
    """Compare requested/provider titles using the canonical Kobo identity."""

    provider_identity = (
        normalize_kobo_title_identity(
            provider_title
        )
    )

    return any(
        provider_identity
        == normalize_kobo_title_identity(
            candidate
        )
        for candidate in requested_candidates
    )


def normalize_kobo_cover_title_identity(
    value: str,
) -> str:
    """Additional legacy cover-identity normalization.

    These rules reproduce the existing VerifiedCover fallback behavior.
    They are kept separate from the strict Kobo resolver identity so the
    PI-2 migration does not silently broaden resolver matching.
    """

    normalized = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    )

    # Equivalent Japanese wave-dash characters.
    normalized = (
        normalized
        .replace("〜", "~")
        .replace("～", "~")
    )

    normalized = strip_kobo_edition_annotations(
        normalized
    )

    normalized = strip_kobo_cover_bonus_annotations(
        normalized
    )

    # Legacy provider notation.
    normalized = normalized.replace(
        "(コミック)",
        "",
    )

    # COV7C_LATIN_WRAPPER_DASH_V1
    # Normalize only a paired delimiter surrounding a Latin phrase.
    # Japanese word-internal long-vowel marks remain identity-significant.
    normalized = re.sub(
        r"[-ー]\s*"
        r"([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z0-9]+)*)"
        r"\s*[-ー]",
        r"-\1-",
        normalized,
    )

    # Remove only comic/catalog-like trailing labels.
    normalized = re.sub(
        r"\s*\([^()]*(?:"
        r"コミックス|コミック|COMICS|"
        r"アクションコミックス|"
        r"コミックス・エース|"
        r"モンスターコミックス"
        r")[^()]*\)\s*$",
        "",
        normalized,
        flags=re.I,
    )

    # XNR_0917_COVER_SEPARATOR_COMPAT_V1
    #
    # Rakuten Kobo product pages serialize title separators with
    # several visually-equivalent dash characters.  Keep this
    # compatibility inside the legacy cover fallback only; the
    # strict Kobo resolver identity remains unchanged.
    normalized = (
        normalized
        .replace("’", "'")
        .replace("‘", "'")
        .replace("ʼ", "'")
        .replace("―", "ー")
        .replace("‐", "ー")
        .replace("‒", "ー")
        .replace("–", "ー")
        .replace("—", "ー")
        .replace("−", "ー")
    )

    # Do not globally rewrite ASCII "-".  It is meaningful inside
    # Latin titles such as "BUNGO-unreal-".  Normalize it only when
    # its surrounding context makes it a Japanese title separator.
    japanese = r"\u3040-\u30ff\u3400-\u9fff"

    normalized = re.sub(
        rf"(?<=[{japanese}])\s*-\s*(?=[{japanese}])",
        "ー",
        normalized,
    )

    # e.g. 90's-音速...
    normalized = re.sub(
        rf"(?<=[A-Za-z0-9'])\s*-\s*(?=[{japanese}])",
        "ー",
        normalized,
    )

    # e.g. 最終章 -（9）
    normalized = re.sub(
        rf"(?<=[{japanese}])\s*-\s*(?=(?:\(?\d|$))",
        "ー",
        normalized,
    )

    # Equivalent numeric volume notation:
    # 第20巻 / 20巻 -> 20
    normalized = re.sub(
        r"第?0*(\d+)巻",
        lambda match: str(
            int(match.group(1))
        ),
        normalized,
    )

    # (20) / （20） after NFKC -> (20)
    normalized = re.sub(
        r"\(0*(\d+)\)",
        lambda match: str(
            int(match.group(1))
        ),
        normalized,
    )

    # Trailing :20 / ：20 after NFKC.
    normalized = re.sub(
        r"\s*:\s*0*(\d+)(?=\s*$)",
        lambda match: str(
            int(match.group(1))
        ),
        normalized,
    )

    # Kobo storefront trailing slash-volume.
    normalized = re.sub(
        r"\s*/\s*0*(\d+)(?=\s*$)",
        lambda match: str(
            int(match.group(1))
        ),
        normalized,
    )

    # COV7C_SPECIAL_EDITION_VOLUME_ORDER_V1
    # Keep 特装版 semantically significant; canonicalize order only.
    normalized = re.sub(
        r"(?<!\d)(\d{1,3})\s*特装版(?=\s*$)",
        lambda match: (
            "特装版"
            + str(
                int(
                    match.group(1)
                )
            )
        ),
        normalized,
    )

    # Equivalent ellipsis representations.
    normalized = (
        normalized
        .replace("・・・", "…")
        .replace("...", "…")
    )

    normalized = re.sub(
        r"…+",
        "…",
        normalized,
    )

    # Existing cover fallback ignores remaining whitespace.
    return re.sub(
        r"\s+",
        "",
        normalized,
    )


# XNR_0917_COVER_EXACT_DUPLICATE_WORK_V1
def _kobo_cover_title_candidates(
    value: str,
) -> tuple[str, ...]:
    """Return cover-only identity candidates.

    In addition to the shared strict candidates, accept one narrowly
    bounded importer artifact:

        <work> <volume> <same exact work>

    Example:
        作品名 1 作品名

    The repeated work text must be exactly identical.  No fuzzy
    substring removal is performed and the volume is preserved.
    """

    candidates = list(
        kobo_identity_title_candidates(
            value
        )
    )

    for candidate in tuple(candidates):
        visible = normalize_visible_title_text(
            unicodedata.normalize(
                "NFKC",
                candidate,
            )
        )

        match = re.fullmatch(
            r"(.+?)\s+([0-9]{1,3})\s+\1",
            visible,
        )

        if match is None:
            continue

        work = match.group(1).strip()

        if not work:
            continue

        volume = str(
            int(
                match.group(2)
            )
        )

        reduced = f"{work} {volume}"

        if reduced not in candidates:
            candidates.append(
                reduced
            )

    return tuple(candidates)



def _kobo_cover_bounded_surface_variants(
    value: str,
) -> tuple[str, ...]:
    """Cover-only, narrowly bounded retailer/importer title variants."""

    base = normalize_visible_title_text(
        unicodedata.normalize(
            "NFKC",
            str(value or ""),
        )
    ).strip()

    variants: list[str] = []

    def add(candidate: str) -> None:
        candidate = candidate.strip()
        if candidate and candidate not in variants:
            variants.append(candidate)

    add(base)

    # Kobo may append a retailer benefit suffix that is not part
    # of the bibliographic work identity.
    for current in tuple(variants):
        add(
            re.sub(
                r"\s*【[^】]*特典[^】]*】\s*$",
                "",
                current,
            )
        )

    # Decorative wave marks around the exact semantic token 外伝
    # are display punctuation only.
    for current in tuple(variants):
        add(
            re.sub(
                r"[〜～~]+\s*外伝\s*[〜～~]+",
                "外伝",
                current,
            )
        )

    # COV_R4_ZERO_PADDED_TERMINAL_VOLUME_V1
    # Importers may preserve a zero-padded terminal volume (01)
    # while Kobo exposes the same volume canonically as 1.
    # Only a standalone numeric token at the end is normalized.
    for current in tuple(variants):
        add(
            re.sub(
                r"(?<=\s)0+([1-9][0-9]{0,2})\s*$",
                lambda match: str(
                    int(match.group(1))
                ),
                current,
            )
        )

    # Kobo sometimes inserts the exact media marker コミック版
    # immediately before the terminal volume.
    for current in tuple(variants):
        add(
            re.sub(
                r"\s+コミック版"
                r"(?=\s*(?:\(\s*\d{1,3}\s*\)|\d{1,3})\s*$)",
                "",
                current,
            )
        )

    # Importer artifact:
    #   鈴木りつ第二短編集 ... 鈴木りつ短編集
    # Remove only the redundant terminal <same stem>短編集 when
    # the title already begins with <same stem>第N短編集.
    for current in tuple(variants):
        match = re.match(
            r"^(.+?)第"
            r"[一二三四五六七八九十百0-9]+"
            r"短編集(?:\s|$)",
            current,
        )

        if match is None:
            continue

        stem = match.group(1).strip()

        if not stem:
            continue

        redundant = stem + "短編集"
        suffix = " " + redundant

        if current.endswith(suffix):
            add(
                current[:-len(suffix)].rstrip()
            )

    return tuple(variants)


def matches_kobo_cover_title_identity(
    *,
    requested_title: str,
    provider_title: str,
) -> bool:
    """Full current cover-title equivalence without consumer dependencies."""

    # PI6D4_EMPTY_WORK_IDENTITY_FAIL_CLOSED_V1
    # Annotation-only or promotion-only text normalizes to an empty
    # strict identity and is not evidence of a work identity.
    if not normalize_kobo_title_identity(
        requested_title
    ):
        return False

    if not normalize_kobo_title_identity(
        provider_title
    ):
        return False

    candidates = _kobo_cover_title_candidates(
        requested_title
    )

    if matches_kobo_title_identity(
        requested_candidates=candidates,
        provider_title=provider_title,
    ):
        return True

    provider_identities = {
        provider_identity
        for provider_identity in (
            normalize_kobo_cover_title_identity(
                provider_variant
            )
            for provider_variant
            in _kobo_cover_bounded_surface_variants(
                provider_title
            )
        )
        # A variant reduced to nothing carries no work identity.
        if provider_identity
    }

    return any(
        normalize_kobo_cover_title_identity(
            requested_variant
        )
        in provider_identities
        for candidate in candidates
        for requested_variant
        in _kobo_cover_bounded_surface_variants(
            candidate
        )
    )

