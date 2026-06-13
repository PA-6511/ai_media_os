import re

REQUIRED_HEADINGS = [
    "SUMMARY",
    "LIKELY_CAUSE",
    "FILES_TO_CHECK",
    "NEXT_ACTION",
    "SAFETY_NOTES",
]

SECRET_PATTERNS = [
    re.compile(r"(?i)(token|secret|password|authorization|bearer)\s*[:=]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9_\-]{20,}\b"),
]
FILE_PATTERN = re.compile(r"[A-Za-z0-9_./\-]+\.[A-Za-z0-9_]+")


def _redact(text: str) -> str:
    sanitized = text or ""
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def _compact_lines(text: str, limit: int = 3) -> list[str]:
    lines = []
    for raw_line in (text or "").splitlines():
        line = _redact(raw_line).strip()
        if not line:
            continue
        if line not in lines:
            lines.append(line[:160])
        if len(lines) >= limit:
            break
    return lines or ["No concise log summary available."]


def _files_to_check(diff_summary: str, failing_tests: list[str]) -> list[str]:
    candidates = []
    for chunk in [diff_summary, *failing_tests]:
        for match in FILE_PATTERN.findall(chunk or ""):
            if match not in candidates:
                candidates.append(match)
    return candidates or ["auto_builder_block_ai/src", "auto_builder_block_ai/tests"]


def preprocess_codex_context(
    raw_log: str,
    diff_summary: str,
    failing_tests: list[str],
) -> str:
    summary_lines = _compact_lines(raw_log)
    likely_cause = _compact_lines("\n".join(failing_tests) or diff_summary, limit=1)
    files_to_check = _files_to_check(diff_summary, failing_tests)

    blocks = [
        "SUMMARY:\n" + "\n".join(f"- {line}" for line in summary_lines),
        "LIKELY_CAUSE:\n" + "\n".join(f"- {line}" for line in likely_cause),
        "FILES_TO_CHECK:\n" + "\n".join(f"- {line}" for line in files_to_check[:5]),
        "NEXT_ACTION:\n- Inspect the listed files and rerun the narrow dry-run validation.",
        "SAFETY_NOTES:\n- Keep credential access disabled.\n- Keep external API and production execution disabled.",
    ]
    result = "\n\n".join(blocks)

    for heading in REQUIRED_HEADINGS:
        if f"{heading}:" not in result:
            raise ValueError(f"missing required heading: {heading}")

    return result