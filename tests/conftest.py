"""Fixtures compartilhadas entre testes unitários e de integração."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from extracao_nf.core.config import Settings, get_settings
from extracao_nf.main import app
from tests import fakes


@pytest.fixture(autouse=True)
def _sem_tracing_real(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # hazard: o lifespan lê o .env real; sem isso os testes enviariam traces ao LangSmith
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings_teste() -> Settings:
    """Settings de teste (upload pequeno + API key fake)."""
    return fakes.settings_teste()


@pytest.fixture
def client(settings_teste: Settings) -> Iterator[TestClient]:
    """Cliente HTTP com get_settings sobrescrito para Settings de teste."""
    app.dependency_overrides[get_settings] = lambda: settings_teste
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def pdf_valido() -> bytes:
    """Bytes mínimos de PDF válido."""
    return fakes.PDF_VALIDO


@pytest.fixture
def png_valido() -> bytes:
    """PNG 2x2 gerado pelo Pillow."""
    return fakes.bytes_imagem("PNG")


@pytest.fixture
def jpeg_valido() -> bytes:
    """JPEG 2x2 gerado pelo Pillow."""
    return fakes.bytes_imagem("JPEG")
