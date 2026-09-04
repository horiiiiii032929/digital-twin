# Final-report diagram quality audit

Status: four system-design figures completed a second visual-polish pass; complete report set still in progress  
Audit date: 2026-09-02  
Report target: 10--15 pages

## Conclusion

The four current Draw.io figures are an appropriate **system-design core**, but
they are not the complete diagram set for the report. The lecture material does
not justify inserting every UML type. It supports selecting a diagram only when
that notation answers a distinct question. For the report, the principal gaps
are:

1. a compact **design class diagram** with key attributes, operations,
   multiplicities, and role names;
2. a **quantitative comparison figure** covering both release and non-release
   results on normalized measures;
3. a **selected-profile decision map** that distinguishes selected, retained
   control, pending, and rejected components; and
4. one Draw.io **AWS deployment view** that maps the accepted logical layers to
   a visibly proposed, unevaluated runtime topology.

The use-case diagram should remain a scope reference or appendix figure. A
package diagram would duplicate the multi-tier architecture unless module
dependency becomes a research question. A state-machine diagram is useful only
if the report gives release lifecycle and rollback a dedicated discussion.

## Teaching evidence reviewed

| Teaching artifact | Evidence in the Enterprise Systems material | Report consequence |
| --- | --- | --- |
| System use cases | `4_requirements_analysis.pdf`, especially PDF pp. 61--68: named system boundary, actors, `<<include>>`, and organization by actor or subsystem | Keep one actor-organized scope figure; do not use it to explain runtime order or deployment |
| Use-case description | `4_requirements_analysis.pdf`, PDF pp. 13--20 and 33--50: trigger, actors, pre/postconditions, aligned actor/system steps, alternatives, and step-linked terminating exceptions | Keep the professor-publication description and exception table as related report components |
| Decision artifacts | `4_requirements_analysis.pdf`, PDF pp. 51--58: decision table, decision tree, and condition/response table | Use the policy decision table; a decision tree is unnecessary unless it communicates the same policy more clearly |
| Multi-tier architecture | `5_introduction_to_enterprise_system.pdf`, PDF pp. 18--19 and 33--35: Presentation, Business Logic, and Data Access layers; web, application, and database servers | Make the logical architecture the stable bridge from the lecture model to the implemented system |
| UML catalogue | `5_introduction_to_enterprise_system.pdf`, PDF p. 37: class and package structural diagrams; activity, use case, state machine, and sequence behavioral diagrams | Select by question rather than trying to display all six UML types |
| Design class diagram | `assignment/final/IT5004A2.pdf`, PDF p. 3: explicitly assessed with necessary classes, attributes, operations, multiplicities, and role names | Add a compact design class diagram; it is the clearest missing professor-aligned artifact |
| Sequence diagram | `assignment/final/IT5004A2.pdf`, PDF p. 3: actor to handler to `DBHelper`, numbered messages, activation, and dashed return | Retain one focused publication sequence rather than a system-wide message catalogue |
| Data-model tutorial | `assignment/3_tutorial_4/tutorial_4.pdf`: classes/entities, associations, role labels, and multiplicities | Carry role names and multiplicities into the compact design class view |
| Tutorial feedback | `assignment/2_tutorial_3/feedback.md`: administrator, staff, and customer should have separate login/logout use cases | Preserve role-specific sign-in/out use cases for Administrator, Professor, and Student |

Only two files are stored in the lecture directory: the requirements-analysis
deck and the enterprise-system introduction deck. The assignment and tutorial
materials were therefore also inspected for the professor's applied notation.

## Quality review of the four improved Draw.io figures

| Figure | What it now does well | Remaining limitation | Recommended report use |
| --- | --- | --- | --- |
| Actor-organized system use cases | Places each actor outside a named system boundary; uses verb-led ellipses; uses short direct, solid, arrowless associations; preserves role-specific sign-in/out; limits `<<include>>` to publication preflight | It is intentionally a scope catalogue and provides no order, state, or deployment semantics | Appendix or requirements subsection |
| Multi-tier logical architecture | Reproduces the lecture's left-to-right Presentation--Business Logic--Data Access separation; shows Web Server and Application Server explicitly; replaces prose blocks with visible responsibilities; isolates persistent and approved external systems | It remains a logical view and must not be cited as AWS deployment evidence | Main system-design figure |
| Governed tutoring activity | Uses named lanes, filled start nodes, bullseye final nodes, rounded activities, diamonds, and bracketed guards; distinguishes failed authorization as a terminating exception from insufficient evidence as a safe alternative; adds an explicit merge before commit | The complete policy path is necessarily dense; the policy decision table should carry detailed action conditions | Main figure if tutoring governance is central; otherwise appendix |
| Professor publication sequence | Uses an actor, underlined instance lifelines, hierarchical numbering, activation bars, dashed returns, and a complete `alt` frame; shortens data-access messages to the abstraction level used in the assignment example | `:ProfessorReleaseHandler` is a design-level handler name, while the implementation uses router functions; the class diagram should make that abstraction explicit | Main system-design figure |

