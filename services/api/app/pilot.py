"""Explicit AWS demo composition with a deterministic rollback route."""
from __future__ import annotations

import os

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app

PRESENTATION_CANDIDATE = "v19-luna-luna-medium"
ROUTES = frozenset({"deterministic-r1", "audited-presentation-v1"})


def create_pilot_app():
    route = os.environ.get("APP_PILOT_TUTOR_ROUTE", "deterministic-r1").strip()
    if route not in ROUTES:
        raise ValueError("APP_PILOT_TUTOR_ROUTE must name an explicit supported route")
    settings = AppSettings.from_env()
    if settings.mode != RuntimeMode.STAGING:
        raise ValueError("The AWS pilot requires credential-authenticated staging mode")
    if route == "audited-presentation-v1":
        from services.api.app.experimental import build_experimental_app
        return build_experimental_app(settings, PRESENTATION_CANDIDATE, serve_web=False)
    return create_app(settings=settings, source_root=settings.source_root, region_crop_root=settings.region_crop_root)
