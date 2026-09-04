# System-design report components

These components are intentionally separate from `report.tex`. They are the
first review unit for the System Design and Implementation section and should
not be treated as accepted report content until their scope and terminology
have been reviewed.

## Visual components

| Component | Primary question | Proposed placement |
| --- | --- | --- |
| `course-digital-twin-use-cases` | What can each actor ask the system to do? | Appendix or opening of system-design section |
| `course-digital-twin-logical-architecture` | How are presentation, business logic, data access, persistence, and external systems separated? | Main system-design section |
| `governed-tutoring-activity` | How does one student turn move across responsibility boundaries and fail safely? | Main system-design section |
| `professor-publication-sequence` | How do preflight gates and atomic publication interact over time? | Main system-design section |

Editable Draw.io sources are under `reports/figures/drawio/`; rendered PDF and
SVG versions are under `reports/figures/`. They use the monochrome notation and
diagram separation taught in IT5004. The earlier Graphviz context,
authority-flow, and AWS figures remain available as content drafts and
traceability artifacts, but they are not authoritative diagram sources.

The conversion applies the lecture conventions directly:

- actors remain outside a named system boundary and connect to verb-led system
  use cases;
- role-specific sign-in/out use cases remain separate, consistent with the
  earlier tutorial feedback;
- `<<include>>` is used only for the reusable publication-preflight behavior;
- activities use responsibility swimlanes, initial/final nodes, decision
  diamonds, and bracketed guard conditions;
- the publication interaction uses actor, Handler, Service, and Data Access
  lifelines, hierarchical message numbering, activation bars, dashed returns,
  and an `alt` frame; and
- the logical architecture preserves the lecture's left-to-right Presentation,
  Business Logic, and Data Access layers.

## LaTeX components

`system-design-tables.tex` contains the publication use-case description, the
tutoring action decision table, and the publication exception table. It expects
the report preamble to load `booktabs`, `tabularx`, and `array`.

The tables distinguish implemented local behavior from proposed deployment
architecture. They make no claim that AWS hosting, professor fidelity, student
usability, or learning improvement has been evaluated.
