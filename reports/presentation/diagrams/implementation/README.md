# Implementation-linked UML figures

These editable Japanese review figures connect actual functions and persistence
boundaries to the product-first presentation. They are technical review assets,
not final English slide layouts. The original PPTX is not rebuilt by this command.

| Figure | Source | Preview |
| --- | --- | --- |
| Worker loop and exact `_process_once()` body | [draw.io](02-worker-cycle-ja.drawio) | [PNG](02-worker-cycle-ja.png) · [PDF](02-worker-cycle-ja.pdf) |
| Graph result, delivery, reuse/suppression and job commit | [draw.io](03-delivery-commit-ja.drawio) | [PNG](03-delivery-commit-ja.png) · [PDF](03-delivery-commit-ja.pdf) |

[Full narrative/function mapping and six code examples](../../planning/implementation-backed-examples-ja.md)
cover setup, empty conversations, initial outreach, event priority, graph
branches, planner fallback, the current learner-input limitation, retries, and
goal completion. An individual detail view has a declared scope; it must be
connected to the full model in the presentation.

The worker figure uses UML initial/final nodes, an explicit merge before the
loop, rounded actions and guarded decision flows. The sequence uses named
lifelines, filled call arrows, dashed reply arrows and an `alt` combined fragment.
The provider graph returns before in-app materialization. Delivery and job
commit are separate persistence operations. Parameter lists with `...` are
intentionally abbreviated; exact owning functions remain linked in the mapping.

Reproduce with:

```sh
uv run python -m scripts.build_implementation_diagrams --export
```

The script uses installed draw.io Desktop, exports PNG/SVG/PDF, and records the
SHA-256 hashes of the direct source files. The worker code block is extracted
from the Python AST rather than manually retyped. Before publishing a deck,
recheck the implementation revision and the selected runtime profile: experimental
and deterministic configurations must not be silently presented as identical.
