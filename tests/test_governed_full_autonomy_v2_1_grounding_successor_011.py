from scripts import build_governed_full_autonomy_v2_1_grounding_successor_011 as builder
from src.digital_twin.grounding.semantic_evidence_atoms import ATOM_VERSION


def test_successor_is_fresh_byte_stable_and_source_contract_aligned() -> None:
    result = builder.build_byte_stable_packages()
    packages = result["packages"]
    assert result["byte_stable"] is True
    assert result["case_count"] == 500
    assert result["cluster_count"] == 100
    assert result["source_range_disjoint_from_prior_development_and_sealed_010"]
    assert packages["source"]["semantic_atom_version"] == ATOM_VERSION
    assert packages["source"]["canonical_answer_contract"] == "semantic_atom_claim"

    chunks = {
        row["region_id"]: row for row in packages["source"]["chunks"]
    }
    for row in packages["gold"]["gold"]:
        if row["expected_action"] != "answer":
            assert row["claims"] == []
            assert row["boundary_reason"]
            continue
        expected = []
        for claim in row["claims"]:
            assert len(claim["evidence_refs"]) == 1
            chunk = chunks[claim["evidence_refs"][0]["region_id"]]
            assert chunk["metadata"]["semantic_atom_version"] == ATOM_VERSION
            assert claim["answer_span"] == chunk["metadata"]["semantic_atom_claim"]
            expected.append(claim["answer_span"])
        assert row["canonical_answer"] == " ".join(expected)


def test_successor_has_exact_course_and_modality_allocation() -> None:
    result = builder.build_packages()
    clusters = result["packages"]["source"]["clusters"]
    observed: dict[tuple[str, str], int] = {}
    for row in clusters:
        key = (row["course_id"], row["source_modality"])
        observed[key] = observed.get(key, 0) + 1
    expected = {
        (course_id, modality): count
        for course_id, allocation in builder.TARGET_ALLOCATION.items()
        for modality, count in allocation.items()
    }
    assert observed == expected
