-- Corrected deterministic diagnostics from the 12-case anchor-002 run.
-- These values are not semantic or professor-fidelity selection evidence.
SELECT *
FROM (
    VALUES
        ('C0', 'Generic; no course evidence', 4.0 / 12.0, 1.0 / 12.0, 9.0 / 12.0, 4.0 / 12.0, 0.0 / 8.0, 8),
        ('C1', 'Generic policy; oracle evidence', 10.0 / 12.0, 9.0 / 12.0, 9.0 / 12.0, 12.0 / 12.0, 8.0 / 8.0, 8),
        ('C2', 'Professor policy; oracle evidence', 10.0 / 12.0, 9.0 / 12.0, 10.0 / 12.0, 12.0 / 12.0, 8.0 / 8.0, 8),
        ('C3', 'Professor policy; selected retrieval', 6.0 / 12.0, 5.0 / 12.0, 9.0 / 12.0, 11.0 / 12.0, 4.0 / 8.0, 8)
) AS condition_diagnostics(
    condition,
    configuration,
    hard_gate_rate,
    structural_rate,
    action_rate,
    citation_id_rate,
    citation_source_applicable_rate,
    citation_source_applicable_n
)
ORDER BY condition;
