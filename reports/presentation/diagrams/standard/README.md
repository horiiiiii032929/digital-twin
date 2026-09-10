# Standard-notation SDLC diagrams

This is the recommended diagram set for the presentation. It supersedes the earlier custom comparison-layout drafts in the parent folder. It contains eight editable draw.io pages and individual PNG/SVG exports; no presentation deck or video has been produced.

## Deliverables

- [Editable draw.io source](sdlc-standard-diagrams.drawio)
- Eight-page review PDF (local artifact: `sdlc-standard-diagrams.pdf`)

| Page | Notation and scope | Image |
| --- | --- | --- |
| 01 | C4 System Context: course teaching system and connected people/provider | PNG (local artifact: `01-c4-context.png`) · [SVG](01-c4-context.svg) |
| 02 | C4 Container: web, API, separate workers and data stores | PNG (local artifact: `02-c4-containers.png`) · [SVG](02-c4-containers.svg) |
| 03 | UML Activity: professor/application/student partitions, preflight and publication | PNG (local artifact: `03-uml-course-activity.png`) · [SVG](03-uml-course-activity.svg) |
| 04 | UML Class: selected domain entities, associations and multiplicities | PNG (local artifact: `04-uml-domain-classes.png`) · [SVG](04-uml-domain-classes.svg) |
| 05 | UML Sequence: preflight and conditional publication | PNG (local artifact: `05-uml-publication-sequence.png`) · [SVG](05-uml-publication-sequence.svg) |
| 06 | UML Sequence: generation and authority/revision checks at commit | PNG (local artifact: `06-uml-tutoring-sequence.png`) · [SVG](06-uml-tutoring-sequence.svg) |
| 07 | UML State Machine: active, completed, expired and cancelled goals | PNG (local artifact: `07-uml-goal-state-machine.png`) · [SVG](07-uml-goal-state-machine.svg) |
| 08 | UML Sequence: saved in-app delivery and worker retry | PNG (local artifact: `08-uml-recovery-sequence.png`) · [SVG](08-uml-recovery-sequence.svg) |

Canvas: 1600 × 1000, allowing readable standalone technical diagrams. PNG: approximately 2400 × 1500. Keep aspect ratio when inserting into slides. All labels are English. PNG/SVG exports embed the editable diagram data.

## Notation rules

- C4: specify level and scope, element type, container technology, responsibility, directed relationship, protocol where applicable and a key. People and external providers stay outside the system boundary. Ingestion and autonomy workers are separate applications.
- UML Activity: use responsibility partitions, rounded actions, initial/final nodes, decision/merge diamonds and bracketed guards. A preflight pass does not itself represent a professor's publication request.
- UML Class: use name/attribute compartments, solid associations and endpoint multiplicities. These are conceptual domain classes, not a complete database schema or an exhaustive source-code class diagram. Attribute types and methods are deliberately omitted.
- UML Sequence: lifelines identify participant roles/types; synchronous calls use filled arrowheads; replies use dashed open arrows. Conditional interactions use opt/alt combined fragments, operand guards and an operand separator. Return messages pass through the actual participating services.
- UML State Machine: use initial pseudostate, rounded states and trigger [guard] / effect labels. The initial transition has an initialization effect, not an event trigger. Persisted terminal records are shown as states, not invented deletion/finalization transitions.
- Notes contain qualifications or constraints. Colour does not introduce new behavioral semantics.

References: [OMG UML 2.5.1](https://www.omg.org/spec/UML/2.5.1/About-UML), [C4 notation](https://c4model.com/diagrams/notation), [C4 container diagram](https://c4model.com/diagrams/container), [C4 review checklist](https://c4model.com/diagrams/checklist).

These are project diagrams using standard notation, not a claim of third-party standards certification. C4 itself is notation independent; its documented element and relationship conventions are used here.

## Source traceability and limits

| Pages | Project sources | Scope qualifications |
| --- | --- | --- |
| 01–02 | [Reported architecture](../../../figures/course-twin-architecture.dot), services/apps/scripts entry points | Logical runtime, not a verified public deployment. Configured inference paths are optional. SQLite records summarize logical storage, not every physical database file. |
| 03, 05 | [Course activity](../../../figures/course-twin-lifecycle.dot), [publication sequence](../../../../research/06_reports/final/figures/publication-sequence.tex), [publication service](../../../../src/digital_twin/student/publication.py) | Successful owned-release path; failed preflight returns to revision. Index preparation and observer hooks do not join the publication transaction. |
| 04 | [Reported domain relationships](../../../figures/course-twin-data-relationships.dot), [student models](../../../../src/digital_twin/student/models.py), [autonomy models](../../../../src/digital_twin/student/autonomy_models.py) | Selected entities only. An opportunity can have zero or one goal; one goal can have many opportunities. |
| 06 | [Tutoring sequence](../../../../research/06_reports/final/figures/tutoring-sequence.tex), [tutoring service](../../../../src/digital_twin/student/service.py), [repository](../../../../src/digital_twin/student/repository.py) | Fresh request reaching generation. Early evidence/policy branches and duplicate handling are summarized in the scope/footer. Message names describe operations; they are not literal API method signatures. |
| 07 | [Goal models](../../../../src/digital_twin/student/autonomy_models.py), [goal interpretation](../../../../src/digital_twin/student/autonomy_control.py), [repository lifecycle](../../../../src/digital_twin/student/repository.py) | Completion guard shown for evidence-count V2 state, not the separate legacy T1 threshold rule. Attempt limit blocks work without an exhausted state. Scope invalidation includes applicable authority/release/consent revocation; a temporary pause is not presented as cancellation. |
| 08 | [Autonomy delivery and job commit](../../../../src/digital_twin/student/autonomy_service.py), [crash-recovery tests](../../../../tests/digital_twin/test_governed_autonomy.py) | Local in-app message identity and persistence. Worker lifeline represents the service role across restart. Retry does not imply exactly-once external side effects. |

The diagrams describe inspected implementation responsibilities, not new benchmark results. Comparison scores belong in ordinary result tables; findings can annotate the appropriate standard diagram rather than creating a new notation. The previous result-bearing diagrams remain historical drafts and are not the recommended insertion assets.

## Reproduction and editing

```sh
uv run python -m scripts.build_standard_sdlc_diagrams --export
```

Requires draw.io Desktop at /Applications/draw.io.app. The generator rebuilds the source and exports each page. After manual edits in draw.io, export directly from draw.io; rerunning the generator replaces those manual changes.

Review completed: draw.io exports, visual inspection of all eight pages, source/target bindings, domain multiplicities, actual goal-status set, conditional-fragment labels and source links. Shapes and text remain editable. Remaining presentation work is to select these assets for the relevant slides and size them for the final deck.

