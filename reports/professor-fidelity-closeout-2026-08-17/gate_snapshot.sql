-- Frozen from professor-fidelity-v2-anchor-002-machine-review-summary-001.
-- The priority column preserves the prospective gate reading order.
SELECT *
FROM (
    VALUES
        (1, 'Generator completion', 'Pass', '48/48 responses', '48/48', 'Exact frozen V4 Pro fingerprint completed reliably.'),
        (2, 'Primary completion', 'Pass', '70 calls; 12 base cases plus two repeats', 'Complete planned run', 'Complete, but completion does not establish calibration.'),
        (3, 'Repeat consistency', 'Fail', '33/48 (68.75%); weighted kappa 0.5707', 'At least 90%', 'Single-label judgments are not sufficiently stable.'),
        (4, 'Pairwise repeat consistency', 'Pass, narrow', '11/12 (91.67%)', 'At least 90%', 'Does not override failed per-dimension consistency.'),
        (5, 'Swapped run completion', 'Fail', '5/12 cases; invalid', '12/12 cases', 'Position sensitivity remains unresolved.'),
        (6, 'Qwen sensitivity completion', 'Fail', '2/12 cases; invalid', '12/12 cases', 'Cross-family sensitivity remains unresolved.'),
        (7, 'Position consistency', 'Unresolved / Fail', 'Invalid partial: 24/29 (82.76%)', 'At least 90% on a complete run', 'Partial agreement cannot be calibration evidence.'),
        (8, 'Zero false pedagogy passes', 'Fail', '1 false pass', '0', 'The evaluator can approve a deterministic contract failure.'),
        (9, 'Blinded human reference', 'Pending', '0/48 labels', 'Complete independent reference', 'Deferred; not passed or waived.'),
        (10, 'Held-out isolation', 'Pass', '0 development or held-out accesses', '0 unauthorized accesses', 'The sealed boundary remains intact.')
) AS gate_outcomes(priority, gate, result, observed, threshold, interpretation)
ORDER BY priority;
