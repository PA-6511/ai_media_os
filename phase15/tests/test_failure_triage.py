from phase15.reporting.failure_triage import triage_failure


def test_triage_import_error() -> None:
    result = triage_failure("", "ImportError: cannot import name X", 1)
    assert result["category"] == "IMPORT_ERROR"


def test_triage_syntax_error() -> None:
    result = triage_failure("", "SyntaxError: invalid syntax", 1)
    assert result["category"] == "SYNTAX_ERROR"


def test_triage_assertion_failed() -> None:
    stdout = "FAILED phase15/tests/test_x.py::test_y - AssertionError: expected 1"
    result = triage_failure(stdout, "", 1)
    assert result["category"] == "TEST_ASSERTION_FAILED"
