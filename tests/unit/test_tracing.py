import os

import pytest
from pydantic import SecretStr

from extracao_nf.core.config import Settings
from extracao_nf.core.tracing import configurar_tracing

_VARIAVEIS = ("LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT")


@pytest.fixture(autouse=True)
def _isolar_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in _VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)


def test_tracing_desabilitado_por_padrao() -> None:
    habilitado = configurar_tracing(Settings(environment="test", langsmith_tracing=False))

    assert habilitado is False
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert "LANGSMITH_API_KEY" not in os.environ


def test_tracing_sem_api_key_fica_desabilitado() -> None:
    settings = Settings(environment="test", langsmith_tracing=True, langsmith_api_key=None)

    assert configurar_tracing(settings) is False
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_habilitado_exporta_variaveis() -> None:
    settings = Settings(
        environment="test",
        langsmith_tracing=True,
        langsmith_api_key=SecretStr("ls-fake"),
        langsmith_project="projeto-teste",
        langsmith_endpoint="https://eu.api.smith.langchain.com",
    )

    assert configurar_tracing(settings) is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "ls-fake"
    assert os.environ["LANGSMITH_PROJECT"] == "projeto-teste"
    assert os.environ["LANGSMITH_ENDPOINT"] == "https://eu.api.smith.langchain.com"
