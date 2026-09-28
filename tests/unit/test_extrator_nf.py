"""Testes unitários do orquestrador de extração (Parte 6)."""

from typing import cast
from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import SecretStr

from extracao_nf.core.config import Settings
from extracao_nf.core.exceptions import ArquivoInvalidoError, PermanentError, TransientError
from extracao_nf.domain.enums import TipoDocumento, TipoInconsistencia
from extracao_nf.domain.models import (
    DadosNota,
    Emitente,
    NotaFiscalExtraida,
    Produto,
    Valores,
)
from extracao_nf.services.extrator_nf import (
    ChainExtracao,
    calcular_inconsistencias,
    extrair_nota_fiscal,
)

PDF_VALIDO = b"%PDF-1.4\n% conteudo minimo de teste"


def _settings() -> Settings:
    return Settings(
        environment="test",
        google_api_key=SecretStr("fake-key"),
        gemini_model="gemini-2.5-flash",
    )


def _nota_completa() -> NotaFiscalExtraida:
    return NotaFiscalExtraida(
        emitente=Emitente(razao_social="ACME LTDA", cnpj="12345678000190"),
        destinatario=None,
        dados_nota=DadosNota(
            numero="123456",
            serie="1",
            tipo_documento=TipoDocumento.NFE,
            data_emissao="2026-03-15",
        ),
        valores=Valores(valor_produtos=1250.0, valor_total_nota=1250.0),
        produtos=[
            Produto(
                descricao="Notebook",
                quantidade=1.0,
                valor_unitario=1250.0,
                valor_total=1250.0,
            )
        ],
    )


def test_extrair_nota_fiscal_completa_ok() -> None:
    """Extração OK com LLM mockado devolve ExtracaoResponse sem inconsistências."""
    nota = _nota_completa()
    chain: ChainExtracao = RunnableLambda(lambda _entrada: nota)

    resposta = extrair_nota_fiscal(
        conteudo=PDF_VALIDO,
        content_type="application/pdf",
        settings=_settings(),
        chain=chain,
    )

    assert resposta.nota_fiscal.emitente.razao_social == "ACME LTDA"
    assert resposta.nota_fiscal.destinatario is None
    assert resposta.inconsistencias == []


def test_extrair_nota_fiscal_campo_faltante_permanece_null() -> None:
    """Campos ausentes ficam null e não viram inconsistência."""
    nota = NotaFiscalExtraida(
        emitente=Emitente(razao_social="LOJA XYZ", cnpj=None),
        destinatario=None,
        dados_nota=DadosNota(numero=None, chave_acesso=None),
        valores=Valores(valor_total_nota=89.9),
        produtos=[],
    )
    chain: ChainExtracao = RunnableLambda(lambda _entrada: nota)

    resposta = extrair_nota_fiscal(
        conteudo=PDF_VALIDO,
        content_type="application/pdf",
        settings=_settings(),
        chain=chain,
    )

    assert resposta.nota_fiscal.emitente.cnpj is None
    assert resposta.nota_fiscal.dados_nota.numero is None
    assert resposta.nota_fiscal.destinatario is None
    assert resposta.inconsistencias == []


def test_extrair_nota_fiscal_soma_produtos_divergente() -> None:
    """Soma dos itens diferente do total gera inconsistência sem quebrar a resposta."""
    nota = NotaFiscalExtraida(
        emitente=Emitente(razao_social="ACME LTDA"),
        valores=Valores(valor_total_nota=100.0),
        produtos=[
            Produto(descricao="A", valor_total=60.0),
            Produto(descricao="B", valor_total=50.0),
        ],
    )
    chain: ChainExtracao = RunnableLambda(lambda _entrada: nota)

    resposta = extrair_nota_fiscal(
        conteudo=PDF_VALIDO,
        content_type="application/pdf",
        settings=_settings(),
        chain=chain,
    )

    assert resposta.nota_fiscal.valores.valor_total_nota == 100.0
    assert len(resposta.inconsistencias) == 1
    inconsistencia = resposta.inconsistencias[0]
    assert inconsistencia.tipo == TipoInconsistencia.SOMA_PRODUTOS_DIVERGE_TOTAL
    assert inconsistencia.campo == "valores.valor_total_nota"
    assert inconsistencia.valor_esperado == "110.00"
    assert inconsistencia.valor_encontrado == "100.00"


def test_calcular_inconsistencias_sem_produtos_nao_gera_alerta() -> None:
    """Sem itens com valor_total, não há como cruzar soma vs total."""
    nota = NotaFiscalExtraida(valores=Valores(valor_total_nota=50.0), produtos=[])
    assert calcular_inconsistencias(nota) == []


def test_extrair_nota_fiscal_timeout_vira_transient_error() -> None:
    """Timeout do LLM deve ser mapeado para TransientError."""

    def _falhar(_entrada: object) -> NotaFiscalExtraida:
        raise TimeoutError("deadline exceeded")

    chain = RunnableLambda(_falhar)

    with pytest.raises(TransientError, match="Falha na chamada ao LLM"):
        extrair_nota_fiscal(
            conteudo=PDF_VALIDO,
            content_type="application/pdf",
            settings=_settings(),
            chain=chain,
        )


def test_extrair_nota_fiscal_rate_limit_vira_transient_error() -> None:
    """Rate limit (429) deve ser classificado como TransientError."""

    def _falhar(_entrada: object) -> NotaFiscalExtraida:
        raise RuntimeError("Error 429: rate limit exceeded")

    with pytest.raises(TransientError):
        extrair_nota_fiscal(
            conteudo=PDF_VALIDO,
            content_type="application/pdf",
            settings=_settings(),
            chain=RunnableLambda(_falhar),
        )


def test_extrair_nota_fiscal_erro_permanente_do_llm() -> None:
    """Erro de autenticação/request inválido vira PermanentError."""

    def _falhar(_entrada: object) -> NotaFiscalExtraida:
        raise RuntimeError("401 Unauthorized: invalid API key")

    with pytest.raises(PermanentError, match="Falha na chamada ao LLM"):
        extrair_nota_fiscal(
            conteudo=PDF_VALIDO,
            content_type="application/pdf",
            settings=_settings(),
            chain=RunnableLambda(_falhar),
        )


def test_extrair_nota_fiscal_rejeita_resposta_fora_do_schema() -> None:
    """Resposta que não é NotaFiscalExtraida vira PermanentError."""
    chain = cast(ChainExtracao, RunnableLambda(lambda _entrada: {"emitente": {}}))

    with pytest.raises(PermanentError, match="fora do schema"):
        extrair_nota_fiscal(
            conteudo=PDF_VALIDO,
            content_type="application/pdf",
            settings=_settings(),
            chain=chain,
        )


def test_extrair_nota_fiscal_propaga_arquivo_invalido() -> None:
    """Arquivo inválido deve falhar antes de chamar o LLM."""
    chain = MagicMock()

    with pytest.raises(ArquivoInvalidoError, match="vazio"):
        extrair_nota_fiscal(
            conteudo=b"",
            content_type="application/pdf",
            settings=_settings(),
            chain=chain,
        )

    chain.invoke.assert_not_called()
