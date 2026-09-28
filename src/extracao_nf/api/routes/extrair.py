from fastapi import APIRouter, Depends, HTTPException, UploadFile

from extracao_nf.api.upload_validation import validar_arquivo_upload
from extracao_nf.core.config import Settings, get_settings
from extracao_nf.core.exceptions import (
    ArquivoIlegivelError,
    ArquivoInvalidoError,
    PermanentError,
    TransientError,
)
from extracao_nf.core.logging import logger
from extracao_nf.domain.models import ExtracaoResponse
from extracao_nf.services.extrator_nf import extrair_nota_fiscal

router = APIRouter(tags=["Extração"])


def _status_falha_llm(exc: TransientError | PermanentError) -> int:
    if isinstance(exc, TransientError) and "timeout" in str(exc).lower():
        return 504
    return 502


@router.post(
    "/extrair-nf",
    summary="Extrair dados de Nota Fiscal",
    description=(
        "Recebe um arquivo PDF, PNG ou JPEG e retorna os dados estruturados "
        "extraídos via LLM (Gemini), com inconsistências determinísticas quando houver."
    ),
    response_model=ExtracaoResponse,
    status_code=200,
)
async def extrair_nf(
    arquivo: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ExtracaoResponse:
    conteudo = await arquivo.read()
    content_type_validado = validar_arquivo_upload(
        conteudo=conteudo,
        content_type=arquivo.content_type,
        tamanho_maximo_bytes=settings.upload_max_bytes,
    )

    nome_arquivo = arquivo.filename or "arquivo"
    logger.info(
        "upload_recebido",
        nome_arquivo=nome_arquivo,
        tamanho_bytes=len(conteudo),
        content_type=content_type_validado,
    )

    try:
        resposta = extrair_nota_fiscal(
            conteudo=conteudo,
            content_type=content_type_validado,
            settings=settings,
        )
    except ArquivoIlegivelError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ArquivoInvalidoError as exc:
        status = 415 if "não suportado" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except (TransientError, PermanentError) as exc:
        raise HTTPException(status_code=_status_falha_llm(exc), detail=str(exc)) from exc

    logger.info(
        "extracao_concluida",
        nome_arquivo=nome_arquivo,
        inconsistencias=len(resposta.inconsistencias),
    )
    return resposta
