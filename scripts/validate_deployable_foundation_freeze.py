#!/usr/bin/env python3
"""Validate historical and current deployable-product foundation freezes."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT / "research/05_evaluation/profiles"
CURRENT_MATCH_SUSPENSION_PATH = (
    ROOT
    / "research/05_evaluation/instruments/deployable_current_match_suspension_v1.json"
)
MANIFEST_PATHS = (
    PROFILE_ROOT / "deployable-product-foundation-freeze-v1.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v2.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v3.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v4.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v5.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v6.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v7.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v8.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v9.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v10.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v11.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v12.json",
)
EXPECTED_EXTERNAL_GATES = {
    "public-dns-and-certificate",
    "clean-host-restore",
    "staging-workflow-walkthrough",
}
FREEZE_SPECS: dict[str, dict[str, Any]] = {
    "deployable-product-foundation-freeze-v1": {
        "status": "go-deeper-external-rehearsal-pending",
        "run_id": "deployable-product-foundation-v1-development-001",
        "candidate_id": "A1-single-node-staging",
        "local_fields": {
            "passed": 41,
            "total": 41,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "41/41",
        "summary_marker": "41/41 frozen local checks",
        "build_fields": {
            "status": "blocked-registry-resolution",
            "compose_graph_validated": True,
            "image_build_claimed": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run verify:deployable-freeze",
        },
        "artifact_count": 30,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v2": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v2-container-001",
        "candidate_id": "A1-single-node-staging-v2",
        "local_fields": {
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 25,
            "live_https_total": 25,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "25/25-live-https",
        "summary_marker": "25/25 live HTTPS checks",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "f879ae4cb275174b9b233a5a7276a6510cec3453dc16a83f40f3891fbe3bde42"
            ),
            "web_image_sha256": (
                "cb87eb79cdbbda694c864b220f76ae008446535a0308b3f068103d555976a582"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
        },
        "artifact_count": 37,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v3": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v3-model-policy-001",
        "candidate_id": "A1-single-node-staging-v3-model-policy",
        "local_fields": {
            "model_policy_focused_passed": 95,
            "model_policy_focused_total": 95,
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 25,
            "live_https_total": 25,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "95/95-policy-and-25/25-live-https",
        "summary_marker": "95/95 focused policy",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "1de9c871a1b24a84528449ef422e105fc274dd751a81d6bed8f698e0df6c9f36"
            ),
            "web_image_sha256": (
                "4dc17ed8463da0427ab4e74c463b0c7680a09c64345327684036a6a0948bd11b"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "artifact_count": 46,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v4": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v4-provider-registry-001",
        "candidate_id": "A1-single-node-staging-v4-provider-registry",
        "local_fields": {
            "model_policy_focused_passed": 107,
            "model_policy_focused_total": 107,
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 30,
            "live_https_total": 30,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "107/107-policy-provider-and-30/30-live-https",
        "summary_marker": "107/107 focused",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "cedb76c79c563200aae4802544eb5d0616157f14ac23da63a8717f9db4e1a440"
            ),
            "web_image_sha256": (
                "e4f4a60903544afab70e93287c8add40499805cc088d28eaf605318642a24917"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "artifact_count": 53,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v5": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v5-local-multimodel-policy-001",
        "candidate_id": "A1-single-node-staging-v5-local-multimodel-policy",
        "local_fields": {
            "model_policy_focused_passed": 113,
            "model_policy_focused_total": 113,
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 30,
            "live_https_total": 30,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "113/113-policy-provider-and-30/30-live-https",
        "summary_marker": "113/113 focused",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "595e59041e63c54cd29e9c35f3e3f934c23689b3adfe58c95e26360b131258cc"
            ),
            "web_image_sha256": (
                "a0af70e70c542dcb04131236d7ebe854aa3161612b32098bfc6a2371f4ebbaea"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "artifact_count": 67,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v6": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v5-local-multimodel-policy-001",
        "candidate_id": "A1-single-node-staging-v5-local-multimodel-policy",
        "local_fields": {
            "model_policy_focused_passed": 113,
            "model_policy_focused_total": 113,
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 30,
            "live_https_total": 30,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "113/113-policy-provider-and-30/30-live-https",
        "summary_marker": "113/113 focused",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "595e59041e63c54cd29e9c35f3e3f934c23689b3adfe58c95e26360b131258cc"
            ),
            "web_image_sha256": (
                "a0af70e70c542dcb04131236d7ebe854aa3161612b32098bfc6a2371f4ebbaea"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "artifact_count": 67,
        "current_match_binding_count": 45,
        "require_current_match": True,
    },
    "deployable-product-foundation-freeze-v7": {
        "status": "go-deeper-current-container-requalification-pending",
        "run_id": (
            "deployable-product-foundation-v7-"
            "post-correctness-requalification-001"
        ),
        "candidate_id": "A1-single-node-staging-v7-post-correctness",
        "local_fields": {
            "in_process_passed": 42,
            "in_process_total": 42,
            "capacity_requests": 100,
            "capacity_errors": 0,
            "api_p95_ms": 3.073,
            "api_p95_gate_ms": 750.0,
            "backup_schema_version": 8,
            "dependency_vulnerabilities": 0,
            "container_build_passed": False,
            "live_https_executed": False,
            "external_provider_calls": 0,
            "external_provider_cost_usd": 0.0,
            "private_data_used": False,
        },
        "local_label": "42/42-current-in-process-container-pending",
        "summary_marker": "42/42 gates",
        "build_fields": {
            "status": "blocked-local-docker-runtime",
            "compose_graph_validated": True,
            "image_build_claimed": False,
            "docker_engine_version_observed": "28.5.1",
            "containers_started": False,
            "runtime_volumes_created": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "tree_binding_count": 14,
        "file_binding_count": 17,
        "require_current_match": False,
        "external_gate_ids": {
            "current-container-build-and-local-https",
            "public-dns-and-certificate",
            "clean-host-restore",
            "staging-workflow-walkthrough",
        },
    },
    "deployable-product-foundation-freeze-v8": {
        "status": "refine-evidence-sufficiency-selection-required",
        "run_id": "deployable-product-foundation-v8-current-image-attempt-001",
        "candidate_id": "A1-single-node-staging-v8-current-image",
        "decision": "refine",
        "selected_implementation_id": None,
        "local_fields": {
            "container_build_passed": True,
            "container_readiness_passed": True,
            "operational_entrypoints_passed": 4,
            "operational_entrypoints_total": 4,
            "clean_admin_bootstrap_passed": True,
            "source_ingestion_reached_publication": True,
            "evidence_sufficiency_selected": False,
            "publication_completed": False,
            "publication_status_code": 409,
            "fail_closed_without_test_control": True,
            "external_provider_calls": 0,
            "external_provider_cost_usd": 0.0,
            "private_data_used": False,
        },
        "local_label": "current-images-healthy-publication-fail-closed",
        "summary_marker": "Publication then failed closed",
        "build_fields": {
            "status": "passed-current-images-product-publication-blocked",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "a78a99e17e3a5b2bdba52aa6c490ca7"
                "aa532df9b46b2b9c9f136840360cde929"
            ),
            "web_image_sha256": (
                "242c39320e0acbee5f014854c4300145"
                "01a716cbb7d055ca9884ad468f644028"
            ),
            "docker_engine_version_observed": "28.5.1",
            "containers_started": True,
            "runtime_volumes_created": True,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "tree_binding_count": 14,
        "file_binding_count": 17,
        "require_current_match": False,
        "external_gate_ids": {
            "evidence-sufficiency-selection-and-live-publication",
            "public-dns-and-certificate",
            "clean-host-restore",
            "staging-workflow-walkthrough",
        },
    },
    "deployable-product-foundation-freeze-v9": {
        "status": "refine-open-set-dataset-and-selection-required",
        "run_id": "deployable-product-foundation-v9-open-set-build-checkpoint-001",
        "candidate_id": "A1-single-node-staging-v9-open-set-build-only",
        "decision": "refine",
        "selected_implementation_id": None,
        "local_fields": {
            "open_set_boundary_focused_passed": 29,
            "open_set_boundary_focused_total": 29,
            "v2_instrument_validated": True,
            "v2_preflight_blocked_fail_closed": True,
            "decision_dataset_frozen": False,
            "candidate_model_bound": False,
            "evidence_sufficiency_selected": False,
            "current_source_image_built": False,
            "publication_completed": False,
            "external_provider_calls": 0,
            "external_provider_cost_usd": 0.0,
            "private_or_heldout_data_used": False,
        },
        "local_label": "29/29-open-set-build-only",
        "summary_marker": "passed 29/29 tests",
        "build_fields": {
            "status": "current-source-images-unbuilt-v8-images-historical",
            "compose_graph_validated": True,
            "image_build_claimed": False,
            "prior_v8_api_image_sha256": (
                "a78a99e17e3a5b2bdba52aa6c490ca7"
                "aa532df9b46b2b9c9f136840360cde929"
            ),
            "prior_v8_web_image_sha256": (
                "242c39320e0acbee5f014854c4300145"
                "01a716cbb7d055ca9884ad468f644028"
            ),
            "containers_started": False,
            "runtime_volumes_created": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:model-policy",
            "npm run verify:evidence-sufficiency-v2",
            "npm run preflight:evidence-sufficiency-v2",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
        },
        "tree_binding_count": 14,
        "file_binding_count": 19,
        "require_current_match": False,
        "external_gate_ids": {
            "evidence-sufficiency-selection-and-live-publication",
            "public-dns-and-certificate",
            "clean-host-restore",
            "staging-workflow-walkthrough",
        },
    },
    "deployable-product-foundation-freeze-v10": {
        "status": "refine-open-set-dataset-and-selection-required",
        "run_id": "deployable-product-foundation-v10-malformed-verifier-correction-001",
        "candidate_id": "A1-single-node-staging-v10-malformed-output-correction",
        "decision": "refine",
        "selected_implementation_id": None,
        "local_fields": {
            "open_set_boundary_focused_passed": 30,
            "open_set_boundary_focused_total": 30,
            "v2_instrument_validated": True,
            "v2_preflight_blocked_fail_closed": True,
            "decision_dataset_frozen": False,
            "candidate_model_bound": False,
            "evidence_sufficiency_selected": False,
            "current_source_image_built": False,
            "publication_completed": False,
            "external_provider_calls": 0,
            "external_provider_cost_usd": 0.0,
            "private_or_heldout_data_used": False,
        },
        "local_label": "30/30-open-set-build-only",
        "summary_marker": "passes 30/30 tests",
        "build_fields": {
            "status": "current-source-images-unbuilt-v8-images-historical",
            "compose_graph_validated": True,
            "image_build_claimed": False,
            "prior_v8_api_image_sha256": (
                "a78a99e17e3a5b2bdba52aa6c490ca7"
                "aa532df9b46b2b9c9f136840360cde929"
            ),
            "prior_v8_web_image_sha256": (
                "242c39320e0acbee5f014854c4300145"
                "01a716cbb7d055ca9884ad468f644028"
            ),
            "containers_started": False,
            "runtime_volumes_created": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:model-policy",
            "npm run verify:evidence-sufficiency-v2",
            "npm run preflight:evidence-sufficiency-v2",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
        },
        "tree_binding_count": 14,
        "file_binding_count": 19,
        "require_current_match": False,
        "external_gate_ids": {
            "evidence-sufficiency-selection-and-live-publication",
            "public-dns-and-certificate",
            "clean-host-restore",
            "staging-workflow-walkthrough",
        },
    },
    "deployable-product-foundation-freeze-v11": {
        "status": "refine-open-set-independent-review-and-selection-required",
        "run_id": "deployable-product-foundation-v11-decision-draft-001",
        "candidate_id": "A1-single-node-staging-v11-decision-draft",
        "decision": "refine",
        "selected_implementation_id": None,
        "local_fields": {
            "decision_draft_focused_passed": 41,
            "decision_draft_focused_total": 41,
            "v2_instrument_validated": True,
            "v2_preflight_blocked_fail_closed": True,
            "decision_draft_authored": True,
            "decision_draft_case_count": 120,
            "decision_draft_source_count": 40,
            "decision_draft_structurally_valid": True,
            "decision_dataset_frozen": False,
            "independent_review_completed": False,
            "candidate_model_bound": False,
            "evidence_sufficiency_selected": False,
            "current_source_image_built": False,
            "publication_completed": False,
            "external_provider_calls": 0,
            "external_provider_cost_usd": 0.0,
            "private_or_heldout_data_used": False,
        },
        "local_label": "41/41-decision-draft-build-only",
        "summary_marker": "passes 41/41 focused tests",
        "build_fields": {
            "status": "current-source-images-unbuilt-v8-images-historical",
            "compose_graph_validated": True,
            "image_build_claimed": False,
            "prior_v8_api_image_sha256": (
                "a78a99e17e3a5b2bdba52aa6c490ca7"
                "aa532df9b46b2b9c9f136840360cde929"
            ),
            "prior_v8_web_image_sha256": (
                "242c39320e0acbee5f014854c4300145"
                "01a716cbb7d055ca9884ad468f644028"
            ),
            "containers_started": False,
            "runtime_volumes_created": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:model-policy",
            "npm run verify:evidence-sufficiency-v2-draft",
            "npm run verify:evidence-sufficiency-v2",
            "npm run preflight:evidence-sufficiency-v2",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
        },
        "tree_binding_count": 14,
        "file_binding_count": 22,
        "require_current_match": False,
        "external_gate_ids": {
            "evidence-sufficiency-selection-and-live-publication",
            "public-dns-and-certificate",
            "clean-host-restore",
            "staging-workflow-walkthrough",
        },
    },
    "deployable-product-foundation-freeze-v12": {
        "status": "refine-independent-review-execution-and-selection-required",
        "run_id": "deployable-product-foundation-v12-review-workflow-001",
        "candidate_id": "A1-single-node-staging-v12-review-workflow",
        "decision": "refine",
        "selected_implementation_id": None,
        "local_fields": {
            "review_workflow_focused_passed": 35,
            "review_workflow_focused_total": 35,
            "review_packet_validated": True,
            "review_packet_case_count": 120,
            "review_batch_count": 12,
            "sensitivity_control_count": 12,
            "network_free_judgment_count": 132,
            "network_free_simulation_passed": True,
            "review_preflight_blocked_fail_closed": True,
            "independent_reviewer_bound": False,
            "independent_review_completed": False,
            "decision_dataset_frozen": False,
            "candidate_model_bound": False,
            "evidence_sufficiency_selected": False,
            "current_source_image_built": False,
            "publication_completed": False,
            "external_provider_calls": 0,
            "external_provider_cost_usd": 0.0,
            "private_or_heldout_data_used": False,
        },
        "local_label": "35/35-review-workflow-build-only",
        "summary_marker": "35-test focused suite passes",
        "build_fields": {
            "status": "current-source-images-unbuilt-v8-images-historical",
            "compose_graph_validated": True,
            "image_build_claimed": False,
            "prior_v8_api_image_sha256": (
                "a78a99e17e3a5b2bdba52aa6c490ca7"
                "aa532df9b46b2b9c9f136840360cde929"
            ),
            "prior_v8_web_image_sha256": (
                "242c39320e0acbee5f014854c4300145"
                "01a716cbb7d055ca9884ad468f644028"
            ),
            "containers_started": False,
            "runtime_volumes_created": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:model-policy",
            "npm run verify:evidence-sufficiency-v2-draft",
            "npm run verify:evidence-sufficiency-v2",
            "npm run verify:evidence-sufficiency-v2-independent-review",
            "npm run simulate:evidence-sufficiency-v2-independent-review",
            "npm run preflight:evidence-sufficiency-v2-independent-review",
            "npm run preflight:evidence-sufficiency-v2",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
        },
        "tree_binding_count": 14,
        "file_binding_count": 26,
        "require_current_match": True,
        "external_gate_ids": {
            "evidence-sufficiency-selection-and-live-publication",
            "public-dns-and-certificate",
            "clean-host-restore",
            "staging-workflow-walkthrough",
        },
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate_current_match_suspension(root: Path) -> dict[str, Any]:
    path = root / CURRENT_MATCH_SUSPENSION_PATH.relative_to(ROOT)
    suspension = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "suspension_id": "deployable-current-match-suspension-v1",
        "status": "active-repository-correctness-audit",
        "suspends_current_match_for": "deployable-product-foundation-freeze-v6",
        "historical_revision_validation_required": True,
        "release_claim_authorized": False,
        "public_deployment_authorized": False,
        "external_evaluation_authorized": False,
        "current_match_drift_is_diagnostic": True,
    }
    for field, value in expected.items():
        if suspension.get(field) != value:
            raise ValueError(f"deployable current-match suspension drifted: {field}")
    if not suspension.get("reason") or not suspension.get("required_successor"):
        raise ValueError("deployable current-match suspension lacks rationale or exit")
    return suspension


def _revision_file(root: Path, revision: str, relative_path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def _is_ancestor(root: Path, revision: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def _is_ancestor_of(root: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def _tree_identity(root: Path, revision: str, relative_path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{revision}:{relative_path}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _path_has_worktree_changes(root: Path, relative_path: str) -> bool:
    return bool(
        subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                relative_path,
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _current_file(root: Path, relative_path: str) -> Path:
    candidate_path = Path(relative_path)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        raise ValueError("freeze paths must remain repository-relative")
    current = root / candidate_path
    if not current.is_file():
        raise ValueError(f"bound artifact is missing: {relative_path}")
    return current


def _revision_json(root: Path, revision: str, relative_path: str) -> dict[str, Any]:
    return json.loads(_revision_file(root, revision, relative_path))


def validate_deployable_freeze(
    manifest: dict[str, Any], *, root: Path
) -> dict[str, Any]:
    freeze_id = manifest.get("freeze_id", "")
    spec = FREEZE_SPECS.get(freeze_id)
    if spec is None:
        raise ValueError("unexpected deployable freeze identifier")
    if manifest.get("status") != spec["status"]:
        raise ValueError("deployable freeze status drifted")
    if manifest.get("run_id") != spec["run_id"]:
        raise ValueError("deployable freeze run identity drifted")
    expected_decision = spec.get("decision", "go-deeper")
    if manifest.get("decision") != expected_decision:
        raise ValueError("deployable freeze decision drifted")
    if manifest.get("candidate_id") != spec["candidate_id"]:
        raise ValueError("deployable freeze candidate drifted")

    revision = manifest.get("evidence_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not _is_ancestor(root, revision):
        raise ValueError("evidence revision is not an ancestor of HEAD")
    if manifest.get("private_or_heldout_data_read") is not False:
        raise ValueError("deployable freeze cannot read private or held-out data")
    if manifest.get("external_model_called") is not False:
        raise ValueError("deployable freeze cannot call an external model")
    if freeze_id in {
        "deployable-product-foundation-freeze-v7",
        "deployable-product-foundation-freeze-v8",
        "deployable-product-foundation-freeze-v9",
        "deployable-product-foundation-freeze-v10",
        "deployable-product-foundation-freeze-v11",
        "deployable-product-foundation-freeze-v12",
    }:
        implementation_revision = manifest.get("implementation_revision", "")
        if (
            not re.fullmatch(r"[0-9a-f]{40}", implementation_revision)
            or not _is_ancestor_of(root, implementation_revision, revision)
        ):
            raise ValueError("current-tree implementation revision is not evidence-bound")
        if manifest.get("schema_version") != 2:
            raise ValueError("current-tree freeze requires the tree-binding schema")
        if manifest.get("release_claim_authorized") is not False:
            raise ValueError("current-tree freeze cannot authorize a release claim")
        if manifest.get("public_deployment_authorized") is not False:
            raise ValueError("current-tree freeze cannot authorize public deployment")

    local_gates = manifest.get("local_gates", {})
    if any(
        local_gates.get(field) != expected
        for field, expected in spec["local_fields"].items()
    ):
        raise ValueError("local gate count or data boundary drifted")

    if freeze_id in {
        "deployable-product-foundation-freeze-v3",
        "deployable-product-foundation-freeze-v4",
    }:
        expected_model_policy = {
            "policy_id": "current-model-policy-2026-08-19",
            "gemma_execution_allowed": False,
            "retired_general_qwen_execution_allowed": False,
            "local_general_model": "qwen3.5:4b",
            "local_general_model_digest": (
                "2a654d98e6fba55d452b7043684e9b57"
                "a947e393bbffa62485a7aac05ee4eefd"
            ),
            "model_called_during_policy_validation": False,
        }
        if freeze_id == "deployable-product-foundation-freeze-v4":
            expected_model_policy["registered_hosted_retrieval_models"] = [
                "jina-embeddings-v5-text-small",
                "jina-reranker-v3",
            ]
        if manifest.get("model_policy") != expected_model_policy:
            raise ValueError("current model policy freeze binding drifted")
    elif freeze_id in {
        "deployable-product-foundation-freeze-v5",
        "deployable-product-foundation-freeze-v6",
    }:
        expected_model_policy = {
            "policy_id": "current-model-policy-2026-08-19-v2",
            "gemma_execution_allowed": False,
            "claude_execution_allowed": False,
            "retired_general_qwen_execution_allowed": False,
            "local_general_model": "qwen3.5:9b-q4_K_M",
            "local_general_model_digest": (
                "6488c96fa5faab64bb65cbd30d4289e2"
                "0e6130ef535a93ef9a49f42eda893ea7"
            ),
            "registered_openrouter_models": [
                "openrouter/deepseek/deepseek-v4-flash-0731",
                "openrouter/mistralai/mistral-small-2603",
            ],
            "openrouter_provider_options": {
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": "deny",
                "zdr": True,
            },
            "registered_hosted_retrieval_models": [
                "jina-embeddings-v5-text-small",
                "jina-reranker-v3",
            ],
            "model_called_during_policy_validation": False,
        }
        if manifest.get("model_policy") != expected_model_policy:
            raise ValueError("current model policy freeze binding drifted")
    elif freeze_id in {
        "deployable-product-foundation-freeze-v7",
        "deployable-product-foundation-freeze-v8",
        "deployable-product-foundation-freeze-v9",
        "deployable-product-foundation-freeze-v10",
        "deployable-product-foundation-freeze-v11",
        "deployable-product-foundation-freeze-v12",
    }:
        expected_model_policy = {
            "policy_id": "current-model-policy-2026-08-21-v3",
            "gemma_execution_allowed": False,
            "claude_execution_allowed": False,
            "retired_general_qwen_execution_allowed": False,
            "product_generator": "deepseek-v4-flash",
            "deterministic_generator_rollback": True,
            "independent_reviewer": "openrouter/mistralai/mistral-small-2603",
            "rejected_reviewer": "openrouter/qwen/qwen3.7-plus",
            "local_general_model": "qwen3.5:9b-q4_K_M",
            "local_general_model_digest": (
                "6488c96fa5faab64bb65cbd30d4289e2"
                "0e6130ef535a93ef9a49f42eda893ea7"
            ),
            "openrouter_allow_fallbacks": False,
            "openrouter_require_parameters": True,
            "model_called_during_policy_validation": False,
        }
        if manifest.get("model_policy") != expected_model_policy:
            raise ValueError("current-tree model policy binding drifted")

    external = manifest.get("external_gates", [])
    gate_ids = [gate.get("id") for gate in external]
    expected_external_gates = spec.get("external_gate_ids", EXPECTED_EXTERNAL_GATES)
    if (
        len(gate_ids) != len(set(gate_ids))
        or set(gate_ids) != expected_external_gates
    ):
        raise ValueError("external gate inventory is incomplete or duplicated")
    if any(gate.get("status") != "pending" for gate in external):
        raise ValueError("external gate cannot pass without a new freeze")

    build = manifest.get("container_build", {})
    if any(
        build.get(field) != expected
        for field, expected in spec["build_fields"].items()
    ):
        raise ValueError("container-build evidence drifted")

    suspension = None
    if freeze_id == "deployable-product-foundation-freeze-v6":
        suspension = _validate_current_match_suspension(root)
    current_drift: list[str] = []
    if freeze_id in {
        "deployable-product-foundation-freeze-v7",
        "deployable-product-foundation-freeze-v8",
        "deployable-product-foundation-freeze-v9",
        "deployable-product-foundation-freeze-v10",
        "deployable-product-foundation-freeze-v11",
        "deployable-product-foundation-freeze-v12",
    }:
        tree_bindings = manifest.get("tree_bindings", [])
        file_bindings = manifest.get("file_bindings", [])
        tree_paths = [binding.get("path") for binding in tree_bindings]
        file_paths = [binding.get("path") for binding in file_bindings]
        if (
            len(tree_paths) != len(set(tree_paths))
            or len(tree_paths) != spec["tree_binding_count"]
            or len(file_paths) != len(set(file_paths))
            or len(file_paths) != spec["file_binding_count"]
            or set(tree_paths) & set(file_paths)
        ):
            raise ValueError("current-tree binding inventory is incomplete or duplicated")
        for binding in tree_bindings:
            relative_path = binding["path"]
            expected = binding.get("git_tree_sha1", "")
            if not re.fullmatch(r"[0-9a-f]{40}", expected):
                raise ValueError(f"invalid tree identity: {relative_path}")
            if _tree_identity(root, revision, relative_path) != expected:
                raise ValueError(f"revision tree identity mismatch: {relative_path}")
            if spec["require_current_match"] and (
                _tree_identity(root, "HEAD", relative_path) != expected
                or _path_has_worktree_changes(root, relative_path)
            ):
                raise ValueError(
                    f"current tree drifted from {freeze_id}: {relative_path}"
                )
        for binding in file_bindings:
            relative_path = binding["path"]
            expected = binding.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError(f"invalid artifact hash: {relative_path}")
            if _sha256(_revision_file(root, revision, relative_path)) != expected:
                raise ValueError(f"revision artifact hash mismatch: {relative_path}")
            requires_current = binding.get("current_match_required")
            if not isinstance(requires_current, bool):
                raise ValueError(
                    f"current-tree current-match classification missing: {relative_path}"
                )
            if spec["require_current_match"] and requires_current and (
                _sha256(_current_file(root, relative_path).read_bytes()) != expected
            ):
                raise ValueError(
                    f"current artifact drifted from {freeze_id}: {relative_path}"
                )
        bindings = [*tree_bindings, *file_bindings]
    else:
        bindings = manifest.get("artifact_bindings", [])
        binding_paths = [binding.get("path") for binding in bindings]
        if (
            len(binding_paths) != len(set(binding_paths))
            or len(binding_paths) != spec["artifact_count"]
        ):
            raise ValueError("artifact binding inventory is incomplete or duplicated")
        for binding in bindings:
            relative_path = binding["path"]
            expected = binding.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError(f"invalid artifact hash: {relative_path}")
            if _sha256(_revision_file(root, revision, relative_path)) != expected:
                raise ValueError(f"revision artifact hash mismatch: {relative_path}")
            binding_requires_current = spec["require_current_match"]
            if freeze_id == "deployable-product-foundation-freeze-v6":
                binding_requires_current = binding.get("current_match_required")
                if not isinstance(binding_requires_current, bool):
                    raise ValueError(
                        f"current-match classification missing: {relative_path}"
                    )
            if binding_requires_current and (
                _sha256(_current_file(root, relative_path).read_bytes()) != expected
            ):
                if suspension is None:
                    raise ValueError(
                        f"current artifact drifted from freeze: {relative_path}"
                    )
                current_drift.append(relative_path)
    if freeze_id == "deployable-product-foundation-freeze-v6":
        current_match_count = sum(
            binding["current_match_required"] for binding in bindings
        )
        if current_match_count != spec["current_match_binding_count"]:
            raise ValueError("current-match artifact scope drifted")
        binding_by_path = {binding["path"]: binding for binding in bindings}
        if binding_by_path["research/05_evaluation/result-registry.md"][
            "current_match_required"
        ]:
            raise ValueError("append-only result registry cannot bind current package")
        if not binding_by_path["compose.staging.yml"]["current_match_required"]:
            raise ValueError("deployment implementation must bind current package")

    record_path = f"research/05_evaluation/records/{spec['run_id']}.json"
    record = _revision_json(root, revision, record_path)
    if (
        record.get("run_id") != manifest["run_id"]
        or record.get("decision", {}).get("outcome") != expected_decision
        or record.get("decision", {}).get("selected_implementation_id")
        != spec.get("selected_implementation_id", manifest["candidate_id"].lower())
    ):
        raise ValueError("registered decision does not match the deployment freeze")
    summary_path = f"research/05_evaluation/{spec['run_id']}-results.md"
    summary = _revision_file(root, revision, summary_path).decode("utf-8")
    if spec["summary_marker"] not in summary:
        raise ValueError("human-readable result does not preserve the local gate count")

    if set(manifest.get("reproduction_commands", [])) != spec["commands"]:
        raise ValueError("deployable freeze reproduction commands drifted")
    package_scripts = json.loads((root / "package.json").read_text(encoding="utf-8"))[
        "scripts"
    ]
    if package_scripts.get("verify:deployable-freeze") != (
        "uv run python -m scripts.validate_deployable_foundation_freeze"
    ):
        raise ValueError("deployable freeze command is not registered")
    if "npm run verify:deployable-freeze" not in package_scripts.get("check", ""):
        raise ValueError("deployable freeze is absent from the full check")
    if freeze_id != "deployable-product-foundation-freeze-v1" and package_scripts.get("verify:staging-https") != (
        "uv run python -m scripts.verify_https_staging"
    ):
        raise ValueError("live HTTPS verification command is not registered")
    if not manifest.get("rollback") or not manifest.get("change_control"):
        raise ValueError("deployable freeze must preserve rollback and change control")

    result = {
        "status": "passed",
        "freeze_id": freeze_id,
        "evidence_revision": revision,
        "decision": manifest["decision"],
        "local_gates": spec["local_label"],
        "external_gates_pending": len(external),
        "artifact_bindings": len(bindings),
        "current_match_required": spec["require_current_match"],
        "private_or_heldout_data_read": False,
        "external_model_called": False,
    }
    if freeze_id == "deployable-product-foundation-freeze-v6":
        result["current_match_bindings"] = spec["current_match_binding_count"]
        result["current_match_enforced"] = suspension is None
        result["current_match_status"] = (
            "enforced"
            if suspension is None
            else "suspended-by-repository-correctness-audit"
        )
        result["current_drift_count"] = len(current_drift)
        result["release_claim_authorized"] = False
    elif freeze_id in {
        "deployable-product-foundation-freeze-v7",
        "deployable-product-foundation-freeze-v8",
        "deployable-product-foundation-freeze-v9",
        "deployable-product-foundation-freeze-v10",
        "deployable-product-foundation-freeze-v11",
        "deployable-product-foundation-freeze-v12",
    }:
        result["tree_bindings"] = spec["tree_binding_count"]
        result["file_bindings"] = spec["file_binding_count"]
        result["current_match_status"] = (
            "enforced" if spec["require_current_match"] else "historical-superseded"
        )
        result["container_build_status"] = build["status"]
        result["image_build_claimed"] = build["image_build_claimed"]
        result["release_claim_authorized"] = False
    return result


def main() -> None:
    results = [
        validate_deployable_freeze(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            root=ROOT,
        )
        for manifest_path in MANIFEST_PATHS
    ]
    print(json.dumps({"status": "passed", "freezes": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
