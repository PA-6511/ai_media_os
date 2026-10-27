def test_intentional_failure():
    expected = 10
    actual = 10

    assert actual == expected, (
        f"intentional probe failure: "
        f"expected={expected}, actual={actual}"
    )
