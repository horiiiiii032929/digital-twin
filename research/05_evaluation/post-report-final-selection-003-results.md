# Final selection paired series 003

Decision: **Refine evaluation adapter; incomplete candidate histories.** The evaluation factory did not accept the new explicit audit-model keyword. Candidate made zero calls and delivered zero outputs. Baseline-only replies cannot form a fair comparison. Missing turns are retained in history records and not fabricated as responses.

Twelve planned paired synthetic cases, two turns per arm (48 planned outputs; consult completion records for missing turns), seed7801. V4 uses Luna-low; candidate V19 uses Luna-low draft and Luna-medium audit/repair. All previous versions and outputs retained. No Sol calls. No human review or learning-effect claim. Exact configurations, hashes, source archives, token/cost counts and delivered replies are recorded per case. Process memory was not independently sampled.

| Run | V4 cost | Candidate cost | Elapsed seconds | Source unchanged |
| --- | --- | --- | --- | --- |
| [post-report-final-selection-003-case-01-live-001](records/post-report-final-selection-003-case-01-live-001.json) | $0.000919 | $0.000000 | 11.2 | True |
| [post-report-final-selection-003-case-02-live-001](records/post-report-final-selection-003-case-02-live-001.json) | $0.001395 | $0.000000 | 11.3 | True |
| [post-report-final-selection-003-case-03-live-001](records/post-report-final-selection-003-case-03-live-001.json) | $0.001408 | $0.000000 | 11.9 | True |
| [post-report-final-selection-003-case-04-live-001](records/post-report-final-selection-003-case-04-live-001.json) | $0.001413 | $0.000000 | 19.3 | True |
| [post-report-final-selection-003-case-05-live-001](records/post-report-final-selection-003-case-05-live-001.json) | $0.001364 | $0.000000 | 12.2 | True |
| [post-report-final-selection-003-case-06-live-001](records/post-report-final-selection-003-case-06-live-001.json) | $0.001302 | $0.000000 | 17.3 | True |
| [post-report-final-selection-003-case-07-live-001](records/post-report-final-selection-003-case-07-live-001.json) | $0.001498 | $0.000000 | 13.7 | True |
| [post-report-final-selection-003-case-08-live-001](records/post-report-final-selection-003-case-08-live-001.json) | $0.000723 | $0.000000 | 6.3 | True |
| [post-report-final-selection-003-case-09-live-001](records/post-report-final-selection-003-case-09-live-001.json) | $0.000981 | $0.000000 | 8.6 | True |
| [post-report-final-selection-003-case-10-live-001](records/post-report-final-selection-003-case-10-live-001.json) | $0.001067 | $0.000000 | 9.3 | True |
| [post-report-final-selection-003-case-11-live-001](records/post-report-final-selection-003-case-11-live-001.json) | $0.001553 | $0.000000 | 15.2 | True |
| [post-report-final-selection-003-case-12-live-001](records/post-report-final-selection-003-case-12-live-001.json) | $0.001651 | $0.000000 | 15.4 | True |

All cases include their paired arm in the same run; failed deliveries remain in the denominator. There is no statistical inference from this table alone. Reproduce via the frozen invocation and orchestration source in each run’s input-artifacts directory, with new run IDs and a prior cumulative-budget reservation.
