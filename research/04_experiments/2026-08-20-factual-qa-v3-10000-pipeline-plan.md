# Factual-QA v3 10,000-case pipeline plan

Date: 2026-08-20

Issue: #87

Status: provider-free design implemented; dataset writing and provider execution unauthorized

## Decision question

Can a source-linked generation and review method create 10,000 trustworthy
dummy factual-QA cases while exposing quality, abstention, course-isolation,
latency, and cost failures?

This implements the supervisor's large dummy-dataset suggestion. It is not a
model leaderboard, a replacement for the verified 100-case retrieval set, or a
Professor Digital Twin fidelity evaluation. A failed gate changes the pipeline
method before another bounded run.

## Prediction

Deterministic source truth plus exact claim and citation lineage will make
acceptance inspectable at 10,000-case scale. A qualified independent reviewer
should catch semantic and boundary defects that deterministic checks cannot,
while never becoming ground truth. The primary risks are repetitive authored
questions, malformed provider responses, weak boundary handling, and dispute
volume that makes cost or human review unbounded.

## Fixed dummy source universe

- 20 synthetic courses.
- 50 source units per course; 1,000 source units total.
- Eight deterministic atomic claims per source; 8,000 claims total.
- Text, code, table, diagram, equation, screenshot, and scanned-document forms.
- No Academia Vault, real course, instructor, student, credential, or private
  path content.

The deterministic source claims are authoritative. LLM agreement is advisory
and cannot create, alter, or replace ground truth.

## Fixed 10,000-case composition

The dataset contains 8,000 answerable and 2,000 boundary cases, exactly 500 per
dummy course. Answerable slices cover direct, paraphrased, multi-source, code,
table, diagram, equation, screenshot, and scan cases. Boundary slices contain
500 each for no evidence, ambiguity, cross-course confusion, and academic
integrity.

## Prospective method

1. Build and validate source and case blueprints locally with zero model calls.
2. DeepSeek V4 Flash authors wording and answers from fixed source truth.
3. Deterministic checks enforce schema, target claims, exact evidence quotes,
   source lineage, expected action, and no extra claims.
4. The Mistral Small 4 route qualified by run 006 independently reviews each
   case. Its verdict is advisory and cannot override deterministic failure.
5. DeepSeek V4 Pro reviews only bounded unresolved disputes. Malformed replies
   are persisted as failures with complete accounting and no retry.
6. Exact and near-duplicate checks run before acceptance. Only unresolved high
   risk cases enter a human packet, capped at 12.

Gemma and Claude remain excluded. Exact provider model identities, routing,
prices, prompts, and call limits must be revalidated and frozen before each
paid stage.

## Stage gates

Execution advances through separately authorized cumulative checkpoints:

| Stage | New cases | Cumulative cases |
| --- | ---: | ---: |
| Pilot | 100 | 100 |
| Checkpoint | 900 | 1,000 |
| Scale | 9,000 | 10,000 |

There is no automatic promotion. Each stage must retain complete call, token,
latency, cost, malformed-response, deterministic failure, reviewer disagreement,
mutation, duplicate, and human-packet accounting. Hard gates are frozen in the
instrument before execution. Any failed gate produces **Refine**, not a model
ranking or hidden retry.

## Current implementation boundary

`scripts/build_factual_qa_v3_10000_blueprints.py` deterministically validates
the 1,000-source, 8,000-claim, 10,000-blueprint design in memory. The design is
byte-stable and hashable. Writing the generated artifact is fail-closed under
the repository execution freeze, and no provider stage is authorized.

The next safe step is to publish this provider-free design, then freeze a
separate 100-case execution instrument with current model identity, prompts,
fresh pricing, call bounds, and a paid authorization checkpoint.
