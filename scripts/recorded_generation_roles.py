"""Reusable recorded role transports for explicitly versioned evaluations."""

from pathlib import Path
from src.digital_twin.llm import LlmBudgetExceededError

from scripts.run_final_profile_longitudinal import (
    RecordedRunClient,
    ContractFailureClient,
)
from services.llm import OpenAiResponsesClient
from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter


class RecordedGenerationRoles(ExperimentalGenerationRoleRouter):
    """Read-only aggregate facade; each role retains its exact request ledger."""

    def __init__(self, *, role_clients, ledger_paths, role_configuration):
        super().__init__(
            planner_client=role_clients["planner"],
            generation_client=role_clients["generation"],
            **({"revision_client": role_clients["revision"]} if "revision" in role_clients else {}),
            role_configuration=role_configuration,
        )
        self.role_clients = dict(role_clients)
        self.ledger_paths = dict(ledger_paths)

    async def chat(self, messages, task):
        if self.stopped:
            raise LlmBudgetExceededError()
        return await super().chat(messages, task)

    @property
    def records(self):
        return [
            {**row, "role": role}
            for role, client in self.role_clients.items()
            for row in client.records
        ]

    @property
    def attempts(self):
        return sum(client.attempts for client in self.role_clients.values())

    @property
    def reserved_usd(self):
        return sum(client.reserved_usd for client in self.role_clients.values())

    @property
    def stopped(self):
        return any(client.stopped for client in self.role_clients.values())


def create_recorded_generation_roles(
    selection,
    ledger_prefix: Path,
    *,
    maximum_calls,
    maximum_cost_usd,
    live=False,
    transport_factory=None,
):
    """Partition finite bounds equally across roles; no hidden pooled allowance."""
    role_count = len(selection["role_configuration"])
    if role_count not in {2, 3} or maximum_calls < role_count:
        raise ValueError("every declared role requires a finite call allocation")
    clients, paths = {}, {}
    for role, config in selection["role_configuration"].items():
        client = (
            transport_factory(role, config)
            if transport_factory
            else (
                OpenAiResponsesClient(
                    config["model"],
                    max_output_tokens=config["output_cap"],
                    reasoning_effort=config["reasoning_effort"],
                    timeout_seconds=30,
                    experimental_sol_enabled=config["model"] == "gpt-5.6-sol",
                )
                if live
                else ContractFailureClient()
            )
        )
        serializer_client = None
        if role == "revision" and selection.get("final_audit_prompt_version") == "v2":
            from src.digital_twin.generation.final_response_audit import make_final_audit_client
            serializer_client = make_final_audit_client(role="repair", model=config["model"])
            if live and transport_factory is None:
                client = serializer_client
        if transport_factory is None and not live:
            client.experimental_transport_configuration = dict(config)
        path = ledger_prefix.with_name(f"{ledger_prefix.name}-{role}.jsonl")
        paths[role] = path
        clients[role] = RecordedRunClient(
            client,
            path,
            maximum_calls=maximum_calls // role_count,
            maximum_cost_usd=maximum_cost_usd / role_count,
            reservation_usd=0.16,
            max_output_tokens=config["output_cap"],
            expected_model=config["model"],
            reasoning_effort=config["reasoning_effort"],
            experimental_sol_enabled=config["model"] == "gpt-5.6-sol",
            network_mode="live" if live else "injected-contract",
            serializer_client=serializer_client,
        )
    return RecordedGenerationRoles(
        role_clients=clients,
        ledger_paths=paths,
        role_configuration=selection["role_configuration"],
    )
