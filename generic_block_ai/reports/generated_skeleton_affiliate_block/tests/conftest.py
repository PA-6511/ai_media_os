import json
from pathlib import Path

import pytest


MANIFEST_PATH = Path(__file__).parent.parent / "block_manifest.json"
POLICY_PATH = Path(__file__).parent.parent / "config" / "policy.json"


@pytest.fixture()
def manifest_data():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def policy_data():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
