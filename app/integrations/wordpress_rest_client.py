from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Mapping
from urllib import error, request
from urllib.parse import urlencode, urlparse


class WordPressTransportError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "remote_unavailable",
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


@dataclass(frozen=True)
class WordPressDraftResponse:
    post_id: int
    status: str
    link: str | None = None
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    featured_media: int | None = None
    date: str | None = None
    date_gmt: str | None = None
    categories: tuple[int, ...] = ()


@dataclass(frozen=True)
class WordPressCategory:
    category_id: int
    name: str
    slug: str
    count: int


@dataclass(frozen=True)
class WordPressMediaResponse:
    media_id: int
    source_url: str
    mime_type: str


@dataclass(frozen=True)
class WordPressAffiliateMetaResponse:
    post_id: int
    title: str
    meta: dict[str, str]


WORDPRESS_AFFILIATE_META_KEYS = frozenset(
    {"kindle_url", "rakuten_kobo_url", "dmm_url"}
)


class WordPressRestClient:
    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        application_password: str,
        timeout_seconds: int = 30,
        opener: Any | None = None,
    ) -> None:
        normalized_base = (base_url or "").strip().rstrip("/")
        parsed = urlparse(normalized_base)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")

        normalized_username = (username or "").strip()
        normalized_password = (application_password or "").strip()

        if not normalized_username:
            raise ValueError("username is required")

        if not normalized_password:
            raise ValueError("application_password is required")

        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")

        if normalized_base.endswith("/wp-json/wp/v2"):
            self.rest_base = normalized_base
        else:
            self.rest_base = normalized_base + "/wp-json/wp/v2"

        self.username = normalized_username
        self.application_password = normalized_password
        self.timeout_seconds = timeout_seconds
        self.opener = opener or request.build_opener()

    @property
    def posts_endpoint(self) -> str:
        return self.rest_base + "/posts"

    @property
    def media_endpoint(self) -> str:
        return self.rest_base + "/media"

    @property
    def categories_endpoint(self) -> str:
        return self.rest_base + "/categories"

    def post_endpoint(self, post_id: int) -> str:
        if (
            isinstance(post_id, bool)
            or not isinstance(post_id, int)
            or post_id <= 0
        ):
            raise ValueError(
                "post_id must be a positive integer"
            )

        return self.posts_endpoint + f"/{post_id}"

    def create_draft(
        self,
        payload: Mapping[str, Any],
    ) -> WordPressDraftResponse:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")

        request_payload = dict(payload)

        if request_payload.get("status") != "draft":
            raise ValueError("WordPress payload status must be draft")

        if not str(request_payload.get("title") or "").strip():
            raise ValueError("WordPress payload title is required")

        if not str(request_payload.get("content") or "").strip():
            raise ValueError("WordPress payload content is required")

        body = json.dumps(
            request_payload,
            ensure_ascii=False,
        ).encode("utf-8")

        credential = (
            f"{self.username}:{self.application_password}"
        ).encode("utf-8")

        encoded_credential = base64.b64encode(
            credential
        ).decode("ascii")

        http_request = request.Request(
            self.posts_endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": "Basic " + encoded_credential,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )

        try:
            with self.opener.open(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_response = response.read()

        except error.HTTPError as exc:
            raise WordPressTransportError(
                f"WordPress HTTP error: {exc.code}"
            ) from exc

        except error.URLError as exc:
            raise WordPressTransportError(
                "WordPress transport failed"
            ) from exc

        try:
            response_payload = json.loads(
                raw_response.decode("utf-8")
            )

        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WordPressTransportError(
                "WordPress returned invalid JSON"
            ) from exc

        if not isinstance(response_payload, dict):
            raise WordPressTransportError(
                "WordPress response must be an object"
            )

        post_id = response_payload.get("id")
        status = response_payload.get("status")
        link = response_payload.get("link")

        if (
            isinstance(post_id, bool)
            or not isinstance(post_id, int)
            or post_id <= 0
        ):
            raise WordPressTransportError(
                "WordPress response has invalid post id"
            )

        if status != "draft":
            raise WordPressTransportError(
                "WordPress did not return draft status"
            )

        if link is not None and not isinstance(link, str):
            raise WordPressTransportError(
                "WordPress response link is invalid"
            )

        return WordPressDraftResponse(
            post_id=post_id,
            status=status,
            link=link,
        )

    def get_draft(
        self,
        *,
        post_id: int,
    ) -> WordPressDraftResponse:
        endpoint = (
            self.post_endpoint(post_id)
            + "?context=edit"
        )

        credential = (
            f"{self.username}:{self.application_password}"
        ).encode("utf-8")

        encoded_credential = base64.b64encode(
            credential
        ).decode("ascii")

        http_request = request.Request(
            endpoint,
            method="GET",
            headers={
                "Authorization": (
                    "Basic " + encoded_credential
                ),
                "Accept": "application/json",
            },
        )

        try:
            with self.opener.open(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_response = response.read()

        except error.HTTPError as exc:
            raise WordPressTransportError(
                "WordPress draft preflight HTTP error: "
                f"{exc.code}"
            ) from exc

        except error.URLError as exc:
            raise WordPressTransportError(
                "WordPress draft preflight "
                "transport failed"
            ) from exc

        try:
            response_payload = json.loads(
                raw_response.decode("utf-8")
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise WordPressTransportError(
                "WordPress draft preflight returned "
                "invalid JSON"
            ) from exc

        if not isinstance(response_payload, dict):
            raise WordPressTransportError(
                "WordPress draft preflight response "
                "must be an object"
            )

        response_post_id = response_payload.get("id")
        status = response_payload.get("status")
        link = response_payload.get("link")
        featured_media = response_payload.get("featured_media")
        raw_categories = response_payload.get("categories", [])

        def editable_text(field_name: str) -> str | None:
            value = response_payload.get(field_name)
            if value is None:
                return None
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                raw = value.get("raw")
                if isinstance(raw, str):
                    return raw
                rendered = value.get("rendered")
                if isinstance(rendered, str):
                    return rendered
            raise WordPressTransportError(
                f"WordPress draft {field_name} is invalid"
            )

        if response_post_id != post_id:
            raise WordPressTransportError(
                "WordPress draft preflight returned "
                "the wrong post id"
            )

        if status != "draft":
            raise WordPressTransportError(
                "WordPress live post is not draft"
            )

        if link is not None and not isinstance(link, str):
            raise WordPressTransportError(
                "WordPress draft preflight link "
                "is invalid"
            )

        if featured_media is not None and (
            isinstance(featured_media, bool)
            or not isinstance(featured_media, int)
            or featured_media < 0
        ):
            raise WordPressTransportError(
                "WordPress draft featured_media is invalid"
            )
        if not isinstance(raw_categories, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in raw_categories
        ):
            raise WordPressTransportError(
                "WordPress draft categories are invalid"
            )

        return WordPressDraftResponse(
            post_id=response_post_id,
            status=status,
            link=link,
            title=editable_text("title"),
            content=editable_text("content"),
            excerpt=editable_text("excerpt"),
            featured_media=featured_media,
            categories=tuple(raw_categories),
        )

    def find_posts_by_slug(
        self,
        *,
        slug: str,
    ) -> list[WordPressDraftResponse]:
        normalized_slug = str(slug or "").strip()
        if not normalized_slug:
            raise ValueError("slug is required")
        endpoint = self.posts_endpoint + "?" + urlencode({
            "context": "edit",
            "slug": normalized_slug,
            "status": "any",
            "per_page": 10,
        })
        credential = f"{self.username}:{self.application_password}".encode(
            "utf-8"
        )
        http_request = request.Request(
            endpoint,
            method="GET",
            headers={
                "Authorization": "Basic " + base64.b64encode(
                    credential
                ).decode("ascii"),
                "Accept": "application/json",
            },
        )
        try:
            with self.opener.open(
                http_request, timeout=self.timeout_seconds
            ) as response:
                raw_response = response.read()
        except error.HTTPError as exc:
            raise WordPressTransportError(
                f"WordPress slug lookup HTTP error: {exc.code}"
            ) from exc
        except error.URLError as exc:
            raise WordPressTransportError(
                "WordPress slug lookup transport failed"
            ) from exc
        try:
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WordPressTransportError(
                "WordPress slug lookup returned invalid JSON"
            ) from exc
        if not isinstance(payload, list):
            raise WordPressTransportError(
                "WordPress slug lookup response must be an array"
            )
        results: list[WordPressDraftResponse] = []
        for value in payload:
            if not isinstance(value, Mapping):
                raise WordPressTransportError(
                    "WordPress slug lookup item is invalid"
                )
            post_id = value.get("id")
            status = value.get("status")
            if (
                isinstance(post_id, bool)
                or not isinstance(post_id, int)
                or post_id <= 0
                or not isinstance(status, str)
            ):
                raise WordPressTransportError(
                    "WordPress slug lookup identity is invalid"
                )
            results.append(WordPressDraftResponse(
                post_id=post_id,
                status=status,
                link=value.get("link") if isinstance(value.get("link"), str) else None,
            ))
        return results

    def upload_media(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> WordPressMediaResponse:
        normalized_filename = (filename or "").strip()

        if not normalized_filename:
            raise ValueError("filename is required")

        if any(
            character in normalized_filename
            for character in (
                "/",
                "\\",
                "\r",
                "\n",
                '"',
            )
        ):
            raise ValueError(
                "filename contains forbidden characters"
            )

        if content_type != "image/jpeg":
            raise ValueError(
                "content_type must be image/jpeg"
            )

        if not isinstance(content, bytes):
            raise ValueError("content must be bytes")

        if len(content) <= 1000:
            raise ValueError(
                "media content is unexpectedly small"
            )

        if not content.startswith(b"\xff\xd8"):
            raise ValueError(
                "media content must be JPEG"
            )

        credential = (
            f"{self.username}:{self.application_password}"
        ).encode("utf-8")

        encoded_credential = base64.b64encode(
            credential
        ).decode("ascii")

        http_request = request.Request(
            self.media_endpoint,
            data=content,
            method="POST",
            headers={
                "Authorization": (
                    "Basic " + encoded_credential
                ),
                "Content-Type": content_type,
                "Content-Disposition": (
                    'attachment; filename="'
                    + normalized_filename
                    + '"'
                ),
                "Accept": "application/json",
            },
        )

        try:
            with self.opener.open(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_response = response.read()

        except error.HTTPError as exc:
            raise WordPressTransportError(
                "WordPress media HTTP error: "
                f"{exc.code}"
            ) from exc

        except error.URLError as exc:
            raise WordPressTransportError(
                "WordPress media transport failed"
            ) from exc

        try:
            response_payload = json.loads(
                raw_response.decode("utf-8")
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise WordPressTransportError(
                "WordPress media returned invalid JSON"
            ) from exc

        if not isinstance(response_payload, dict):
            raise WordPressTransportError(
                "WordPress media response must be an object"
            )

        media_id = response_payload.get("id")
        source_url = response_payload.get("source_url")
        mime_type = response_payload.get("mime_type")

        if (
            isinstance(media_id, bool)
            or not isinstance(media_id, int)
            or media_id <= 0
        ):
            raise WordPressTransportError(
                "WordPress media response has invalid id"
            )

        if (
            not isinstance(source_url, str)
            or not source_url.startswith("https://")
        ):
            raise WordPressTransportError(
                "WordPress media source URL is invalid"
            )

        if mime_type != "image/jpeg":
            raise WordPressTransportError(
                "WordPress media MIME type is invalid"
            )

        return WordPressMediaResponse(
            media_id=media_id,
            source_url=source_url,
            mime_type=mime_type,
        )

    def update_draft(
        self,
        *,
        post_id: int,
        payload: Mapping[str, Any],
    ) -> WordPressDraftResponse:
        endpoint = self.post_endpoint(post_id)

        if not isinstance(payload, Mapping):
            raise ValueError(
                "payload must be a mapping"
            )

        request_payload = dict(payload)

        requested_status = request_payload.get(
            "status"
        )

        if (
            requested_status is not None
            and requested_status != "draft"
        ):
            raise ValueError(
                "WordPress update status must be draft"
            )

        request_payload["status"] = "draft"

        featured_media = request_payload.get(
            "featured_media"
        )

        if featured_media is not None and (
            isinstance(featured_media, bool)
            or not isinstance(featured_media, int)
            or featured_media <= 0
        ):
            raise ValueError(
                "featured_media must be a positive integer"
            )

        if not any(
            key in request_payload
            for key in (
                "title",
                "content",
                "excerpt",
                "featured_media",
            )
        ):
            raise ValueError(
                "draft update has no editable fields"
            )

        body = json.dumps(
            request_payload,
            ensure_ascii=False,
        ).encode("utf-8")

        credential = (
            f"{self.username}:{self.application_password}"
        ).encode("utf-8")

        encoded_credential = base64.b64encode(
            credential
        ).decode("ascii")

        http_request = request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": (
                    "Basic " + encoded_credential
                ),
                "Content-Type": (
                    "application/json; charset=utf-8"
                ),
                "Accept": "application/json",
            },
        )

        try:
            with self.opener.open(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_response = response.read()

        except error.HTTPError as exc:
            raise WordPressTransportError(
                "WordPress draft update HTTP error: "
                f"{exc.code}"
            ) from exc

        except error.URLError as exc:
            raise WordPressTransportError(
                "WordPress draft update transport failed"
            ) from exc

        try:
            response_payload = json.loads(
                raw_response.decode("utf-8")
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise WordPressTransportError(
                "WordPress draft update returned "
                "invalid JSON"
            ) from exc

        if not isinstance(response_payload, dict):
            raise WordPressTransportError(
                "WordPress draft update response "
                "must be an object"
            )

        response_post_id = response_payload.get("id")
        status = response_payload.get("status")
        link = response_payload.get("link")

        if response_post_id != post_id:
            raise WordPressTransportError(
                "WordPress draft update returned "
                "the wrong post id"
            )

        if status != "draft":
            raise WordPressTransportError(
                "WordPress draft update did not "
                "return draft status"
            )

        if link is not None and not isinstance(link, str):
            raise WordPressTransportError(
                "WordPress draft update link is invalid"
            )

        return WordPressDraftResponse(
            post_id=response_post_id,
            status=status,
            link=link,
        )

    def get_post_state(
        self,
        *,
        post_id: int,
    ) -> WordPressDraftResponse:
        endpoint = self.post_endpoint(post_id) + "?context=edit"
        http_request = request.Request(
            endpoint,
            method="GET",
            headers={
                "Authorization": "Basic " + self._encoded_credential(),
                "Accept": "application/json",
            },
        )
        payload = self._open_json(
            http_request,
            error_prefix="WordPress post state",
        )
        return self._parse_schedule_response(
            payload,
            post_id=post_id,
            allowed_statuses={
                "draft",
                "future",
                "publish",
                "pending",
                "private",
                "trash",
            },
        )

    def get_media(self, *, media_id: int) -> WordPressMediaResponse:
        if isinstance(media_id, bool) or not isinstance(media_id, int) or media_id <= 0:
            raise ValueError("media_id must be a positive integer")
        http_request = request.Request(
            self.media_endpoint + f"/{media_id}?context=edit",
            method="GET",
            headers={
                "Authorization": "Basic " + self._encoded_credential(),
                "Accept": "application/json",
            },
        )
        payload = self._open_json(
            http_request,
            error_prefix="WordPress media read",
        )
        if payload.get("id") != media_id:
            raise WordPressTransportError("WordPress media returned the wrong id")
        source_url = payload.get("source_url")
        mime_type = payload.get("mime_type")
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            raise WordPressTransportError("WordPress media source URL is invalid")
        if not isinstance(mime_type, str) or not mime_type.startswith("image/"):
            raise WordPressTransportError("WordPress media MIME type is invalid")
        return WordPressMediaResponse(media_id, source_url, mime_type)

    def get_post_affiliate_meta(
        self,
        *,
        post_id: int,
    ) -> WordPressAffiliateMetaResponse:
        endpoint = (
            self.post_endpoint(post_id)
            + "?context=edit&_fields=id,title,meta"
        )
        http_request = request.Request(
            endpoint,
            method="GET",
            headers={
                "Authorization": "Basic " + self._encoded_credential(),
                "Accept": "application/json",
            },
        )
        payload = self._open_json(
            http_request,
            error_prefix="WordPress affiliate meta read",
        )
        return self._parse_affiliate_meta_response(payload, post_id=post_id)

    def update_post_affiliate_meta(
        self,
        *,
        post_id: int,
        meta: Mapping[str, str],
    ) -> WordPressAffiliateMetaResponse:
        request_meta = dict(meta)
        if not request_meta:
            raise ValueError("affiliate meta update must not be empty")
        if set(request_meta) - WORDPRESS_AFFILIATE_META_KEYS:
            raise ValueError("affiliate meta update contains forbidden keys")
        if any(
            not isinstance(value, str) or not value.strip()
            for value in request_meta.values()
        ):
            raise ValueError("affiliate meta values must be non-empty strings")
        request_meta = {
            key: value.strip() for key, value in request_meta.items()
        }
        http_request = request.Request(
            self.post_endpoint(post_id),
            data=json.dumps(
                {"meta": request_meta},
                ensure_ascii=False,
            ).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": "Basic " + self._encoded_credential(),
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        payload = self._open_json(
            http_request,
            error_prefix="WordPress affiliate meta update",
        )
        response = self._parse_affiliate_meta_response(
            payload,
            post_id=post_id,
        )
        if any(response.meta.get(key) != value for key, value in request_meta.items()):
            raise WordPressTransportError(
                "WordPress affiliate meta update was not confirmed"
            )
        return response

    @staticmethod
    def _parse_affiliate_meta_response(
        payload: Mapping[str, Any],
        *,
        post_id: int,
    ) -> WordPressAffiliateMetaResponse:
        if payload.get("id") != post_id:
            raise WordPressTransportError(
                "WordPress affiliate meta response returned the wrong post id"
            )
        raw_title = payload.get("title")
        if isinstance(raw_title, Mapping):
            title = raw_title.get("raw") or raw_title.get("rendered")
        else:
            title = raw_title
        raw_meta = payload.get("meta")
        if not isinstance(title, str) or not title.strip():
            raise WordPressTransportError(
                "WordPress affiliate meta response title is invalid"
            )
        if not isinstance(raw_meta, Mapping):
            raise WordPressTransportError(
                "WordPress affiliate meta response meta is invalid"
            )
        meta: dict[str, str] = {}
        for key in WORDPRESS_AFFILIATE_META_KEYS:
            value = raw_meta.get(key)
            if isinstance(value, str) and value.strip():
                meta[key] = value.strip()
        return WordPressAffiliateMetaResponse(
            post_id=post_id,
            title=title.strip(),
            meta=meta,
        )

    def list_categories(self, *, per_page: int = 100) -> list[WordPressCategory]:
        if isinstance(per_page, bool) or not isinstance(per_page, int) or not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")
        categories: list[WordPressCategory] = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            endpoint = self.categories_endpoint + "?" + urlencode(
                {"context": "view", "hide_empty": "false", "per_page": per_page, "page": page}
            )
            http_request = request.Request(
                endpoint,
                method="GET",
                headers={
                    "Authorization": "Basic " + self._encoded_credential(),
                    "Accept": "application/json",
                },
            )
            payload, headers = self._open_json_value(
                http_request,
                error_prefix="WordPress category list",
            )
            if not isinstance(payload, list):
                raise WordPressTransportError(
                    "WordPress category list response must be an array"
                )
            for value in payload:
                if not isinstance(value, Mapping):
                    raise WordPressTransportError("WordPress category is invalid")
                category_id = value.get("id")
                name = value.get("name")
                slug = value.get("slug")
                count = value.get("count")
                if (
                    isinstance(category_id, bool)
                    or not isinstance(category_id, int)
                    or category_id <= 0
                    or not isinstance(name, str)
                    or not name.strip()
                    or not isinstance(slug, str)
                    or not slug.strip()
                    or isinstance(count, bool)
                    or not isinstance(count, int)
                    or count < 0
                ):
                    raise WordPressTransportError("WordPress category fields are invalid")
                categories.append(
                    WordPressCategory(category_id, name, slug, count)
                )
            header_value = headers.get("X-WP-TotalPages") or headers.get("x-wp-totalpages")
            if header_value is not None:
                try:
                    total_pages = int(header_value)
                except (TypeError, ValueError) as exc:
                    raise WordPressTransportError(
                        "WordPress category pagination header is invalid"
                    ) from exc
                if total_pages < 1:
                    raise WordPressTransportError(
                        "WordPress category pagination header is invalid"
                    )
            page += 1
        return categories

    def schedule_post(
        self,
        *,
        post_id: int,
        date: str,
        date_gmt: str,
        category_id: int | None = None,
    ) -> WordPressDraftResponse:
        request_payload = {
            "status": "future",
            "date": str(date or "").strip(),
            "date_gmt": str(date_gmt or "").strip(),
        }
        if category_id is not None:
            self._validate_category_id(category_id)
            request_payload["categories"] = [category_id]
        if not request_payload["date"] or not request_payload["date_gmt"]:
            raise ValueError("date and date_gmt are required")
        response = self._update_schedule_state(
            post_id=post_id,
            payload=request_payload,
        )
        if response.status != "future":
            raise WordPressTransportError(
                "WordPress schedule update did not return future status"
            )
        if response.date != request_payload["date"]:
            raise WordPressTransportError(
                "WordPress schedule update returned the wrong date"
            )
        if response.date_gmt != request_payload["date_gmt"]:
            raise WordPressTransportError(
                "WordPress schedule update returned the wrong date_gmt"
            )
        if category_id is not None and category_id not in response.categories:
            raise WordPressTransportError(
                "WordPress schedule update did not confirm category"
            )
        return response

    def update_category(
        self,
        *,
        post_id: int,
        category_id: int,
    ) -> WordPressDraftResponse:
        self._validate_category_id(category_id)
        response = self._update_schedule_state(
            post_id=post_id,
            payload={"categories": [category_id]},
        )
        if category_id not in response.categories:
            raise WordPressTransportError(
                "WordPress category update did not confirm category"
            )
        return response

    @staticmethod
    def _validate_category_id(category_id: int) -> None:
        if isinstance(category_id, bool) or not isinstance(category_id, int) or category_id <= 0:
            raise ValueError("category_id must be a positive integer")

    def cancel_schedule(
        self,
        *,
        post_id: int,
    ) -> WordPressDraftResponse:
        response = self._update_schedule_state(
            post_id=post_id,
            payload={"status": "draft"},
        )
        if response.status != "draft":
            raise WordPressTransportError(
                "WordPress schedule cancellation did not return draft status"
            )
        return response

    def _encoded_credential(self) -> str:
        credential = (
            f"{self.username}:{self.application_password}"
        ).encode("utf-8")
        return base64.b64encode(credential).decode("ascii")

    def _open_json(
        self,
        http_request: request.Request,
        *,
        error_prefix: str,
    ) -> dict[str, Any]:
        payload, _headers = self._open_json_value(
            http_request,
            error_prefix=error_prefix,
        )
        if not isinstance(payload, dict):
            raise WordPressTransportError(
                f"{error_prefix} response must be an object"
            )
        return payload

    def _open_json_value(
        self,
        http_request: request.Request,
        *,
        error_prefix: str,
    ) -> tuple[Any, Mapping[str, Any]]:
        try:
            with self.opener.open(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_response = response.read()
                headers = response.headers
        except error.HTTPError as exc:
            if exc.code == 404:
                code = "post_not_found"
            elif exc.code in {401, 403}:
                code = "authentication_failed"
            else:
                code = "remote_http_error"
            raise WordPressTransportError(
                f"{error_prefix} HTTP error: {exc.code}",
                code=code,
                http_status=exc.code,
            ) from exc
        except error.URLError as exc:
            raise WordPressTransportError(
                f"{error_prefix} transport failed",
                code="remote_unavailable",
            ) from exc
        try:
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WordPressTransportError(
                f"{error_prefix} returned invalid JSON"
            ) from exc
        return payload, headers

    def _update_schedule_state(
        self,
        *,
        post_id: int,
        payload: Mapping[str, Any],
    ) -> WordPressDraftResponse:
        allowed_fields = {"status", "date", "date_gmt", "categories"}
        request_payload = dict(payload)
        if set(request_payload) - allowed_fields:
            raise ValueError("schedule update contains forbidden fields")
        http_request = request.Request(
            self.post_endpoint(post_id),
            data=json.dumps(
                request_payload,
                ensure_ascii=False,
            ).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": "Basic " + self._encoded_credential(),
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        response_payload = self._open_json(
            http_request,
            error_prefix="WordPress schedule update",
        )
        return self._parse_schedule_response(
            response_payload,
            post_id=post_id,
            allowed_statuses={"draft", "future"},
        )

    @staticmethod
    def _parse_schedule_response(
        payload: Mapping[str, Any],
        *,
        post_id: int,
        allowed_statuses: set[str] | None,
    ) -> WordPressDraftResponse:
        if payload.get("id") != post_id:
            raise WordPressTransportError(
                "WordPress response returned the wrong post id"
            )
        status = payload.get("status")
        if not isinstance(status, str) or not status.strip():
            raise WordPressTransportError(
                "WordPress response status is invalid"
            )
        if allowed_statuses is not None and status not in allowed_statuses:
            raise WordPressTransportError(
                "WordPress response returned an unexpected status"
            )
        date = payload.get("date")
        date_gmt = payload.get("date_gmt")
        raw_categories = payload.get("categories", [])
        featured_media = payload.get("featured_media")
        for field_name, value in (("date", date), ("date_gmt", date_gmt)):
            if value is not None and not isinstance(value, str):
                raise WordPressTransportError(
                    f"WordPress response {field_name} is invalid"
                )
        if not isinstance(raw_categories, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in raw_categories
        ):
            raise WordPressTransportError(
                "WordPress response categories are invalid"
            )
        if featured_media is not None and (
            isinstance(featured_media, bool)
            or not isinstance(featured_media, int)
            or featured_media < 0
        ):
            raise WordPressTransportError(
                "WordPress response featured_media is invalid"
            )
        return WordPressDraftResponse(
            post_id=post_id,
            status=status,
            link=(payload.get("link") if isinstance(payload.get("link"), str) else None),
            date=date,
            date_gmt=date_gmt,
            categories=tuple(raw_categories),
            featured_media=featured_media,
        )
