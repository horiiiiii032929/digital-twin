from __future__ import annotations

import pytest

from scripts.build_multimodal_private_draft import build_dataset, review_html


def sample_queue() -> dict:
    return {
        "records": [
            {
                "candidate_id": "mm-page-0123456789abcdef",
                "render_path": "tests/fixtures/multimodal/diagram_flow.svg",
                "render_sha256": "0" * 64,
                "page_text": "Synthetic surrounding text.",
                "source_id": "vault-synthetic",
                "course_id": "IT5002",
                "document_sha256": "1" * 64,
                "page": 3,
            }
        ]
    }


def authoring() -> dict:
    return {
        "cases": [
            {
                "case_id": "mmr1-synthetic-flow-01",
                "candidate_id": "mm-page-0123456789abcdef",
                "slice": "visual_answerable",
                "modality": "diagram",
                "query": "Which component appears in the synthetic flow?",
                "expected_action": "retrieve",
                "required_claims": ["A synthetic component appears."],
                "visual_dependency": "visual_semantics_required",
                "region": {
                    "region_id": "region-synthetic-flow",
                    "bbox": [0.1, 0.1, 0.8, 0.8],
                    "kind": "diagram",
                },
            }
        ]
    }


def test_builder_binds_render_to_private_source_provenance() -> None:
    dataset = build_dataset(sample_queue(), authoring())

    asset = dataset["source_assets"][0]
    assert dataset["dataset_kind"] == "private_course"
    assert asset["source_artifact_id"] == "vault-synthetic"
    assert asset["source_document_sha256"] == "1" * 64
    assert asset["page"] == 3
    assert dataset["cases"][0]["gold_region_ids"] == ["region-synthetic-flow"]
    assert dataset["cases"][0]["review"]["researcher_verified"] is False


def test_builder_rejects_unknown_sample_candidate() -> None:
    invalid = authoring()
    invalid["cases"][0]["candidate_id"] = "mm-page-fedcba9876543210"

    with pytest.raises(ValueError, match="unknown candidate IDs"):
        build_dataset(sample_queue(), invalid)


def test_review_html_escapes_case_content(tmp_path) -> None:
    dataset = build_dataset(sample_queue(), authoring())
    dataset["cases"][0]["query"] = "Is x <script>alert(1)</script>?"

    rendered = review_html(dataset, tmp_path / "review.html")

    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "Export confirmations" in rendered
    assert "data-check=\"region\"" in rendered
    assert "policy-confirm" in rendered
    assert "cases confirmed" in rendered
