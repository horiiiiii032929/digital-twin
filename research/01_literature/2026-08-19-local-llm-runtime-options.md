# Local LLM runtime options for the Digital Twin

Date: 2026-08-19

Scope: 16 GiB Apple M1 Pro development machine; factual-QA, citation, pedagogy,
and multimodal review workflows

## Outcome

Keep Ollama as the local runtime and use the exact
`qwen3.5:9b-q4_K_M` artifact as the sole local general/multimodal candidate.
Use it for inexpensive screening, public sensitivity probes, structured-output
development, and offline fallback. Do not use it as the sole judge for dataset
acceptance, citation correctness, Professor Digital Twin fidelity, or release
decisions.

Use direct DeepSeek for the currently selected paid workflows. Add OpenRouter
as an optional exact-route gateway for DeepSeek and a cross-family Mistral
reviewer. This keeps provider setup simple without creating an uncontrolled
model router.

## Runtime assessment

| Runtime | Fit on this machine | Strength | Limitation | Decision |
|---|---|---|---|---|
| Ollama | Good | Existing integration, model lifecycle, vision, JSON schema, simple local API | Less tuning/control than lower-level runtimes | Keep |
| MLX-LM | Good for experiments | Apple-Silicon-native quantization, prompt caching, memory controls | Official HTTP server is not recommended for production | Defer unless Ollama becomes the measured bottleneck |
| llama.cpp | Good for text/structured output | Mature Metal support, grammars/JSON schema, OpenAI-compatible server | More operational work; multimodal support is still evolving | Defer as a targeted fallback |
| vLLM | Poor | Strong production serving on supported accelerators | Apple Silicon support remains experimental and source-build oriented | Drop for this host |

## Local model assessment

`qwen3.5:9b-q4_K_M` is technically usable here: it is an official 6.6 GB
text-and-image artifact, leaves working memory headroom on 16 GiB, and can
produce schema-constrained output through Ollama. It is a materially stronger
local candidate than the retired 4B artifact, but installation and model-card
capabilities are not quality evidence for this project.

The next #87 instrument should therefore test it on public probes for:

- exact source-fact extraction and unsupported-claim rejection;
- citation presence and source alignment;
- schema validity and malformed-output recovery;
- table, diagram, equation, and scanned-page understanding;
- sensitivity to deliberately wrong candidate answers; and
- latency and peak memory at the frozen local context.

If those gates fail, improve the method or use the independent API reviewer;
do not add another local model merely to create model-count diversity.

## Operating profile

- One loaded model at a time and `OLLAMA_NUM_PARALLEL=1`.
- Start with an 8K context and increase only after memory/latency measurement.
- Pin the exact manifest digest, prompt, schema, seed, context, Ollama version,
  and machine identity in every named run.
- Use synthetic/public inputs for technical probes. Private course material
  requires the existing permission and provider-boundary controls.
- Keep local outputs diagnostic until calibrated against deterministic checks
  and a small human-reviewed sample.

## Primary sources

- [Ollama model library: Qwen3.5 9B Q4_K_M](https://ollama.com/library/qwen3.5:9b-q4_K_M)
- [Ollama structured outputs](https://ollama.com/blog/structured-outputs)
- [Ollama vision capability](https://docs.ollama.com/capabilities/vision)
- [MLX-LM](https://github.com/ml-explore/mlx-lm)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [vLLM Apple Silicon installation](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)
