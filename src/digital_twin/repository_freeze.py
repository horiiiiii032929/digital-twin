"""Repository-wide pre-evaluation execution freeze."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


FREEZE_ID = "repository-correctness-pre-evaluation-freeze-v1"
FREEZE_ACTIVE = True
BLOCKED_OPERATIONS = frozenset(
    {
        "dataset_generation",
        "external_model_evaluation",
        "heldout_execution",
        "local_model_evaluation",
        "method_evaluation_execution",
    }
)

# Explicit coverage is required because flag-based discovery misses entrypoints that
# execute immediately with defaults. Values document every prohibited capability a
# script can exercise; one fail-closed guard at the entrypoint blocks all of them.
FROZEN_ENTRYPOINT_OPERATIONS = MappingProxyType(
    {
        "scripts/analyze_cross_course_retrieval_heldout.py": ("heldout_execution",),
        "scripts/analyze_it5002_rapid_result.py": ("heldout_execution",),
        "scripts/apply_cross_course_qc_patch.py": ("dataset_generation",),
        "scripts/apply_cross_course_second_review.py": ("dataset_generation",),
        "scripts/apply_multimodal_researcher_review.py": ("dataset_generation",),
        "scripts/benchmark_evidence_sufficiency.py": ("method_evaluation_execution",),
        "scripts/benchmark_retrieval.py": ("method_evaluation_execution",),
        "scripts/build_course_tutor_splits.py": ("dataset_generation",),
        "scripts/build_atomic_claim_validation_dataset.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_confirmation_v2.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_open_10000.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_open_reference_aggregate_007.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_open_development_v2.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_open_development_v3.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_open_source_plan_v2.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_source_aligned_confirmation.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_atomic_m2_confirmation.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_atomic_m2_product_checkpoint.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_action_router_confirmation.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_action_router_product_checkpoint.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_semantic_target_successor.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_source_semantic_atoms.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_ambiguity_safe_successor.py": (
            "dataset_generation",
        ),
        "scripts/build_cross_engine_sealed_confirmation_010.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_development_region_corpus.py": (
            "dataset_generation",
        ),
        "scripts/build_governed_full_autonomy_v2_1_grounding_successor_011.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_open_mixed_wording_005.py": (
            "dataset_generation",
        ),
        "scripts/build_academic_factual_qa_visual_supplement.py": (
            "dataset_generation",
        ),
        "scripts/build_true_visual_colpali_confirmation.py": (
            "dataset_generation",
        ),
        "scripts/build_true_visual_product_checkpoint.py": (
            "dataset_generation",
        ),
        "scripts/build_whole_system_architecture_tranches.py": (
            "dataset_generation",
        ),
        "scripts/construct_academic_factual_qa_open_10000.py": (
            "dataset_generation",
            "external_model_evaluation",
        ),
        "scripts/build_evidence_sufficiency_v2_decision_draft.py": (
            "dataset_generation",
        ),
        "scripts/build_evidence_sufficiency_v2_decision_draft_002.py": (
            "dataset_generation",
        ),
        "scripts/build_factual_qa_v3_10000_blueprints.py": ("dataset_generation",),
        "scripts/build_factual_qa_v3_10000_truth_packages.py": ("dataset_generation",),
        "scripts/build_generator_qualification_dataset.py": ("dataset_generation",),
        "scripts/build_it5002_rapid_dataset.py": (
            "dataset_generation",
            "local_model_evaluation",
        ),
        "scripts/build_multimodal_development_artifacts.py": (
            "dataset_generation",
            "local_model_evaluation",
        ),
        "scripts/build_multimodal_visual_embeddings.py": (
            "dataset_generation",
            "local_model_evaluation",
        ),
        "scripts/build_multimodal_private_draft.py": ("dataset_generation",),
        "scripts/cross_review_course_tutor_authoring.py": ("dataset_generation",),
        "scripts/draft_cross_course_benchmark.py": (
            "dataset_generation",
            "local_model_evaluation",
        ),
        "scripts/draft_cross_course_benchmark_v2.py": (
            "dataset_generation",
            "local_model_evaluation",
        ),
        "scripts/evaluate_generation.py": ("method_evaluation_execution",),
        "scripts/evaluate_ml_dependency_compatibility.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/evaluate_retrieval.py": ("method_evaluation_execution",),
        "scripts/execute_professor_fidelity.py": (
            "external_model_evaluation",
            "heldout_execution",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/execute_academic_factual_qa_panel_review_v2.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/judge_generator_qualification_v3.py": ("external_model_evaluation",),
        "scripts/judge_professor_fidelity.py": (
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/finalize_factual_qa_v3_conversion.py": ("dataset_generation",),
        "scripts/finalize_professor_fidelity_blinded_review.py": (
            "dataset_generation",
        ),
        "scripts/prepare_course_tutor_authoring_review.py": ("dataset_generation",),
        "scripts/prepare_academic_factual_qa_panel_review_v2.py": (
            "dataset_generation",
        ),
        "scripts/prepare_academic_factual_qa_open_development_003.py": (
            "method_evaluation_execution",
        ),
        "scripts/prepare_evidence_sufficiency_v2_independent_review.py": (
            "dataset_generation",
        ),
        "scripts/run_evidence_sufficiency_v2_independent_review.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_evidence_sufficiency_v2_candidate_comparison.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/prepare_professor_fidelity_blinded_review.py": ("dataset_generation",),
        "scripts/qualify_retrieval_index_lifecycle.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/qualify_professor_fidelity_judge_v4.py": (
            "external_model_evaluation",
        ),
        "scripts/review_generator_qualification_v2.py": ("local_model_evaluation",),
        "scripts/record_cross_course_reviews.py": ("dataset_generation",),
        "scripts/render_generator_qualification_second_review.py": (
            "dataset_generation",
        ),
        "scripts/run_course_tutor_hybrid_review.py": (
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_course_digital_twin_evaluation_program.py": (
            "dataset_generation",
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_provider_integration.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_true_visual_supplement_003.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_true_visual_colpali_confirmation.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_true_visual_product_checkpoint.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_true_visual_omni_confirmation_002.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_final_cross_method_factual_confirmation.py": (
            "heldout_execution",
            "method_evaluation_execution",
        ),
        "scripts/run_professor_fidelity_proxy_c0_c3_002.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_professor_fidelity_proxy_c0_c3_003.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_local_r1_final_technical_completion_001.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_successor_architecture_development_fold_001.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_successor_architecture_policy_value_fold_004.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_successor_architecture_confirmation_005.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_successor_architecture_engine_comparison_006.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_grounding_selection_002.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_002.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_003.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_004.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_005.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_006.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_007.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_008.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_009.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_012.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_013.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_014.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_015.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_016.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_017.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_018.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_019.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_020.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_actual_product_confirmation_021.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_persona_confirmation_023.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/recover_governed_full_autonomy_confirmation_score.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_product_evidence_gate_selection_004.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_product_evidence_gate_selection_003.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_product_evidence_gate_selection_002.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_product_evidence_gate_selection.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_corpus_confirmation_028.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_corpus_confirmation_027.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_corpus_confirmation_026.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_corpus_confirmation_025.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_persona_confirmation_024.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        # Persona-robust selection is network-free today, but it is an
        # evaluation execution entrypoint and must remain covered if a paid
        # successor is added later.
        "scripts/run_governed_full_autonomy_v2_1_persona_robust_selection_022.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_persona_wording_bank_022.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/analyze_governed_full_autonomy_v2_1_actual_product_confirmation_012.py": (
            "method_evaluation_execution",
        ),
        "scripts/analyze_governed_full_autonomy_v2_1_actual_product_confirmation_013.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_grounding_successor_011.py": (
            "method_evaluation_execution",
        ),
        # Hidden-state learner extension of 010: --simulate is deterministic and
        # network-free; --execute is registered here but has no bounded pilot
        # authorization, so it fails closed until one is reviewed and added.
        "scripts/run_governed_full_autonomy_v2_1_hidden_state_learner_014.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_governed_full_autonomy_v2_1_cross_engine_evaluation_010.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_whole_system_architecture_round.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_semantic_target_comparison.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_source_semantic_atom_comparison.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_ambiguity_safe_comparison.py": (
            "method_evaluation_execution",
        ),
        "scripts/audit_academic_factual_qa_source_semantic_atom_failures.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_course_digital_twin_autonomous_long_run_001.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_source_aligned_wording.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_source_aligned_retrieval.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_atomic_m2_confirmation.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_course_digital_twin_nonhuman_supplements.py": (
            "dataset_generation",
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_autonomous_tutoring_graph_development.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_autonomous_tutoring_r1_local_confirmation.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_proactive_outreach_a1_development.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_proactive_outreach_a1_shadow_confirmation.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_atomic_claim_validation_confirmation.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_end_to_end_pilot.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_end_to_end_pilot_v2.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_10000.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_10000_winner.py": (
            "external_model_evaluation",
            "heldout_execution",
            "method_evaluation_execution",
        ),
        "scripts/score_academic_factual_qa_open_10000_winner.py": (
            "heldout_execution",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_api_retrieval_selection.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_development_checkpoint_003.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_development_checkpoint_004.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_product_checkpoint_005.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_product_checkpoint_006.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_product_checkpoint_007.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_reference_validation.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_r1_model_cascade.py": (
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_r1_public_preview.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_advisory_audit_004.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_product_003.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_wording.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_wording_v2.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_open_wording_v3.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_openai_reviewer_calibration.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_openai_reviewer_calibration_004.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_t0_confirmation.py": (
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_visual_checkpoint.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/score_academic_factual_qa_open_10000.py": (
            "heldout_execution",
            "method_evaluation_execution",
        ),
        "scripts/run_cross_course_retrieval_heldout.py": (
            "heldout_execution",
            "method_evaluation_execution",
        ),
        "scripts/run_cross_course_retrieval_pilot.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_cross_course_retrieval_qualification.py": (
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_quality_pilot.py": (
            "dataset_generation",
            "external_model_evaluation",
        ),
        "scripts/run_factual_qa_v3_oracle_pilot.py": (
            "dataset_generation",
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_v3_reviewer_qualification.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_v3_scale_pilot_100.py": (
            "dataset_generation",
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_v3_scale_pilot_100_003.py": (
            "dataset_generation",
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_v3_scale_checkpoint_1000.py": (
            "dataset_generation",
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_v3_scale_completion_10000.py": (
            "dataset_generation",
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_factual_qa_v3_scale_rehearsal.py": (
            "dataset_generation",
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_generator_qualification.py": (
            "external_model_evaluation",
            "heldout_execution",
            "method_evaluation_execution",
        ),
        "scripts/run_generator_qualification_stability.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_it5002_retrieval_rapid.py": (
            "heldout_execution",
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_local_reviewer_sensitivity.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_multimodal_product_grounding.py": ("method_evaluation_execution",),
        "scripts/run_multimodal_retrieval_development.py": (
            "method_evaluation_execution",
        ),
        "scripts/run_multimodal_retrieval_v3_development.py": (
            "local_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_professor_fidelity_experiment.py": ("heldout_execution",),
        "scripts/run_academic_factual_qa_atomic_m2_product_checkpoint.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/run_academic_factual_qa_action_router_product_checkpoint.py": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        "scripts/sample_multimodal_pdf_pages.py": ("dataset_generation",),
        "scripts/seal_course_tutor_anchor.py": ("dataset_generation",),
        "scripts/seal_course_tutor_splits.py": ("dataset_generation",),
        "scripts/seal_cross_course_benchmark.py": ("dataset_generation",),
        "scripts/seal_multimodal_benchmark.py": ("dataset_generation",),
        "scripts/second_review_cross_course_benchmark.py": ("dataset_generation",),
        "scripts/second_review_multimodal_benchmark.py": ("dataset_generation",),
    }
)

# One named, versioned pilot may execute while the wider pre-evaluation freeze
# remains active. The authorization is intentionally not operation-generic: a
# successor instrument requires a new code review and an explicit entry here.
BOUNDED_PILOT_AUTHORIZATIONS = MappingProxyType(
    {
        "academic-factual-qa-open-10000-deterministic-development-001": (
            "dataset_generation",
        ),
        "academic-factual-qa-open-10000-reference-aggregate-007": (
            "dataset_generation",
        ),
        "course-digital-twin-whole-system-architecture-development-freeze-001": (
            "dataset_generation",
        ),
        "course-digital-twin-whole-system-architecture-round-1-001": (
            "method_evaluation_execution",
        ),
        "course-digital-twin-whole-system-architecture-round-2-001": (
            "method_evaluation_execution",
        ),
        "course-digital-twin-whole-system-architecture-round-3-001": (
            "method_evaluation_execution",
        ),
        "governed-full-autonomy-v2-1-grounding-successor-011": (
            "dataset_generation",
            "method_evaluation_execution",
        ),
        # Issue #198, authorized by the researcher on 2026-09-03. Runs the
        # confirmation-024 selected candidate against the sealed Program 011
        # 10,000+1,000 package as a known-benchmark regression. The
        # deterministic arms reach no provider at all; only the
        # candidate-provider arm may call one, under a USD 5 ceiling.
        "academic-factual-qa-open-10000-winner-regression-001": (
            "external_model_evaluation",
            "heldout_execution",
            "method_evaluation_execution",
        ),
        # Issue #198, authorized by the researcher on 2026-09-03. Fresh
        # multi-source-corpus successor to persona confirmation 024, running
        # the dominance-scoped v4 grounding architecture under a USD 5 ceiling.
        "governed-full-autonomy-v2-1-corpus-confirmation-025": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        # Issue #198. Fresh package successor to the invalid 025 attempt.
        "governed-full-autonomy-v2-1-corpus-confirmation-026": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        # Issue #198. Harness-only successor binding the unopened 026 package.
        "governed-full-autonomy-v2-1-corpus-confirmation-027": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        # Issue #198. Operator-only successor; identical unopened package.
        "governed-full-autonomy-v2-1-corpus-confirmation-028": (
            "external_model_evaluation",
            "method_evaluation_execution",
        ),
        # Issue #198. Provider-free development-split gate selection for the
        # product; touches no sealed or held-out package.
        "product-evidence-gate-selection-001": (
            "method_evaluation_execution",
        ),
        "product-evidence-gate-selection-002": (
            "method_evaluation_execution",
        ),
        "product-evidence-gate-selection-003": (
            "method_evaluation_execution",
        ),
        "product-evidence-gate-selection-004": (
            "method_evaluation_execution",
        ),
        # Issue #198. Deterministic re-materialization of the committed
        # development clusters at the granularity their gold cites. No
        # provider call and no new source.
        "academic-factual-qa-development-region-corpus-001": (
            "dataset_generation",
        ),
        # Issue #131. Fresh public-source visual package and its bounded,
        # first-party Jina retrieval confirmation. This does not authorize the
        # later actual-product answer/citation checkpoint.
        "true-visual-colpali-confirmation-001": (
            "dataset_generation",
        ),
        # Issue #210. The actual-product run is complete and its provider
        # authority is revoked; only deterministic package validation remains.
        "true-visual-product-checkpoint-001": (
            "dataset_generation",
        ),
    }
)


class RepositoryFreezeError(RuntimeError):
    """Raised before work prohibited by the active correctness freeze."""


@dataclass(frozen=True)
class RepositoryFreezeStatus:
    freeze_id: str
    active: bool
    blocked_operations: tuple[str, ...]


def freeze_status() -> RepositoryFreezeStatus:
    return RepositoryFreezeStatus(
        freeze_id=FREEZE_ID,
        active=FREEZE_ACTIVE,
        blocked_operations=tuple(sorted(BLOCKED_OPERATIONS)),
    )


def require_pre_evaluation_operation_allowed(operation: str) -> None:
    """Fail closed before a frozen evaluation, held-out, or dataset operation."""

    if operation not in BLOCKED_OPERATIONS:
        raise RepositoryFreezeError(
            f"{operation!r} is not registered by {FREEZE_ID}; fail closed"
        )
    if FREEZE_ACTIVE:
        raise RepositoryFreezeError(
            f"{FREEZE_ID} blocks {operation} until a versioned repository "
            "correctness freeze is complete"
        )


def require_bounded_pilot_operation_allowed(
    instrument_id: str,
    operation: str | None = None,
) -> None:
    """Authorize only an exact, reviewed pilot while retaining the global freeze."""

    operations = BOUNDED_PILOT_AUTHORIZATIONS.get(instrument_id)
    if operations is None:
        raise RepositoryFreezeError(
            f"{instrument_id!r} is not a bounded authorization under {FREEZE_ID}"
        )
    if not operations or any(
        allowed_operation not in BLOCKED_OPERATIONS
        for allowed_operation in operations
    ):
        raise RepositoryFreezeError(
            f"{instrument_id!r} has an invalid bounded authorization"
        )
    if operation is not None and operation not in operations:
        raise RepositoryFreezeError(
            f"{instrument_id!r} is not authorized for {operation!r}"
        )
