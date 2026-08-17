-- Frozen deterministic diagnostics from the 12-case anchor-002 run.
-- These values are not semantic or professor-fidelity selection evidence.
SELECT *
FROM (
    VALUES
        ('C0', 'Generic; no course evidence', 4.0 / 12.0, 1.0 / 12.0, 9.0 / 12.0, 4.0 / 12.0, 4.0 / 12.0),
        ('C1', 'Generic policy; oracle evidence', 10.0 / 12.0, 9.0 / 12.0, 9.0 / 12.0, 12.0 / 12.0, 12.0 / 12.0),
        ('C2', 'Professor policy; oracle evidence', 10.0 / 12.0, 9.0 / 12.0, 10.0 / 12.0, 12.0 / 12.0, 12.0 / 12.0),
        ('C3', 'Professor policy; selected retrieval', 6.0 / 12.0, 5.0 / 12.0, 9.0 / 12.0, 11.0 / 12.0, 7.0 / 12.0)
) AS condition_diagnostics(
    condition,
    configuration,
    hard_gate_rate,
    structural_rate,
    action_rate,
    citation_id_rate,
    citation_source_rate
)
ORDER BY condition;
