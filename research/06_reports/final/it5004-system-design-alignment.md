# IT5004 alignment for final-report system design

Status: source review complete; four Draw.io system-design figures improved and quality-audited  
Purpose: align the report's system-flow artifacts with the modeling approach
taught in IT5004 Enterprise Systems Architecture Fundamentals

## Sources reviewed

The canonical local sources are under
`academia_vault/2025_semester_1/IT5004_enterprise_system/`.

- `lecture/4_requirements_analysis.pdf` (71 pages): system use cases and system
  boundaries; actor--system flow-of-events tables; normal, alternative, and
  terminating exception flows; related decision artifacts; `<<include>>`; and
  organization by actor or subsystem. The most relevant examples are on PDF
  pages 10--20, 34--50, 54--58, 61--64, and 66--68.
- `lecture/5_introduction_to_enterprise_system.pdf` (38 pages): client/server
  separation; web, application, and database servers; presentation, business
  logic, and data-access layers; persistence after application failure; and
  separation of concerns. The most relevant examples are on PDF pages 7--19,
  24--29, and 32--38.
- `assignment/final/IT5004A2.pdf` (3 pages): the professor's System Design brief
  requires a design class diagram and a sequence diagram. Its sequence example
  sends numbered messages from an actor to a handler and then to `DBHelper`,
  with a dashed return.
- The mid-term activity diagram, use-case diagram, use-case description, and
  final class/sequence submissions were inspected as examples of how the
  notation was applied. They are supporting examples, not authoritative
  teaching definitions.

## Modeling rules to carry into this report

### Separate scope, behavior, interaction, and deployment

One diagram should answer one design question:

1. A **system use-case diagram** defines functional scope. Actors remain
   outside a named system boundary; verb-led use cases remain inside and are
   grouped by actor or subsystem.
2. A **use-case description** defines one important workflow using a triggering
   event, actor, preconditions, postconditions, numbered actor/system steps,
   alternative flows, and terminating exception conditions tied to step
   numbers.
3. A **UML activity diagram** explains branching behavior with an initial
   node, final node, action nodes, guard-labelled decisions, and swimlanes when
   responsibility changes.
4. A **UML sequence diagram** explains runtime collaboration. Lifelines should
   follow the presentation/business-logic/data-access separation; messages are
   ordered and numbered, returns are dashed, and `alt` or `loop` frames carry
   non-trivial branches.
5. A **logical architecture diagram** explains separation of concerns through
   presentation, business-logic, and data-access layers before naming hosting
   products.
6. A **deployment diagram** maps those logical responsibilities to runtime
   nodes and external systems without redefining application behavior.

### Keep decision complexity outside the main flow

The lecture treats decision tables, decision trees, and condition/response
tables as related artifacts. The tutoring action lattice is therefore clearer
as a compact decision table than as several branches embedded inside one
oversized flowchart. The activity diagram can reference the policy decision and
remain readable.

### Show alternative and exception semantics precisely

- An alternative flow still reaches the use-case goal by a different path.
- An exception condition terminates the use case immediately.
- Each exception identifies the normal-flow step at which it can occur.

For the Course Digital Twin, insufficient evidence can be an alternative safe
flow when the system returns a clarification or abstention. Failed
authorization, cross-course access, invalid release state, or an unrecoverable
commit failure are terminating exceptions.

### Preserve the enterprise layers

The logical architecture should use this course-aligned path:

`Professor / Student / Administrator clients`
`-> Presentation layer`
`-> Business-logic layer`
`-> Data-access and provider-adapter layer`
`-> Persistent stores or approved external systems`

The web application belongs to the presentation layer. FastAPI handlers,
authorization, evidence policy, tutoring orchestration, evaluation, and release
control belong to business logic. Repositories, content-store interfaces,
retrieval adapters, provider gateways, and durable job/outbox adapters belong
to the data-access/adaptation boundary. SQLite and content-addressed objects are
persistence mechanisms rather than business-logic components.

