from pathlib import Path


RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_daily_new_release_roundup_impl.sh"
)


def test_cover_gate_projects_public_payload_before_reading_image_url():
    source = RUNNER.read_text(encoding="utf-8")
    block_start = source.index("PY_XNR_COVER_SOURCE")
    block_end = source.index("PY_XNR_COVER_SOURCE", block_start + 1)
    cover_gate = source[block_start:block_end]

    assert "from app.services.xnr_roundup_candidate_projection import (" in cover_gate
    assert "build_context_candidate_payload" in cover_gate
    assert "raw_payload = json.loads(" in cover_gate
    assert "payload = build_context_candidate_payload(" in cover_gate
    assert cover_gate.index("payload = build_context_candidate_payload(") < cover_gate.index(
        "items = ["
    )
    assert 'image_url = str(item.get("image_url") or "").strip()' in cover_gate


def test_cover_gate_keeps_the_existing_url_predicate():
    source = RUNNER.read_text(encoding="utf-8")
    block_start = source.index("PY_XNR_COVER_SOURCE")
    block_end = source.index("PY_XNR_COVER_SOURCE", block_start + 1)
    cover_gate = source[block_start:block_end]

    assert 'marker in image_url.lower()' in cover_gate
    assert '("noimage", "no-image", "no_image")' in cover_gate
    assert 'parsed.scheme != "https"' in cover_gate
    assert "or not parsed.netloc" in cover_gate
    assert "or is_placeholder" in cover_gate
