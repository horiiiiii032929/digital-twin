# IT5004 presentation teaching001

Purpose: replace fictional teaching material in presentation examples with
Professor Lek's actual IT5004 Enterprise Systems Architecture Fundamentals
lecture. User explicitly requested these materials and actual AI-generated
responses in the current conversation. Historical evaluation datasets and
results retain their identities; this is a new presentation-development run.

Source: Lecture5, PDF pages24,33,34 (printed slides25,34,35), on data access,
business logic and presentation. Cover identifies Lek Hsiang Hui. Private
source and exact extracted text/hashes: data/interim/it5004-presentation-001/.
Extraction removes only repeating footer and page numbers. Pages visually
inspected. Use lectures only; exclude assignment solutions, private student
records, secrets and unrelated materials. Authored shopping-website questions
are illustrative learner questions, not quotations from the professor.

Decision question: does this course-grounded, familiar scenario clearly show
how teaching settings influence actual app responses? Prediction: explanation
first versus elicitation first is distinguishable; both must use the lecture's
separation of concerns and address the follow-up. Check source consistency,
stage fit, continuation, unclear names, unsupported extra implementation detail,
and withheld outputs qualitatively. No general quality percentage or claim to
reproduce the professor's actual personal style. Profiles are synthetic.

Existing V4 control and V19 Luna candidate, same source/profile/questions per
arm, one repeat, seed7801, four histories/two turns each. Existing persistent
application-service runner with restart before second turn. One subject and two
profiles are sufficient for choosing an illustration, not general robustness
or real-learner evaluation. No prompt, source or validation changes after the
run begins; retain failures. No promotion or change to existing release.

Provider: existing configured OpenAI Responses API, gpt-5.6-luna low planning
and generation, medium candidate audit/repair, output cap3000. No Sol. Existing
project API credential; account class and contractual retention/training/region
settings were not independently verified in this run. Do not assert no-training
or regional guarantees. Transferred fields: three lecture text excerpts,
synthetic questions/state/settings and generated replies; no full PDF or images.
Local derived artifacts stay in ignored storage; no public publication or new
remote file upload. No project-controlled deletion of provider logs is claimed.
Maximum144 calls and US$14.08 reservation within remaining cumulative US$30.

```sh
uv run --env-file .env python -m scripts.run_paired_pedagogy_development --live --candidate v19-luna-luna-medium --packet data/interim/it5004-presentation-001/packet.json --input-provenance data/interim/it5004-presentation-001/source-manifest.json --input-provenance research/04_experiments/it5004-presentation-teaching-001.md --output-dir reports/generated/it5004-presentation-teaching-live-001 --maximum-calls 144 --maximum-cost-usd 14.08
```

Every raw response is retained privately. Durable results contain sanitized
observations and hashes, not copied lecture passages. Independent calibrated
semantic grading is outside this small illustration run. Report latency, calls,
tokens and cost; memory and hosted capacity are not measured.
