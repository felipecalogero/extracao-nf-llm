"""Testes unitários do serviço de preparação de documento."""

from io import BytesIO

import pytest
from PIL import Image

from extracao_nf.core.exceptions import ArquivoIlegivelError, ArquivoInvalidoError
from extracao_nf.services.document_preparer import preparar_documento

PDF_VALIDO = b"%PDF-1.4\n% conteudo minimo de teste"


def _criar_imagem_bytes(formato: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(buffer, format=formato)
    return buffer.getvalue()


def test_preparar_documento_pdf_valido() -> None:
    """PDF com assinatura %PDF deve gerar data URI em base64."""
    documento = preparar_documento(conteudo=PDF_VALIDO, content_type="application/pdf")

    assert documento.content_type == "application/pdf"
    assert documento.tamanho_bytes == len(PDF_VALIDO)
    assert documento.data_uri.startswith("data:application/pdf;base64,")
    assert len(documento.data_uri) > len("data:application/pdf;base64,")


@pytest.mark.parametrize(
    ("formato", "content_type"),
    [
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
    ],
)
def test_preparar_documento_imagem_valida(formato: str, content_type: str) -> None:
    """Imagens legíveis pelo Pillow devem gerar data URI correspondente."""
    conteudo = _criar_imagem_bytes(formato)
    documento = preparar_documento(conteudo=conteudo, content_type=content_type)

    assert documento.content_type == content_type
    assert documento.tamanho_bytes == len(conteudo)
    assert documento.data_uri.startswith(f"data:{content_type};base64,")


def test_preparar_documento_rejeita_arquivo_vazio() -> None:
    """Arquivo sem bytes deve levantar ArquivoInvalidoError."""
    with pytest.raises(ArquivoInvalidoError, match="vazio"):
        preparar_documento(conteudo=b"", content_type="application/pdf")


def test_preparar_documento_rejeita_tipo_nao_suportado() -> None:
    """Tipo MIME fora da lista permitida deve levantar ArquivoInvalidoError."""
    with pytest.raises(ArquivoInvalidoError, match="não suportado"):
        preparar_documento(conteudo=b"conteudo", content_type="text/plain")


def test_preparar_documento_rejeita_pdf_corrompido() -> None:
    """PDF sem assinatura %PDF deve levantar ArquivoInvalidoError."""
    with pytest.raises(ArquivoInvalidoError, match="corrompido"):
        preparar_documento(conteudo=b"nao-e-pdf", content_type="application/pdf")


def test_preparar_documento_rejeita_imagem_corrompida() -> None:
    """PNG com header válido mas conteúdo inválido deve levantar ArquivoIlegivelError."""
    png_corrompido = b"\x89PNG\r\n\x1a\n" + b"conteudo-invalido"

    with pytest.raises(ArquivoIlegivelError, match="ilegível"):
        preparar_documento(conteudo=png_corrompido, content_type="image/png")
