from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date


class SupplementParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedSupplementCandidate:
    title: str
    volume_label: str | None
    release_date: date
    publisher_name: str | None
    author_name: str | None
    imprint_name: str | None
    raw_text: str
    parser_confidence: str
    parser_warnings: tuple[str, ...]


_IGNORED_EXACT = {
    "漫画",
    "コミック",
    "本",
    "前へ",
    "次へ",
    "画像",
    "画像なし",
}
_MONTH_OR_DAY = re.compile(r"^\d{1,2}\s*(?:月|日)$")
_WEEKDAY = re.compile(r"^(?:月|火|水|木|金|土|日)(?:曜日|曜)?$")
_VOLUME_PAREN = re.compile(r"\s*[\(（]\s*(\d+)\s*(?:巻)?\s*[\)）]\s*$")
_VOLUME_EXPLICIT = re.compile(r"\s*第\s*(\d+)\s*巻\s*$")
_VOLUME_BARE = re.compile(r"\s+(\d+)\s*$")
_TRAILING_PAREN = re.compile(r"\s*[\(（]([^()（）]+)[\)）]\s*$")
_STANDALONE_VOLUME = re.compile(r"^\d+$")
_ASCII_TITLE_WITH_NUMBER = re.compile(r"[A-Za-z!！:：×xX].*\d+$")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_author(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).strip()


def _is_ignored_line(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized:
        return True
    return (
        normalized in _IGNORED_EXACT
        or bool(_MONTH_OR_DAY.fullmatch(normalized))
        or bool(_WEEKDAY.fullmatch(normalized))
        or normalized.startswith("楽天ブックス")
        or normalized.startswith("新刊カレンダー")
    )


def _looks_like_title_line(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized or _STANDALONE_VOLUME.fullmatch(normalized):
        return False
    _, volume_label, _, _ = split_title_volume_imprint(normalized)
    return volume_label is not None or bool(
        _ASCII_TITLE_WITH_NUMBER.search(normalized)
    )


def split_title_volume_imprint(
    value: str,
) -> tuple[str, str | None, str | None, tuple[str, ...]]:
    working = normalize_text(value)
    warnings: list[str] = []
    imprint_name: str | None = None

    trailing_parenthesis = _TRAILING_PAREN.search(working)
    if trailing_parenthesis and not re.fullmatch(
        r"\d+\s*(?:巻)?", trailing_parenthesis.group(1)
    ):
        prefix = working[: trailing_parenthesis.start()].rstrip()
        if (
            _VOLUME_PAREN.search(prefix)
            or _VOLUME_EXPLICIT.search(prefix)
            or _VOLUME_BARE.search(prefix)
        ):
            imprint_name = normalize_text(trailing_parenthesis.group(1))
            working = prefix

    volume_label: str | None = None
    parenthesized_volume = _VOLUME_PAREN.search(working)
    if parenthesized_volume:
        volume_label = str(int(parenthesized_volume.group(1)))
        working = working[: parenthesized_volume.start()].rstrip()
        repeated_bare = _VOLUME_BARE.search(working)
        if repeated_bare and str(int(repeated_bare.group(1))) == volume_label:
            working = working[: repeated_bare.start()].rstrip()
    else:
        explicit_volume = _VOLUME_EXPLICIT.search(working)
        if explicit_volume:
            volume_label = str(int(explicit_volume.group(1)))
            working = working[: explicit_volume.start()].rstrip()
        else:
            bare_volume = _VOLUME_BARE.search(working)
            if bare_volume:
                volume_label = str(int(bare_volume.group(1)))
                working = working[: bare_volume.start()].rstrip()

    title = normalize_text(working)
    if not title:
        warnings.append("TITLE_MISSING")
    return title, volume_label, imprint_name, tuple(warnings)


def parse_rakuten_comic_calendar_text(
    raw_text: str,
    *,
    target_release_date: date,
) -> tuple[ParsedSupplementCandidate, ...]:
    if not raw_text or not raw_text.strip():
        raise SupplementParseError("EMPTY_TEXT")

    source_lines = [line for line in raw_text.splitlines() if not _is_ignored_line(line)]
    candidates: list[ParsedSupplementCandidate] = []

    offset = 0
    while offset < len(source_lines):
        block = source_lines[offset : offset + 3]
        raw_block = "\n".join(block).strip()
        current = source_lines[offset]
        following = source_lines[offset + 1 : offset + 3]
        title, volume_label, imprint_name, warnings = split_title_volume_imprint(
            current
        )

        if (
            volume_label is None
            and following
            and _STANDALONE_VOLUME.fullmatch(normalize_text(following[0]))
        ):
            volume_label = str(int(normalize_text(following[0])))
            candidates.append(
                ParsedSupplementCandidate(
                    title=title,
                    volume_label=volume_label,
                    release_date=target_release_date,
                    publisher_name=None,
                    author_name=None,
                    imprint_name=imprint_name,
                    raw_text="\n".join(source_lines[offset : offset + 2]),
                    parser_confidence="REVIEW_REQUIRED",
                    parser_warnings=("METADATA_MISSING",),
                )
            )
            offset += 2
            continue

        adjacent_title = any(_looks_like_title_line(line) for line in following)
        if len(block) < 3 or adjacent_title:
            confidence = (
                "REVIEW_REQUIRED" if volume_label is not None else "UNPARSED"
            )
            candidates.append(
                ParsedSupplementCandidate(
                    title=title,
                    volume_label=volume_label,
                    release_date=target_release_date,
                    publisher_name=None,
                    author_name=None,
                    imprint_name=imprint_name,
                    raw_text=current,
                    parser_confidence=confidence,
                    parser_warnings=(
                        "ADJACENT_TITLE_BOUNDARY"
                        if adjacent_title
                        else "INCOMPLETE_BLOCK",
                    ),
                )
            )
            offset += 1
            continue

        confidence = "HIGH"
        if not title:
            confidence = "UNPARSED"
        elif warnings or volume_label is None:
            confidence = "REVIEW_REQUIRED"

        candidates.append(
            ParsedSupplementCandidate(
                title=title,
                volume_label=volume_label,
                release_date=target_release_date,
                publisher_name=normalize_text(block[1]) or None,
                author_name=normalize_author(block[2]) or None,
                imprint_name=imprint_name,
                raw_text=raw_block,
                parser_confidence=confidence,
                parser_warnings=warnings,
            )
        )
        offset += 3

    if not candidates:
        raise SupplementParseError("NO_PARSEABLE_ITEMS")
    return tuple(candidates)
