from __future__ import annotations

from typing import Any


class Module:
    def __init__(self):
        pass

    def run(self):
        pass

    @staticmethod
    def _evaluate(proposals: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not proposals:
            return None
        return max(
            proposals,
            key=lambda proposal: float(proposal.get("priority", 0.0)),
        )

    @staticmethod
    def _build_business_analysis(
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        """Expose business KPI evidence for Core analysis."""

        metrics = snapshot.get(
            "business_metrics"
        )

        if not isinstance(metrics, dict) or not metrics:
            return {
                "status": "UNAVAILABLE",
                "reason": "business_metrics_not_available",
                "report_type": snapshot.get(
                    "report_type"
                ),
                "period": snapshot.get(
                    "period"
                ),
                "current_metrics": {},
                "comparison_metrics": {},
                "unavailable_metrics": [],
                "notable_changes": [],
            }

        comparison_root = snapshot.get(
            "comparison"
        )

        if not isinstance(
            comparison_root,
            dict,
        ):
            comparison_root = {}

        comparison = comparison_root.get(
            "business_metrics"
        )

        if not isinstance(
            comparison,
            dict,
        ):
            comparison = {}

        unavailable_metrics = sorted(
            name
            for name, metric in metrics.items()
            if (
                not isinstance(
                    metric,
                    dict,
                )
                or metric.get(
                    "value"
                )
                is None
            )
        )

        notable_changes: list[
            dict[str, Any]
        ] = []

        for name, change in comparison.items():
            if not isinstance(
                change,
                dict,
            ):
                continue

            current = change.get(
                "current"
            )
            previous = change.get(
                "previous"
            )
            delta = change.get(
                "value"
            )
            percent_change = change.get(
                "percent_change"
            )

            if (
                current is None
                or previous is None
                or delta is None
            ):
                continue

            current_metric = metrics.get(
                name
            )

            basis = (
                current_metric.get(
                    "basis"
                )
                if isinstance(
                    current_metric,
                    dict,
                )
                else None
            )

            notable_changes.append(
                {
                    "metric": name,
                    "current": current,
                    "previous": previous,
                    "delta": delta,
                    "percent_change":
                        percent_change,
                    "percent_change_reason":
                        change.get(
                            "percent_change_reason"
                        ),
                    "basis": basis,
                }
            )

        def _number(
            value: Any,
        ) -> float | None:
            if isinstance(
                value,
                bool,
            ):
                return None

            if isinstance(
                value,
                (int, float),
            ):
                return float(
                    value
                )

            return None

        def _change_score(
            row: dict[str, Any],
        ) -> tuple[float, float]:
            percent = _number(
                row.get(
                    "percent_change"
                )
            )

            delta = _number(
                row.get(
                    "delta"
                )
            )

            return (
                (
                    abs(percent)
                    if percent is not None
                    else -1.0
                ),
                (
                    abs(delta)
                    if delta is not None
                    else -1.0
                ),
            )

        notable_changes.sort(
            key=_change_score,
            reverse=True,
        )

        return {
            "status": "OK",
            "reason": None,
            "report_type": snapshot.get(
                "report_type"
            ),
            "period": snapshot.get(
                "period"
            ),
            "current_metrics": metrics,
            "comparison_metrics": comparison,
            "unavailable_metrics":
                unavailable_metrics,
            "notable_changes":
                notable_changes[:5],
        }

    def evaluate_x_analytics_advisory(
        self,
        *,
        reader: Any | None = None,
        report_type: str = "x_kpi_summary",
    ) -> dict[str, Any]:
        """Read advisory evidence without triggering execution or writes."""

        if reader is None:
            from core.x_analytics_advisory_reader import (
                XAnalyticsAdvisoryReader,
            )

            reader = XAnalyticsAdvisoryReader()
        result = reader.get_latest(report_type)
        if result.get("status") not in {"OK", "STALE"}:
            return {
                "status": result.get("status", "UNAVAILABLE"),
                "reason": result.get("reason"),
                "advisory_only": True,
                "selected_proposal": None,
                "business_analysis":
                    self._build_business_analysis({}),
            }
        snapshot = result.get("snapshot") or {}
        business_analysis = self._build_business_analysis(
            snapshot
        )
        actions = snapshot.get("recommended_actions") or []
        proposals = [
            {
                "item_id": str(
                    action.get("rule_id") or f"x-advisory-{index}"
                ),
                "block_name": "x_analytics_advisory_provider",
                "priority": float(len(actions) - index),
                "reason": str(
                    action.get("summary") or "analytics advisory"
                ),
                "advisory_only": True,
                "execution_allowed": False,
                "metadata": {
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "report_type": snapshot.get("report_type"),
                    "target_period": action.get("target_period"),
                    "sample_size": action.get("sample_size"),
                    "constraints": action.get("constraints"),
                    "experiment_candidate": isinstance(
                        action.get("evidence"),
                        dict,
                    ),
                    "human_review_required": True,
                    "evidence": action.get("evidence"),
                    "source_content_treated_as_instruction": False,
                },
            }
            for index, action in enumerate(actions)
            if isinstance(action, dict)
            and action.get("advisory_only") is True
            and action.get("execution_allowed") is False
        ]
        return {
            "status": result["status"],
            "reason": result.get("reason"),
            "snapshot_id": snapshot.get("snapshot_id"),
            "advisory_only": True,
            "selected_proposal": self._evaluate(proposals),
            "proposal_count": len(proposals),
            "business_analysis": business_analysis,
        }