## Consequences for the current drafts

| Current artifact | Problem under the IT5004 framing | Required revision |
| --- | --- | --- |
| F1 system context | Mixes actors, use cases, logical layers, and physical adapters | Split into a UML system use-case diagram and a separate multi-tier logical architecture |
| F2 governed tutoring flow | Correctly exposes decisions but does not show responsibility lanes or standard start/end semantics | Convert to a swimlane activity diagram and move the action lattice to a decision table |
| F3 release lifecycle | A lifecycle picture alone does not show collaborating objects or actor/system steps | Use a concise use-case description plus a sequence diagram for professor publication |
| F7 evidence lineage | Reads as data lineage but not runtime collaboration | Retain lineage, then reference it from a focused tutoring sequence diagram |
| F9/F10 AWS proposals | Name deployment services before making the logical tier mapping explicit | Preserve the same presentation/business/data-access responsibilities inside both AWS options |
| F11 failure map | Risks mixing recoverable alternatives with terminating exceptions | Replace or supplement it with a step-linked exception table and a compact policy decision table |

## Draw.io implementation rules

The editable review sources are uncompressed `.drawio` documents under
`reports/figures/drawio/`. The Draw.io versions, rather than the earlier
Graphviz sketches, are authoritative for the four converted system-design
components.

- Keep the diagrams monochrome, with one-pixel UML lines, white fills, and no
  decorative shadows or vendor iconography.
- Keep system-use-case actors outside the system boundary. Use solid,
  arrowless associations and dashed open-arrow `<<include>>` dependencies.
- Retain the role-specific sign-in/out use cases identified in the tutorial
  feedback rather than collapsing them into one ambiguous login use case.
- Use rounded activity nodes, diamonds, bracketed guards, a filled initial
  node, a bullseye final node, and named responsibility lanes.
- Use underlined sequence participants, dashed lifelines and returns, narrow
  activation bars, hierarchical message numbering, and an explicit `alt`
  frame for failed and passed preflight paths.
- In the logical architecture, preserve the lecture's left-to-right flow from
  Presentation Layer to Business Logic Layer to Data Access (DA) Layer. AWS
  services may be mapped only after this logical separation is accepted.

## Recommended system-design bundle

For a 10--15-page report, the main text should contain three system-design
figures:

1. **Multi-tier logical architecture** -- the stable separation of concerns,
   independent of local or AWS hosting.
2. **Governed tutoring activity diagram** -- the complete student-turn flow
   with swimlanes, guarded alternatives, and terminating exceptions.
3. **Professor publication sequence diagram** -- ordered collaboration from
   professor action through evaluation and immutable release publication.

Use-case scope, the design class diagram, the detailed use-case descriptions,
the policy decision table, and the managed AWS alternative can appear as small
tables or appendix figures. This preserves the professor's notation without
turning the report into a diagram catalogue.

## Conversion record

1. F2 was redrafted as an IT5004-style Draw.io swimlane activity diagram. The
   improved version separates the failed-authorization exception from safe
   alternative outcomes and uses an explicit merge before atomic commit.
2. F1 was split into Draw.io logical multi-tier architecture and system-use-case
   scope diagrams. The improved use-case source contains three actor-organized
   system-boundary views with short, direct associations; the architecture now
   uses visible responsibilities rather than explanatory prose blocks.
3. F3 was drafted as a Draw.io professor-publication sequence diagram and a
   separate LaTeX use-case description. The improved sequence uses underlined
   instance names, shorter DA-level messages, and an `alt` frame that encloses
   both complete outcomes.
4. F11 was drafted as a policy decision table and a step-linked exception
   table.
5. F9/F10 still require Draw.io conversion and remapping after the logical
   architecture is accepted.

The converted figures remain review drafts until their terminology and scope
are approved. They should not yet be inserted into `report.tex` as final system
design evidence. The completeness and quality decisions are recorded in
[`diagram-quality-audit.md`](diagram-quality-audit.md).