The second pass standardized title and body typography, increased report-scale
label sizes, regularized use-case widths and line breaks, clarified the logical
architecture's hosting-independent status, enlarged activity decisions and
rerouted dense guards, and removed note/lifeline collisions from the sequence
diagram. The activity diagram is intentionally retained as a full-page portrait
figure; shrinking it into a half-page layout would make the guarded alternatives
harder to audit.

## Complete figure set for a 10--15-page report

### Recommended main-body set

| Priority | Figure | Reason for inclusion | Current state |
| --- | --- | --- | --- |
| 1 | Multi-tier logical architecture | Establishes separation of concerns and the stable system boundary | Improved Draw.io figure ready for content review |
| 2 | Governed tutoring activity | Shows deterministic authority, the bounded provider role, and safe outcomes | Improved Draw.io figure ready for content review |
| 3 | Professor publication sequence | Demonstrates the evaluated release gate and immutable publication collaboration | Improved Draw.io figure ready for content review |
| 4 | Evaluation evolution and release decision | Explains why valid No Release, invalid, and later Keep outcomes coexist | Existing evidence figure; needs final caption review |
| 5 | Normalized quantitative comparison | Compares retrieval, grounded answer, citation, safety, latency, and cost only where definitions and denominators are compatible | Missing; construct from machine-readable records |
| 6 | Selected-profile decision map | States what is selected, what remains a control, and what is pending or dropped | Missing |
| 7, conditional | Low-divergence AWS deployment | Answers the user's deployment question while preserving the qualified single-host topology | Earlier Graphviz prototype exists; Draw.io conversion missing and must say “proposed; not implemented or evaluated” |

If space is tight, the activity diagram moves to the appendix before any results
figure is removed. If AWS is not a report research question, its deployment
diagram also moves to the appendix.

### Appendix or supporting set

| Figure or component | Decision |
| --- | --- |
| Actor-organized system use cases | Include as the requirements boundary reference |
| Compact design class diagram | Add next; show only architecture-bearing classes rather than every model and method |
| Professor-publication use-case description | Retain as a table with normal, alternative, and step-linked exception flows |
| Policy decision and exception tables | Retain; these are explicitly lecture-aligned related artifacts |
| Release state machine | Add only if Draft, Published, Withdrawn, rollback, and gate transitions receive substantive analysis |
| Package diagram | Omit unless package dependency or replaceability is directly evaluated |
| Managed AWS target | Keep in the appendix as a proposed alternative, not as selected architecture |
| Evidence lineage and multimodal lineage | Include only where the methodology or limitations text refers to exact provenance and region-level evidence |

## Diagram acceptance checklist

Before any figure enters `report.tex`, require all of the following:

- it answers one explicit report question and does not mix functional scope,
  runtime order, logical layers, and physical deployment;
- every symbol has the meaning used in the lecture or is defined in the caption;
- labels remain readable when the figure is placed at its intended LaTeX width;
- observed, implemented, selected, and proposed states are visually or
  caption-wise distinguishable;
- the figure is traceable to repository evidence or is explicitly labelled as
  a proposal;
- unfavorable and non-release evidence is not omitted from comparison figures;
- the editable `.drawio`, reviewable `.svg`, and LaTeX-ready `.pdf` remain in
  sync; and
- the rendered PDF is one page, unclipped, and free of connector/label
  collisions.

## Next review unit

The next incremental unit should contain only two new Draw.io figures:

1. the compact design class diagram; and
2. the low-divergence AWS deployment diagram.

After those are reviewed, the next unit should be the normalized quantitative
comparison and selected-profile decision map. This order keeps system design
and academic results separate and avoids drafting the entire report in one
pass.
