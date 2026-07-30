"""Tests for the QC-amended private benchmark authoring helpers."""

from scripts.draft_cross_course_benchmark_v2 import resolve_quote


def test_resolve_quote_preserves_an_exact_source_span() -> None:
    source = "First line.\n\nSecond   line with evidence."

    resolved = resolve_quote(
        "First line. Second line with evidence.",
        source,
    )

    assert resolved == "First line.\n\nSecond   line with evidence."


def test_resolve_quote_strips_model_added_quote_marks() -> None:
    source = "The source contains a complete supporting statement."

    resolved = resolve_quote(
        '"The source contains a complete supporting statement."',
        source,
    )

    assert resolved == source


def test_resolve_quote_rejects_content_not_present_in_source() -> None:
    assert resolve_quote("An invented statement.", "Unrelated source.") is None
