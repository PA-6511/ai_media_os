import pytest

from pipelines.retry_policy import should_retry


@pytest.mark.parametrize(
    "error_message,expected_retryable",
    [
        ("HTTP 429 too many requests", True),
        ("wordpress publish failed status=503", True),
        ("HTTP 401 unauthorized", False),
        ("", False),
    ],
)
def test_should_retry_classification_boundaries(error_message: str, expected_retryable: bool) -> None:
    result = should_retry(error_message, retry_count=0, max_retry_count=3)
    assert bool(result["retryable"]) is expected_retryable


def test_should_retry_stops_on_max_retry_exceeded() -> None:
    result = should_retry("temporary server error", retry_count=3, max_retry_count=3)
    assert result["retryable"] is False
    assert result["reason"] == "max_retry_exceeded"
