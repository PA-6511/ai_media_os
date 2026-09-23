from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from typing import Callable

from . import campaign
from . import new_release
from . import new_release_autofill
from . import sale
from . import enrichment
from . import x_publish

from .campaign import (
    observe_output as observe_campaign,
)

from .sale import (
    observe_output as observe_sale,
)

from .command_adapter import (
    CommandRunner,
    SubprocessCommandRunner,
    execute_command,
)

from .types import (
    CommandSpec,
    StepResult,
    StepStatus,
)

from .wordpress import (
    observe_new_release_output
    as observe_wordpress,
)

from .x import (
    observe_new_release_output
    as observe_x,
)


SpecFactory = Callable[
    [],
    CommandSpec | None,
]


@dataclass
class DailyCycleReport:

    status: str

    steps: list[StepResult]


    def as_dict(
        self,
    ) -> dict:

        return {

            "status":
                self.status,

            "steps": [

                {
                    **asdict(step),
                    "status":
                        step.status.value,
                }

                for step in self.steps
            ],
        }


class DailyCycle:


    DEFAULT_COMPONENTS = (
        "new_release",
        "new_release_autofill",
        "x_publish",
        "sale",
        "campaign",
        "enrichment",
    )


    def __init__(
        self,
        *,
        runner:
            CommandRunner | None = None,
    ) -> None:


        self.runner = (

            runner

            if runner is not None

            else SubprocessCommandRunner()
        )


        self.factories: dict[
            str,
            SpecFactory,
        ] = {

            "new_release":
                new_release.command_spec,
            "new_release_autofill":
                new_release_autofill.command_spec,

            "x_publish":
                x_publish.command_spec,

            "sale":
                sale.command_spec,

            "campaign":
                campaign.command_spec,

            "enrichment":
                enrichment.command_spec,
        }


    def plan(
        self,
        components:
            tuple[str, ...] | None = None,
    ) -> list[dict]:


        selected = (

            components

            if components is not None

            else self.DEFAULT_COMPONENTS
        )


        plan: list[dict] = []


        for component in selected:


            factory = self.factories.get(
                component
            )


            if factory is None:

                plan.append(
                    {
                        "component":
                            component,
                        "available":
                            False,
                        "reason":
                            "UNKNOWN_COMPONENT",
                    }
                )

                continue


            spec = factory()


            if spec is None:

                plan.append(
                    {
                        "component":
                            component,
                        "available":
                            False,
                        "reason":
                            "ENTRYPOINT_NOT_FOUND",
                    }
                )

                continue


            plan.append(
                {
                    "component":
                        component,
                    "available":
                        True,
                    "argv":
                        list(
                            spec.argv
                        ),
                    "cwd":
                        spec.cwd,
                }
            )


        return plan


    def run(
        self,
        components:
            tuple[str, ...] | None = None,
    ) -> DailyCycleReport:


        selected = (

            components

            if components is not None

            else self.DEFAULT_COMPONENTS
        )


        results: list[
            StepResult
        ] = []


        for component in selected:


            factory = self.factories.get(
                component
            )


            if factory is None:

                results.append(
                    StepResult(
                        component=component,
                        status=(
                            StepStatus.SKIPPED
                        ),
                        code=(
                            "UNKNOWN_COMPONENT"
                        ),
                    )
                )

                continue


            # =================================================
            # x_publish must consume the CURRENT new_release
            # result from this same cycle.
            # =================================================

            if component == "x_publish":


                new_result = next(
                    (
                        item

                        for item in reversed(
                            results
                        )

                        if (
                            item.component
                            == "new_release"
                        )
                    ),
                    None,
                )


                if (
                    new_result is None
                    or new_result.status
                    != StepStatus.PASS
                ):

                    results.append(
                        StepResult(
                            component=component,
                            status=(
                                StepStatus.SKIPPED
                            ),
                            code=(
                                "NEW_RELEASE_NOT_READY"
                            ),
                        )
                    )

                    continue


                spec = (
                    x_publish
                    .command_spec_from_new_release(
                        new_result.metadata
                    )
                )


                if spec is None:

                    results.append(
                        StepResult(
                            component=component,
                            status=(
                                StepStatus.BLOCKED
                            ),
                            code=(
                                "NEW_RELEASE_X_"
                                "CONTEXT_INCOMPLETE"
                            ),
                        )
                    )

                    continue


            else:

                spec = factory()


            if spec is None:

                results.append(
                    StepResult(
                        component=component,
                        status=(
                            StepStatus.SKIPPED
                        ),
                        code=(
                            "ENTRYPOINT_NOT_FOUND"
                        ),
                    )
                )

                continue


            result = execute_command(
                spec=spec,
                runner=self.runner,
            )


            # =================================================
            # Bind X result
            # =================================================

            if component == "x_publish":


                observed = (
                    x_publish.observe_output(
                        result.output
                    )
                )


                result.metadata[
                    "x_publish"
                ] = {

                    "status":
                        observed.status,

                    "code":
                        observed.code,

                    "x_post_id":
                        observed.x_post_id,

                    "x_post_url":
                        observed.x_post_url,

                    "evidence_path":
                        observed.evidence_path,

                    "delivery_state":
                        observed.delivery_state,

                    "x_post_executed":
                        observed.x_post_executed,
                }


                if observed.status in {
                    "SKIPPED_ALREADY_POSTED",
                    "SKIPPED_MANUAL_POST_EVIDENCE",
                }:

                    result.status = (
                        StepStatus.SKIPPED
                    )

                    result.code = (
                        observed.status
                    )


                elif (
                    observed.status
                    == "POSTED"
                ):

                    result.status = (
                        StepStatus.PASS
                    )

                    result.code = "POSTED"


                elif observed.status in {
                    "PRE_SEND_BLOCKED",
                    "AUTOMATION_DISABLED",
                    "CANARY_NEW_POST_BLOCKED",
                }:

                    result.status = (
                        StepStatus.BLOCKED
                    )

                    result.code = (
                        observed.status
                    )


                elif (
                    observed.status
                    == "UNKNOWN_DELIVERY"
                ):

                    result.status = (
                        StepStatus.FAILED
                    )

                    result.code = (
                        "UNKNOWN_DELIVERY"
                    )


            # =================================================
            # Existing new-release observation
            # =================================================

            elif (
                component == "new_release"
                and result.status
                == StepStatus.PASS
            ):


                wp = observe_wordpress(
                    result.output
                )


                x = observe_x(
                    result.output
                )


                result.metadata.update(
                    {

                        "wordpress": {

                            "post_id":
                                wp.post_id,

                            "status":
                                wp.status,

                            "permalink":
                                wp.permalink,
                        },

                        "x": {

                            "article_url_state":
                                x.article_url_state,

                            "article_url":
                                x.article_url,

                            "draft_path":
                                x.draft_path,
                        },
                    }
                )


            # =================================================
            # Existing sale observation
            # =================================================

            elif (
                component == "sale"
                and result.status
                == StepStatus.PASS
            ):


                observed = observe_sale(
                    result.output
                )


                result.metadata[
                    "sale"
                ] = {

                    "candidate_count":
                        observed.candidate_count,

                    "success_count":
                        observed.success_count,

                    "failed_count":
                        observed.failed_count,

                    "skipped_count":
                        observed.skipped_count,

                    "external_call_count":
                        observed.external_call_count,

                    "outcome":
                        observed.outcome,
                }


            # =================================================
            # Existing campaign observation
            # =================================================

            elif (
                component == "campaign"
                and result.status
                == StepStatus.PASS
            ):


                observed = observe_campaign(
                    result.output
                )


                result.metadata[
                    "campaign"
                ] = {

                    "campaign_id":
                        observed.campaign_id,

                    "selected_count":
                        observed.selected_count,

                    "created_count":
                        observed.created_count,

                    "existing_exact_count":
                        observed.existing_exact_count,

                    "no_fresh_candidates":
                        observed.no_fresh_candidates,

                    "external_get_count":
                        observed.external_get_count,
                }



            # =================================================
            # Kobo affiliate / cover enrichment observation
            # =================================================

            elif (
                component == "enrichment"
            ):

                observed = (
                    enrichment.observe_output(
                        result.output
                    )
                )

                result.metadata[
                    "enrichment"
                ] = {
                    "status": observed.status,
                    "candidate_count": observed.candidate_count,
                    "selected_count": observed.selected_count,
                    "success_count": observed.success_count,
                    "failed_count": observed.failed_count,
                    "recovered_count": observed.recovered_count,
                    "skipped_count": observed.skipped_count,
                    "external_get_count": observed.external_get_count,
                    "database_write_count": observed.database_write_count,
                    "policy_current_and_agreed": (
                        observed.policy_current_and_agreed
                    ),
                    "evidence_file": observed.evidence_file,
                    "error_code": observed.error_code,
                    "outcome": observed.outcome,
                }

                if observed.outcome == "PASS":
                    result.status = StepStatus.PASS
                    result.code = (
                        observed.status
                        or "PASS"
                    )

                elif observed.outcome == "SKIP_BUSY":
                    result.status = StepStatus.SKIPPED
                    result.code = "SKIP_BUSY"

                elif observed.outcome == "BLOCKED_POLICY":
                    result.status = StepStatus.BLOCKED
                    result.code = "POLICY_NOT_CURRENT"

                else:
                    result.status = StepStatus.FAILED
                    result.code = (
                        observed.outcome
                        or "ENRICHMENT_OUTPUT_INVALID"
                    )

            results.append(
                result
            )


        failed = [

            result

            for result in results

            if result.status in {
                StepStatus.BLOCKED,
                StepStatus.FAILED,
            }
        ]


        status = (

            "DEGRADED"

            if failed

            else "PASS"
        )


        return DailyCycleReport(
            status=status,
            steps=results,
        )
