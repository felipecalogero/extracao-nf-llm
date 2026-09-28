"""Testes de integração do endpoint POST /extrair-nf."""

from collections.abc import Iterator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr

from extracao_nf.core.config import Settings, get_settings
from extracao_nf.core.exceptions import (
    ArquivoIlegivelError,
    PermanentError,
    TransientError,
)
from extracao_nf.domain.models import Emitente, ExtracaoResponse, NotaFiscalExtraida, Valores
from extracao_nf.main import app

PDF_VALIDO = b"%PDF-1.4\n% conteudo minimo de teste"


def _imagem_bytes(formato: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(buffer, format=formato)
    return buffer.getvalue()


PNG_VALIDO = _imagem_bytes("PNG")
JPEG_VALIDO = _imagem_bytes("JPEG")


def _resposta_ok() -> ExtracaoResponse:
    return ExtracaoResponse(
        nota_fiscal=NotaFiscalExtraida(
            emitente=Emitente(razao_social="ACME"),
            valores=Valores(valor_total_nota=10.0),
        ),
        inconsistencias=[],
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente HTTP com limite de upload reduzido e API key fake."""
    settings = Settings(
        upload_max_bytes=1024,
        google_api_key=SecretStr("fake"),
        environment="test",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("nome", "conteudo", "content_type"),
    [
        ("nota.pdf", PDF_VALIDO, "application/pdf"),
        ("nota.png", PNG_VALIDO, "image/png"),
        ("nota.jpg", JPEG_VALIDO, "image/jpeg"),
    ],
)
def test_extrair_nf_aceita_arquivo_valido(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    nome: str,
    conteudo: bytes,
    content_type: str,
) -> None:
    """PDF, PNG e JPEG válidos devem retornar 200 com ExtracaoResponse."""
    monkeypatch.setattr(
        "extracao_nf.api.routes.extrair.extrair_nota_fiscal",
        lambda **_kwargs: _resposta_ok(),
    )

    response = client.post(
        "/extrair-nf",
        files={"arquivo": (nome, conteudo, content_type)},
    )

    assert response.status_code == 200
    body = response.json()
    assert "nota_fiscal" in body
    assert "inconsistencias" in body
    assert body["nota_fiscal"]["emitente"]["razao_social"] == "ACME"
    assert body["nota_fiscal"]["valores"]["valor_total_nota"] == 10.0
    assert body["inconsistencias"] == []


def test_extrair_nf_rejeita_tipo_nao_suportado(client: TestClient) -> None:
    """Tipo MIME fora da lista permitida deve retornar 415."""
    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("documento.txt", b"conteudo", "text/plain")},
    )

    assert response.status_code == 415
    assert "não suportado" in response.json()["detail"].lower()


def test_extrair_nf_rejeita_arquivo_vazio(client: TestClient) -> None:
    """Arquivo sem conteúdo deve retornar 400."""
    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("vazio.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo vazio."


def test_extrair_nf_rejeita_arquivo_corrompido(client: TestClient) -> None:
    """PDF com content-type correto mas sem assinatura %PDF deve retornar 400."""
    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("corrompido.pdf", b"nao-e-um-pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert "corrompido" in response.json()["detail"].lower()


def test_extrair_nf_rejeita_arquivo_acima_do_limite(client: TestClient) -> None:
    """Arquivo maior que upload_max_bytes deve retornar 400."""
    conteudo_grande = b"%PDF-1.4\n" + b"x" * 2000
    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("grande.pdf", conteudo_grande, "application/pdf")},
    )

    assert response.status_code == 400
    assert "tamanho máximo" in response.json()["detail"].lower()


def test_extrair_nf_arquivo_ilegivel_retorna_422(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ArquivoIlegivelError do domínio deve mapear para 422."""

    def _falha(**_kwargs: object) -> ExtracaoResponse:
        raise ArquivoIlegivelError("Imagem ilegível.")

    monkeypatch.setattr(
        "extracao_nf.api.routes.extrair.extrair_nota_fiscal",
        _falha,
    )

    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("nota.pdf", PDF_VALIDO, "application/pdf")},
    )

    assert response.status_code == 422
    assert "ilegível" in response.json()["detail"].lower()


def test_extrair_nf_erro_permanente_retorna_502(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PermanentError do LLM deve mapear para 502."""

    def _falha(**_kwargs: object) -> ExtracaoResponse:
        raise PermanentError("Falha permanente do LLM.")

    monkeypatch.setattr(
        "extracao_nf.api.routes.extrair.extrair_nota_fiscal",
        _falha,
    )

    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("nota.pdf", PDF_VALIDO, "application/pdf")},
    )

    assert response.status_code == 502
    assert "permanente" in response.json()["detail"].lower()


def test_extrair_nf_timeout_retorna_504(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TransientError com timeout na mensagem deve mapear para 504."""

    def _falha(**_kwargs: object) -> ExtracaoResponse:
        raise TransientError("LLM timeout após 60s.")

    monkeypatch.setattr(
        "extracao_nf.api.routes.extrair.extrair_nota_fiscal",
        _falha,
    )

    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("nota.pdf", PDF_VALIDO, "application/pdf")},
    )

    assert response.status_code == 504
    assert "timeout" in response.json()["detail"].lower()


def test_extrair_nf_rate_limit_retorna_502(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TransientError sem timeout (ex.: rate limit) deve mapear para 502."""

    def _falha(**_kwargs: object) -> ExtracaoResponse:
        raise TransientError("Rate limit do provedor.")

    monkeypatch.setattr(
        "extracao_nf.api.routes.extrair.extrair_nota_fiscal",
        _falha,
    )

    response = client.post(
        "/extrair-nf",
        files={"arquivo": ("nota.pdf", PDF_VALIDO, "application/pdf")},
    )

    assert response.status_code == 502
    assert "rate limit" in response.json()["detail"].lower()
