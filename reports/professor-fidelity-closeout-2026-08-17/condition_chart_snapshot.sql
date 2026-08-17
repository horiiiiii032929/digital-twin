-- Chart-ready projection of the frozen 12-case deterministic diagnostics.
SELECT *
FROM (
    VALUES
        ('C0', 'Hard gates', 4.0 / 12.0, 4, 12),
        ('C0', 'Structural', 1.0 / 12.0, 1, 12),
        ('C1', 'Hard gates', 10.0 / 12.0, 10, 12),
        ('C1', 'Structural', 9.0 / 12.0, 9, 12),
        ('C2', 'Hard gates', 10.0 / 12.0, 10, 12),
        ('C2', 'Structural', 9.0 / 12.0, 9, 12),
        ('C3', 'Hard gates', 6.0 / 12.0, 6, 12),
        ('C3', 'Structural', 5.0 / 12.0, 5, 12)
) AS condition_chart(condition, diagnostic, rate, passes, case_count)
ORDER BY condition, diagnostic;
