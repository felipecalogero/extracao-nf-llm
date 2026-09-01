"""Endpoint POST /extrair-nf.

Recebe um arquivo (PDF ou imagem), valida tipo/tamanho e, por enquanto,
retorna um stub com metadados do upload — sem chamar o LLM.
"""

from fastapi import APIRouter, Depends, UploadFile

from extracao_nf.api.schemas import ExtracaoStubResponse
from extracao_nf.api.upload_validation import validar_arquivo_upload
from extracao_nf.core.config import Settings, get_settings
from extracao_nf.core.logging import logger

router = APIRouter(tags=["Extração"])


@router.post(
    "/extrair-nf",
    summary="Extrair dados de Nota Fiscal",
    description=(
        "Recebe um arquivo PDF, PNG ou JPEG e valida o upload. "
        "A extração via LLM será integrada nas próximas etapas."
    ),
    response_model=ExtracaoStubResponse,
    status_code=200,
)
async def extrair_nf(
    arquivo: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ExtracaoStubResponse:
    """Valida o arquivo enviado e retorna metadados (stub)."""
    conteudo = await arquivo.read()
    content_type_validado = validar_arquivo_upload(
        conteudo=conteudo,
        content_type=arquivo.content_type,
        tamanho_maximo_bytes=settings.upload_max_bytes,
    )

    nome_arquivo = arquivo.filename or "arquivo"
    logger.info(
        "upload recebido",
        nome_arquivo=nome_arquivo,
        tamanho_bytes=len(conteudo),
        content_type=content_type_validado,
    )

    return ExtracaoStubResponse(
        nome_arquivo=nome_arquivo,
        tamanho_bytes=len(conteudo),
        content_type=content_type_validado,
    )
