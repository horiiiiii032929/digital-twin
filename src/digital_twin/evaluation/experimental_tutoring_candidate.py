"""Explicit experimental runtime selections; none changes the release default."""

EXPERIMENTAL_CANDIDATES = ("v4", "v5", "v6", "v7", "v8", "v9", "v10")
GENERATION_VARIANTS = {
    "v14-luna-sol-medium": ("gpt-5.6-luna", "low"),
    "v14-luna-sol": ("gpt-5.6-luna", "low"),
    "v13-luna-sol": ("gpt-5.6-luna", "low"),
    "v12-luna-sol": ("gpt-5.6-luna", "low"),
    "v11-luna-low": ("gpt-5.6-luna", "low"),
    "v10-luna-low": ("gpt-5.6-luna", "low"),
    "v10-luna-medium": ("gpt-5.6-luna", "medium"),
    "v10-sol-low": ("gpt-5.6-sol", "low"),
}
EXPERIMENTAL_CANDIDATES += tuple(GENERATION_VARIANTS)
EXPERIMENTAL_MODEL = "gpt-5.6-luna"
EXPERIMENTAL_OUTPUT_CAP = 3000


def experimental_tutoring_configuration(version: str) -> dict:
    """Return a fresh, inspectable configuration for one named candidate."""
    if version not in EXPERIMENTAL_CANDIDATES:
        raise ValueError("unknown experimental tutoring candidate")
    variant = version if version in GENERATION_VARIANTS else None
    if variant:
        version = "v14" if variant in {"v14-luna-sol", "v14-luna-sol-medium"} else "v13" if variant == "v13-luna-sol" else "v12" if variant == "v12-luna-sol" else "v11" if variant == "v11-luna-low" else "v10"
    flags = {
        "teaching_profile_context_enabled": True,
        "question_specific_generation_enabled": True,
        "bounded_generation_contract_enabled": True,
        "named_referent_context_enabled": True,
    }
    if version in {"v5", "v6", "v7"}:
        flags["instructional_moves_enabled"] = True
    if version in {"v6", "v7"}:
        flags["instructional_continuation_enabled"] = True
    if version == "v7":
        flags["instructional_request_coverage_enabled"] = True
    if version in {"v8", "v9", "v10", "v11", "v12", "v13", "v14"}:
        flags["instructional_compact_response_enabled"] = True
    if version in {"v9", "v10", "v11", "v12", "v13", "v14"}:
        flags["instructional_profile_authority_enabled"] = True
    if version in {"v10", "v11", "v12", "v13", "v14"}:
        flags["instructional_typed_response_enabled"] = True
    if version in {"v11", "v12", "v13", "v14"}:
        flags["instructional_evidence_strength_enabled"] = True
    if version in {"v12", "v13", "v14"}:
        flags["instructional_factual_revision_enabled"] = True
    if version == "v14":
        flags["instructional_conditional_revision_enabled"] = True
    if version == "v13":
        flags["instructional_bounded_revision_enabled"] = True
    selection = {
        "version": version,
        "implementation_id": f"question-specific-profile-grounded-{version}",
        "model": EXPERIMENTAL_MODEL,
        "output_cap": EXPERIMENTAL_OUTPUT_CAP,
        "reasoning_effort": "low",
        "runtime_flags": flags,
        "semantic_support_verified": False,
        "default_or_selected_profile_changed": False,
    }

    if variant:
        model, effort = GENERATION_VARIANTS[variant]
        selection.update(version=variant, variant_id=variant, model=model, reasoning_effort=effort,
            role_configuration={
                "planner": {"model": EXPERIMENTAL_MODEL, "output_cap": EXPERIMENTAL_OUTPUT_CAP, "reasoning_effort": "low"},
                "generation": {"model": model, "output_cap": EXPERIMENTAL_OUTPUT_CAP, "reasoning_effort": effort},
            })
        selection["runtime_flags"]["experimental_generation_model_id"] = model
    if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"}:
        selection["role_configuration"]["revision"] = {"model": "gpt-5.6-sol", "output_cap": 3000, "reasoning_effort": "low"}
        if variant == "v14-luna-sol-medium":
            selection["role_configuration"]["revision"]["reasoning_effort"] = "medium"
        selection["final_response_role"] = "generation-if-kept-otherwise-revision" if variant in {"v14-luna-sol", "v14-luna-sol-medium"} else "revision"
    return selection
