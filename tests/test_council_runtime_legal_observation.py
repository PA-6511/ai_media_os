import sys
import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

COUNCIL_RUNTIME_PATH = BASE_DIR / "core" / "council_runtime.py"
_spec = importlib.util.spec_from_file_location("core_council_runtime_file", COUNCIL_RUNTIME_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
CouncilRuntime = _module.CouncilRuntime


class _DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None


class _DummyBlock:
    def run(self):
        return [
            {
                "task_id": "t-1",
                "item_id": "i-1",
                "target": "target-1",
                "priority": 0.8,
                "status": "ok",
                "metadata": {
                    "signals": ["affiliate_link"],
                    "disclosure_checked": False,
                },
            }
        ]


class _EmptyBlock:
    def run(self):
        return []


class _DummyCoreAI:
    def evaluate(self, proposals):
        if not proposals:
            return None
        return {
            **proposals[0],
            "decision": "accept",
            "reason": "keep_existing_flow",
        }


class _DummyPipeline:
    def __init__(self):
        self.calls = 0

    def run(self, task):
        self.calls += 1
        return {"status": "ok", "task": task}


def test_runtime_keeps_existing_flow_even_when_legal_observation_warn(monkeypatch):
    observed = {"called": 0}

    def _fake_observer(core_input, *, event_id, logger):
        observed["called"] += 1
        core_input.setdefault("decision_packages", []).append(
            {
                "package_type": "decision_package",
                "decision": {"status": "WARN"},
                "legal_gate": {"status": "LEGAL_REVIEW_REQUIRED"},
            }
        )
        return {
            "decision_package": {
                "decision": {"status": "WARN"},
                "legal_gate": {"status": "LEGAL_REVIEW_REQUIRED"},
            },
            "report_path": "reports/legal_compliance_gate_observations/fake.json",
        }

    monkeypatch.setattr(_module, "observe_legal_gate_in_core_input", _fake_observer)

    pipeline = _DummyPipeline()
    runtime = CouncilRuntime([_DummyBlock()], _DummyCoreAI(), pipeline, _DummyLogger())
    result = runtime.run_once()

    assert observed["called"] == 1
    assert pipeline.calls == 1
    assert result["status"] == "ok"
    assert result["legal_gate_observation"]["status"] == "LEGAL_REVIEW_REQUIRED"


def test_runtime_no_task_still_returns_without_behavior_change(monkeypatch):
    def _fake_observer(core_input, *, event_id, logger):
        core_input.setdefault("decision_packages", []).append(
            {
                "package_type": "decision_package",
                "decision": {"status": "WARN"},
                "legal_gate": {"status": "WARN"},
            }
        )
        return {
            "decision_package": {
                "decision": {"status": "WARN"},
                "legal_gate": {"status": "WARN"},
            },
            "report_path": "reports/legal_compliance_gate_observations/fake_no_task.json",
        }

    monkeypatch.setattr(_module, "observe_legal_gate_in_core_input", _fake_observer)

    pipeline = _DummyPipeline()
    runtime = CouncilRuntime([_EmptyBlock()], _DummyCoreAI(), pipeline, _DummyLogger())
    result = runtime.run_once()

    assert result["status"] == "no_task"
    assert pipeline.calls == 0
    assert result["legal_gate_observation"]["status"] == "WARN"
