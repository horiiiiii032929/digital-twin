"""Qualify the exact local Qwen artifact as a diagnostic factual-QA reviewer."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import math
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from src.digital_twin.model_policy import require_registered_current_model


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "local_qwen_reviewer_sensitivity_v2_development_002.json"
)
DEFAULT_OUTPUT = ROOT / (
    "reports/generated/"
    "local-qwen-reviewer-sensitivity-v2-development-002.json"
)
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
SEMANTIC_REVIEW_FIELDS = (
    "response_action_correct",
    "response_content_correct",
    "evidence_complete",
    "course_boundary_respected",
)


class ReviewerSensitivityError(RuntimeError):
    """Raised when the frozen reviewer qualification cannot be completed safely."""


@dataclass(frozen=True)
class ReviewCall:
    value: dict[str, Any]
    provider_model: str
    provider_digest: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class ReviewTransport(Protocol):
    identity: dict[str, Any]

    async def review(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        image_bytes: list[bytes],
    ) -> ReviewCall: ...


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewerSensitivityError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise ReviewerSensitivityError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise ReviewerSensitivityError(f"path escapes repository: {value}") from error
    return path


def validate_assets(instrument_path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = load_json(instrument_path)
    if instrument.get("status") != "frozen-pending-execution":
        raise ReviewerSensitivityError("instrument is not frozen pending execution")
    if instrument.get("method_version") != (
        "hybrid-deterministic-lineage-derived-triage-v2"
    ):
        raise ReviewerSensitivityError("instrument does not use the supported method")

    dataset_binding = instrument.get("dataset", {})
    dataset_path = _root_path(str(dataset_binding.get("path", "")))
    if sha256_file(dataset_path) != dataset_binding.get("sha256"):
        raise ReviewerSensitivityError("probe dataset hash does not match instrument")
    dataset = load_json(dataset_path)
    if dataset.get("status") != "frozen":
        raise ReviewerSensitivityError("probe dataset is not frozen")
    if dataset.get("dataset_id") != dataset_binding.get("dataset_id"):
        raise ReviewerSensitivityError("probe dataset identity does not match instrument")
    if dataset.get("content_class") != "synthetic-public":
        raise ReviewerSensitivityError("only synthetic-public probes are authorized")

    corpus_binding = dataset.get("source_corpus", {})
    corpus_path = _root_path(str(corpus_binding.get("path", "")))
    if sha256_file(corpus_path) != corpus_binding.get("sha256"):
        raise ReviewerSensitivityError("source corpus hash does not match dataset")
    corpus = load_json(corpus_path)
    source_units = corpus.get("source_units")
    blueprints = corpus.get("case_blueprints")
    if not isinstance(source_units, list) or not isinstance(blueprints, list):
        raise ReviewerSensitivityError("source corpus collections are invalid")
    source_map = {item.get("source_unit_id"): item for item in source_units}
    blueprint_map = {item.get("blueprint_id"): item for item in blueprints}
    if len(source_map) != len(source_units) or None in source_map:
        raise ReviewerSensitivityError("source unit identifiers are not unique")
    if len(blueprint_map) != len(blueprints) or None in blueprint_map:
        raise ReviewerSensitivityError("blueprint identifiers are not unique")

    pairs = dataset.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ReviewerSensitivityError("probe pairs are missing")
    pair_ids = [item.get("pair_id") for item in pairs]
    if len(set(pair_ids)) != len(pair_ids) or None in pair_ids:
        raise ReviewerSensitivityError("pair identifiers are not unique")
    if len(pairs) != dataset_binding.get("pair_count"):
        raise ReviewerSensitivityError("pair count does not match instrument")
    if len(pairs) * 2 != dataset_binding.get("probe_count"):
        raise ReviewerSensitivityError("probe count does not match instrument")
    if len(pairs) * 2 > instrument["execution"]["call_limit"]:
        raise ReviewerSensitivityError("probe count exceeds frozen call limit")

    valid_failures = set(instrument.get("failure_labels", []))
    if "none" not in valid_failures:
        raise ReviewerSensitivityError("failure labels must include none")
    visual_assets: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        blueprint_id = pair.get("blueprint_id")
        if blueprint_id not in blueprint_map:
            raise ReviewerSensitivityError(f"unknown blueprint: {blueprint_id}")
        source_ids = pair.get("source_unit_ids")
        if not isinstance(source_ids, list) or any(
            item not in source_map for item in source_ids
        ):
            raise ReviewerSensitivityError(f"invalid sources for pair: {pair['pair_id']}")
        for condition in ("clean", "defect"):
            candidate = pair.get(condition)
            _validate_candidate(candidate, pair_id=pair["pair_id"], condition=condition)
        if pair["clean"].get("primary_failure") is not None:
            raise ReviewerSensitivityError("clean probes cannot define a failure")
        failure = pair["defect"].get("primary_failure")
        if failure not in valid_failures - {"none"}:
            raise ReviewerSensitivityError(
                f"invalid defect label for pair: {pair['pair_id']}"
            )
        if pair.get("source_mode") == "approved-image":
            if len(source_ids) != 1:
                raise ReviewerSensitivityError("visual probes require one image source")
            source = source_map[source_ids[0]]
            asset_path = _root_path(str(source.get("path", "")))
            if sha256_file(asset_path) != source.get("sha256"):
                raise ReviewerSensitivityError(f"visual asset hash mismatch: {asset_path}")
            visual_assets[source_ids[0]] = {
                "path": asset_path,
                "sha256": source["sha256"],
            }

    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "dataset": dataset,
        "dataset_path": dataset_path,
        "corpus": corpus,
        "corpus_path": corpus_path,
        "source_map": source_map,
        "blueprint_map": blueprint_map,
        "visual_assets": visual_assets,
        "source_integrity_rate": 1.0,
    }


def _validate_candidate(
    candidate: Any, *, pair_id: str, condition: str
) -> None:
    if not isinstance(candidate, dict):
        raise ReviewerSensitivityError(f"missing {condition} candidate: {pair_id}")
    for field in ("question", "answer", "action"):
        if not isinstance(candidate.get(field), str) or not candidate[field].strip():
            raise ReviewerSensitivityError(
                f"invalid {condition}.{field} for pair: {pair_id}"
            )
    citations = candidate.get("citation_source_ids")
    if not isinstance(citations, list) or any(
        not isinstance(item, str) for item in citations
    ):
        raise ReviewerSensitivityError(
            f"invalid {condition} citations for pair: {pair_id}"
        )


def _assert_local_chat_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ReviewerSensitivityError("Ollama must use a loopback HTTP URL")
    if parsed.path.rstrip("/") != "/api/chat":
        raise ReviewerSensitivityError("Ollama reviewer must use /api/chat")
    return url


class OllamaMultimodalJsonTransport:
    """Exact-identity Ollama transport with JSON-schema and image support."""

    def __init__(self, binding: dict[str, Any], *, url: str) -> None:
        self.binding = binding
        self.model = require_registered_current_model(binding["model"])
        self.url = _assert_local_chat_url(url)
        self.base_url = self.url.removesuffix("/api/chat")
        self.identity = self._inspect_identity()

    def _request_json(
        self,
        *,
        url: str,
        body: dict[str, Any] | None = None,
        timeout: float = 15,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="GET" if body is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                value = json.load(response)
        except (OSError, json.JSONDecodeError) as error:
            raise ReviewerSensitivityError(f"Ollama request failed: {url}") from error
        if not isinstance(value, dict):
            raise ReviewerSensitivityError("Ollama response root must be an object")
        return value

    def _inspect_identity(self) -> dict[str, Any]:
        tags = self._request_json(url=f"{self.base_url}/api/tags")
        matches = [
            item
            for item in tags.get("models", [])
            if item.get("name") == self.model
        ]
        if len(matches) != 1:
            raise ReviewerSensitivityError(
                f"exact local model is not installed once: {self.model}"
            )
        installed = matches[0]
        if installed.get("digest") != self.binding["model_digest"]:
            raise ReviewerSensitivityError("installed model digest does not match instrument")
        show = self._request_json(
            url=f"{self.base_url}/api/show", body={"model": self.model}
        )
        capabilities = show.get("capabilities", [])
        missing = set(self.binding["required_capabilities"]) - set(capabilities)
        if missing:
            raise ReviewerSensitivityError(
                f"installed model lacks required capabilities: {sorted(missing)}"
            )
        version = self._request_json(url=f"{self.base_url}/api/version")
        return {
            "model": self.model,
            "digest": installed["digest"],
            "size_bytes": installed.get("size"),
            "details": installed.get("details", {}),
            "capabilities": capabilities,
            "ollama_version": version.get("version"),
        }

    async def review(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        image_bytes: list[bytes],
    ) -> ReviewCall:
        return await asyncio.to_thread(
            self._review_sync,
            prompt=prompt,
            schema=schema,
            image_bytes=image_bytes,
        )

    def _review_sync(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        image_bytes: list[bytes],
    ) -> ReviewCall:
        user_message: dict[str, Any] = {"role": "user", "content": prompt}
        if image_bytes:
            user_message["images"] = [
                base64.b64encode(value).decode("ascii") for value in image_bytes
            ]
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _system_prompt()},
                user_message,
            ],
            "stream": False,
            "think": False,
            "format": schema,
            "options": {
                "temperature": self.binding["temperature"],
                "seed": self.binding["seed"],
                "num_predict": self.binding["max_output_tokens"],
            },
            "keep_alive": "5m",
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request, timeout=self.binding["timeout_seconds"]
            ) as response:
                envelope = json.load(response)
        except (OSError, json.JSONDecodeError) as error:
            raise ReviewerSensitivityError("Ollama review request failed") from error
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            value = json.loads(envelope["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ReviewerSensitivityError("Ollama returned malformed review JSON") from error
        if not isinstance(value, dict):
            raise ReviewerSensitivityError("Ollama review JSON root must be an object")
        return ReviewCall(
            value=value,
            provider_model=str(envelope.get("model", self.model)),
            provider_digest=self.identity["digest"],
            input_tokens=int(envelope.get("prompt_eval_count", 0) or 0),
            output_tokens=int(envelope.get("eval_count", 0) or 0),
            latency_ms=elapsed_ms,
        )


def review_schema() -> dict[str, Any]:
    properties: dict[str, Any] = {
        "evidence_observation": {"type": "string", "minLength": 1},
        "rationale": {"type": "string", "minLength": 1},
    }
    properties.update(
        {field: {"type": "boolean"} for field in SEMANTIC_REVIEW_FIELDS}
    )
    required = [*SEMANTIC_REVIEW_FIELDS, "evidence_observation", "rationale"]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def validate_semantic_review(review: dict[str, Any]) -> dict[str, Any]:
    if any(not isinstance(review.get(field), bool) for field in SEMANTIC_REVIEW_FIELDS):
        raise ReviewerSensitivityError("semantic review boolean fields are invalid")
    for field in ("evidence_observation", "rationale"):
        if not isinstance(review.get(field), str) or not review[field].strip():
            raise ReviewerSensitivityError(f"review {field} is missing")
    return dict(review)


def deterministic_citation_lineage(
    pair: dict[str, Any], candidate: dict[str, Any]
) -> bool:
    cited = set(candidate["citation_source_ids"])
    if pair["source_mode"] in {"approved-text", "approved-image"}:
        allowed = set(pair["source_unit_ids"])
    else:
        allowed = set()
    if candidate["action"] == "answer" and allowed:
        return cited == allowed
    return not cited


def derive_review(
    semantic: dict[str, Any],
    *,
    pair: dict[str, Any],
    candidate: dict[str, Any],
    blueprint: dict[str, Any],
) -> dict[str, Any]:
    citation_correct = deterministic_citation_lineage(pair, candidate)
    accepted = all(semantic[field] for field in SEMANTIC_REVIEW_FIELDS) and (
        citation_correct
    )
    primary_failure = _derive_primary_failure(
        semantic,
        pair=pair,
        blueprint=blueprint,
        citation_correct=citation_correct,
        accepted=accepted,
    )
    return {
        **semantic,
        "citation_lineage_correct": citation_correct,
        "verdict": "accept" if accepted else "reject",
        "primary_failure": primary_failure,
        "contract_mismatch": False,
        "derivation": "hybrid-deterministic-lineage-derived-triage-v2",
    }


def _derive_primary_failure(
    semantic: dict[str, Any],
    *,
    pair: dict[str, Any],
    blueprint: dict[str, Any],
    citation_correct: bool,
    accepted: bool,
) -> str:
    if accepted:
        return "none"
    if pair["source_mode"] == "disallowed-distractor":
        return "cross_course_leakage"
    if blueprint["expected_action"] != "answer" and not semantic[
        "response_action_correct"
    ]:
        if pair["source_mode"] == "no-evidence":
            return "unsupported_no_evidence_answer"
        return "wrong_boundary_action"
    if pair["source_mode"] == "no-evidence":
        return "unsupported_no_evidence_answer"
    if pair["source_mode"] == "approved-image" and not semantic[
        "response_content_correct"
    ]:
        return "visual_evidence_mismatch"
    if len(pair["source_unit_ids"]) > 1 and (
        not semantic["evidence_complete"] or not citation_correct
    ):
        return "incomplete_answer"
    if not semantic["response_content_correct"]:
        return "wrong_factual_answer"
    if not citation_correct or not semantic["evidence_complete"]:
        return "incomplete_answer"
    return "wrong_factual_answer"


def _system_prompt() -> str:
    return (
        "You are a strict but fair semantic reviewer of one synthetic factual-QA "
        "case. Use only approved evidence and any attached image. Treat a source "
        "marked disallowed-distractor as unavailable to the target course. For "
        "no-evidence, abstention is correct. For ambiguity, targeted clarification "
        "is correct. Inspect attached images directly and bind each image to its "
        "explicit source ID. Citation membership is checked separately in code; "
        "do not reject an answer because visual source text is intentionally "
        "withheld. Judge only the requested semantic dimensions. Return JSON only."
    )


def _prompt(
    *,
    pair: dict[str, Any],
    candidate: dict[str, Any],
    blueprint: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
) -> str:
    sources = []
    for image_index, source_id in enumerate(pair["source_unit_ids"], start=1):
        source = source_map[source_id]
        rendered = {
            "source_unit_id": source_id,
            "course_id": source["course_id"],
            "modality": source["modality"],
            "locator": source["locator"],
            "authorization": (
                "disallowed-distractor"
                if pair["source_mode"] == "disallowed-distractor"
                else "approved-target-course"
            ),
        }
        if pair["source_mode"] in {
            "approved-text",
            "disallowed-distractor",
        }:
            rendered["source_text"] = source["evidence_text"]
        else:
            rendered["visual_attachment_index"] = image_index
            rendered["visual_instruction"] = (
                "This source ID is approved and is the attached image. Inspect it "
                "directly; its textual source truth is intentionally withheld."
            )
        sources.append(rendered)
    approved_citation_ids = (
        pair["source_unit_ids"]
        if pair["source_mode"] in {"approved-text", "approved-image"}
        else []
    )
    payload = {
        "review_context": {
            "target_course_id": blueprint["course_id"],
            "expected_action": blueprint["expected_action"],
            "question_intent": blueprint["question_intent"],
            "source_mode": pair["source_mode"],
            "sources": sources,
            "approved_citation_source_ids": approved_citation_ids,
            "citation_lineage_status": (
                "checked separately by deterministic exact-ID code; do not judge it"
            ),
        },
        "candidate": candidate,
        "semantic_dimensions_only": {
            "response_action_correct": "candidate action matches expected_action",
            "response_content_correct": "candidate response correctly addresses the question",
            "evidence_complete": "all factual content is supported and every requested answer part is present",
            "course_boundary_respected": "only target-course approved evidence is used",
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _render_svg(path: Path) -> bytes:
    try:
        completed = subprocess.run(
            ["rsvg-convert", "--format=png", str(path)],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReviewerSensitivityError(f"cannot render SVG asset: {path}") from error
    if not completed.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ReviewerSensitivityError(f"rendered asset is not PNG: {path}")
    return completed.stdout


def _image_bytes(pair: dict[str, Any], source_map: dict[str, dict[str, Any]]) -> list[bytes]:
    if pair["source_mode"] != "approved-image":
        return []
    source = source_map[pair["source_unit_ids"][0]]
    path = _root_path(source["path"])
    if path.suffix.casefold() == ".svg":
        return [_render_svg(path)]
    return [path.read_bytes()]


async def execute(
    assets: dict[str, Any], transport: ReviewTransport
) -> dict[str, Any]:
    instrument = assets["instrument"]
    dataset = assets["dataset"]
    schema = review_schema()
    results = []
    memory_samples = [_ollama_rss_mib()]
    call_count = 0
    for pair in dataset["pairs"]:
        blueprint = assets["blueprint_map"][pair["blueprint_id"]]
        images = _image_bytes(pair, assets["source_map"])
        for condition in ("clean", "defect"):
            if call_count >= instrument["execution"]["call_limit"]:
                raise ReviewerSensitivityError("frozen call limit reached")
            call_count += 1
            candidate = pair[condition]
            expected_verdict = "accept" if condition == "clean" else "reject"
            expected_failure = (
                "none" if condition == "clean" else candidate["primary_failure"]
            )
            error: str | None = None
            call: ReviewCall | None = None
            review: dict[str, Any] | None = None
            try:
                call = await transport.review(
                    prompt=_prompt(
                        pair=pair,
                        candidate={
                            key: value
                            for key, value in candidate.items()
                            if key != "primary_failure"
                        },
                        blueprint=blueprint,
                        source_map=assets["source_map"],
                    ),
                    schema=schema,
                    image_bytes=images,
                )
                semantic_review = validate_semantic_review(call.value)
                review = derive_review(
                    semantic_review,
                    pair=pair,
                    candidate=candidate,
                    blueprint=blueprint,
                )
            except ReviewerSensitivityError as exc:
                error = str(exc)
            memory_samples.append(_ollama_rss_mib())
            results.append(
                {
                    "probe_id": f"{pair['pair_id']}--{condition}",
                    "pair_id": pair["pair_id"],
                    "blueprint_id": pair["blueprint_id"],
                    "condition": condition,
                    "source_mode": pair["source_mode"],
                    "modality": "visual" if images else "text-or-boundary",
                    "expected_verdict": expected_verdict,
                    "expected_primary_failure": expected_failure,
                    "candidate": candidate,
                    "review": review,
                    "error": error,
                    "call": None if call is None else {
                        "provider_model": call.provider_model,
                        "provider_digest": call.provider_digest,
                        "input_tokens": call.input_tokens,
                        "output_tokens": call.output_tokens,
                        "latency_ms": call.latency_ms,
                    },
                }
            )
    analysis = analyze_results(instrument, results, transport.identity)
    return {
        "schema_version": 1,
        "run_id": instrument["instrument_id"],
        "status": "complete",
        "instrument_path": str(assets["instrument_path"].relative_to(ROOT)),
        "instrument_sha256": sha256_file(assets["instrument_path"]),
        "dataset_path": str(assets["dataset_path"].relative_to(ROOT)),
        "dataset_sha256": sha256_file(assets["dataset_path"]),
        "source_corpus_path": str(assets["corpus_path"].relative_to(ROOT)),
        "source_corpus_sha256": sha256_file(assets["corpus_path"]),
        "content_class": dataset["content_class"],
        "code_revision": _git_output("rev-parse", "HEAD"),
        "worktree_dirty_at_start": bool(_git_output("status", "--porcelain")),
        "model_identity": transport.identity,
        "external_provider_calls": 0,
        "private_data_calls": 0,
        "approximate_cost_usd": 0.0,
        "memory": {
            "ollama_model_process_rss_samples_mib": memory_samples,
            "ollama_model_process_peak_rss_mib": max(memory_samples),
            "sampler_process_names": ["ollama runner", "llama-server"],
        },
        "metrics": analysis["metrics"],
        "gates": analysis["gates"],
        "all_gates_passed": analysis["all_gates_passed"],
        "decision": "go-deeper-diagnostic-only" if analysis["all_gates_passed"] else "refine",
        "results": results,
    }


def analyze_results(
    instrument: dict[str, Any],
    results: list[dict[str, Any]],
    identity: dict[str, Any],
) -> dict[str, Any]:
    completed = [item for item in results if item["review"] is not None]
    clean = [item for item in results if item["condition"] == "clean"]
    defects = [item for item in results if item["condition"] == "defect"]
    visual_clean = [
        item for item in clean if item["source_mode"] == "approved-image"
    ]
    visual_defects = [
        item for item in defects if item["source_mode"] == "approved-image"
    ]
    accepted_clean = [
        item for item in clean if item["review"] and item["review"]["verdict"] == "accept"
    ]
    rejected_defects = [
        item for item in defects if item["review"] and item["review"]["verdict"] == "reject"
    ]
    accepted_visual_clean = [
        item for item in visual_clean if item["review"] and item["review"]["verdict"] == "accept"
    ]
    rejected_visual_defects = [
        item for item in visual_defects if item["review"] and item["review"]["verdict"] == "reject"
    ]
    correctly_classified = [
        item
        for item in defects
        if item["review"]
        and item["review"]["primary_failure"] == item["expected_primary_failure"]
    ]
    latencies = [item["call"]["latency_ms"] for item in completed]
    metrics = {
        "probe_count": len(results),
        "pair_count": len(results) // 2,
        "structured_completion_rate": _rate(len(completed), len(results)),
        "critical_defect_recall": _rate(len(rejected_defects), len(defects)),
        "clean_control_acceptance_rate": _rate(len(accepted_clean), len(clean)),
        "visual_defect_recall": _rate(len(rejected_visual_defects), len(visual_defects)),
        "visual_clean_accept_count": len(accepted_visual_clean),
        "visual_clean_count": len(visual_clean),
        "primary_failure_accuracy": _rate(len(correctly_classified), len(defects)),
        "contract_mismatch_count": sum(
            bool(item["review"] and item["review"].get("contract_mismatch", False))
            for item in results
        ),
        "input_tokens": sum(item["call"]["input_tokens"] for item in completed),
        "output_tokens": sum(item["call"]["output_tokens"] for item in completed),
        "latency_ms_total": sum(latencies),
        "latency_ms_p50": _percentile(latencies, 0.5),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "external_provider_calls": 0,
        "private_data_calls": 0,
        "approximate_cost_usd": 0.0,
    }
    expected = instrument["candidate"]
    required_capabilities = set(expected["required_capabilities"])
    gates = {
        "source_integrity": True,
        "model_identity_exact": (
            identity.get("model") == expected["model"]
            and identity.get("digest") == expected["model_digest"]
        ),
        "vision_capability": required_capabilities.issubset(
            set(identity.get("capabilities", []))
        ),
        "structured_completion_rate": metrics["structured_completion_rate"]
        >= instrument["quality_gates"]["structured_completion_rate_min"],
        "critical_defect_recall": metrics["critical_defect_recall"]
        >= instrument["quality_gates"]["critical_defect_recall_min"],
        "clean_control_acceptance_rate": metrics["clean_control_acceptance_rate"]
        >= instrument["quality_gates"]["clean_control_acceptance_rate_min"],
        "visual_defect_recall": metrics["visual_defect_recall"]
        >= instrument["quality_gates"]["visual_defect_recall_min"],
        "visual_clean_accept_count": metrics["visual_clean_accept_count"]
        >= instrument["quality_gates"]["visual_clean_accept_count_min"],
        "primary_failure_accuracy": metrics["primary_failure_accuracy"]
        >= instrument["quality_gates"]["primary_failure_accuracy_min"],
        "external_provider_calls": metrics["external_provider_calls"]
        <= instrument["quality_gates"]["external_provider_calls_max"],
        "private_data_calls": metrics["private_data_calls"]
        <= instrument["quality_gates"]["private_data_calls_max"],
        "cost": metrics["approximate_cost_usd"]
        <= instrument["quality_gates"]["cost_usd_max"],
    }
    return {"metrics": metrics, "gates": gates, "all_gates_passed": all(gates.values())}


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _ollama_rss_mib() -> float:
    try:
        output = subprocess.run(
            ["ps", "-axo", "rss=,command="],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return 0.0
    total_kib = 0
    for line in output.splitlines():
        if "ollama runner" not in line and "llama-server" not in line:
            continue
        fields = line.strip().split(maxsplit=1)
        if fields and fields[0].isdigit():
            total_kib += int(fields[0])
    return total_kib / 1024


def _git_output(*arguments: str) -> str:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _write_output(path: Path, payload: dict[str, Any]) -> None:
    path = path.resolve()
    if path.exists():
        raise ReviewerSensitivityError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    enriched = dict(payload)
    enriched["completed_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(enriched, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    assets = validate_assets(arguments.instrument.resolve())
    summary = {
        "instrument_id": assets["instrument"]["instrument_id"],
        "pair_count": len(assets["dataset"]["pairs"]),
        "probe_count": len(assets["dataset"]["pairs"]) * 2,
        "visual_pair_count": sum(
            pair["source_mode"] == "approved-image"
            for pair in assets["dataset"]["pairs"]
        ),
        "source_integrity_rate": assets["source_integrity_rate"],
        "execution_authorized": arguments.execute,
    }
    if not arguments.execute:
        print(json.dumps(summary, indent=2))
        return 0
    transport = OllamaMultimodalJsonTransport(
        assets["instrument"]["candidate"], url=arguments.ollama_url
    )
    payload = asyncio.run(execute(assets, transport))
    _write_output(arguments.output, payload)
    print(
        json.dumps(
            {
                **summary,
                "all_gates_passed": payload["all_gates_passed"],
                "decision": payload["decision"],
                "output": str(arguments.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
