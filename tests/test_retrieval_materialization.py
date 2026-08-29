from pathlib import Path

import pytest

from src.digital_twin.evaluation.retrieval_materialization import (
    RetrievalMaterializationError,
    materialize_retrieval_indexes,
)


def test_r1_materialization_rejects_missing_pinned_model_before_loading():
    with pytest.raises(RetrievalMaterializationError, match="snapshot"):
        materialize_retrieval_indexes(
            chunks_by_course={},
            profile={
                "components": [
                    {
                        "component": "retriever",
                        "implementation": {
                            "configuration": {"embedding_revision": "revision"}
                        },
                    },
                    {
                        "component": "chunker",
                        "implementation": {
                            "implementation_id": "chunker",
                            "version": "v1",
                        },
                    },
                ]
            },
            model_root=Path("/definitely/missing"),
            output_root=Path("/unused"),
        )
