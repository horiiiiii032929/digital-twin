from types import SimpleNamespace

import pytest

from services.api.app import pilot, experimental
from services.api.app.config import RuntimeMode


@pytest.mark.parametrize('route', ['latest', '', 'v19-luna-luna-medium'])
def test_pilot_rejects_ambiguous_or_unsupported_route(monkeypatch, route):
    monkeypatch.setenv('APP_PILOT_TUTOR_ROUTE', route)
    with pytest.raises(ValueError, match='explicit supported route'):
        pilot.create_pilot_app()


def test_presentation_route_uses_existing_audited_factory_without_static_web(monkeypatch):
    monkeypatch.setenv('APP_PILOT_TUTOR_ROUTE', 'audited-presentation-v1')
    settings = SimpleNamespace(mode=RuntimeMode.STAGING)
    monkeypatch.setattr(pilot.AppSettings, 'from_env', lambda: settings)
    calls = []
    sentinel = object()
    def build(actual, candidate, *, serve_web):
        calls.append((actual, candidate, serve_web))
        return sentinel
    monkeypatch.setattr(experimental, 'build_experimental_app', build)
    assert pilot.create_pilot_app() is sentinel
    assert calls == [(settings, 'v19-luna-luna-medium', False)]


def test_pilot_default_uses_deterministic_rollback_composition(monkeypatch):
    monkeypatch.delenv('APP_PILOT_TUTOR_ROUTE', raising=False)
    settings = SimpleNamespace(mode=RuntimeMode.STAGING, source_root='sources', region_crop_root='crops')
    monkeypatch.setattr(pilot.AppSettings, 'from_env', lambda: settings)
    monkeypatch.setattr(pilot, 'create_app', lambda **kwargs: kwargs)
    assert pilot.create_pilot_app() == dict(settings=settings, source_root='sources', region_crop_root='crops')


def test_pilot_refuses_synthetic_header_auth_mode(monkeypatch):
    monkeypatch.setenv('APP_PILOT_TUTOR_ROUTE', 'audited-presentation-v1')
    monkeypatch.setattr(pilot.AppSettings, 'from_env', lambda: SimpleNamespace(mode=RuntimeMode.DEMO))
    with pytest.raises(ValueError, match='credential-authenticated'):
        pilot.create_pilot_app()
