# Conditional revision isolated Stage A preflight review

This is an assistant source review of the isolated direct revision component. It is not human review, whole-application V14 qualification, or semantic acceptance of generated responses.

The isolated root is `/tmp/digital-twin-v14-stage-a-20260906`. Its exact source manifest is retained at `reports/generated/conditional-revision-controls-v1/isolated-source-manifest.json`. The reviewer independently compared all 190 members of the prior V13 source archive with this snapshot: every non-overlay member was byte-identical, and all five declared overlay hashes matched. The base ZIP SHA-256 is `c60fcb0e4a0ec0f47f107719364ea930e3ec2e8f99c3057e680b588bf0e34d32`.

The overlays are the conditional revision component, provider schema registry, direct controls runner and its test, and the prospective conditional revision plan. The snapshot does not install the new V14 factory or unfinished generated-preview feature. The runner calls the actual conditional helper directly on authored drafts, preserves researcher-authored origin on KEEP, attributes replacements to Sol, and records the assessed input/draft hashes and complete conditional decision. Gold is excluded from the provider payload. The final 112-control packet SHA-256 is `158b135f656fd116b4801f49374fbf85eb9bec326e68a0a63ff488888e599b0b`.

The execution owner ran, from the isolated root:

```sh
PYTHONPATH=. /Users/hikaru/Documents/dev/digital-twin/.venv/bin/python -m pytest -q tests/test_factual_revision_controls.py -k 'not three_roles and not unknown_revision'
```

Result: 10 passed, 2 deselected in 8.32 seconds; log `/tmp/v14-isolated-component-tests.log`. The two excluded tests require the absent integrated multi-role helper. The earlier broader copied suite's 11 failures and 22 passes are retained; they must not be presented as an application regression pass. Prior independent conditional-core tests passed 21 cases on the main tree, but do not substitute for snapshot evidence.

The reviewed scope is sufficient for the named 112-case injected contract followed by the already authorized finite direct-helper Stage A trial, conditional on the contract and unchanged source/input hashes. No whole-tree correctness inventory was refreshed while unrelated application sources were changing. Semantic gates remain all 40 prior adequate drafts preserved, at least 30 of 32 prior defective drafts repaired, all 8 prior disclosure defects repaired, all 16 fresh adequate drafts preserved, all 16 fresh defective drafts repaired, zero critical errors, and known usage. All outputs require subsequent independent assistant review and root adjudication; no Stage B acceptance follows from this preflight.
