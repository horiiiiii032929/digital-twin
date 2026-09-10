# IT5004 presentation teaching002: fixture correction

Run001 made zero provider calls: three authored objective labels were identical,
violating the application's uniqueness contract before runtime creation.
Keep its output and failure record. Correct only the authored objective metadata
to identify each layer's responsibility separately in private packet-v2.json.
Lecture excerpts, synthetic profiles, fixed student questions and runtime
configuration are unchanged. No validation is weakened. No model output from001
exists to select or reuse. This is one corrected execution, not an output retake.

All scope, provider/data authorization, review dimensions, caps and limitations
in it5004-presentation-teaching-001.md apply. Transfer the unused US$14.08
reservation to002. Source provenance remains in source-manifest.json.

```sh
uv run --env-file .env python -m scripts.run_paired_pedagogy_development --live --candidate v19-luna-luna-medium --packet data/interim/it5004-presentation-001/packet-v2.json --input-provenance data/interim/it5004-presentation-001/source-manifest.json --input-provenance research/04_experiments/it5004-presentation-teaching-001.md --input-provenance research/04_experiments/it5004-presentation-teaching-002.md --output-dir reports/generated/it5004-presentation-teaching-live-002 --maximum-calls 144 --maximum-cost-usd 14.08
```
