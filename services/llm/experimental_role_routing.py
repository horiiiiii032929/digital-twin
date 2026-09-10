"""Explicit experimental generation/planning role routing."""

from src.digital_twin.llm import LlmConfigurationError, LlmIdentityDriftError

GENERATION_TASK = "question_specific_typed_instruction"
REVISION_TASK = "question_specific_factual_revision"
PLANNING_TASKS = frozenset(
    {
        "reactive_tutoring_intent",
        "source_bound_attempt_assessment_v1",
        "autonomous_tutoring_plan",
        "hierarchical_autonomy_plan",
        "autonomy_plan_verifier",
        "autonomous_tutoring_wording_strategy",
    }
)


class ExperimentalGenerationRoleRouter:
    """Keep all planning tasks on the fixed transport; reject unknown tasks."""

    def __init__(self, *, planner_client, generation_client, role_configuration, revision_client=None):
        if not isinstance(role_configuration, dict) or set(role_configuration) not in ({"planner", "generation"}, {"planner", "generation", "revision"}):
            raise ValueError("Exact planner and generation role configuration required")
        required = {"model", "output_cap", "reasoning_effort"}
        if any(
            not isinstance(value, dict)
            or set(value) != required
            or not isinstance(value.get("model"), str)
            or not isinstance(value.get("reasoning_effort"), str)
            for value in role_configuration.values()
        ):
            raise ValueError("Each role requires exact model, cap and reasoning fields")
        planner = role_configuration["planner"]
        generator = role_configuration["generation"]
        if planner != {
            "model": "gpt-5.6-luna",
            "output_cap": 3000,
            "reasoning_effort": "low",
        }:
            raise ValueError("Planner must remain Luna-low with the fixed cap")
        if generator["output_cap"] != 3000 or (
            generator["model"],
            generator["reasoning_effort"],
        ) not in {
            ("gpt-5.6-luna", "low"),
            ("gpt-5.6-luna", "medium"),
            ("gpt-5.6-sol", "low"),
        }:
            raise ValueError("Generator variant is not prospectively declared")
        if "revision" in role_configuration:
            revision = role_configuration["revision"]
            if (
                revision_client is None
                or generator != planner
                or (revision["model"], revision["reasoning_effort"]) not in {("gpt-5.6-sol", "low"), ("gpt-5.6-sol", "medium"), ("gpt-5.6-luna", "medium")}
                or revision["output_cap"] != 3000
                or revision["reasoning_effort"] not in {"low", "medium"}
            ):
                raise ValueError("Revision requires Luna-low draft and a declared Sol low/medium or Luna medium transport")
        elif revision_client is not None:
            raise ValueError("Revision transport requires an explicit revision role")
        self.revision_client = revision_client
        self.planner_client = planner_client
        self.generation_client = generation_client
        self.role_configuration = {
            role: dict(value) for role, value in role_configuration.items()
        }

    def role_for_task(self, task):
        if task in {"final_response_quality_audit_v2", "final_response_issue_guided_repair_v2"} and "revision" in self.role_configuration:
            return "revision"
        if task in {REVISION_TASK, "question_specific_bounded_revision", "question_specific_conditional_revision"} and "revision" in self.role_configuration:
            return "revision"
        if task == GENERATION_TASK:
            return "generation"
        if task in PLANNING_TASKS:
            return "planner"
        raise LlmConfigurationError("Task is outside the experimental role contract")

    def client_for_role(self, role):
        if role == "revision" and self.revision_client is not None:
            return self.revision_client
        if role == "generation":
            return self.generation_client
        if role == "planner":
            return self.planner_client
        raise LlmConfigurationError("Unknown experimental role")

    def conservative_request_cost_usd(self, messages, task):
        client = self.client_for_role(self.role_for_task(task))
        bound = getattr(client, "conservative_request_cost_usd", None)
        if not callable(bound):
            return None
        return bound(messages, task)

    async def chat(self, messages, task):
        role = self.role_for_task(task)
        response = await self.client_for_role(role).chat(messages, task)
        if response.provider_model != self.role_configuration[role]["model"]:
            error = LlmIdentityDriftError(
                provider_model=response.provider_model,
                provider_revision=response.provider_revision,
            )
            error.usage = response.usage
            raise error
        return response
