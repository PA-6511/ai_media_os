from pathlib import Path

SRC_ROOT = Path(__file__).parent.parent / "src"

FORBIDDEN_TEXT = [
    "import requests",
    "import httpx",
    "import aiohttp",
    "import subprocess",
    "os.system(",
    "urllib.request",
    "socket.connect",
]


def test_no_forbidden_imports_in_src() -> None:
    checked_files = [
        path
        for path in SRC_ROOT.rglob("*.py")
        if ".pytest_cache" not in str(path)
    ]

    assert checked_files

    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in text, f"{forbidden!r} found in {path}"
