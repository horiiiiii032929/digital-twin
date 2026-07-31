from __future__ import annotations

import pymupdf

from scripts.sample_multimodal_pdf_pages import page_diagnostic, select_pages


def test_page_diagnostic_prioritizes_visual_page() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Architecture flow from client to course store")
    page.draw_rect(pymupdf.Rect(70, 100, 240, 180))
    page.draw_line((240, 140), (360, 140))

    diagnostic = page_diagnostic(page)

    assert diagnostic["score"] > 0
    assert "diagram" in diagnostic["suggested_modalities"]
    assert diagnostic["drawing_objects"] >= 2


def test_selection_balances_courses_and_limits_source_dominance() -> None:
    diagnostics = []
    for course in ("IT5002", "CS5421"):
        for source in ("source-a", "source-b"):
            for page in range(1, 4):
                diagnostics.append(
                    {
                        "course_id": course,
                        "source_id": f"{course}-{source}",
                        "page": page,
                        "score": 20 - page,
                    }
                )

    selected = select_pages(diagnostics, per_course=3)

    assert len(selected) == 6
    assert {item["course_id"] for item in selected} == {"IT5002", "CS5421"}
    for course in ("IT5002", "CS5421"):
        course_sources = {
            item["source_id"] for item in selected if item["course_id"] == course
        }
        assert len(course_sources) == 2
