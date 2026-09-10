# Plain-language teaching demo001

Decision question: can a self-contained familiar lesson show what the current
experimental app actually does with explicit explanatory versus Socratic
preferences? This is presentation development, not a new component selection.

Prediction: explaining a password reset link requires no invented product name
or unseen PDF. The explanatory profile should answer first; the Socratic profile
should elicit an attempt first. Both should address the supplied follow-up.

Dataset: plain-language-teaching-demo-v1, two synthetic profiles, identical source
and two fixed student turns. All source text is available on the eventual slide.
Existing V4 control and V19 Luna-low/Luna-medium audit candidate, existing paired
persistent application-service runner, one repeat, seed7801. The second turn
includes the runner's existing persistence/restart check. No source or prompt
repair after observing output. Retain withheld and failed responses.

Before execution, inspect these dimensions: source consistency (30-minute expiry,
one use, replacement invalidates prior links), profile-appropriate first turn,
response to the supplied second-turn attempt, no fabricated account information,
no unexplained special names, no source-only repetition instead of required help.
Report each response, action, elapsed time, provider calls/cost, and contract
completion. Author review is qualitative and not independent calibrated grading.
No aggregate quality percentage, learning benefit or real-instructor fidelity.

One topic and two profiles suffice for selecting an understandable illustration;
they do not cover general boundary, adversarial or privacy robustness. Existing
component evaluation and failure records remain authoritative for adoption.
No policy, algorithm, default profile or application change is proposed.

Reserve US$14.08 within the cumulative US$30 authorization. Maximum144 calls,
3000-token existing caps, no Sol. No retry series. Output:
reports/generated/plain-language-teaching-demo-live-001. Full configuration,
source hashes, code revision/dirty state and provider records come from runner.

Reproduce with the configured provider credential loaded privately:

```sh
uv run --env-file .env python -m scripts.run_paired_pedagogy_development --live --candidate v19-luna-luna-medium --packet research/05_evaluation/datasets/plain-language-teaching-demo-v1.json --input-provenance research/04_experiments/plain-language-teaching-demo-001.md --output-dir reports/generated/plain-language-teaching-demo-live-001 --maximum-calls 144 --maximum-cost-usd 14.08
```

Keep an example only as an illustration of the actual response, including its
limitations. If it is weak, record the finding instead of replacing the AI output
with an authored answer. No new recording or deck is declared complete by this run.
