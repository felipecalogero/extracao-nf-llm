"""Fakes e builders reutilizáveis nos testes unitários e de integração."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock

from langchain_core.runnables import RunnableLambda
from PIL import Image
from pydantic import SecretStr

from extracao_nf.core.config import Settings
from extracao_nf.domain.enums import TipoDocumento
from extracao_nf.domain.models import (
    DadosNota,
    Destinatario,
    Emitente,
    ExtracaoResponse,
    Inconsistencia,
    NotaFiscalExtraida,
    Produto,
    Valores,
)

PDF_VALIDO = b"%PDF-1.4\n% conteudo minimo de teste"


def bytes_imagem(formato: str = "PNG", size: tuple[int, int] = (2, 2)) -> bytes:
    """Gera bytes mínimos de PNG/JPEG via Pillow para testes de upload."""
    buffer = BytesIO()
    Image.new("RGB", size, color="white").save(buffer, format=formato)
    return buffer.getvalue()


def settings_teste(
    *,
    google_api_key: str | None = "fake",
    upload_max_bytes: int = 1024,
    gemini_model: str = "gemini-3.8-flash",
    llm_temperature: float = 0.0,
    llm_timeout_seconds: float = 30.0,
) -> Settings:
    """Settings padrão para ambiente de teste (sem ler .env real)."""
    return Settings(
        environment="test",
        google_api_key=SecretStr(google_api_key) if google_api_key is not None else None,
        upload_max_bytes=upload_max_bytes,
        gemini_model=gemini_model,
        llm_temperature=llm_temperature,
        llm_timeout_seconds=llm_timeout_seconds,
    )


def nota_fiscal_exemplo(
    *,
    razao_social: str | None = "ACME LTDA",
    cnpj: str | None = "12345678000190",
    numero: str | None = "123456",
    serie: str | None = "1",
    tipo_documento: TipoDocumento = TipoDocumento.NFE,
    data_emissao: str | None = "2026-03-15",
    valor_total_nota: float | None = 1250.0,
    valor_produtos: float | None = 1250.0,
    produtos: list[Produto] | None = None,
    destinatario: Destinatario | None = None,
) -> NotaFiscalExtraida:
    """Nota fiscal completa típica (emitente ACME + 1 notebook)."""
    if produtos is None:
        produtos = [
            Produto(
                descricao="Notebook",
                quantidade=1.0,
                valor_unitario=1250.0,
                valor_total=1250.0,
            )
        ]

    return NotaFiscalExtraida(
        emitente=Emitente(razao_social=razao_social, cnpj=cnpj),
        destinatario=destinatario,
        dados_nota=DadosNota(
            numero=numero,
            serie=serie,
            tipo_documento=tipo_documento,
            data_emissao=data_emissao,
        ),
        valores=Valores(valor_produtos=valor_produtos, valor_total_nota=valor_total_nota),
        produtos=produtos,
    )


def extracao_response_exemplo(
    *,
    nota_fiscal: NotaFiscalExtraida | None = None,
    inconsistencias: list[Inconsistencia] | None = None,
) -> ExtracaoResponse:
    """Resposta HTTP típica de sucesso (usada em testes de integração)."""
    if nota_fiscal is None:
        nota_fiscal = NotaFiscalExtraida(
            emitente=Emitente(razao_social="ACME"),
            valores=Valores(valor_total_nota=10.0),
        )
    return ExtracaoResponse(
        nota_fiscal=nota_fiscal,
        inconsistencias=inconsistencias or [],
    )


def chain_retorna(nota: NotaFiscalExtraida) -> RunnableLambda[dict[str, str], NotaFiscalExtraida]:
    """Chain fake que sempre devolve a nota informada."""
    return RunnableLambda(lambda _entrada: nota)


def chain_erro(exc: BaseException) -> RunnableLambda[dict[str, str], NotaFiscalExtraida]:
    """Chain fake que sempre levanta a exceção informada."""

    def _falhar(_entrada: object) -> NotaFiscalExtraida:
        raise exc

    return RunnableLambda(_falhar)


def fake_llm_com_nota(nota: NotaFiscalExtraida | None = None) -> MagicMock:
    """LLM fake cujo with_structured_output devolve a nota via RunnableLambda."""
    if nota is None:
        nota = NotaFiscalExtraida()
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_retorna(nota)
    return llm
