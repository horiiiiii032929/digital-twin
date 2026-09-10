# Visual presentation revision

The 15 draw.io diagrams replace text-heavy explanations in the 70-slide cited deck. Slide 17 corresponds to slide 15 in the previous 61-slide Revised deck. Each diagram is authored for this project using the existing implementation, examples and recorded results. Examples remain labeled as illustrations; no new experiment or model output is introduced.

Affected slides: 15, 17, 24, 32, 33, 38, 43, 44, 47, 50, 53, 61, 63, 69 and 70. Process fragments use conventional action, decision and connector shapes. Other diagrams are explanatory comparisons, inputs/outputs or arithmetic illustrations, rather than claims to be complete UML specifications.

The editable source is the `.drawio` file. PNG exports preserve the diagram as a single image in PowerPoint. Text, tables and existing charts outside these diagrams remain native slide objects. The presentation is a visual explanation, not a literal execution trace unless the slide explicitly says so.

Rebuild diagrams with `python3 reports/generated/it5004-visual/diagrams.py` from the repository root. It uses the installed draw.io export command. The canonical deck authoring file is `reports/generated/it5004-visual/build.mjs`, followed by `embed.py`, `citations.py`, `finalize.mjs` and `package.py`. Use a new finalization filename for each revision. Do not overwrite previous deliveries.
