"""ASGI entry point kept stable for uvicorn and existing imports."""

from services.api.app.factory import create_app
from services.api.app.store import store

app = create_app(store)

__all__ = ["app", "create_app"]
