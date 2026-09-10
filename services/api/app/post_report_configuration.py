"""Shared, explicit API/worker selectors for unpromoted learning comparisons."""
from collections.abc import Mapping
import os


def post_report_runtime_flags(environment: Mapping[str, str] | None = None) -> dict:
    environment = os.environ if environment is None else environment
    definitions = {
        "APP_POST_REPORT_LEARNING": ("post_report_learning_mode", "control",
            {"control", "assessed-count", "assessed-decay", "assessed-bkt", "assessed-pfa"}),
        "APP_POST_REPORT_PLANNER": ("post_report_planner_mode", "configured",
            {"configured", "rules", "analytic-only"}),
        "APP_POST_REPORT_GOAL_RECOVERY": ("post_report_goal_recovery_enabled", "false", {"true", "false"}),
        "APP_POST_REPORT_SOURCE_ASSESSMENT": ("post_report_source_assessment_enabled", "false", {"true", "false"}),
        "APP_POST_REPORT_MODEL_ASSESSMENT": ("post_report_model_assessment_enabled", "false", {"true", "false"}),
        "APP_POST_REPORT_ASSESSMENT_VERSION": ("post_report_model_assessment_version", "v1", {"v1", "v2"}),
        "APP_POST_REPORT_CONTEXT_RETRIEVAL": ("post_report_context_retrieval_enabled", "false", {"true", "false"}),
    }
    flags = {}
    for name, (argument, default, allowed) in definitions.items():
        value = environment.get(name, default).strip()
        if value not in allowed:
            raise ValueError(f"{name} must be one of {', '.join(sorted(allowed))}")
        if value != default:
            flags[argument] = value == "true" if allowed == {"true", "false"} else value
    return flags
