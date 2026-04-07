import json

from config import core_runtime_config as runtime_cfg


def test_load_core_runtime_config_invalid_json_returns_defaults(tmp_path) -> None:
    broken_path = tmp_path / "broken.json"
    broken_path.write_text("{invalid", encoding="utf-8")

    loaded = runtime_cfg.load_core_runtime_config(broken_path)
    assert loaded["retry"]["max_retry_count"] == 3
    assert loaded["core"]["invalid_decision_fallback"] == "freeze"


def test_get_retry_max_retry_count_falls_back_on_broken_values(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "core_runtime.json"
    cfg_path.write_text(
        json.dumps(
            {
                "retry": {
                    "max_retry_count": "oops",
                    "max_retry_count_clamp_min": "oops",
                    "max_retry_count_clamp_max": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_cfg, "DEFAULT_CORE_RUNTIME_CONFIG_PATH", cfg_path)

    assert runtime_cfg.get_retry_max_retry_count() == 3


def test_get_retry_max_retry_count_respects_clamp(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "core_runtime.json"
    cfg_path.write_text(
        json.dumps(
            {
                "retry": {
                    "max_retry_count": 99,
                    "max_retry_count_clamp_min": 1,
                    "max_retry_count_clamp_max": 4,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_cfg, "DEFAULT_CORE_RUNTIME_CONFIG_PATH", cfg_path)

    assert runtime_cfg.get_retry_max_retry_count() == 4
