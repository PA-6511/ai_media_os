from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = ROOT / "config/x_draft_module_contract.json"

FEEDBACK_ID_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
URL_PLACEHOLDER_HOSTS = {
    "example.com",
    "example.org",
    "example.net",
    "localhost",
}
URL_PLACEHOLDER_TOKENS = {
    "placeholder",
    "dummy",
    "sample",
    "test.invalid",
    "your-domain",
    "yourdomain",
}


class XDraftGenerationError(ValueError):
    """Raised when an X draft cannot be generated safely."""


@dataclass(frozen=True)
class XDraftInput:
    ebook_item_id: str
    title: str
    volume_label: str
    release_date: str
    category: str
    author_name: str
    article_url: str
    wordpress_draft_id: int
    wordpress_status: str


@dataclass(frozen=True)
class XDraftResult:
    feedback_id: str
    ebook_item_id: str
    wordpress_draft_id: int
    template_id: str
    generated_text: str
    character_count: int
    contains_pr: bool
    selected_url: str
    record_stage: str
    x_status: str
    review_status: str
    initialize_request: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XDraftGenerationError(message)


def load_contract(
    contract_path: Path = DEFAULT_CONTRACT_PATH,
) -> dict[str, Any]:
    require(
        contract_path.exists(),
        f"X draft contract is missing: {contract_path}",
    )

    try:
        contract = json.loads(
            contract_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise XDraftGenerationError(
            f"X draft contract contains invalid JSON: {contract_path}: {exc}"
        ) from exc

    require(
        isinstance(contract, dict),
        "X draft contract root must be an object",
    )
    require(
        contract.get("contract_id") == "X_DRAFT_MODULE_CONTRACT_V1",
        "unsupported X draft contract",
    )

    return contract


def normalize_text(value: str, field_name: str) -> str:
    require(
        isinstance(value, str),
        f"{field_name} must be a string",
    )

    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.strip()

    require(
        bool(normalized),
        f"{field_name} must not be empty",
    )

    return normalized


def validate_length(
    value: str,
    *,
    field_name: str,
    maximum: int,
) -> None:
    require(
        len(value) <= maximum,
        f"{field_name} must be at most {maximum} characters",
    )


def normalize_release_date(value: str) -> str:
    normalized = normalize_text(
        value,
        "release_date",
    )

    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise XDraftGenerationError(
            "release_date must use YYYY-MM-DD"
        ) from exc

    require(
        parsed.isoformat() == normalized,
        "release_date must use YYYY-MM-DD",
    )

    return normalized


def validate_article_url(article_url: str) -> str:
    normalized = normalize_text(article_url, "article_url")
    parsed = urlparse(normalized)

    require(
        parsed.scheme.lower() == "https",
        "article_url must use https",
    )
    require(
        bool(parsed.hostname),
        "article_url must contain a hostname",
    )
    require(
        parsed.username is None and parsed.password is None,
        "article_url must not contain credentials",
    )

    hostname = parsed.hostname.lower()

    require(
        hostname not in URL_PLACEHOLDER_HOSTS,
        "article_url placeholder host is forbidden",
    )

    lowered_url = normalized.lower()

    require(
        not any(token in lowered_url for token in URL_PLACEHOLDER_TOKENS),
        "article_url placeholder value is forbidden",
    )

    return normalized


def author_to_hashtag(author_name: str) -> str:
    normalized = normalize_text(author_name, "author_name")

    hashtag_body = re.sub(
        r"[\s\u3000・,，、/／|｜&＆]+",
        "",
        normalized,
    )
    hashtag_body = hashtag_body.replace("#", "")
    hashtag_body = re.sub(r"[^\w一-龥ぁ-んァ-ヶー]", "", hashtag_body)

    require(
        bool(hashtag_body),
        "author_name cannot be converted to a hashtag",
    )

    return f"#{hashtag_body}"


def sanitize_feedback_component(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    sanitized = FEEDBACK_ID_SAFE_PATTERN.sub("-", normalized)
    sanitized = sanitized.strip("._-")

    if sanitized:
        return sanitized[:48]

    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]

    return digest


def build_feedback_id(
    *,
    ebook_item_id: str,
    wordpress_draft_id: int,
    template_id: str,
) -> str:
    safe_item_id = sanitize_feedback_component(ebook_item_id)

    identity_source = (
        f"{ebook_item_id}|{wordpress_draft_id}|{template_id}"
    )
    identity_hash = hashlib.sha256(
        identity_source.encode("utf-8")
    ).hexdigest()[:12]

    feedback_id = (
        f"xdraft-{safe_item_id}-"
        f"wp{wordpress_draft_id}-{identity_hash}"
    )

    require(
        bool(re.fullmatch(r"[A-Za-z0-9._-]+", feedback_id)),
        "generated feedback_id is invalid",
    )

    return feedback_id


def validate_input(
    draft_input: XDraftInput,
    contract: dict[str, Any],
) -> XDraftInput:
    title = normalize_text(draft_input.title, "title")
    volume_label = normalize_text(
        draft_input.volume_label,
        "volume_label",
    )
    release_date = normalize_release_date(
        draft_input.release_date
    )
    category = normalize_text(
        draft_input.category,
        "category",
    )
    author_name = normalize_text(
        draft_input.author_name,
        "author_name",
    )
    ebook_item_id = normalize_text(
        draft_input.ebook_item_id,
        "ebook_item_id",
    )
    article_url = validate_article_url(draft_input.article_url)

    field_rules = contract["input_contract"]["field_rules"]

    validate_length(
        title,
        field_name="title",
        maximum=int(field_rules["title"]["max_length"]),
    )
    validate_length(
        volume_label,
        field_name="volume_label",
        maximum=int(field_rules["volume_label"]["max_length"]),
    )
    validate_length(
        author_name,
        field_name="author_name",
        maximum=int(field_rules["author_name"]["max_length"]),
    )

    require(
        isinstance(draft_input.wordpress_draft_id, int)
        and not isinstance(draft_input.wordpress_draft_id, bool),
        "wordpress_draft_id must be an integer",
    )
    require(
        draft_input.wordpress_draft_id
        >= int(field_rules["wordpress_draft_id"]["minimum"]),
        "wordpress_draft_id must be at least 1",
    )

    wordpress_status = normalize_text(
        draft_input.wordpress_status,
        "wordpress_status",
    ).upper()

    require(
        wordpress_status
        == field_rules["wordpress_status"]["required_value"],
        "wordpress_status must be DRAFT",
    )

    return XDraftInput(
        ebook_item_id=ebook_item_id,
        title=title,
        volume_label=volume_label,
        release_date=release_date,
        category=category,
        author_name=author_name,
        article_url=article_url,
        wordpress_draft_id=draft_input.wordpress_draft_id,
        wordpress_status=wordpress_status,
    )


def render_template(
    *,
    draft_input: XDraftInput,
    contract: dict[str, Any],
) -> str:
    generation = contract["generation_contract"]
    template_lines = generation["template_lines"]

    author_hashtag = author_to_hashtag(draft_input.author_name)

    rendered_lines = [
        str(line).format(
            title=draft_input.title,
            volume_label=draft_input.volume_label,
            author_hashtag=author_hashtag,
            article_url=draft_input.article_url,
        )
        for line in template_lines
    ]

    generated_text = "\n".join(rendered_lines)
    generated_text = unicodedata.normalize(
        generation["unicode_normalization"],
        generated_text,
    )
    generated_text = generated_text.replace(
        "\r\n",
        "\n",
    ).replace("\r", "\n")

    if generation.get("trim_outer_whitespace") is True:
        generated_text = generated_text.strip()

    return generated_text


class XDraftGenerationService:
    def __init__(
        self,
        contract_path: Path = DEFAULT_CONTRACT_PATH,
    ) -> None:
        self.contract = load_contract(contract_path)

    def generate(
        self,
        draft_input: XDraftInput,
    ) -> XDraftResult:
        require(
            isinstance(draft_input, XDraftInput),
            "draft_input must be XDraftInput",
        )

        validated = validate_input(
            draft_input,
            self.contract,
        )

        generated_text = render_template(
            draft_input=validated,
            contract=self.contract,
        )

        generation = self.contract["generation_contract"]
        output = self.contract["output_contract"]
        fixed_values = output["fixed_values"]

        maximum_character_count = int(
            generation["maximum_character_count"]
        )
        character_count = len(generated_text)
        contains_pr = "#PR" in generated_text

        require(
            bool(generated_text),
            "generated_text must not be empty",
        )
        require(
            character_count <= maximum_character_count,
            (
                "generated_text exceeds character limit: "
                f"{character_count}/{maximum_character_count}"
            ),
        )
        require(
            contains_pr,
            "generated_text must contain #PR",
        )
        require(
            validated.article_url in generated_text,
            "generated_text must contain article_url",
        )

        template_id = generation["template_id"]

        feedback_id = build_feedback_id(
            ebook_item_id=validated.ebook_item_id,
            wordpress_draft_id=validated.wordpress_draft_id,
            template_id=template_id,
        )

        initialize_request = {
            "action": "INITIALIZE",
            "feedback_id": feedback_id,
            "article_item_id": validated.ebook_item_id,
            "wordpress_post_id": validated.wordpress_draft_id,
            "template_id": template_id,
            "article_context": {
                "title": validated.title,
                "volume_label": validated.volume_label,
                "release_date": validated.release_date,
                "category": validated.category,
                "author_name": validated.author_name,
                "article_url": validated.article_url,
                "wordpress_status": validated.wordpress_status,
            },
            "generated_text": generated_text,
            "wording_labels": [
                "TITLE_FIRST",
                "ARTICLE_CTA",
                "INFORMATIONAL_TONE",
                "MULTIPLE_HASHTAGS",
            ],
        }

        return XDraftResult(
            feedback_id=feedback_id,
            ebook_item_id=validated.ebook_item_id,
            wordpress_draft_id=validated.wordpress_draft_id,
            template_id=template_id,
            generated_text=generated_text,
            character_count=character_count,
            contains_pr=contains_pr,
            selected_url=validated.article_url,
            record_stage=fixed_values["record_stage"],
            x_status=fixed_values["x_status"],
            review_status=fixed_values["review_status"],
            initialize_request=initialize_request,
        )
