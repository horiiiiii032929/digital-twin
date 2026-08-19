from scripts.remediate_factual_qa_v3_ocr import build_result


def test_build_result_requires_nonempty_ocr_text() -> None:
    expected = {
        "/tmp/a.png": ("source-a", 1),
        "/tmp/b.png": ("source-b", 1),
    }
    payload = {
        "records": [
            {
                "path": "/tmp/a.png",
                "width": 100,
                "height": 200,
                "lines": [{"text": "Visible fact", "confidence": 0.9, "bbox": [0, 0, 1, 1]}],
            },
            {"path": "/tmp/b.png", "width": 100, "height": 200, "lines": []},
        ]
    }

    records, counts = build_result(expected, payload)

    assert counts == {"ocr_empty": 1, "ocr_ready": 1}
    assert records[0]["character_count"] == len("Visible fact")
