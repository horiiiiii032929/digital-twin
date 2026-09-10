# Product-first diagram review

The Japanese activity diagram models the first event-driven review opportunity
for a student who has opened the course and enabled in-app outreach but has not
sent a question. This is a code-derived scenario, not a newly recorded run.

- [Editable draw.io](01-agent-initiated-activity-ja.drawio)
- PNG (local artifact: `01-agent-initiated-activity-ja.png`)
- [SVG](01-agent-initiated-activity-ja.svg)
- PDF (local artifact: `01-agent-initiated-activity-ja.pdf`)
- [Japanese narrative and diagram allocation](../../planning/product-first-standard-diagrams-ja.md)

UML activity partitions indicate responsibility. Rounded rectangles are actions,
the diamond is a decision with guarded outgoing flows, and bullseyes end the
depicted scenario. A scenario ending is not a completed learning goal. The
API and worker share the software responsibility partition, but conversation
creation and goal creation are separate actions with their real function names
and request/worker ownership. The connected worker and delivery detail figures
are under `../implementation/`.

The 24-hour interval is measured from goal creation, not enrollment or login.
Authority, evidence, scheduling and content checks can prevent delivery. A
professor's explicit scheduled outreach is a separate entry path and does not
require a prior conversation. Existing slides and the demo video are unchanged.

Rebuild and export through draw.io Desktop:

```sh
uv run python -m scripts.build_product_first_activity --export
```

The generator replaces this diagram's files. Manual edits should be exported
directly from draw.io unless the generator is also updated.
