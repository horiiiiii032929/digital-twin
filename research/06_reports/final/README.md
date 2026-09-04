# Final Report

Use this folder for final paper, presentation, and demo evidence.

The protected final-delivery runway begins after the 2026-08-26 evidence
freeze. Complete the full report draft and main figures by 2026-09-03, finish
revisions, slides, demo stabilization, and rehearsal by 2026-09-09, and reserve
2026-09-10 through 2026-09-12 for blocking corrections and submission
packaging. Do not use the buffer for new features, methods, or claims.

Recommended sections:

- Problem and motivation
- Related work
- System design
- Implementation
- Deployment architecture and operational controls
- Evaluation
- Professor and student pilot usability
- Privacy, security, reliability, cost, and rollback
- Limitations
- Future work

Every material claim should link to a registered result, architecture decision,
professor checkpoint, or primary source. Distinguish a deployable controlled
pilot from institution-wide production readiness, and do not claim learning
improvement without a consented outcome study.

System-flow figures must follow the separation and UML conventions recorded in
[the IT5004 enterprise-systems alignment review](it5004-system-design-alignment.md)
before they are promoted from prototype artwork into the LaTeX report.
The first modular, IT5004-aligned review set is indexed in
[the system-design component README](components/README.md); it remains separate
from `report.tex` until its scope and terminology are accepted.

Maintain the report argument in
[`reports/claim-to-evidence-matrix.md`](../../../reports/claim-to-evidence-matrix.md)
from protocol freeze onward. A result belongs in the final paper or slides only
when the row links to a stable registered result and machine-readable source.

## Evidence inventory

Before drafting or refreshing the report, rebuild the report-specific evidence
inventory:

```bash
uv run python -m scripts.build_final_report_evidence_inventory
```

The command writes a complete file manifest, a parsed evaluation-result ledger,
aggregate counts for ignored local evidence, and a validation summary under
`research/06_reports/final/evidence-inventory/`. Ignored raw and generated
directories are represented by counts and byte totals only; their filenames,
hashes, and contents must not be copied into committed report artifacts.
