from __future__ import annotations

from langchain_core.runnables import Runnable

from extracao_nf.core.config import Settings
from extracao_nf.core.exceptions import (
    ArquivoIlegivelError,
    ArquivoInvalidoError,
    ExtracaoNFError,
    PermanentError,
    TransientError,
)
from extracao_nf.core.logging import logger
from extracao_nf.domain.enums import TipoInconsistencia
from extracao_nf.domain.models import ExtracaoResponse, Inconsistencia, NotaFiscalExtraida
from extracao_nf.services.document_preparer import preparar_documento
from extracao_nf.services.prompt_builder import montar_chain

type ChainExtracao = Runnable[dict[str, str], NotaFiscalExtraida]

# invariant: 1 centavo evita falso positivo por aritmética de float
_TOLERANCIA_MONETARIA = 0.01

_MARCADORES_TRANSITORIOS = (
    "timeout",
    "timed out",
    "rate limit",
    "rate_limit",
    "resource_exhausted",
    "429",
    "500",
    "502",
    "503",
    "504",
    "unavailable",
    "temporarily",
    "overloaded",
)


def _eh_erro_transitorio(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, InterruptedError)):
        return True

    nome = type(exc).__name__.lower()
    if any(token in nome for token in ("timeout", "ratelimit", "unavailable", "internalserver")):
        return True

    mensagem = str(exc).lower()
    return any(marcador in mensagem for marcador in _MARCADORES_TRANSITORIOS)


def _mapear_erro_llm(exc: BaseException) -> ExtracaoNFError:
    if isinstance(exc, ExtracaoNFError):
        return exc

    mensagem = f"Falha na chamada ao LLM: {exc}"
    if _eh_erro_transitorio(exc):
        return TransientError(mensagem)
    return PermanentError(mensagem)


def calcular_inconsistencias(nota: NotaFiscalExtraida) -> list[Inconsistencia]:
    # invariant: campo ausente (null) não é inconsistência — só divergência numérica cruzada
    inconsistencias: list[Inconsistencia] = []

    totais_itens = [p.valor_total for p in nota.produtos if p.valor_total is not None]
    total_nota = nota.valores.valor_total_nota

    if totais_itens and total_nota is not None:
        soma_produtos = sum(totais_itens)
        if abs(soma_produtos - total_nota) > _TOLERANCIA_MONETARIA:
            inconsistencias.append(
                Inconsistencia(
                    tipo=TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL,
                    campo="valores.valor_total_nota",
                    descricao=(
                        "A soma dos valor_total dos produtos diverge do "
                        "valores.valor_total_nota informado no documento."
                    ),
                    valor_esperado=f"{soma_produtos:.2f}",
                    valor_encontrado=f"{total_nota:.2f}",
                )
            )

    return inconsistencias


def extrair_nota_fiscal(
    *,
    conteudo: bytes,
    content_type: str,
    settings: Settings,
    chain: ChainExtracao | None = None,
) -> ExtracaoResponse:
    documento = preparar_documento(conteudo=conteudo, content_type=content_type)
    logger.info(
        "documento_preparado",
        content_type=documento.content_type,
        tamanho_bytes=documento.tamanho_bytes,
    )

    chain_extracao = chain if chain is not None else montar_chain(settings=settings)

    try:
        nota = chain_extracao.invoke({"data_uri": documento.data_uri})
    except (ArquivoInvalidoError, ArquivoIlegivelError):
        raise
    except ExtracaoNFError:
        raise
    except Exception as exc:
        erro = _mapear_erro_llm(exc)
        logger.error(
            "falha_llm",
            erro=str(erro),
            tipo_erro=type(erro).__name__,
            causa=type(exc).__name__,
        )
        raise erro from exc

    if not isinstance(nota, NotaFiscalExtraida):
        raise PermanentError(f"Resposta do LLM fora do schema esperado: {type(nota).__name__}.")

    inconsistencias = calcular_inconsistencias(nota)
    logger.info(
        "extracao_concluida",
        inconsistencias=len(inconsistencias),
        produtos=len(nota.produtos),
    )

    return ExtracaoResponse(nota_fiscal=nota, inconsistencias=inconsistencias)
