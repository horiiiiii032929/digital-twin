"""Run a deterministic, synthetic verification of local ingestion and chunking."""

import json
import tempfile
from pathlib import Path

from src.digital_twin.grounding import (
    HeadingParagraphChunker,
    LocalDocumentParser,
    LocalFigureStore,
)
from scripts.synthetic_course_corpus import (
    synthetic_source_and_approval,
    synthetic_source_paths,
)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="digital-twin-ingestion-") as temp:
        temp_root = Path(temp)
        paths = synthetic_source_paths(temp_root)

        parser = LocalDocumentParser(LocalFigureStore(temp_root / "figures"))
        chunker = HeadingParagraphChunker(max_chars=480, overlap_chars=80)
        summaries = []
        for path in paths:
            source, approval = synthetic_source_and_approval(path)
            first = parser.parse(path, source, approval)
            second = parser.parse(path, source, approval)
            first_chunks = chunker.chunk(first.document)
            second_chunks = chunker.chunk(second.document)
            if first.document != second.document:
                raise RuntimeError(f"non-deterministic parsing: {path.name}")
            if [figure.id for figure in first.figures] != [
                figure.id for figure in second.figures
            ]:
                raise RuntimeError(f"non-deterministic figures: {path.name}")
            if [chunk.id for chunk in first_chunks] != [
                chunk.id for chunk in second_chunks
            ]:
                raise RuntimeError(f"non-deterministic chunking: {path.name}")
            provenance_preserved = all(
                chunk.source_artifact_id == source.id
                and chunk.source_version == source.version
                and chunk.retrieval_allowed
                for chunk in first_chunks
            )
            if not provenance_preserved:
                raise RuntimeError(f"provenance was not preserved: {path.name}")
            summaries.append(
                {
                    "source": path.name,
                    "document_id": first.document.id,
                    "segments": len(first.document.segments),
                    "chunks": len(first_chunks),
                    "figures": len(first.figures),
                    "provenance_preserved": provenance_preserved,
                }
            )

        print(
            json.dumps(
                {
                    "status": "passed",
                    "documents": len(summaries),
                    "chunks": sum(item["chunks"] for item in summaries),
                    "figures": sum(item["figures"] for item in summaries),
                    "results": summaries,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
