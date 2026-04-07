from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = BASE_DIR / "docs" / "mock_server_check_latest.md"


def write_mock_server_check(markdown: str, output_path: Path | None = None) -> str:
    """Mock server 確認手順 Markdown をファイル保存し、保存先パスを返す。"""
    path = output_path or DEFAULT_OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)
