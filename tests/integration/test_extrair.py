"""Testes de integração do endpoint POST /extrair-nf."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from extracao_nf.core.config import Settings, get_settings
from extracao_nf.main import app

PDF_VALIDO = b"%PDF-1.4\n% conteudo minimo de teste"
PNG_VALIDO = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_VALIDO = b"\xff\xd8\xff\xe0" + b"\x00" * 16


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente HTTP com limite de upload reduzido para facilitar testes."""
    settings = Settings(upload_max_bytes=1024)
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
    nome: str,
    conteudo: bytes,
    content_type: str,
) -> None:
    """PDF, PNG e JPEG válidos devem retornar 200 com metadados do upload."""
    response = client.post(
        "/extrair-nf",
        files={"arquivo": (nome, conteudo, content_type)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nome_arquivo"] == nome
    assert body["tamanho_bytes"] == len(conteudo)
    assert body["content_type"] == content_type
    assert "mensagem" in body


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
