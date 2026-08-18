"""ASGI entry point kept stable for uvicorn and existing imports."""

from pathlib import Path

from dotenv import load_dotenv

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app
from services.api.app.store import store, student_store


load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
settings = AppSettings.from_env()
app = (
    create_app(store, student_repository=student_store, settings=settings)
    if settings.mode == RuntimeMode.DEMO
    else create_app(
        settings=settings,
        region_crop_root=settings.region_crop_root,
        source_root=settings.source_root,
    )
)

__all__ = ["app", "create_app"]
