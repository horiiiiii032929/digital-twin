"""ASGI entry point kept stable for uvicorn and existing imports."""

from pathlib import Path

from dotenv import load_dotenv

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app


load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
settings = AppSettings.from_env()
if settings.mode == RuntimeMode.DEMO:
    from services.api.app.store import store
    from src.digital_twin.student import seed_synthetic_student_workflow

    app = create_app(store, settings=settings)
    seed_synthetic_student_workflow(app.state.student_repository)
else:
    app = create_app(
        settings=settings,
        region_crop_root=settings.region_crop_root,
        source_root=settings.source_root,
    )

__all__ = ["app", "create_app"]
