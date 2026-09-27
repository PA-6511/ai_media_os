from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence


POSTS_LOOKUP_ENDPOINT = "https://api.x.com/2/tweets"
POST_READ_UNIT_COST_USD = Decimal("0.005")
MAX_POSTS_PER_REQUEST = 100


class XApiMetricsError(RuntimeError):
    def __init__(
        self,
        category: str,
        status_code: int | None = None,
        *,
        request_count: int = 0,
    ) -> None:
        self.category = category
        self.status_code = status_code
        self.request_count = request_count
        suffix = f":http_{status_code}" if status_code is not None else ""
        super().__init__(f"X_API_METRICS_{category.upper()}{suffix}")


@dataclass(frozen=True)
class XApiPostMetrics:
    post_id: str
    author_id: str | None
    posted_at: datetime | None
    text: str | None
    metrics: dict[str, int | None]
    missing_reasons: dict[str, str]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class XApiFetchResult:
    posts: tuple[XApiPostMetrics, ...]
    errors: tuple[dict[str, Any], ...]
    raw_payload: dict[str, Any]
    public_only: bool
    request_count: int


def oauth1_from_environment() -> Any:
    from requests_oauthlib import OAuth1

    required = (
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    )
    missing = [name for name in required if not str(os.getenv(name) or "").strip()]
    if missing:
        raise XApiMetricsError("credentials_missing")
    return OAuth1(*(os.environ[name] for name in required))


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _count(mapping: dict[str, Any], name: str) -> int | None:
    value = mapping.get(name)
    return int(value) if isinstance(value, int) and value >= 0 else None


def _normalize_post(payload: dict[str, Any]) -> XApiPostMetrics:
    public = payload.get("public_metrics")
    private = payload.get("non_public_metrics")
    public = public if isinstance(public, dict) else {}
    private = private if isinstance(private, dict) else {}
    reposts = _count(public, "repost_count")
    if reposts is None:
        reposts = _count(public, "retweet_count")
    metrics = {
        "impressions": _count(public, "impression_count"),
        "likes": _count(public, "like_count"),
        "reposts": reposts,
        "replies": _count(public, "reply_count"),
        "link_clicks": _count(private, "url_link_clicks"),
        "profile_clicks": _count(private, "user_profile_clicks"),
        "engagements": _count(private, "engagements"),
        "views": None,
        "follows": None,
    }
    missing_reasons = {
        name: (
            "unsupported_by_post_metrics_api"
            if name == "follows"
            else "video_media_metrics_not_requested"
            if name == "views"
            else "non_public_metrics_unavailable"
            if name in {"link_clicks", "profile_clicks", "engagements"}
            else "public_metric_missing"
        )
        for name, value in metrics.items()
        if value is None
    }
    return XApiPostMetrics(
        post_id=str(payload.get("id") or ""),
        author_id=(
            str(payload.get("author_id")) if payload.get("author_id") else None
        ),
        posted_at=_parse_datetime(payload.get("created_at")),
        text=str(payload["text"]) if payload.get("text") is not None else None,
        metrics=metrics,
        missing_reasons=missing_reasons,
        raw_payload=payload,
    )


class XApiMetricsClient:
    def __init__(self, *, http: Any | None = None, auth: Any | None = None) -> None:
        if http is None:
            import requests

            http = requests.Session()
        self.http = http
        self.auth = auth if auth is not None else oauth1_from_environment()

    @staticmethod
    def _category(status_code: int) -> str:
        if status_code == 401:
            return "authentication"
        if status_code == 402:
            return "balance"
        if status_code == 403:
            return "permission"
        if status_code == 429:
            return "rate_limit"
        if status_code >= 500:
            return "server"
        return "request"

    def _request(self, post_ids: Sequence[str], *, private: bool) -> Any:
        fields = "author_id,created_at,text,public_metrics"
        if private:
            fields += ",non_public_metrics"
        try:
            return self.http.get(
                POSTS_LOOKUP_ENDPOINT,
                auth=self.auth,
                params={"ids": ",".join(post_ids), "tweet.fields": fields},
                timeout=30,
            )
        except Exception as exc:
            if type(exc).__module__.startswith("requests"):
                raise XApiMetricsError("timeout_or_network") from exc
            raise

    def fetch_posts(
        self,
        post_ids: Sequence[str],
        *,
        include_private: bool = True,
    ) -> XApiFetchResult:
        normalized = tuple(dict.fromkeys(str(value) for value in post_ids))
        if not normalized or len(normalized) > MAX_POSTS_PER_REQUEST:
            raise ValueError("post_ids must contain 1 to 100 unique IDs")
        try:
            response = self._request(normalized, private=include_private)
        except XApiMetricsError as exc:
            raise XApiMetricsError(
                exc.category,
                exc.status_code,
                request_count=1,
            ) from exc
        request_count = 1
        public_only = not include_private
        if response.status_code == 403 and include_private:
            try:
                response = self._request(normalized, private=False)
            except XApiMetricsError as exc:
                raise XApiMetricsError(
                    exc.category,
                    exc.status_code,
                    request_count=2,
                ) from exc
            request_count += 1
            public_only = True
        if response.status_code != 200:
            raise XApiMetricsError(
                self._category(int(response.status_code)),
                int(response.status_code),
                request_count=request_count,
            )
        try:
            payload = response.json()
        except Exception as exc:
            raise XApiMetricsError("invalid_response") from exc
        if not isinstance(payload, dict):
            raise XApiMetricsError("invalid_response")
        data = payload.get("data")
        errors = payload.get("errors")
        return XApiFetchResult(
            posts=tuple(
                _normalize_post(item)
                for item in (data if isinstance(data, list) else [])
                if isinstance(item, dict) and str(item.get("id") or "")
            ),
            errors=tuple(
                item for item in (errors if isinstance(errors, list) else [])
                if isinstance(item, dict)
            ),
            raw_payload=payload,
            public_only=public_only,
            request_count=request_count,
        )