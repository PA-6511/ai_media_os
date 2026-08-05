from phase26.rehearsal.observation_points_builder import build_observation_points


def test_observation_points_include_required_items() -> None:
    result = build_observation_points({})
    assert result["status"] == "OBSERVATION_POINTS_READY"
    assert "target_file_before_state" in result["points"]
    assert "stop_condition_status" in result["points"]
